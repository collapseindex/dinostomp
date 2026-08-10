"""Stomp battery tests, selftest style: build a clean eval, inject exactly one
defect, assert the one matching check fires. Plus placebo (clean fixtures must
come out clean) and vacuous-pass protection.
"""

import json
from pathlib import Path

import pytest
import yaml

from dinostomp import validate_obj
from dinostomp.lint import Reporter, lint_eval
from dinostomp.runner import OK, run_spec

# Gauntlet-hardened: each fail witness kills a specific mutant class.
WITNESSES = [
    {"output": "57", "target": "57", "expect": "pass"},
    {"output": "The answer is 57", "target": "57", "expect": "fail"},   # substring-lenient
    {"output": "5", "target": "57", "expect": "fail"},                  # prefix-lenient
    {"output": "not 57", "target": "57", "expect": "fail"},             # negation-blind
    {"output": "FIFTY", "target": "fifty", "expect": "fail"},           # case-blind
]


def arith_items(n=24):
    out = []
    for i in range(10, 10 + n):
        out.append({"id": f"a{i}", "input": f"What is {i} + {i + 1}? Reply with the bare number.",
                    "target": str(2 * i + 1)})
    return out


def choice_items(n=24):
    out = []
    fruits = ["apple", "pear", "plum", "kiwi"]
    for i in range(n):
        choices = [f"{f}{i}" for f in fruits]
        out.append({"id": f"c{i}", "input": f"Pick the correct fruit for slot {i}.",
                    "target": choices[i % 4], "choices": choices})
    return out


