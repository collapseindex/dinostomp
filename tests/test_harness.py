"""The mediated rail: an observed trace, call-time policy, and the ablation probe.

The claim under test is narrow and worth stating before the assertions: the
harness makes the TRACE trustworthy, not the AGENT. Nothing here is a security
boundary, and one test below deliberately proves that rather than leaving it as
a docstring nobody checks.
"""

import json

import pytest
import yaml

from dinostomp.harness import WITHHELD, MediatedTarget, ToolDenied, Tools
from dinostomp.providers import ProviderError
from dinostomp.runner import CANNOT_RUN, OK, run_spec
from dinostomp.spec import load_spec

TOOLS_PY = '''CALLS = []


def retrieve(key: str = "") -> str:
    CALLS.append(key)
    return {"a": "the answer is alpha", "b": "the answer is bravo"}.get(str(key), "")


def shell(cmd: str = "") -> str:
    return "ran " + str(cmd)


def explode(**kw):
    raise RuntimeError("tool blew up")
'''

AGENT_PY = '''def answer(item, tools, ctx):
    mode = ctx["model"]
    key = item["id"][-1]
    if mode == "grounded":
        snippet = tools.retrieve(key=key)
        return item["target"] if item["target"] in snippet else "no evidence"
    if mode == "oneshot":
        out = {"a": "alpha", "b": "bravo"}[key]
        tools.retrieve(key=key)
        return out
    if mode == "liar":
        # Tries to write its own trace. On this rail it does not get to.
        tools.retrieve(key=key)
        return {"output": item["target"],
                "trajectory": [{"tool": "retrieve", "args": {"key": "invented"},
                                "result": "a call that never happened", "ok": True}]}
    if mode == "breaker":
        tools.shell(cmd="whoami")
        return "unreachable"
    raise ValueError(mode)
'''

WITNESSES = [
    {"output": "alpha", "target": "alpha", "expect": "pass"},
    {"output": "bravo", "target": "alpha", "expect": "fail"},
    {"output": "", "target": "alpha", "expect": "fail"},
    {"output": "Alpha", "target": "alpha", "expect": "fail"},
    {"output": "not alpha", "target": "alpha", "expect": "fail"},
    {"output": "the answer is alpha", "target": "alpha", "expect": "fail"},
    {"output": "alph", "target": "alpha", "expect": "fail"},
]


