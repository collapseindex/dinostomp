"""S16: authorship circularity. The check that reads the Fable/GPT lesson back
into the tool, an eval whose questions, keys, scorer, and witnesses all trace to
one author (worst of all, one model) has no independent check inside it.

Negative-tested: fires on each circular shape, stays quiet when an independent
hand appears, and is n/a when nothing is declared.
"""
import json
from pathlib import Path

import yaml

from dinostomp.lint import lint_eval

ITEMS = [{"id": f"q{i}", "input": f"question {i}", "target": "57"} for i in range(6)]
WIT = [
    {"output": "57", "target": "57", "expect": "pass", "why": "exact"},
    {"output": "58", "target": "57", "expect": "fail", "why": "wrong"},
    {"output": "The answer is 57", "target": "57", "expect": "fail", "why": "wrapped"},
]


def _pod(tmp, provenance=None):
    spec = {
        "name": "authorship-fixture", "version": "0.1.0",
        "question": "does the model answer exactly?",
        "data": {"path": "items.jsonl", "format": "jsonl"},
        "models": [{"provider": "dry", "model": "dry-strong"}],
        "scorer": {"kind": "exact", "witnesses": WIT},
        "run": {"n": len(ITEMS), "seed": 7, "budget_usd": 0},
    }
    if provenance is not None:
        spec["provenance"] = provenance
    lines = ['{"_canary": "dinostomp canary DO NOT TRAIN test-fixture"}']
    lines += [json.dumps(i) for i in ITEMS]
    (tmp / "items.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    p = tmp / "eval.yaml"
    p.write_text(yaml.safe_dump(spec), encoding="utf-8")
    return p


def s16(report):
    return next(f for f in report["findings"] if f["id"] == "S16")


def test_s16_is_na_without_provenance(tmp_path):
    report, issues = lint_eval(_pod(tmp_path))
    assert report is not None, issues
    assert s16(report)["level"] == "n/a"


def test_s16_warns_when_one_model_authored_everything(tmp_path):
    report, _ = lint_eval(_pod(tmp_path, {
        "items_by": "claude-opus-5", "keys_by": "claude-opus-5",
        "scorer_by": "claude-opus-5", "witnesses_by": "claude-opus-5"}))
    f = s16(report)
    assert f["level"] == "warn", f
    assert "independent hand" in f["detail"] or "independent hand" in " ".join(f["examples"])
    assert any("a model" in e for e in f["examples"])


def test_s16_warns_on_self_keyed_items(tmp_path):
    # items and keys share a model author; scorer/witnesses independent humans.
    report, _ = lint_eval(_pod(tmp_path, {
        "items_by": "gpt-5", "keys_by": "gpt-5",
        "scorer_by": "human:alice", "witnesses_by": "human:bob"}))
    f = s16(report)
    assert f["level"] == "warn", f
    assert any("never independently verified" in e for e in f["examples"])
    assert not any("scorer and witnesses" in e for e in f["examples"])


def test_s16_warns_on_self_fitted_witnesses(tmp_path):
    report, _ = lint_eval(_pod(tmp_path, {
        "items_by": "human:alice", "keys_by": "human:bob",
        "scorer_by": "gpt-5", "witnesses_by": "gpt-5"}))
    f = s16(report)
    assert f["level"] == "warn", f
    assert any("fitted to the scorer author" in e for e in f["examples"])


def test_s16_passes_when_an_independent_hand_appears(tmp_path):
    report, _ = lint_eval(_pod(tmp_path, {
        "items_by": "claude-opus-5", "keys_by": "human:alice",
        "scorer_by": "human:bob", "witnesses_by": "human:carol"}))
    assert s16(report)["level"] == "pass"


def test_s16_all_one_author_but_reviewed_still_flags_but_softer(tmp_path):
    # review_by breaks the whole-eval loop; the sub-loops (self-keyed,
    # self-fitted) still stand and are reported.
    report, _ = lint_eval(_pod(tmp_path, {
        "items_by": "claude-opus-5", "keys_by": "claude-opus-5",
        "scorer_by": "claude-opus-5", "witnesses_by": "claude-opus-5",
        "review_by": "human:dana"}))
    f = s16(report)
    assert f["level"] == "warn"
    # the whole-eval line is gone; the two sub-loops remain
    assert not any("nothing in the eval" in e for e in f["examples"])
    assert any("never independently verified" in e for e in f["examples"])
    assert any("fitted to the scorer author" in e for e in f["examples"])