FLEET = [{"provider": "dry", "model": f"dry-{x}"}
         for x in ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot")]


def write_eval(tmp_path: Path, items, name="lint-fixture", models=None, witnesses=None) -> Path:
    spec = {
        "name": name,
        "version": "0.1.0",
        "question": "Does the model pick the declared target exactly?",
        "data": {"path": "items.jsonl", "format": "jsonl"},
        "models": models or [{"provider": "dry", "model": "dry-strong"}],
        "scorer": {"kind": "exact", "witnesses": witnesses or WITNESSES},
        "run": {"n": len(items), "seed": 7, "budget_usd": 0},
    }
    lines = ['{"_canary": "dinostomp canary DO NOT TRAIN test-fixture"}']
    lines += [json.dumps(i) for i in items]
    (tmp_path / "items.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    p = tmp_path / "eval.yaml"
    p.write_text(yaml.safe_dump(spec), encoding="utf-8")
    return p


def finding(report, cid):
    return next(f for f in report["findings"] if f["id"] == cid)


def stomp(spec_path):
    report, issues = lint_eval(spec_path)
    assert report is not None, issues
    return report


# --- placebo: clean fixtures must come out clean ------------------------------


def test_placebo_freeform_fleet_is_clean(tmp_path):
    spec_path = write_eval(tmp_path, arith_items(), models=FLEET)
    assert run_spec(spec_path).exit_code == OK
    report = stomp(spec_path)
    assert report["summary"]["verdict"] == "sound", report["findings"]
    assert validate_obj(report, "report") == []


def test_placebo_choices_fleet_is_clean(tmp_path):
    spec_path = write_eval(tmp_path, choice_items(), models=FLEET)
    assert run_spec(spec_path).exit_code == OK
    report = stomp(spec_path)
    assert report["summary"]["verdict"] == "sound", report["findings"]


def test_single_model_skips_psychometrics_with_unlock_hint(tmp_path):
    spec_path = write_eval(tmp_path, arith_items())
    assert run_spec(spec_path).exit_code == OK
    report = stomp(spec_path)
    assert report["summary"]["verdict"] == "incomplete", "one model can never be a clean bill of health"
    p1 = finding(report, "P1")
    assert p1["level"] == "skip"
    assert "unlock" in p1["detail"]


def test_no_runs_is_incomplete_never_clean(tmp_path):
    report = stomp(write_eval(tmp_path, arith_items()))
    assert report["summary"]["verdict"] == "incomplete"
    assert finding(report, "R1")["level"] == "skip"


# --- S-series: one injected defect each ----------------------------------------


def test_s1_duplicate_question(tmp_path):
    items = arith_items()
    items[5]["input"] = items[3]["input"]
    report = stomp(write_eval(tmp_path, items))
    assert finding(report, "S1")["level"] == "fail"
    assert report["summary"]["verdict"] == "broken"


def test_s2_answer_leak(tmp_path):
    # TEXT targets: a purely numeric target is exempt, because a number in a
    # word problem is a premise rather than a disclosure. Pointing S2 at GSM8K
    # called 27 items leaks, every one of them a quantity the question needed.
    items = [{"id": f"t{i}", "input": f"Which country is city {i} the capital of?",
              "target": name} for i, name in enumerate(
                  ["France", "Japan", "Canada", "Norway", "Peru", "Egypt", "Ireland",
                   "Greece", "Vietnam", "Cuba", "Poland", "Austria", "Morocco", "Jordan",
                   "Ecuador", "Kenya", "Portugal", "Finland", "Sweden", "Hungary"])]
    items[4]["input"] += " (hint: it is " + items[4]["target"] + ")"
    witnesses = [{"output": "France", "target": "France", "expect": "pass"},
                 {"output": "The answer is France", "target": "France", "expect": "fail"},
                 {"output": "Fran", "target": "France", "expect": "fail"},
                 {"output": "not France", "target": "France", "expect": "fail"},
                 {"output": "france", "target": "France", "expect": "fail"}]
    report = stomp(write_eval(tmp_path, items, witnesses=witnesses))
    assert finding(report, "S2")["level"] == "fail"


def test_s2_ignores_a_number_the_question_needed(tmp_path):
    """GSM8K's answer is often a quantity that also appears as a premise."""
    items = arith_items()
    items[4]["input"] += " (the shop had " + items[4]["target"] + " in stock)"
    report = stomp(write_eval(tmp_path, items))
    assert finding(report, "S2")["level"] in ("pass", "n/a")


def test_s2_ignores_a_forced_choice_that_names_its_own_answer(tmp_path):
    """TruthfulQA asks "Have Christians or Jews won more Nobel Prizes?" and
    accepts "Christians". The question cannot be asked without containing it."""
    items = [{"id": f"t{i}", "input": f"Did group {i} or the other group win more medals?",
              "target": name} for i, name in enumerate(
                  ["Alphas", "Betas", "Gammas", "Deltas", "Epsilons", "Zetas", "Etas",
                   "Thetas", "Iotas", "Kappas", "Lambdas", "Mus", "Nus", "Xis", "Omicrons",
                   "Pis", "Rhos", "Sigmas", "Taus", "Upsilons"])]
    items[3]["input"] = "Did the Deltas or the Gammas win more medals?"
    witnesses = [{"output": "Alphas", "target": "Alphas", "expect": "pass"},
                 {"output": "Betas", "target": "Alphas", "expect": "fail"},
                 {"output": "Alpha", "target": "Alphas", "expect": "fail"},
                 {"output": "not Alphas", "target": "Alphas", "expect": "fail"},
                 {"output": "alphas", "target": "Alphas", "expect": "fail"}]
    report = stomp(write_eval(tmp_path, items, witnesses=witnesses))
    assert finding(report, "S2")["level"] == "pass"


def test_s3_position_bias(tmp_path):
    items = choice_items()
    for i in items:  # gold always first
        gold = i["target"]
        i["choices"].remove(gold)
        i["choices"].insert(0, gold)
    report = stomp(write_eval(tmp_path, items))
    assert finding(report, "S3")["level"] == "warn", "statistical bias is a diagnostic, not a proof"
    assert report["summary"]["verdict"] != "broken"


def test_s4_longest_option_bias(tmp_path):
    items = choice_items()
    for i in items:
        gold = i["target"]
        long_gold = gold + "-the-obviously-correct-one"
        i["choices"] = [long_gold if c == gold else c for c in i["choices"]]
        i["target"] = long_gold
    report = stomp(write_eval(tmp_path, items))
    assert finding(report, "S4")["level"] == "warn", "statistical bias is a diagnostic, not a proof"


def test_s5_duplicate_option(tmp_path):
    items = choice_items()
    items[2]["choices"][1] = items[2]["choices"][0]
    items[2]["target"] = items[2]["choices"][0]
    report = stomp(write_eval(tmp_path, items))
    assert finding(report, "S5")["level"] == "fail"


def test_s6_target_not_in_choices(tmp_path):
    items = choice_items()
    items[7]["target"] = "banana999"
    report = stomp(write_eval(tmp_path, items))
    assert finding(report, "S6")["level"] == "fail"


def test_s7_contradictory_targets(tmp_path):
    items = arith_items()
    items[8]["input"] = items[2]["input"]
    items[8]["target"] = "999"
    report = stomp(write_eval(tmp_path, items))
    assert finding(report, "S7")["level"] == "fail"


def test_s3_s4_skip_below_min_witnesses(tmp_path):
    report = stomp(write_eval(tmp_path, choice_items(8)))
    assert finding(report, "S3")["level"] == "skip"
    assert finding(report, "S4")["level"] == "skip"


def test_choice_checks_na_on_freeform_dataset(tmp_path):
    report = stomp(write_eval(tmp_path, arith_items()))
    for cid in ("S3", "S4", "S5", "S6"):
        assert finding(report, cid)["level"] == "n/a"


# --- R-series: break the run artifacts ------------------------------------------


def ran_eval(tmp_path, items=None):
    spec_path = write_eval(tmp_path, items or arith_items())
    outcome = run_spec(spec_path)
    assert outcome.exit_code == OK
    run_file = outcome.run_files[0]
    manifest_path = run_file.with_name(run_file.stem + "_manifest.json")
    return spec_path, run_file, manifest_path


def test_r1_spec_drift_fires(tmp_path):
    spec_path, _, _ = ran_eval(tmp_path)
    spec_path.write_text(spec_path.read_text(encoding="utf-8") + "\n# tweaked after the run\n",
                         encoding="utf-8")
    report = stomp(spec_path)
    assert finding(report, "R1")["level"] == "fail"
    assert report["summary"]["verdict"] == "broken"


def test_r1_data_drift_fires(tmp_path):
    spec_path, _, _ = ran_eval(tmp_path)
    items_file = tmp_path / "items.jsonl"
    items_file.write_text(
        items_file.read_text(encoding="utf-8") + '{"id": "a99", "input": "sneaky new item?", "target": "yes"}\n',
        encoding="utf-8",
    )
    report = stomp(spec_path)
    f = finding(report, "R1")
    assert f["level"] == "fail"
    assert any("data" in ex for ex in f["examples"])


def test_r1_scorer_code_drift_fires(tmp_path):
    (tmp_path / "scorer.py").write_text(
        "def score(output, target):\n    return output.strip() == str(target)\n", encoding="utf-8")
    spec_path = write_eval(tmp_path, arith_items())
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    spec["scorer"] = {"kind": "python", "code": "scorer.py", "witnesses": WITNESSES}
    spec_path.write_text(yaml.safe_dump(spec), encoding="utf-8")
    assert run_spec(spec_path).exit_code == OK

    (tmp_path / "scorer.py").write_text(
        "def score(output, target):\n    return True  # everything passes now, hooray\n", encoding="utf-8")
    report = stomp(spec_path)
    f = finding(report, "R1")
    assert f["level"] == "fail"
    assert any("scorer" in ex for ex in f["examples"])


def test_r2_hacked_witness_report_fires(tmp_path):
    spec_path, _, manifest_path = ran_eval(tmp_path)
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    m["witness_report"]["verdict"] = "failed"
    manifest_path.write_text(json.dumps(m), encoding="utf-8")
    report = stomp(spec_path)
    assert finding(report, "R2")["level"] == "fail"


def test_r3_overspend_fires(tmp_path):
    spec_path, _, manifest_path = ran_eval(tmp_path)
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    m["spend_usd"] = m["budget_cap_usd"] + 1.0
    manifest_path.write_text(json.dumps(m), encoding="utf-8")
    report = stomp(spec_path)
    assert finding(report, "R3")["level"] == "fail"


def test_r4_corrupt_record_fires(tmp_path):
    spec_path, run_file, _ = ran_eval(tmp_path)
    with run_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"key": "zz#r0", "output": "orphan"}) + "\n")
    report = stomp(spec_path)
    assert finding(report, "R4")["level"] == "fail"


