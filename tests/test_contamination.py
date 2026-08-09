"""Canary regurgitation, and the sensitivity rule that makes a clean result mean something."""

import json

import yaml

from dinostomp import contamination
from dinostomp.lint import lint_eval

NL = chr(10)


def test_split_leaves_a_tail_worth_memorising():
    head, tail = contamination.split_canary("dinostomp-canary-abcdef123456")
    assert head and len(tail) >= contamination.MIN_TAIL_CHARS
    assert head + tail == "dinostomp-canary-abcdef123456"


def test_reproduction_ignores_case_and_spacing_but_not_content():
    assert contamination.reproduced("  ABC123  ", "abc123")
    assert not contamination.reproduced("abc124", "abc123")
    assert not contamination.reproduced("", "abc123")


def test_every_probe_carries_a_positive_control():
    cases = contamination.build_cases("dinostomp-canary-abcdef123456")
    kinds = [c["kind"] for c in cases]
    assert kinds.count("canary") == 1
    assert kinds.count("control") >= 1, (
        "without a control, a clean canary result is unfalsifiable: it looks the same "
        "whether the model is uncontaminated or the probe is simply blind")


def _pod(tmp_path, records):
    """A pod with a canary probe already on disk, so S10 can be exercised offline."""
    pod = tmp_path / "pod"
    (pod / "data" / "runs").mkdir(parents=True, exist_ok=True)
    (pod / "data" / "results").mkdir(parents=True, exist_ok=True)
    items = [{"id": f"a{i}", "input": f"What is {i} + {i + 1}? Reply with the bare number.",
              "target": str(2 * i + 1)} for i in range(10, 34)]
    spec = {
        "name": "canary-pod", "version": "0.1.0",
        "question": "Does the model answer two-digit addition with the bare number?",
        "data": {"path": "items.jsonl", "format": "jsonl"},
        "models": [{"provider": "openrouter", "model": "m", "price_in": 0.1, "price_out": 0.1}],
        "scorer": {"kind": "exact", "witnesses": [
            {"output": "57", "target": "57", "expect": "pass"},
            {"output": "The answer is 57", "target": "57", "expect": "fail"},
            {"output": "5", "target": "57", "expect": "fail"},
            {"output": "not 57", "target": "57", "expect": "fail"},
        ]},
        "run": {"n": 24, "seed": 42, "budget_usd": 1.0},
    }
    lines = ['{"_canary": "dinostomp-canary-abcdef123456"}']
    lines += [json.dumps(i) for i in items]
    (pod / "items.jsonl").write_text(NL.join(lines) + NL, encoding="utf-8")
    (pod / "eval.yaml").write_text(yaml.safe_dump(spec), encoding="utf-8")

    stem = "20260808_000000_canary-pod_m_canaryprobe_s42"
    (pod / "data" / "runs" / f"{stem}.jsonl").write_text(
        NL.join(json.dumps(r) for r in records) + NL, encoding="utf-8")
    (pod / "data" / "runs" / f"{stem}_manifest.json").write_text(json.dumps({
        "tool_version": "0", "spec_name": "canary-pod", "spec_version": "0.1.0",
        "spec_sha256": "0" * 64, "data_sha256": "0" * 64, "provider": "openrouter", "model": "m",
        "seed": 42, "budget_cap_usd": 1.0, "probe": "canary", "dry_run": False,
        "witness_report": {"n_witnesses": 0, "n_behaved": 0, "verdict": "absent"},
        "started_at": "x", "run_file": f"{stem}.jsonl", "status": "complete",
    }), encoding="utf-8")
    return pod / "eval.yaml"


def _rec(kind, hit):
    return {"key": kind, "item_id": kind, "model": "m", "provider": "openrouter", "seed": 42,
            "output": "x", "canary_kind": kind,
            "score": {"verdict": "flag" if hit else "fail"}, "ts": "x"}


def level_of(report, cid):
    return next(f["level"] for f in report["findings"] if f["id"] == cid)


def test_s10_skips_when_the_probe_cannot_even_reproduce_a_control(tmp_path):
    # The instrument has no demonstrated sensitivity here, so a clean canary
    # result proves nothing and must not be reported as one.
    spec = _pod(tmp_path, [_rec("control", False), _rec("canary", False)])
    report, _ = lint_eval(spec)
    assert level_of(report, "S10") == "skip"
    assert "sensitivity" in next(f for f in report["findings"] if f["id"] == "S10")["detail"]


def test_s10_passes_only_when_the_control_landed(tmp_path):
    spec = _pod(tmp_path, [_rec("control", True), _rec("canary", False)])
    assert level_of(lint_eval(spec)[0], "S10") == "pass"


def test_s10_warns_when_a_sensitive_probe_finds_the_canary(tmp_path):
    spec = _pod(tmp_path, [_rec("control", True), _rec("canary", True)])
    report, _ = lint_eval(spec)
    assert level_of(report, "S10") == "warn"
    assert any("seen this dataset" in e
               for e in next(f for f in report["findings"] if f["id"] == "S10")["examples"])
