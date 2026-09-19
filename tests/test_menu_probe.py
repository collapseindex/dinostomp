"""P15 and the menu probe: does a right answer survive the tool list changing?

Suggested by @xchatgcp reviewing the onepass routing results: in production a
tool list changes under a router (a tool is added, retired, or renamed in a
schema change), and a router that was only right against the original list
is matching the list, not the request. The probe applies one such change per
item; the keyed answer and an abstain option are never touched.
"""
import json

import yaml

from dinostomp.lint import lint_eval
from dinostomp.providers import Completion
from dinostomp.runner import OK, menu_change, menu_pool, run_spec
from tests.test_lint import WITNESSES, finding

N = 40


def _items():
    out = []
    for i in range(N):
        tools = [f"tool_{i}_{k}" for k in range(3)] + ["NONE"]
        target = tools[i % 3]
        out.append({"id": f"r{i}", "input": f"Request {i}: please run {target}.", "target": target,
                    "choices": tools,
                    "metadata": {"options": {t: f"{t}: does thing {t}" for t in tools}}})
    return out


def _pod(tmp_path):
    items = _items()
    spec = {"name": "menu-pod", "version": "0.1.0",
            "question": "Does the router pick the named tool whatever else is on the list?",
            "data": {"path": "items.jsonl", "format": "jsonl"},
            "models": [{"provider": "openai", "model": "router", "price_in": 1.0, "price_out": 1.0}],
            "scorer": {"kind": "exact", "witnesses": WITNESSES},
            "run": {"n": N, "seed": 7, "budget_usd": 1.0}}
    lines = ['{"_canary": "dinostomp canary DO NOT TRAIN menu tests"}'] + [json.dumps(i) for i in items]
    (tmp_path / "items.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    p = tmp_path / "eval.yaml"
    p.write_text(yaml.safe_dump(spec), encoding="utf-8")
    return p


class Router:
    """Reads the request for the tool name. `fragile` routers only trust a
    list exactly as it was built, and fall back to the first option otherwise."""

    def __init__(self, fragile: bool):
        self.fragile = fragile

    def complete(self, item, seed, params):
        menu = item.get("choices") or []
        named = next((t for t in menu if t in item["input"]), "NONE")
        if self.fragile and (len(menu) != 4 or any(t.endswith("_v2") for t in menu)):
            named = menu[0]
        return Completion(text=named, input_tokens=10, output_tokens=1)


def _run(tmp_path, fragile):
    spec = _pod(tmp_path)
    factory = lambda p, m, **kw: Router(fragile)                          # noqa: E731
    assert run_spec(spec, provider_factory=factory).exit_code == OK
    assert run_spec(spec, probe="menu", provider_factory=factory).exit_code == OK
    report, issues = lint_eval(spec)
    assert report is not None, issues
    return spec, finding(report, "P15")


def test_a_router_that_matches_the_list_trips_p15(tmp_path):
    _, p15 = _run(tmp_path, fragile=True)
    assert p15["level"] == "warn", p15
    ev = p15["evidence"]["menu"]["router"]
    assert ev["lost"] > 0 and set(ev["lost_by_kind"]) <= {"add", "remove", "rename"}
    assert "breaks" in p15["examples"][0]


def test_a_router_that_reads_the_request_passes_p15(tmp_path):
    _, p15 = _run(tmp_path, fragile=False)
    assert p15["level"] == "pass", p15


def test_every_menu_record_says_what_changed(tmp_path):
    spec, _ = _run(tmp_path, fragile=False)
    probe = next((tmp_path / "data" / "runs").glob("*menuprobe*.jsonl"))
    kinds = [json.loads(l)["perturbation"].split(":")[1] for l in probe.read_text(encoding="utf-8").splitlines()]
    assert len(kinds) == N and set(kinds) == {"add", "remove", "rename"}


# --- the transform on its own --------------------------------------------------


def test_the_keyed_answer_and_the_abstain_option_are_never_touched():
    items = _items()
    pool = menu_pool(items)
    assert all(name != "NONE" for name, _ in pool), "an abstain option is not a tool to add"
    for seed in range(5):
        for it in items:
            changed, what = menu_change(it, seed, pool)
            assert it["target"] in changed["choices"] and "NONE" in changed["choices"]
            assert set(changed["metadata"]["options"]) == set(changed["choices"])
            kind = what.split(":")[1]
            if kind == "rename":
                old, new = what.split(":", 2)[2].split("->")
                assert new == old + "_v2" and old != it["target"]
                assert new in changed["metadata"]["options"][new]
            if kind == "remove":
                assert len(changed["choices"]) == len(it["choices"]) - 1


def test_the_change_is_deterministic_and_an_added_tool_comes_from_elsewhere():
    items = _items()
    pool = menu_pool(items)
    a = [menu_change(it, 7, pool) for it in items]
    b = [menu_change(it, 7, pool) for it in items]
    assert a == b
    for it, (changed, what) in zip(items, a):
        if what.startswith("menu:add:"):
            added = what.split(":", 2)[2]
            assert added not in it["choices"] and added in changed["choices"]


def test_an_item_without_a_menu_is_left_alone():
    assert menu_change({"id": "x", "input": "q", "target": "a"}, 1, []) is None
