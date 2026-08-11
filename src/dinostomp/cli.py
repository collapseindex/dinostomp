"""dinostomp CLI.

    dinostomp new <dir>           scaffold a fresh eval pod
    dinostomp validate <spec>     check a spec and print machine-readable issues
    dinostomp run <spec>          run it (witness gate, budget cap, resumable)
    dinostomp stomp <spec>        lint the spec, dataset, and runs; honest verdict
    dinostomp report <spec>       stomp, then write STOMP.md + STOMP.json + badge
    dinostomp verify <spec>       re-derive a pod's PUBLISHED report offline;
                                  verified / mismatch / unverifiable
    dinostomp plan <spec>         power, cost, and witness preview BEFORE money
    dinostomp fingerprint         SHA-256 of this engine's own code and schemas
    dinostomp inspect <spec>      what a pod's Python touches, WITHOUT running it

Exit codes, per command:
  new:      0 created, 2 path exists / bad args
  validate: 0 valid, 2 invalid
  run:      0 complete, 1 gated (witnesses failed, nothing ran),
            2 cannot run (invalid spec/data, unknown price, missing key),
            3 stopped early (budget/provider/scorer; partial on disk, resumable)
  stomp:    0 clean or ok, 1 broken, 2 cannot stomp, 4 incomplete
  report:   same as stomp
  verify:   0 verified, 1 mismatch, 2 unverifiable
  plan:     0 planned, 2 cannot plan
  fingerprint: 0 always (it reports, it does not judge)
  inspect:  0 nothing flagged, 1 capabilities worth reading, 2 cannot inspect
Incomplete (4) is nonzero BY DEFAULT: an unattended pipeline must not accept
thin coverage because someone forgot a flag. --allow-incomplete is the
explicit escape hatch.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from pathlib import Path

import dinostomp
from dinostomp.claims import describe as describe_claim
from dinostomp.fingerprint import engine_files, engine_fingerprint
from dinostomp.inspection import inspect_file
from dinostomp.items import load_items
from dinostomp.dataset import looks_like_dataset, repair_items, unrepairable_findings
from dinostomp.evidence import NEEDS, missing_for, survey
from dinostomp.importing import (build_manifest, infer_record_mapping, read_log,
                                 to_records, write_run)
from dinostomp.lint import (ORDERING_WORDS, SCOPE_BLURB, SCOPE_CHECKS, SLUGS,
                            _discover_runs, _expected_hashes, lint_dataset, lint_eval)
from dinostomp.mutation import run_gauntlet
from dinostomp.overlap import load_reference
from dinostomp.providers import DEFAULT_MAX_TOKENS
from dinostomp.psychometrics import min_detectable_effect, n_for_effect
from dinostomp.report import verify_report, write_report
from dinostomp.runner import (CHARS_PER_TOKEN_EST, GATED, CANNOT_RUN, resolve_rates,
                              run_spec, run_template_probe, select_items)
from dinostomp.providers import ProviderError
from dinostomp.scorers import make_scorer, run_witnesses
from dinostomp.spec import load_spec
from dinostomp.suggest import propose

LEVEL_TAGS = {"pass": "[ok]  ", "fail": "[FAIL]", "warn": "[warn]", "skip": "[skip]", "n/a": "[n/a] "}

INCOMPLETE_EXIT = 4


def _verdict_exit(verdict: str, allow_incomplete: bool) -> int:
    if verdict == "broken":
        return 1
    if verdict == "incomplete" and not allow_incomplete:
        return INCOMPLETE_EXIT
    return 0


def _print_issues(issues) -> None:
    for i in issues:
        print(f"  [{i.check}] {i.loc}: {i.message}")


POD_TEMPLATE = """\
# New dinostomp pod. Edit the question, drop your items in items.jsonl,
# swap the dry model for a real provider when ready. The witnesses are
# not decoration: the run refuses to start if the scorer cannot fail.
name: {name}
version: 0.1.0
question: "REPLACE ME: the one question this eval answers, in one sentence."

entitled_claims:
  - "REPLACE ME: what a green result is allowed to claim. Nothing more."

data:
  path: items.jsonl
  format: jsonl

models:
  - {{provider: dry, model: dry-strong}}

scorer:
  kind: exact
  # One fail witness per scoring-bug class; the W1 mutation gauntlet checks
  # that every applicable mutant scorer dies against this suite.
  witnesses:
    - {{output: "expected answer", target: "expected answer", expect: pass}}
    - {{output: "The answer is: expected answer", target: "expected answer", expect: fail, why: "no credit for wrappers"}}
    - {{output: "expected", target: "expected answer", expect: fail, why: "no credit for truncation"}}
    - {{output: "not expected answer", target: "expected answer", expect: fail, why: "no credit for negation"}}
    - {{output: "EXPECTED ANSWER", target: "expected answer", expect: fail, why: "case is part of the contract"}}
    - {{output: "expected  answer", target: "expected answer", expect: fail, why: "whitespace is part of the contract"}}
    - {{output: "wrong answer", target: "expected answer", expect: fail}}

run:
  n: 3
  seed: 42
  budget_usd: 0
