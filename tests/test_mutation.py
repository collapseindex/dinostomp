"""Mutation gauntlet tests. The gauntlet itself gets the house treatment:
prove each mutant is killable, prove survival is detected, prove
equivalent mutants are excluded rather than reported as unkillable."""

from pathlib import Path

from dinostomp.mutation import MUTANTS, run_gauntlet
from dinostomp.scorers import make_scorer

TEXT_ITEMS = [{"id": "t1", "input": "name the species?", "target": "setosa"}]
DIGIT_ITEMS = [{"id": "d1", "input": "12 + 45 = ?", "target": "57"}]

MINIMAL = [
    {"output": "setosa", "target": "setosa", "expect": "pass"},
    {"output": "versicolor", "target": "setosa", "expect": "fail"},
]

HARDENED = MINIMAL + [
    {"output": "It is setosa.", "target": "setosa", "expect": "fail"},   # kills substring-lenient
    {"output": "seto", "target": "setosa", "expect": "fail"},            # kills prefix-lenient
    {"output": "not setosa", "target": "setosa", "expect": "fail"},      # kills negation-blind
    {"output": "SETOSA", "target": "setosa", "expect": "fail"},          # kills case-blind
]


def exact():
    return make_scorer({"kind": "exact", "witnesses": []}, Path("."))


def numeric():
    return make_scorer({"kind": "numeric", "witnesses": []}, Path("."))


def names(mutants):
    return {m.name for m in mutants}


def test_minimal_witnesses_leave_survivors_with_suggestions():
    result = run_gauntlet(exact(), MINIMAL, TEXT_ITEMS)
    survivors = names(result.survived)
    assert "substring-lenient" in survivors
    assert "prefix-lenient" in survivors
    assert "negation-blind" in survivors
    assert all(m.suggestion for m in result.survived), "every survivor names the witness that kills it"


def test_hardened_witnesses_kill_every_applicable_mutant():
    result = run_gauntlet(exact(), HARDENED, TEXT_ITEMS)
    assert result.survived == [], [m.name for m in result.survived]
    assert result.n_applicable >= 6


def test_constant_mutants_always_die():
    result = run_gauntlet(exact(), MINIMAL, TEXT_ITEMS)
    assert "always-pass" in result.killed, "an expect:fail witness must kill always-pass"
    assert "always-fail" in result.killed, "an expect:pass witness must kill always-fail"


def test_case_blind_is_na_on_digit_targets():
    result = run_gauntlet(exact(), MINIMAL, DIGIT_ITEMS)
    assert "case-blind" in result.not_applicable, "equivalent mutants are excluded, not unkillable"


def test_space_blind_applicability_follows_targets():
    spaced = [{"id": "s1", "input": "q?", "target": "new york"}]
    result = run_gauntlet(exact(), MINIMAL, spaced)
    assert "space-blind" not in result.not_applicable, "spaced targets make the mutant meaningful"
    result_digits = run_gauntlet(exact(), MINIMAL, DIGIT_ITEMS)
    assert "space-blind" in result_digits.not_applicable


def test_uncheckable_credit_na_for_exact_but_live_for_numeric():
    assert "uncheckable-credit" in run_gauntlet(exact(), MINIMAL, TEXT_ITEMS).not_applicable

    digit_witnesses = [
        {"output": "57", "target": "57", "expect": "pass"},
        {"output": "58", "target": "57", "expect": "fail"},
    ]
    live = run_gauntlet(numeric(), digit_witnesses, DIGIT_ITEMS)
    assert "uncheckable-credit" in names(live.survived), "no uncheckable witness: the mutant survives"

    pinned = digit_witnesses + [{"output": "no digits here", "target": "57", "expect": "uncheckable"}]
    killed = run_gauntlet(numeric(), pinned, DIGIT_ITEMS)
    assert "uncheckable-credit" in killed.killed, "expect: uncheckable is exactly what kills this mutant"


def test_negation_blind_na_when_scorer_already_ignores_negation():
    """A numeric scorer extracts the first number, so 'not 46' already scores
    pass: the negation-blind mutant is behaviorally equivalent and must be
    n/a, not an unkillable permanent warning."""
    digit_witnesses = [
        {"output": "46", "target": "46", "expect": "pass"},
        {"output": "48", "target": "46", "expect": "fail"},
    ]
    result = run_gauntlet(numeric(), digit_witnesses, DIGIT_ITEMS)
    assert "negation-blind" in result.not_applicable

    exact_result = run_gauntlet(exact(), MINIMAL, TEXT_ITEMS)
    assert "negation-blind" not in exact_result.not_applicable, "exact scorers CAN reject negation"


def test_every_mutant_has_distinct_name_and_bug_class():
    assert len({m.name for m in MUTANTS}) == len(MUTANTS)
    assert all(m.bug_class for m in MUTANTS)
