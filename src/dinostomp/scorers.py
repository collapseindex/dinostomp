"""Built-in scorers and the witness gate.

A scorer maps (output, target) to a verdict: pass, fail, or uncheckable.
Uncheckable means the scorer could not extract anything to judge; it is
excluded from every denominator downstream, never silently counted.

The witness gate is the core rule of the toolkit: before a scorer touches
real data, it must reproduce the spec's witness cases, including at least
one it must fail. A witness that comes back uncheckable never counts as
behaved; witnesses must be decisive by construction.
"""

from __future__ import annotations

import importlib.util
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")
# Choice extraction, in priority order. The bare-letter fallback searches the
# ORIGINAL case and only A-H: uppercasing first would turn the words "I" and
# "a" into winning candidates ("I think the answer is B" must extract B).
CHOICE_LONE = re.compile(r"^\W*([A-Za-z])\W*$")
# The stated letter must be followed by punctuation or end-of-text, else the
# article in "the answer is a tricky one" wins the capture.
CHOICE_STATED = re.compile(
    r"(?:answer|option|choice)\s*(?:is)?\s*[:\-]?\s*\(?([A-Za-z])\)?(?=\s*(?:[.,;:!?]|$))",
    re.IGNORECASE,
)
CHOICE_BARE = re.compile(r"\b([A-H])\b")


@dataclass(frozen=True)
class ScoreResult:
    verdict: str  # "pass" | "fail" | "uncheckable"
    evidence: str = ""
    value: float | None = None

    def to_dict(self) -> dict:
        out: dict[str, Any] = {"verdict": self.verdict}
        if self.evidence:
            out["evidence"] = self.evidence
        if self.value is not None:
            out["value"] = self.value
        return out


Scorer = Callable[[str, Any], ScoreResult]


def _targets(target: Any) -> list[str]:
    if isinstance(target, list):
        return [str(t) for t in target]
    return [str(target)]


def _exact(output: str, target: Any) -> ScoreResult:
    got = output.strip()
    for t in _targets(target):
        if got == t.strip():
            return ScoreResult("pass", evidence=f"exact match: {t.strip()!r}")
    return ScoreResult("fail", evidence=f"output {got[:80]!r} != target")


def _includes(output: str, target: Any) -> ScoreResult:
    for t in _targets(target):
        if t in output:
            return ScoreResult("pass", evidence=f"contains {t!r}")
    return ScoreResult("fail", evidence="target substring absent")


def _numeric_factory(params: dict) -> Scorer:
    tolerance = float(params.get("tolerance", 1e-6))
    # Which number is the answer. `first` is the default because it is the
    # conservative reading of "reply with the number", but it is a trap on any
    # model that shows its working: "12*3=36, 8*5=40, 36+40=76" starts with 12.
    # Found live, where it scored a model 0.000 whose real accuracy was 0.438
    # and ranked it LAST in a fleet it actually led. R16 detects the symptom;
    # this is the knob that fixes it.
    which = str(params.get("extract", "first")).lower()

    def numeric(output: str, target: Any) -> ScoreResult:
        found = NUMBER_RE.findall(output)
        if not found:
            return ScoreResult("uncheckable", evidence="no number found in output")
        raw = found[-1] if which == "last" else found[0]
        got = float(raw)
        wants = []
        for t in _targets(target):
            try:
                wants.append(float(t))
            except ValueError:
                continue
        if not wants:
            return ScoreResult("uncheckable", evidence=f"no numeric target among {target!r}")
        ok = any(abs(got - w) <= tolerance for w in wants)
        return ScoreResult(
            "pass" if ok else "fail",
            evidence=f"extracted {raw} ({which} of {len(found)}) vs target(s) {wants} "
                     f"(tol {tolerance:g})",
        )

    return numeric


def _extract_choice(output: str) -> tuple[str | None, str]:
    """(letter, how). Priority: lone letter, stated answer, bare A-H."""
    m = CHOICE_LONE.match(output.strip())
    if m:
        return m.group(1).upper(), "lone letter"
    m = CHOICE_STATED.search(output)
    if m:
        return m.group(1).upper(), "stated answer"
    m = CHOICE_BARE.search(output)
    if m:
        return m.group(1), "bare letter"
    return None, "no choice letter found (lone, stated, or bare A-H)"


