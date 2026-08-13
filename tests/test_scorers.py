"""Scorer and witness-gate tests. Each scorer kind gets its own must-fail
and must-uncheckable cases; the gate gets tests proving it fires."""

from pathlib import Path

import pytest

from dinostomp.scorers import ScoreResult, make_scorer, run_witnesses


def scorer(kind, params=None, base=None, code=None):
    cfg = {"kind": kind, "witnesses": []}
    if params:
        cfg["params"] = params
    if code:
        cfg["code"] = code
    return make_scorer(cfg, base or Path("."))


# --- kinds ---------------------------------------------------------------------


def test_exact():
    s = scorer("exact")
    assert s("57", "57").verdict == "pass"
    assert s("  57  ", "57").verdict == "pass"
    assert s("The answer is 57", "57").verdict == "fail"
    assert s("57", ["56", "57"]).verdict == "pass"


def test_includes():
    s = scorer("includes")
    assert s("I think it is 57.", "57").verdict == "pass"
    assert s("I think it is 58.", "57").verdict == "fail"


def test_numeric_tolerance_and_uncheckable():
    s = scorer("numeric", params={"tolerance": 0.5})
    assert s("the result is 57.3", "57").verdict == "pass"
    assert s("the result is 58.1", "57").verdict == "fail"
    assert s("no digits here", "57").verdict == "uncheckable"
    assert s("57", "not a number").verdict == "uncheckable"


def test_choice():
    s = scorer("choice")
    assert s("The answer is B.", "b").verdict == "pass"
    assert s("answer: C", "B").verdict == "fail"
    assert s("no letters that stand alone", "B").verdict == "uncheckable"


def test_choice_survives_prose_pronouns():
    """The old extractor uppercased first, so 'I' and 'a' won: the single
    worst wrong-verdict bug the review found."""
    s = scorer("choice")
    assert s("I think the answer is B.", "B").verdict == "pass"
    assert s("The answer is a tricky one, so B", "B").verdict == "pass"
    assert s("A) is wrong, B) is right... just kidding, A.", "A").verdict == "pass"
    assert s("(C)", "C").verdict == "pass"
    assert s("b", "B").verdict == "pass"
    assert s("I believe D fits", "D").verdict == "pass"


def test_choice_multi_target():
    s = scorer("choice")
    assert s("B", ["B", "C"]).verdict == "pass"
    assert s("D", ["B", "C"]).verdict == "fail"


def test_regex_extracts_group():
    s = scorer("regex", params={"pattern": r"ANSWER:\s*(\w+)"})
    assert s("blah ANSWER: dog", "dog").verdict == "pass"
    assert s("blah ANSWER: cat", "dog").verdict == "fail"
    assert s("no marker at all", "dog").verdict == "uncheckable"


def test_regex_requires_pattern():
    with pytest.raises(ValueError):
        scorer("regex", params={})


def test_regex_optional_group_is_uncheckable_not_a_crash():
    s = scorer("regex", params={"pattern": r"ANSWER:\s*(\d+)?"})
    result = s("ANSWER: ", "57")
    assert result.verdict == "uncheckable"
    assert "captured nothing" in result.evidence


def test_python_scorer_crash_is_uncheckable_not_fatal(tmp_path):
    code = tmp_path / "angry.py"
    code.write_text(
        "def score(output, target):\n"
        "    if 'boom' in output:\n"
        "        raise RuntimeError('rare branch')\n"
        "    return [output == str(target)]  # unsupported type on purpose\n",
        encoding="utf-8",
    )
    s = scorer("python", base=tmp_path, code="angry.py")
    crashed = s("boom", "x")
    assert crashed.verdict == "uncheckable"
    assert "RuntimeError" in crashed.evidence
    wrong_type = s("x", "x")
    assert wrong_type.verdict == "uncheckable"
    assert "list" in wrong_type.evidence


def test_numeric_multi_target_any_match():
    s = scorer("numeric", params={"tolerance": 0.5})
    assert s("the answer is 57", ["N/A", "57"]).verdict == "pass"
    assert s("the answer is 99", ["N/A", "57"]).verdict == "fail"
    assert s("57", ["N/A", "nope"]).verdict == "uncheckable"


def test_python_scorer(tmp_path):
    code = tmp_path / "myscorer.py"
    code.write_text(
        "def score(output, target):\n"
        "    if 'skip' in output:\n"
        "        return None\n"
        "    return output.lower().strip() == str(target).lower()\n",
        encoding="utf-8",
    )
    s = scorer("python", base=tmp_path, code="myscorer.py")
    assert s("Dog", "dog").verdict == "pass"
    assert s("cat", "dog").verdict == "fail"
    assert s("skip me", "dog").verdict == "uncheckable"


def test_python_scorer_missing_score_function(tmp_path):
    code = tmp_path / "bad.py"
    code.write_text("x = 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="score"):
        scorer("python", base=tmp_path, code="bad.py")


# --- the gate ---------------------------------------------------------------------


def test_witnesses_validated():
    s = scorer("exact")
    report = run_witnesses(
        s,
        [
            {"output": "57", "target": "57", "expect": "pass"},
            {"output": "58", "target": "57", "expect": "fail"},
        ],
    )
    assert report.verdict == "validated"
    assert report.n_behaved == 2


def test_witness_failure_carries_evidence():
    s = scorer("includes")  # laxer than the witness demands
    report = run_witnesses(
        s,
        [
            {"output": "57", "target": "57", "expect": "pass"},
            {"output": "The answer is 57", "target": "57", "expect": "fail", "why": "no credit for wrappers"},
        ],
    )
    assert report.verdict == "failed"
    assert report.failures[0]["expected"] == "fail"
    assert report.failures[0]["got"] == "pass"
    assert report.failures[0]["why"] == "no credit for wrappers"


def test_uncheckable_witness_never_counts_as_behaved():
    s = scorer("numeric")
    report = run_witnesses(s, [{"output": "no digits", "target": "57", "expect": "fail"}])
    assert report.verdict == "failed", "uncheckable must not satisfy an expect=fail witness"


def test_numeric_extract_last_is_the_fix_for_shown_working():
    """Found live: a model answering "12*3=36, 8*5=40, 36+40=76" for target 76
    scored 0.000 under first-number extraction and 0.438 under last-number,
    which inverted its rank in the fleet. R16 detects it; this knob fixes it."""
    from dinostomp.scorers import make_scorer
    from pathlib import Path

    shown = "12*3=36\n8*5=40\n36+40=76"
    first = make_scorer({"kind": "numeric", "params": {"tolerance": 0.01}}, Path("."))
    last = make_scorer({"kind": "numeric", "params": {"tolerance": 0.01, "extract": "last"}}, Path("."))
    assert first(shown, "76").verdict == "fail", "first-number extraction is the trap"
    assert last(shown, "76").verdict == "pass"
    # and the default is unchanged for a bare answer
    assert first("76", "76").verdict == "pass" and last("76", "76").verdict == "pass"
