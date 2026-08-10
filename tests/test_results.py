"""The RESULTS half of a report: what the models did.

The tests that matter here are PARITY tests. Every number in the results block
also exists somewhere else (a run summary on disk, a check's evidence, the CLI
line), and this project's own Law 2 says one quantity gets one value. Two
accuracies for one model is the defect, not a rounding disagreement.
"""

import json
import shutil
from pathlib import Path

import pytest

from dinostomp import results
from dinostomp.lint import lint_eval
from dinostomp.report import render_markdown

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def fleet_report():
    report, issues = lint_eval(REPO / "examples" / "fleet" / "eval.yaml")
    assert report is not None, issues
    return report


# --- parity: one quantity, one value -----------------------------------------


def test_results_accuracy_equals_the_accuracy_the_checks_report(fleet_report):
    """R7 publishes per-model accuracy in its evidence. If the results table
    disagreed with it, the report would state a model's score twice and
    differently, which is the class of defect R9 gates on elsewhere."""
    r7 = next(f for f in fleet_report["findings"] if f["id"] == "R7")
    from_check = r7["evidence"]["per_model_accuracy"]
    from_results = {m["model"]: m["accuracy"] for m in fleet_report["results"]["models"]}
    assert from_results.keys() == from_check.keys()
    for model, acc in from_check.items():
        assert abs(from_results[model] - acc) < 1e-3, (
            f"{model}: results say {from_results[model]}, R7 says {acc}")


def test_results_accuracy_equals_the_summary_written_at_run_time(fleet_report):
    """The runner wrote a summary per run. Results are recomputed from records
    and must land on the same number WITHOUT reading that summary: R9 is the
    check that catches a summary which stopped matching, and the results table
    must not be the one place a stale summary survives."""
    pod = REPO / "examples" / "fleet"
    on_disk = {}
    for path in sorted((pod / "data" / "results").glob("*_summary.json")):
        if "probe" in path.name:
            continue
        s = json.loads(path.read_text(encoding="utf-8"))
        on_disk[s["model"]] = s["accuracy_on_checkable"]
    computed = {m["model"]: m["accuracy"] for m in fleet_report["results"]["models"]}
    assert on_disk, "no summaries on disk to compare against"
    for model, acc in on_disk.items():
        assert abs(computed[model] - acc) < 1e-3, (
            f"{model}: recomputed {computed[model]}, summary on disk says {acc}")


def test_fleet_aggregates_match_the_psychometrics_checks(fleet_report):
    res = fleet_report["results"]["fleet"]
    p1 = next(f for f in fleet_report["findings"] if f["id"] == "P1")
    p8 = next(f for f in fleet_report["findings"] if f["id"] == "P8")
    assert abs(res["kr20"] - p1["evidence"]["kr20"]) < 1e-3
    assert abs(res["spread"] - p8["evidence"]["spread"]) < 1e-3


# --- the accuracy denominator ------------------------------------------------


def test_uncheckable_records_stay_out_of_the_accuracy_denominator():
    entries = [{
        "manifest": {"model": "m", "provider": "p", "dry_run": True},
        "records": [
            {"model": "m", "score": {"verdict": "pass"}, "output": "a"},
            {"model": "m", "score": {"verdict": "fail"}, "output": "b"},
            {"model": "m", "score": {"verdict": "uncheckable"}, "output": ""},
            {"model": "m", "score": {"verdict": "uncheckable"}, "output": ""},
        ],
    }]
    row = results.per_model(entries)[0]
    assert row["n_records"] == 4
    assert row["n_checkable"] == 2
    assert row["accuracy"] == 0.5, "1 of 2 checkable, not 1 of 4 records"
    assert row["judgeability"] == 0.5, "judgeability is what says the other half vanished"


def test_a_model_with_nothing_checkable_reports_none_not_zero():
    """Zero accuracy and no evidence of accuracy are different claims, and a
    0.0 in a results table reads as 'this model got everything wrong'."""
    entries = [{"manifest": {"model": "m"},
                "records": [{"model": "m", "score": {"verdict": "uncheckable"}}]}]
    row = results.per_model(entries)[0]
    assert row["accuracy"] is None and row["ci95"] is None


