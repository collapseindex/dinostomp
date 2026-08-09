"""The run orchestrator: spec in, ledgered results out.

Order of operations is the discipline:

  1. validate the spec (refuse on any issue)
  2. load and validate the data (refuse on any issue)
  3. run the scorer's witnesses (refuse if any misbehave; nothing is written)
  4. only then touch a model, streaming every record to disk under a budget

A run that stops early (budget, provider, or scorer failure) is a clean partial: its
records are on disk, its manifest says why it stopped, and resuming it never
re-pays for finished items.
"""

from __future__ import annotations

import json
import platform
import random
import sys
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path

import dinostomp
from dinostomp.fingerprint import engine_fingerprint
from dinostomp.items import load_items
from dinostomp.providers import ZERO_RATE_PROVIDERS, ProviderError, make_provider
from dinostomp.psychometrics import majority, wilson_ci
from dinostomp.runlog import Budget, BudgetExceeded, Cost, RunLog, price_call, rates_for, utc_now
from dinostomp.scorers import make_scorer, run_witnesses
from dinostomp.spec import Issue, jsonl_lines, load_spec, spec_sha256
from dinostomp.templates import DEFAULT_FRAMINGS, FRAMINGS_BY_NAME, framed_input


# Exit codes, also used by the CLI:
OK = 0            # ran to completion
GATED = 1         # witnesses failed: the scorer may not touch real data
CANNOT_RUN = 2    # invalid spec/data, missing key, bad arguments
STOPPED_EARLY = 3 # budget, provider, or scorer stopped a run partway; partial on disk, resumable

CHARS_PER_TOKEN_EST = 4  # worst-case estimator only; real usage reprices every call
SPEND_EPS = 1e-9         # rounding slack when comparing accumulated spend to the cap


def mount_hashes(spec: dict, base: Path) -> dict:
    """{declared path: sha256} for files the pod depends on from outside itself."""
    out = {}
    for raw in spec.get("mounts") or []:
        path = base / str(raw)
        if path.is_file():
            out[str(raw)] = spec_sha256(path)
    return out


def judge_entrypoint(spec: dict) -> str | None:
    """The pod-local file a python judge loads, without its symbol suffix."""
    scorer = spec.get("scorer") or {}
    if scorer.get("kind") != "judge":
        return None
    judge = scorer.get("judge") or {}
    if judge.get("provider") != "python":
        return None
    entry = judge.get("entrypoint") or ""
    return entry.rpartition(":")[0] if ":" in entry else entry or None


def target_entrypoint(model_cfg: dict) -> str | None:
    """The pod-local file a target loads, without its symbol suffix.

    Both code rails, because both are pod-local code inside the drift boundary:
    editing a mediated agent after a run is exactly as much drift as editing a
    self-reporting one.
    """
    if model_cfg.get("provider") not in ("python", "mediated"):
        return None
    entry = model_cfg.get("entrypoint") or ""
    return entry.rpartition(":")[0] if ":" in entry else entry or None


def tool_hashes(spec: dict, base: Path) -> dict:
    """{tool name: sha256} for every pod-local tool the harness offers.

    Hashed for the same reason the agent is: a tool is code that produces the
    evidence an answer is judged against, so swapping one between runs changes
    the experiment and the manifest has to say so.
    """
    out = {}
    for name, entry in (spec.get("tools") or {}).items():
        rel = str(entry).rpartition(":")[0] if ":" in str(entry) else str(entry)
        path = base / rel
        if path.is_file():
            out[str(name)] = spec_sha256(path)
    return out


def _env_envelope() -> dict:
    """Environment fingerprint for the manifest. Reproducibility tiers, stated
    honestly: local inputs are hash-pinned; requests are reproducible given
    this envelope; hosted-model immutability is UNKNOWN unless the provider
    exposes a pinned revision."""
    versions = {}
    for pkg in ("dinostomp", "jsonschema", "PyYAML"):
        try:
            versions[pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            versions[pkg] = "unknown"
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "packages": versions,
    }


@dataclass
class RunOutcome:
    exit_code: int
    issues: list[Issue] = field(default_factory=list)
    witness_failures: list[dict] = field(default_factory=list)
    run_files: list[Path] = field(default_factory=list)
    summaries: list[dict] = field(default_factory=list)
    stopped_reason: str = ""


def summarize(records: list[dict]) -> dict:
    """Aggregate one run file. Uncheckable is excluded from the accuracy
    denominator and reported on its own line; that exclusion is the point.

    Estimator discipline: with repeats > 1, accuracy and its Wilson interval
    are computed over ITEM-MAJORITY outcomes (strict majority per item, from
    the same `majority()` the fleet-matrix cells use) rather than pooled
    records. Pooling correlated repeats narrows the interval optimistically and
    brackets a different estimator than the matrix reasons about; the summary
    names which estimator it used.

    An item whose repeats split evenly is UNDECIDED, not failed, and lands in
    `n_repeat_ties` and `n_uncheckable` rather than in the denominator. Scoring
    ties 0 was the original rule and it silently changed the estimand: at
    repeats=2 a model with true per-item rate p reported p squared, so a 50%
    model published 24% behind an interval that excluded the truth (N-008).
    """
    by_verdict = {"pass": 0, "fail": 0, "flag": 0, "uncheckable": 0}
    by_item: dict[str, list[int]] = {}
    spend = 0.0
    for r in records:
        v = (r.get("score") or {}).get("verdict")
        if v in by_verdict:
            by_verdict[v] += 1
        votes = by_item.setdefault(str(r.get("item_id")), [])
        if v in ("pass", "fail", "flag"):
            votes.append(1 if v == "pass" else 0)
        spend += float((r.get("usage") or {}).get("cost_usd") or 0.0)

    repeated = any(len(v) > 1 for v in by_item.values())
    ties = 0
    if repeated:
        estimator = "item_majority"
        decided = []
        for v in by_item.values():
            if not v:
                continue
            out = majority(v)
            if out is None:
                # An item the model could not decide about itself. Counted as
                # uncheckable and excluded from the accuracy denominator, which
                # is what every other undecided verdict here gets. Scoring it 0
                # instead would report p-squared at repeats=2 (N-008); R20
                # warns whenever this count is non-zero.
                ties += 1
            else:
                decided.append(out)
        checkable = len(decided)
        passes = sum(decided)
        judge_denominator = len(by_item)
        # In ITEMS, like the numerator. Every count this estimator reports has to
        # share a unit or the report mixes items and records in one line: an item
        # is undecided if its repeats tied, or if nothing it returned was
        # scoreable at all.
        uncheckable = judge_denominator - checkable
    else:
        estimator = "per_record"
        checkable = by_verdict["pass"] + by_verdict["fail"] + by_verdict["flag"]
        passes = by_verdict["pass"]
        judge_denominator = len(records)
        uncheckable = by_verdict["uncheckable"]

    ci = wilson_ci(passes, checkable)
    return {
        "n_records": len(records),
        "estimator": estimator,
        "n_checkable": checkable,
        "n_uncheckable": uncheckable,
        # Items whose repeats split evenly, so the majority vote reached no
        # verdict. Reported separately from a scorer's own `uncheckable`
        # because the cause and the remedy are different: this one is an odd
        # `run.repeats` away from being decidable.
        "n_repeat_ties": ties,
        # Conditional accuracy and judgeability travel together: 80% accurate
        # on 90%-judgeable output must never masquerade as plain 80%.
        "n_passes": passes,
        "accuracy_on_checkable": round(passes / checkable, 6) if checkable else None,
        "accuracy_ci95": [round(ci[0], 4), round(ci[1], 4)] if ci else None,
        "judgeability": round(checkable / judge_denominator, 4) if judge_denominator else None,
        "by_verdict": by_verdict,
        "spend_usd": round(spend, 9),
    }