"""

POD_ITEMS = """\
{{"_canary": "dinostomp canary DO NOT TRAIN {canary}"}}
{{"id": "ex1", "input": "REPLACE ME: first question", "target": "expected answer"}}
{{"id": "ex2", "input": "REPLACE ME: second question", "target": "expected answer"}}
{{"id": "ex3", "input": "REPLACE ME: third question", "target": "expected answer"}}
"""


def cmd_new(args) -> int:
    pod = Path(args.directory)
    if pod.exists():
        print(f"refusing to touch an existing path: {pod}")
        return CANNOT_RUN
    name = re.sub(r"[^a-z0-9_-]+", "-", pod.name.lower()).strip("-") or "new-eval"
    pod.mkdir(parents=True)
    (pod / "eval.yaml").write_text(POD_TEMPLATE.format(name=name), encoding="utf-8", newline="\n")
    (pod / "items.jsonl").write_text(POD_ITEMS.format(canary=uuid.uuid4().hex), encoding="utf-8", newline="\n")
    print(f"pod created: {pod}")
    print(f"  next: edit {pod / 'eval.yaml'} and {pod / 'items.jsonl'}")
    print(f"  then: dinostomp run {pod / 'eval.yaml'} && dinostomp stomp {pod / 'eval.yaml'}")
    return 0


NL = chr(10)


def cmd_inspect(args) -> int:
    """Read a pod's Python statically, so --trust-code can be an informed choice.

    This never imports anything: that is the entire point. It is not a sandbox
    and not a malware detector, and a clean report is not a safety certificate.
    """
    spec, issues = load_spec(args.spec)
    if spec is None:
        print("UNREADABLE:")
        _print_issues(issues)
        return CANNOT_RUN
    base = Path(args.spec).resolve().parent

    paths = []
    scorer = spec.get("scorer") or {}
    if scorer.get("kind") == "python" and scorer.get("code"):
        paths.append(("scorer", scorer["code"]))
    judge = scorer.get("judge") or {}
    if judge.get("provider") == "python" and judge.get("entrypoint"):
        paths.append(("judge", judge["entrypoint"].rpartition(":")[0] or judge["entrypoint"]))
    for mc in spec.get("models") or []:
        # BOTH code rails. A mediated agent is imported and run exactly like a
        # python target; only its tools are held elsewhere. Listing one and not
        # the other told a reader of a mediated pod that it "ships no pod-local
        # Python", which was the most flattering possible falsehood (D-030).
        if mc.get("provider") in ("python", "mediated") and mc.get("entrypoint"):
            rel = mc["entrypoint"].rpartition(":")[0] or mc["entrypoint"]
            paths.append((f"target {mc['model']}", rel))

    # TOOLS ARE THE MOST PRIVILEGED CODE IN A POD. They are imported and called
    # in the PARENT process, which is true even under `isolation: subprocess`:
    # the boundary exists to keep the AGENT away from them, not to contain them.
    # A reader deciding on --trust-code needs these more than anything else here.
    for name, entry in (spec.get("tools") or {}).items():
        rel = str(entry).rpartition(":")[0] or str(entry)
        paths.append((f"tool {name} [runs in the PARENT process]", rel))

    if not paths:
        print(f"{spec['name']}: ships no pod-local Python. Nothing here can run on your machine.")
        return 0

    by_path: dict[str, list[str]] = {}
    for role, rel in paths:
        by_path.setdefault(rel, []).append(role)
    flagged = 0
    print(f"{spec['name']}: {len(by_path)} pod-local Python file(s). Read this before --trust-code.")
    for rel, roles in by_path.items():
        role = ", ".join(roles)
        report = inspect_file(base / rel)
        print(f"{NL}  {rel}  ({role})")
        if report.error:
            print(f"    [!] {report.error}")
            flagged += 1
            continue
        if report.clean:
            print("    nothing flagged. Note this is a static read, not a guarantee.")
            continue
        flagged += 1
        for f in report.findings:
            print(f"    [!] {f}")
    print(f"{NL}This is NOT a sandbox and NOT a malware detector: it reports what the code reaches "
          "for, statically, and a determined author can hide any of it.")
    return 1 if flagged else 0


def cmd_fingerprint(args) -> int:
    """The engine's own hash, so a reader can confirm which bytes judged them."""
    value = engine_fingerprint()
    files = engine_files()
    print(value)
    if args.verbose:
        print(f"  dinostomp {dinostomp.__version__}")
        print(f"  covers {len(files)} shipped file(s) under src/dinostomp (code + schemas)")
        print("  compare against the value published in the README; a difference means the "
              "engine is not the one that README describes")
    return 0


def cmd_validate(args) -> int:
    spec, issues = load_spec(args.spec)
    if args.json:
        print(json.dumps([i.to_dict() for i in issues], indent=2))
        return 0 if spec is not None and not issues else CANNOT_RUN
    if spec is None:
        print("UNREADABLE:")
        _print_issues(issues)
        return CANNOT_RUN
    if issues:
        print(f"INVALID: {len(issues)} issue(s)")
        _print_issues(issues)
        return CANNOT_RUN
    print(f"VALID: {spec['name']} v{spec['version']}")
    print(f"  question: {spec['question']}")
    return 0


def cmd_run(args) -> int:
    if args.probe == "template":
        # One pass per framing, so this one has its own driver. The cost is
        # linear in the number of framings and it is real money, which is why
        # `plan` states it before anything is spent.
        framings = [f.strip() for f in args.framings.split(",")] if args.framings else None
        outcome = run_template_probe(args.spec, framings=framings)
    else:
        outcome = run_spec(
            args.spec,
            resume=Path(args.resume) if args.resume else None,
            limit=args.limit,
            dry_run=args.dry_run,
            price_in=args.price_in,
            price_out=args.price_out,
            probe=args.probe,
        )
    if outcome.exit_code == CANNOT_RUN:
        print("CANNOT RUN:")
        _print_issues(outcome.issues)
        return CANNOT_RUN
    if outcome.exit_code == GATED:
        print(f"GATED: {len(outcome.witness_failures)} witness case(s) misbehaved. Nothing was run.")
        for f in outcome.witness_failures:
            why = f" ({f['why']})" if f.get("why") else ""
            print(
                f"  witness[{f['index']}]: expected {f['expected']}, got {f['got']}"
                f" on output {f['output']!r} vs target {f['target']!r}{why}"
            )
            if f.get("evidence"):
                print(f"    scorer evidence: {f['evidence']}")
        return GATED
    for s in outcome.summaries:
        if s.get("probe") == "judge":
            # A probe is not a result and must never be printed like one: half
            # its cases are supposed to fail, so it has no accuracy to report.
            agree = s.get("agreement_with_construction")
            agree_str = "n/a" if agree is None else f"{agree:.0%}"
            print(
                f"{s['spec_name']} | {s['model']} | {s['status']} | JUDGE PROBE | "
                f"agrees with {agree_str} of {s['n_baseline_cases']} known case(s), "
                f"{s['n_records']} grading(s) over {s['n_perturbations']} perturbation(s) "
                f"| ${s['spend_usd']:.4f}"
            )
            continue
        if s.get("probe") == "crossjudge":
            # A cross-judge run re-grades recorded outputs with a SECOND judge.
            # It has no accuracy of its own; what it produces is a difference of
            # differences that J4 reads. Printing it like a result would invite
            # someone to quote a second judge's pass rate as a model's score.
            print(
                f"{s['spec_name']} | {s['model']} | {s['status']} | CROSS-JUDGE PROBE | "
                f"{s['n_records']} regrading(s) of recorded outputs "
                f"| ${s['spend_usd']:.4f}"
            )
            continue
        if s.get("probe"):
            # Any other probe: report it as a probe rather than crashing on a
            # field its summary shape does not carry. `crossjudge` reached the
            # accuracy line and raised KeyError on the first real cross-judge
            # run this project ever did.
            print(f"{s['spec_name']} | {s['model']} | {s['status']} | "
                  f"{s['probe'].upper()} PROBE | {s['n_records']} record(s) "
                  f"| ${s['spend_usd']:.4f}")
            continue
        acc = s["accuracy_on_checkable"]
        if acc is None:
            acc_str = "n/a (nothing checkable)"
        else:
            lo, hi = s["accuracy_ci95"]
            acc_str = f"{acc:.3f} [{lo:.2f}, {hi:.2f}]"
        print(
            f"{s['spec_name']} | {s['model']} | {s['status']} | "
            f"acc {acc_str} on {s['n_checkable']} checkable "
            f"({s['n_uncheckable']} uncheckable excluded) | ${s['spend_usd']:.4f}"
        )
    for p in outcome.run_files:
        print(f"  run file: {p}")
    if outcome.stopped_reason:
        print(f"STOPPED EARLY: {outcome.stopped_reason}")
        print("  resume with: dinostomp run <spec> --resume <run file>")
    return outcome.exit_code


