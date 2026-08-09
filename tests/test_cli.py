"""CLI tests: the pod scaffolder, exit codes, and the stomp output contract."""

import json
from pathlib import Path

import yaml

from dinostomp import validate_obj
from dinostomp.cli import main
from dinostomp.lint import CHECKS

REPO = Path(__file__).resolve().parents[1]


def test_new_scaffolds_a_valid_pod(tmp_path, capsys):
    pod = tmp_path / "my-pod"
    assert main(["new", str(pod)]) == 0
    assert main(["validate", str(pod / "eval.yaml")]) == 0
    out = capsys.readouterr().out
    assert "pod created" in out


def test_new_refuses_existing_path(tmp_path, capsys):
    pod = tmp_path / "my-pod"
    assert main(["new", str(pod)]) == 0
    assert main(["new", str(pod)]) == 2
    assert "refusing" in capsys.readouterr().out


def test_validate_exit_codes(tmp_path):
    pod = tmp_path / "p"
    main(["new", str(pod)])
    spec_path = pod / "eval.yaml"
    assert main(["validate", str(spec_path)]) == 0

    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    del spec["scorer"]["witnesses"]
    spec_path.write_text(yaml.safe_dump(spec), encoding="utf-8")
    assert main(["validate", str(spec_path)]) == 2


def test_run_then_stomp_roundtrip(tmp_path, capsys):
    pod = tmp_path / "p"
    main(["new", str(pod)])
    spec_path = str(pod / "eval.yaml")
    assert main(["run", spec_path]) == 0
    assert main(["stomp", spec_path]) == 4, "incomplete is nonzero BY DEFAULT: CI-safe without flags"
    out = capsys.readouterr().out
    assert "INCOMPLETE" in out, "a single-model pod is never a clean bill of health"
    assert "n/a of" in out, "full-battery size must always be visible"
    assert "dry provider" in out, "an all-dry stomp must say so"
    assert "invariants" in out and "diagnostics" in out, "the two tiers are named"


def test_stomp_allow_incomplete_is_the_explicit_escape_hatch(tmp_path, capsys):
    pod = tmp_path / "p"
    main(["new", str(pod)])
    spec_path = str(pod / "eval.yaml")
    main(["run", spec_path])
    assert main(["stomp", spec_path, "--allow-incomplete"]) == 0
    assert "explicit say-so" in capsys.readouterr().out, "the escape hatch is loudly recorded"


def test_stomp_json_report_validates(tmp_path):
    pod = tmp_path / "p"
    main(["new", str(pod)])
    spec_path = str(pod / "eval.yaml")
    main(["run", spec_path])
    out_json = tmp_path / "report.json"
    main(["stomp", spec_path, "--json", str(out_json)])
    report = json.loads(out_json.read_text(encoding="utf-8"))
    assert validate_obj(report, "report") == []
    # Derived, not pinned: the battery size lives in one place (the registry).
    assert report["coverage"]["declared_total"] == len(CHECKS)
    assert report["power"]["mde_unpaired_80pct"] is not None
    assert report["inputs"]["spec_sha256"]
    assert report["runs"][0]["dry_run"] is True
