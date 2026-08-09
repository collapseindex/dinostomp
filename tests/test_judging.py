"""Judge gauntlet tests: who evaluated your evaluator?

Every check below is proved by breaking a judge on purpose, per the house rule.
"""

import json

import pytest
import yaml

from dinostomp.judging import PERTURBATIONS, REPEAT_TAG, DryJudge, build_cases, parse_verdict
from dinostomp.lint import lint_eval
from dinostomp.runner import GATED, OK, run_spec
from dinostomp.spec import load_spec

BOTS = '''\
FACTS = {"paris": "France", "tokyo": "Japan", "ottawa": "Canada", "oslo": "Norway",
         "lima": "Peru", "cairo": "Egypt", "dublin": "Ireland", "athens": "Greece",
         "hanoi": "Vietnam", "havana": "Cuba", "warsaw": "Poland", "vienna": "Austria",
         "rabat": "Morocco", "amman": "Jordan", "quito": "Ecuador", "nairobi": "Kenya",
         "lisbon": "Portugal", "helsinki": "Finland", "stockholm": "Sweden",
         "budapest": "Hungary", "canberra": "Australia", "kathmandu": "Nepal"}
STYLE = {"bot-bare": "{a}", "bot-wrapped": "The answer is {a}."}


def run(item, ctx):
    words = str(item["input"]).rstrip("?").split()
    city = words[words.index("is") + 1].lower()
    return {"output": STYLE.get(ctx["model"], "{a}").format(a=FACTS.get(city, "?"))}
'''

JUDGE = '''\
NEGATORS = ("not", "no", "never")


def judge(output, target, ctx):
    wants = [str(t) for t in target] if isinstance(target, list) else [str(target)]
    got = " ".join(str(output).split()).lower()
%(bias)s
    for want in wants:
        needle = " ".join(want.split()).lower()
        if needle and needle in got:
            before = got[:got.index(needle)].rstrip().split()
            if before and before[-1] in NEGATORS:
                return "Denies the reference.\\nFAIL"
            return "States the reference.\\nPASS"
    return "Does not contain the reference.\\nFAIL"
'''

WITNESSES = [
    {"output": "France", "target": "France", "expect": "pass"},
    {"output": "The answer is France.", "target": "France", "expect": "pass"},
    {"output": "Japan", "target": "France", "expect": "fail"},
    {"output": "not France", "target": "France", "expect": "fail"},
    {"output": "Franc", "target": "France", "expect": "fail"},
]


def items():
    facts = json_facts()
    return [{"id": f"cap-{c}", "input": f"Which country is {c.title()} the capital of?",
             "target": k} for c, k in facts.items()]


def json_facts():
    import re
    return dict(re.findall(r'"([a-z]+)": "([A-Za-z]+)"', BOTS.split("STYLE")[0]))