# --- item statistics ---------------------------------------------------------


def test_item_difficulty_and_who_missed_it():
    matrix = {"strong": {"i1": 1, "i2": 1}, "weak": {"i1": 1, "i2": 0}}
    items = [{"id": "i1", "target": "a"}, {"id": "i2", "target": "b"}]
    rows = {r["id"]: r for r in results.per_item(matrix, items, {})}
    assert rows["i1"]["p"] == 1.0 and rows["i1"]["separates"] is False
    assert rows["i2"]["p"] == 0.5 and rows["i2"]["separates"] is True
    assert rows["i2"]["missed_by"] == ["weak"]


def test_the_most_common_wrong_answer_comes_from_the_models_that_missed_it():
    matrix = {"a": {"i1": 0}, "b": {"i1": 0}, "c": {"i1": 1}}
    outputs = {"a": {"i1": "42"}, "b": {"i1": "42"}, "c": {"i1": "7"}}
    row = results.per_item(matrix, [{"id": "i1", "target": "7"}], outputs)[0]
    assert row["top_wrong_answer"] == "42", "the passing model's answer must not appear here"


# --- slices ------------------------------------------------------------------


def test_slices_split_accuracy_by_every_metadata_field():
    matrix = {"m": {"i1": 1, "i2": 1, "i3": 0, "i4": 0}}
    items = [{"id": "i1", "metadata": {"subject": "math", "hard": False}},
             {"id": "i2", "metadata": {"subject": "math", "hard": False}},
             {"id": "i3", "metadata": {"subject": "law", "hard": True}},
             {"id": "i4", "metadata": {"subject": "law", "hard": True}}]
    sl = results.slices(matrix, items)
    assert set(sl) == {"subject", "hard"}
    by_subject = {r["value"]: r for r in sl["subject"]}
    assert by_subject["math"]["accuracy"] == 1.0
    assert by_subject["law"]["accuracy"] == 0.0
    assert by_subject["law"]["by_model"] == {"m": 0.0}


def test_items_with_no_metadata_produce_no_slices():
    assert results.slices({"m": {"i1": 1}}, [{"id": "i1"}]) == {}


# --- results never decide anything -------------------------------------------


def test_the_results_block_cannot_change_a_verdict():
    """Results describe. If a number here could gate, a hard item or an
    expensive model would become a defect, and the constitutional split between
    invariants and diagnostics would gain a third, undeclared member."""
    source = (REPO / "src" / "dinostomp" / "results.py").read_text(encoding="utf-8")
    body = "\n".join(line for line in source.splitlines()
                     if not line.lstrip().startswith("#"))
    for forbidden in ("rep.check", "Reporter(", "rep.skip"):
        assert forbidden not in body, (
            f"results.py contains {forbidden!r}; it must compute no verdict")


def test_probe_runs_are_not_pooled_into_the_results(tmp_path):
    """A blind probe is a deliberately handicapped control. Pooling it into a
    model's accuracy would publish the handicap as the score."""
    src = REPO / "examples" / "agent"
    dst = tmp_path / "agent"
    shutil.copytree(src, dst)
    probes = list((dst / "data" / "runs").glob("*blindprobe*.jsonl"))
    assert probes, "the agent pod is supposed to ship a blind probe on disk"
    report, _ = lint_eval(dst / "eval.yaml")
    for m in report["results"]["models"]:
        # 26 items per model per run; pooling the probe would double it.
        assert m["runs"] == 1, (
            f"{m['model']} shows {m['runs']} runs; the blind probe leaked into the results")


def test_the_rendered_report_is_stable_and_states_what_it_truncated(fleet_report):
    md = render_markdown(fleet_report)
    assert md == render_markdown(fleet_report), "rendering is not deterministic"
    assert "## Results" in md
    assert "ON CHECKABLE" in md, "the accuracy caveat must travel with the table"
    n_items = len(fleet_report["results"]["items"])
    assert (f"all {n_items} item(s)" in md) or (f"of {n_items}" in md), (
        "the item table must say how many rows it shows out of how many")
