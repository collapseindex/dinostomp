"""Typed claims: the C1 compiler. Negative tests plant unsupportable claims
and assert the pod goes broken; authoring nonsense dies at load time."""

import yaml

from dinostomp import load_spec
from dinostomp.runner import OK, run_spec
from tests.test_lint import FLEET, arith_items, finding, stomp, write_eval


def with_claims(tmp_path, claims, models=None):
    spec_path = write_eval(tmp_path, arith_items(), models=models or FLEET)
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    spec["claims"] = claims
    spec_path.write_text(yaml.safe_dump(spec), encoding="utf-8")
    return spec_path


# --- load-time authoring errors ---------------------------------------------------


def test_claim_about_phantom_model_rejected_at_load(tmp_path):
    spec_path = with_claims(tmp_path, [{"type": "accuracy", "model": "gpt-imaginary"}])
    _, issues = load_spec(spec_path)
    assert any("does not run" in i.message for i in issues)


def test_model_cannot_beat_itself(tmp_path):
    spec_path = with_claims(tmp_path, [
        {"type": "superiority", "better": "dry-alpha", "worse": "dry-alpha"}])
    _, issues = load_spec(spec_path)
    assert any("cannot beat itself" in i.message for i in issues)


# --- C1 evaluation ------------------------------------------------------------------


def test_supported_claims_pass_and_render(tmp_path):
    spec_path = with_claims(tmp_path, [
        {"type": "accuracy", "model": "dry-alpha", "min": 0.80},
        {"type": "superiority", "better": "dry-alpha", "worse": "dry-charlie", "min_effect": 0.20},
    ])
    assert run_spec(spec_path).exit_code == OK
    report = stomp(spec_path)
    assert finding(report, "C1")["level"] == "pass"
    assert all(c["supported"] for c in report["claims"])
    req_names = {r["name"] for c in report["claims"] for r in c["requirements"]}
    assert "paired bootstrap clears min_effect at the declared confidence" in req_names


def test_unsupportable_superiority_breaks_the_pod(tmp_path):
    """dry-charlie does not beat dry-alpha; a spec claiming so chose its own
    bar and failed it: gated, verdict broken."""
    spec_path = with_claims(tmp_path, [
        {"type": "superiority", "better": "dry-charlie", "worse": "dry-alpha", "min_effect": 0.05}])
    run_spec(spec_path)
    report = stomp(spec_path)
    f = finding(report, "C1")
    assert f["level"] == "fail"
    assert report["summary"]["verdict"] == "broken"
    assert any("bootstrap" in ex for ex in f["examples"])


def test_accuracy_claim_needs_the_lower_bound_not_the_point(tmp_path):
    """dry-alpha scores 100% on 24 items, but the 95% lower bound is ~86%:
    a claimed minimum of 90% must fail even though the point estimate clears it."""
    spec_path = with_claims(tmp_path, [
        {"type": "accuracy", "model": "dry-alpha", "min": 0.90}])
    run_spec(spec_path)
    report = stomp(spec_path)
    f = finding(report, "C1")
    assert f["level"] == "fail"
    assert any("lower bound" in ex for ex in f["examples"])


def test_claims_without_runs_skip(tmp_path):
    spec_path = with_claims(tmp_path, [{"type": "accuracy", "model": "dry-alpha"}])
    report = stomp(spec_path)
    assert finding(report, "C1")["level"] == "skip"


def test_no_typed_claims_is_na(tmp_path):
    spec_path = write_eval(tmp_path, arith_items())
    run_spec(spec_path)
    report = stomp(spec_path)
    assert finding(report, "C1")["level"] == "n/a"
