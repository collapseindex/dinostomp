"""suggest-witnesses: helps with the homework, never does it.

The failure this must not have: generating witnesses, keeping whatever kills
the mutants, and reporting a green gauntlet. That fits the witnesses TO the
mutants and turns W1 from an independent measure of witness adequacy into the
thing they were optimised against.
"""

import json

import pytest
import yaml

from dinostomp.cli import main
from dinostomp.suggest import propose


def test_it_writes_nothing(tmp_path, capsys):
    pod = tmp_path / "p"
    main(["new", str(pod)])
    before = (pod / "eval.yaml").read_bytes()
    assert main(["suggest-witnesses", str(pod / "eval.yaml")]) == 0
    assert (pod / "eval.yaml").read_bytes() == before, "the command edited the spec"
    assert "does not edit your spec" in capsys.readouterr().out


def test_every_proposal_carries_a_reason(tmp_path):
    items = [{"id": "a", "input": "q", "target": "blue sky"}]
    for case in propose(items, "exact"):
        assert case["why"], f"{case} has no stated reason"
        assert case["expect"] in ("pass", "fail", "uncheckable")


def test_proposals_include_at_least_one_rejection():
    """A scorer that cannot fail is not a scorer, so a suggestion set that
    proposes only accepting cases would be worse than none."""
    items = [{"id": "a", "input": "q", "target": "blue sky"}]
    cases = propose(items, "exact")
    assert any(c["expect"] == "pass" for c in cases)
    assert sum(1 for c in cases if c["expect"] == "fail") >= 3


def test_a_numeric_target_proposes_uncheckable_not_fail():
    """A numeric scorer handed no number has not judged the answer wrong.

    Getting this backwards is the exact mistake the witness gate caught while
    the GSM8K benchmark pod was being written.
    """
    cases = propose([{"id": "a", "input": "q", "target": "18"}], "numeric")
    empties = [c for c in cases if c["output"] == ""]
    assert empties and empties[0]["expect"] == "uncheckable"


def test_a_text_target_proposes_a_case_case_decision():
    cases = propose([{"id": "a", "input": "q", "target": "Setosa"}], "exact")
    assert any("case is part of the contract" in c["why"] for c in cases)


def test_it_reports_authored_and_suggested_coverage_separately(tmp_path, capsys):
    """The number that matters is what a HUMAN's witnesses catch on their own."""
    pod = tmp_path / "p"
    main(["new", str(pod)])
    spec_path = pod / "eval.yaml"
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    # strip the scaffold down to the bare legal minimum: one pass, one fail
    spec["scorer"]["witnesses"] = [
        {"output": "expected answer", "target": "expected answer", "expect": "pass"},
        {"output": "wrong answer", "target": "expected answer", "expect": "fail"},
    ]
    spec_path.write_text(yaml.safe_dump(spec), encoding="utf-8")
    assert main(["suggest-witnesses", str(spec_path)]) == 0
    out = capsys.readouterr().out
    assert "killed by your authored witnesses" in out
    assert "killed once suggestions are added" in out
    assert "a suite nobody thought about" in out, (
        "when suggestions close a gap the authored witnesses left, the output has to say "
        "that is a to-do rather than a score")


def test_a_hosted_judge_pod_declines_to_compute_coverage(tmp_path, capsys):
    """Running the gauntlet on a judge would pay a provider during a suggestion."""
    pod = tmp_path / "p"
    main(["new", str(pod)])
    spec_path = pod / "eval.yaml"
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    spec["scorer"] = {"kind": "judge", "rubric": "Is the answer correct overall?",
                      "judge": {"provider": "anthropic", "model": "claude-haiku-4-5"},
                      "witnesses": spec["scorer"]["witnesses"]}
    spec_path.write_text(yaml.safe_dump(spec), encoding="utf-8")
    assert main(["suggest-witnesses", str(spec_path)]) == 0
    assert "Gauntlet coverage not computed" in capsys.readouterr().out
