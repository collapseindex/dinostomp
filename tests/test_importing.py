"""Importing another harness's log, and the four defects a real one exposed.

Every test here was written against a genuine artifact: an lm-evaluation-harness
details file for ARC-Challenge, 1172 items, 25-shot, published by the Open LLM
Leaderboard in July 2023 for a third-party 111M model. Before that log, the
importer had only ever been pointed at evidence this engine wrote, which is why
all four of these survived to be found at once.

The rule this file exists to protect: an import may lose coverage, never gain
a number. Anything the source log does not say, the report must not say either.
"""

import json

import pytest

from dinostomp.importing import infer_record_mapping, to_records
from dinostomp.lint import Reporter
from dinostomp.runner import CANNOT_RUN, run_spec
from dinostomp.spec import load_schema, validate_obj
from tests.test_lint import arith_items, finding, stomp, write_eval

# A loglikelihood-ranking log: verdicts, no generated text anywhere. This is the
# shape ARC, MMLU and HellaSwag are actually scored in on the Open LLM
# Leaderboard, so it is not an exotic case to support.
LOGLIK = [{"example": f"a{i}", "acc": i % 3 != 0} for i in range(10, 34)]


def rows_with(**cols):
    out = []
    for i, base in enumerate(LOGLIK):
        r = dict(base)
        for k, v in cols.items():
            r[k] = v[i] if isinstance(v, list) else v
        out.append(r)
    return out


# --- output is optional, because a whole class of eval never produces any ------


def test_record_schema_does_not_require_output():
    assert "output" not in (load_schema("record").get("required") or [])


def test_a_record_without_output_is_valid_and_one_with_empty_output_is_too():
    """Absent and empty must BOTH validate: they are different claims.

    Absent means the harness emitted no text. Empty means the model answered
    with nothing. Collapsing them would let an import invent a result.
    """
    base = {"item_id": "a1", "model": "m", "provider": "imported", "seed": 0,
            "score": {"verdict": "pass", "evidence": "x"}, "ts": "1970-01-01T00:00:00+00:00"}
    assert not validate_obj(base, "record")
    assert not validate_obj({**base, "output": ""}, "record")


def test_a_loglikelihood_log_imports_without_an_output_column():
    mapping, _, issues = infer_record_mapping(LOGLIK, {"item_id": "example"})
    assert not issues, [i.message for i in issues]
    assert "output" not in mapping
    records, rec_issues = to_records(LOGLIK, mapping, model="m", seed=0)
    assert not rec_issues and len(records) == len(LOGLIK)
    assert all("output" not in r for r in records), "an absent output was defaulted to a value"


def test_an_output_column_is_still_carried_when_the_log_has_one():
    rows = rows_with(output=[f"answer {i}" for i in range(len(LOGLIK))])
    mapping, _, issues = infer_record_mapping(rows, {"item_id": "example"})
    assert not issues and mapping["output"] == "output"
    records, _ = to_records(rows, mapping, model="m", seed=0)
    assert records[0]["output"] == "answer 0"


# --- the contract skip must not be overwritten by the check's own body --------


def test_a_body_skip_does_not_replace_a_contract_skip():
    """R16 shipped this: with no `output` anywhere it reported "no model has 5+
    failed records to inspect" over 966 failed records. The reason was false and
    the advice it implied was useless."""
    rep = Reporter()
    rep.skip("R16", "no `output` on every record", missing=list(load_needs("R16")))
    rep.skip("R16", "no model has 5+ failed records to inspect")
    assert "output" in rep.findings["R16"].detail
    assert rep.findings["R16"].evidence["missing_evidence"] == ["output"]


def test_an_ordinary_skip_is_still_recorded_and_still_overwritable():
    """The negative test for the guard above: it must only protect a skip that
    NAMED missing evidence, or it would freeze the first reason any check gives
    and hide better ones."""
    rep = Reporter()
    rep.skip("R16", "first reason")
    rep.skip("R16", "second and better reason")
    assert rep.findings["R16"].detail == "second and better reason"


def test_a_contract_skip_still_replaces_an_ordinary_skip():
    rep = Reporter()
    rep.skip("R16", "no model has 5+ failed records to inspect")
    rep.skip("R16", "no `output` on every record", missing=list(load_needs("R16")))
    assert "output" in rep.findings["R16"].detail


