"""Wave 2 instruments: S9 shortcut sniffing (offline) and R13 blind
solvability (probe runs). The negative tests plant the Clever Hans and
assert the battery names him."""

import json
from pathlib import Path

import yaml

from dinostomp.runner import OK, blind_input, run_spec
from tests.test_lint import (FLEET, arith_items, choice_items, finding,
                             rewrite_run_consistently, stomp, write_eval)


# --- S9: surface-feature shortcut -----------------------------------------------


def test_s9_overlap_shortcut_flagged(tmp_path):
    """Gold options that echo the question's words are findable without a model."""
    items = []
    for i in range(24):
        gold = f"the blue widget {i}"
        distractors = [f"red gadget {i + 100}", f"green gizmo {i + 200}", f"black gimmick {i + 300}"]
        items.append({"id": f"c{i}",
                      "input": f"Which option mentions the blue widget {i} we discussed?",
                      "target": gold, "choices": [*distractors, gold]})
    report = stomp(write_eval(tmp_path, items))
    f = finding(report, "S9")
    assert f["level"] == "warn"
    assert any("question-overlap" in ex for ex in f["examples"])


def test_s9_shortest_shortcut_flagged(tmp_path):
    items = choice_items()
    for i in items:  # gold becomes the uniquely shortest option
        short_gold = i["target"][:2] + "!"
        i["choices"] = [short_gold if c == i["target"] else c + "-extended" for c in i["choices"]]
        i["target"] = short_gold
    report = stomp(write_eval(tmp_path, items))
    f = finding(report, "S9")
    assert f["level"] == "warn"
    assert any("shortest option" in ex for ex in f["examples"])


def test_s9_clean_choices_pass(tmp_path):
    report = stomp(write_eval(tmp_path, choice_items()))
    assert finding(report, "S9")["level"] == "pass"


def test_s9_na_on_freeform(tmp_path):
    report = stomp(write_eval(tmp_path, arith_items()))
    assert finding(report, "S9")["level"] == "n/a"


# --- blind probe runner mechanics ----------------------------------------------


def test_blind_input_strips_everything_but_format():
    choice = {"id": "x", "input": "What is the capital of France?", "target": "Paris",
              "choices": ["Paris", "Lyon"]}
    blind = blind_input(choice)
    assert "France" not in blind and "capital" not in blind
    assert "Paris" in blind and "Lyon" in blind, "options survive; the question does not"
    free = blind_input({"id": "y", "input": "What is 2+2?", "target": "4"})
    assert "2+2" not in free


def test_probe_run_is_tagged_and_separate(tmp_path):
    spec_path = write_eval(tmp_path, arith_items())
    assert run_spec(spec_path).exit_code == OK
    assert run_spec(spec_path, probe="blind").exit_code == OK
    run_dir = tmp_path / "data" / "runs"
    probe_manifests = [json.loads(p.read_text(encoding="utf-8"))
                       for p in run_dir.glob("*_manifest.json")]
    probes = [m for m in probe_manifests if m.get("probe") == "blind"]
    assert len(probes) == 1
    assert "blindprobe" in probes[0]["run_file"], "probe runs are visibly named"


def test_dry_probe_never_fools_r13(tmp_path):
    """The dry provider reads the key, so its blind accuracy is meaningless;
    a dry-only pod is n/a, not warned."""
    spec_path = write_eval(tmp_path, arith_items())
    run_spec(spec_path)
    run_spec(spec_path, probe="blind")
    report = stomp(spec_path)
    assert finding(report, "R13")["level"] == "n/a"


# --- R13: blind solvability -----------------------------------------------------


def forge_live(manifest_path: Path):
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    m["dry_run"] = False
    m["provider"] = "openrouter"
    manifest_path.write_text(json.dumps(m), encoding="utf-8")


def test_r13_blind_success_warns(tmp_path):
    items = choice_items()
    targets = {str(i["id"]): i["target"] for i in items}
    spec_path = write_eval(tmp_path, items)
    run_spec(spec_path)
    outcome = run_spec(spec_path, probe="blind")
    probe_file = outcome.run_files[0]

    def ace_it_blind(r, idx):  # the model finds gold without the question
        if idx % 4 != 3:
            r["output"] = targets[str(r["item_id"])]
            r["score"] = {"verdict": "pass"}
        else:
            r["output"] = "zz-not-an-option"
            r["score"] = {"verdict": "fail"}
        return r

    rewrite_run_consistently(spec_path, probe_file, ace_it_blind)
    forge_live(probe_file.with_name(probe_file.stem + "_manifest.json"))
    report = stomp(spec_path)
    f = finding(report, "R13")
    assert f["level"] == "warn"
    assert "WITHOUT the question" in f["detail"]


