"""Partial credit: the graded-scorer path, and the two checkers that guard it.

Negative-tested the house way. Each checker is shown firing on a scorer that
really has the defect, and staying quiet on one that does not, because a check
that cannot fail is decoration.
"""
import json
from pathlib import Path

import yaml

from dinostomp.cli import main
from dinostomp.lint import lint_eval
from dinostomp.results import per_model, fleet
from dinostomp.scorers import ScoreResult, make_scorer, run_witnesses

GRADED_SCORER = '''\
def score(output, target):
    """Fraction of the target's comma-separated fields present in the output."""
    want = [w.strip() for w in str(target).split(",") if w.strip()]
    if not want:
        return None
    hit = sum(1 for w in want if w in output)
    return hit / len(want)
'''

ITEMS = [{"id": f"g{i}", "input": f"list {i}", "target": "alpha,bravo,charlie"}
         for i in range(6)]

# One partial witness (0<v<1) proves the gradation; the two ends anchor it.
GRADED_WITNESSES = [
    {"output": "alpha bravo charlie", "target": "alpha,bravo,charlie",
     "expect": "pass", "expect_value": 1.0},
    {"output": "nothing here", "target": "alpha,bravo,charlie",
     "expect": "fail", "expect_value": 0.0},
    {"output": "alpha bravo", "target": "alpha,bravo,charlie",
     "expect": "fail", "expect_value": 2 / 3},
]


def _pod(tmp, scorer_src, witnesses, code_name="scorer.py"):
    (tmp / code_name).write_text(scorer_src, encoding="utf-8")
    spec = {
        "name": "graded-fixture", "version": "0.1.0",
        "question": "How many target fields did the model list?",
        "data": {"path": "items.jsonl", "format": "jsonl"},
        "models": [{"provider": "dry", "model": "dry-strong"}],
        "scorer": {"kind": "python", "code": code_name, "witnesses": witnesses},
        "run": {"n": len(ITEMS), "seed": 7, "budget_usd": 0},
    }
    lines = ['{"_canary": "dinostomp canary DO NOT TRAIN test-fixture"}']
    lines += [json.dumps(i) for i in ITEMS]
    (tmp / "items.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    p = tmp / "eval.yaml"
    p.write_text(yaml.safe_dump(spec), encoding="utf-8")
    return p


def finding(report, cid):
    return next((f for f in report["findings"] if f["id"] == cid), None)


# --- the scoring primitive --------------------------------------------------

def test_python_scorer_returns_native_float_as_graded_credit(tmp_path):
    (tmp_path / "s.py").write_text(GRADED_SCORER, encoding="utf-8")
    sc = make_scorer({"kind": "python", "code": "s.py", "witnesses": []}, tmp_path)
    r = sc("alpha bravo", "alpha,bravo,charlie")
    assert abs(r.value - 2 / 3) < 1e-9
    assert r.verdict == "fail"          # verdict stays categorical, perfect-only
    assert sc("alpha bravo charlie", "alpha,bravo,charlie").verdict == "pass"


# --- aggregation ------------------------------------------------------------

def _entry(model, records):
    return {"manifest": {"model": model, "provider": "dry"},
            "records": [{**r, "model": model} for r in records]}


def test_partial_score_is_the_mean_graded_value_on_checkable():
    recs = [{"score": {"verdict": "fail", "value": 0.0}},
            {"score": {"verdict": "fail", "value": 2 / 3}},
            {"score": {"verdict": "pass", "value": 1.0}},
            {"score": {"verdict": "uncheckable"}}]  # no value, contributes nothing
    rows = per_model([_entry("m", recs)])
    row = rows[0]
    assert row["n_graded"] == 3
    assert row["partial_score"] == round((0.0 + 2 / 3 + 1.0) / 3, 4)
    # accuracy is unchanged: still binary passes / checkable
    assert row["accuracy"] == round(1 / 3, 4)


def test_partial_score_is_none_when_no_scorer_grades():
    rows = per_model([_entry("m", [{"score": {"verdict": "pass"}},
                                   {"score": {"verdict": "fail"}}])])
    assert rows[0]["partial_score"] is None
    assert rows[0]["n_graded"] == 0


def test_fleet_reports_mean_partial_only_over_graded_models():
    graded = per_model([_entry("m", [{"score": {"verdict": "fail", "value": 0.5}}])])
    plain = per_model([_entry("n", [{"score": {"verdict": "pass"}}])])
    f = fleet({}, graded + plain)
    assert f["n_models_graded"] == 1
    assert f["mean_partial_score"] == 0.5


# --- run_witnesses honors expect_value --------------------------------------

def test_witness_expect_value_must_be_hit():
    graded = lambda o, t: ScoreResult("fail", value=0.5)  # noqa: E731
    ok = run_witnesses(graded, [{"output": "x", "target": "y", "expect": "fail",
                                 "expect_value": 0.5}])
    assert ok.verdict == "validated"
    miss = run_witnesses(graded, [{"output": "x", "target": "y", "expect": "fail",
                                   "expect_value": 0.9}])
    assert miss.verdict == "failed"
    # a witness with no expect_value still passes on verdict alone
    bare = run_witnesses(graded, [{"output": "x", "target": "y", "expect": "fail"}])
    assert bare.verdict == "validated"


# --- W3: a graded scorer must witness its gradation -------------------------

def test_w3_passes_when_a_partial_witness_pins_the_gradation(tmp_path):
    report, issues = lint_eval(_pod(tmp_path, GRADED_SCORER, GRADED_WITNESSES),
                               trust_code=True)
    assert report is not None, issues
    assert finding(report, "W3")["level"] == "pass"


def test_w3_fails_a_graded_scorer_that_shows_gradation_but_never_pins_it(tmp_path):
    # A witness output that visibly produces 2/3, but no witness pins that value:
    # the gradation is on display and unproven.
    unpinned = [
        {"output": "alpha bravo charlie", "target": "alpha,bravo,charlie", "expect": "pass"},
        {"output": "nothing", "target": "alpha,bravo,charlie", "expect": "fail"},
        {"output": "alpha bravo", "target": "alpha,bravo,charlie", "expect": "fail"},
    ]
    report, issues = lint_eval(_pod(tmp_path, GRADED_SCORER, unpinned), trust_code=True)
    assert report is not None, issues
    w3 = finding(report, "W3")
    assert w3["level"] == "fail", w3
    assert "unproven" in w3["detail"]


def test_w3_is_not_applicable_to_a_plain_categorical_scorer(tmp_path):
    binary = "def score(output, target):\n    return str(target) in output\n"
    wits = [{"output": "alpha,bravo,charlie", "target": "alpha,bravo,charlie", "expect": "pass"},
            {"output": "no", "target": "alpha,bravo,charlie", "expect": "fail"}]
    report, issues = lint_eval(_pod(tmp_path, binary, wits), trust_code=True)
    assert report is not None, issues
    assert finding(report, "W3")["level"] == "n/a"


def test_w3_fails_an_out_of_range_witness_value(tmp_path):
    bad = ('def score(output, target):\n'
           '    if "OOR" in output:\n'
           '        return 1.5\n'
           '    return 1.0 if str(target) in output else 0.0\n')
    wits = [{"output": "alpha,bravo,charlie", "target": "alpha,bravo,charlie", "expect": "pass"},
            {"output": "OOR", "target": "alpha,bravo,charlie", "expect": "fail"}]
    report, issues = lint_eval(_pod(tmp_path, bad, wits), trust_code=True)
    assert report is not None, issues
    w3 = finding(report, "W3")
    assert w3["level"] == "fail"
    assert "outside [0,1]" in w3["detail"]
