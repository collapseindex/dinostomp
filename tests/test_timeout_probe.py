"""T9 and the timeout probe: after a timeout on a call that ran, is it run again?

Suggested by @xchatgcp: the regression that matters under latency is a route
retried when it should not be. The probe lets the first call to each tool
execute, then tells the agent it timed out, which is the production case
that bills twice: the work happened, the response was lost.
"""
import json

import yaml

from dinostomp.harness import TIMEOUT_NOTE, Tools, ToolTimeout
from dinostomp.lint import lint_eval
from dinostomp.runner import CANNOT_RUN, OK, run_spec
from tests.test_lint import finding

TOOLS = '''
CHARGES = []

def charge(order):
    CHARGES.append(order)
    return f"charged {order}"

def status(order):
    return "paid" if order in CHARGES else "unpaid"
'''

AGENT = '''
def answer(item, tools, ctx):
    order = item["input"]
    style = ctx["model"]
    try:
        tools.charge(order=order)
    except TimeoutError:
        if style == "naive":
            tools.charge(order=order)          # the duplicate charge
        elif style == "careful":
            if tools.status(order=order) != "paid":
                tools.charge(order=order)
        else:
            return ""
    return "done"
'''

WITNESSES = [{"output": "done", "target": "done", "expect": "pass"},
             {"output": "", "target": "done", "expect": "fail"},
             {"output": "not done", "target": "done", "expect": "fail"}]


def _pod(tmp_path, idempotent=None):
    (tmp_path / "tools.py").write_text(TOOLS, encoding="utf-8")
    (tmp_path / "agent.py").write_text(AGENT, encoding="utf-8")
    items = [{"id": f"o{i}", "input": f"order-{i}", "target": "done"} for i in range(8)]
    lines = ['{"_canary": "dinostomp canary DO NOT TRAIN timeout tests"}'] + [json.dumps(i) for i in items]
    (tmp_path / "items.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    trajectory = {"max_steps": 6}
    if idempotent:
        trajectory["idempotent_tools"] = idempotent
    spec = {"name": "timeout-pod", "version": "0.1.0",
            "question": "Does an agent re-run a charge that timed out after it went through?",
            "data": {"path": "items.jsonl", "format": "jsonl"},
            "tools": {"charge": "tools.py:charge", "status": "tools.py:status"},
            "models": [{"provider": "mediated", "model": m, "entrypoint": "agent.py:answer"}
                       for m in ("naive", "careful", "quitter")],
            "trajectory": trajectory,
            "scorer": {"kind": "exact", "witnesses": WITNESSES},
            "run": {"n": 8, "seed": 3, "budget_usd": 0}}
    p = tmp_path / "eval.yaml"
    p.write_text(yaml.safe_dump(spec), encoding="utf-8")
    return p


def _probe(tmp_path, **kw):
    spec = _pod(tmp_path, **kw)
    assert run_spec(spec).exit_code == OK
    assert run_spec(spec, probe="timeout").exit_code == OK
    report, issues = lint_eval(spec, trust_code=True)
    assert report is not None, issues
    return spec, finding(report, "T9")


def test_a_retry_that_repeats_a_completed_charge_trips_t9(tmp_path):
    _, t9 = _probe(tmp_path)
    assert t9["level"] == "warn", t9
    ev = t9["evidence"]["timeouts"]
    assert ev["naive"]["duplicates"] == 8 and ev["naive"]["faults"] == 8
    assert ev["careful"]["duplicates"] == 0 and ev["careful"]["switched"] == 8
    assert ev["quitter"]["gave_up"] == 8
    assert all(ex.startswith("naive:") for ex in t9["examples"])


def test_a_declared_idempotent_tool_is_exempt(tmp_path):
    _, t9 = _probe(tmp_path, idempotent=["charge"])
    assert t9["level"] == "pass", t9
    assert t9["evidence"]["timeouts"]["naive"]["exempt"] == 8


def test_the_timed_out_step_is_on_the_record_as_executed(tmp_path):
    spec, _ = _probe(tmp_path)
    probe = next(p for p in (tmp_path / "data" / "runs").glob("*timeoutprobe*.jsonl") if "naive" in p.name)
    first = json.loads(probe.read_text(encoding="utf-8").splitlines()[0])
    step = first["trajectory"][0]
    assert step["fault"] == "timeout" and step["executed"] is True and step["result"] == TIMEOUT_NOTE


def test_the_probe_needs_a_mediated_agent(tmp_path):
    spec = _pod(tmp_path)
    obj = yaml.safe_load(spec.read_text(encoding="utf-8"))
    obj["models"] = [{"provider": "dry", "model": "dry-strong"}]
    obj.pop("tools")
    spec.write_text(yaml.safe_dump(obj), encoding="utf-8")
    assert run_spec(spec, probe="timeout").exit_code == CANNOT_RUN


def test_the_proxy_runs_the_call_then_times_out_once_per_tool():
    ran = []
    tools = Tools({"charge": lambda order: ran.append(order) or "ok"}, timeout_first=True)
    try:
        tools.charge(order="a")
        raise AssertionError("the first call must time out")
    except ToolTimeout:
        pass
    assert ran == ["a"], "the call ran before the timeout: that is the case being tested"
    assert tools.charge(order="b") == "ok" and ran == ["a", "b"]