def _stomp_dataset(args) -> int:
    """`dinostomp stomp mydata.csv`: the front door.

    Every finding this project has made in someone else's data came from checks
    that read items at rest. Making people write a spec to reach them taxes the
    one thing the tool is demonstrably good at.
    """
    overrides = {"id": getattr(args, "id_field", None), "input": getattr(args, "input_field", None),
                 "target": getattr(args, "target_field", None),
                 "choices": getattr(args, "choices_field", None)}
    references, ref_errors = {}, []
    for ref in (getattr(args, "against", None) or []):
        ref_items, errs = load_reference(ref)
        ref_errors.extend(errs)
        if ref_items:
            references[Path(ref).name] = ref_items
    for err in ref_errors:
        print(f"  [reference] skipped: {err}")
    report, issues, ctx = lint_dataset(args.spec, field_overrides=overrides,
                                       separator=getattr(args, "separator", None),
                                       references=references,
                                       use_extensions=not getattr(args, "no_extensions", False))
    if report is None:
        print("CANNOT STOMP:")
        _print_issues(issues)
        if ctx.get("notes"):
            print("  what was read:")
            for note in ctx["notes"]:
                print(f"    {note}")
        return CANNOT_RUN

    # A report with no `dataset` block came from the extension-only path: the
    # core could not read the file or found no eval mapping in it, and every
    # finding below belongs to an extension that could.
    ds = report.get("dataset")
    if ds:
        print(f"DATASET AUDIT: {Path(args.spec).name}  "
              f"({ds['items']} items from {ds['rows']} rows)")
    else:
        print(f"DATASET AUDIT: {Path(args.spec).name}  (no core check ran)")
        _print_issues(issues)
    # The mapping is a GUESS, and every finding below rests on it. Printed
    # first, above the findings, because a guess the reader cannot see is a
    # guess the reader cannot correct.
    for note in ctx["notes"]:
        print(f"  {note}")
    print()
    # Skips that all share one reason get one line. Sixty-one identical
    # "over the 100MB cap" rows bury the findings underneath them, and a reader
    # who scrolls past the wall of grey is a reader who missed the audit.
    shared_skip = ""
    if not ds:
        reasons = {f["detail"] for f in report["findings"] if f["level"] == "skip"}
        if len(reasons) == 1:
            shared_skip = reasons.pop()
    for f in report["findings"]:
        if f["level"] == "n/a" or (shared_skip and f["level"] == "skip"):
            continue
        print(f"  {LEVEL_TAGS[f['level']]} {f['slug']:<22} {f['check']:<56} {f['detail']}")
        for ex in f.get("examples", []):
            print(f"           - {ex}")
    if shared_skip:
        n = sum(1 for f in report["findings"] if f["level"] == "skip")
        print(f"  [skip] {n} core check(s), all for the same reason: {shared_skip}")
        print()
    for f in report.get("extension_findings", []):
        if f["level"] == "n/a":
            continue
        print(f"  {LEVEL_TAGS[f['level']]} {f['check_id']:<22} "
              f"{('' if f['validated'] else '[unvalidated] '):<56}{f['detail']}")
        for ex in f.get("examples", []):
            print(f"           - {ex}")

    cov = report["coverage"]
    fails, warns = report["summary"]["fail"], report["summary"]["warn"]
    verdict = report["summary"]["verdict"]
    in_scope = len(SCOPE_CHECKS["data"])
    print()
    # Scoped verdict: this audit is structurally incomplete forever, and
    # exiting nonzero for that would train people to pass --allow-incomplete by
    # reflex. It reports at DATA scope and says so.
    # Order matters, and it was wrong here: `warns` was tested before the
    # computed verdict, so an audit where every data check skipped and one
    # extension warned printed "OK AT DATA SCOPE" over a report whose own
    # summary said `incomplete`. Coverage outranks tone. INCOMPLETE first.
    if fails:
        print(f"BROKEN AT DATA SCOPE: {fails} gated finding(s) in the dataset itself")
    elif verdict == "incomplete":
        n_skipped = len(cov["skipped"])
        print(f"INCOMPLETE AT DATA SCOPE: {n_skipped} check(s) could not run"
              + (f", and {warns} warning(s) came from what did" if warns else ""))
    elif warns:
        print(f"OK AT DATA SCOPE: no failures, {warns} warning(s)")
    else:
        print(f"MECHANICALLY SOUND AT DATA SCOPE: no integrity findings across "
              f"{cov['ran']} of {in_scope} data checks")
    print(f"  Scope: {SCOPE_BLURB['data']}. The other "
          f"{cov['declared_total'] - in_scope} checks need a scorer, a run, or a claim, and are "
          f"out of scope here rather than missing: `dinostomp new <dir>` builds the pod that "
          f"reaches them.")
    if getattr(args, "emit_fixes", False):
        _emit_fixes(args, report, ctx)
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2), encoding="utf-8", newline="\n")
        print(f"  wrote: {args.json}")
    return 1 if fails else 0


