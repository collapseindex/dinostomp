"""Witness mutation testing: measuring what the witness gate actually proves.

The gate proves a scorer CAN fail. This module measures whether the witnesses
would notice a scorer that fails WRONG: each mutant below is a plausible
buggy variant of the real scorer, embodying a scoring-bug class observed in
the wild. A mutant is KILLED when at least one witness catches it giving a
verdict the spec did not expect. A mutant that sails through the whole
witness suite is a blind spot, reported with the witness that would close it.

Equivalent mutants are excluded per dataset: case-blindness cannot matter to
numeric targets, so it is n/a there rather than an unkillable false alarm.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from dinostomp.scorers import ScoreResult, Scorer


NEGATION_RE = re.compile(r"^\s*(?:not|no|never|hardly|unlikely)\s+", re.IGNORECASE)
UNCHECKABLE_PROBE = "⁇ no parseable answer here ⁇"


def _targets(target: Any) -> list[str]:
    if isinstance(target, list):
        return [str(t) for t in target]
    return [str(target)]


@dataclass(frozen=True)
class Mutant:
    name: str
    bug_class: str
    wrap: Callable[[Scorer], Scorer]
    suggestion: str  # the witness that would kill this mutant


@dataclass
class GauntletResult:
    killed: list[str] = field(default_factory=list)
    survived: list[Mutant] = field(default_factory=list)
    not_applicable: list[str] = field(default_factory=list)

    @property
    def n_applicable(self) -> int:
        return len(self.killed) + len(self.survived)


def _always(verdict: str) -> Callable[[Scorer], Scorer]:
    def wrap(scorer: Scorer) -> Scorer:
        return lambda output, target: ScoreResult(verdict, evidence="mutant: constant verdict")
    return wrap


def _case_blind(scorer: Scorer) -> Scorer:
    def mutant(output: str, target: Any) -> ScoreResult:
        t = [x.lower() for x in target] if isinstance(target, list) else str(target).lower()
        return scorer(output.lower(), t)
    return mutant


def _space_blind(scorer: Scorer) -> Scorer:
    def mutant(output: str, target: Any) -> ScoreResult:
        collapse = lambda s: " ".join(str(s).split())
        t = [collapse(x) for x in target] if isinstance(target, list) else collapse(target)
        return scorer(collapse(output), t)
    return mutant


def _substring_lenient(scorer: Scorer) -> Scorer:
    def mutant(output: str, target: Any) -> ScoreResult:
        result = scorer(output, target)
        if result.verdict == "fail" and any(t and t in output for t in _targets(target)):
            return ScoreResult("pass", evidence="mutant: target appears inside the output")
        return result
    return mutant


def _prefix_lenient(scorer: Scorer) -> Scorer:
    def mutant(output: str, target: Any) -> ScoreResult:
        result = scorer(output, target)
        got = output.strip()
        if result.verdict == "fail" and got and any(t.startswith(got) for t in _targets(target)):
            return ScoreResult("pass", evidence="mutant: output is a prefix of the target")
        return result
    return mutant


def _negation_blind(scorer: Scorer) -> Scorer:
    def mutant(output: str, target: Any) -> ScoreResult:
        return scorer(NEGATION_RE.sub("", output), target)
    return mutant


def _uncheckable_credit(scorer: Scorer) -> Scorer:
    def mutant(output: str, target: Any) -> ScoreResult:
        result = scorer(output, target)
        if result.verdict == "uncheckable":
            return ScoreResult("pass", evidence="mutant: uncheckable credited as pass")
        return result
    return mutant


MUTANTS: list[Mutant] = [
    Mutant("always-pass", "credits everything",
           _always("pass"), "(any expect: fail witness kills this; its survival means the gauntlet itself is broken)"),
    Mutant("always-fail", "credits nothing",
           _always("fail"), "(any expect: pass witness kills this; its survival means the gauntlet itself is broken)"),
    Mutant("case-blind", "ignores letter case",
           _case_blind, "a witness whose output differs from the target only by case, expect: fail (or pass, if case should not matter: then say so)"),
    Mutant("space-blind", "ignores whitespace differences",
           _space_blind, "a witness whose output differs from the target only by a RUN of internal "
           "whitespace (e.g. a doubled space), with the expected verdict pinned"),
    Mutant("substring-lenient", "credits the target appearing inside prose",
           _substring_lenient, "a witness embedding the target in a sentence, expect: fail"),
    Mutant("prefix-lenient", "credits a truncated answer",
           _prefix_lenient, "a witness giving a strict prefix of the target, expect: fail"),
    Mutant("negation-blind", "credits a negated answer",
           _negation_blind, "a witness like 'not <target>', expect: fail"),
    Mutant("uncheckable-credit", "silently converts uncheckable into pass",
           _uncheckable_credit, "a witness with an unparseable output, expect: uncheckable"),
]


def _applicable(mutant: Mutant, scorer: Scorer, items: list[dict]) -> bool:
    """Exclude mutants that are equivalent on this dataset's target space, or
    behaviorally equivalent to the scorer itself (a numeric scorer that
    extracts the first number already ignores 'not '; the negation-blind
    mutant is then indistinguishable and no legal witness could kill it)."""
    all_targets = [t for i in items for t in _targets(i["target"])]

    def distinguishes(transform) -> bool:
        """Does this scorer treat the transformed output differently at all?

        If not, the mutant is behaviorally identical to the scorer and NO legal
        witness could kill it. Reporting it as a survivor would be a false
        alarm demanding a witness that cannot exist, which is worse than not
        running the mutant: it teaches authors to distrust the gauntlet.
        """
        try:
            return any(scorer(transform(t), t).verdict != scorer(t, t).verdict
                       for t in all_targets[:20] if t.strip())
        except Exception:  # noqa: BLE001 - probes must never crash the gauntlet
            return True

    def can_trigger(transform) -> bool:
        """The leniency mutants only upgrade a FAIL. If the scorer answers
        `uncheckable` (or already passes) on the shape they would upgrade, they
        can never fire, and again no witness could kill them. Probing the
        mutant's actual trigger is the difference between a real blind spot and
        an impossible homework assignment."""
        try:
            return any(scorer(transform(t), t).verdict == "fail"
                       for t in all_targets[:20] if t.strip())
        except Exception:  # noqa: BLE001 - probes must never crash the gauntlet
            return True

    if mutant.name == "case-blind":
        # A scorer that grades meaning is case-insensitive on purpose; only ask
        # for a case witness where case actually changes this scorer's mind.
        return (any(c.isalpha() for t in all_targets for c in t)
                and distinguishes(lambda t: t.swapcase()))
    if mutant.name == "space-blind":
        return any(" " in t.strip() for t in all_targets)
    if mutant.name == "prefix-lenient":
        return (any(len(t.strip()) >= 2 for t in all_targets)
                and can_trigger(lambda t: t.strip()[:-1]))
    if mutant.name == "substring-lenient":
        return can_trigger(lambda t: f"the answer is {t}")
    if mutant.name == "uncheckable-credit":
        try:
            return scorer(UNCHECKABLE_PROBE, all_targets[0] if all_targets else "x").verdict == "uncheckable"
        except Exception:  # noqa: BLE001 - a crashing probe means no uncheckable path to credit
            return False
    if mutant.name == "negation-blind":
        # Applicable only if stripping a negator can change the verdict at all.
        try:
            return any(scorer(f"not {t}", t).verdict != scorer(t, t).verdict
                       for t in all_targets[:20])
        except Exception:  # noqa: BLE001 - probes must never crash the gauntlet
            return True
    return True


def run_gauntlet(scorer: Scorer, witnesses: list[dict], items: list[dict]) -> GauntletResult:
    """Run every applicable mutant against the witness suite.

    A mutant is killed when some witness gets a verdict other than its
    expected one under the mutant (the witness would have flagged the bug).
    """
    result = GauntletResult()
    for mutant in MUTANTS:
        if not _applicable(mutant, scorer, items):
            result.not_applicable.append(mutant.name)
            continue
        mutated = mutant.wrap(scorer)
        caught = False
        for w in witnesses:
            try:
                verdict = mutated(w["output"], w["target"]).verdict
            except Exception:  # noqa: BLE001 - a mutant that crashes on a witness is caught
                caught = True
                break
            if verdict != w["expect"]:
                caught = True
                break
        if caught:
            result.killed.append(mutant.name)
        else:
            result.survived.append(mutant)
    return result
