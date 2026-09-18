"""Test a Jev question the way you would test an if-statement.

    dinostomp jev urgency.jev.yaml

A decisions model (TypeSafe's Jev) is called from application code with a
question and a state, and answers with a probability. The developer who
wrote the question usually has three playground examples and a hunch about
the threshold. This takes a question file (the question, plus labelled
examples) and answers what they need before shipping it:

  * accuracy on their examples, with an interval that says how much 40
    examples can tell them;
  * for a yes/no (noul) question, where to cut p(yes), and how much of the
    traffic the model answers confidently and how often it is right there;
  * calibration (ECE, the same measure and bar as R23);
  * the blank-input prior: what the question answers with NO state. If
    answering that to every example scores close to the model, the examples
    are lopsided or the question leans, and the accuracy says little;
  * rewording: content-free changes to the state (whitespace, a markdown
    fence, a polite sign-off) that must not flip an answer;
  * the examples it got wrong while sure, which are either mislabelled or
    the question's blind spot, and are the first thing to read;
  * a saved result per run, compared with the last run of the same question,
    so a model update that moves the answers is a printed line, not a
    production incident.

Every measure is one the battery already uses; this file is the front door.
The call goes through the `typesafe` provider, which falls back to the
OpenRouter door when only that key is set.
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from dinostomp.calibration import coverage_table, expected_calibration_error
from dinostomp.judging import PERTURBATIONS
from dinostomp.providers import ProviderError, make_provider
from dinostomp.psychometrics import MIN_EVIDENCE, wilson_ci
from dinostomp.runlog import utc_now

MAX_FILE_BYTES = 1024 * 1024          # a question file is text a person wrote
MAX_EXAMPLES = 1000
MAX_STATE_CHARS = 20_000
MAX_INSTRUCTIONS_CHARS = 2_000
MIN_EXAMPLES = 2
DEFAULT_MODEL = "jev-latest"
DEFAULT_PROVIDER = "typesafe"
NOUL_LABELS = ("yes", "no")
# Rewording that changes no meaning for ANY input. The judge gauntlet's other
# three (verbosity, confidence, authority) can legitimately change what a
# question like "is this claim sourced?" should answer, so they are opt-in.
DEFAULT_REWORDING = ("whitespace", "formatting", "politeness")
REWORDING_SAMPLE = 20                  # examples perturbed per run; each costs one call per perturbation
REWORDING_SEED = 20260918
CUT_GRID = [round(0.05 * i, 2) for i in range(1, 20)]   # 0.05 .. 0.95
CONFIDENT = 0.90                       # the floor the "confident" line reports
ECE_BAR = 0.10                         # R23's bar, stated once here for the printout
BLIND_LIFT_MIN = 0.10                  # R15's bar: the model must clear its own blank-input score by this
SHOW_WRONG = 5
PROGRESS_EVERY = 10
RESULT_DIR = Path("data") / "jev"
KNOWN_PERTURBATIONS = {p.name: p for p in PERTURBATIONS}


class QuestionFileError(ValueError):
    """The question file is malformed. The message says where."""


@dataclass
class Question:
    path: Path
    kind: str                          # "noul" | "choice"
    instructions: str
    criteria: dict[str, str] | None
    labels: list[str]                  # noul: [yes, no]; choice: the criteria keys
    examples: list[dict]               # {"state": str, "expect": str}
    model: str
    rewording: list[str]
    require: dict[str, float] = field(default_factory=dict)

    def fingerprint(self) -> str:
        """Identity of the question and its examples, not of the model. Two runs
        with the same fingerprint are comparable; a run after an edit is not."""
        body = json.dumps({"kind": self.kind, "instructions": self.instructions,
                           "criteria": self.criteria, "examples": self.examples},
                          sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _label(value: Any) -> str:
    # YAML 1.1 reads a bare `yes` / `no` as a boolean. Writing `expect: yes`
    # is the obvious thing to type, so a boolean means the noul label.
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return str(value)


def load_question(path: str | Path) -> Question:
    """Parse and validate a question file. Every rejection names the field."""
    path = Path(path)
    if not path.is_file():
        raise QuestionFileError(f"{path}: no such file")
    size = path.stat().st_size
    if size > MAX_FILE_BYTES:
        raise QuestionFileError(f"{path}: {size:,} bytes, over the {MAX_FILE_BYTES // 1024} KB cap")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise QuestionFileError(f"{path}: not valid YAML: {exc}") from None
    if not isinstance(raw, dict):
        raise QuestionFileError(f"{path}: expected a mapping with `question` and `examples`")

    q = raw.get("question")
    if not isinstance(q, dict):
        raise QuestionFileError("question: required, a mapping with `type` and `instructions`")
    kind = str(q.get("type") or "")
    if kind not in ("noul", "choice"):
        raise QuestionFileError(f"question.type: {kind!r}; expected noul (yes/no) or choice")
    instructions = q.get("instructions")
    if not isinstance(instructions, str) or not instructions.strip():
        raise QuestionFileError("question.instructions: required, the question as text")
    if len(instructions) > MAX_INSTRUCTIONS_CHARS:
        raise QuestionFileError(f"question.instructions: over {MAX_INSTRUCTIONS_CHARS} characters")
    criteria = q.get("criteria")
    if criteria is not None:
        if not isinstance(criteria, dict) or not criteria:
            raise QuestionFileError("question.criteria: a mapping of option -> what it means")
        # A noul question's criteria keys are `true` and `false`, which YAML also
        # reads as booleans; they are keys here, not labels, so they stay words.
        criteria = {(str(k).lower() if isinstance(k, bool) else str(k)): str(v) for k, v in criteria.items()}
    if kind == "choice":
        if not criteria or len(criteria) < 2:
            raise QuestionFileError("question.criteria: a choice question needs at least two options")
        labels = list(criteria)
    else:
        if criteria is not None and set(criteria) - {"true", "false"}:
            raise QuestionFileError("question.criteria: a noul question takes only `true` and `false`")
        labels = list(NOUL_LABELS)

    examples_raw = raw.get("examples")
    if not isinstance(examples_raw, list) or len(examples_raw) < MIN_EXAMPLES:
        raise QuestionFileError(f"examples: at least {MIN_EXAMPLES}, each {{state, expect}}")
    if len(examples_raw) > MAX_EXAMPLES:
        raise QuestionFileError(f"examples: {len(examples_raw)}, over the {MAX_EXAMPLES} cap")
    examples = []
    for i, ex in enumerate(examples_raw):
        if not isinstance(ex, dict) or "state" not in ex or "expect" not in ex:
            raise QuestionFileError(f"examples[{i}]: needs `state` and `expect`")
        state = ex["state"]
        if not isinstance(state, str):
            raise QuestionFileError(f"examples[{i}].state: text, got {type(state).__name__}")
        if len(state) > MAX_STATE_CHARS:
            raise QuestionFileError(f"examples[{i}].state: over {MAX_STATE_CHARS:,} characters")
        expect = _label(ex["expect"])
        if expect not in labels:
            raise QuestionFileError(f"examples[{i}].expect: {expect!r} is not one of {labels}")
        examples.append({"state": state, "expect": expect})

    rewording = raw.get("rewording", list(DEFAULT_REWORDING))
    if not isinstance(rewording, list) or any(r not in KNOWN_PERTURBATIONS for r in rewording):
        raise QuestionFileError(f"rewording: a list drawn from {sorted(KNOWN_PERTURBATIONS)}")
    require = raw.get("require") or {}
    if not isinstance(require, dict) or set(require) - {"accuracy", "flips"}:
        raise QuestionFileError("require: optional, keys `accuracy` (0..1) and `flips` (a count)")
    return Question(path=path, kind=kind, instructions=instructions, criteria=criteria,
                    labels=labels, examples=examples, model=str(raw.get("model") or DEFAULT_MODEL),
                    rewording=list(rewording), require={k: float(v) for k, v in require.items()})


def _ask(provider, q: Question, state: str):
    """One call. Returns (probability per label, the completion)."""
    if q.kind == "noul":
        params = {"question": "noul", "instructions": q.instructions, "labels": list(NOUL_LABELS)}
        if q.criteria:
            params["criteria"] = q.criteria
        item = {"id": "q", "input": state, "target": NOUL_LABELS[0]}
    else:
        params = {"instructions": q.instructions}
        item = {"id": "q", "input": state, "target": q.labels[0], "choices": q.labels,
                "metadata": {"options": q.criteria}}
    completion = provider.complete(item, 0, params)
    evidence = json.loads(completion.trajectory[0]["result"])
    return {str(k): float(v) for k, v in evidence["distribution"].items()}, completion


def _top(dist: dict[str, float]) -> tuple[str, float]:
    label = max(dist, key=dist.get)
    return label, dist[label]


@dataclass
class Result:
    question: Question
    provider: str
    model_reported: str
    answers: list[dict]                # per example: expect, dist, answer, p
    blank: dict[str, float]
    flips: list[str]
    reworded: int
    tokens_in: int
    tokens_out: int

    @property
    def n(self) -> int:
        return len(self.answers)

    @property
    def correct(self) -> int:
        return sum(a["answer"] == a["expect"] for a in self.answers)

    def accuracy_at_cut(self, cut: float) -> float:
        yes, no = NOUL_LABELS
        right = sum((yes if a["dist"].get(yes, 0.0) >= cut else no) == a["expect"] for a in self.answers)
        return right / self.n

    def points(self) -> list[tuple[float, bool]]:
        return [(a["p"], a["answer"] == a["expect"]) for a in self.answers]


def run_question(q: Question, provider_name: str = DEFAULT_PROVIDER, model: str | None = None,
                 rewording: bool = True, provider_factory=None, progress=None) -> Result:
    """Every call the report needs: each example, one blank input, and the
    rewording sample. Sequential, with a progress line for slow links."""
    provider = (provider_factory or make_provider)(provider_name, model or q.model)
    sample = []
    if rewording and q.rewording:
        order = list(range(len(q.examples)))
        random.Random(REWORDING_SEED).shuffle(order)
        sample = order[:REWORDING_SAMPLE]
    total = len(q.examples) + 1 + len(sample) * len(q.rewording)
    done = 0
    tokens_in = tokens_out = 0
    model_reported = ""

    def tick():
        nonlocal done
        done += 1
        if progress and (done % PROGRESS_EVERY == 0 or done == total):
            progress(done, total)

    answers = []
    for ex in q.examples:
        dist, c = _ask(provider, q, ex["state"])
        tokens_in, tokens_out = tokens_in + c.input_tokens, tokens_out + c.output_tokens
        model_reported = c.model_reported or model_reported
        answer, p = _top(dist)
        answers.append({"state": ex["state"], "expect": ex["expect"], "dist": dist, "answer": answer, "p": p})
        tick()
    blank, c = _ask(provider, q, "")
    tokens_in, tokens_out = tokens_in + c.input_tokens, tokens_out + c.output_tokens
    tick()
    flips = []
    for i in sample:
        base = answers[i]["answer"]
        for name in q.rewording:
            dist, c = _ask(provider, q, KNOWN_PERTURBATIONS[name].apply(q.examples[i]["state"]))
            tokens_in, tokens_out = tokens_in + c.input_tokens, tokens_out + c.output_tokens
            moved, _ = _top(dist)
            if moved != base:
                flips.append(f"{name} on example {i + 1}: {base} -> {moved}")
            tick()
    return Result(question=q, provider=getattr(provider, "provider_name", provider_name),
                  model_reported=model_reported, answers=answers, blank=blank, flips=flips,
                  reworded=len(sample) * len(q.rewording), tokens_in=tokens_in, tokens_out=tokens_out)


def summarize(r: Result) -> dict:
    """The numbers the printout and the saved file both carry."""
    q = r.question
    acc = r.correct / r.n
    ci = wilson_ci(r.correct, r.n)
    blank_label, blank_p = _top(r.blank)
    blind_acc = sum(a["expect"] == blank_label for a in r.answers) / r.n
    points = r.points()
    out = {"n": r.n, "correct": r.correct, "accuracy": round(acc, 4),
           "accuracy_ci95": [round(ci[0], 4), round(ci[1], 4)] if ci else None,
           "blank": {"answer": blank_label, "p": round(blank_p, 4), "accuracy_if_always": round(blind_acc, 4)},
           "flips": len(r.flips), "reworded": r.reworded,
           "confident": coverage_table(points)[f"{CONFIDENT:.2f}"],
           "ece": round(expected_calibration_error(points), 4) if r.n >= MIN_EVIDENCE else None}
    if q.kind == "noul":
        at_half = r.accuracy_at_cut(0.5)
        best = max(CUT_GRID, key=lambda c: (r.accuracy_at_cut(c), -abs(c - 0.5)))
        out["cut"] = {"at_0.50": round(at_half, 4), "best": best, "at_best": round(r.accuracy_at_cut(best), 4)}
    return out


def verdict(q: Question, s: dict) -> tuple[bool, list[str], list[str]]:
    """(requirements met, requirement failures, advisories)."""
    failures, advice = [], []
    if "accuracy" in q.require and s["accuracy"] < q.require["accuracy"]:
        failures.append(f"accuracy {s['accuracy']:.0%} is under the required {q.require['accuracy']:.0%}")
    if "flips" in q.require and s["flips"] > q.require["flips"]:
        failures.append(f"{s['flips']} rewording flip(s), {int(q.require['flips'])} allowed")
    if s["n"] < MIN_EVIDENCE:
        advice.append(f"{s['n']} examples; {MIN_EVIDENCE}+ before accuracy and calibration mean much")
    if s["accuracy"] - s["blank"]["accuracy_if_always"] <= BLIND_LIFT_MIN:
        advice.append(f"answering {s['blank']['answer']!r} to everything scores "
                      f"{s['blank']['accuracy_if_always']:.0%}; add examples of the other answer(s)")
    if s["ece"] is not None and s["ece"] > ECE_BAR:
        advice.append(f"ECE {s['ece']:.2f}: the probabilities overstate or understate; threshold with care")
    if s["flips"]:
        advice.append(f"{s['flips']} answer(s) flipped under rewording that changes no meaning")
    return not failures, failures, advice


def save_result(r: Result, s: dict) -> Path:
    """Law 6: under data/jev/ beside the question file, metadata in the name."""
    out_dir = r.question.path.parent / RESULT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    model = (r.model_reported or r.question.model).replace("/", "-")
    name = f"{utc_now().strftime('%Y%m%d_%H%M%S')}_jev_{r.question.path.stem.split('.')[0]}_{model}_n{r.n}.json"
    record = {"question_file": r.question.path.name, "question_sha256": r.question.fingerprint(),
              "provider": r.provider, "model": r.question.model, "model_reported": r.model_reported,
              "at": utc_now().isoformat(), "summary": s, "flips": r.flips,
              "tokens": {"input": r.tokens_in, "output": r.tokens_out},
              "answers": [{"expect": a["expect"], "answer": a["answer"], "p": round(a["p"], 4),
                           "dist": {k: round(v, 4) for k, v in a["dist"].items()}} for a in r.answers]}
    path = out_dir / name
    # LF on every platform: a saved result is an artifact, and artifacts are
    # hashed as exact bytes (see .gitattributes).
    path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return path


def previous_result(q: Question, exclude: Path | None = None) -> dict | None:
    """The newest saved run of this exact question and examples, if any."""
    out_dir = q.path.parent / RESULT_DIR
    if not out_dir.is_dir():
        return None
    fp = q.fingerprint()
    for path in sorted(out_dir.glob("*_jev_*.json"), reverse=True):
        if exclude is not None and path.resolve() == exclude.resolve():
            continue
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if record.get("question_sha256") == fp:
            return record
    return None


def compare(prev: dict | None, r: Result, s: dict) -> str | None:
    """One line against the last run of the same question."""
    if prev is None:
        return None
    changed = sum(a["answer"] != b.get("answer") for a, b in zip(r.answers, prev.get("answers") or []))
    was = prev.get("summary", {}).get("accuracy")
    model_then, model_now = prev.get("model_reported") or "?", r.model_reported or "?"
    when = str(prev.get("at", ""))[:10]
    models = model_now if model_then == model_now else f"{model_then} -> {model_now}"
    if not changed and was == s["accuracy"]:
        return f"vs last run ({when}, {models}): no change"
    return (f"vs last run ({when}, {models}): accuracy {was:.0%} -> {s['accuracy']:.0%}, "
            f"{changed} answer(s) changed")


def render(r: Result, s: dict, saved: Path | None, line_vs_last: str | None) -> str:
    q = r.question
    lo, hi = s["accuracy_ci95"] or (0, 0)
    lines = [f"{q.path.name} | {q.kind} | {r.model_reported or q.model} via {r.provider} | {s['n']} examples", ""]
    lines.append(f"  accuracy     {s['accuracy']:.0%} ({s['correct']} of {s['n']})   95% interval {lo:.0%} to {hi:.0%}")
    if "cut" in s:
        c = s["cut"]
        if c["at_best"] > c["at_0.50"]:
            lines.append(f"  threshold    p(yes) >= 0.50 gives {c['at_0.50']:.0%}; best cut {c['best']:.2f} gives "
                         f"{c['at_best']:.0%} (fitted on these {s['n']}; confirm on new examples before moving it)")
        else:
            lines.append(f"  threshold    p(yes) >= 0.50 gives {c['at_0.50']:.0%}; no other cut does better on these examples")
    conf = s["confident"]
    if conf["accuracy"] is not None:
        lines.append(f"  confident    at >= {CONFIDENT:.2f} it answers {conf['coverage']:.0%} of inputs, "
                     f"{conf['accuracy']:.0%} of those right")
    else:
        lines.append(f"  confident    no answer reached {CONFIDENT:.2f}")
    if s["ece"] is not None:
        lines.append(f"  calibration  ECE {s['ece']:.3f} (bar {ECE_BAR:.2f})")
    b = s["blank"]
    lines.append(f"  blank input  answers {b['answer']!r} at {b['p']:.2f}; saying that to every example "
                 f"scores {b['accuracy_if_always']:.0%}; the model is "
                 f"{(s['accuracy'] - b['accuracy_if_always']) * 100:+.0f} points from that")
    if r.reworded:
        lines.append(f"  rewording    {s['flips']} of {r.reworded} answer(s) flipped ({', '.join(q.rewording)})")
    wrong = sorted((a for a in r.answers if a["answer"] != a["expect"] and a["p"] >= CONFIDENT),
                   key=lambda a: -a["p"])
    if wrong:
        lines += ["", "  sure and wrong (read these first: a wrong label, or the question's blind spot):"]
        for a in wrong[:SHOW_WRONG]:
            state = " ".join(a["state"].split())
            lines.append(f"    {a['answer']} at {a['p']:.2f}, expected {a['expect']}: {state[:90]!r}")
    for f in r.flips[:SHOW_WRONG]:
        lines.append(f"    flip: {f}")
    ok, failures, advice = verdict(q, s)
    lines.append("")
    for f in failures:
        lines.append(f"  FAIL  {f}")
    for a in advice:
        lines.append(f"  note  {a}")
    lines.append(f"  {'ready' if ok and not advice else 'passes its requirements' if ok else 'does not meet its requirements'}")
    if line_vs_last:
        lines.append(f"  {line_vs_last}")
    if saved:
        lines.append(f"  saved {saved}")
    lines.append(f"  tokens {r.tokens_in:,} in, {r.tokens_out:,} out")
    return "\n".join(lines)


def cmd_jev(args) -> int:
    """`dinostomp jev FILE`: exit 0 when the file's `require` holds (or it has
    none), 1 when a requirement fails, 2 when the file or the call is broken."""
    try:
        q = load_question(args.file)
    except QuestionFileError as exc:
        print(f"CANNOT RUN: {exc}", file=sys.stderr)
        return 2
    calls = len(q.examples) + 1 + (0 if args.no_rewording else
                                   min(REWORDING_SAMPLE, len(q.examples)) * len(q.rewording))
    print(f"{calls} call(s) to {args.model or q.model}", file=sys.stderr)

    def progress(done, total):
        print(f"  {done}/{total}", file=sys.stderr)

    try:
        r = run_question(q, provider_name=args.provider, model=args.model,
                         rewording=not args.no_rewording, progress=progress)
    except ProviderError as exc:
        print(f"CANNOT RUN: {exc}", file=sys.stderr)
        return 2
    s = summarize(r)
    saved = None if args.no_save else save_result(r, s)
    line = compare(previous_result(q, exclude=saved), r, s)
    print(render(r, s, saved, line))
    ok, _, _ = verdict(q, s)
    return 0 if ok else 1