def test_r5_credited_truncation_fires(tmp_path):
    spec_path, run_file, _ = ran_eval(tmp_path)
    records = [json.loads(l) for l in run_file.read_text(encoding="utf-8").splitlines()]
    victim = next(r for r in records if r["score"]["verdict"] == "pass")
    victim["finish_reason"] = "length"
    run_file.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    report = stomp(spec_path)
    assert finding(report, "R5")["level"] == "fail"


def rewrite_run_consistently(spec_path, run_file, mutate_record):
    """Rewrite records AND regenerate the summary, so only the intended
    inconsistency remains. The battery now cross-checks outputs, verdicts,
    and summaries against each other; a lazy forgery trips R8/R9 instead of
    the check under test."""
    from dinostomp.runner import summarize

    records = [json.loads(l) for l in run_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    records = [mutate_record(r, i) for i, r in enumerate(records)]
    run_file.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    summary_path = run_file.parents[1] / "results" / (run_file.stem + "_summary.json")
    published = json.loads(summary_path.read_text(encoding="utf-8"))
    published.update(summarize(records))
    summary_path.write_text(json.dumps(published), encoding="utf-8")


def test_r7_chance_level_accuracy_warns(tmp_path):
    items = choice_items()
    targets = {str(i["id"]): i["target"] for i in items}
    spec_path, run_file, _ = ran_eval(tmp_path, items)

    def to_chance(r, idx):  # consistent forgery: outputs agree with verdicts
        if idx % 4 == 0:
            r["output"] = targets[str(r["item_id"])]
            r["score"] = {"verdict": "pass"}
        else:
            r["output"] = "zz-not-an-option"
            r["score"] = {"verdict": "fail"}
        return r

    rewrite_run_consistently(spec_path, run_file, to_chance)
    report = stomp(spec_path)
    f = finding(report, "R7")
    assert f["level"] == "warn"
    assert report["summary"]["verdict"] != "broken", "soft check must warn, not break"


def test_forged_verdicts_are_caught_by_rescoring(tmp_path):
    """The lazy version of the forgery above: flip verdicts without touching
    outputs. R8 must catch it and the verdict must be broken."""
    spec_path, run_file, _ = ran_eval(tmp_path)
    records = [json.loads(l) for l in run_file.read_text(encoding="utf-8").splitlines()]
    victim = next(r for r in records if r["score"]["verdict"] == "pass")
    victim["score"]["verdict"] = "fail"
    run_file.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    report = stomp(spec_path)
    f = finding(report, "R8")
    assert f["level"] == "fail"
    assert any("re-scores pass" in ex for ex in f["examples"])
    assert report["summary"]["verdict"] == "broken"


def test_s2_candidate_list_is_not_a_leak(tmp_path):
    """A question offering the answer space ('answer yes, no, or maybe') names
    its own target without leaking anything."""
    items = []
    for i, t in enumerate(["yes", "no", "maybe", "yes", "no", "maybe"] * 4):
        items.append({"id": f"c{i}", "input": f"Question {i}: answer yes, no, or maybe.", "target": t})
    report = stomp(write_eval(tmp_path, items))
    assert finding(report, "S2")["level"] == "pass", "candidate lists must be exempt"


def test_s8_missing_canary_warns(tmp_path):
    spec_path = write_eval(tmp_path, arith_items())
    items_file = tmp_path / "items.jsonl"
    lines = [l for l in items_file.read_text(encoding="utf-8").splitlines() if "_canary" not in l]
    items_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report = stomp(spec_path)
    f = finding(report, "S8")
    assert f["level"] == "warn"
    assert "_canary" in f["detail"]


def test_p7_ceiling_pinning_warns(tmp_path):
    spec_path, run_files = fleet_eval(tmp_path)

    def ace_everything(r):
        r["score"] = {"verdict": "pass"}
        return r

    rewrite_records(run_files, ace_everything)
    report = stomp(spec_path)
    f = finding(report, "P7")
    assert f["level"] == "warn"
    assert any("saturated" in ex for ex in f["examples"])


def test_p7_floor_pinning_warns(tmp_path):
    spec_path, run_files = fleet_eval(tmp_path)

    def flunk_everything(r):
        r["score"] = {"verdict": "fail"}
        return r

    rewrite_records(run_files, flunk_everything)
    report = stomp(spec_path)
    f = finding(report, "P7")
    assert f["level"] == "warn"
    assert any("broken key" in ex for ex in f["examples"])


def test_p8_no_dynamic_range_warns(tmp_path):
    spec_path, run_files = fleet_eval(tmp_path)

    def same_for_everyone(r):  # verdict depends only on the item: zero spread
        r["score"] = {"verdict": "pass" if int(r["item_id"][1:]) % 2 else "fail"}
        return r

    rewrite_records(run_files, same_for_everyone)
    report = stomp(spec_path)
    assert finding(report, "P8")["level"] == "warn"


def test_r7_informed_guesser_floor_beats_uniform(tmp_path):
    """A free-form dataset with a skewed answer key: 85% accuracy sounds great
    until you notice 80% of the targets are the same word."""
    items = []
    for i in range(24):
        target = "yes" if i < 19 else f"word{i}"
        items.append({"id": f"g{i}", "input": f"Question number {i}, please answer.", "target": target})
    spec_path = write_eval(tmp_path, items)
    outcome = run_spec(spec_path)
    assert outcome.exit_code == OK

    targets = {str(i["id"]): i["target"] for i in items}

    def modal_guesser(r, idx):  # consistent forgery: right on every 'yes', wrong elsewhere
        t = targets[str(r["item_id"])]
        if t == "yes":
            r["output"] = "yes"
            r["score"] = {"verdict": "pass"}
        else:
            r["output"] = "yes"
            r["score"] = {"verdict": "fail"}
        return r

    rewrite_run_consistently(spec_path, outcome.run_files[0], modal_guesser)
    report = stomp(spec_path)
    f = finding(report, "R7")
    assert f["level"] == "warn", "79% accuracy must not beat a 79% modal floor"
    assert "modal target" in f["detail"]


def test_s2_ignores_one_char_targets(tmp_path):
    items = arith_items()
    items.append({"id": "tiny", "input": "How many suns? Reply 1 or 2.", "target": "1"})
    report = stomp(write_eval(tmp_path, items))
    assert finding(report, "S2")["level"] == "pass", "min_leak_len must exempt 1-char targets"


def test_r6_high_uncheckable_rate_warns(tmp_path):
    items = arith_items()
    spec_path = write_eval(tmp_path, items)
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    spec["scorer"] = {
        "kind": "numeric",
        "witnesses": [
            {"output": "57", "target": "57", "expect": "pass"},
            {"output": "58", "target": "57", "expect": "fail"},
        ],
    }
    spec_path.write_text(yaml.safe_dump(spec), encoding="utf-8")
    outcome = run_spec(spec_path)
    assert outcome.exit_code == OK
    run_file = outcome.run_files[0]

    def go_mute(r, idx):  # consistent forgery: wordless outputs are uncheckable for numeric
        r["output"] = "no comment"
        r["score"] = {"verdict": "uncheckable"}
        return r

    rewrite_run_consistently(spec_path, run_file, go_mute)
    report = stomp(spec_path)
    assert finding(report, "R6")["level"] == "warn"


def test_r9_edited_summary_fires(tmp_path):
    spec_path, run_file, _ = ran_eval(tmp_path)
    summary_path = run_file.parents[1] / "results" / (run_file.stem + "_summary.json")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["accuracy_on_checkable"] = 0.99
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    report = stomp(spec_path)
    assert finding(report, "R9")["level"] == "fail"
    assert report["summary"]["verdict"] == "broken"


def test_r10_foreign_run_warns_and_is_quarantined(tmp_path):
    spec_path, run_files = fleet_eval(tmp_path)
    stray_manifest = run_files[0].with_name(run_files[0].stem + "_manifest.json")
    m = json.loads(stray_manifest.read_text(encoding="utf-8"))
    m["spec_name"] = "some-other-eval"
    stray_manifest.write_text(json.dumps(m), encoding="utf-8")
    report = stomp(spec_path)
    f = finding(report, "R10")
    assert f["level"] == "warn"
    assert any("foreign" in ex for ex in f["examples"])
    assert finding(report, "R1")["witnesses"] == len(run_files) - 1, "foreign run must not feed R1"


def test_r10_narrowed_run_warns(tmp_path):
    spec_path = write_eval(tmp_path, arith_items())
    assert run_spec(spec_path, limit=3).exit_code == OK
    report = stomp(spec_path)
    f = finding(report, "R10")
    assert f["level"] == "warn"
    assert any("3 of the spec's 24" in ex for ex in f["examples"])


def test_r11_deleted_miss_fires(tmp_path):
    spec_path, run_file, _ = ran_eval(tmp_path)
    records = [json.loads(l) for l in run_file.read_text(encoding="utf-8").splitlines()]
    dropped = records[:-1]  # delete the last item from a run that claims complete
    run_file.write_text("\n".join(json.dumps(r) for r in dropped) + "\n", encoding="utf-8")
    summary_path = run_file.parents[1] / "results" / (run_file.stem + "_summary.json")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    from dinostomp.runner import summarize

    summary.update(summarize(dropped))
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    report = stomp(spec_path)
    f = finding(report, "R11")
    assert f["level"] == "fail"
    assert any("1 missing" in ex for ex in f["examples"])


def test_r12_selective_uncheckability_flagged(tmp_path):
    """A model whose outputs increasingly evade the scorer must not hide
    behind a healthy conditional accuracy."""
    spec_path = write_eval(tmp_path, arith_items(), models=FLEET)
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    spec["scorer"] = {
        "kind": "numeric",
        "witnesses": [
            {"output": "57", "target": "57", "expect": "pass"},
            {"output": "58", "target": "57", "expect": "fail"},
            {"output": "mysterious silence", "target": "57", "expect": "uncheckable"},
        ],
    }
    spec_path.write_text(yaml.safe_dump(spec), encoding="utf-8")
    assert run_spec(spec_path).exit_code == OK
    run_files = sorted((tmp_path / "data" / "runs").glob("*.jsonl"))

    def evade_for_alpha(r, idx):  # dry-alpha's outputs become unjudgeable half the time
        if r["model"] == "dry-alpha" and idx % 2 == 0:
            r["output"] = "mysterious silence"
            r["score"] = {"verdict": "uncheckable"}
        return r

    for rf in run_files:
        rewrite_run_consistently(spec_path, rf, evade_for_alpha)
    report = stomp(spec_path)
    f = finding(report, "R12")
    assert f["level"] == "warn"
    assert any("dry-alpha" in ex for ex in f["examples"])


def test_r12_skips_single_model(tmp_path):
    spec_path = write_eval(tmp_path, arith_items())
    run_spec(spec_path)
    report = stomp(spec_path)
    assert finding(report, "R12")["level"] == "skip"


def test_summary_carries_judgeability(tmp_path):
    spec_path = write_eval(tmp_path, arith_items())
    outcome = run_spec(spec_path)
    assert outcome.summaries[0]["judgeability"] == 1.0


def test_manifest_carries_env_and_reported_model(tmp_path):
    spec_path = write_eval(tmp_path, arith_items())
    outcome = run_spec(spec_path)
    manifest = json.loads(
        outcome.run_files[0].with_name(outcome.run_files[0].stem + "_manifest.json").read_text(encoding="utf-8"))
    assert manifest["env"]["python"]
    assert manifest["env"]["packages"]["dinostomp"] != ""
    assert manifest["model_reported"] == "dry-strong", "dry reports itself; hosted providers report their alias"


# --- P-series: fleet psychometrics -----------------------------------------------


def fleet_eval(tmp_path, items=None):
    spec_path = write_eval(tmp_path, items or arith_items(), models=FLEET)
    outcome = run_spec(spec_path)
    assert outcome.exit_code == OK
    return spec_path, sorted((tmp_path / "data" / "runs").glob("*.jsonl"))


def rewrite_records(run_files, fn):
    """Apply fn(record) -> record to every record in every run file."""
    for rf in run_files:
        records = [json.loads(l) for l in rf.read_text(encoding="utf-8").splitlines() if l.strip()]
        records = [fn(r) for r in records]
        rf.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")


def test_p1_unreliable_totals_warn(tmp_path):
    spec_path, run_files = fleet_eval(tmp_path)

    def scramble(r):  # checkerboard: every model totals the same, reliability undefined
        parity = (sum(r["model"].encode()) + int(r["item_id"][1:])) % 2
        r["score"]["verdict"] = "pass" if parity == 0 else "fail"
        return r

    rewrite_records(run_files, scramble)
    report = stomp(spec_path)
    assert finding(report, "P1")["level"] == "warn"


def test_p2_inverted_key_flagged(tmp_path):
    spec_path, run_files = fleet_eval(tmp_path)

    def invert_a15(r):  # a15's key is now wrong: strong models "miss", weak "hit"
        if r["item_id"] == "a15":
            r["score"]["verdict"] = "fail" if r["score"]["verdict"] == "pass" else "pass"
        return r

    rewrite_records(run_files, invert_a15)
    report = stomp(spec_path)
    f = finding(report, "P2")
    assert f["level"] == "warn"
    assert any("a15" in ex for ex in f["examples"])


def test_p3_dead_weight_warns(tmp_path):
    spec_path, run_files = fleet_eval(tmp_path)

    def flatten(r):  # everyone right: the test separates nobody
        r["score"]["verdict"] = "pass"
        return r

    rewrite_records(run_files, flatten)
    report = stomp(spec_path)
    assert finding(report, "P3")["level"] == "warn"


def test_p4_ragged_matrix_fails(tmp_path):
    spec_path, run_files = fleet_eval(tmp_path)
    victim = run_files[0]
    records = [json.loads(l) for l in victim.read_text(encoding="utf-8").splitlines() if l.strip()]
    records = [r for r in records if r["item_id"] != "a12"]
    victim.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    report = stomp(spec_path)
    assert finding(report, "P4")["level"] == "fail"
    assert report["summary"]["verdict"] == "broken"


def test_p5_unanimous_wrong_answer_flagged(tmp_path):
    spec_path, run_files = fleet_eval(tmp_path)

    def unanimize(r):  # whole fleet gives the same wrong answer on a20
        if r["item_id"] == "a20":
            r["output"] = "wrongzz"
            r["score"]["verdict"] = "fail"
        return r

    rewrite_records(run_files, unanimize)
    report = stomp(spec_path)
    f = finding(report, "P5")
    assert f["level"] == "warn"
    assert any("a20" in ex for ex in f["examples"])


def test_p6_na_without_an_ordering_claim(tmp_path):
    spec_path = write_eval(tmp_path, arith_items(), models=FLEET)
    run_spec(spec_path)
    report = stomp(spec_path)
    assert finding(report, "P6")["level"] == "n/a"


def test_p6_ordering_claim_within_noise_warns(tmp_path):
    spec_path = write_eval(tmp_path, arith_items(), models=FLEET)
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    spec["entitled_claims"] = ["Relative ordering of the six dry models."]
    spec_path.write_text(yaml.safe_dump(spec), encoding="utf-8")
    run_spec(spec_path)
    report = stomp(spec_path)
    f = finding(report, "P6")
    assert f["level"] == "warn", "dry-alpha and dry-delta tie; the claimed ordering is inside noise"
    assert any("flips or ties" in ex for ex in f["examples"])


def test_p6_clearly_separated_ordering_passes(tmp_path):
    two = [{"provider": "dry", "model": "dry-alpha"}, {"provider": "dry", "model": "dry-charlie"}]
    spec_path = write_eval(tmp_path, arith_items(), models=two)
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    spec["entitled_claims"] = ["dry-alpha ranks above dry-charlie on this item set."]
    spec_path.write_text(yaml.safe_dump(spec), encoding="utf-8")
    run_spec(spec_path)
    report = stomp(spec_path)
    assert finding(report, "P6")["level"] == "pass", "100% vs 37.5% on 24 items separates cleanly"


# --- reporter discipline -----------------------------------------------------------


def test_zero_witness_pass_becomes_skip():
    rep = Reporter()
    rep.check("S1", ok=True, detail="looked at nothing", n=0)
    assert rep.findings["S1"].level == "skip"


def test_unreached_checks_count_as_skipped_in_report():
    rep = Reporter()
    report = rep.report("nowhere")
    assert report["summary"]["verdict"] == "incomplete"
    assert len(report["coverage"]["skipped"]) == len(report["findings"])


def test_report_validates_against_schema(tmp_path):
    report = stomp(write_eval(tmp_path, arith_items()))
    assert validate_obj(report, "report") == []


def test_s2_forced_choice_exemption_does_not_open_on_a_distant_or(tmp_path):
    """The exemption is for the alternatives a question OFFERS.

    Negative half of the forced-choice rule: appending an unrelated "or" to a
    leaky question must not open the gate, or the exemption is a one-word
    bypass of a gating check.
    """
    items = [{"id": f"t{i}", "input": f"Which country is city {i} the capital of?",
              "target": name} for i, name in enumerate(
                  ["France", "Japan", "Canada", "Norway", "Peru", "Egypt", "Ireland",
                   "Greece", "Vietnam", "Cuba", "Poland", "Austria", "Morocco", "Jordan",
                   "Ecuador", "Kenya", "Portugal", "Finland", "Sweden", "Hungary"])]
    items[4]["input"] = ("The answer is Peru. " + "Padding that pushes the leak well away. " * 3
                         + "Answer in English or in French.")
    witnesses = [{"output": "France", "target": "France", "expect": "pass"},
                 {"output": "The answer is France", "target": "France", "expect": "fail"},
                 {"output": "Fran", "target": "France", "expect": "fail"},
                 {"output": "not France", "target": "France", "expect": "fail"},
                 {"output": "france", "target": "France", "expect": "fail"}]
    report = stomp(write_eval(tmp_path, items, witnesses=witnesses))
    assert finding(report, "S2")["level"] == "fail"


# --- item identity: a choice item is its question PLUS its options -------------


def _mc(iid, question, choices, target):
    return {"id": iid, "input": question, "choices": choices, "target": target}


def _mc_pod(tmp_path, items):
    witnesses = [{"output": "alpha", "target": "alpha", "expect": "pass"},
                 {"output": "beta", "target": "alpha", "expect": "fail"}]
    return write_eval(tmp_path, items, witnesses=witnesses)


def test_s1_same_stem_different_options_is_not_a_duplicate(tmp_path):
    """MMLU asks "Which of the following statements is correct?" many times.

    Keyed on the stem alone, 22 such items were called duplicates and 11 called
    contradictory, both on GATING checks. The options are half the question.
    """
    items = [_mc(f"i{i}", "Which of the following statements is correct?",
                 [f"alpha{i}", f"beta{i}", f"gamma{i}", f"delta{i}"], f"alpha{i}")
             for i in range(20)]
    report = stomp(_mc_pod(tmp_path, items))
    assert finding(report, "S1")["level"] == "pass"
    assert finding(report, "S7")["level"] == "pass"


def test_s1_still_catches_a_genuine_duplicate_choice_item(tmp_path):
    """The other half: identical stem AND identical options IS one item twice.

    MMLU's first 3000 test rows contain 90 of these.
    """
    items = [_mc(f"i{i}", f"Question {i}?",
                 [f"alpha{i}", f"beta{i}", f"gamma{i}", f"delta{i}"], f"alpha{i}")
             for i in range(20)]
    items.append(_mc("dup", "Question 3?", ["alpha3", "beta3", "gamma3", "delta3"], "alpha3"))
    report = stomp(_mc_pod(tmp_path, items))
    assert finding(report, "S1")["level"] == "fail"


def test_s1_ignores_option_ORDER_when_deciding_identity(tmp_path):
    """Same options in a different arrangement is the same item presented
    differently. P9 is the check that cares about arrangement."""
    items = [_mc(f"i{i}", f"Question {i}?",
                 [f"alpha{i}", f"beta{i}", f"gamma{i}", f"delta{i}"], f"alpha{i}")
             for i in range(20)]
    items.append(_mc("perm", "Question 3?", ["delta3", "alpha3", "gamma3", "beta3"], "alpha3"))
    report = stomp(_mc_pod(tmp_path, items))
    assert finding(report, "S1")["level"] == "fail"


def test_s5_leaves_notation_alone_when_case_carries_the_content(tmp_path):
    """MMLU's Punnett-square items offer 'BB Bb' against 'Bb bb'.

    Naive case-folding calls four correct MMLU items defective. The rule is not
    "never fold case", it is that a WIDE collapse means the case is the content:
    these four options fold to one string, so folding them proves nothing.
    """
    items = [_mc(f"i{i}", f"Cross {i}?", ["BB BB", "BB Bb", "Bb Bb", "Bb bb"], "Bb Bb")
             for i in range(20)]
    report = stomp(_mc_pod(tmp_path, items))
    assert finding(report, "S5")["level"] == "pass"
    items.append(_mc("real", "Cross X?", ["687", "687", "1,493", "1,695"], "687"))
    report = stomp(_mc_pod(tmp_path, items))
    assert finding(report, "S5")["level"] == "fail", "an exact repeat is still a defect"


def test_s5_catches_a_case_only_duplicate_when_exactly_one_pair_collapses(tmp_path):
    """The catch the strict rule was costing, confirmed by human annotation.

    `Sc = Ej` against `sC = eJ` in MMLU's predicate logic is labelled
    `multiple_correct_answers` by MMLU-Redux's annotators (N-012). Exactly one
    pair collapses under folding, which is what separates it from the genetics
    items above where all four do.
    """
    items = [_mc(f"i{i}", f"Which formula {i}?",
                 ["Cs > Ej", "Sc = Ej", "sC = eJ", "Sx = Jy"], "Sc = Ej")
             for i in range(20)]
    report = stomp(_mc_pod(tmp_path, items))
    assert finding(report, "S5")["level"] == "fail"
    assert "case or spacing" in finding(report, "S5")["detail"]


def test_s5_ignores_a_wide_case_collapse_even_at_three(tmp_path):
    """The boundary, stated as a test rather than left to the reader.

    Three of four options folding together is still a wide collapse and still
    reads as notation. Only a single collapsed PAIR is treated as a duplicate.
    """
    items = [_mc(f"i{i}", f"Genotype {i}?", ["Aa Bb", "aa bb", "AA BB", "zz zz"], "zz zz")
             for i in range(20)]
    report = stomp(_mc_pod(tmp_path, items))
    assert finding(report, "S5")["level"] == "pass", (
        "three options folding to one is notation, not a duplicated option")


def test_s5_treats_spacing_only_differences_as_duplicates(tmp_path):
    """`Increase     Increase` against `Increase Increase` is one answer twice,
    and MMLU ships exactly that (high_school_macroeconomics)."""
    items = [_mc(f"i{i}", f"Effect {i}?",
                 ["Increase     Increase", "Increase Increase", "Decrease", "No change"],
                 "Decrease")
             for i in range(20)]
    report = stomp(_mc_pod(tmp_path, items))
    assert finding(report, "S5")["level"] == "fail"


# --- P2's null: a raw count of negative discriminations is not a finding -------


def test_p2_null_holds_both_margins_fixed():
    """The null must preserve every model's score AND every item's difficulty.

    Getting this wrong is not a rounding error. A null that destroys item
    difficulty expected 65 negative discriminations on a real GSM8K fleet where
    the honest answer was 31, which hides five inverted keys; a null that
    destroys fleet skill expected 114, which hides everything.
    """
    from dinostomp.psychometrics import common_items, negative_rpb_null

    matrix = {f"m{k}": {f"i{j}": int((j * 7 + k * 3) % 5 > k % 3) for j in range(40)}
              for k in range(6)}
    items = common_items(matrix)
    row_totals = {m: sum(matrix[m][i] for i in items) for m in matrix}
    col_totals = {i: sum(matrix[m][i] for m in matrix) for i in items}

    # the sampler is internal, so assert the invariant it must not break:
    # a null built by swapping checkerboards cannot move a margin, so the
    # count it returns must be reproducible and bounded by the item count.
    a = negative_rpb_null(matrix, -0.05, 60)
    b = negative_rpb_null(matrix, -0.05, 60)
    assert a == b, "a lint that returns a different verdict on a second run is not a lint"
    assert 0 <= a <= len(items)
    assert sum(row_totals.values()) == sum(col_totals.values())


def test_p2_stays_quiet_when_the_count_is_what_chance_produces(tmp_path):
    """Real GSM8K: 31 observed against 31 expected. No finding."""
    from dinostomp.psychometrics import negative_rpb_null

    # a fleet with real skill spread and no planted key errors
    matrix = {f"m{k}": {f"i{j}": int(((j * 13 + k * 29) % 100) / 100 < 0.4 + 0.1 * k)
                        for j in range(60)} for k in range(5)}
    observed = None
    from dinostomp.psychometrics import point_biserials
    rpb = point_biserials(matrix)
    observed = sum(1 for v in rpb.values() if v is not None and v <= -0.05)
    null_95 = negative_rpb_null(matrix, -0.05, 80)
    assert observed <= null_95, (
        f"an unplanted fleet produced {observed} negative discriminations against a "
        f"null of {null_95}; the null is too tight and P2 will manufacture findings")


def test_p2_says_out_loud_when_it_has_no_power(tmp_path):
    """P2 is ONE-SIDED and its pass message has to admit it.

    Measured power at 200 items with 10% of keys inverted: 0/5 detections at
    six examinees, 5/5 at forty, no false alarms at any size. A quiet P2 on a
    four-model fleet is not a clean answer key, and a report that let it read
    that way would be the most flattering possible failure.
    """
    report = stomp(write_eval(tmp_path, arith_items(), models=FLEET))
    p2 = finding(report, "P2")
    assert p2["level"] in ("pass", "skip", "n/a")
    if p2["level"] == "pass":
        assert "NOT evidence of a clean answer key" in p2["detail"]
        assert p2["evidence"]["underpowered"] is True
        assert p2["evidence"]["n_examinees"] < 12


# --- S2's numeric exemption: narrow, not total --------------------------------


def test_s2_catches_a_disclosed_numeric_answer(tmp_path):
    """The blanket numeric exemption made S2 blind to every numeric-answer
    dataset. An adversarial pod ending every question "(It is 21.)" scored 0 of
    24 leaks (D-037)."""
    items = [{"id": f"d{i}", "input": f"What is {i} + {i + 1}? (It is {2 * i + 1}.)",
              "target": str(2 * i + 1)} for i in range(10, 34)]
    report = stomp(write_eval(tmp_path, items))
    assert finding(report, "S2")["level"] == "fail"


def test_s2_still_ignores_a_number_stated_as_a_premise(tmp_path):
    """The negative test, and the reason the exemption exists at all.

    GSM8K is full of quantities that collide with answers: "15 litres of
    pineapple drink", answer 15. Twenty-seven of those were called leaks before
    the exemption was added, and narrowing it must not bring them back.
    """
    items = [{"id": f"p{i}", "input": f"Sally bought {i} litres of juice and drank some. "
                                      f"How many litres did she buy?", "target": str(i)}
             for i in range(10, 34)]
    report = stomp(write_eval(tmp_path, items))
    assert finding(report, "S2")["level"] == "pass", finding(report, "S2")["detail"]


def test_s2_numeric_disclosure_respects_digit_boundaries():
    """`210` must not satisfy a search for a disclosed `21`."""
    from dinostomp.lint import _norm, _numeric_disclosed

    assert _numeric_disclosed(_norm("the answer is 21"), "21")
    assert not _numeric_disclosed(_norm("the answer is 210"), "21")
    assert not _numeric_disclosed(_norm("she bought 21 apples; how many?"), "21")