def blind_input(item: dict) -> str:
    """The blind-probe transform: everything informative is deleted, the
    response format is preserved. A model that still scores above the
    informed-guesser floor is exploiting something other than the question."""
    if "choices" in item:
        options = "\n".join(f"- {c}" for c in item["choices"])
        return ("Pick one of the following options. There is no question. "
                f"Reply with exactly one option, nothing else:\n{options}")
    return ("There is no question. Reply with your single best guess at the "
            "expected answer, bare, nothing else.")


def render_options(item: dict, order: list) -> str:
    """The question with a lettered option block appended, in the given order.

    The model is asked for the option TEXT, not the letter, and that is not a
    style choice. Shuffling moves the gold answer to a different letter, so a
    letter-keyed target would have to be rewritten per rendering; the scorer
    would then grade against something the item does not contain, and R8 could
    no longer re-score a recorded output offline. Keying on the text keeps the
    target invariant under permutation, which is the only way the two arms of a
    presentation-order comparison stay comparable.

    The letters stay in the block because their POSITIONS are what the probe
    varies. Only the answer format is text.
    """
    block = "\n".join(f"{chr(65 + i)}. {c}" for i, c in enumerate(order))
    return (f"{item['input']}\n\n{block}\n\n"
            "Answer with exactly one of the options above, copied verbatim.")


def shuffled_input(item: dict, seed: int) -> str | None:
    """The presentation-order transform: same question, same options, different
    ORDER.

    Only possible when the pod lets dinostomp render the options (`choices` on
    the item plus `render_choices` on the data block), because otherwise the
    option order lives inside prose the tool does not own. That is precisely why
    this sat on the roadmap: you cannot permute what you do not render.

    Deterministic per (item, seed), so a shuffle probe re-runs identically.
    """
    choices = item.get("choices")
    if not isinstance(choices, list) or len(choices) < 2:
        return None
    order = list(choices)
    random.Random(f"shuffle|{seed}|{item['id']}").shuffle(order)
    if order == list(choices):      # a permutation that changed nothing tests nothing
        order = order[1:] + order[:1]
    return render_options(item, order)


def select_items(items: list[dict], n: int, seed: int) -> list[dict]:
    """Deterministic selection: seeded shuffle, first n. Same seed, same items.

    Public because the stomp battery re-derives this selection to verify that
    a run's records cover exactly the items the seed chose.
    """
    if n >= len(items):
        return list(items)
    shuffled = list(items)
    random.Random(seed).shuffle(shuffled)
    return shuffled[:n]


def resolve_rates(provider: str, model: str, price_in, price_out,
                  spec_in=None, spec_out=None) -> tuple[float | None, float | None, str]:
    """(rate_in, rate_out, label). None rates mean the run must be refused.

    Precedence: rates declared in the SPEC beat command-line flags, which beat
    the built-in table. Spec-declared wins because it is the only one inside
    spec_sha256: a rate typed at a shell prompt vanishes the moment the command
    scrolls away, while a rate in the spec is hashed, published, and re-derived
    by anyone who verifies the pod.
    """
    if spec_in is not None and spec_out is not None:
        return float(spec_in), float(spec_out), "spec"
    if provider in ZERO_RATE_PROVIDERS:
        # A python target costs the ledger nothing to CALL. If it spends money
        # inside itself it must report that spend, which is priced separately
        # and labelled target-reported rather than metered.
        return 0.0, 0.0, ("dry" if provider == "dry" else "target")
    if price_in is not None and price_out is not None:
        return float(price_in), float(price_out), "explicit"
    rate_in, rate_out, label = rates_for(model)
    if label == "unpriced":
        return None, None, "unpriced"
    return rate_in, rate_out, label


