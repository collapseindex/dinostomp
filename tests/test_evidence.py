"""The evidence contract: what each check reads, stated in schema terms.

The failure this replaces: a check that could not run said "no runs on disk
yet", which is unactionable in general and false when there ARE runs and the
check needs a field they lack. The failure it must not introduce: a table that
claims a check reads a field it does not, which would make a skip message a
confident lie.
"""

import json
import shutil

from dinostomp.cli import main
from dinostomp.evidence import NEEDS, Survey, missing_for, skip_reason, survey
from dinostomp.lint import CHECKS, lint_eval
from dinostomp.runner import OK, run_spec
from tests.test_lint import arith_items, finding, write_eval


def strip_field(pod_dir, field):
    for rf in (pod_dir / "data" / "runs").glob("*.jsonl"):
        rows = [json.loads(l) for l in rf.read_text(encoding="utf-8").splitlines() if l.strip()]
        for r in rows:
            r.pop(field, None)
        rf.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


# --- the contract itself ------------------------------------------------------


def test_every_declared_need_names_a_real_check():
    ids = {cid for cid, *_ in CHECKS}
    assert set(NEEDS) <= ids, f"NEEDS names checks that do not exist: {set(NEEDS) - ids}"


def test_every_need_states_why_and_where():
    for cid, needs in NEEDS.items():
        assert needs, f"{cid} declares an empty need list"
        for n in needs:
            assert n.where in ("record", "manifest"), f"{cid}: bad location {n.where!r}"
            assert n.field and n.why, f"{cid}: a need without a field or a reason"
            assert n.field in n.describe() and n.why in n.describe()


def test_no_check_declares_a_schema_required_field():
    """A record missing a REQUIRED field is schema-invalid, which R4 gates on.

    Telling a check to skip over something the report already calls broken
    would hide a gating finding behind a coverage line.
    """
    from dinostomp.spec import load_schema

    required = {
        "record": set(load_schema("record").get("required") or []),
        "manifest": set(load_schema("manifest").get("required") or []),
    }
    for cid, needs in NEEDS.items():
        for n in needs:
            if n.field in ("output", "score", "seed"):
                continue  # read as evidence AND schema-required; harmless overlap
            assert n.field not in required[n.where], (
                f"{cid} declares {n.field!r}, which the {n.where} schema already requires")


# --- skips that name the missing field ---------------------------------------


def test_a_missing_field_is_named_not_blamed_on_the_runner(tmp_path):
    pod = write_eval(tmp_path, arith_items())
    assert run_spec(pod).exit_code == OK
    assert finding(lint_eval(pod)[0], "R5")["level"] == "pass"

    strip_field(tmp_path, "finish_reason")
    f = finding(lint_eval(pod)[0], "R5")
    assert f["level"] == "skip"
    assert "finish_reason" in f["detail"], "the skip must name the FIELD"
    assert "no runs on disk" not in f["detail"], "there are runs on disk; saying otherwise is false"
    assert "0 of" in f["detail"], "state how much of the evidence carries it"


def test_the_skip_survives_a_later_vacuous_pass(tmp_path):
    """A check disqualified by the contract must not be revived by a later pass
    computing a green result over zero rows."""
    pod = write_eval(tmp_path, arith_items())
    assert run_spec(pod).exit_code == OK
    strip_field(tmp_path, "usage")
    f = finding(lint_eval(pod)[0], "R3")
    assert f["level"] == "skip"
    # only the record field went; the manifest still carries spend_usd, and the
    # skip names exactly what is absent rather than the whole declared need
    assert f["evidence"]["missing_evidence"] == ["usage"]
    assert "usage" in f["detail"] and "spend_usd" not in f["detail"]


def test_no_evidence_at_all_points_at_both_ways_to_get_some():
    reason = skip_reason("R5", survey([]))
    assert "dinostomp run" in reason
    assert "dinostomp import" in reason, (
        "the contract's whole point is that this runner is not the only producer")


def test_a_check_with_its_fields_present_is_not_skipped():
    s = Survey(n_records=10, n_manifests=1, record_fields={"finish_reason": 10})
    assert missing_for("R5", s) == []
    assert skip_reason("R5", s) is None


# --- import: the contract, exercised from outside -----------------------------


def foreign_pod(tmp_path, rows=None, name="foreign.jsonl"):
    pod = tmp_path / "pod"
    shutil.copytree("examples/fleet", pod,
                    ignore=shutil.ignore_patterns("data", "STOMP.*", "*.svg"))
    items = [json.loads(l) for l in (pod / "items.jsonl").read_text(encoding="utf-8").splitlines()
             if l.strip() and "_canary" not in l]
    rows = rows or [{"doc_id": it["id"], "completion": it["target"] if i % 4 else "wrong",
                     "is_correct": i % 4 != 0} for i, it in enumerate(items)]
    log = pod / name
    log.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return pod, log


