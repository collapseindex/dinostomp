"""`run --models a,b` runs only the named arms of a spec, under the same spec hash.

A fleet that stops early (one provider failed after retries) leaves the
remaining arms unrun. Re-running the spec would pay for the finished arms
again; resuming continues one run only. The filter runs just the missing
arms, and their manifests carry the same spec hash as the finished ones, so
the report pools them as one fleet.
"""

import json

from dinostomp.runner import CANNOT_RUN, OK, run_spec
from tests.test_runner import make_eval


def two_dry(spec):
    spec["models"] = [{"provider": "dry", "model": "dry-strong"}, {"provider": "dry", "model": "dry-weak"}]


def test_filter_runs_only_the_named_arm(tmp_path):
    outcome = run_spec(make_eval(tmp_path, two_dry), only_models=["dry-weak"])
    assert outcome.exit_code == OK
    assert len(outcome.run_files) == 1 and "dry-weak" in outcome.run_files[0].name
    manifest = json.loads(outcome.run_files[0].with_name(outcome.run_files[0].stem + "_manifest.json")
                          .read_text(encoding="utf-8"))
    assert manifest["model"] == "dry-weak" and manifest["status"] == "complete"


def test_filter_and_full_run_share_the_spec_hash(tmp_path):
    spec = make_eval(tmp_path, two_dry)
    full = run_spec(spec)
    only = run_spec(spec, only_models=["dry-strong"])
    hashes = set()
    for out in (full, only):
        for rf in out.run_files:
            hashes.add(json.loads(rf.with_name(rf.stem + "_manifest.json").read_text(encoding="utf-8"))["spec_sha256"])
    assert len(hashes) == 1


def test_unknown_model_name_refuses(tmp_path):
    outcome = run_spec(make_eval(tmp_path, two_dry), only_models=["dry-strong", "nope"])
    assert outcome.exit_code == CANNOT_RUN
    assert any("nope" in i.message for i in outcome.issues)
