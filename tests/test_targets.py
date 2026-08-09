"""Target rail tests: the agent adapter, the trajectory record, and T1-T6.

House rule applies here like everywhere else: every check gets a test that
breaks something on purpose and asserts the breakage is caught.
"""

import json

import pytest
import yaml

from dinostomp.lint import lint_eval
from dinostomp.providers import ProviderError
from dinostomp.runner import OK, STOPPED_EARLY, run_spec
from dinostomp.spec import load_spec
from dinostomp.targets import normalize_step, normalize_trajectory, split_entrypoint, to_completion

WITNESSES = [
    {"output": "57", "target": "57", "expect": "pass"},
    {"output": "The answer is 57", "target": "57", "expect": "fail"},
    {"output": "5", "target": "57", "expect": "fail"},
    {"output": "not 57", "target": "57", "expect": "fail"},
    {"output": "FIFTY", "target": "fifty", "expect": "fail"},
]

AGENT = '''\
def run(item, ctx):
    parts = str(item["input"]).split()
    total = int(parts[2]) + int(parts[4].rstrip("?"))
    steps = [{"tool": "calc", "args": {"n": str(item["id"])}, "result": "sum = " + str(total), "ok": True}]
%(twist)s
    return {"output": str(total), "trajectory": steps}
'''


def items(n=24):
    return [{"id": f"a{i}", "input": f"What is {i} + {i + 1}? Reply with the bare number.",
             "target": str(2 * i + 1)} for i in range(10, 10 + n)]