def _choice(output: str, target: Any) -> ScoreResult:
    got, how = _extract_choice(output)
    if got is None:
        return ScoreResult("uncheckable", evidence=how)
    wants = {t.strip().upper() for t in _targets(target)}
    return ScoreResult(
        "pass" if got in wants else "fail",
        evidence=f"extracted {got} ({how}) vs target {'/'.join(sorted(wants))}",
    )


def _regex_factory(params: dict) -> Scorer:
    pattern = params.get("pattern")
    if not isinstance(pattern, str) or not pattern:
        raise ValueError("regex scorer requires params.pattern")
    compiled = re.compile(pattern, re.DOTALL)

    def regex(output: str, target: Any) -> ScoreResult:
        m = compiled.search(output)
        if not m:
            return ScoreResult("uncheckable", evidence=f"pattern {pattern!r} did not match")
        raw = m.group(1) if m.groups() else m.group(0)
        if raw is None:  # optional group matched nothing
            return ScoreResult("uncheckable", evidence=f"pattern {pattern!r} matched but its group captured nothing")
        got = raw.strip()
        for t in _targets(target):
            if got == t.strip():
                return ScoreResult("pass", evidence=f"extracted {got!r}")
        return ScoreResult("fail", evidence=f"extracted {got!r} != target")

    return regex


def _python_factory(code_path: Path) -> Scorer:
    """Load score(output, target) from a user's python file.

    The file is the spec author's own code on their own machine; dinostomp
    runs it exactly as pytest would run their tests.
    """
    spec = importlib.util.spec_from_file_location("dinostomp_user_scorer", code_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load scorer module: {code_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fn = getattr(module, "score", None)
    if not callable(fn):
        raise ValueError(f"{code_path} must define score(output, target)")

    def python_scorer(output: str, target: Any) -> ScoreResult:
        # A user scorer must never kill a paid run mid-flight: any surprise
        # (bad return type, exception on a rare branch) degrades to
        # uncheckable, which is excluded from denominators and surfaces in
        # the uncheckable-rate check instead of a traceback after spend.
        try:
            result = fn(output, target)
        except Exception as exc:  # noqa: BLE001 - user code, by design
            logger.warning("user scorer raised: %s", exc)
            return ScoreResult("uncheckable", evidence=f"user scorer raised {type(exc).__name__}: {exc}")
        if isinstance(result, ScoreResult):
            return result
        if isinstance(result, bool):
            return ScoreResult("pass" if result else "fail", evidence="user scorer boolean")
        if result is None:
            return ScoreResult("uncheckable", evidence="user scorer returned None")
        return ScoreResult(
            "uncheckable",
            evidence=f"user scorer returned {type(result).__name__}, expected bool, None, or ScoreResult",
        )

    return python_scorer


def make_scorer(cfg: dict, base_dir: Path) -> Scorer:
    """Build a scorer from a validated spec's scorer block."""
    kind = cfg["kind"]
    params = cfg.get("params") or {}
    if kind == "exact":
        return _exact
    if kind == "includes":
        return _includes
    if kind == "numeric":
        return _numeric_factory(params)
    if kind == "choice":
        return _choice
    if kind == "regex":
        return _regex_factory(params)
    if kind == "python":
        return _python_factory(base_dir / cfg["code"])
    if kind == "judge":
        from dinostomp.judging import JudgeScorer  # local: judging imports ScoreResult from here

        return JudgeScorer(cfg, base_dir)
    raise ValueError(f"unknown scorer kind: {kind!r}")


@dataclass
class WitnessReport:
    n_witnesses: int
    n_behaved: int
    verdict: str  # "validated" | "failed"
    failures: list[dict] = field(default_factory=list)

    def to_manifest(self) -> dict:
        return {"n_witnesses": self.n_witnesses, "n_behaved": self.n_behaved, "verdict": self.verdict}


def run_witnesses(scorer: Scorer, witnesses: list[dict]) -> WitnessReport:
    """Execute every witness case. Strict: a witness must land exactly on its
    expected verdict, including expect: uncheckable, which pins how the
    scorer behaves on unparseable output."""
    failures = []
    behaved = 0
    for i, w in enumerate(witnesses):
        result = scorer(w["output"], w["target"])
        if result.verdict == w["expect"]:
            behaved += 1
        else:
            failures.append(
                {
                    "index": i,
                    "output": w["output"],
                    "target": w["target"],
                    "expected": w["expect"],
                    "got": result.verdict,
                    "evidence": result.evidence,
                    "why": w.get("why", ""),
                }
            )
    verdict = "validated" if behaved == len(witnesses) else "failed"
    return WitnessReport(len(witnesses), behaved, verdict, failures)
