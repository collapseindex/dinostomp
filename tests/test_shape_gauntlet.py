"""W2, the response-shape gauntlet.

Same house treatment as W1: prove each shape fires on a scorer that really has
that bug, prove a sound scorer comes back clean, and prove the guards exclude
scorers the shape cannot fairly judge. A check that cannot fail is decoration,
so every defect below is a working reproduction of one found in the wild, not a
hypothetical.
"""

import re
from pathlib import Path

from dinostomp.mutation import SHAPES, run_shape_gauntlet
from dinostomp.scorers import ScoreResult, make_scorer

TEXT = [{"id": f"t{i}", "input": "q", "target": t}
        for i, t in enumerate(["SETOSA", "VERSICOLOR", "VIRGINICA", "CANDIDUM"])]
NUM = [{"id": f"n{i}", "input": "q", "target": t} for i, t in enumerate(["57", "12", "340", "9"])]

LABEL = re.compile(r"answer\s*[:：]\s*(.+)", re.IGNORECASE)


def _payload(output):
    m = LABEL.search(output)
    return (m.group(1) if m else output).strip()


def sound(output, target):
    """Extracts the last labelled answer, compares case-insensitively."""
    hits = LABEL.findall(output)
    got = (hits[-1] if hits else output).strip().rstrip(".").strip("* ")
    return ScoreResult("pass" if got.upper() == str(target).upper() else "fail", evidence=got)


def lost(result):
    return {s.name for s in result.lost}


def leaked(result):
    return {s.name for s in result.leaked}


def test_a_sound_scorer_holds_every_shape():
    result = run_shape_gauntlet(sound, TEXT)
    assert result.form == "labelled"
    assert not result.lost and not result.leaked, f"false alarm: {lost(result)} {leaked(result)}"
    assert result.n_applicable >= 5


def test_case_sensitive_extraction_under_case_blind_comparison_is_caught():
    """N-2 in the wild: the comparison uppercased both sides, so case was meant
    not to matter, but the fallback that had to run first was case-sensitive and
    returned nothing, leaving that leniency permanently unreachable."""
    def buggy(output, target):
        got = _payload(output)
        if not re.search(r"\b[A-Z]{3,}\b", got):     # case-SENSITIVE extraction
            return ScoreResult("fail", evidence="no answer extracted")
        return ScoreResult("pass" if got.upper() == str(target).upper() else "fail", evidence=got)

    assert "answer-case" in lost(run_shape_gauntlet(buggy, TEXT))


def test_case_policy_alone_is_not_reported():
    """A scorer that requires exact case is making a choice, not a mistake. The
    shape must only fire on the INCONSISTENCY, never on the policy."""
    def strict(output, target):
        return ScoreResult("pass" if _payload(output) == str(target) else "fail", evidence="")

    result = run_shape_gauntlet(strict, TEXT)
    assert "answer-case" in result.not_applicable
    assert "answer-case" not in lost(result)


def test_first_match_extraction_is_caught():
    """N-1: the question states a value from the answer space, the model
    restates it while working, and the scorer grades that instead."""
    def first_match(output, target):
        hits = LABEL.findall(output)
        got = (hits[0] if hits else output).strip()
        return ScoreResult("pass" if got.upper() == str(target).upper() else "fail", evidence=got)

    def first_number(output, target):
        found = re.findall(r"-?\d+(?:\.\d+)?", output)
        if not found:
            return ScoreResult("uncheckable", evidence="")
        return ScoreResult("pass" if abs(float(found[0]) - float(target)) < 1e-9 else "fail", evidence="")

    assert "reasoning-prefix" in lost(run_shape_gauntlet(first_number, NUM))
    # The labelled variant needs the decoy to reach the first label, so use a
    # scorer that keys off the first label-like match anywhere in the response.
    def first_label_anywhere(output, target):
        m = re.search(r"(?:answer|value)\s*[:\s]\s*(\S+)", output, re.IGNORECASE)
        got = (m.group(1) if m else output).strip().rstrip(".")
        return ScoreResult("pass" if got.upper() == str(target).upper() else "fail", evidence=got)

    assert "reasoning-prefix" in lost(run_shape_gauntlet(first_label_anywhere, TEXT))


def test_zero_width_separator_is_caught():
    """N-3: `[:\\s]*` matches the empty string, so a keyword in prose captures
    the next word. 'the answer is X' yields 'IS'."""
    def zero_width(output, target):
        m = re.search(r"answer[:\s]*([A-Za-z]+)", output, re.IGNORECASE)
        got = (m.group(1) if m else "").strip()
        return ScoreResult("pass" if got.upper() == str(target).upper() else "fail", evidence=got)

    assert "keyword-in-prose" in lost(run_shape_gauntlet(zero_width, TEXT))


def test_scavenging_the_working_is_caught():
    """Found in our OWN repair of another benchmark: when the answer line could
    not be read, the fallback scanned the reasoning and credited a matching
    string, inventing a point the model never earned."""
    def scavenger(output, target):
        hits = LABEL.findall(output)
        if not hits:
            # Not substring-lenient: with no label at all it credits nothing.
            # The bug is narrower, and nastier, than that.
            return ScoreResult("fail", evidence="no labelled answer")
        got = hits[-1].strip()
        if got.upper() == str(target).upper():
            return ScoreResult("pass", evidence=got)
        if str(target).upper() in output.upper():     # the label failed: scavenge the working
            return ScoreResult("pass", evidence="found in reasoning")
        return ScoreResult("fail", evidence=got)

    assert "decoy-in-working" in leaked(run_shape_gauntlet(scavenger, TEXT))


def test_substring_lenient_scorers_skip_the_decoy_arm():
    """A scorer that credits the target loose in prose is substring-lenient by
    construction. The decoy arm cannot separate scavenging from that declared
    behaviour, so demanding it fail would be homework that cannot be done."""
    result = run_shape_gauntlet(make_scorer({"kind": "includes", "witnesses": []}, Path(".")), TEXT)
    assert "decoy-in-working" in result.not_applicable
    assert not result.leaked


def test_a_strict_comparator_is_out_of_scope():
    """`exact` rejects 'SETOSA.' on purpose. Every shape would fire on it, so
    the whole check is n/a rather than a page of false alarms."""
    result = run_shape_gauntlet(make_scorer({"kind": "exact", "witnesses": []}, Path(".")), TEXT)
    assert result.n_applicable == 0
    assert len(result.not_applicable) == len(SHAPES)


def test_the_shipped_numeric_default_is_flagged_and_the_knob_clears_it():
    """extract:first is the shipped default and it grades the working. This is
    the same bug class R16 catches from failed records AFTER a paid run; W2
    catches it from the scorer alone, before spending anything."""
    first = make_scorer({"kind": "numeric", "witnesses": [], "params": {}}, Path("."))
    last = make_scorer({"kind": "numeric", "witnesses": [], "params": {"extract": "last"}}, Path("."))
    assert "reasoning-prefix" in lost(run_shape_gauntlet(first, NUM))
    assert not run_shape_gauntlet(last, NUM).lost


def test_every_shape_carries_a_repair_suggestion():
    assert all(s.suggestion and s.bug_class for s in SHAPES)
