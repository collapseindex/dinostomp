"""Spec-declared pricing: the rate a run was charged at is part of the pod.

A rate typed at a shell prompt is gone the moment the command scrolls away. A
rate declared in the spec is inside spec_sha256, so it is published with the
pod, re-derived by anyone who verifies it, and any later edit is drift.
"""

import json

import yaml

from dinostomp.lint import lint_eval
from dinostomp.runner import CANNOT_RUN, OK, resolve_rates, run_spec

RATES = {"price_in": 0.5, "price_out": 1.5}


def make_pod(tmp_path, model_extra=None, budget=1.0, provider="dry"):
    pod = tmp_path / "pod"
    pod.mkdir(parents=True, exist_ok=True)
    items = [{"id": f"a{i}", "input": f"What is {i} + {i + 1}? Reply with the bare number.",
              "target": str(2 * i + 1)} for i in range(10, 34)]
    model = {"provider": provider, "model": "priced-model", **(model_extra or {})}
    spec = {
        "name": "priced-pod", "version": "0.1.0",
        "question": "Does the model answer two-digit addition with the bare number?",
        "data": {"path": "items.jsonl", "format": "jsonl"},
        "models": [model],
        "scorer": {"kind": "exact", "witnesses": [
            {"output": "57", "target": "57", "expect": "pass"},
            {"output": "The answer is 57", "target": "57", "expect": "fail"},
            {"output": "5", "target": "57", "expect": "fail"},
            {"output": "not 57", "target": "57", "expect": "fail"},
        ]},
        "run": {"n": 24, "seed": 42, "budget_usd": budget},
    }
    lines = ['{"_canary": "dinostomp canary DO NOT TRAIN pricing"}']
    lines += [json.dumps(i) for i in items]
    (pod / "items.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (pod / "eval.yaml").write_text(yaml.safe_dump(spec), encoding="utf-8")
    return pod / "eval.yaml"


def test_spec_rates_beat_flags_and_the_table():
    # Precedence matters: the spec is the only source that is hashed.
    assert resolve_rates("openrouter", "x", 9.0, 9.0, 0.5, 1.5) == (0.5, 1.5, "spec")
    assert resolve_rates("openrouter", "x", 9.0, 9.0, None, None) == (9.0, 9.0, "explicit")
    assert resolve_rates("openrouter", "unknown-model", None, None, None, None)[2] == "unpriced"


def test_a_dry_model_with_spec_rates_is_priced_by_them(tmp_path):
    spec = make_pod(tmp_path, model_extra=RATES)
    outcome = run_spec(spec)
    assert outcome.exit_code == OK
    record = json.loads(outcome.run_files[0].read_text(encoding="utf-8").splitlines()[0])
    assert record["usage"]["rate_label"] == "spec", "provenance of the price is recorded, not just the price"
    assert record["usage"]["cost_usd"] > 0, "declared rates actually bill"


def test_the_manifest_carries_the_declared_rates(tmp_path):
    spec = make_pod(tmp_path, model_extra=RATES)
    outcome = run_spec(spec)
    manifest = json.loads(outcome.run_files[0].with_name(
        outcome.run_files[0].stem + "_manifest.json").read_text(encoding="utf-8"))
    assert (manifest["rate_in_per_mtok"], manifest["rate_out_per_mtok"]) == (0.5, 1.5)


def test_editing_a_rate_after_the_run_is_drift(tmp_path):
    # The whole reason rates belong in the spec: repricing history is caught.
    spec = make_pod(tmp_path, model_extra=RATES)
    assert run_spec(spec).exit_code == OK
    obj = yaml.safe_load(spec.read_text(encoding="utf-8"))
    obj["models"][0]["price_in"] = 0.0001
    spec.write_text(yaml.safe_dump(obj), encoding="utf-8")
    report, _ = lint_eval(spec)
    assert next(f for f in report["findings"] if f["id"] == "R1")["level"] == "fail"


def test_half_a_price_is_rejected_at_load_time(tmp_path):
    spec = make_pod(tmp_path, model_extra={"price_in": 0.5})
    from dinostomp.spec import load_spec
    _, issues = load_spec(spec)
    assert issues, "price_in without price_out cannot bill anything"


def test_the_manifest_total_equals_the_sum_of_its_records(tmp_path):
    """R3's identity has to survive many tiny costs, not just zero.

    Found live: small models bill fractions of a microdollar per call, and
    rounding each of 120 records to six decimals accumulated ~3e-5 of drift,
    which is 30x R3's tolerance. Every dry pod passed because every dry cost
    was exactly 0.00, so the money invariant had only ever been tested at zero.
    """
    spec = make_pod(tmp_path, model_extra={"price_in": 0.0031, "price_out": 0.0017})
    outcome = run_spec(spec)
    assert outcome.exit_code == OK

    records = [json.loads(l) for l in
               outcome.run_files[0].read_text(encoding="utf-8").splitlines() if l.strip()]
    ledger = sum(r["usage"]["cost_usd"] for r in records)
    manifest = json.loads(outcome.run_files[0].with_name(
        outcome.run_files[0].stem + "_manifest.json").read_text(encoding="utf-8"))

    assert ledger > 0, "the fixture must actually bill something, or it proves nothing"
    assert abs(manifest["spend_usd"] - ledger) <= 1e-6, (
        f"manifest ${manifest['spend_usd']} vs ledger ${ledger}: per-record rounding drifted")

    report, _ = lint_eval(spec)
    assert next(f for f in report["findings"] if f["id"] == "R3")["level"] == "pass"


def test_an_unpriced_network_model_refuses_to_run(tmp_path):
    # A model that cannot be priced cannot be capped, and an uncapped run is
    # not a run this tool will start.
    spec = make_pod(tmp_path, provider="openrouter")
    outcome = run_spec(spec)
    assert outcome.exit_code == CANNOT_RUN
    assert any("no known price" in i.message for i in outcome.issues)


def test_plan_never_prints_zero_for_a_self_funded_target(tmp_path, capsys):
    """A python target that pays for its own model calls cannot be forecast.

    Printing $0.0000 for it would be the one thing `plan` must never do:
    understate a bill. It says so instead.
    """
    from dinostomp.cli import main

    pod = tmp_path / "pod"
    pod.mkdir(parents=True, exist_ok=True)
    (pod / "agent.py").write_text(
        'def run(item, ctx):\n    return {"output": "0", "cost_usd": 0.01}\n', encoding="utf-8")
    spec = make_pod(tmp_path)
    obj = yaml.safe_load(spec.read_text(encoding="utf-8"))
    obj["models"] = [{"provider": "python", "model": "agent-a", "entrypoint": "agent.py:run"}]
    spec.write_text(yaml.safe_dump(obj), encoding="utf-8")

    assert main(["plan", str(spec)]) == 0
    out = capsys.readouterr().out
    assert "price their own calls" in out
    assert "NOT forecastable" in out
