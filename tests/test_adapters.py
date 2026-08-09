"""The Inspect AI adapter: the contract's second foreign format.

The first (an lm-evaluation-harness details file) cost five defects on contact,
D-021 to D-025. That is what n=1 buys you: evidence that first contact is
expensive, not evidence that the contract generalises. This file is the second
data point.

Offline cases use SYNTHETIC logs shaped from the real ones. The real-log cases
skip unless `python benchmarks/inspect-import/fetch.py` has been run, and they
SKIP rather than quietly passing, because a test that turns into a no-op is
worse than one that fails.
"""

import json
import zipfile
from pathlib import Path

import pytest

from dinostomp.adapters import inspect_ai as ia

REAL = Path(__file__).resolve().parents[1] / "benchmarks" / "inspect-import"
needs_real = pytest.mark.skipif(
    not (REAL / "browser.json").is_file(),
    reason="run `python benchmarks/inspect-import/fetch.py` to check against real logs")


def log(samples, *, model="openai/gpt-4o-mini", task="fixture", version=2):
    return {"version": version, "status": "success",
            "eval": {"model": model, "task": task, "created": "2026-01-01T00:00:00+00:00"},
            "results": {"total_samples": len(samples)},
            "samples": samples}


def sample(sid=1, *, epoch=1, value="C", scorer="choice", text="an answer",
           events=None, usage=None, stop="stop", extra_scores=None):
    s = {"id": sid, "epoch": epoch, "input": f"Q{sid}?", "target": "A",
         "scores": {scorer: {"value": value, "answer": text}},
         "output": {"choices": [{"message": {"content": text}, "stop_reason": stop}]}}
    if extra_scores:
        s["scores"].update(extra_scores)
    if events is not None:
        s["events"] = events
    if usage is not None:
        s["model_usage"] = usage
    return s


# --- detection ---------------------------------------------------------------


def test_a_json_log_is_detected(tmp_path):
    p = tmp_path / "run.json"
    p.write_text(json.dumps(log([sample()])), encoding="utf-8")
    assert ia.detect(p)


def test_an_eval_archive_is_detected(tmp_path):
    p = tmp_path / "run.eval"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("header.json", json.dumps(log([])))
        z.writestr("samples/1_epoch_1.json", json.dumps(sample()))
    assert ia.detect(p)
    header, samples = ia.read(p)
    assert len(samples) == 1 and header["eval"]["task"] == "fixture"


@pytest.mark.parametrize("name, content", [
    ("plain.jsonl", '{"id": 1, "acc": 1}\n'),
    ("other.json", '{"results": [], "not_inspect": true}'),
    ("broken.json", "{not json at all"),
    ("empty.json", ""),
    ("archive.eval", "not a zip"),
])
def test_detection_never_raises_and_never_false_positives(tmp_path, name, content):
    """A sniff runs against every log anyone points at this tool, including
    files it has no business reading. It must answer False, not explode."""
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    assert ia.detect(p) is False


# --- the verdict vocabulary, which is the part that does not transfer --------


def test_correct_and_incorrect_map_cleanly(tmp_path):
    h = log([sample(1, value="C"), sample(2, value="I")])
    recs, issues = ia.to_records(h, h["samples"], scorer="choice", model="m", seed=0)
    assert not issues
    assert [r["score"]["verdict"] for r in recs] == ["pass", "fail"]


@pytest.mark.parametrize("value, why", [
    ("P", "partial"), ("N", "noanswer"), (0.5, "fractional"),
])
def test_a_score_this_battery_cannot_represent_becomes_uncheckable(value, why):
    """NOT a pass, NOT a fail, and not silently dropped.

    Inspect distinguishes partial credit and no-answer from an incorrect answer.
    A binary verdict cannot hold either, so forcing one would invent a number.
    `uncheckable` keeps them out of the accuracy denominator and R6 reports the
    rate, which is the machinery this tool already has for exactly this.
    """
    h = log([sample(1, value=value)])
    recs, issues = ia.to_records(h, h["samples"], scorer="choice", model="m", seed=0)
    assert not issues
    assert recs[0]["score"]["verdict"] == "uncheckable"
    assert str(value) in recs[0]["score"]["evidence"]


def test_zero_and_one_still_work():
    h = log([sample(1, value=1), sample(2, value=0)])
    recs, _ = ia.to_records(h, h["samples"], scorer="choice", model="m", seed=0)
    assert [r["score"]["verdict"] for r in recs] == ["pass", "fail"]


# --- rival scorers: D-023, in a different harness ----------------------------


def test_two_scorers_are_listed_so_the_caller_must_choose():
    """An Inspect task may run several scorers. Picking one silently is the
    acc/acc_norm defect (D-023) in a new costume."""
    h = log([sample(1, value="C", extra_scores={"includes": {"value": "I"}})])
    assert ia.scorer_names(h, h["samples"]) == ["choice", "includes"]