def _emit_fixes(args, report: dict, ctx: dict) -> None:
    """Write the repaired dataset next to the original, plus a per-item log.

    Only mechanical repairs: deletions and deduplications a reader can verify by
    eye. Nothing here invents an answer or rewrites a question, and every
    finding that CANNOT be repaired that way is printed with the reason, so a
    repaired file is never mistaken for a clean one.
    """
    items = ctx.get("items") or []
    kept, log = repair_items(items, report)
    src = Path(args.spec)
    out = (Path(args.emit_fixes) if isinstance(args.emit_fixes, str)
           else src.with_name(f"{src.stem}.fixed.jsonl"))
    logfile = out.with_name(out.stem + ".fixes.txt")

    body = "\n".join(json.dumps(i, ensure_ascii=False) for i in kept)
    out.write_text(body + "\n", encoding="utf-8", newline="\n")
    header = [f"# dinostomp {dinostomp.__version__} (engine {engine_fingerprint()[:16]})",
              f"# source: {src.name}", f"# kept {len(kept)} of {len(items)} item(s)", ""]
    logfile.write_text("\n".join(header + log) + "\n", encoding="utf-8", newline="\n")

    print()
    print(f"  fixes: {len(items) - len(kept)} item(s) dropped, {len(kept)} kept")
    print(f"  wrote: {out}")
    print(f"  wrote: {logfile}   (one line per dropped item, with the check that condemned it)")
    left = unrepairable_findings(report)
    if left:
        print("  NOT repaired, because a mechanical fix would be a guess:")
        for line in left:
            print(f"    - {line}")
        print("  The repaired file is not a clean file. Re-stomp it.")


def cmd_suggest_witnesses(args) -> int:
    """Propose witness cases. Writes nothing: a human accepts, edits, or rejects.

    Generating witnesses and keeping whatever kills the mutants would fit the
    witnesses TO the mutants, and W1 would stop being an independent measure of
    witness adequacy. So the proposals come from the data and from named bug
    classes, and the gauntlet is reported twice: once for the suite as it stands
    and once for the witnesses a human actually wrote.
    """
    spec, issues = load_spec(args.spec)
    if spec is None or issues:
        print("CANNOT SUGGEST:")
        _print_issues(issues)
        return CANNOT_RUN
    base = Path(args.spec).resolve().parent
    items, data_issues = load_items(spec["data"], base)
    if data_issues:
        print("CANNOT SUGGEST:")
        _print_issues(data_issues)
        return CANNOT_RUN

    kind = spec["scorer"]["kind"]
    authored = list(spec["scorer"].get("witnesses") or [])
    candidates = propose(items, kind)
    existing = {(w["output"], str(w["target"])) for w in authored}
    fresh = [c for c in candidates if (c["output"], str(c["target"])) not in existing]

    print(f"{spec['name']}: {len(authored)} authored witness(es), "
          f"{len(fresh)} suggestion(s) not already covered")
    print()
    if fresh:
        print("  Paste under scorer.witnesses, then EDIT. Each one encodes a decision about")
        print("  your scorer that only you can make:")
        print()
        for c in fresh:
            target = json.dumps(c["target"])
            print(f'    - {{output: {json.dumps(c["output"])}, target: {target}, '
                  f'expect: {c["expect"]}, why: "{c["why"]}"}}')
        print()

    if kind in ("python", "judge"):
        print("  Gauntlet coverage not computed: this pod scores with code or a hosted judge, "
              "which linting refuses to run without --trust-code.")
    else:
        scorer = make_scorer(spec["scorer"], base)
        both = run_gauntlet(scorer, authored + fresh, items)
        alone = run_gauntlet(scorer, authored, items) if authored else None
        print(f"  mutants killed by your authored witnesses:  "
              f"{len(alone.killed) if alone else 0} of "
              f"{alone.n_applicable if alone else (both.n_applicable if both else 0)}")
        print(f"  mutants killed once suggestions are added:  "
              f"{len(both.killed)} of {both.n_applicable}")
        if alone is not None and len(both.killed) > len(alone.killed):
            print()
            print("  Read that gap as a to-do, not a score. A suite that only holds up with")
            print("  generated cases in it is a suite nobody thought about, and W1 cannot tell")
            print("  the difference. Edit the suggestions until they say what YOU mean.")
    print()
    print("  Nothing was written. This command does not edit your spec.")
    return 0


def cmd_evidence(args) -> int:
    """What evidence is on disk, and which checks it unlocks.

    The contract made visible. A check that cannot run should never be a
    mystery, and this is the place to look before wondering why coverage is
    thin.
    """
    spec, issues = load_spec(args.spec)
    if spec is None or issues:
        print("CANNOT READ:")
        _print_issues(issues)
        return CANNOT_RUN
    base = Path(args.spec).resolve().parent
    discovered, _ = _discover_runs(base, spec["name"])
    ev = survey(discovered)

    print(f"{spec['name']}: {ev.n_records} record(s) across {ev.n_manifests} run(s)")
    if not discovered:
        print("  No evidence on disk. `dinostomp run <spec>` produces it, or "
              "`dinostomp import` brings another harness's logs into this contract.")
    print()
    print("  The battery consumes the record and manifest SCHEMAS, not this runner. Any")
    print("  producer of conforming evidence is auditable; these are the fields each")
    print("  check reads beyond the schema-required core.")
    print()
    ready, blocked = [], []
    for cid, needs in sorted(NEEDS.items()):
        gaps = missing_for(cid, ev)
        (blocked if gaps else ready).append((cid, needs, gaps))
    for cid, needs, _ in ready:
        print(f"  [have] {SLUGS[cid]:<22} {', '.join(n.field for n in needs)}")
    for cid, needs, gaps in blocked:
        missing = ", ".join(n.field for n in gaps)
        print(f"  [MISS] {SLUGS[cid]:<22} needs {missing}")
        for n in gaps:
            print(f"           {n.field}: {n.why}")
    print()
    print(f"  {len(ready)} of {len(NEEDS)} evidence-gated check(s) have what they need.")
    print("  Checks not listed here need only the schema-required fields; whether they")
    print("  apply is decided by the eval's shape, not by its evidence.")
    return 0


def _match_adapter(source: Path):
    """Which adapter recognises this log, if any. Never raises on a foreign file."""
    from dinostomp.adapters import ADAPTERS

    for name, module in ADAPTERS.items():
        try:
            if module.detect(source):
                return name, module
        except Exception:  # noqa: BLE001 - a sniff must never crash an import
            continue
    return None