def load_needs(cid):
    from dinostomp.evidence import NEEDS
    return NEEDS[cid]


def test_the_output_reading_checks_skip_naming_the_field(tmp_path):
    """End to end through the real CLI: a pod whose only evidence is output-less
    names `output` in all three skips, rather than blaming the runner or the
    item count. R16 is the one that regressed and the one that matters, because
    its old message pointed at a shortage of failed records that did not exist.
    """
    from dinostomp.cli import main

    items = arith_items()
    pod = write_eval(tmp_path, items)
    log = tmp_path / "foreign.jsonl"
    # Half fail on purpose, so R16 has plenty of failed records and cannot
    # honestly skip for want of them. The only thing missing is the text.
    log.write_text("\n".join(
        json.dumps({"example": it["id"], "acc": int(i % 2 == 0)})
        for i, it in enumerate(items)) + "\n", encoding="utf-8")
    assert main(["import", str(pod), str(log), "--item-id-field", "example",
                 "--model", "dry-strong", "--seed", "7"]) == 0
    report = stomp(pod)
    for cid in ("R8", "R14", "R16"):
        f = finding(report, cid)
        assert f["level"] == "skip", f"{cid} did not skip: {f['detail']}"
        assert "output" in f["detail"], f"{cid} skipped without naming the field: {f['detail']}"


# --- a rival score column that disagrees --------------------------------------


def test_two_disagreeing_verdict_columns_are_refused_not_chosen():
    """`acc` and `acc_norm` differed on 221 of 1172 real rows, 17.6% vs 19.7%,
    and the leaderboard published the one the mapping did NOT pick."""
    rows = rows_with(acc_norm=[not r["acc"] for r in LOGLIK])
    _, _, issues = infer_record_mapping(rows, {"item_id": "example"})
    msgs = [i.message for i in issues]
    assert any("acc_norm" in m and "disagree" in m for m in msgs), msgs


def test_a_rival_that_agrees_everywhere_imports_clean():
    """The negative test: the rule must fire on the DISAGREEMENT, not on the
    mere presence of a second verdict-shaped column."""
    rows = rows_with(acc_norm=[r["acc"] for r in LOGLIK])
    _, _, issues = infer_record_mapping(rows, {"item_id": "example"})
    assert not issues, [i.message for i in issues]


def test_a_constant_flag_column_is_not_a_rival():
    """The first version of this rule fired on `truncated`, which is 0 on all
    1172 rows and so "disagreed" with the score on exactly the passing rows."""
    rows = rows_with(truncated=0)
    _, _, issues = infer_record_mapping(rows, {"item_id": "example"})
    assert not issues, [i.message for i in issues]


def test_naming_the_score_field_settles_it():
    rows = rows_with(acc_norm=[not r["acc"] for r in LOGLIK])
    mapping, _, issues = infer_record_mapping(
        rows, {"item_id": "example", "score": "acc_norm"})
    assert not issues and mapping["score"] == "acc_norm"


# --- an `imported` model is declarable and unrunnable -------------------------


def test_the_provider_enum_admits_imported():
    schema = load_schema("eval")
    enum = schema["$defs"]["model"]["properties"]["provider"]["enum"]
    assert "imported" in enum


@pytest.mark.parametrize("dry", [False, True])
def test_run_refuses_an_imported_model_including_under_dry(tmp_path, dry):
    """--dry is the dangerous path: it substitutes the offline provider for
    whatever was declared, so without this guard `run --dry` would write a full
    set of fabricated records under a real model's name."""
    pod = write_eval(tmp_path, arith_items(),
                     models=[{"provider": "imported", "model": "Corianas/111m"}])
    outcome = run_spec(pod, dry_run=dry)
    assert outcome.exit_code == CANNOT_RUN
    assert "imported" in outcome.issues[0].message
    assert not list((tmp_path / "data" / "runs").glob("*.jsonl")) if (
        tmp_path / "data" / "runs").exists() else True


def test_the_error_message_names_a_flag_someone_can_type():
    """`--item_id-field` is not a flag argparse accepts; the message used to
    print it anyway."""
    _, _, issues = infer_record_mapping([{"nothing": 1}])
    locs = [i.loc for i in issues]
    assert "--item-id-field" in locs, locs
    assert not any("_" in loc for loc in locs), locs
