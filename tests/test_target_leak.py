"""S17, the trench-coat detector: a single column that all but determines the
target is a candidate label leak. Negative-tested on the two shapes it must
catch, the three false positives it must not raise, and the two scopes where it
does not apply.
"""
import csv
import hashlib
import json
from pathlib import Path

import yaml

from dinostomp.dataset import leak_candidates, target_is_classlike
from dinostomp.lint import lint_dataset, lint_eval


def _csv(tmp, rows):
    p = tmp / "data.csv"
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return p


def churn(n=200, leaky=True, imbalance=8):
    rows = []
    for i in range(n):
        c = int(hashlib.sha256(f"c{i}".encode()).hexdigest(), 16) % 100 < imbalance
        r = {"customer_id": f"CUST-{i:05d}", "tenure_months": (i * 7) % 60,
             "support_tier": "high" if (i * 13) % 10 < 3 else "low",
             "churned": "yes" if c else "no"}
        if leaky:
            r["refund_after_cancel"] = "yes" if c else "no"          # value leak
            r["days_until_cancellation"] = str((i * 3) % 90) if c else ""  # missingness leak
        rows.append(r)
    return rows


def finding(rep, cid):
    return next((f for f in rep["findings"] if f["id"] == cid), None)


def s17(tmp, rows, target="churned"):
    rep, issues, _ = lint_dataset(_csv(tmp, rows), field_overrides={"target": target})
    assert rep is not None, issues
    return finding(rep, "S17")


# --- the two leak shapes it must catch --------------------------------------

def test_s17_catches_a_value_leak_and_a_missingness_leak(tmp_path):
    f = s17(tmp_path, churn(leaky=True))
    assert f["level"] == "warn", f
    flagged = {c["column"] for c in f["evidence"]["candidates"]}
    assert "refund_after_cancel" in flagged
    assert "days_until_cancellation" in flagged


def test_s17_is_base_rate_robust_on_a_severe_imbalance(tmp_path):
    # 3% positive: a perfect leak lifts raw accuracy only 3 points, but NMI is 1.
    f = s17(tmp_path, churn(leaky=True, imbalance=3))
    assert f["level"] == "warn"
    assert any(c["column"] == "refund_after_cancel" for c in f["evidence"]["candidates"])


# --- the false positives it must NOT raise ----------------------------------

def test_s17_clean_table_passes(tmp_path):
    assert s17(tmp_path, churn(leaky=False))["level"] == "pass"


def test_s17_does_not_flag_a_high_cardinality_id(tmp_path):
    # customer_id is unique per row; grouping on it "predicts" everything.
    f = s17(tmp_path, churn(leaky=True))
    assert "customer_id" not in {c["column"] for c in f["evidence"]["candidates"]}


def test_s17_does_not_flag_a_strong_but_noisy_feature(tmp_path):
    rows = []
    for i in range(200):
        u = int(hashlib.sha256(f"x{i}".encode()).hexdigest(), 16) / 16 ** 64
        churned = u < 0.4
        # correlated ~75% of the time, not deterministic
        tier = "low" if (churned if (u * 9 % 1) < 0.75 else not churned) else "high"
        rows.append({"id": f"c{i}", "signup_channel": ["ads", "organic", "ref"][i % 3],
                     "risk_tier": tier, "churned": "yes" if churned else "no"})
    assert s17(tmp_path, rows)["level"] == "pass"


# --- the two scopes where it does not apply ---------------------------------

def test_tabular_audit_does_not_hard_gate_answer_leak(tmp_path):
    # The synthesized "question" is a join of the feature values, so the target's
    # own value sits inside it by construction. S2 (answer-leak, a hard gate)
    # must not read that as a leak and fail the table; S17 owns leak here.
    rep, issues, _ = lint_dataset(_csv(tmp_path, churn(leaky=True)),
                                  field_overrides={"target": "churned"})
    assert rep is not None, issues
    assert finding(rep, "S2")["level"] == "n/a"


def test_s17_na_when_target_is_free_text(tmp_path):
    rows = [{"question": f"Capital of country {i}?", "answer": f"City{i}", "hint": f"h{i}"}
            for i in range(60)]
    rep, issues, _ = lint_dataset(_csv(tmp_path, rows), field_overrides={"target": "answer"})
    assert rep is not None, issues
    assert finding(rep, "S17")["level"] == "n/a"


def test_s17_na_on_an_eval_pod(tmp_path):
    (tmp_path / "items.jsonl").write_text(
        '{"_canary": "dinostomp canary DO NOT TRAIN test"}\n'
        + "\n".join(json.dumps({"id": f"q{i}", "input": f"{i}+1?", "target": str(i + 1)})
                    for i in range(6)) + "\n", encoding="utf-8")
    spec = {"name": "p", "version": "0.1.0", "question": "Does the model add one to the input?",
            "data": {"path": "items.jsonl", "format": "jsonl"},
            "models": [{"provider": "dry", "model": "dry-strong"}],
            "scorer": {"kind": "exact", "witnesses": [
                {"output": "2", "target": "2", "expect": "pass"},
                {"output": "3", "target": "2", "expect": "fail"}]},
            "run": {"n": 6, "seed": 7, "budget_usd": 0}}
    p = tmp_path / "eval.yaml"
    p.write_text(yaml.safe_dump(spec), encoding="utf-8")
    rep, issues = lint_eval(p)
    assert rep is not None, issues
    assert finding(rep, "S17")["level"] == "n/a"