def test_a_foreign_log_becomes_auditable_evidence(tmp_path):
    pod, log = foreign_pod(tmp_path)
    assert main(["import", str(pod / "eval.yaml"), str(log),
                 "--model", "dry-alpha", "--seed", "42"]) == 0
    report, _ = lint_eval(pod / "eval.yaml")
    by_slug = {f["slug"]: f for f in report["findings"]}
    # the pod's own scorer independently re-derives the foreign verdicts
    assert by_slug["verdict-rederive"]["level"] == "pass"
    # and the drift boundary applies to imported evidence like any other
    assert by_slug["input-drift"]["level"] == "pass"
    assert by_slug["summary-rederive"]["level"] == "pass"
    assert by_slug["witness-replay"]["level"] == "pass"


def test_an_import_claims_no_engine_and_engine_drift_says_so(tmp_path):
    """An import must not stamp tool_sha256: this engine did not produce it."""
    pod, log = foreign_pod(tmp_path)
    main(["import", str(pod / "eval.yaml"), str(log), "--model", "dry-alpha", "--seed", "42"])
    mf = next((pod / "data" / "runs").glob("imported_*_manifest.json"))
    manifest = json.loads(mf.read_text(encoding="utf-8"))
    assert "tool_sha256" not in manifest
    assert manifest["imported"] is True
    assert manifest["imported_from"].endswith("foreign.jsonl")
    assert finding(lint_eval(pod / "eval.yaml")[0], "R19")["level"] == "n/a"


def test_fields_the_foreign_log_lacks_skip_naming_themselves(tmp_path):
    pod, log = foreign_pod(tmp_path)
    main(["import", str(pod / "eval.yaml"), str(log), "--model", "dry-alpha", "--seed", "42"])
    report, _ = lint_eval(pod / "eval.yaml")
    by_slug = {f["slug"]: f for f in report["findings"]}
    assert by_slug["truncation-credit"]["level"] == "skip"
    assert "finish_reason" in by_slug["truncation-credit"]["detail"]
    assert by_slug["spend-ledger"]["level"] == "skip"
    assert "usage" in by_slug["spend-ledger"]["detail"]


def test_an_unreadable_verdict_refuses_rather_than_guessing(tmp_path, capsys):
    """Defaulting to `fail` invents a number; defaulting to `pass` invents a
    flattering one. Neither is acceptable, so nothing is written."""
    pod, log = foreign_pod(tmp_path, rows=[
        {"doc_id": "a", "completion": "x", "is_correct": "sort of"}])
    assert main(["import", str(pod / "eval.yaml"), str(log)]) == 2
    assert not (pod / "data").exists(), "a refused import must write nothing"
    assert "guessing would invent a number nobody measured" in capsys.readouterr().out


def test_an_ambiguous_log_refuses_and_names_the_candidates(tmp_path):
    pod, log = foreign_pod(tmp_path, rows=[
        {"doc_id": "a", "completion": "x", "response": "y", "is_correct": True}])
    assert main(["import", str(pod / "eval.yaml"), str(log)]) == 2


def test_import_will_not_land_evidence_a_broken_gate_cannot_rederive(tmp_path):
    """The scorer that re-derives imported verdicts is the one being gated, so
    a pod whose witnesses do not pass must not accept an import."""
    import yaml

    pod, log = foreign_pod(tmp_path)
    spec_path = pod / "eval.yaml"
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    spec["scorer"]["witnesses"] = [
        {"output": "anything", "target": "anything", "expect": "fail"},   # a lie
        {"output": "x", "target": "y", "expect": "pass"},                 # also a lie
    ]
    spec_path.write_text(yaml.safe_dump(spec), encoding="utf-8")
    assert main(["import", str(spec_path), str(log)]) == 1
    assert not (pod / "data").exists()


def test_the_evidence_command_lists_what_is_had_and_what_is_missing(tmp_path, capsys):
    pod, log = foreign_pod(tmp_path)
    main(["import", str(pod / "eval.yaml"), str(log), "--model", "dry-alpha", "--seed", "42"])
    capsys.readouterr()
    assert main(["evidence", str(pod / "eval.yaml")]) == 0
    out = capsys.readouterr().out
    assert "[have] verdict-rederive" in out
    assert "[MISS] truncation-credit" in out
    assert "finish_reason: a truncated response is identified by it" in out
    assert "not this runner" in out, "the command must state the contract it is showing"
