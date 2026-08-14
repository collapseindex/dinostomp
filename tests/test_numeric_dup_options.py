"""S18 numeric-dup-options: two options that are the same number in different
writing. Negative-tested on the surface forms it must equate, the false
positives it must not raise, and the scopes where it does not apply.

The point of the check is the F-002 failure reached through arithmetic: if two
options are the same number and one is the key, a model that computes the value
and picks the other spelling is marked wrong while being right.
"""
import json
from pathlib import Path

import pytest
import yaml

from dinostomp.lint import _as_number, lint_dataset, lint_eval


def _jsonl(tmp, rows):
    p = tmp / "data.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return p


def finding(rep, cid):
    return next((f for f in rep["findings"] if f["id"] == cid), None)


def s18(tmp, rows):
    rep, issues, _ = lint_dataset(_jsonl(tmp, rows))
    assert rep is not None, issues
    return finding(rep, "S18")


def _pool(n=4):
    # distinct-number filler so the dataset has numeric choice items around the
    # one under test, and so S18 is never n/a for the wrong reason.
    return [{"id": f"p{i}", "input": f"pick a number, item {i}",
             "choices": ["11", "13", "17", "19"], "target": "11"} for i in range(n)]


# --- the surface forms it must equate ----------------------------------------

@pytest.mark.parametrize("a, b", [
    ("1000", "1,000"),      # thousands separator
    ("0.5", "1/2"),         # integer fraction
    ("12", "twelve"),       # single number word
    ("5", "5.0"),           # trailing zero
    ("0.5", "50%"),         # percent
    ("100", "one hundred"), # compound word stays unparsed on the 'b' side...
])
def test_s18_equates_surface_forms(tmp_path, a, b):
    # "one hundred" does not parse (compound), so that row is the control: it must
    # NOT be flagged, proving the check only fires on values it actually equated.
    rows = _pool() + [{"id": "t", "input": "the item under test",
                       "choices": [a, b, "3", "7"], "target": a}]
    f = s18(tmp_path, rows)
    parses = _as_number(a) is not None and _as_number(b) is not None
    equal = parses and abs(_as_number(a) - _as_number(b)) < 1e-9
    if equal:
        assert f["level"] == "warn", f
        assert any("t:" in ex for ex in f["examples"])
    else:
        assert not any(ex.startswith("t:") for ex in f.get("examples", []))


def test_s18_names_the_keyed_case_louder(tmp_path):
    rows = _pool() + [{"id": "onkey", "input": "one of the equal pair is the key",
                       "choices": ["1000", "1,000", "3", "7"], "target": "1000"}]
    ex = next(e for e in s18(tmp_path, rows)["examples"] if e.startswith("onkey:"))
    assert "keyed answer" in ex


def test_s18_flags_an_equal_pair_that_is_not_the_key_without_the_note(tmp_path):
    rows = _pool() + [{"id": "offkey", "input": "the equal pair are both distractors",
                       "choices": ["1000", "1,000", "3", "7"], "target": "3"}]
    ex = next(e for e in s18(tmp_path, rows)["examples"] if e.startswith("offkey:"))
    assert "same number" in ex and "keyed answer" not in ex


# --- the false positives it must NOT raise -----------------------------------

def test_s18_clean_distinct_numbers_pass(tmp_path):
    assert s18(tmp_path, _pool())["level"] == "pass"


def test_s18_does_not_flag_formulas_or_genotypes(tmp_path):
    # The strings that killed S5's punctuation and substring rules; none parse as
    # a number, so S18 never compares them.
    rows = _pool() + [
        {"id": "logic", "input": "which formula is valid",
         "choices": ["(F . L) . C", "F . L . C", "F . (L . C)", "L . F . C"], "target": "(F . L) . C"},
        {"id": "gene", "input": "which genotype",
         "choices": ["BB Bb", "Bb bb", "BB bb", "Bb Bb"], "target": "BB Bb"}]
    assert s18(tmp_path, rows)["level"] == "pass"


def test_s18_does_not_equate_a_ratio_written_as_a_list(tmp_path):
    # "1,2,3" is a list, not a thousands-separated number; must stay unparsed so a
    # coordinate or a set is never read as 123.
    rows = _pool() + [{"id": "lst", "input": "which coordinate",
                       "choices": ["1,2,3", "4,5,6", "123", "456"], "target": "1,2,3"}]
    f = s18(tmp_path, rows)
    assert not any(ex.startswith("lst:") for ex in f.get("examples", []))


# --- the scopes where it does not apply --------------------------------------

def test_s18_na_when_no_numeric_options(tmp_path):
    rows = [{"id": f"c{i}", "input": f"capital of country {i}?",
             "choices": ["Paris", "Rome", "Oslo", "Bonn"], "target": "Paris"} for i in range(5)]
    assert s18(tmp_path, rows)["level"] == "n/a"


def test_s18_na_when_no_choice_items(tmp_path):
    rows = [{"id": f"q{i}", "input": f"{i} plus one?", "target": str(i + 1)} for i in range(5)]
    assert s18(tmp_path, rows)["level"] == "n/a"


def test_s18_runs_in_a_pod_not_only_a_bare_dataset(tmp_path):
    items = ("\n".join(json.dumps({"id": f"q{i}", "input": f"How many is item {i}?",
                                   "choices": ["1000", "1,000", "3", "7"], "target": "1000"})
                       for i in range(4)) + "\n")
    (tmp_path / "items.jsonl").write_text(
        '{"_canary": "dinostomp canary DO NOT TRAIN test"}\n' + items, encoding="utf-8")
    spec = {"name": "p", "version": "0.1.0",
            "question": "Does the model pick the right numeric option every time?",
            "data": {"path": "items.jsonl", "format": "jsonl"},
            "models": [{"provider": "dry", "model": "dry-strong"}],
            "scorer": {"kind": "exact", "witnesses": [
                {"output": "1000", "target": "1000", "expect": "pass"},
                {"output": "3", "target": "1000", "expect": "fail"}]},
            "run": {"n": 4, "seed": 7, "budget_usd": 0}}
    p = tmp_path / "eval.yaml"
    p.write_text(yaml.safe_dump(spec), encoding="utf-8")
    rep, issues = lint_eval(p)
    assert rep is not None, issues
    assert finding(rep, "S18")["level"] == "warn"