def _import_via_adapter(adapter, source: Path, args, model: str):
    """Run a named adapter. Returns (records, issues, model, trajectory_source)."""
    name, module = adapter
    header, samples = module.read(source)
    for note in module.summarise(header, samples):
        print(f"  {note}")

    scorers = module.scorer_names(header, samples)
    if not scorers:
        return [], [Issue(loc="--score-field", check="import",
                          message=f"this {name} log carries no scores; there is nothing to "
                                  "import as a verdict")], model, None
    chosen = args.score_field or (scorers[0] if len(scorers) == 1 else None)
    if chosen is None:
        return [], [Issue(
            loc="--score-field", check="import",
            message=f"this log carries {len(scorers)} scorers ({', '.join(scorers)}) and they "
                    "may disagree. This tool will not choose which number you meant: pass "
                    f"--score-field {scorers[0]}")], model, None
    if chosen not in scorers:
        return [], [Issue(loc="--score-field", check="import",
                          message=f"no scorer named {chosen!r} in this log; it has "
                                  f"{', '.join(scorers)}")], model, None
    print(f"  score    <- {chosen}" + ("   (you said so)" if args.score_field else ""))

    # The log names the model that produced it. Preferred over the spec's first
    # entry, because a record labelled with the wrong model is a lie about whose
    # answer it is; `--model` still overrides for the case where a pod renames.
    reported = (header.get("eval") or {}).get("model")
    if reported and not args.model:
        model = str(reported)
    records, issues = module.to_records(header, samples, scorer=chosen, model=model,
                                        seed=int(args.seed))
    traj = "foreign_observed" if any(r.get("trajectory") for r in records) else None
    return records, issues, model, traj


def cmd_import(args) -> int:
    """Bring another harness's log into this pod as conforming evidence.

    The reference implementation of the evidence contract, and deliberately
    unprivileged: imported records are schema-validated at the boundary, the
    manifest says `imported` and names its source, and it claims no
    `tool_sha256`, because this engine did not produce these numbers.
    """
    spec, issues = load_spec(args.spec)
    if spec is None or issues:
        print("CANNOT IMPORT:")
        _print_issues(issues)
        return CANNOT_RUN
    base = Path(args.spec).resolve().parent
    source = Path(args.log)
    model = args.model or (spec["models"][0]["model"] if spec.get("models") else "imported")
    trajectory_source = None

    # An ADAPTER first. A nested harness log is not a table, and a column mapper
    # cannot read one at all; sniffing keeps that from being a confusing failure
    # about missing columns.
    adapter = _match_adapter(source)
    if adapter is not None:
        records, rec_issues, model, trajectory_source = _import_via_adapter(
            adapter, source, args, model)
        if rec_issues:
            print(f"CANNOT IMPORT: {len(rec_issues)} problem(s). Nothing was written.")
            _print_issues(rec_issues[:5])
            return CANNOT_RUN
    else:
        rows, read_issues = read_log(source)
        if read_issues:
            print("CANNOT IMPORT:")
            _print_issues(read_issues)
            return CANNOT_RUN

        overrides = {"item_id": args.item_id_field, "output": args.output_field,
                     "score": args.score_field, "model": args.model_field}
        mapping, notes, map_issues = infer_record_mapping(rows, overrides)
        for note in notes:
            print(f"  {note}")
        if map_issues:
            print("CANNOT IMPORT:")
            _print_issues(map_issues)
            return CANNOT_RUN

        records, rec_issues = to_records(rows, mapping, model=model, seed=int(args.seed))
    if rec_issues:
        print(f"CANNOT IMPORT: {len(rec_issues)} row(s) could not become records. "
              "A half-imported run is a lie about coverage, so nothing was written.")
        _print_issues(rec_issues[:5])
        return CANNOT_RUN

    # Pass this pod's witness gate before writing anything. The scorer that
    # will re-derive these verdicts is the one being validated, so the gate is
    # meaningful here, and a run that cannot pass it must not land on disk.
    try:
        scorer = make_scorer(spec["scorer"], base)
    except (ValueError, ProviderError) as exc:
        print(f"CANNOT IMPORT: this pod's scorer will not build: {exc}")
        return CANNOT_RUN
    wr = run_witnesses(scorer, spec["scorer"]["witnesses"])
    if wr.verdict != "validated":
        print("CANNOT IMPORT: this pod's witness gate does not pass, so its scorer may not")
        print("  re-derive anything. Fix the scorer before importing evidence for it.")
        return GATED

    hashes = _expected_hashes(Path(args.spec).resolve(), spec)
    stem = f"imported_{spec['name']}_{model.replace('/', '-')}_n{len(records)}_s{args.seed}"
    manifest = build_manifest(spec, hashes, model=model, seed=int(args.seed), source=source,
                              n_records=len(records), run_file=f"{stem}.jsonl",
                              witness_report=wr.to_manifest())
    if trajectory_source:
        # FOREIGN_OBSERVED, never harness_observed. Another harness watched
        # those tool calls; this one did not. Better evidence than an agent's
        # self-report, because the exporting harness is a third party to the
        # agent, and still someone else's word. T8 prints the difference.
        manifest["trajectory_source"] = trajectory_source
    repeats = 1 + max((int(r.get("repeat") or 0) for r in records), default=0)
    if repeats > 1:
        manifest["repeats"] = repeats
    rf, mf, sf = write_run(base, records, manifest, stem)
    print()
    print(f"  imported {len(records)} record(s) from {source.name}")
    print(f"  wrote: {rf}")
    print(f"  wrote: {mf}")
    print(f"  wrote: {sf}")
    print()
    print("  This evidence is UNPRIVILEGED. It is schema-validated like any other, the")
    print("  manifest says `imported` and names its source, and it claims no tool_sha256,")
    print("  because this engine did not produce it: engine-drift reports that rather than")
    print("  pretending otherwise. Checks whose fields your log lacks will SKIP, naming the")
    print("  field. Nothing was invented to fill a gap.")
    print()
    print(f"  next: dinostomp evidence {args.spec}")
    return 0