def test_naming_a_scorer_selects_it():
    h = log([sample(1, value="C", extra_scores={"includes": {"value": "I"}})])
    recs, _ = ia.to_records(h, h["samples"], scorer="includes", model="m", seed=0)
    assert recs[0]["score"]["verdict"] == "fail"


def test_a_sample_missing_the_chosen_scorer_is_refused_not_skipped():
    """A partially scored log must not import as a run with holes in it."""
    h = log([sample(1, value="C"), {"id": 2, "epoch": 1, "scores": {}}])
    recs, issues = ia.to_records(h, h["samples"], scorer="choice", model="m", seed=0)
    assert len(recs) == 1 and issues
    assert "no score from" in issues[0].message


# --- what Inspect carries that lm-eval did not -------------------------------


def test_tool_events_become_a_trajectory_and_nothing_else_does():
    """Inspect logs model calls, sandbox ops, spans and store writes in the same
    stream. Folding those in would inflate every step count and make T3 and T6
    measure something different than they do on a native run."""
    events = [
        {"event": "sample_init"},
        {"event": "model", "model": "gpt-4o"},
        {"event": "tool", "function": "web_browser_go",
         "arguments": {"url": "https://example.org"}, "result": "a page"},
        {"event": "span_begin"},
        {"event": "tool", "function": "search", "arguments": {"q": "x"},
         "result": "hits", "error": "timed out"},
    ]
    h = log([sample(1, events=events)])
    recs, _ = ia.to_records(h, h["samples"], scorer="choice", model="m", seed=0)
    traj = recs[0]["trajectory"]
    assert [s["tool"] for s in traj] == ["web_browser_go", "search"]
    assert traj[0]["args"] == {"url": "https://example.org"} and traj[0]["ok"] is True
    assert traj[1]["ok"] is False, "an event carrying an error is not a successful call"


def test_a_sample_with_no_tool_events_carries_no_trajectory():
    h = log([sample(1, events=[{"event": "model"}])])
    recs, _ = ia.to_records(h, h["samples"], scorer="choice", model="m", seed=0)
    assert "trajectory" not in recs[0]


def test_usage_is_summed_across_models_and_carries_no_invented_cost():
    """Inspect does not record spend. Computing one from a rate table this
    adapter does not have would be a number nobody measured, so `cost_usd` is
    absent and R3 skips naming the field."""
    h = log([sample(1, usage={"openai/gpt-4o": {"input_tokens": 10, "output_tokens": 2},
                              "openai/gpt-4o-mini": {"input_tokens": 5, "output_tokens": 1}})])
    recs, _ = ia.to_records(h, h["samples"], scorer="choice", model="m", seed=0)
    assert recs[0]["usage"] == {"input_tokens": 15, "output_tokens": 3}
    assert "cost_usd" not in recs[0]["usage"]


def test_an_absent_answer_is_omitted_not_emptied():
    """Same rule as the flat importer: absent and empty are different claims."""
    h = log([{"id": 1, "epoch": 1, "scores": {"choice": {"value": "I"}}}])
    recs, issues = ia.to_records(h, h["samples"], scorer="choice", model="m", seed=0)
    assert not issues and "output" not in recs[0] and "finish_reason" not in recs[0]


def test_epoch_becomes_the_repeat_index():
    """`epoch` is Inspect's word for running the same item again, which is what
    `run.repeats` means here, so the majority estimator and R20 apply."""
    h = log([sample(1, epoch=1), sample(1, epoch=2), sample(1, epoch=3)])
    recs, _ = ia.to_records(h, h["samples"], scorer="choice", model="m", seed=0)
    assert [r["repeat"] for r in recs] == [0, 1, 2]
    assert len({r["key"] for r in recs}) == 3, "repeats must not collide on one key"


# --- the real logs -----------------------------------------------------------


@needs_real
@pytest.mark.parametrize("name, task, n", [
    ("mmlu-choices.eval", "inspect_evals/mmlu_0_shot", 1),
    ("security-guide.json", "security_guide", 3),
    ("browser.json", "browser", 1),
])
def test_a_real_inspect_log_adapts(name, task, n):
    header, samples = ia.read(REAL / name)
    assert ia.detect(REAL / name)
    assert (header["eval"]["task"]) == task
    assert len(samples) == n
    scorers = ia.scorer_names(header, samples)
    assert scorers, "a real log with no scorer would be nothing to import"
    recs, issues = ia.to_records(header, samples, scorer=scorers[0], model="m", seed=0)
    assert not issues, [i.message for i in issues]
    assert len(recs) == n
    assert all(r["score"]["verdict"] in ("pass", "fail", "uncheckable") for r in recs)


