"""R23 overconfident and R24 confidence-blind: what a reported probability is worth.

A one-pass model answers with a probability per option. R23 holds the stated
confidence to the observed accuracy (ECE); R24 asks whether confidence ranks
right answers above wrong ones at all (AUROC against the noise bar). The two
fail independently, and the planted trials below prove it: an overconfident
but well-ordered model trips R23 only, a constant-confidence model trips R24
only, an honest one passes both, and a pod of text models is n/a for both.
"""
import json
import random

from dinostomp.calibration import (auroc, confidence_points, coverage_table,
                                   expected_calibration_error, probability_vector)
from dinostomp.runner import OK, run_spec
from tests.test_lint import choice_items, finding, rewrite_run_consistently, stomp, write_eval

N_ITEMS = 60


def _vector_step(answer: str, choices: list[str], p_answer: float) -> dict:
    rest = (1.0 - p_answer) / (len(choices) - 1)
    dist = {c: rest for c in choices}
    dist[answer] = p_answer
    return {"tool": "score_options", "args": {"n_options": len(choices)},
            "result": json.dumps({"top": answer, "p_top": p_answer, "distribution": dist}), "ok": True}


def _ran(tmp_path):
    items = choice_items(N_ITEMS)
    spec = write_eval(tmp_path, items)
    outcome = run_spec(spec)
    assert outcome.exit_code == OK
    return spec, outcome.run_files[0], {str(i["id"]): i for i in items}


def _plant(spec, run_file, items_of, draw):
    """Give every record a vector. `draw(idx, rng)` returns (confidence, was_right); the
    output is set to the target or a distractor to match, so only the vector is planted."""
    rng = random.Random(11)

    def mutate(r, idx):
        item = items_of[str(r["item_id"])]
        conf, ok = draw(idx, rng)
        r["output"] = item["target"] if ok else next(c for c in item["choices"] if c != item["target"])
        r["score"] = {"verdict": "pass" if ok else "fail"}
        r["trajectory"] = [_vector_step(r["output"], item["choices"], conf)]
        return r

    rewrite_run_consistently(spec, run_file, mutate)


def _three_in_four(idx):
    return idx % 4 != 0


def test_overconfident_but_ordered_model_trips_r23_only(tmp_path):
    spec, run_file, choices_of = _ran(tmp_path)
    # right answers at 0.99, wrong ones at 0.95: perfectly ordered, ~20 points too sure
    _plant(spec, run_file, choices_of, lambda i, rng: (0.99 if _three_in_four(i) else 0.95, _three_in_four(i)))
    report = stomp(spec)
    r23, r24 = finding(report, "R23"), finding(report, "R24")
    assert r23["level"] == "warn", r23
    assert "overconfident" in r23["examples"][0] and "dry-strong" in r23["examples"][0]
    assert r24["level"] == "pass", r24
    assert report["summary"]["verdict"] != "broken"     # diagnostics never break the verdict


def test_constant_confidence_trips_r24_only(tmp_path):
    spec, run_file, choices_of = _ran(tmp_path)
    # every answer at 0.75 against 75% accuracy: calibrated in aggregate, blind per item
    _plant(spec, run_file, choices_of, lambda i, rng: (0.75, _three_in_four(i)))
    report = stomp(spec)
    assert finding(report, "R23")["level"] == "pass"
    r24 = finding(report, "R24")
    assert r24["level"] == "warn", r24
    assert "AUROC 0.50" in r24["examples"][0]


def test_honest_confidence_passes_both(tmp_path):
    spec, run_file, choices_of = _ran(tmp_path)
    # calibrated by construction: right with exactly the probability it states
    def honest(i, rng):
        conf = rng.uniform(0.5, 1.0)
        return conf, rng.random() < conf

    _plant(spec, run_file, choices_of, honest)
    report = stomp(spec)
    assert finding(report, "R23")["level"] == "pass"
    assert finding(report, "R24")["level"] == "pass"
    ev = finding(report, "R23")["evidence"]
    assert 0.0 < ev["coverage"]["dry-strong"]["0.80"]["coverage"] < 1.0


def test_text_models_are_not_applicable(tmp_path):
    spec, _, _ = _ran(tmp_path)
    report = stomp(spec)
    for cid in ("R23", "R24"):
        assert finding(report, cid)["level"] == "n/a", finding(report, cid)


# --- the math, on its own ---------------------------------------------------


def test_probability_vector_reads_only_a_real_distribution():
    good = {"trajectory": [{"tool": "t", "result": json.dumps({"distribution": {"a": 0.7, "b": 0.3}})}]}
    assert probability_vector(good) == {"a": 0.7, "b": 0.3}
    for bad in (
        {},                                                                        # no trajectory
        {"trajectory": [{"tool": "t", "result": "not json"}]},
        {"trajectory": [{"tool": "t", "result": json.dumps({"top": "a"})}]},       # no distribution
        {"trajectory": [{"tool": "t", "result": json.dumps({"distribution": {"a": 0.9, "b": 0.5}})}]},
        {"trajectory": [{"tool": "t", "result": json.dumps({"distribution": {"a": 1.2, "b": -0.2}})}]},
        {"trajectory": [{"tool": "t", "result_truncated": True,
                         "result": json.dumps({"distribution": {"a": 1.0}})}]},
    ):
        assert probability_vector(bad) is None, bad


def test_confidence_points_use_the_answer_given_and_skip_uncheckable():
    rec = lambda out, verdict, dist: {"output": out, "score": {"verdict": verdict},
                                      "trajectory": [{"tool": "t", "result": json.dumps({"distribution": dist})}]}
    pts = confidence_points([
        rec("a", "pass", {"a": 0.8, "b": 0.2}),
        rec("b", "fail", {"a": 0.6, "b": 0.4}),          # confidence is the mass on "b", the answer given
        rec("a", "uncheckable", {"a": 0.9, "b": 0.1}),
        rec("zzz", "fail", {"a": 0.9, "b": 0.1}),        # answer not in the vector: not evidence
    ])
    assert pts == [(0.8, True), (0.4, False)]


def test_ece_is_zero_when_confidence_equals_accuracy_and_large_when_not():
    honest = [(0.95, True)] * 19 + [(0.95, False)]       # says 95%, right 95%
    assert expected_calibration_error(honest) < 0.01
    liar = [(0.95, i < 10) for i in range(20)]           # says 95%, right 50%
    assert abs(expected_calibration_error(liar) - 0.45) < 0.01
    assert expected_calibration_error([]) == 0.0


def test_auroc_orders_and_reports_noise():
    perfect = [(0.9, True)] * 10 + [(0.1, False)] * 10
    area, z = auroc(perfect)
    assert area == 1.0 and z > 3
    constant = [(0.5, True)] * 10 + [(0.5, False)] * 10
    area, z = auroc(constant)
    assert area == 0.5 and abs(z) < 1e-9
    assert auroc([(0.5, True)] * 5) is None                # one class only


def test_coverage_table_reports_the_operating_curve():
    pts = [(0.95, True), (0.85, True), (0.75, False), (0.55, False)]
    table = coverage_table(pts)
    assert table["0.90"] == {"coverage": 0.25, "accuracy": 1.0}
    assert table["0.70"] == {"coverage": 0.75, "accuracy": round(2 / 3, 4)}
    assert table["0.95"]["coverage"] == 0.25 and table["0.50"]["coverage"] == 1.0