def cmd_stomp(args) -> int:
    # A bare data file is a DATASET audit, not a pod audit. Routed on the
    # extension only: sniffing content would let a malformed spec quietly become
    # a cheerful verdict about the wrong thing.
    if looks_like_dataset(args.spec):
        return _stomp_dataset(args)
    references = {}
    for ref in (getattr(args, "against", None) or []):
        ref_items, errs = load_reference(ref)
        for err in errs:
            print(f"  [reference] skipped: {err}")
        if ref_items:
            references[Path(ref).name] = ref_items
    report, issues = lint_eval(args.spec, trust_code=args.trust_code,
                               references=references,
                               use_extensions=not args.no_extensions)
    if report is None:
        print("CANNOT STOMP:")
        _print_issues(issues)
        return CANNOT_RUN
    for f in report["findings"]:
        print(f"  {LEVEL_TAGS[f['level']]} {f['slug']:<22} {f['check']:<56} {f['detail']}")
        for ex in f.get("examples", []):
            print(f"           - {ex}")
    cov = report["coverage"]
    verdict = report["summary"]["verdict"]
    invariants = [f for f in report["findings"] if f["gating"]]
    diagnostics = [f for f in report["findings"] if not f["gating"]]
    print(f"  invariants (deterministic, gating): "
          f"{sum(1 for f in invariants if f['level'] == 'pass')} ok, "
          f"{sum(1 for f in invariants if f['level'] == 'fail')} FAIL | "
          f"diagnostics (statistical, advisory): "
          f"{sum(1 for f in diagnostics if f['level'] == 'pass')} ok, "
          f"{sum(1 for f in diagnostics if f['level'] == 'warn')} warn")
    # Coverage is stated in full: n/a checks leave the denominator, but their
    # count is always visible so shrinking the dataset never buys a cleaner line.
    suffix = f"({cov['ran']} of {cov['declared']} ran; {len(cov['not_applicable'])} n/a of {cov['declared_total']} declared)"
    if verdict == "sound":
        # Not "CLEAN", and not a bare "SOUND" either. This line gets screenshotted
        # and pasted into a README, where "sound" quietly becomes "this benchmark
        # is good". Interface semantics beat documentation, so the qualifier
        # rides ON the verdict rather than sitting in a paragraph below it.
        print(f"MECHANICALLY SOUND: no integrity findings, full coverage {suffix}")
    elif verdict == "ok":
        print(f"OK: no failures, {report['summary']['warn']} warning(s) {suffix}")
    elif verdict == "incomplete":
        print(f"INCOMPLETE: no failures, but only {cov['ran']} of {cov['declared']} checks ran "
              f"({len(cov['not_applicable'])} n/a of {cov['declared_total']} declared). Not a clean bill of health.")
    else:
        print(f"BROKEN: {report['summary']['fail']} gated finding(s) {suffix}")

    for f in report.get("extension_findings") or []:
        tag = "" if f["validated"] else "  [UNVALIDATED EXTENSION]"
        print(f"  {LEVEL_TAGS[f['level']]} {f['check_id']:<22} {f['detail']}{tag}")
        for ex in f.get("examples", [])[:4]:
            print(f"           - {ex}")
    for ext in report.get("extensions") or []:
        state = "validated" if ext["validated"] else "UNVALIDATED, excluded from coverage"
        print(f"  extension: {ext['name']} {ext['version']} "
              f"({ext['sha256'][:16]}), {len(ext['checks'])} check(s), {state}")
        if not ext["validated"]:
            print(f"      {ext['unvalidated_reason']}")
    for problem in report.get("extension_problems") or []:
        print(f"  extension problem: {problem}")

    cv = report.get("construct_validity") or {}
    if cv:
        print(f"  measures the intended construct: {cv['measures_the_intended_construct']}. "
              "Mechanical integrity is not construct validity; a trivial eval can pass "
              "every check here.")

    runs = report.get("runs") or []
    if runs and all(r["dry_run"] for r in runs):
        print("  note: all runs used the offline dry provider; results exercise the benchmark, not any real model.")
    if verdict in ("sound", "ok") and report.get("entitled_claims"):
        print("  this result is entitled to claim:")
        for claim in report["entitled_claims"]:
            print(f"    - {claim}")
    for c in report.get("claims") or []:
        tag = "SUPPORTED" if c["supported"] else "NOT SUPPORTED"
        print(f"  typed claim [{tag}]: {c['description']}")

    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2), encoding="utf-8", newline="\n")
        print(f"  report: {args.json}")
    if verdict == "incomplete" and args.allow_incomplete:
        print("  --allow-incomplete: exiting 0 despite thin coverage, on your explicit say-so.")
    return _verdict_exit(verdict, args.allow_incomplete)


def cmd_report(args) -> int:
    report, issues, written = write_report(args.spec, trust_code=args.trust_code,
                                           use_extensions=not args.no_extensions)
    if report is None:
        print("CANNOT REPORT:")
        _print_issues(issues)
        return CANNOT_RUN
    verdict = report["summary"]["verdict"]
    cov = report["coverage"]
    print(f"verdict: {verdict} ({cov['ran']} of {cov['declared']} ran; "
          f"{len(cov['not_applicable'])} n/a of {cov['declared_total']} declared)")
    for p in written:
        print(f"  wrote: {p}")
    if verdict == "incomplete" and args.allow_incomplete:
        print("  --allow-incomplete: exiting 0 despite thin coverage, on your explicit say-so.")
    return _verdict_exit(verdict, args.allow_incomplete)


def cmd_verify(args) -> int:
    status, details, report = verify_report(args.spec, trust_code=args.trust_code)
    if status == "verified":
        verdict = report["summary"]["verdict"]
        print("VERIFIED: the published report re-derives from this pod, offline, byte-for-byte.")
        print(f"  published verdict: {verdict} (re-derived, not trusted)")
        for d in details:
            print(f"  - {d}")
        return 0
    if status == "mismatch":
        print("MISMATCH: the published report is NOT what this pod re-derives.")
        for d in details:
            print(f"  - {d}")
        print("  Either the pod changed after publishing (stale) or the report was edited (worse).")
        print("  Regenerate with: dinostomp report <spec>")
        return 1
    print("UNVERIFIABLE:")
    for d in details:
        print(f"  - {d}")
    return CANNOT_RUN


