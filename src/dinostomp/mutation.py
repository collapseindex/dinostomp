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


# ---------------------------------------------------------------------------
# W2: the same idea pointed the other way.
#
# W1 mutates the SCORER and asks whether the witnesses would notice it getting
# more permissive. That only ever catches a scorer crediting too much. The
# opposite bug is invisible to it: a scorer that loses a CORRECT answer because
# of the shape it arrived in. Observed in the wild, all in one afternoon on one
# public benchmark:
#
#   * extraction stricter than comparison. The comparison uppercased both sides,
#     so case was meant not to matter, but the extractor's fallback was
#     case-sensitive and returned nothing, so the lenient comparison was
#     unreachable and a correct lowercase answer scored zero.
#   * first-match extraction. The question stated a value from the answer space,
#     the model restated it while reasoning, and the scorer graded that instead
#     of the answer: it graded its own input.
#   * a label pattern whose separator could match ZERO characters, so a keyword
#     in ordinary prose captured the following token ("the answer is X" -> "IS").
#   * an extractor restricted to one script, unable to read an answer written in
#     another, returning nothing rather than reading it.
#
# So W2 perturbs the RESPONSE in ways that must not change a correct verdict,
# and pairs them with a decoy that must still fail. Without that decoy arm a
# scorer could pass W2 by crediting everything, which is the exact bug W1 exists
# to catch. The two checks have to be able to fail in opposite directions.
#
# W2 never demands a leniency POLICY. It only demands consistency: if a form is
# accepted, trivial surface variants of THAT SAME form must be accepted too.
# Requiring `Answer:` is a legitimate design choice; accepting `Answer: X` while
# rejecting `Answer: X.` is not a choice anyone made on purpose.
# ---------------------------------------------------------------------------

DECOY_NOTE = "the value {decoy} came up while working"


@dataclass(frozen=True)
class Shape:
    name: str
    bug_class: str
    render: Callable[[Callable[[str], str], str, str], str]  # (form, target, decoy) -> response
    expect: str
    suggestion: str
    needs_alpha: bool = False


@dataclass
class ShapeResult:
    form: str = ""                                  # which baseline form was accepted
    lost: list[Shape] = field(default_factory=list)      # should pass, did not
    leaked: list[Shape] = field(default_factory=list)    # should fail, passed
    held: list[str] = field(default_factory=list)
    not_applicable: list[str] = field(default_factory=list)

    @property
    def n_applicable(self) -> int:
        return len(self.held) + len(self.lost) + len(self.leaked)

    @property
    def clean(self) -> bool:
        return not self.lost and not self.leaked


SHAPES: list[Shape] = [
    Shape("trailing-punctuation", "loses an answer to a full stop",
          lambda form, t, d: form(t) + ".", "pass",
          "accept a trailing '.' after the answer, or state that punctuation is significant"),
    Shape("surrounding-whitespace", "loses an answer to a stray newline",
          lambda form, t, d: "\n  " + form(t) + "  \n", "pass",
          "strip the response before extracting"),
    Shape("markdown-emphasis", "loses an answer a model wrote in bold",
          lambda form, t, d: form(t).replace("Answer:", "**Answer:**", 1), "pass",
          "tolerate markdown around the label"),
    Shape("label-case", "accepts 'Answer:' but not 'answer:'",
          lambda form, t, d: form(t).replace("Answer:", "answer:", 1), "pass",
          "match the label case-insensitively"),
    Shape("answer-case", "extraction is stricter about case than comparison is",
          lambda form, t, d: form(t.lower()), "pass",
          "make the extractor's fallback as case-insensitive as the comparison, "
          "or reject case mismatches in the comparison too", needs_alpha=True),
    # The label keyword appears in ordinary prose BEFORE the real answer line.
    # A label pattern whose separator can match zero characters captures the
    # next token instead: "the answer is X" yields "is".
    Shape("keyword-in-prose", "a label pattern with a zero-width separator captures the next word",
          lambda form, t, d: f"Working through it, the answer is derived below.\n{form(t)}", "pass",
          "require an explicit separator after the label keyword, so prose cannot "
          "look like a label"),
    Shape("reasoning-prefix", "grades the input: an answer-space value stated before the answer",
          lambda form, t, d: f"{DECOY_NOTE.format(decoy=d)}.\n{form(t)}", "pass",
          "extract from the LAST labelled answer, not the first match in the response"),
    # The negative arm. Correct answer in the prose, WRONG answer in the label.
    # A scorer that scavenges the working to rescue an unreadable label credits
    # this, inventing a point the model never earned.
    Shape("decoy-in-working", "scavenges the working when the answer line is unreadable",
          lambda form, t, d: f"{DECOY_NOTE.format(decoy=t)}.\n{form(d)}", "fail",
          "when a labelled answer cannot be read, report it unread rather than "
          "falling back to scanning the reasoning"),
]


