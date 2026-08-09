"""verify and plan: the checkable-by-construction pair.

verify's negative tests are the point: a tampered or stale published report
must be a MISMATCH, and a pod with no published report must be UNVERIFIABLE,
never silently fine.
"""

import json
from pathlib import Path

import pytest

from dinostomp.cli import main
from dinostomp.report import JSON_NAME, MD_NAME, verify_report


def make_pod(tmp_path, run=True, report=True):
    pod = tmp_path / "p"
    main(["new", str(pod)])
    if run:
        main(["run", str(pod / "eval.yaml")])
    if report:
        main(["report", str(pod / "eval.yaml"), "--allow-incomplete"])
    return pod


# --- verify -----------------------------------------------------------------


def test_fresh_report_verifies(tmp_path, capsys):
    pod = make_pod(tmp_path)
    assert main(["verify", str(pod / "eval.yaml")]) == 0
    out = capsys.readouterr().out
    assert "VERIFIED" in out
    assert "re-derived, not trusted" in out


def test_hand_edited_report_is_a_mismatch(tmp_path, capsys):
    pod = make_pod(tmp_path)
    md = pod / MD_NAME
    md.write_text(md.read_text(encoding="utf-8").replace("INCOMPLETE", "STOMPED CLEAN"), encoding="utf-8")
    assert main(["verify", str(pod / "eval.yaml")]) == 1
    out = capsys.readouterr().out
    assert "MISMATCH" in out
    assert "STOMP.md" in out


def test_stale_report_after_new_run_is_a_mismatch(tmp_path):
    pod = make_pod(tmp_path)
    main(["run", str(pod / "eval.yaml")])  # a second run changes the pod's state
    assert main(["verify", str(pod / "eval.yaml")]) == 1


def test_no_published_report_is_unverifiable(tmp_path, capsys):
    pod = make_pod(tmp_path, report=False)
    assert main(["verify", str(pod / "eval.yaml")]) == 2
    assert "UNVERIFIABLE" in capsys.readouterr().out


def test_tampered_json_caught_even_when_md_matches(tmp_path):
    pod = make_pod(tmp_path)
    jp = pod / JSON_NAME
    report = json.loads(jp.read_text(encoding="utf-8"))
    report["summary"]["verdict"] = "clean"
    jp.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    status, details, _ = verify_report(pod / "eval.yaml")
    assert status == "mismatch"
    assert any("STOMP.json" in d for d in details)


# --- plan --------------------------------------------------------------------


def test_plan_prints_power_witnesses_and_budget(tmp_path, capsys):
    pod = make_pod(tmp_path, run=False, report=False)
    assert main(["plan", str(pod / "eval.yaml")]) == 0
    out = capsys.readouterr().out
    assert "resolves gaps down to" in out, "MDE stated before any money"
    assert "mutant scorers die" in out or "would survive" in out
    assert "budget" in out and "fits" in out, "dry pod fits a zero cap"


def test_plan_ordering_claim_gets_sample_size_table(tmp_path, capsys):
    import yaml

    pod = make_pod(tmp_path, run=False, report=False)
    spec_path = pod / "eval.yaml"
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    spec["entitled_claims"] = ["Model A ranks above model B."]
    spec_path.write_text(yaml.safe_dump(spec), encoding="utf-8")
    main(["plan", str(spec_path)])
    out = capsys.readouterr().out
    assert "ordering claim entitled" in out
    assert "gap 10%" in out


def test_plan_flags_surviving_mutants(tmp_path, capsys):
    import yaml

    pod = make_pod(tmp_path, run=False, report=False)
    spec_path = pod / "eval.yaml"
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    spec["scorer"]["witnesses"] = [
        {"output": "expected answer", "target": "expected answer", "expect": "pass"},
        {"output": "wrong answer", "target": "expected answer", "expect": "fail"},
    ]
    spec_path.write_text(yaml.safe_dump(spec), encoding="utf-8")
    main(["plan", str(spec_path)])
    out = capsys.readouterr().out
    assert "would survive" in out, "a thin witness suite is flagged before the run, not after"


def _forecast(capsys, spec_path, extra_seeds=None):
    """The forecast total `plan` prints, in dollars."""
    import re
    import yaml

    spec = yaml.safe_load(Path(spec_path).read_text(encoding="utf-8"))
    spec["models"] = [{"provider": "openrouter", "model": "some/small-model",
                       "price_in": 0.10, "price_out": 0.20,
                       "params": {"max_tokens": 8192}}]
    if extra_seeds:
        spec["run"]["seeds"] = extra_seeds
    spec["run"]["budget_usd"] = 10.0
    Path(spec_path).write_text(yaml.safe_dump(spec), encoding="utf-8")
    capsys.readouterr()
    main(["plan", str(spec_path)])
    out = capsys.readouterr().out
    return float(re.search(r"worst case \$([0-9.]+) vs cap", out).group(1)), out


def test_plan_forecast_counts_every_extra_seed(tmp_path, capsys):
    """run.seeds repeats the WHOLE eval and every call of it is billed.

    Negative half first: with the seeds line deleted the forecast is the
    one-seed number, which is what shipped and what understated a real pod 3x.
    """
    pod = make_pod(tmp_path, run=False, report=False)
    one, _ = _forecast(capsys, pod / "eval.yaml")
    three, out = _forecast(capsys, pod / "eval.yaml", extra_seeds=[11, 23])
    assert one > 0
    # the printed figure is rounded to 4dp, so compare inside that grain
    assert three == pytest.approx(one * 3, abs=2e-4), "a 3-seed pod costs 3 passes"
    assert "+2 extra seed(s)" in out, "and the item line says so out loud"