def test_r13_blind_at_floor_passes(tmp_path):
    items = choice_items()
    targets = {str(i["id"]): i["target"] for i in items}
    spec_path = write_eval(tmp_path, items)
    run_spec(spec_path)
    outcome = run_spec(spec_path, probe="blind")
    probe_file = outcome.run_files[0]

    def chance_blind(r, idx):  # blind guessing lands at the 1-in-4 floor
        if idx % 4 == 0:
            r["output"] = targets[str(r["item_id"])]
            r["score"] = {"verdict": "pass"}
        else:
            r["output"] = "zz-not-an-option"
            r["score"] = {"verdict": "fail"}
        return r

    rewrite_run_consistently(spec_path, probe_file, chance_blind)
    forge_live(probe_file.with_name(probe_file.stem + "_manifest.json"))
    report = stomp(spec_path)
    assert finding(report, "R13")["level"] == "pass"


def test_r13_probe_records_never_pollute_real_stats(tmp_path):
    """The probe run must not feed R7, the fleet matrix, or the summaries the
    battery pools; only R13 reads it."""
    spec_path = write_eval(tmp_path, arith_items(), models=FLEET)
    assert run_spec(spec_path).exit_code == OK
    run_spec(spec_path, probe="blind")
    report = stomp(spec_path)
    r7 = finding(report, "R7")
    # R7 judges per model now (a pooled fleet hides the one examinee sitting at
    # chance), so it counts models rather than records. The property under test
    # is unchanged: the probe contributes neither a model nor a record to it.
    per_model = r7["evidence"]["per_model_accuracy"]
    assert r7["witnesses"] == 6, "R7 counts real models only; the probe's run is excluded"
    assert len(per_model) == 6 and all(m.startswith("dry-") for m in per_model), per_model

def test_r13_ignores_probes_that_were_not_blind(tmp_path):
    """A shuffle/judge/canary probe ran with the inputs INTACT.

    Negative test for the filter: before it, any non-dry probe counted as blind
    evidence, so a shuffle probe scoring well made R13 announce that the eval
    was solvable without the question. Confidently, and backed by a run that
    had the question.
    """
    from dinostomp.lint import lint_eval
    from dinostomp.spec import spec_sha256

    pod = write_eval(tmp_path, choice_items(30),
                     models=[{"provider": "dry", "model": "dry-alpha"}])
    assert run_spec(pod).exit_code == OK
    runs = tmp_path / "data" / "runs"
    # the stem carries the spec name and model; run discovery reads it, and a
    # mismatched one makes the probe invisible (which is how the first version
    # of this test passed against the unfixed code)
    stem = "20260808_000000_lint-fixture_dry-alpha_shuffleprobe_s7"
    recs = [{"key": f"i{i}", "item_id": f"i{i}", "model": "dry-alpha",
             "provider": "openrouter", "seed": 7, "output": "x",
             "score": {"verdict": "pass"}, "ts": "x"} for i in range(30)]
    (runs / f"{stem}.jsonl").write_text(
        "\n".join(json.dumps(r) for r in recs) + "\n", encoding="utf-8")
    (runs / f"{stem}_manifest.json").write_text(json.dumps({
        "tool_version": "0", "spec_name": "lint-fixture", "spec_version": "0.1.0",
        "spec_sha256": spec_sha256(pod), "data_sha256": spec_sha256(tmp_path / "items.jsonl"),
        "provider": "openrouter", "model": "dry-alpha", "seed": 7, "budget_cap_usd": 0,
        "probe": "shuffle", "dry_run": False,
        "witness_report": {"n_witnesses": 0, "n_behaved": 0, "verdict": "absent"},
        "started_at": "x", "run_file": f"{stem}.jsonl", "status": "complete",
    }), encoding="utf-8")
    report, _ = lint_eval(pod)
    r13 = next(f for f in report["findings"] if f["id"] == "R13")
    assert r13["level"] in ("skip", "n/a"), "a 100% shuffle probe is not 100% blind accuracy"
    assert "blind" in r13["detail"].lower()