def _verdict(scorer: Scorer, output: str, target: Any) -> str:
    try:
        return scorer(output, target).verdict
    except Exception:  # noqa: BLE001 - a scorer that crashes on a shape has lost the answer
        return "error"


def run_shape_gauntlet(scorer: Scorer, items: list[dict], sample: int = 12) -> ShapeResult:
    """Probe whether a correct answer survives a change of surface form.

    Establishes a baseline form the scorer already accepts, then perturbs it.
    Everything is measured against that baseline, so a scorer that legitimately
    demands a strict format is judged on its own terms rather than ours.
    """
    result = ShapeResult()
    pairs: list[tuple[str, str]] = []
    seen: set[str] = set()
    for item in items:
        for t in _targets(item["target"]):
            if t.strip() and t not in seen:
                seen.add(t)
                pairs.append((t, item))
        if len(pairs) >= sample:
            break
    targets = [t for t, _ in pairs][:sample]
    if len(targets) < 2:
        result.not_applicable = [s.name for s in SHAPES]
        return result

    # Only EXTRACTING scorers are in scope. A scorer that demands the bare
    # string is a comparator, not a parser: it rejects "setosa." on purpose, and
    # every shape below would fire on it as a false alarm. The bugs W2 hunts
    # live in extraction, so the entry condition is that the scorer can find an
    # answer inside a labelled line at all.
    def form(t: str) -> str:
        return f"Answer: {t}"

    if not all(_verdict(scorer, form(t), t) == "pass" for t in targets):
        result.not_applicable = [s.name for s in SHAPES]
        return result
    result.form = "labelled"

    # `answer-case` must not demand case-insensitivity as a POLICY: requiring
    # exact case is a legitimate choice. What it hunts is the INCONSISTENCY seen
    # in the wild, where the comparison lowercased both sides (so case was meant
    # not to matter) while the extractor's fallback stayed case-sensitive and
    # returned nothing, leaving the lenient comparison unreachable. That is
    # visible from outside: bare-lowercase passes, labelled-lowercase does not.
    # Probing with a lowercase OUTPUT cannot work: a case-sensitive extractor
    # blocks that too, so the bug would hide the evidence of itself and the
    # shape would exclude the exact scorer it exists for. Vary the TARGET's case
    # instead, leaving the output in the form extraction already accepts. That
    # isolates the comparison from the extraction.
    cased = [t for t in targets if t != t.lower()]
    case_blind_comparison = bool(cased) and all(
        _verdict(scorer, form(t), t.lower()) == "pass" for t in cased)
    # A scorer that already credits the target sitting loose in prose is
    # substring-lenient by construction. The decoy arm cannot then tell
    # scavenging apart from that declared behaviour, and demanding it fail would
    # be an impossible homework assignment. W1's substring-lenient mutant is
    # where that design gets examined; here it is n/a.
    prose_lenient = any(_verdict(scorer, DECOY_NOTE.format(decoy=t) + ".", t) == "pass"
                        for t in targets)
    for shape in SHAPES:
        if shape.expect == "fail" and prose_lenient:
            result.not_applicable.append(shape.name)
            continue
        if shape.needs_alpha and not case_blind_comparison:
            result.not_applicable.append(shape.name)
            continue
        bad = False
        for i, t in enumerate(targets):
            decoy = targets[(i + 1) % len(targets)]
            if decoy == t:
                continue
            verdict = _verdict(scorer, shape.render(form, t, decoy), t)
            if shape.expect == "pass" and verdict != "pass":
                bad = True
                break
            if shape.expect == "fail" and verdict == "pass":
                bad = True
                break
        if not bad:
            result.held.append(shape.name)
        elif shape.expect == "pass":
            result.lost.append(shape)
        else:
            result.leaked.append(shape)
    return result


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
