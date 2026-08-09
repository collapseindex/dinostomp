"""Schema pack tests.

House rule: every check gets a negative test. A validator we have not seen
fire is not a validator, so most tests here break something on purpose and
assert the breakage is caught.
"""

import json
from pathlib import Path

import jsonschema
import pytest
import yaml

from dinostomp import SCHEMA_NAMES, load_schema, load_spec, spec_sha256, validate_obj

REPO = Path(__file__).resolve().parents[1]
SMOKE = REPO / "examples" / "smoke" / "eval.yaml"


def smoke_spec() -> dict:
    return yaml.safe_load(SMOKE.read_text(encoding="utf-8"))


# --- the schemas themselves are valid ---------------------------------------


@pytest.mark.parametrize("name", SCHEMA_NAMES)
def test_schema_is_valid_jsonschema(name):
    schema = load_schema(name)
    jsonschema.validators.validator_for(schema).check_schema(schema)


def test_unknown_schema_name_rejected():
    with pytest.raises(ValueError):
        load_schema("nope")


# --- the example spec is green (positive control) ---------------------------


def test_smoke_example_validates():
    spec, issues = load_spec(SMOKE)
    assert spec is not None
    assert issues == [], [i.to_dict() for i in issues]


def test_smoke_items_validate():
    lines = (REPO / "examples" / "smoke" / "items.jsonl").read_text(encoding="utf-8").splitlines()
    canaries = [l for l in lines if "_canary" in l]
    items = [l for l in lines if l.strip() and "_canary" not in l]
    assert len(canaries) == 1, "example pods model the canary convention"
    assert len(items) == 6
    for line in items:
        assert validate_obj(json.loads(line), "items") == []


# --- witness rule: the load-bearing negative tests --------------------------


def test_scorer_without_witnesses_rejected():
    spec = smoke_spec()
    del spec["scorer"]["witnesses"]
    assert any("witnesses" in i.message for i in validate_obj(spec, "eval"))


def test_witnesses_without_a_must_fail_case_rejected():
    """A scorer that cannot fail is not a scorer. This is the core rule."""
    spec = smoke_spec()
    spec["scorer"]["witnesses"] = [
        w for w in spec["scorer"]["witnesses"] if w["expect"] == "pass"
    ]
    # keep >= 2 items so minItems is not what fires
    spec["scorer"]["witnesses"].append(dict(spec["scorer"]["witnesses"][0]))
    assert validate_obj(spec, "eval") != []


def test_witnesses_without_a_must_pass_case_rejected():
    spec = smoke_spec()
    spec["scorer"]["witnesses"] = [
        w for w in spec["scorer"]["witnesses"] if w["expect"] == "fail"
    ]
    assert validate_obj(spec, "eval") != []


# --- other required discipline fields ---------------------------------------


@pytest.mark.parametrize("field", ["seed", "budget_usd", "n"])
def test_run_field_required(field):
    spec = smoke_spec()
    del spec["run"][field]
    assert any(field in i.message for i in validate_obj(spec, "eval"))


def test_question_required():
    spec = smoke_spec()
    del spec["question"]
    assert validate_obj(spec, "eval") != []


def test_unknown_top_level_key_rejected():
    spec = smoke_spec()
    spec["surprise"] = True
    assert validate_obj(spec, "eval") != []


def test_python_scorer_requires_code_path():
    spec = smoke_spec()
    spec["scorer"]["kind"] = "python"
    assert any("code" in i.message for i in validate_obj(spec, "eval"))


# --- cross-file checks --------------------------------------------------------


def test_missing_data_file_caught(tmp_path):
    spec = smoke_spec()
    p = tmp_path / "eval.yaml"
    p.write_text(yaml.safe_dump(spec), encoding="utf-8")
    _, issues = load_spec(p)
    assert any(i.check == "path" for i in issues)