@needs_real
def test_the_real_agent_log_yields_real_tool_calls():
    header, samples = ia.read(REAL / "browser.json")
    recs, _ = ia.to_records(header, samples, scorer="includes", model="m", seed=0)
    traj = recs[0]["trajectory"]
    assert traj, "the browser log's whole point is its tool events"
    assert all(s["tool"] for s in traj), "a step with no tool name would trip T3"
    assert any("web_browser" in s["tool"] for s in traj)


@needs_real
def test_the_real_logs_round_trip_into_a_pod_and_stomp(tmp_path):
    """End to end through the real CLI: import a real Inspect log into a pod
    built from that log's own items, then audit it.

    n=3, which is why this repository ships no Inspect pod: these are fixtures,
    not published runs, and three items cannot audit anybody's eval. What it
    does establish is that the round trip works on a real artifact.
    """
    import yaml

    from dinostomp.cli import main
    from dinostomp.lint import lint_eval

    header, samples = ia.read(REAL / "security-guide.json")
    items = [{"id": str(s["id"]), "input": str(s.get("input")), "target": str(s.get("target"))}
             for s in samples]
    lines = ['{"_canary": "dinostomp canary DO NOT TRAIN inspect-roundtrip"}']
    lines += [json.dumps(i) for i in items]
    (tmp_path / "items.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    spec = {
        "name": "inspect-roundtrip", "version": "0.1.0",
        "question": "Does an imported Inspect run audit like any other evidence?",
        "data": {"path": "items.jsonl", "format": "jsonl"},
        "models": [{"provider": "imported", "model": "openai/gpt-4o-mini"}],
        "scorer": {"kind": "includes", "witnesses": [
            {"output": "alpha", "target": "alpha", "expect": "pass"},
            {"output": "beta", "target": "alpha", "expect": "fail"},
            {"output": "", "target": "alpha", "expect": "fail"},
            {"output": "ALPHA", "target": "alpha", "expect": "fail"},
            {"output": "alph", "target": "alpha", "expect": "fail"},
        ]},
        "run": {"n": len(items), "seed": 0, "budget_usd": 0},
    }
    sp = tmp_path / "eval.yaml"
    sp.write_text(yaml.safe_dump(spec), encoding="utf-8")

    assert main(["import", str(sp), str(REAL / "security-guide.json"), "--seed", "0"]) == 0
    report, issues = lint_eval(sp)
    assert report is not None, issues
    # It audits like anything else: no crash, a real verdict, honest coverage.
    assert report["summary"]["verdict"] in ("sound", "ok", "incomplete", "broken")
    rf = next((tmp_path / "data" / "runs").glob("*.jsonl"))
    m = json.loads(rf.with_name(rf.stem + "_manifest.json").read_text(encoding="utf-8"))
    assert m["imported"] is True
    assert "tool_sha256" not in m, "an imported run may not claim this engine produced it"


@needs_real
def test_an_imported_trace_is_labelled_foreign_not_harness_observed(tmp_path):
    """The honesty line for adapters.

    Inspect watched those tool calls. dinostomp did not. That is better evidence
    than an agent's self-report, because the exporting harness is a third party
    to the agent, and it is still someone else's word. Calling it
    `harness_observed` would claim an observation this engine never made.
    """
    import yaml

    from dinostomp.cli import main

    header, samples = ia.read(REAL / "browser.json")
    items = [{"id": str(s["id"]), "input": "q", "target": "AI Security Institute"}
             for s in samples]
    lines = ['{"_canary": "dinostomp canary DO NOT TRAIN inspect-traj"}']
    lines += [json.dumps(i) for i in items]
    (tmp_path / "items.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    spec = {
        "name": "inspect-traj", "version": "0.1.0",
        "question": "Is an imported trajectory labelled as somebody else's observation?",
        "data": {"path": "items.jsonl", "format": "jsonl"},
        "models": [{"provider": "imported", "model": "openai/gpt-4o-mini"}],
        "scorer": {"kind": "includes", "witnesses": [
            {"output": "alpha", "target": "alpha", "expect": "pass"},
            {"output": "beta", "target": "alpha", "expect": "fail"},
            {"output": "", "target": "alpha", "expect": "fail"},
            {"output": "ALPHA", "target": "alpha", "expect": "fail"},
            {"output": "alph", "target": "alpha", "expect": "fail"},
        ]},
        "run": {"n": len(items), "seed": 0, "budget_usd": 0},
    }
    sp = tmp_path / "eval.yaml"
    sp.write_text(yaml.safe_dump(spec), encoding="utf-8")
    assert main(["import", str(sp), str(REAL / "browser.json"), "--seed", "0"]) == 0
    rf = next((tmp_path / "data" / "runs").glob("*.jsonl"))
    m = json.loads(rf.with_name(rf.stem + "_manifest.json").read_text(encoding="utf-8"))
    assert m["trajectory_source"] == "foreign_observed"