def run_crossjudge_probe(
    spec_path: str | Path,
    *,
    out_dir: Path | None = None,
    provider_factory=make_provider,
) -> RunOutcome:
    """Re-grade the outputs already on disk with a SECOND judge.

    Nothing new is generated: the same recorded responses are graded again, so
    any formatting advantage a model has applies identically to both judges and
    cancels. What survives the subtraction is the interaction J4 reads.
    """
    spec_file = Path(spec_path).resolve()
    spec, issues = load_spec(spec_file)
    if spec is None or issues:
        return RunOutcome(CANNOT_RUN, issues=issues)
    scorer_cfg = spec["scorer"]
    cross = scorer_cfg.get("cross_judge")
    if scorer_cfg.get("kind") != "judge" or not cross:
        return RunOutcome(CANNOT_RUN, issues=[Issue(
            loc="$.scorer.cross_judge", check="probe",
            message="a cross-judge probe needs `scorer.kind: judge` and a `cross_judge` block "
                    "naming a second judge from a different family; one judge cannot tell you "
                    "whether it favours its own")])
    base = spec_file.parent

    from dinostomp.judging import JudgeScorer, judge_family
    if judge_family(cross) == judge_family(scorer_cfg["judge"]):
        return RunOutcome(CANNOT_RUN, issues=[Issue(
            loc="$.scorer.cross_judge", check="probe",
            message="the cross judge is from the SAME family as the primary judge, so their "
                    "difference cannot separate favouritism from shared taste")])

    rate_in, rate_out, rate_label = resolve_rates(
        cross["provider"], cross.get("model", ""), None, None,
        cross.get("price_in"), cross.get("price_out"))
    if rate_in is None:
        return RunOutcome(CANNOT_RUN, issues=[Issue(
            loc="$.scorer.cross_judge", check="budget",
            message=f"cross judge {cross.get('model')!r} has no known price")])

    judge = JudgeScorer({**scorer_cfg, "judge": cross}, base, provider_factory=provider_factory)
    run_cfg = spec["run"]
    seed = int(run_cfg["seed"])
    judge.seed = seed

    # Records store the OUTPUT, not the target, so the reference has to come
    # from the dataset. Grading against a missing target silently fails every
    # item, and the resulting deltas are just pass rates wearing a disguise.
    items, data_issues = load_items(spec["data"], base)
    if data_issues:
        return RunOutcome(CANNOT_RUN, issues=data_issues)
    target_of = {str(i["id"]): i["target"] for i in items}

    runs = sorted((base / "data" / "runs").glob("*.jsonl"))
    graded_any = False
    outcome = RunOutcome(OK)
    budget = Budget(cap_usd=float(run_cfg["budget_usd"]))
    model_name = cross.get("model") or cross.get("entrypoint", "cross-judge")

    log = RunLog(spec["name"], model_name, "crossjudgeprobe", seed,
                 data_dir=(out_dir or base) / "data", resume_path=None)
    manifest = {
        "tool_version": dinostomp.__version__, "tool_sha256": engine_fingerprint(),
        "spec_name": spec["name"], "spec_version": spec["version"],
        "spec_sha256": spec_sha256(spec_file),
        "data_sha256": spec_sha256(base / spec["data"]["path"]),
        "provider": cross["provider"], "model": model_name, "seed": seed,
        "dry_run": cross["provider"] in ("dry", "python"),
        "budget_cap_usd": float(run_cfg["budget_usd"]),
        "rate_in_per_mtok": rate_in, "rate_out_per_mtok": rate_out,
        "witness_report": {"n_witnesses": 0, "n_behaved": 0, "verdict": "absent"},
        "env": _env_envelope(), "probe": "crossjudge",
        "started_at": utc_now().isoformat(), "status": "running",
    }
    stopped = ""
    with log:
        log.write_manifest(manifest)
        for rf in runs:
            mf = rf.with_name(rf.stem + "_manifest.json")
            if not mf.is_file():
                continue
            try:
                m = json.loads(mf.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if m.get("probe") or m.get("spec_name") != spec["name"]:
                continue
            graded = str(m.get("model"))
            for line in jsonl_lines(rf.read_text(encoding="utf-8")):
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if "output" not in rec or str(rec.get("item_id")) not in target_of:
                    continue
                before = (judge.input_tokens, judge.output_tokens)
                try:
                    result = judge(rec["output"], target_of[str(rec["item_id"])])
                except ProviderError as exc:
                    stopped = f"provider: {exc}"
                    break
                usd = ((judge.input_tokens - before[0]) * rate_in
                       + (judge.output_tokens - before[1]) * rate_out) / 1_000_000
                budget.record(usd)
                graded_any = True
                log.append({
                    "key": f"{graded}#{rec.get('key', rec.get('item_id'))}",
                    "item_id": rec.get("item_id"), "model": model_name,
                    "provider": cross["provider"], "seed": seed,
                    "output": rec["output"], "finish_reason": "stop",
                    "score": result.to_dict(), "judge_response": judge.last_response,
                    "graded_model": graded,
                    "usage": {"input_tokens": judge.input_tokens - before[0],
                              "output_tokens": judge.output_tokens - before[1],
                              "cost_usd": round(usd, Cost.USD_DECIMALS), "rate_label": rate_label},
                    "ts": utc_now().isoformat(),
                })
                if budget.spent_usd > budget.cap_usd + SPEND_EPS:
                    stopped = "budget: the cross judge reached the cap"
                    break
            if stopped:
                break
        manifest["status"] = "stopped_early" if stopped else "complete"
        if stopped:
            manifest["stopped_reason"] = stopped
        manifest["spend_usd"] = round(budget.spent_usd, Cost.USD_DECIMALS)
        manifest["spend_source"] = "metered"
        manifest["judge_calls"] = int(judge.calls)
        manifest["finished_at"] = utc_now().isoformat()
        log.write_manifest(manifest)
        recs = log.records()
        summary = {"spec_name": spec["name"], "model": model_name, "provider": cross["provider"],
                   "seed": seed, "status": manifest["status"], "probe": "crossjudge",
                   "estimator": "crossjudge_probe", "n_records": len(recs),
                   "spend_usd": round(budget.spent_usd, Cost.USD_DECIMALS)}
        log.write_summary(summary)

    if not graded_any:
        return RunOutcome(CANNOT_RUN, issues=[Issue(
            loc="$", check="probe",
            message="no real runs on disk to re-grade; run the eval first")])
    outcome.run_files.append(log.path)
    outcome.summaries.append(summary)
    if stopped:
        outcome.exit_code = STOPPED_EARLY
        outcome.stopped_reason = stopped
    return outcome


def run_canary_probe(
    spec_path: str | Path,
    *,
    out_dir: Path | None = None,
    provider_factory=make_provider,
) -> RunOutcome:
    """Ask every model to continue the pod's canary, and a control it certainly
    memorised. See contamination.py: without the control, a clean result is
    unfalsifiable."""
    from dinostomp import contamination

    spec_file = Path(spec_path).resolve()
    spec, issues = load_spec(spec_file)
    if spec is None or issues:
        return RunOutcome(CANNOT_RUN, issues=issues)
    base = spec_file.parent
    canary = contamination.read_canary(base / spec["data"]["path"])
    if not canary:
        return RunOutcome(CANNOT_RUN, issues=[Issue(
            loc="$.data.path", check="probe",
            message="a canary probe needs a `_canary` line in the dataset; this pod ships none")])
    if len(canary) < contamination.MIN_CANARY_CHARS:
        return RunOutcome(CANNOT_RUN, issues=[Issue(
            loc="$.data.path", check="probe",
            message=f"this pod's canary is {len(canary)} characters; a string short enough to be "
                    f"produced by chance is not evidence of contamination. Use at least "
                    f"{contamination.MIN_CANARY_CHARS}.")])

    cases = contamination.build_cases(canary)
    hashes = {"spec_sha256": spec_sha256(spec_file),
              "data_sha256": spec_sha256(base / spec["data"]["path"])}
    run_cfg = spec["run"]
    seed = int(run_cfg["seed"])
    outcome = RunOutcome(OK)

    for model_cfg in spec["models"]:
        provider_name = model_cfg["provider"]
        if provider_name in ZERO_RATE_PROVIDERS:
            continue  # a local target cannot have memorised anything upstream
        model = model_cfg["model"]
        rate_in, rate_out, rate_label = resolve_rates(
            provider_name, model, None, None, model_cfg.get("price_in"), model_cfg.get("price_out"))
        if rate_in is None:
            return RunOutcome(CANNOT_RUN, issues=[Issue(
                loc="$.models", check="budget", message=f"{model!r} has no known price")])
        try:
            provider = provider_factory(provider_name, model)
        except ProviderError as exc:
            return RunOutcome(CANNOT_RUN, issues=[Issue(loc="$.models", message=str(exc), check="provider")])

        log = RunLog(spec["name"], model, "canaryprobe", seed,
                     data_dir=(out_dir or base) / "data", resume_path=None)
        budget = Budget(cap_usd=float(run_cfg["budget_usd"]))
        manifest = {
            "tool_version": dinostomp.__version__,
        "tool_sha256": engine_fingerprint(), "spec_name": spec["name"],
            "spec_version": spec["version"], **hashes, "provider": provider_name, "model": model,
            "seed": seed, "n_items": len(cases), "dry_run": False,
            "budget_cap_usd": float(run_cfg["budget_usd"]),
            "rate_in_per_mtok": rate_in, "rate_out_per_mtok": rate_out,
            "witness_report": {"n_witnesses": 0, "n_behaved": 0, "verdict": "absent"},
            "env": _env_envelope(), "probe": "canary",
            "started_at": utc_now().isoformat(), "status": "running",
        }
        stopped = ""
        with log:
            log.write_manifest(manifest)
            for case in cases:
                item = {"id": case["case_id"], "input": contamination.prompt_for(case), "target": case["tail"]}
                try:
                    completion = provider.complete(item, seed, {"max_tokens": 64, "temperature": 0})
                except ProviderError as exc:
                    stopped = f"provider: {exc}"
                    break
                cost = price_call(model, completion.input_tokens, completion.output_tokens,
                                  raw=completion.raw_usage, rate_in=rate_in, rate_out=rate_out,
                                  rate_label=rate_label)
                budget.record(cost.usd)
                hit = contamination.reproduced(completion.text, case["tail"])
                log.append({
                    "key": case["case_id"], "item_id": case["case_id"], "model": model,
                    "provider": provider_name, "seed": seed, "output": completion.text,
                    "finish_reason": completion.finish_reason,
                    "score": {"verdict": "flag" if hit else "fail",
                              "evidence": f"{case['kind']}: continuation "
                                          f"{'REPRODUCED' if hit else 'not reproduced'}"},
                    "canary_kind": case["kind"],
                    "usage": cost.to_dict(), "ts": utc_now().isoformat(),
                })
                if budget.spent_usd > budget.cap_usd + SPEND_EPS:
                    stopped = "budget: canary probe reached the cap"
                    break
            manifest["status"] = "stopped_early" if stopped else "complete"
            if stopped:
                manifest["stopped_reason"] = stopped
            manifest["spend_usd"] = round(budget.spent_usd, Cost.USD_DECIMALS)
            manifest["spend_source"] = "metered"
            manifest["finished_at"] = utc_now().isoformat()
            log.write_manifest(manifest)
            recs = log.records()
            summary = {
                "spec_name": spec["name"], "model": model, "provider": provider_name, "seed": seed,
                "status": manifest["status"], "probe": "canary", "estimator": "canary_probe",
                "n_records": len(recs),
                "controls_reproduced": sum(1 for r in recs if r.get("canary_kind") == "control"
                                           and r["score"]["verdict"] == "flag"),
                "n_controls": sum(1 for r in recs if r.get("canary_kind") == "control"),
                "canary_reproduced": any(r.get("canary_kind") == "canary"
                                         and r["score"]["verdict"] == "flag" for r in recs),
                "spend_usd": round(budget.spent_usd, Cost.USD_DECIMALS),
            }
            log.write_summary(summary)
        outcome.run_files.append(log.path)
        outcome.summaries.append(summary)
        if stopped:
            outcome.exit_code = STOPPED_EARLY
            outcome.stopped_reason = stopped
            break
    if not outcome.summaries:
        return RunOutcome(CANNOT_RUN, issues=[Issue(
            loc="$.models", check="probe",
            message="a canary probe needs a hosted model; this pod's models are all local")])
    return outcome


JUDGE_GAUNTLET_ITEMS = 8  # items sampled for the gauntlet; every drop is logged, never silent


def run_judge_probe(
    spec_path: str | Path,
    *,
    out_dir: Path | None = None,
    limit: int | None = None,
    provider_factory=make_provider,
) -> RunOutcome:
    """Make the judge earn the right to judge.

    Grades cases whose correct verdict is known BY CONSTRUCTION, then regrades
    each one under content-free perturbations. The result is a probe run:
    tagged in its manifest, never pooled with real results, read only by J1/J2.
    Its own budget is the spec's cap, because a judge is not free.
    """
    from dinostomp.judging import PERTURBATIONS, build_cases

    PERTURBATION_NAMES = [x.name for x in PERTURBATIONS]

    spec_file = Path(spec_path).resolve()
    spec, issues = load_spec(spec_file)
    if spec is None or issues:
        return RunOutcome(CANNOT_RUN, issues=issues)
    if spec["scorer"]["kind"] != "judge":
        return RunOutcome(CANNOT_RUN, issues=[Issue(
            loc="$.scorer.kind", check="probe",
            message="a judge probe needs a judge scorer; this spec scores with "
                    f"{spec['scorer']['kind']!r}")])
    base = spec_file.parent

    items, data_issues = load_items(spec["data"], base)
    if data_issues:
        return RunOutcome(CANNOT_RUN, issues=data_issues)
    try:
        scorer = make_scorer(spec["scorer"], base)
    except (ValueError, ProviderError) as exc:
        return RunOutcome(CANNOT_RUN, issues=[Issue(loc="$.scorer", message=str(exc), check="scorer")])

    witness_report = run_witnesses(scorer, spec["scorer"]["witnesses"])
    if witness_report.verdict != "validated":
        return RunOutcome(GATED, witness_failures=witness_report.failures)

    judge_cfg = spec["scorer"]["judge"]
    rate_in, rate_out, rate_label = resolve_rates(
        judge_cfg["provider"], judge_cfg.get("model", ""), None, None,
        judge_cfg.get("price_in"), judge_cfg.get("price_out"))
    if rate_in is None:
        return RunOutcome(CANNOT_RUN, issues=[Issue(
            loc="$.scorer.judge.model", check="budget",
            message=f"judge model {judge_cfg.get('model')!r} has no known price")])

    hashes = {"spec_sha256": spec_sha256(spec_file),
              "data_sha256": spec_sha256(base / spec["data"]["path"])}
    judge_file = judge_entrypoint(spec)
    if judge_file:
        hashes["judge_sha256"] = spec_sha256(base / judge_file)

    run_cfg = spec["run"]
    seed = int(run_cfg["seed"])
    sample = min(int(limit or JUDGE_GAUNTLET_ITEMS), len(items))
    if sample < len(items):
        print(f"  judge gauntlet samples {sample} of {len(items)} item(s) "
              f"(cap: JUDGE_GAUNTLET_ITEMS={JUDGE_GAUNTLET_ITEMS}); the rest are not graded here")
    cases = build_cases(select_items(items, sample, seed), sample)

    model = judge_cfg.get("model") or judge_cfg.get("entrypoint", "judge")
    log = RunLog(spec["name"], model, f"n{sample}-judgeprobe", seed,
                 data_dir=(out_dir or base) / "data", resume_path=None)
    budget = Budget(cap_usd=float(run_cfg["budget_usd"]))
    manifest = {
        "tool_version": dinostomp.__version__,
        "tool_sha256": engine_fingerprint(),
        "spec_name": spec["name"],
        "spec_version": spec["version"],
        **hashes,
        "provider": judge_cfg["provider"],
        "model": model,
        "seed": seed,
        "n_items": len(cases),
        "dry_run": judge_cfg["provider"] in ("dry", "python"),
        "budget_cap_usd": float(run_cfg["budget_usd"]),
        "rate_in_per_mtok": rate_in,
        "rate_out_per_mtok": rate_out,
        "witness_report": witness_report.to_manifest(),
        "env": _env_envelope(),
        "probe": "judge",
        "started_at": utc_now().isoformat(),
        "status": "running",
    }

    stopped = ""
    outcome = RunOutcome(OK)
    with log:
        log.write_manifest(manifest)
        for case in cases:
            before = (scorer.input_tokens, scorer.output_tokens)
            try:
                result = scorer(case.output, case.target)
            except ProviderError as exc:
                stopped = f"provider: {exc}"
                break
            usd = ((scorer.input_tokens - before[0]) * rate_in
                   + (scorer.output_tokens - before[1]) * rate_out) / 1_000_000
            budget.record(usd)
            log.append({
                "key": case.case_id,
                "item_id": case.item_id,
                "model": model,
                "provider": judge_cfg["provider"],
                "seed": seed,
                "output": case.output,
                "finish_reason": "stop",
                "score": result.to_dict(),
                "judge_response": scorer.last_response,
                "perturbation": case.perturbation,
                "polarity": case.polarity,
                "usage": {"input_tokens": scorer.input_tokens - before[0],
                          "output_tokens": scorer.output_tokens - before[1],
                          "cost_usd": round(usd, 8), "rate_label": rate_label},
                "ts": utc_now().isoformat(),
            })
            if budget.spent_usd > budget.cap_usd + SPEND_EPS:
                stopped = (f"budget: judge grading reached ${budget.spent_usd:.4f} against the "
                           f"${budget.cap_usd:.2f} cap")
                break
        manifest["status"] = "stopped_early" if stopped else "complete"
        if stopped:
            manifest["stopped_reason"] = stopped
        manifest["spend_usd"] = round(budget.spent_usd, Cost.USD_DECIMALS)
        manifest["spend_source"] = "metered"
        manifest["judge_calls"] = int(scorer.calls)
        manifest["finished_at"] = utc_now().isoformat()
        log.write_manifest(manifest)
        # A probe has no accuracy. Half its cases are SUPPOSED to fail, so
        # reporting passes/total here would publish a meaningless number that
        # looks like a result. The summary reports what the probe measured.
        recs = log.records()
        base = [r for r in recs if not r.get("perturbation")]
        agreed = sum(1 for r in base
                     if (r.get("score") or {}).get("verdict")
                     == ("pass" if r.get("polarity") == "correct" else "fail"))
        summary = {
            "spec_name": spec["name"], "model": model, "provider": judge_cfg["provider"],
            "seed": seed, "status": manifest["status"], "probe": "judge",
            "estimator": "judge_probe",
            "n_records": len(recs),
            "n_baseline_cases": len(base),
            "agreement_with_construction": round(agreed / len(base), 6) if base else None,
            "n_perturbations": len(PERTURBATION_NAMES),
            "spend_usd": round(budget.spent_usd, Cost.USD_DECIMALS),
        }
        log.write_summary(summary)

    outcome.run_files.append(log.path)
    outcome.summaries.append(summary)
    if stopped:
        outcome.exit_code = STOPPED_EARLY
        outcome.stopped_reason = stopped
    return outcome


def run_spec(
    spec_path: str | Path,
    *,
    out_dir: Path | None = None,
    resume: Path | None = None,
    limit: int | None = None,
    dry_run: bool = False,
    price_in: float | None = None,
    price_out: float | None = None,
    probe: str | None = None,
    framing: str | None = None,
    provider_factory=make_provider,
) -> RunOutcome:
    """Run every model in the spec. See module docstring for the order of gates."""
    if probe == "crossjudge":
        return run_crossjudge_probe(spec_path, out_dir=out_dir, provider_factory=provider_factory)
    if probe == "canary":
        return run_canary_probe(spec_path, out_dir=out_dir, provider_factory=provider_factory)
    if probe == "judge":
        return run_judge_probe(spec_path, out_dir=out_dir, limit=limit,
                               provider_factory=provider_factory)
    spec_file = Path(spec_path).resolve()
    spec, issues = load_spec(spec_file)
    if spec is None or issues:
        return RunOutcome(CANNOT_RUN, issues=issues)
    base = spec_file.parent

    items, data_issues = load_items(spec["data"], base)
    if data_issues:
        return RunOutcome(CANNOT_RUN, issues=data_issues)

    try:
        scorer = make_scorer(spec["scorer"], base)
    except ValueError as exc:
        return RunOutcome(CANNOT_RUN, issues=[Issue(loc="$.scorer", message=str(exc), check="scorer")])

    # The gate. Nothing below this line happens if the scorer misbehaves.
    witness_report = run_witnesses(scorer, spec["scorer"]["witnesses"])
    if witness_report.verdict != "validated":
        return RunOutcome(GATED, witness_failures=witness_report.failures)

    # The drift boundary: hash every file that influences this run.
    hashes = {
        "spec_sha256": spec_sha256(spec_file),
        "data_sha256": spec_sha256(base / spec["data"]["path"]),
    }
    if spec["scorer"]["kind"] == "python":
        hashes["scorer_sha256"] = spec_sha256(base / spec["scorer"]["code"])
    judge_file = judge_entrypoint(spec)
    if judge_file:
        # A judge decides verdicts, so it is the last input that should be
        # allowed to change quietly.
        hashes["judge_sha256"] = spec_sha256(base / judge_file)
    mounts = mount_hashes(spec, base)
    if mounts:
        # Shared code outside the pod. Declaring it is what makes referencing it
        # legal, and hashing it is what the declaration buys: a workspace-wide
        # scorer edited between runs is drift, exactly like a pod-local one.
        hashes["mount_sha256"] = mounts

    # Target code is per-model, so it is hashed per model rather than folded
    # into the shared set: two agents in one fleet are two different inputs.
    target_hashes: dict[str, str] = {}
    for mc in spec["models"]:
        entry = target_entrypoint(mc)
        if entry:
            target_hashes[mc["model"]] = spec_sha256(base / entry)

    models = list(spec["models"])
    resume_seed = None
    if resume is not None:
        # A resume must continue the SAME experiment: same spec, same data,
        # same scorer code, and only the model the interrupted run belongs to.
        mp = Path(resume).with_name(Path(resume).stem + "_manifest.json")
        try:
            old = json.loads(mp.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return RunOutcome(CANNOT_RUN, issues=[
                Issue(loc="$", message=f"cannot resume: manifest unreadable ({exc})", check="resume")])
        stale = [k.replace("_sha256", "") for k, v in hashes.items() if old.get(k) != v]
        resumed_target = target_hashes.get(str(old.get("model")))
        if resumed_target is not None and old.get("target_sha256") != resumed_target:
            stale.append("target")
        if stale:
            return RunOutcome(CANNOT_RUN, issues=[
                Issue(loc="$", check="resume",
                      message=f"cannot resume: {', '.join(stale)} changed since that run; "
                              "finished items would no longer mean the same thing. Re-run instead.")])
        if dry_run and not old.get("dry_run"):
            return RunOutcome(CANNOT_RUN, issues=[
                Issue(loc="$", check="resume",
                      message="refusing to resume a real-provider run with --dry-run: synthetic "
                              "outputs would be appended into a paid ledger")])
        resume_seed = old.get("seed")
        models = [mc for mc in models
                  if mc["model"] == old.get("model")
                  and ("dry" if dry_run else mc["provider"]) == old.get("provider")]
        if not models:
            return RunOutcome(CANNOT_RUN, issues=[
                Issue(loc="$.models", check="resume",
                      message=f"cannot resume: no model in this spec matches "
                              f"{old.get('provider')!r}/{old.get('model')!r}")])

    judge_cfg = (spec["scorer"].get("judge") or {}) if spec["scorer"]["kind"] == "judge" else {}
    judge_rate_in, judge_rate_out, judge_rate_label = resolve_rates(
        judge_cfg.get("provider", "dry"), judge_cfg.get("model", ""), None, None,
        judge_cfg.get("price_in"), judge_cfg.get("price_out"))
    if judge_cfg and judge_rate_in is None:
        return RunOutcome(CANNOT_RUN, issues=[Issue(
            loc="$.scorer.judge.model", check="budget",
            message=f"judge model {judge_cfg.get('model')!r} has no known price; a judge that "
                    "cannot be priced cannot be capped, and an uncapped grader is not free")])

    if probe == "ablate" and not any(mc.get("provider") == "mediated" for mc in spec["models"]):
        return RunOutcome(CANNOT_RUN, issues=[Issue(
            loc="--probe ablate", check="probe",
            message="the ablation probe withholds TOOL results, and only a `mediated` agent reaches "
                    "its tools through the harness. A `python` target calls its own functions "
                    "directly, so there would be nothing to withhold and the probe run would "
                    "silently be an ordinary one")])

    render_choices = bool(spec["data"].get("render_choices"))
    if probe == "shuffle" and not render_choices:
        return RunOutcome(CANNOT_RUN, issues=[Issue(
            loc="$.data.render_choices", check="probe",
            message="a shuffle probe permutes an option block that dinostomp renders; set "
                    "data.render_choices: true so the tool owns the order, otherwise the "
                    "ordering lives in your prompt text and nothing here can permute it")])

    run_cfg = spec["run"]
    primary_seed = int(run_cfg["seed"])
    # Every declared seed is a full pass over the eval. Selection AND sampling
    # both move with it, which is exactly the spread a single-seed number hides.
    seeds = [primary_seed] + [int(s) for s in (run_cfg.get("seeds") or []) if int(s) != primary_seed]
    if resume is not None:
        # A resume continues ONE interrupted run. Without this, resuming a
        # multi-seed pod would continue that run and then start fresh ones for
        # every other declared seed, quietly turning a resume into a new run.
        if resume_seed is None or int(resume_seed) not in seeds:
            return RunOutcome(CANNOT_RUN, issues=[Issue(
                loc="$.run.seeds", check="resume",
                message=f"cannot resume: that run used seed {resume_seed!r}, which this spec no "
                        "longer declares")])
        seeds = [int(resume_seed)]
    repeats = int(run_cfg.get("repeats", 1))
    n = min(int(run_cfg["n"]), len(items))
    if limit is not None:
        n = min(n, int(limit))

    data_dir = (out_dir or base) / "data"
    outcome = RunOutcome(OK)

    # An `imported` model names evidence this engine did not produce and cannot
    # produce. Refused BEFORE the dry-run substitution below, because --dry would
    # otherwise turn "I cannot call this" into a full set of fabricated records
    # under the real model's name, which is the exact failure this tool exists to
    # object to.
    foreign = sorted({mc["model"] for mc in models if mc["provider"] == "imported"})
    if foreign:
        return RunOutcome(CANNOT_RUN, issues=[Issue(
            loc="$.models", check="run",
            message=f"{', '.join(repr(m) for m in foreign)} declares provider 'imported': this "
                    "engine cannot call it, and --dry would fabricate its answers rather than "
                    "leave them missing. Attach the other harness's log with `dinostomp import` "
                    "instead")])

    for seed, model_cfg in [(s, mc) for mc in models for s in seeds]:
        selected = select_items(items, n, seed)
        provider_name = "dry" if dry_run else model_cfg["provider"]
        model = model_cfg["model"]
        params = model_cfg.get("params") or {}

        rate_in, rate_out, rate_label = resolve_rates(
            provider_name, model, price_in, price_out,
            model_cfg.get("price_in"), model_cfg.get("price_out"))
        if rate_in is None:
            outcome.issues.append(
                Issue(
                    loc="$.models",
                    message=f"{model!r} has no known price; pass --price-in/--price-out to run it",
                    check="budget",
                )
            )
            return RunOutcome(CANNOT_RUN, issues=outcome.issues)
        if provider_name not in ZERO_RATE_PROVIDERS and float(run_cfg["budget_usd"]) <= 0:
            outcome.issues.append(
                Issue(loc="$.run.budget_usd", message="network provider with a zero budget; nothing can run", check="budget")
            )
            return RunOutcome(CANNOT_RUN, issues=outcome.issues)

        extra = {}
        if provider_name == "python":
            extra = {"entrypoint": model_cfg.get("entrypoint"), "base_dir": base}
        elif provider_name == "mediated":
            # Policy travels to the HARNESS, not just to the checks. On this
            # rail a forbidden tool is denied when the agent reaches for it, so
            # T1 reads a record of something that was stopped rather than a
            # record of something that happened.
            traj = spec.get("trajectory") or {}
            extra = {"entrypoint": model_cfg.get("entrypoint"), "base_dir": base,
                     "tools": spec.get("tools") or {},
                     "forbidden": set(traj.get("forbidden_tools") or ()),
                     "max_steps": traj.get("max_steps"),
                     "ablate": probe == "ablate",
                     "isolation": spec.get("isolation") or {}}
        try:
            provider = provider_factory(provider_name, model, **extra)
        except ProviderError as exc:
            return RunOutcome(CANNOT_RUN, issues=[Issue(loc="$.models", message=str(exc), check="provider")])

        params_tag = f"n{n}" + (f"-{probe}probe" if probe else "")
        if probe == "template":
            params_tag += f"-{framing}"
        log = RunLog(spec["name"], model, params_tag, seed, data_dir=data_dir, resume_path=resume)
        budget = Budget(cap_usd=float(run_cfg["budget_usd"]), spent_usd=log.prior_spend_usd)
        max_tokens = int(params.get("max_tokens", 1024))

        manifest = {
            "tool_version": dinostomp.__version__,
        "tool_sha256": engine_fingerprint(),
            "spec_name": spec["name"],
            "spec_version": spec["version"],
            **hashes,
            "provider": provider_name,
            "model": model,
            "seed": seed,
            "n_items": n,
            "repeats": repeats,
            "dry_run": bool(dry_run or provider_name == "dry"),
            **({"framing": framing} if probe == "template" else {}),
            "budget_cap_usd": float(run_cfg["budget_usd"]),
            "rate_in_per_mtok": rate_in,
            "rate_out_per_mtok": rate_out,
            "witness_report": witness_report.to_manifest(),
            "env": _env_envelope(),
            "started_at": utc_now().isoformat(),
            "status": "running",
        }
        if provider_name in ("python", "mediated") and model in target_hashes:
            manifest["target_sha256"] = target_hashes[model]
        if provider_name == "mediated":
            iso = spec.get("isolation") or {}
            # The rail is recorded, not inferred at audit time. A reader must be
            # able to tell an OBSERVED trajectory from a self-reported one
            # without knowing which provider string means which, and the checks
            # must not have to guess either.
            manifest["trajectory_source"] = "harness_observed"
            manifest["tool_sha256_by_name"] = tool_hashes(spec, base)
            # Recorded, because "the harness watched this" and "the harness
            # watched this from another process" are different claims and a
            # reader of a report cannot tell them apart otherwise.
            manifest["isolation"] = str(iso.get("mode") or "inprocess")
        elif provider_name == "python":
            manifest["trajectory_source"] = "self_reported"
        if probe:
            # Probe runs carry their nature in the manifest so the battery can
            # never confuse a blind baseline with a real result.
            manifest["probe"] = probe
        if resume is not None:
            manifest["resumed_from"] = str(resume)
            manifest["prior_spend_usd"] = round(log.prior_spend_usd, 6)

        stopped = ""
        target_reported_spend = False
        with log:
            log.write_manifest(manifest)
            for item in selected:
                for rep in range(repeats):
                    key = f"{item['id']}#r{rep}"
                    if log.is_done(key):
                        continue
                    # Estimate on the same serialization the provider sends,
                    # not Python repr; worst case output = full max_tokens.
                    prompt = item["input"] if isinstance(item["input"], str) else json.dumps(item["input"])
                    est = (len(prompt) / CHARS_PER_TOKEN_EST * rate_in + max_tokens * rate_out) / 1_000_000
                    try:
                        budget.check(est)
                    except BudgetExceeded as exc:
                        stopped = f"budget: {exc}"
                        break
                    if probe == "blind":
                        call_item = {**item, "input": blind_input(item)}
                    elif probe == "template":
                        # The item's own text is untouched; only the task
                        # statement wrapped around it changes, which is what
                        # makes a swing attributable to the framing.
                        base_input = item["input"]
                        if render_choices and isinstance(item.get("choices"), list):
                            base_input = render_options(item, item["choices"])
                        call_item = {**item,
                                     "input": framed_input(item, framing, rendered=base_input)}
                    elif probe == "shuffle":
                        shuffled = shuffled_input(item, seed)
                        call_item = {**item, "input": shuffled} if shuffled else item
                    elif render_choices and isinstance(item.get("choices"), list):
                        call_item = {**item, "input": render_options(item, item["choices"])}
                    else:
                        call_item = item
                    try:
                        completion = provider.complete(call_item, seed, params)
                    except ProviderError as exc:
                        stopped = f"provider: {exc}"
                        break
                    if completion.cost_usd is not None:
                        # The target priced its own call (it spent money the
                        # ledger cannot see). Recorded as a claim, labelled as
                        # one, and counted against the same cap.
                        target_reported_spend = True
                        cost = Cost(
                            input_tokens=completion.input_tokens,
                            output_tokens=completion.output_tokens,
                            usd=float(completion.cost_usd),
                            rate_label="target-reported",
                            raw=completion.raw_usage,
                        )
                    else:
                        cost = price_call(
                            model, completion.input_tokens, completion.output_tokens,
                            raw=completion.raw_usage, rate_in=rate_in, rate_out=rate_out,
                            rate_label=rate_label,
                        )
                    budget.record(cost.usd)
                    if completion.model_reported and "model_reported" not in manifest:
                        manifest["model_reported"] = completion.model_reported
                    before = (getattr(scorer, "input_tokens", 0), getattr(scorer, "output_tokens", 0))
                    try:
                        result = scorer(completion.text, item["target"])
                    except Exception as exc:  # noqa: BLE001 - stop clean, but bank the paid output first
                        result = None
                        stopped = f"scorer: {type(exc).__name__}: {exc}"
                    # A judge is a model too. Its tokens are spend, they count
                    # against the same cap, and they are itemised in the record
                    # rather than folded invisibly into "the cost of the eval".
                    judge_usd = 0.0
                    if judge_rate_in:
                        d_in = getattr(scorer, "input_tokens", 0) - before[0]
                        d_out = getattr(scorer, "output_tokens", 0) - before[1]
                        judge_usd = (d_in * judge_rate_in + d_out * judge_rate_out) / 1_000_000
                        if judge_usd:
                            cost.usd += judge_usd
                            budget.spent_usd += judge_usd
                    # The pre-call estimate is a forecast; this is the fact. A
                    # provider that returns more than forecast, a target that
                    # reports its own spend, or a judge whose grading cost more
                    # than the answer must still not walk past the cap.
                    over_cap = budget.spent_usd > budget.cap_usd + SPEND_EPS
                    record = {
                        "key": key,
                        "item_id": item["id"],
                        "model": model,
                        "provider": provider_name,
                        "seed": seed,
                        "repeat": rep,
                        "output": completion.text,
                        "finish_reason": completion.finish_reason,
                        "score": result.to_dict() if result else
                                 {"verdict": "uncheckable", "evidence": f"scorer crashed: {stopped}"},
                        "usage": cost.to_dict(),
                        "ts": utc_now().isoformat(),
                    }
                    if judge_usd:
                        record["usage"]["judge_cost_usd"] = round(judge_usd, 8)
                    if getattr(scorer, "last_response", ""):
                        # The judge's own words, kept so the verdict stays
                        # re-derivable offline (R8 never calls a model).
                        record["judge_response"] = scorer.last_response
                    if completion.trajectory:
                        record["trajectory"] = completion.trajectory
                    log.append(record)
                    if over_cap and not stopped:
                        stopped = (f"budget: actual spend ${budget.spent_usd:.4f} passed the "
                                   f"${budget.cap_usd:.2f} cap; this item is paid for and banked")
                    if stopped:
                        break
                if stopped:
                    break

            manifest["status"] = "stopped_early" if stopped else "complete"
            if stopped:
                manifest["stopped_reason"] = stopped
            manifest["spend_usd"] = round(budget.spent_usd, Cost.USD_DECIMALS)
            manifest["spend_source"] = "target_reported" if target_reported_spend else "metered"
            if judge_cfg:
                manifest["judge_calls"] = int(getattr(scorer, "calls", 0))
            manifest["finished_at"] = utc_now().isoformat()
            log.write_manifest(manifest)
            summary = {
                "spec_name": spec["name"],
                "model": model,
                "provider": provider_name,
                "seed": seed,
                "status": manifest["status"],
                **summarize(log.records()),
            }
            log.write_summary(summary)

        outcome.run_files.append(log.path)
        outcome.summaries.append(summary)
        if stopped:
            outcome.exit_code = STOPPED_EARLY
            outcome.stopped_reason = stopped
            break  # do not start the next model on a blown budget or dead provider

    return outcome


def run_template_probe(
    spec_path: str | Path,
    *,
    framings: list[str] | None = None,
    out_dir: Path | None = None,
    provider_factory=make_provider,
) -> RunOutcome:
    """Re-run the eval once per instruction framing. Same items, same seed.

    The cost is linear in the number of framings, and it is real money, so the
    caller sees it in `plan` before it is spent. What comes back is one tagged
    run file per (model, framing), which P11 and P12 read.

    Stops at the first framing that cannot run, rather than pressing on: a
    partial framing set would give P12 a ranking comparison over a sample that
    is not the same sample, which is the exact confound this probe exists to
    measure.
    """
    names = list(framings or DEFAULT_FRAMINGS)
    unknown = [n for n in names if n not in FRAMINGS_BY_NAME]
    if unknown:
        return RunOutcome(CANNOT_RUN, issues=[Issue(
            loc="--framings", check="probe",
            message=f"unknown framing(s) {', '.join(unknown)}; known: "
                    f"{', '.join(FRAMINGS_BY_NAME)}")])
    if len(names) < 2:
        return RunOutcome(CANNOT_RUN, issues=[Issue(
            loc="--framings", check="probe",
            message="a template probe needs at least 2 framings; one phrasing is "
                    "what every eval already does")])

    last = RunOutcome(OK)
    for name in names:
        last = run_spec(spec_path, out_dir=out_dir, probe="template", framing=name,
                        provider_factory=provider_factory)
        if last.exit_code != OK:
            last.issues.append(Issue(
                loc="--probe template", check="probe",
                message=f"stopped at framing {name!r}; the framings that did run are on disk but "
                        "P12 needs the whole set to compare rankings over the same sample"))
            return last
    return last