def test_absolute_data_path_rejected(tmp_path):
    spec = smoke_spec()
    spec["data"]["path"] = str(tmp_path / "items.jsonl")
    p = tmp_path / "eval.yaml"
    p.write_text(yaml.safe_dump(spec), encoding="utf-8")
    (tmp_path / "items.jsonl").write_text("", encoding="utf-8")
    _, issues = load_spec(p)
    assert any("relative" in i.message for i in issues)


def test_traversal_data_path_rejected(tmp_path):
    spec = smoke_spec()
    spec["data"]["path"] = "../items.jsonl"
    nest = tmp_path / "nest"
    nest.mkdir()
    p = nest / "eval.yaml"
    p.write_text(yaml.safe_dump(spec), encoding="utf-8")
    (tmp_path / "items.jsonl").write_text("", encoding="utf-8")
    _, issues = load_spec(p)
    assert any("escapes" in i.message for i in issues)


def test_absolute_scorer_path_rejected(tmp_path):
    spec = smoke_spec()
    spec["scorer"]["kind"] = "python"
    spec["scorer"]["code"] = str(tmp_path / "s.py")
    (tmp_path / "s.py").write_text("def score(o, t):\n    return True\n", encoding="utf-8")
    (tmp_path / "items.jsonl").write_text('{"id":"a","input":"q?","target":"t"}\n', encoding="utf-8")
    p = tmp_path / "eval.yaml"
    p.write_text(yaml.safe_dump(spec), encoding="utf-8")
    _, issues = load_spec(p)
    assert any("scorer code" in i.message and "relative" in i.message for i in issues)


def test_traversal_scorer_path_rejected(tmp_path):
    spec = smoke_spec()
    spec["scorer"]["kind"] = "python"
    spec["scorer"]["code"] = "../s.py"
    nest = tmp_path / "nest"
    nest.mkdir()
    (tmp_path / "s.py").write_text("def score(o, t):\n    return True\n", encoding="utf-8")
    (nest / "items.jsonl").write_text('{"id":"a","input":"q?","target":"t"}\n', encoding="utf-8")
    p = nest / "eval.yaml"
    p.write_text(yaml.safe_dump(spec), encoding="utf-8")
    _, issues = load_spec(p)
    assert any("scorer code" in i.message and "escapes" in i.message for i in issues)


def test_unparseable_yaml_reported_not_raised(tmp_path):
    p = tmp_path / "eval.yaml"
    p.write_text("scorer: [unclosed", encoding="utf-8")
    spec, issues = load_spec(p)
    assert spec is None
    assert issues and issues[0].check == "parse"


# --- records and manifests ----------------------------------------------------


def test_record_uncheckable_is_a_legal_verdict():
    rec = {
        "item_id": "a1",
        "model": "dry-strong",
        "provider": "dry",
        "seed": 42,
        "output": "57",
        "score": {"verdict": "uncheckable"},
        "ts": "2026-08-07T00:00:00Z",
    }
    assert validate_obj(rec, "record") == []


def test_manifest_requires_witness_report():
    manifest = {
        "tool_version": "0.1.0",
        "spec_name": "smoke-arith",
        "spec_version": "0.1.0",
        "spec_sha256": "0" * 64,
        "data_sha256": "0" * 64,
        "provider": "dry",
        "model": "dry-strong",
        "seed": 42,
        "budget_cap_usd": 0,
        "started_at": "2026-08-07T00:00:00Z",
        "run_file": "runs/x.jsonl",
    }
    assert any("witness_report" in i.message for i in validate_obj(manifest, "manifest"))
    manifest["witness_report"] = {"n_witnesses": 3, "n_behaved": 3, "verdict": "validated"}
    assert validate_obj(manifest, "manifest") == []


def test_spec_sha256_matches_file_bytes():
    import hashlib

    assert spec_sha256(SMOKE) == hashlib.sha256(SMOKE.read_bytes()).hexdigest()