def cmd_plan(args) -> int:
    """Everything knowable BEFORE spending a cent, from the spec alone."""
    spec, issues = load_spec(args.spec)
    if spec is None or issues:
        print("CANNOT PLAN:")
        _print_issues(issues)
        return CANNOT_RUN
    base = Path(args.spec).resolve().parent
    items, data_issues = load_items(spec["data"], base)
    if data_issues:
        print("CANNOT PLAN:")
        _print_issues(data_issues)
        return CANNOT_RUN

    run_cfg = spec["run"]
    n = min(int(run_cfg["n"]), len(items))
    repeats = int(run_cfg.get("repeats", 1))
    # `run.seeds` repeats the WHOLE eval once per extra seed, and every one of
    # those calls is billed. Forecasting one seed's worth here understated a
    # real 3-seed pod by 3x. The cap still held (it is checked against actual
    # spend before every call), but `plan` exists precisely so nobody has to
    # find that out from the bill.
    passes = repeats * (1 + len(run_cfg.get("seeds") or []))
    selected = select_items(items, n, int(run_cfg["seed"]))
    print(f"PLAN for {spec['name']} v{spec['version']}")
    extra = run_cfg.get("seeds") or []
    seed_note = f", +{len(extra)} extra seed(s)" if extra else ""
    print(f"  items: {n} of {len(items)} shipped (seed {run_cfg['seed']}, repeats {repeats}{seed_note})")

    mde = min_detectable_effect(n)
    print(f"  power: at n={n}, an unpaired comparison resolves gaps down to ~{mde:.0%} (80% power); "
          "the paired bootstrap behind P6/C1 does better when errors overlap")
    claims = [c.lower() for c in (spec.get("entitled_claims") or [])]
    if any(w in c for c in claims for w in ORDERING_WORDS):
        print("  ordering claim entitled: items needed for the gap you expect to certify (unpaired):")
        for gap in (0.05, 0.10, 0.20):
            n_needed = n_for_effect(gap)
            marker = " <- you have enough (unpaired)" if n >= n_needed else ""
            print(f"    gap {gap:.0%}: n = {n_needed}{marker}")
    for claim in spec.get("claims") or []:
        if claim.get("type") == "superiority":
            min_effect = float(claim.get("min_effect", 0.0))
            provable = mde is not None and min_effect >= mde
            note = ("above the unpaired MDE at this n" if provable else
                    f"below the unpaired MDE (~{mde:.0%}) at n={n}; the paired bootstrap may still support it "
                    f"if errors overlap, else need up to n ~ {n_for_effect(min_effect)}")
            print(f"  typed claim: {describe_claim(claim)}: {note}")
        else:
            print(f"  typed claim: {describe_claim(claim)}")

    scorer = make_scorer(spec["scorer"], base)
    if not getattr(scorer, "offline_replayable", True):
        # Running the gauntlet would call a hosted judge once per mutant per
        # witness. `plan` exists to be the thing you run BEFORE spending, so it
        # refuses to spend to tell you about spending.
        print("  witnesses: not previewed; this pod grades with a hosted judge, and the mutation "
              "gauntlet would have to pay it. Use `dinostomp run <spec> --probe judge`.")
        gauntlet = None
    else:
        gauntlet = run_gauntlet(scorer, spec["scorer"]["witnesses"], items)
    if gauntlet is None:
        pass
    elif gauntlet.survived:
        print(f"  witnesses: {len(gauntlet.survived)} mutant scorer(s) would survive; the stomp will warn:")
        for m in gauntlet.survived:
            print(f"    - {m.name} ({m.bug_class}); add {m.suggestion}")
    else:
        print(f"  witnesses: all {gauntlet.n_applicable} applicable mutant scorers die. Gate is tight.")

    total_worst = 0.0
    unpriced = []
    self_funded = []
    for mc in spec["models"]:
        rate_in, rate_out, label = resolve_rates(mc["provider"], mc["model"], args.price_in,
                                                 args.price_out, mc.get("price_in"), mc.get("price_out"))
        if rate_in is None:
            unpriced.append(mc["model"])
            continue
        if mc["provider"] == "python":
            # A target that calls a paid model inside itself reports its own
            # spend, which this forecast cannot see. Saying "$0.0000" for it
            # would be the one thing `plan` must never do: understate a bill.
            self_funded.append(mc["model"])
            continue
        max_tokens = int((mc.get("params") or {}).get("max_tokens", DEFAULT_MAX_TOKENS))
        prompt_chars = sum(len(str(i["input"])) for i in selected)
        worst = passes * (prompt_chars / CHARS_PER_TOKEN_EST * rate_in + n * max_tokens * rate_out) / 1_000_000
        total_worst += worst
        print(f"  cost, worst case: {mc['model']} ({label}) ${worst:.4f}")
    if self_funded:
        print(f"  cost: {len(self_funded)} python target(s) ({', '.join(self_funded)}) price their own "
              "calls; that spend is NOT forecastable here and is reported by the target at run time. "
              "The cap still stops the run when their reported spend reaches it.")
    if unpriced:
        print(f"  cost: {len(unpriced)} model(s) unpriced ({', '.join(unpriced)}); pass --price-in/--price-out")
    if spec["scorer"]["kind"] == "judge":
        jm = (spec["scorer"].get("judge") or {}).get("model", "the judge")
        print(f"  cost: a judge grades every record; {jm}'s calls are charged against this same cap "
              "and are not included in the figure above")
    cap = float(run_cfg["budget_usd"])
    known = "worst case" if not (self_funded or spec["scorer"]["kind"] == "judge") else "forecastable worst case"
    print(f"  budget: {known} ${total_worst:.4f} vs cap ${cap:.2f}"
          + ("; the run would STOP EARLY, so raise the cap or cut n" if total_worst > cap else "; fits"))
    return 0