def make_pod(tmp_path, twist="", models=("agent-a",), policy=None, budget=0.0, agent_src=None):
    pod = tmp_path / "pod"
    pod.mkdir(parents=True, exist_ok=True)
    (pod / "agent.py").write_text(agent_src or AGENT % {"twist": twist}, encoding="utf-8")
    spec = {
        "name": "target-pod", "version": "0.1.0",
        "question": "Does the agent answer from its own tool output?",
        "data": {"path": "items.jsonl", "format": "jsonl"},
        "models": [{"provider": "python", "model": m, "entrypoint": "agent.py:run"} for m in models],
        "scorer": {"kind": "exact", "witnesses": WITNESSES},
        "run": {"n": 24, "seed": 7, "budget_usd": budget},
    }
    if policy:
        spec["trajectory"] = policy
    lines = ['{"_canary": "dinostomp canary DO NOT TRAIN targets"}']
    lines += [json.dumps(i) for i in items()]
    (pod / "items.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (pod / "eval.yaml").write_text(yaml.safe_dump(spec), encoding="utf-8")
    return pod / "eval.yaml"


def level_of(report, cid):
    return next(f["level"] for f in report["findings"] if f["id"] == cid)


# --- the adapter ------------------------------------------------------------


def test_entrypoint_symbol_defaults_to_run():
    assert split_entrypoint("agent.py:solve") == ("agent.py", "solve")
    assert split_entrypoint("agent.py") == ("agent.py", "run")


def test_bare_string_return_is_a_completion():
    c = to_completion("42", "m")
    assert c.text == "42" and c.trajectory == []


def test_malformed_step_is_recorded_not_repaired():
    # The check for nameless steps can only fire if the adapter refuses to
    # invent a plausible name here.
    assert normalize_step({"result": "x"})["tool"] == ""
    assert normalize_step("just a string")["tool"] == ""
    assert normalize_trajectory("not a list")[0]["tool"] == ""


def test_oversized_result_is_truncated_and_says_so():
    step = normalize_step({"tool": "t", "result": "x" * 99_999})
    assert step["result_truncated"] is True
    assert len(step["result"]) < 99_999


def test_target_returning_junk_is_a_provider_error():
    for junk in (17, {"trajectory": []}, {"output": 3}):
        with pytest.raises(ProviderError):
            to_completion(junk, "m")


def test_negative_cost_is_refused():
    with pytest.raises(ProviderError):
        to_completion({"output": "x", "cost_usd": -1}, "m")


# --- the runner -------------------------------------------------------------


def test_agent_pod_runs_and_records_its_trajectory(tmp_path):
    spec = make_pod(tmp_path)
    outcome = run_spec(spec)
    assert outcome.exit_code == OK
    records = [json.loads(l) for l in outcome.run_files[0].read_text(encoding="utf-8").splitlines() if l.strip()]
    assert all(r["trajectory"][0]["tool"] == "calc" for r in records)
    manifest = json.loads(outcome.run_files[0].with_name(
        outcome.run_files[0].stem + "_manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["target_sha256"]) == 64, "the agent is inside the drift boundary"
    assert manifest["spend_source"] == "metered"


def test_crashing_target_stops_the_run_instead_of_banking_a_wrong_answer(tmp_path):
    spec = make_pod(tmp_path, agent_src='def run(item, ctx):\n    raise RuntimeError("boom")\n')
    outcome = run_spec(spec)
    assert outcome.exit_code == STOPPED_EARLY
    assert "boom" in outcome.stopped_reason


def test_target_reported_spend_is_labelled_and_still_capped(tmp_path):
    # A target that spends money inside itself must report it; the ledger
    # records the claim, labels it unaudited, and enforces the same cap.
    src = ('def run(item, ctx):\n'
           '    return {"output": "0", "cost_usd": 0.02, "trajectory": []}\n')
    spec = make_pod(tmp_path, agent_src=src, budget=0.01)
    outcome = run_spec(spec)
    assert outcome.exit_code == STOPPED_EARLY, "the cap holds against target-reported spend"
    assert "budget" in outcome.stopped_reason
    manifest = json.loads(outcome.run_files[0].with_name(
        outcome.run_files[0].stem + "_manifest.json").read_text(encoding="utf-8"))
    assert manifest["spend_source"] == "target_reported"
    record = json.loads(outcome.run_files[0].read_text(encoding="utf-8").splitlines()[0])
    assert record["usage"]["rate_label"] == "target-reported"


def test_editing_the_agent_after_a_run_is_drift(tmp_path):
    spec = make_pod(tmp_path)
    assert run_spec(spec).exit_code == OK
    agent = spec.parent / "agent.py"
    agent.write_text(agent.read_text(encoding="utf-8") + "\n# tweak\n", encoding="utf-8")
    report, _ = lint_eval(spec)
    assert level_of(report, "R1") == "fail"
    assert any("target" in e for e in
               next(f for f in report["findings"] if f["id"] == "R1")["examples"])


# --- spec-level refusals ----------------------------------------------------


def test_entrypoint_escaping_the_pod_is_rejected(tmp_path):
    spec = make_pod(tmp_path)
    obj = yaml.safe_load(spec.read_text(encoding="utf-8"))
    obj["models"][0]["entrypoint"] = "../elsewhere.py:run"
    spec.write_text(yaml.safe_dump(obj), encoding="utf-8")
    _, issues = load_spec(spec)
    assert any("escapes the eval directory" in i.message for i in issues)


def test_tool_both_required_and_forbidden_is_rejected(tmp_path):
    spec = make_pod(tmp_path, policy={"required_tools": ["calc"], "forbidden_tools": ["calc"]})
    _, issues = load_spec(spec)
    assert any("both required and forbidden" in i.message for i in issues)


def test_trajectory_policy_without_a_target_is_rejected(tmp_path):
    spec = make_pod(tmp_path)
    obj = yaml.safe_load(spec.read_text(encoding="utf-8"))
    obj["models"] = [{"provider": "dry", "model": "dry-strong"}]
    obj["trajectory"] = {"required_tools": ["calc"]}
    spec.write_text(yaml.safe_dump(obj), encoding="utf-8")
    _, issues = load_spec(spec)
    assert any("python, mediated or imported target" in i.message for i in issues)


# --- T1-T6, each broken on purpose ------------------------------------------


def test_t1_catches_a_forbidden_tool(tmp_path):
    spec = make_pod(tmp_path, policy={"forbidden_tools": ["shell.exec"]},
                    twist='    steps.append({"tool": "shell.exec", "args": {}, "result": "", "ok": True})')
    assert run_spec(spec).exit_code == OK
    report, _ = lint_eval(spec)
    assert level_of(report, "T1") == "fail"
    assert report["summary"]["verdict"] == "broken"


def test_t2_catches_a_skipped_required_tool(tmp_path):
    spec = make_pod(tmp_path, policy={"required_tools": ["calc"]},
                    twist='    steps = [{"tool": "guess", "args": {}, "result": "", "ok": True}]')
    assert run_spec(spec).exit_code == OK
    report, _ = lint_eval(spec)
    assert level_of(report, "T2") == "fail"


def test_t3_catches_nameless_steps_and_runaways(tmp_path):
    spec = make_pod(tmp_path, twist='    steps.append({"tool": "", "args": {}, "result": "?", "ok": True})')
    assert run_spec(spec).exit_code == OK
    assert level_of(lint_eval(spec)[0], "T3") == "fail"

    spec2 = make_pod(tmp_path / "b", policy={"max_steps": 2}, twist="    steps = steps * 5")
    assert run_spec(spec2).exit_code == OK
    assert level_of(lint_eval(spec2)[0], "T3") == "fail"


def test_t4_catches_answers_absent_from_their_own_evidence(tmp_path):
    spec = make_pod(tmp_path, twist='    steps = [{"tool": "calc", "args": {}, '
                                    '"result": "computed elsewhere", "ok": True}]')
    assert run_spec(spec).exit_code == OK
    assert level_of(lint_eval(spec)[0], "T4") == "warn"


def test_t4_is_per_model_so_one_liar_cannot_hide_in_an_honest_fleet(tmp_path):
    # Pooled, three honest agents would drown the fourth's 100% ungrounded rate
    # (6 of 96 records = 6%, under the threshold). Per model it is unmissable.
    spec = make_pod(tmp_path, models=("agent-a", "agent-b", "agent-c", "agent-d"),
                    twist='    if ctx["model"] == "agent-d":\n'
                          '        steps = [{"tool": "calc", "args": {}, "result": "trust me", "ok": True}]')
    assert run_spec(spec).exit_code == OK
    report, _ = lint_eval(spec)
    assert level_of(report, "T4") == "warn"
    assert any("agent-d" in e for e in
               next(f for f in report["findings"] if f["id"] == "T4")["examples"])


def test_t5_catches_the_one_target_that_reports_nothing(tmp_path):
    spec = make_pod(tmp_path, models=("agent-a", "agent-b", "agent-c", "agent-d"),
                    twist='    if ctx["model"] == "agent-d":\n        steps = []')
    assert run_spec(spec).exit_code == OK
    assert level_of(lint_eval(spec)[0], "T5") == "warn"


def test_t6_catches_a_looping_agent(tmp_path):
    spec = make_pod(tmp_path, models=("agent-a", "agent-b", "agent-c", "agent-d"),
                    twist='    if ctx["model"] == "agent-d":\n        steps = steps * 3')
    assert run_spec(spec).exit_code == OK
    assert level_of(lint_eval(spec)[0], "T6") == "warn"


def test_trajectory_checks_are_not_applicable_without_a_target(tmp_path):
    # A completion-only pod must not be nagged about trajectories it cannot have.
    spec = make_pod(tmp_path)
    obj = yaml.safe_load(spec.read_text(encoding="utf-8"))
    obj["models"] = [{"provider": "dry", "model": "dry-strong"}]
    spec.write_text(yaml.safe_dump(obj), encoding="utf-8")
    assert run_spec(spec).exit_code == OK
    report, _ = lint_eval(spec)
    assert all(level_of(report, cid) == "n/a" for cid in ("T1", "T2", "T3", "T4", "T5", "T6"))
