"""R22 numeric-miss: a failed answer that is the same NUMBER as its target.

The run-time mirror of S18. An exact scorer marks "1/2" wrong against a key of
"0.5", so a model that computed the right value is scored as a miss, accuracy is
understated, and a ranking can flip. R16 (its sibling) is string containment and
cannot see this, so the tests assert R16 stays quiet while R22 fires: proof the
gap is real and not a duplicate.
"""
import json

import pytest

from tests.test_lint import finding, rewrite_run_consistently, stomp, write_eval
from dinostomp.runner import OK, run_spec


def _numeric_items(n=24):
    # distinct decimal targets; item d04 keys to exactly 0.5
    return [{"id": f"d{i:02d}", "input": f"What is one tenth times {i + 1}, as a decimal?",
             "target": str(round(0.1 * (i + 1), 2))} for i in range(n)]


def _ran(tmp_path, items):
    spec = write_eval(tmp_path, items)
    outcome = run_spec(spec)
    assert outcome.exit_code == OK
    return spec, outcome.run_files[0]


def test_r22_flags_a_fraction_scored_wrong_against_a_decimal(tmp_path):
    items = _numeric_items()
    spec, run_file = _ran(tmp_path, items)

    def mutate(r, idx):
        if str(r.get("item_id")) == "d04":               # target "0.5"
            r["output"] = "1/2"                            # the right value, wrong form
            r["score"] = {"verdict": "fail"}
        return r

    rewrite_run_consistently(spec, run_file, mutate)
    report = stomp(spec)
    r22 = finding(report, "R22")
    assert r22["level"] == "warn", r22
    assert any("d04" in ex and "1/2" in ex for ex in r22["examples"])
    # the gap is real: R16 (string containment) cannot see it
    assert finding(report, "R16")["level"] in ("pass", "skip", "n/a")
    # a diagnostic must never break the verdict
    assert report["summary"]["verdict"] != "broken"


def test_r22_flags_a_thousands_separator(tmp_path):
    items = [{"id": f"k{i:02d}", "input": f"How many grams in {i + 1} kilograms?",
              "target": str((i + 1) * 1000)} for i in range(24)]
    spec, run_file = _ran(tmp_path, items)

    def mutate(r, idx):
        if str(r.get("item_id")) == "k00":               # target "1000"
            r["output"] = "1,000"
            r["score"] = {"verdict": "fail"}
        return r

    rewrite_run_consistently(spec, run_file, mutate)
    r22 = finding(stomp(spec), "R22")
    assert r22["level"] == "warn"
    assert any("k00" in ex for ex in r22["examples"])


def test_r22_passes_a_genuinely_wrong_numeric_answer(tmp_path):
    items = _numeric_items()
    spec, run_file = _ran(tmp_path, items)

    def mutate(r, idx):
        if str(r.get("item_id")) == "d04":               # target "0.5"
            r["output"] = "0.9"                            # actually wrong, not equivalent
            r["score"] = {"verdict": "fail"}
        return r

    rewrite_run_consistently(spec, run_file, mutate)
    assert finding(stomp(spec), "R22")["level"] == "pass"


def test_r22_na_when_targets_are_not_numeric(tmp_path):
    items = [{"id": f"t{i:02d}", "input": f"What is the capital of country {i}?",
              "target": ["Paris", "Rome", "Oslo", "Bonn"][i % 4]} for i in range(24)]
    spec, run_file = _ran(tmp_path, items)

    def mutate(r, idx):
        if idx == 3:
            r["output"] = "Nowhere"
            r["score"] = {"verdict": "fail"}
        return r

    rewrite_run_consistently(spec, run_file, mutate)
    assert finding(stomp(spec), "R22")["level"] == "n/a"


def test_r22_skips_without_runs(tmp_path):
    # Like every run-scope check, R22 skips (not n/a) when there are no runs to
    # read, so an incomplete pod stays incomplete rather than looking answered.
    spec = write_eval(tmp_path, _numeric_items())
    assert finding(stomp(spec), "R22")["level"] == "skip"