def main(argv=None) -> int:
    # Item text is utf-8; a cp1252 console must not crash the report print.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="dinostomp", description="Build evals fast. Everything gets stomped.")
    parser.add_argument("--version", action="version", version=f"dinostomp {dinostomp.__version__} (engine {engine_fingerprint()[:16]})")
    sub = parser.add_subparsers(dest="command", required=True)

    p_new = sub.add_parser("new", help="scaffold a fresh eval pod")
    p_new.add_argument("directory")
    p_new.set_defaults(func=cmd_new)

    p_val = sub.add_parser("validate", help="validate a spec, print issues")
    p_val.add_argument("spec")
    p_val.add_argument("--json", action="store_true", help="print issues as JSON")
    p_val.set_defaults(func=cmd_validate)

    p_run = sub.add_parser("run", help="run a spec")
    p_run.add_argument("spec")
    p_run.add_argument("--resume", help="existing run file to continue")
    p_run.add_argument("--limit", type=int, help="cap the number of items")
    p_run.add_argument("--dry-run", action="store_true", help="force the offline dry provider")
    p_run.add_argument("--price-in", type=float, help="input rate, USD per MTok, for unpriced models")
    p_run.add_argument("--price-out", type=float, help="output rate, USD per MTok, for unpriced models")
    p_run.add_argument("--framings", help="template probe: comma-separated framing names "
                                          "(default: all six)")
    p_run.add_argument("--probe", choices=["blind", "judge", "canary", "shuffle", "crossjudge",
                                           "template", "ablate"],
                       help="probe mode: 'blind' strips every input before the call and feeds R13; "
                            "'judge' grades constructed cases whose right verdict is known, then "
                            "regrades them under content-free perturbations, and feeds J1/J2. "
                            "Either way the run is tagged in its manifest and never pools with "
                            "the real results. 'canary' asks each hosted model to continue "
                            "this pod's canary, alongside a passage it certainly memorised, and "
                            "feeds S10. 'shuffle' re-asks every choice item with its options "
                            "permuted, and feeds P9. 'ablate' re-runs a MEDIATED agent "
                            "with every tool result withheld: an answer that does not change "
                            "when its evidence is taken away did not causally depend on it, "
                            "which is what T7 reads and what T4 could only ever guess at")
    p_run.set_defaults(func=cmd_run)

    p_inspect = sub.add_parser("inspect", help="what a pod's Python touches, without running it")
    p_inspect.add_argument("spec")
    p_inspect.set_defaults(func=cmd_inspect)

    p_fp = sub.add_parser("fingerprint", help="SHA-256 of this engine's own code and schemas")
    p_fp.add_argument("-v", "--verbose", action="store_true", help="also print what it covers")
    p_fp.set_defaults(func=cmd_fingerprint)

    p_sw = sub.add_parser("suggest-witnesses",
                          help="propose witness cases for a pod's scorer; writes nothing")
    p_sw.add_argument("spec")
    p_sw.set_defaults(func=cmd_suggest_witnesses)

    p_ev = sub.add_parser("evidence", help="what evidence is on disk and which checks it unlocks")
    p_ev.add_argument("spec")
    p_ev.set_defaults(func=cmd_evidence)

    p_imp = sub.add_parser("import", help="bring another harness's log in as conforming evidence")
    p_imp.add_argument("spec")
    p_imp.add_argument("log", help="a .jsonl/.csv/.json log from another harness")
    p_imp.add_argument("--model", help="model name to record (default: the spec's first)")
    p_imp.add_argument("--seed", default=0, help="seed to record (imports rarely state one)")
    p_imp.add_argument("--item-id-field")
    p_imp.add_argument("--output-field")
    p_imp.add_argument("--score-field")
    p_imp.add_argument("--model-field")
    p_imp.set_defaults(func=cmd_import)

    p_stomp = sub.add_parser("stomp", help="lint a spec and its runs, or a bare dataset file")
    p_stomp.add_argument("spec", help="an eval.yaml, or a .csv/.jsonl/.json dataset to audit directly")
    p_stomp.add_argument("--input-field", help="dataset audit: which column holds the question")
    p_stomp.add_argument("--target-field", help="dataset audit: which column holds the answer")
    p_stomp.add_argument("--choices-field", help="dataset audit: which column holds the options")
    p_stomp.add_argument("--id-field", help="dataset audit: which column holds the item id")
    p_stomp.add_argument("--separator", help="dataset audit: splits multi-value cells, e.g. '|'")
    p_stomp.add_argument("--against", action="append", metavar="PATH",
                         help="dataset audit: a reference dataset to check for overlap against. "
                              "Repeatable. This compares corpora you HAVE; it never checks "
                              "training data and cannot.")
    p_stomp.add_argument("--emit-fixes", nargs="?", const=True, metavar="PATH",
                         help="dataset audit: write the mechanically repaired dataset (and a "
                              "per-item log of what was dropped and why) next to the original")
    p_stomp.add_argument("--trust-code", action="store_true",
                          help="permit importing this pod's scorer/judge Python. Linting a pod you did not write RUNS that code; off by default")
    p_stomp.add_argument("--json", help="also write the machine-readable report here")
    p_stomp.add_argument("--allow-incomplete", action="store_true",
                         help="exit 0 on incomplete coverage (strict is the default)")
    p_stomp.add_argument("--no-extensions", action="store_true",
                         help="core checks only. Publishes a report that re-derives on any machine with this engine, rather than one that re-derives only where your plugins are installed.")
    p_stomp.set_defaults(func=cmd_stomp)

    p_report = sub.add_parser("report", help="stomp and write STOMP.md + STOMP.json + badge into the pod")
    p_report.add_argument("spec")
    p_report.add_argument("--trust-code", action="store_true",
                          help="permit importing this pod's scorer/judge Python. Linting a pod you "
                               "did not write RUNS that code; off by default")
    p_report.add_argument("--allow-incomplete", action="store_true",
                          help="exit 0 on incomplete coverage (strict is the default)")
    p_report.add_argument("--no-extensions", action="store_true",
                         help="core checks only. Publishes a report that re-derives on any machine with this engine, rather than one that re-derives only where your plugins are installed.")
    p_report.set_defaults(func=cmd_report)

    p_verify = sub.add_parser("verify", help="re-derive a pod's published report offline; verified/mismatch/unverifiable")
    p_verify.add_argument("spec")
    p_verify.add_argument("--trust-code", action="store_true",
                          help="permit importing this pod's scorer/judge Python. Verifying a pod you did not write RUNS that code; off by default")
    p_verify.add_argument("--no-extensions", action="store_true",
                         help="core checks only. Publishes a report that re-derives on any machine with this engine, rather than one that re-derives only where your plugins are installed.")
    p_verify.set_defaults(func=cmd_verify)

    p_plan = sub.add_parser("plan", help="power, cost, and witness preview before any money is spent")
    p_plan.add_argument("spec")
    p_plan.add_argument("--price-in", type=float, help="input rate, USD per MTok, for unpriced models")
    p_plan.add_argument("--price-out", type=float, help="output rate, USD per MTok, for unpriced models")
    p_plan.set_defaults(func=cmd_plan)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
