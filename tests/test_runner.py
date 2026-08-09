"""Runner tests. The paid-run rules each get a test that simulates the
failure they exist for: blown budget, dead provider mid-run, interrupted run.
"""

import json
import re
from pathlib import Path

import pytest
import yaml

from dinostomp import validate_obj
from dinostomp.providers import Completion, ProviderError
from dinostomp.runner import CANNOT_RUN, GATED, OK, STOPPED_EARLY, run_spec, summarize

REPO = Path(__file__).resolve().parents[1]
SMOKE = REPO / "examples" / "smoke"


def make_eval(tmp_path: Path, mutate=None) -> Path:
    """Copy the smoke eval into tmp and optionally mutate the spec."""
    spec = yaml.safe_load((SMOKE / "eval.yaml").read_text(encoding="utf-8"))
    if mutate:
        mutate(spec)
    (tmp_path / "items.jsonl").write_text((SMOKE / "items.jsonl").read_text(encoding="utf-8"), encoding="utf-8")
    p = tmp_path / "eval.yaml"
    p.write_text(yaml.safe_dump(spec), encoding="utf-8")
    return p


class CountingProvider:
    """Deterministic paid-looking provider for budget/resume/crash tests."""

    calls = 0
    fail_on_call: int | None = None

    def __init__(self, model: str):
        self.model = model

    def complete(self, item, seed, params):
        type(self).calls += 1
        if type(self).fail_on_call is not None and type(self).calls >= type(self).fail_on_call:
            raise ProviderError("simulated provider death")
        first = str(item["target"][0] if isinstance(item["target"], list) else item["target"])
        # honest worst case: spends the full max_tokens the spec asked for
        return Completion(text=first, input_tokens=0, output_tokens=200_000)


@pytest.fixture(autouse=True)
def _reset_counting_provider():
    CountingProvider.calls = 0
    CountingProvider.fail_on_call = None


def counting_factory(provider, model):
    return CountingProvider(model)


def paid_spec(spec):
    """Turn the smoke spec into a fake-paid one: $0.40 per call at these rates."""
    spec["models"] = [{"provider": "openai", "model": "fake-model", "params": {"max_tokens": 200_000}}]
    spec["run"]["budget_usd"] = 1.0


PRICES = dict(price_in=2.0, price_out=2.0)  # 200k tokens/call at $2/MTok = $0.40


# --- the happy path -----------------------------------------------------------