def make_pod(tmp_path, bias="", models=("bot-bare",), judge_provider="python"):
    pod = tmp_path / "pod"
    pod.mkdir(parents=True, exist_ok=True)
    (pod / "bots.py").write_text(BOTS, encoding="utf-8")
    (pod / "judge.py").write_text(JUDGE % {"bias": bias}, encoding="utf-8")
    judge_cfg = ({"provider": "python", "entrypoint": "judge.py:judge"}
                 if judge_provider == "python" else {"provider": "dry", "model": "judge-control"})
    data = items()
    spec = {
        "name": "judge-pod", "version": "0.1.0",
        "question": "Does the judge grade the answer rather than its phrasing?",
        "data": {"path": "items.jsonl", "format": "jsonl"},
        "models": [{"provider": "python", "model": m, "entrypoint": "bots.py:run"} for m in models],
        "scorer": {"kind": "judge", "rubric": "Mark PASS if the response names the reference country.",
                   "judge": judge_cfg, "witnesses": WITNESSES},
        "run": {"n": len(data), "seed": 7, "budget_usd": 0},
    }
    lines = ['{"_canary": "dinostomp canary DO NOT TRAIN judge tests"}']
    lines += [json.dumps(i) for i in data]
    (pod / "items.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (pod / "eval.yaml").write_text(yaml.safe_dump(spec), encoding="utf-8")
    return pod / "eval.yaml"


def probed(tmp_path, **kw):
    spec = make_pod(tmp_path, **kw)
    assert run_spec(spec).exit_code == OK
    assert run_spec(spec, probe="judge").exit_code == OK
    return spec


def level_of(report, cid):
    return next(f["level"] for f in report["findings"] if f["id"] == cid)


# --- verdict parsing --------------------------------------------------------


def test_verdict_parsing_takes_the_last_ruling():
    assert parse_verdict("This would FAIL if it were wrong.\nPASS").verdict == "pass"
    assert parse_verdict("Looks plausible.\nFAIL").verdict == "fail"


def test_a_judge_that_did_not_rule_is_uncheckable_not_a_fail():
    assert parse_verdict("I am not sure what to say here.").verdict == "uncheckable"
    assert parse_verdict("").verdict == "uncheckable"


def test_dry_judge_sees_through_wrappers_but_not_negation():
    j = DryJudge("judge-control")
    assert parse_verdict(j("The answer is France.", "France", {})).verdict == "pass"
    assert parse_verdict(j("not France", "France", {})).verdict == "fail"
    assert parse_verdict(j("Japan", "France", {})).verdict == "fail"


# --- the gauntlet's cases ---------------------------------------------------


def test_cases_carry_a_known_verdict_and_every_perturbation():
    cases = build_cases(items(), 3)
    names = {c.perturbation for c in cases}
    assert names == {"", REPEAT_TAG, *(p.name for p in PERTURBATIONS)}
    assert {c.polarity for c in cases} == {"correct", "corrupted"}
    # the corrupted case must be a DIFFERENT real answer, not gibberish
    corrupted = next(c for c in cases if c.polarity == "corrupted" and not c.perturbation)
    assert corrupted.output != str(corrupted.target)


def test_perturbations_preserve_the_answer_they_wrap():
    for p in PERTURBATIONS:
        assert "France" in p.apply("France"), f"{p.name} destroyed the answer it was meant to reword"


# --- J1, J2, J3, each broken on purpose -------------------------------------


def test_clean_judge_survives_its_own_gauntlet(tmp_path):
    report, _ = lint_eval(probed(tmp_path))
    assert [level_of(report, cid) for cid in ("J1", "J2", "J3")] == ["pass", "pass", "pass"]


def test_j1_catches_a_judge_that_passes_its_witnesses_then_misgrades(tmp_path):
    spec = probed(tmp_path, bias='    if len(got) < 6:\n        return "Too terse.\\nFAIL"')
    assert level_of(lint_eval(spec)[0], "J1") == "warn"


def test_j2_catches_verbosity_bias(tmp_path):
    spec = probed(tmp_path, bias='    if len(got) > 120:\n        return "Thorough.\\nPASS"')
    report, _ = lint_eval(spec)
    assert level_of(report, "J2") == "warn"
    finding = next(f for f in report["findings"] if f["id"] == "J2")
    assert "verbosity" in finding["evidence"]["biased_perturbations"]
    assert "verbosity" in finding["evidence"]["inflating"], "a fail->pass flip must be named as inflation"


def test_j2_catches_manufactured_confidence(tmp_path):
    spec = probed(tmp_path, bias='    if "absolutely certain" in got:\n        return "Confident.\\nPASS"')
    report, _ = lint_eval(spec)
    assert level_of(report, "J2") == "warn"
    assert "confidence" in next(f for f in report["findings"]
                                if f["id"] == "J2")["evidence"]["biased_perturbations"]


def test_j3_catches_a_judge_that_contradicts_itself(tmp_path):
    spec = probed(tmp_path, bias='    if "france" not in got and "franc" not in got:\n'
                                 '        globals()["_n"] = globals().get("_n", 0) + 1\n'
                                 '        if globals()["_n"] % 2:\n'
                                 '            return "On reflection, no.\\nFAIL"')
    assert level_of(lint_eval(spec)[0], "J3") == "warn"


def test_judge_checks_skip_until_the_probe_exists(tmp_path):
    spec = make_pod(tmp_path)
    assert run_spec(spec).exit_code == OK
    report, _ = lint_eval(spec)
    assert all(level_of(report, cid) == "skip" for cid in ("J1", "J2", "J3"))
    assert "--probe judge" in next(f for f in report["findings"] if f["id"] == "J1")["detail"]


def test_judge_checks_are_not_applicable_without_a_judge(tmp_path):
    spec = make_pod(tmp_path)
    obj = yaml.safe_load(spec.read_text(encoding="utf-8"))
    obj["scorer"] = {"kind": "includes", "witnesses": WITNESSES[:2] + [WITNESSES[2]]}
    spec.write_text(yaml.safe_dump(obj), encoding="utf-8")
    assert run_spec(spec).exit_code == OK
    report, _ = lint_eval(spec)
    assert all(level_of(report, cid) == "n/a" for cid in ("J1", "J2", "J3"))


# --- the judge as an input --------------------------------------------------


def test_a_judge_that_cannot_fail_is_stopped_by_the_gate(tmp_path):
    spec = make_pod(tmp_path, bias='    return "Looks fine.\\nPASS"')
    assert run_spec(spec).exit_code == GATED, "a judge contradicting its witnesses scores nothing"


def test_editing_the_judge_after_a_run_is_drift(tmp_path):
    spec = probed(tmp_path)
    judge = spec.parent / "judge.py"
    judge.write_text(judge.read_text(encoding="utf-8") + "\n# tweak\n", encoding="utf-8")
    report, _ = lint_eval(spec)
    assert level_of(report, "R1") == "fail"


def test_verdicts_re_derive_offline_from_the_judges_own_words(tmp_path):
    spec = probed(tmp_path)
    run_file = next(p for p in (spec.parent / "data" / "runs").glob("*.jsonl")
                    if "judgeprobe" not in p.name)
    records = [json.loads(l) for l in run_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert all("judge_response" in r for r in records), "a verdict with no recorded basis"
    was = records[0]["score"]["verdict"]
    records[0]["score"] = {"verdict": "fail" if was == "pass" else "pass", "evidence": "forged"}
    run_file.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    report, _ = lint_eval(spec)
    assert level_of(report, "R8") == "fail", "R8 must re-derive from the judge response, offline"


def test_a_verdict_with_no_recorded_judge_response_cannot_be_checked(tmp_path):
    spec = probed(tmp_path)
    run_file = next(p for p in (spec.parent / "data" / "runs").glob("*.jsonl")
                    if "judgeprobe" not in p.name)
    records = [json.loads(l) for l in run_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    stripped = [{k: v for k, v in r.items() if k != "judge_response"} for r in records]
    run_file.write_text("\n".join(json.dumps(r) for r in stripped) + "\n", encoding="utf-8")
    report, _ = lint_eval(spec)
    assert level_of(report, "R8") == "fail"


def test_judge_entrypoint_escaping_the_pod_is_rejected(tmp_path):
    spec = make_pod(tmp_path)
    obj = yaml.safe_load(spec.read_text(encoding="utf-8"))
    obj["scorer"]["judge"]["entrypoint"] = "../sneaky.py:judge"
    spec.write_text(yaml.safe_dump(obj), encoding="utf-8")
    _, issues = load_spec(spec)
    assert any("escapes the eval directory" in i.message for i in issues)


def test_a_judge_scorer_must_declare_a_rubric_and_a_judge(tmp_path):
    spec = make_pod(tmp_path)
    obj = yaml.safe_load(spec.read_text(encoding="utf-8"))
    del obj["scorer"]["rubric"]
    spec.write_text(yaml.safe_dump(obj), encoding="utf-8")
    _, issues = load_spec(spec)
    assert issues


def test_the_probe_summary_reports_no_accuracy(tmp_path):
    # Half a probe's cases are SUPPOSED to fail. Publishing an accuracy for it
    # would be publishing a meaningless number that looks like a result.
    spec = probed(tmp_path)
    summary = next(p for p in (spec.parent / "data" / "results").glob("*.json")
                   if "judgeprobe" in p.name)
    body = json.loads(summary.read_text(encoding="utf-8"))
    assert body["probe"] == "judge"
    assert "accuracy_on_checkable" not in body
    assert body["agreement_with_construction"] == 1.0


@pytest.mark.parametrize("field", ["judge_calls", "judge_sha256"])
def test_the_manifest_records_what_the_judge_did(tmp_path, field):
    spec = probed(tmp_path)
    manifest = next(p for p in (spec.parent / "data" / "runs").glob("*_manifest.json")
                    if "judgeprobe" not in p.name)
    assert field in json.loads(manifest.read_text(encoding="utf-8"))


def test_a_hosted_judge_pod_lints_without_an_api_key(tmp_path, monkeypatch):
    """A stranger must be able to verify a published judge-scored pod.

    Found live: building the judge's provider eagerly meant `plan`, `stomp` and
    `verify` all demanded the PUBLISHER's API key for commands that never call
    a judge, and `plan` died with a traceback. The provider is built lazily now.
    """
    for var in ("OPENROUTER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    spec = make_pod(tmp_path)
    obj = yaml.safe_load(spec.read_text(encoding="utf-8"))
    obj["scorer"]["judge"] = {"provider": "openrouter", "model": "microsoft/phi-4"}
    obj["models"] = [{"provider": "python", "model": "bot-bare", "entrypoint": "bots.py:run"}]
    spec.write_text(yaml.safe_dump(obj), encoding="utf-8")

    report, issues = lint_eval(spec)                       # must not raise, must not need a key
    assert report is not None, issues
    assert level_of(report, "R2") in ("skip", "pass", "fail")
    assert level_of(report, "W1") == "skip", "the gauntlet must not pay a hosted judge during a lint"

    from dinostomp.cli import main
    assert main(["plan", str(spec)]) == 0, "plan must never require a key or traceback"
