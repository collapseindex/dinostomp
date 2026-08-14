"""S20 key-skew: a data-scope warning that the answer key leans hard on one
value, so a model can score high by always guessing the majority. R7 catches
this once models have run; S20 reads it off the key before a cent is spent.
Diagnostic; negative-tested on skew, balance, and the degenerate one-answer key.
"""
import json

from dinostomp.lint import lint_dataset


def _jsonl(tmp, rows):
    p = tmp / "data.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return p


def finding(rep, cid):
    return next((f for f in rep["findings"] if f["id"] == cid), None)


def s20(tmp, rows):
    rep, issues, _ = lint_dataset(_jsonl(tmp, rows))
    assert rep is not None, issues
    return finding(rep, "S20")


def _q(i):
    return f"Is statement number {i} considered true in this dataset here?"


def test_s20_warns_on_a_skewed_key(tmp_path):
    # 65% "yes": always guessing yes scores 65% knowing nothing.
    rows = [{"id": f"q{i}", "question": _q(i),
             "answer": "yes" if i % 20 < 13 else ("no" if i % 2 else "maybe")} for i in range(40)]
    f = s20(tmp_path, rows)
    assert f["level"] == "warn", f
    assert f["evidence"]["modal_share"] >= 0.6


def test_s20_warns_on_a_skewed_binary_key(tmp_path):
    rows = [{"id": f"q{i}", "question": _q(i), "answer": "yes" if i % 10 < 7 else "no"} for i in range(40)]
    assert s20(tmp_path, rows)["level"] == "warn"          # 70/30


def test_s20_passes_a_balanced_binary_key(tmp_path):
    rows = [{"id": f"q{i}", "question": _q(i), "answer": "yes" if i % 2 else "no"} for i in range(40)]
    assert s20(tmp_path, rows)["level"] == "pass"          # 50/50, modal == uniform


def test_s20_passes_a_balanced_multiclass_key(tmp_path):
    rows = [{"id": f"q{i}", "question": f"What category is item number {i} in here?",
             "answer": ["alpha", "beta", "gamma", "delta"][i % 4]} for i in range(40)]
    assert s20(tmp_path, rows)["level"] == "pass"          # 25% each


def test_s20_names_a_degenerate_one_answer_key(tmp_path):
    rows = [{"id": f"q{i}", "question": _q(i), "answer": "yes"} for i in range(40)]
    f = s20(tmp_path, rows)
    assert f["level"] == "warn"
    assert "no variety" in f["detail"] or "one answer" in f["detail"]


def test_s20_na_below_the_item_floor(tmp_path):
    rows = [{"id": f"q{i}", "question": _q(i), "answer": "yes"} for i in range(8)]
    assert s20(tmp_path, rows)["level"] == "n/a"