def test_dry_run_completes_and_artifacts_validate(tmp_path):
    outcome = run_spec(make_eval(tmp_path))
    assert outcome.exit_code == OK
    assert len(outcome.run_files) == 1

    records = [json.loads(l) for l in outcome.run_files[0].read_text(encoding="utf-8").splitlines()]
    assert len(records) == 6
    for rec in records:
        assert validate_obj(rec, "record") == [], rec

    manifest_path = outcome.run_files[0].with_name(outcome.run_files[0].stem + "_manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert validate_obj(manifest, "manifest") == []
    assert manifest["witness_report"]["verdict"] == "validated"
    assert manifest["status"] == "complete"


def test_run_filename_follows_convention(tmp_path):
    outcome = run_spec(make_eval(tmp_path))
    name = outcome.run_files[0].name
    assert re.fullmatch(r"\d{8}_\d{6}_smoke-arith_dry-strong_n6_s42\.jsonl", name), name


def test_dry_provider_is_deterministic(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    a = run_spec(make_eval(tmp_path / "a"))
    b = run_spec(make_eval(tmp_path / "b"))
    strip = lambda p: [
        {k: v for k, v in json.loads(l).items() if k != "ts"}
        for l in p.read_text(encoding="utf-8").splitlines()
    ]
    assert strip(a.run_files[0]) == strip(b.run_files[0])


# --- the witness gate -----------------------------------------------------------


def test_misbehaving_witness_blocks_the_run(tmp_path):
    def sabotage(spec):
        # scorer 'includes' credits substrings, so the wrapped-answer witness
        # (expect: fail) misbehaves. Exactly the bug the gate exists to catch:
        # a laxer scorer silently inflating scores.
        spec["scorer"]["kind"] = "includes"

    outcome = run_spec(make_eval(tmp_path, sabotage))
    assert outcome.exit_code == GATED
    assert outcome.witness_failures
    assert not (tmp_path / "data").exists(), "gated run must write nothing"


# --- money rules -----------------------------------------------------------------


def test_budget_stops_the_run_before_overspend(tmp_path):
    outcome = run_spec(make_eval(tmp_path, paid_spec), provider_factory=counting_factory, **PRICES)
    assert outcome.exit_code == STOPPED_EARLY
    assert "budget" in outcome.stopped_reason
    # $1 cap at $0.40/call: exactly 2 calls, the third is refused before it happens
    assert CountingProvider.calls == 2
    records = outcome.run_files[0].read_text(encoding="utf-8").splitlines()
    assert len(records) == 2
    manifest = json.loads(
        outcome.run_files[0].with_name(outcome.run_files[0].stem + "_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["status"] == "stopped_early"
    assert manifest["spend_usd"] <= 1.0


def test_unpriced_network_model_refused_without_rates(tmp_path):
    outcome = run_spec(make_eval(tmp_path, paid_spec), provider_factory=counting_factory)
    assert outcome.exit_code == CANNOT_RUN
    assert any("price" in i.message for i in outcome.issues)
    assert CountingProvider.calls == 0


def test_network_provider_with_zero_budget_refused(tmp_path):
    def broke(spec):
        paid_spec(spec)
        spec["run"]["budget_usd"] = 0

    outcome = run_spec(make_eval(tmp_path, broke), provider_factory=counting_factory, **PRICES)
    assert outcome.exit_code == CANNOT_RUN
    assert CountingProvider.calls == 0


# --- interruption and resume ------------------------------------------------------


def test_provider_death_leaves_clean_partial(tmp_path):
    CountingProvider.fail_on_call = 3
    def cheap(spec):
        paid_spec(spec)
        spec["run"]["budget_usd"] = 100.0

    outcome = run_spec(make_eval(tmp_path, cheap), provider_factory=counting_factory, **PRICES)
    assert outcome.exit_code == STOPPED_EARLY
    assert "provider" in outcome.stopped_reason
    records = outcome.run_files[0].read_text(encoding="utf-8").splitlines()
    assert len(records) == 2, "the two completed calls survived the crash"


def test_resume_never_repays_finished_items(tmp_path):
    CountingProvider.fail_on_call = 3
    def cheap(spec):
        paid_spec(spec)
        spec["run"]["budget_usd"] = 100.0

    spec_path = make_eval(tmp_path, cheap)
    first = run_spec(spec_path, provider_factory=counting_factory, **PRICES)
    assert first.exit_code == STOPPED_EARLY

    CountingProvider.fail_on_call = None
    calls_before = CountingProvider.calls
    second = run_spec(spec_path, resume=first.run_files[0], provider_factory=counting_factory, **PRICES)
    assert second.exit_code == OK
    # 6 items total, 2 already on disk: exactly 4 new calls
    assert CountingProvider.calls - calls_before == 4
    records = second.run_files[0].read_text(encoding="utf-8").splitlines()
    assert len(records) == 6
    manifest = json.loads(
        second.run_files[0].with_name(second.run_files[0].stem + "_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["prior_spend_usd"] == pytest.approx(0.8)
    assert manifest["status"] == "complete"


def test_torn_final_line_does_not_break_resume(tmp_path):
    CountingProvider.fail_on_call = 4
    def cheap(spec):
        paid_spec(spec)
        spec["run"]["budget_usd"] = 100.0

    spec_path = make_eval(tmp_path, cheap)
    first = run_spec(spec_path, provider_factory=counting_factory, **PRICES)
    # simulate a hard kill mid-write: truncate the last line
    raw = first.run_files[0].read_text(encoding="utf-8")
    first.run_files[0].write_text(raw[: len(raw) - 30], encoding="utf-8")

    CountingProvider.fail_on_call = None
    second = run_spec(spec_path, resume=first.run_files[0], provider_factory=counting_factory, **PRICES)
    assert second.exit_code == OK

    def parse_key(line):
        try:
            return json.loads(line)["key"]
        except json.JSONDecodeError:
            return None

    keys = [k for k in (parse_key(l) for l in second.run_files[0].read_text(encoding="utf-8").splitlines() if l.strip()) if k]
    # the torn record was redone; all 6 items present exactly once among parseable lines
    assert len(keys) == len(set(keys)) == 6


def test_resume_refuses_when_data_changed(tmp_path):
    CountingProvider.fail_on_call = 3
    def cheap(spec):
        paid_spec(spec)
        spec["run"]["budget_usd"] = 100.0

    spec_path = make_eval(tmp_path, cheap)
    first = run_spec(spec_path, provider_factory=counting_factory, **PRICES)
    assert first.exit_code == STOPPED_EARLY

    items_file = tmp_path / "items.jsonl"
    items_file.write_text(items_file.read_text(encoding="utf-8") + '{"id": "a7", "input": "9 + 9 = ?", "target": "18"}\n', encoding="utf-8")

    CountingProvider.fail_on_call = None
    calls_before = CountingProvider.calls
    second = run_spec(spec_path, resume=first.run_files[0], provider_factory=counting_factory, **PRICES)
    assert second.exit_code == CANNOT_RUN
    assert any("data" in i.message for i in second.issues)
    assert CountingProvider.calls == calls_before, "a refused resume must not spend a cent"


def test_multimodel_resume_only_continues_the_interrupted_model(tmp_path):
    CountingProvider.fail_on_call = 3
    def two_models(spec):
        paid_spec(spec)
        spec["run"]["budget_usd"] = 100.0
        spec["models"] = [
            {"provider": "openai", "model": "fake-a", "params": {"max_tokens": 200_000}},
            {"provider": "openai", "model": "fake-b", "params": {"max_tokens": 200_000}},
        ]

    spec_path = make_eval(tmp_path, two_models)
    first = run_spec(spec_path, provider_factory=counting_factory, **PRICES)
    assert first.exit_code == STOPPED_EARLY
    assert len(first.run_files) == 1, "model B must not start after model A died"

    CountingProvider.fail_on_call = None
    second = run_spec(spec_path, resume=first.run_files[0], provider_factory=counting_factory, **PRICES)
    assert second.exit_code == OK
    assert len(second.run_files) == 1, "resume continues fake-a only, never starts fake-b"
    manifest = json.loads(
        second.run_files[0].with_name(second.run_files[0].stem + "_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["model"] == "fake-a"
    keys = [json.loads(l)["key"] for l in second.run_files[0].read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(keys) == len(set(keys)) == 6


def test_colliding_model_slugs_get_distinct_ledgers(tmp_path):
    def twins(spec):
        spec["models"] = [
            {"provider": "dry", "model": "dry_twin"},
            {"provider": "dry", "model": "dry-twin"},
        ]

    outcome = run_spec(make_eval(tmp_path, twins))
    assert outcome.exit_code == OK
    assert len(outcome.run_files) == 2
    assert outcome.run_files[0] != outcome.run_files[1]
    for rf in outcome.run_files:
        records = [json.loads(l) for l in rf.read_text(encoding="utf-8").splitlines()]
        assert len(records) == 6, "each twin runs all items in its own ledger"
        assert len({r["model"] for r in records}) == 1


def test_resume_with_dry_run_refused_on_paid_ledger(tmp_path):
    CountingProvider.fail_on_call = 3
    def cheap(spec):
        paid_spec(spec)
        spec["run"]["budget_usd"] = 100.0

    spec_path = make_eval(tmp_path, cheap)
    first = run_spec(spec_path, provider_factory=counting_factory, **PRICES)
    assert first.exit_code == STOPPED_EARLY

    second = run_spec(spec_path, resume=first.run_files[0], dry_run=True,
                      provider_factory=counting_factory, **PRICES)
    assert second.exit_code == CANNOT_RUN
    assert any("paid ledger" in i.message for i in second.issues)


def test_atomic_write_survives_transient_windows_locks(tmp_path, monkeypatch):
    """A virus scanner grabbing the fresh temp file must not kill a paid run:
    the rename retries through transient PermissionErrors."""
    import os as real_os

    from dinostomp import runlog

    calls = {"n": 0}
    original = real_os.replace

    def flaky_replace(src, dst):
        calls["n"] += 1
        if calls["n"] <= 2:
            raise PermissionError(32, "file in use", str(src))
        return original(src, dst)

    monkeypatch.setattr(runlog.os, "replace", flaky_replace)
    monkeypatch.setattr(runlog, "REPLACE_RETRY_DELAY_S", 0)
    target = tmp_path / "m.json"
    runlog._atomic_write_json(target, {"ok": True})
    assert json.loads(target.read_text(encoding="utf-8")) == {"ok": True}
    assert calls["n"] == 3, "two transient locks survived, third attempt landed"


def test_manifest_carries_the_full_drift_boundary(tmp_path):
    outcome = run_spec(make_eval(tmp_path))
    manifest = json.loads(
        outcome.run_files[0].with_name(outcome.run_files[0].stem + "_manifest.json").read_text(encoding="utf-8")
    )
    import hashlib
    assert manifest["data_sha256"] == hashlib.sha256((tmp_path / "items.jsonl").read_bytes()).hexdigest()


# --- aggregation ---------------------------------------------------------------------


def test_summarize_excludes_uncheckable_from_denominator():
    records = [
        {"item_id": "a", "score": {"verdict": "pass"}, "usage": {"cost_usd": 0.1}},
        {"item_id": "b", "score": {"verdict": "fail"}, "usage": {"cost_usd": 0.1}},
        {"item_id": "c", "score": {"verdict": "uncheckable"}, "usage": {"cost_usd": 0.1}},
        {"item_id": "d", "score": {"verdict": "pass"}, "usage": {}},
    ]
    s = summarize(records)
    assert s["estimator"] == "per_record"
    assert s["n_checkable"] == 3
    assert s["n_uncheckable"] == 1
    assert s["accuracy_on_checkable"] == pytest.approx(2 / 3)
    assert s["spend_usd"] == pytest.approx(0.3)


def test_summarize_repeats_switch_to_item_majority():
    """With repeats, the interval must bracket the same estimator the fleet
    matrix uses: item-majority outcomes computed over items, so correlated
    repeats cannot narrow it (reviewer-2 round 3, finding 1).

    A TIE is undecided, not failed. This assertion used to read "the b tie
    scores 0, conservative", and conservative was the wrong word: scoring ties 0
    changes the estimand rather than shading it. At repeats=2 a model with true
    per-item rate p reports p squared, which put a measured 50% model at 24%
    behind an interval that excluded the truth (N-008).
    """
    records = []
    for item, verdicts in (("a", ["pass", "pass"]), ("b", ["pass", "fail"]),
                           ("c", ["fail", "fail"]), ("d", ["uncheckable", "uncheckable"])):
        for v in verdicts:
            records.append({"item_id": item, "score": {"verdict": v}, "usage": {}})
    s = summarize(records)
    assert s["estimator"] == "item_majority"
    assert s["n_checkable"] == 2, "a and c decided; b tied and d was never scoreable"
    assert s["n_repeat_ties"] == 1, "b split its own vote"
    assert s["accuracy_on_checkable"] == pytest.approx(1 / 2)
    # Items, not records, in every count this estimator prints.
    assert s["n_uncheckable"] == 2, "the tie and the unscoreable item, both counted in items"
    assert s["judgeability"] == pytest.approx(2 / 4)
    lo, hi = s["accuracy_ci95"]
    assert hi - lo > 0.5, "an interval over 2 items is honestly enormous"


def test_summarize_odd_repeats_never_tie_and_are_unchanged():
    """The negative direction: the tie rule must not touch odd repeats, or the
    fix would silently re-estimate every pod already using them."""
    records = []
    for item, verdicts in (("a", ["pass", "pass", "fail"]), ("b", ["fail", "fail", "pass"])):
        for v in verdicts:
            records.append({"item_id": item, "score": {"verdict": v}, "usage": {}})
    s = summarize(records)
    assert s["estimator"] == "item_majority"
    assert s["n_repeat_ties"] == 0
    assert s["n_checkable"] == 2 and s["n_uncheckable"] == 0
    assert s["accuracy_on_checkable"] == pytest.approx(1 / 2)


def test_an_even_repeat_tie_does_not_report_zero_accuracy():
    """N-008 in miniature: 8 items, every one a 1-1 split, true rate 50%.

    Ties-score-0 reported 0% here. Undecided reports that nothing was decided,
    which is the honest answer and is visibly different from "the model failed".
    """
    records = [{"item_id": f"i{i}", "score": {"verdict": v}, "usage": {}}
               for i in range(8) for v in ("pass", "fail")]
    s = summarize(records)
    assert s["n_repeat_ties"] == 8
    assert s["n_checkable"] == 0
    assert s["accuracy_on_checkable"] is None, "no decided item is not 0% accuracy"
    assert s["judgeability"] == pytest.approx(0.0)


def test_summarize_all_uncheckable_reports_none_not_zero():
    s = summarize([{"score": {"verdict": "uncheckable"}, "usage": {}}])
    assert s["accuracy_on_checkable"] is None