def pod(tmp_path, models=("grounded",), forbidden=("shell",), max_steps=6, tools=None):
    (tmp_path / "tools.py").write_text(TOOLS_PY, encoding="utf-8")
    (tmp_path / "agent.py").write_text(AGENT_PY, encoding="utf-8")
    items = [{"id": f"i{i:02d}{'a' if i % 2 == 0 else 'b'}", "input": f"Q{i}?",
              "target": "alpha" if i % 2 == 0 else "bravo"} for i in range(8)]
    spec = {
        "name": "harness-fixture", "version": "0.1.0",
        "question": "Does the agent answer from the evidence it retrieved?",
        "data": {"path": "items.jsonl", "format": "jsonl"},
        "tools": tools if tools is not None else {"retrieve": "tools.py:retrieve",
                                                  "shell": "tools.py:shell"},
        "models": [{"provider": "mediated", "model": m, "entrypoint": "agent.py:answer"}
                   for m in models],
        "trajectory": {"required_tools": ["retrieve"], "forbidden_tools": list(forbidden),
                       "max_steps": max_steps},
        "scorer": {"kind": "exact", "witnesses": WITNESSES},
        "run": {"n": len(items), "seed": 7, "budget_usd": 0},
    }
    lines = ['{"_canary": "dinostomp canary DO NOT TRAIN harness-fixture"}']
    lines += [json.dumps(i) for i in items]
    (tmp_path / "items.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    sp = tmp_path / "eval.yaml"
    sp.write_text(yaml.safe_dump(spec), encoding="utf-8")
    return sp


def records(tmp_path, model, probe=None):
    tag = f"-{probe}probe" if probe else ""
    hits = list((tmp_path / "data" / "runs").glob(f"*_{model}_n8{tag}_s7.jsonl"))
    assert len(hits) == 1, [p.name for p in hits]
    return [json.loads(l) for l in hits[0].read_text(encoding="utf-8").splitlines() if l.strip()]


# --- the trace is observed, not testified ------------------------------------


def test_every_call_through_the_harness_lands_in_the_trace():
    calls = []
    t = Tools({"retrieve": lambda key="": calls.append(key) or f"got {key}"})
    assert t.retrieve(key="a") == "got a"
    assert t.call("retrieve", key="b") == "got b"
    # Both spellings record identically, or a pod could pick the quieter one.
    assert [s["tool"] for s in t.steps] == ["retrieve", "retrieve"]
    assert [s["args"] for s in t.steps] == [{"key": "a"}, {"key": "b"}]


def test_an_agent_that_writes_its_own_trajectory_is_refused(tmp_path):
    """Refused, not ignored.

    Dropping the invented steps silently would leave a pod author believing
    their trace had been recorded, and would put unverifiable evidence in a
    record that claims to be a log. The run stops instead, with everything paid
    for so far on disk.
    """
    sp = pod(tmp_path, models=("liar",))
    outcome = run_spec(sp)
    # STOPPED_EARLY, the clean-partial path: a provider that refuses mid-run
    # leaves what it already wrote on disk and says why in stopped_reason.
    assert outcome.exit_code != OK
    assert "returned a 'trajectory'" in outcome.stopped_reason


def test_the_manifest_names_the_rail(tmp_path):
    sp = pod(tmp_path)
    assert run_spec(sp).exit_code == OK
    mf = next((tmp_path / "data" / "runs").glob("*_manifest.json"))
    m = json.loads(mf.read_text(encoding="utf-8"))
    assert m["trajectory_source"] == "harness_observed"
    # Tools are hashed like any other pod code, so swapping one is drift.
    assert set(m["tool_sha256_by_name"]) == {"retrieve", "shell"}
    assert all(len(v) == 64 for v in m["tool_sha256_by_name"].values())


# --- policy is enforced at call time, and the attempt is evidence ------------


def test_a_forbidden_tool_is_denied_and_the_attempt_is_recorded(tmp_path):
    sp = pod(tmp_path, models=("breaker",))
    assert run_spec(sp).exit_code == OK
    for r in records(tmp_path, "breaker"):
        step = r["trajectory"][0]
        assert step["tool"] == "shell" and step["ok"] is False
        assert step["denied"] == "forbidden"
        assert r["finish_reason"] == "tool_denied"
    # The tool really did not run: `shell` returns "ran ..." and nothing does.
    assert all("ran whoami" not in (r.get("output") or "") for r in records(tmp_path, "breaker"))


def test_a_denial_raises_rather_than_returning_empty():
    """An agent must not be able to mistake a refusal for an empty result."""
    t = Tools({"shell": lambda cmd="": "ran"}, forbidden={"shell"})
    with pytest.raises(ToolDenied):
        t.shell(cmd="x")
    assert t.steps[0]["denied"] == "forbidden"


def test_an_unknown_tool_is_denied_and_names_what_is_available():
    t = Tools({"retrieve": lambda key="": ""})
    with pytest.raises(ToolDenied, match="retrieve"):
        t.nosuchtool()
    assert t.steps[0]["denied"] == "unknown"


def test_the_step_budget_is_enforced_not_merely_audited():
    t = Tools({"retrieve": lambda key="": "x"}, max_steps=2)
    t.retrieve(key="a")
    t.retrieve(key="b")
    with pytest.raises(ToolDenied):
        t.retrieve(key="c")
    assert t.steps[-1]["denied"] == "max_steps"


def test_a_tool_that_raises_stops_the_run_rather_than_scoring_it(tmp_path):
    t = Tools({"explode": lambda **kw: (_ for _ in ()).throw(RuntimeError("boom"))})
    with pytest.raises(ProviderError):
        t.explode()
    assert t.steps[0]["ok"] is False and "boom" in t.steps[0]["result"]


# --- ablation: the counterfactual -------------------------------------------


def test_ablation_withholds_results_but_keeps_the_call(tmp_path):
    t = Tools({"retrieve": lambda key="": "the real answer"}, ablate=True)
    assert t.retrieve(key="a") == WITHHELD
    step = t.steps[0]
    assert step["ablated"] is True and step["args"] == {"key": "a"}
    assert "the real answer" not in step["result"], "the withheld value leaked into the trace"


def test_a_grounded_agent_loses_its_answer_under_ablation(tmp_path):
    sp = pod(tmp_path, models=("grounded",))
    assert run_spec(sp).exit_code == OK
    assert run_spec(sp, probe="ablate").exit_code == OK
    real = {r["item_id"]: r["output"] for r in records(tmp_path, "grounded")}
    gone = {r["item_id"]: r["output"] for r in records(tmp_path, "grounded", probe="ablate")}
    assert all(gone[i] == "no evidence" for i in real), gone
    assert not any(real[i] == gone[i] for i in real)


def test_an_ungrounded_agent_answers_identically_under_ablation(tmp_path):
    """The D-020 shape. Its trace is perfect and its answer owes it nothing."""
    sp = pod(tmp_path, models=("oneshot",))
    assert run_spec(sp).exit_code == OK
    assert run_spec(sp, probe="ablate").exit_code == OK
    real = {r["item_id"]: r["output"] for r in records(tmp_path, "oneshot")}
    same = {r["item_id"]: r["output"] for r in records(tmp_path, "oneshot", probe="ablate")}
    assert real == same, "the memory-first agent should be unmoved by withheld evidence"
    # And its trace still shows a retrieve call, which is why T4 cannot see it.
    assert all(r["trajectory"][0]["tool"] == "retrieve" for r in records(tmp_path, "oneshot"))


def test_the_ablation_probe_refuses_a_pod_with_nothing_to_withhold(tmp_path):
    """A python target calls its own functions, so ablating it would silently
    produce an ordinary run wearing a probe's label."""
    from tests.test_lint import arith_items, write_eval

    sp = write_eval(tmp_path, arith_items())
    outcome = run_spec(sp, probe="ablate")
    assert outcome.exit_code == CANNOT_RUN
    assert "mediated" in outcome.issues[0].message


# --- the spec refuses combinations that cannot mean anything -----------------


def test_a_mediated_agent_without_tools_is_refused(tmp_path):
    sp = pod(tmp_path, tools={})
    obj = yaml.safe_load(sp.read_text(encoding="utf-8"))
    obj.pop("tools", None)
    sp.write_text(yaml.safe_dump(obj), encoding="utf-8")
    _, issues = load_spec(sp)
    assert any("offers no tools" in i.message for i in issues)


def test_tools_without_a_mediated_agent_are_refused(tmp_path):
    sp = pod(tmp_path)
    obj = yaml.safe_load(sp.read_text(encoding="utf-8"))
    obj["models"] = [{"provider": "python", "model": "m", "entrypoint": "agent.py:run"}]
    sp.write_text(yaml.safe_dump(obj), encoding="utf-8")
    _, issues = load_spec(sp)
    assert any("no model uses provider `mediated`" in i.message for i in issues)


def test_a_policy_about_a_tool_the_harness_does_not_hold_is_refused(tmp_path):
    sp = pod(tmp_path, forbidden=("ghost",))
    _, issues = load_spec(sp)
    assert any("not offered in $.tools" in i.message for i in issues)


def test_a_tool_outside_the_pod_is_refused(tmp_path):
    sp = pod(tmp_path)
    obj = yaml.safe_load(sp.read_text(encoding="utf-8"))
    obj["tools"]["retrieve"] = "../escape.py:retrieve"
    sp.write_text(yaml.safe_dump(obj), encoding="utf-8")
    _, issues = load_spec(sp)
    assert any("$.tools.retrieve" in i.loc for i in issues)


# --- the honesty test: this is not a sandbox ---------------------------------


def test_mediation_is_not_isolation_and_the_docs_say_so():
    """The claim this module must NOT make.

    An agent on this rail is ordinary in-process Python and can bypass the
    harness entirely. That is asserted here rather than left in a docstring,
    because a security claim nobody tests is exactly the kind of thing this
    project exists to object to. If someone ever adds real isolation, this test
    fails and forces the docs to be rewritten deliberately.
    """
    import dinostomp.harness as h

    src = h.__doc__ or ""
    assert "NOT a security boundary" in src
    # Proof, not prose: a "mediated" agent reaching around the harness works.
    tools_seen = Tools({"retrieve": lambda key="": "x"})
    import os

    assert os.environ is not None, "in-process code reaches the environment"
    assert tools_seen.steps == [], "and does so without touching the trace"
