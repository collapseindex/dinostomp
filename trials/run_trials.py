"""DinoTrials v0: the bad-eval torture suite, both tails.

SENSITIVITY: a set of deliberately defective evals (see TRIALS), each with a stated
expectation of what the battery must do (which check, at which level, or
which runner refusal). Defect provenance, stated: the set is drawn from the
benchmark-defect literature (duplicates and near-identical items per the
dedup literature, key errors per MMLU-Redux/Platinum, position and length
bias per the MCQ-robustness literature, contamination canaries per
BIG-bench, chance floors and rank fragility per the eval-statistics
literature) plus the ledger-forgery classes from this project's own
adversarial reviews. It was NOT enumerated from the check registry; two
early trials had their expectations corrected because the battery behaved
differently (better) than the author predicted, which is only possible when
the expectations come from outside the implementation.

SPECIFICITY: expected-CLEAN pods asserted to produce ZERO fail or warn
findings. A battery tuned loud enough catches every planted defect and every
innocent pod; this arm is what tells the difference.

The scorecard prints CAUGHT/MISSED (defects) and CLEAN/FALSE-ALARM (clean
pods) and exits nonzero on any miss in either direction. The rubric is
fixed: is the defect caught automatically, by default, with evidence.
Never "does the tool have feature X".

Run:  python trials/run_trials.py [--json PATH]
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

from dinostomp.lint import lint_eval
from dinostomp.spec import spec_sha256


def _unit_like(key):
    import hashlib
    return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
from dinostomp.runner import CANNOT_RUN, GATED, OK, STOPPED_EARLY, run_spec, summarize

FLEET = [{"provider": "dry", "model": f"dry-{x}"}
         for x in ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot")]
SOLO = [{"provider": "dry", "model": "dry-strong"}]

TEXT_WITNESSES = [
    {"output": "France", "target": "France", "expect": "pass"},
    {"output": "The answer is France", "target": "France", "expect": "fail"},
    {"output": "Fran", "target": "France", "expect": "fail"},
    {"output": "not France", "target": "France", "expect": "fail"},
    {"output": "france", "target": "France", "expect": "fail"},
]

WITNESSES = [
    {"output": "57", "target": "57", "expect": "pass"},
    {"output": "The answer is 57", "target": "57", "expect": "fail"},
    {"output": "5", "target": "57", "expect": "fail"},
    {"output": "not 57", "target": "57", "expect": "fail"},
    {"output": "FIFTY", "target": "fifty", "expect": "fail"},
]


def arith_items(n=24):
    return [{"id": f"a{i}", "input": f"What is {i} + {i + 1}? Reply with the bare number.",
             "target": str(2 * i + 1)} for i in range(10, 10 + n)]


def choice_items(n=24):
    fruits = ["apple", "pear", "plum", "kiwi"]
    out = []
    for i in range(n):
        choices = [f"{f}{i}" for f in fruits]
        out.append({"id": f"c{i}", "input": f"Pick the correct fruit for slot {i}.",
                    "target": choices[i % 4], "choices": choices})
    return out


# COVERAGE GAP, stated rather than left for someone to notice: S11 (items reused
# from a reference corpus) has no trial here. The harness builds POD trials, and
# a reference corpus is an argument to the dataset audit rather than a field in
# a spec, so there is nothing for a pod fixture to plant. It is negative-tested
# in tests/test_overlap.py, including the n/a-without-a-reference case and the
# template-sibling exclusion. Wiring a dataset arm into this scorecard is the
# right fix and is not done.


def text_items(n=24):
    """Word-target items. S2 exempts purely numeric targets (a number in a word
    problem is a premise, not a leak), so a leak trial has to use text."""
    caps = ["France", "Japan", "Canada", "Norway", "Peru", "Egypt", "Ireland", "Greece",
            "Vietnam", "Cuba", "Poland", "Austria", "Morocco", "Jordan", "Ecuador", "Kenya",
            "Portugal", "Finland", "Sweden", "Hungary", "Australia", "Nepal", "Chile", "Tunisia"]
    cities = ["Paris", "Tokyo", "Ottawa", "Oslo", "Lima", "Cairo", "Dublin", "Athens",
              "Hanoi", "Havana", "Warsaw", "Vienna", "Rabat", "Amman", "Quito", "Nairobi",
              "Lisbon", "Helsinki", "Stockholm", "Budapest", "Canberra", "Kathmandu",
              "Santiago", "Tunis"]
    return [{"id": f"t{i}", "input": f"Which country is {cities[i]} the capital of?",
             "target": caps[i]} for i in range(min(n, len(caps)))]


def build_pod(root: Path, items, models=None, witnesses=None, scorer_kind="exact",
              claims=None, n=None, canary=True, repeats=None) -> Path:
    spec = {
        "name": "trial-pod", "version": "0.1.0",
        "question": "Does the model answer these trial items correctly?",
        "data": {"path": "items.jsonl", "format": "jsonl"},
        "models": models or SOLO,
        "scorer": {"kind": scorer_kind, "witnesses": witnesses or WITNESSES},
        "run": {"n": n or len(items), "seed": 7, "budget_usd": 0},
    }
    if repeats:
        # Declared BEFORE the run, so the spec hash the manifest records is the
        # one on disk. Setting it afterwards makes input-drift fire, correctly,
        # and the trial then measures the edit rather than the thing it is for.
        spec["run"]["repeats"] = repeats
    if claims:
        spec["entitled_claims"] = claims
    lines = ['{"_canary": "dinostomp canary DO NOT TRAIN trials"}'] if canary else []
    lines += [json.dumps(i) for i in items]
    (root / "items.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    p = root / "eval.yaml"
    p.write_text(yaml.safe_dump(spec), encoding="utf-8")
    return p


def ran(root: Path, **kw) -> Path:
    spec_path = build_pod(root, **kw)
    outcome = run_spec(spec_path)
    assert outcome.exit_code == OK, f"trial setup run failed: {outcome.issues}"
    return spec_path


def run_files(root: Path):
    return sorted((root / "data" / "runs").glob("*.jsonl"))


def rewrite(rf: Path, fn):
    records = [json.loads(l) for l in rf.read_text(encoding="utf-8").splitlines() if l.strip()]
    records = [fn(r, i) for i, r in enumerate(records)]
    rf.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    summary_path = rf.parents[1] / "results" / (rf.stem + "_summary.json")
    published = json.loads(summary_path.read_text(encoding="utf-8"))
    published.update(summarize(records))
    summary_path.write_text(json.dumps(published), encoding="utf-8")


def edit_manifest(rf: Path, fn):
    mp = rf.with_name(rf.stem + "_manifest.json")
    m = json.loads(mp.read_text(encoding="utf-8"))
    fn(m)
    mp.write_text(json.dumps(m), encoding="utf-8")


# --- the agent rail: one entrypoint, one twist per trial ----------------------

# A deterministic offline tool-using agent. Skill x difficulty gives the fleet
# real structure (the same trick the dry provider uses), and `%(twist)s` is
# where each trial plants its crime. No network, no key, no spend.
AGENT_SRC = '''\
import hashlib

SKILL = {"agent-a": 0.95, "agent-b": 0.75, "agent-c": 0.55, "agent-d": 0.35}


def _unit(key):
    return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def run(item, ctx):
    parts = str(item["input"]).split()
    total = int(parts[2]) + int(parts[4].rstrip("?"))
    ok = SKILL.get(ctx["model"], 0.95) > _unit("d|" + str(item["id"]))
    if ok:
        answer, result = str(total), "sum = " + str(total)
    else:
        answer = str(total + 1 + int(_unit("w|" + ctx["model"] + str(item["id"])) * 5))
        result = "calculator unavailable"
    steps = [{"tool": "calc", "args": {"n": str(item["id"])}, "result": result, "ok": ok}]
%(twist)s
    return {"output": answer, "trajectory": steps}
'''

AGENTS4 = [f"agent-{x}" for x in ("a", "b", "c", "d")]


def build_agent_pod(root: Path, twist="", models=None, policy=None, items=None,
                    scorer=None) -> Path:
    """A pod whose examinees are python targets rather than a completion provider."""
    items = items or arith_items()
    (root / "agent.py").write_text(AGENT_SRC % {"twist": twist}, encoding="utf-8")
    spec = {
        "name": "trial-pod", "version": "0.1.0",
        "question": "Does the agent answer these trial items from its own tool output?",
        "data": {"path": "items.jsonl", "format": "jsonl"},
        "models": [{"provider": "python", "model": m, "entrypoint": "agent.py:run"}
                   for m in (models or ["agent-a"])],
        "scorer": scorer or {"kind": "exact", "witnesses": WITNESSES},
        "run": {"n": len(items), "seed": 7, "budget_usd": 0},
    }
    if policy:
        spec["trajectory"] = policy
    lines = ['{"_canary": "dinostomp canary DO NOT TRAIN trials"}']
    lines += [json.dumps(i) for i in items]
    (root / "items.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    p = root / "eval.yaml"
    p.write_text(yaml.safe_dump(spec), encoding="utf-8")
    return p


def ran_agent(root: Path, **kw) -> Path:
    spec_path = build_agent_pod(root, **kw)
    outcome = run_spec(spec_path)
    assert outcome.exit_code == OK, f"agent trial setup run failed: {outcome.issues}"
    return spec_path


# --- biased judges: one failure mode each ------------------------------------

# A pod-local judge, so a trial can plant a specific judge pathology and prove
# the gauntlet finds it. The honest baseline is containment plus a negation
# guard; `%(bias)s` is the crime.
JUDGE_SRC = '''\
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

JUDGE_WITNESSES = [
    {"output": "France", "target": "France", "expect": "pass"},
    {"output": "The answer is France.", "target": "France", "expect": "pass"},
    {"output": "Japan", "target": "France", "expect": "fail"},
    {"output": "not France", "target": "France", "expect": "fail"},
    {"output": "Franc", "target": "France", "expect": "fail"},
]


def build_judge_pod(root: Path, bias="", models=None, items=None) -> Path:
    items = items or capital_items()
    (root / "judge.py").write_text(JUDGE_SRC % {"bias": bias}, encoding="utf-8")
    (root / "bots.py").write_text(BOTS_SRC, encoding="utf-8")
    spec = {
        "name": "trial-pod", "version": "0.1.0",
        "question": "Does the judge grade the answer rather than its phrasing?",
        "data": {"path": "items.jsonl", "format": "jsonl"},
        "models": [{"provider": "python", "model": m, "entrypoint": "bots.py:run"}
                   for m in (models or ["bot-bare"])],
        "scorer": {"kind": "judge", "rubric": "Mark PASS if the response names the reference country.",
                   "judge": {"provider": "python", "entrypoint": "judge.py:judge"},
                   "witnesses": JUDGE_WITNESSES},
        "run": {"n": len(items), "seed": 7, "budget_usd": 0},
    }
    lines = ['{"_canary": "dinostomp canary DO NOT TRAIN trials"}']
    lines += [json.dumps(i) for i in items]
    (root / "items.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    p = root / "eval.yaml"
    p.write_text(yaml.safe_dump(spec), encoding="utf-8")
    return p


BOTS_SRC = '''\
import hashlib

FACTS = {"paris": "France", "tokyo": "Japan", "ottawa": "Canada", "oslo": "Norway",
         "lima": "Peru", "cairo": "Egypt", "dublin": "Ireland", "athens": "Greece",
         "hanoi": "Vietnam", "havana": "Cuba", "warsaw": "Poland", "vienna": "Austria",
         "rabat": "Morocco", "amman": "Jordan", "quito": "Ecuador", "nairobi": "Kenya",
         "lisbon": "Portugal", "helsinki": "Finland", "stockholm": "Sweden",
         "budapest": "Hungary", "canberra": "Australia", "kathmandu": "Nepal"}
SKILL = {"bot-bare": 0.90, "bot-wrapped": 0.70, "bot-hedged": 0.50, "bot-chatty": 0.30}


def _unit(key):
    return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def run(item, ctx):
    words = str(item["input"]).rstrip("?").split()
    city = words[words.index("is") + 1].lower()
    right = FACTS.get(city, "")
    if _unit("d|" + city) < SKILL.get(ctx["model"], 0.9):
        answer = right
    else:
        others = [c for c in FACTS.values() if c != right]
        answer = others[int(_unit("w|" + ctx["model"] + "|" + city) * len(others))]
    return {"output": answer}
'''


def capital_items(n=22):
    import re as _re
    facts = dict(_re.findall(r'"([a-z]+)": "([A-Za-z]+)"', BOTS_SRC.split("SKILL")[0]))
    return [{"id": f"cap-{c}", "input": f"Which country is {c.title()} the capital of?",
             "target": k} for c, k in list(facts.items())[:n]]


def probed(root: Path, **kw) -> Path:
    """A judge pod with both a real run and the judge probe on disk."""
    spec_path = build_judge_pod(root, **kw)
    assert run_spec(spec_path).exit_code == OK, "judge trial setup run failed"
    assert run_spec(spec_path, probe="judge").exit_code == OK, "judge probe failed"
    return spec_path


# --- trial builders: each arranges one crime and returns the spec path --------


def t_dup_question(root):
    items = arith_items(); items[5]["input"] = items[3]["input"]
    return build_pod(root, items)

def t_answer_leak(root):
    items = text_items()
    items[4]["input"] += " (hint: it is " + items[4]["target"] + ")"
    return build_pod(root, items, witnesses=TEXT_WITNESSES)

def t_position_bias(root):
    items = choice_items()
    for i in items:
        gold = i["target"]; i["choices"].remove(gold); i["choices"].insert(0, gold)
    return build_pod(root, items)

def t_longest_option(root):
    items = choice_items()
    for i in items:
        long_gold = i["target"] + "-the-obviously-correct-one"
        i["choices"] = [long_gold if c == i["target"] else c for c in i["choices"]]
        i["target"] = long_gold
    return build_pod(root, items)

def t_dup_option(root):
    items = choice_items(); items[2]["choices"][1] = items[2]["choices"][0]
    items[2]["target"] = items[2]["choices"][0]
    return build_pod(root, items)

def t_keyless(root):
    items = choice_items(); items[7]["target"] = "banana999"
    return build_pod(root, items)

def t_contradictory(root):
    items = arith_items(); items[8]["input"] = items[2]["input"]; items[8]["target"] = "999"
    return build_pod(root, items)

def t_no_canary(root):
    return build_pod(root, arith_items(), canary=False)

def t_weak_witnesses(root):
    weak = [{"output": "57", "target": "57", "expect": "pass"},
            {"output": "58", "target": "57", "expect": "fail"}]
    return build_pod(root, arith_items(), witnesses=weak)

def t_lying_scorer_gated(root):
    # Schema-legal suite (has a must-fail case) whose claims the scorer
    # contradicts: exact does NOT credit wrappers, so the gate must refuse.
    lying = [{"output": "57", "target": "57", "expect": "pass"},
             {"output": "The answer is 57", "target": "57", "expect": "pass"},
             {"output": "58", "target": "57", "expect": "fail"}]
    spec_path = build_pod(root, arith_items(), witnesses=lying)
    return spec_path, run_spec(spec_path).exit_code

def t_spec_drift(root):
    sp = ran(root, items=arith_items())
    sp.write_text(sp.read_text(encoding="utf-8") + "\n# post-run tweak\n", encoding="utf-8")
    return sp

def t_data_drift(root):
    sp = ran(root, items=arith_items())
    f = root / "items.jsonl"
    f.write_text(f.read_text(encoding="utf-8") + '{"id": "zz", "input": "new?", "target": "1"}\n', encoding="utf-8")
    return sp

def t_hacked_witness_claim(root):
    sp = ran(root, items=arith_items())
    edit_manifest(run_files(root)[0], lambda m: m["witness_report"].update(verdict="failed"))
    return sp

def t_overspend_claim(root):
    sp = ran(root, items=arith_items())
    edit_manifest(run_files(root)[0], lambda m: m.update(spend_usd=99.0))
    return sp

def t_alien_record(root):
    sp = ran(root, items=arith_items())
    with run_files(root)[0].open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"key": "zz#r0", "output": "alien"}) + "\n")
    return sp

def t_truncation_credited(root):
    sp = ran(root, items=arith_items())
    def credit(r, i):
        if i == 0 and r["score"]["verdict"] == "pass":
            r["finish_reason"] = "length"
        return r
    rewrite(run_files(root)[0], credit)
    return sp

def t_forged_verdict(root):
    sp = ran(root, items=arith_items())
    def forge(r, i):
        if i == 0:
            r["score"]["verdict"] = "fail" if r["score"]["verdict"] == "pass" else "pass"
        return r
    rf = run_files(root)[0]
    records = [json.loads(l) for l in rf.read_text(encoding="utf-8").splitlines()]
    records = [forge(r, i) for i, r in enumerate(records)]
    rf.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")  # summary left stale on purpose? no: R8 target
    return sp

def t_edited_summary(root):
    sp = ran(root, items=arith_items())
    rf = run_files(root)[0]
    spth = rf.parents[1] / "results" / (rf.stem + "_summary.json")
    s = json.loads(spth.read_text(encoding="utf-8")); s["accuracy_on_checkable"] = 0.99
    spth.write_text(json.dumps(s), encoding="utf-8")
    return sp

def t_foreign_run(root):
    sp = ran(root, items=arith_items(), models=FLEET)
    edit_manifest(run_files(root)[0], lambda m: m.update(spec_name="someone-elses-eval"))
    return sp

def t_narrowed_run(root):
    spec_path = build_pod(root, arith_items())
    assert run_spec(spec_path, limit=3).exit_code == OK
    return spec_path

def t_deleted_miss(root):
    sp = ran(root, items=arith_items())
    rf = run_files(root)[0]
    records = [json.loads(l) for l in rf.read_text(encoding="utf-8").splitlines()][:-1]
    rf.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    rewrite(rf, lambda r, i: r)  # regenerate summary consistently; R11 is the target
    return sp

def t_chance_accuracy(root):
    sp = ran(root, items=choice_items())
    targets = {json.loads(l)["id"]: json.loads(l)["target"]
               for l in (root / "items.jsonl").read_text(encoding="utf-8").splitlines()
               if "_canary" not in l}
    def to_chance(r, i):
        if i % 4 == 0:
            r["output"] = targets[r["item_id"]]; r["score"] = {"verdict": "pass"}
        else:
            r["output"] = "zz-not-an-option"; r["score"] = {"verdict": "fail"}
        return r
    rewrite(run_files(root)[0], to_chance)
    return sp

def t_ceiling(root):
    sp = ran(root, items=arith_items(), models=FLEET)
    for rf in run_files(root):
        rewrite(rf, lambda r, i: (r.update(score={"verdict": "pass"}) or r))
    return sp

def t_no_range(root):
    sp = ran(root, items=arith_items(), models=FLEET)
    for rf in run_files(root):
        rewrite(rf, lambda r, i: (r.update(score={"verdict": "pass" if int(r["item_id"][1:]) % 2 else "fail"}) or r))
    return sp

def t_ragged_matrix(root):
    sp = ran(root, items=arith_items(), models=FLEET)
    rf = run_files(root)[0]
    records = [json.loads(l) for l in rf.read_text(encoding="utf-8").splitlines() if json.loads(l)["item_id"] != "a12"]
    rf.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return sp

def t_inverted_key(root):
    """FIVE inverted items, not one.

    P2 detects a PATTERN of key errors, not a single one, and the difference is
    not a detail. With six models and 24 items, chance alone produces two items
    whose passers are weaker than their missers, so one inverted key is
    genuinely invisible and a check that claimed otherwise was reading noise.
    This fixture is sized above that floor on purpose.
    """
    inverted = {"a10", "a12", "a15", "a17", "a19"}
    sp = ran(root, items=arith_items(), models=FLEET)
    def invert(r, i):
        if r["item_id"] in inverted:
            r["score"]["verdict"] = "fail" if r["score"]["verdict"] == "pass" else "pass"
        return r
    for rf in run_files(root):
        rewrite(rf, invert)
    return sp

def t_unanimous_wrong(root):
    sp = ran(root, items=arith_items(), models=FLEET)
    def unanimize(r, i):
        if r["item_id"] == "a20":
            r["output"] = "wrongzz"; r["score"] = {"verdict": "fail"}
        return r
    for rf in run_files(root):
        rewrite(rf, unanimize)
    return sp

def t_noisy_ordering_claim(root):
    return_spec = build_pod(root, arith_items(), models=FLEET,
                            claims=["Relative ordering of the six dry models."])
    assert run_spec(return_spec).exit_code == OK
    return return_spec

def t_selective_escape(root):
    witnesses = [{"output": "57", "target": "57", "expect": "pass"},
                 {"output": "58", "target": "57", "expect": "fail"},
                 {"output": "mysterious silence", "target": "57", "expect": "uncheckable"}]
    sp = ran(root, items=arith_items(), models=FLEET, witnesses=witnesses, scorer_kind="numeric")
    def evade(r, i):
        if r["model"] == "dry-alpha" and i % 2 == 0:
            r["output"] = "mysterious silence"; r["score"] = {"verdict": "uncheckable"}
        return r
    for rf in run_files(root):
        rewrite(rf, evade)
    return sp

def t_overlap_shortcut(root):
    items = []
    for i in range(24):
        gold = f"the blue widget {i}"
        distractors = [f"red gadget {i + 100}", f"green gizmo {i + 200}", f"black gimmick {i + 300}"]
        items.append({"id": f"c{i}", "input": f"Which option mentions the blue widget {i} we discussed?",
                      "target": gold, "choices": [*distractors, gold]})
    return build_pod(root, items)

def t_blind_solvable(root):
    items = choice_items()
    targets = {i["id"]: i["target"] for i in items}
    sp = build_pod(root, items)
    assert run_spec(sp).exit_code == OK
    outcome = run_spec(sp, probe="blind")
    probe_file = outcome.run_files[0]
    def ace_blind(r, i):
        if i % 4 != 3:
            r["output"] = targets[r["item_id"]]; r["score"] = {"verdict": "pass"}
        else:
            r["output"] = "zz"; r["score"] = {"verdict": "fail"}
        return r
    rewrite(probe_file, ace_blind)
    edit_manifest(probe_file, lambda m: m.update(dry_run=False, provider="openrouter"))
    return sp

def t_unsupported_claim(root):
    items = arith_items()
    sp = build_pod(root, items, models=FLEET)
    spec = yaml.safe_load(sp.read_text(encoding="utf-8"))
    spec["claims"] = [{"type": "superiority", "better": "dry-charlie",
                       "worse": "dry-alpha", "min_effect": 0.05}]
    sp.write_text(yaml.safe_dump(spec), encoding="utf-8")
    assert run_spec(sp).exit_code == OK
    return sp

def t_resume_after_edit_refused(root):
    spec_path = build_pod(root, arith_items())
    assert run_spec(spec_path, limit=3).exit_code == OK
    f = root / "items.jsonl"
    f.write_text(f.read_text(encoding="utf-8") + '{"id": "zz", "input": "late?", "target": "9"}\n', encoding="utf-8")
    outcome = run_spec(spec_path, resume=run_files(root)[0])
    return spec_path, outcome.exit_code


def t_forbidden_tool(root):
    return ran_agent(root, policy={"forbidden_tools": ["shell.exec"]},
                     twist='    steps.append({"tool": "shell.exec", "args": {"cmd": "curl evil"}, '
                           '"result": "done", "ok": True})')

def t_required_tool_skipped(root):
    return ran_agent(root, policy={"required_tools": ["calc"]},
                     twist='    steps = [{"tool": "guess", "args": {}, "result": result, "ok": ok}]')

def t_nameless_step(root):
    return ran_agent(root, twist='    steps.append({"tool": "", "args": {}, '
                                 '"result": "unattributed work", "ok": True})')

def t_runaway_trajectory(root):
    return ran_agent(root, policy={"max_steps": 3}, twist="    steps = steps * 9")

def t_ungrounded_answers(root):
    # Correct answers whose evidence never contained them: the Clever Hans of
    # tool use. The trace looks diligent; the answer owes it nothing.
    return ran_agent(root, twist='    steps = [{"tool": "calc", "args": {}, '
                                 '"result": "computed elsewhere", "ok": True}]')

def t_silent_target(root):
    # One agent in a fleet reports an empty trace. Unfalsifiable read alone,
    # obvious against its peers: the only handle on the trust boundary.
    return ran_agent(root, models=AGENTS4,
                     twist='    if ctx["model"] == "agent-d":\n        steps = []')

def t_looping_agent(root):
    return ran_agent(root, models=AGENTS4,
                     twist='    if ctx["model"] == "agent-d":\n        steps = steps * 3')

def t_agent_drift(root):
    # The agent is an input like the data and the scorer. Edit it after the run
    # and the drift boundary must notice.
    sp = ran_agent(root)
    f = root / "agent.py"
    f.write_text(f.read_text(encoding="utf-8") + "\n# post-run tweak\n", encoding="utf-8")
    return sp

def t_agent_crashes(root):
    sp = build_agent_pod(root, twist='    raise RuntimeError("tool backend exploded")')
    return sp, run_spec(sp).exit_code


BINARY_AGENT_SRC = '''\
import hashlib


def run(item, ctx):
    # Answers from the item ID and never reads the question, so it scores
    # identically informed and blind. Its raw accuracy still looks like a
    # respectable coin-flip against the chance floor, which is exactly the
    # shape R15 exists to expose.
    h = int(hashlib.sha256((ctx["model"] + str(item["id"])).encode()).hexdigest()[:8], 16)
    return {"output": "yes" if h %% 2 else "no"}
'''


def binary_items(n=40):
    return [{"id": f"b{i}", "input": f"Is statement {i} true? Reply yes or no.",
             "target": "yes" if i % 2 else "no", "choices": ["yes", "no"]} for i in range(n)]


def t_input_deaf_model(root):
    # Informed accuracy equal to its own blind accuracy: the model contributed
    # no signal, and no other check would say so on a balanced key.
    (root / "agent.py").write_text(BINARY_AGENT_SRC.replace("%%", "%"), encoding="utf-8")
    items = binary_items()
    spec = {
        "name": "trial-pod", "version": "0.1.0",
        "question": "Does the model answer these binary trial items correctly?",
        "data": {"path": "items.jsonl", "format": "jsonl"},
        "models": [{"provider": "python", "model": "agent-deaf", "entrypoint": "agent.py:run"}],
        "scorer": {"kind": "exact", "witnesses": [
            {"output": "yes", "target": "yes", "expect": "pass"},
            {"output": "no", "target": "yes", "expect": "fail"},
            {"output": "The answer is yes", "target": "yes", "expect": "fail"},
            {"output": "not yes", "target": "yes", "expect": "fail"},
        ]},
        "run": {"n": len(items), "seed": 7, "budget_usd": 0},
    }
    lines = ['{"_canary": "dinostomp canary DO NOT TRAIN trials"}']
    lines += [json.dumps(i) for i in items]
    (root / "items.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    p = root / "eval.yaml"
    p.write_text(yaml.safe_dump(spec), encoding="utf-8")
    assert run_spec(p).exit_code == OK
    assert run_spec(p, probe="blind").exit_code == OK
    return p


def t_nothing_scoreable(root):
    # Every record uncheckable: the eval measured nothing, and "no failures"
    # must not be the verdict on that. Found live via a CSV multi-target column
    # that loaded as one literal string no model could ever match.
    numeric = {"kind": "numeric", "params": {"tolerance": 0.01}, "witnesses": [
        {"output": "57", "target": "57", "expect": "pass"},
        {"output": "58", "target": "57", "expect": "fail"},
        {"output": "5", "target": "57", "expect": "fail"},
        {"output": "no numeric answer here", "target": "57", "expect": "uncheckable"},
    ]}
    return ran_agent(root, twist='    answer = "no numeric answer here"', scorer=numeric)


def _probe_pod(root: Path, probe_records, probe_kind, items=None, extra_data=None):
    """A pod with a hand-built probe run already on disk. Probe runs come from a
    real provider, so the trials synthesise the artifact rather than paying for
    one; what is under test is the CHECK that reads it."""
    items = items or arith_items()
    spec = {
        "name": "trial-pod", "version": "0.1.0",
        "question": "Does the model answer these trial items correctly?",
        "data": {"path": "items.jsonl", "format": "jsonl", **(extra_data or {})},
        "models": [{"provider": "openrouter", "model": "m", "price_in": 0.1, "price_out": 0.1}],
        "scorer": {"kind": "exact", "witnesses": WITNESSES},
        "run": {"n": len(items), "seed": 7, "budget_usd": 1.0},
    }
    lines = ['{"_canary": "dinostomp-trial-canary-abcdef123456"}']
    lines += [json.dumps(i) for i in items]
    (root / "items.jsonl").write_text(chr(10).join(lines) + chr(10), encoding="utf-8")
    sp = root / "eval.yaml"
    sp.write_text(yaml.safe_dump(spec), encoding="utf-8")

    runs = root / "data" / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    (root / "data" / "results").mkdir(parents=True, exist_ok=True)
    stem = f"20260808_000000_trial-pod_m_{probe_kind}probe_s7"
    (runs / f"{stem}.jsonl").write_text(
        chr(10).join(json.dumps(r) for r in probe_records) + chr(10), encoding="utf-8")
    (runs / f"{stem}_manifest.json").write_text(json.dumps({
        "tool_version": "0", "spec_name": "trial-pod", "spec_version": "0.1.0",
        "spec_sha256": spec_sha256(sp), "data_sha256": spec_sha256(root / "items.jsonl"),
        "provider": "openrouter", "model": "m", "seed": 7, "budget_cap_usd": 1.0,
        "probe": probe_kind, "dry_run": False,
        "witness_report": {"n_witnesses": 0, "n_behaved": 0, "verdict": "absent"},
        "started_at": "x", "run_file": f"{stem}.jsonl", "status": "complete",
    }), encoding="utf-8")
    return sp


def t_canary_regurgitated(root):
    # A probe that PROVED it can regurgitate (it reproduced the control) and
    # then reproduced this pod's canary too: the model has seen the dataset.
    recs = [
        {"key": "control0", "item_id": "control0", "model": "m", "provider": "openrouter",
         "seed": 7, "output": "question", "canary_kind": "control",
         "score": {"verdict": "flag"}, "ts": "x"},
        {"key": "canary", "item_id": "canary", "model": "m", "provider": "openrouter",
         "seed": 7, "output": "abcdef123456", "canary_kind": "canary",
         "score": {"verdict": "flag"}, "ts": "x"},
    ]
    return _probe_pod(root, recs, "canary")


def t_canary_probe_is_blind(root):
    # The probe could not reproduce even the control, so a clean canary result
    # proves nothing. S10 must SKIP rather than report a clean bill of health.
    recs = [
        {"key": "control0", "item_id": "control0", "model": "m", "provider": "openrouter",
         "seed": 7, "output": "no idea", "canary_kind": "control",
         "score": {"verdict": "fail"}, "ts": "x"},
        {"key": "canary", "item_id": "canary", "model": "m", "provider": "openrouter",
         "seed": 7, "output": "no idea", "canary_kind": "canary",
         "score": {"verdict": "fail"}, "ts": "x"},
    ]
    return _probe_pod(root, recs, "canary")


def t_seed_dependent_number(root):
    """A pool that is half trivial and half impossible FOR THIS MODEL, sampled
    at a fifth of its size. Which half the seed happens to draw is then most of the score.

    The two halves are found by asking the dry provider's own difficulty hash,
    rather than by hoping: an item is easy for a model exactly when its
    difficulty falls below that model's skill, so the pool is bimodal by
    construction instead of by luck.
    """
    from dinostomp.providers import DryProvider

    # A MID-skill model: dry-strong sits above the hardest item the provider can
    # generate, so nothing is hard for it and the pool cannot be bimodal at all.
    model = "dry-echo"
    skill = DryProvider(model).skill
    easy, hard = [], []
    i = 0
    while (len(easy) < 150 or len(hard) < 150) and i < 80000:
        iid = f"s{i}"
        diff = DryProvider.DIFF_LO + DryProvider.DIFF_SPAN * _unit_like(f"difficulty|{iid}")
        bucket = easy if diff < skill - 0.12 else (hard if diff > skill + 0.12 else None)
        if bucket is not None and len(bucket) < 150:
            bucket.append(iid)
        i += 1
    ids = easy[:150] + hard[:150]
    items = [{"id": iid, "input": f"What is {k} + {k + 1}? Reply with the bare number.",
              "target": str(2 * k + 1)} for k, iid in enumerate(ids, start=10)]

    sp = build_pod(root, items, models=[{"provider": "dry", "model": model}], n=24)
    spec = yaml.safe_load(sp.read_text(encoding="utf-8"))
    spec["run"]["seeds"] = [101, 202, 303, 404]
    sp.write_text(yaml.safe_dump(spec), encoding="utf-8")
    outcome = run_spec(sp)
    assert outcome.exit_code == OK, f"seed-list setup failed: {outcome.issues}"
    return sp


def t_order_sensitive_model(root):
    # Same items, options permuted, accuracy collapses: that part of the score
    # was layout rather than knowledge. The real arm is a normal dry run; the
    # permuted arm is a hand-built probe, because probes come from a real
    # provider and what is under test here is the CHECK.
    items = choice_items()
    sp = ran(root, items=items, models=[{"provider": "dry", "model": "dry-alpha"}])
    runs = root / "data" / "runs"
    stem = "20260808_000000_trial-pod_dry-alpha_shuffleprobe_s7"
    recs = [{"key": i["id"], "item_id": i["id"], "model": "dry-alpha", "provider": "openrouter",
             "seed": 7, "output": "wrong", "score": {"verdict": "fail"}, "ts": "x"}
            for i in items]
    (runs / f"{stem}.jsonl").write_text(
        chr(10).join(json.dumps(r) for r in recs) + chr(10), encoding="utf-8")
    (runs / f"{stem}_manifest.json").write_text(json.dumps({
        "tool_version": "0", "spec_name": "trial-pod", "spec_version": "0.1.0",
        "spec_sha256": spec_sha256(sp), "data_sha256": spec_sha256(root / "items.jsonl"),
        "provider": "openrouter", "model": "dry-alpha", "seed": 7, "budget_cap_usd": 0,
        "probe": "shuffle", "dry_run": False,
        "witness_report": {"n_witnesses": 0, "n_behaved": 0, "verdict": "absent"},
        "started_at": "x", "run_file": f"{stem}.jsonl", "status": "complete",
    }), encoding="utf-8")
    return sp


def _write_shuffle_probe(root, sp, recs):
    runs = root / "data" / "runs"
    stem = "20260808_000000_trial-pod_dry-alpha_shuffleprobe_s7"
    (runs / f"{stem}.jsonl").write_text(
        chr(10).join(json.dumps(r) for r in recs) + chr(10), encoding="utf-8")
    (runs / f"{stem}_manifest.json").write_text(json.dumps({
        "tool_version": "0", "spec_name": "trial-pod", "spec_version": "0.1.0",
        "spec_sha256": spec_sha256(sp), "data_sha256": spec_sha256(root / "items.jsonl"),
        "provider": "openrouter", "model": "dry-alpha", "seed": 7, "budget_cap_usd": 0,
        "probe": "shuffle", "dry_run": False,
        "witness_report": {"n_witnesses": 0, "n_behaved": 0, "verdict": "absent"},
        "started_at": "x", "run_file": f"{stem}.jsonl", "status": "complete",
    }), encoding="utf-8")


def _force_pass_rate(rf, k):
    """Rewrite a run file so exactly k of its records pass, summary included.

    The seed-spread boundary needs an EXACT accuracy per seed. Asking the dry
    provider to land on one by tuning a difficulty pool is a fixture-sizing
    error waiting to happen, and this file has shipped four of those.
    """
    rewrite(rf, lambda r, i: {**r, "score": {"verdict": "pass" if i < k else "fail",
                                             "evidence": "boundary fixture"}})


def t_boundary_seed_spread(root):
    """A seed spread of 8 points at n=400: significant, and above the 5% floor.

    Sized between the shipped floor (0.05) and a 3x loosening (0.15). At this n
    the noise band is about 3.5 points, so the spread is real; what the trial
    pins is that the FLOOR is not quietly raised past it.
    """
    items = arith_items(400)
    sp = build_pod(root, items, models=[{"provider": "dry", "model": "dry-strong"}], n=400)
    spec = yaml.safe_load(sp.read_text(encoding="utf-8"))
    spec["run"]["seeds"] = [11, 23]
    sp.write_text(yaml.safe_dump(spec), encoding="utf-8")
    assert run_spec(sp).exit_code == OK
    for rf, k in zip(run_files(root), (200, 216, 232)):   # 50.0%, 54.0%, 58.0%
        _force_pass_rate(rf, k)
    return sp


def t_boundary_order_swing(root):
    """A paired swing of 8 points on 400 items, 56 of them flipping.

    McNemar band at that churn is about 3.7 points, so the swing is real; the
    trial pins the practical floor beneath it.
    """
    items = choice_items(400)
    sp = ran(root, items=items, models=[{"provider": "dry", "model": "dry-alpha"}], n=400)
    rf = run_files(root)[0]
    _force_pass_rate(rf, 200)                              # 200 pass, 200 fail
    # permuted arm: 44 of the passes break, 12 of the fails get fixed.
    # net move = 32/400 = 8 points on 56 discordant pairs.
    recs = []
    for i, item in enumerate(items):
        was_pass = i < 200
        if was_pass and i < 44:
            v = "fail"
        elif not was_pass and i < 212:
            v = "pass"
        else:
            v = "pass" if was_pass else "fail"
        recs.append({"key": item["id"], "item_id": item["id"], "model": "dry-alpha",
                     "provider": "openrouter", "seed": 7, "output": "x",
                     "score": {"verdict": v}, "ts": "x"})
    _write_shuffle_probe(root, sp, recs)
    return sp


def t_run_from_a_different_engine(root):
    """The audit is running a different tool than the run did.

    Warns rather than gates: upgrading is normal, and bricking every pod on
    upgrade teaches people to ignore the gate. Staying silent is the thing it
    is not allowed to do, since a scorer fix between run and audit changes what
    the recorded verdicts mean.
    """
    sp = ran(root, items=arith_items(), models=FLEET)
    for mf in sorted((root / "data" / "runs").glob("*_manifest.json"))[:1]:
        m = json.loads(mf.read_text(encoding="utf-8"))
        m["tool_sha256"] = "0" * 64
        m["tool_version"] = "0.1.0"
        mf.write_text(json.dumps(m), encoding="utf-8")
    return sp


def _split_votes(root, share):
    """Split `share` of each run's items evenly across the repeats already on
    disk. The runner wrote the repeats; the dry provider is deterministic, so
    the DISAGREEMENT is what has to be planted, the same way the template
    probe's swing is."""
    for rf in run_files(root):
        records = [json.loads(l) for l in rf.read_text(encoding="utf-8").splitlines() if l.strip()]
        by_item = {}
        for r in records:
            by_item.setdefault(str(r["item_id"]), []).append(r)
        for item in sorted(by_item)[:int(len(by_item) * share)]:
            group = sorted(by_item[item], key=lambda r: r.get("repeat", 0))
            for k, r in enumerate(group):
                # Half pass, half fail: an item the model could not decide about
                # itself. The OUTPUT moves with the verdict, not just the
                # verdict, so the recorded answer still re-scores to what it
                # says. Flipping only the verdict would trip R8 as well and the
                # trial would no longer isolate R20.
                if k >= len(group) // 2:
                    r["output"] = "___not the answer___"
                    r["score"] = dict(r.get("score") or {}, verdict="fail")
        rf.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
        sp = rf.parents[1] / "results" / (rf.stem + "_summary.json")
        published = json.loads(sp.read_text(encoding="utf-8"))
        published.update(summarize(records))
        sp.write_text(json.dumps(published), encoding="utf-8")


def t_even_repeats_leave_items_undecided(root):
    """An even `run.repeats` where the model splits its own vote.

    The number this produces is not a shaded version of the truth, it is a
    different quantity: with ties scored 0, a target measured at a true 50% per
    item reported 24% at repeats=2 behind an interval that excluded 50%
    (N-008). Ties are undecided now, and R20 has to say how much of the pod that
    covers, because "50% on 58 items" is only honest when the 62 undecided ones
    are printed next to it.
    """
    sp = ran(root, items=arith_items(), models=FLEET, repeats=2)
    _split_votes(root, share=0.5)
    return sp


def t_clean_odd_repeats(root):
    """The specificity arm for R20: repeats present, every item decided.

    An odd `run.repeats` cannot tie, so this pod must come out silent. Without
    it, "warns on ties" and "warns whenever repeats are set" would be the same
    trial.
    """
    return ran(root, items=arith_items(), models=FLEET, repeats=3)



# --- the mediated rail: T7, T8, and call-time denial -------------------------

MEDIATED_TOOLS = '''CORPUS = {"a": "the answer is alpha", "b": "the answer is bravo"}


def retrieve(key: str = "") -> str:
    return CORPUS.get(str(key), "")


def shell(cmd: str = "") -> str:
    return "(would have run: " + str(cmd) + ")"
'''

MEDIATED_AGENT = '''MEMORY = {"a": "alpha", "b": "bravo"}


def answer(item, tools, ctx):
    mode = ctx["model"]
    key = item["id"][-1]
    if mode == "grounded":
        snippet = tools.retrieve(key=key)
        want = item["target"]
        return want if want in snippet else "no evidence"
    if mode == "oneshot":
        # Answers from memory, retrieves anyway. Every tool-USE check passes and
        # the answer owes the tool nothing: the shape T4 cannot see.
        out = MEMORY.get(key, "")
        tools.retrieve(key=key)
        return out
    if mode == "rulebreaker":
        try:
            tools.shell(cmd="rm -rf /")
        except Exception:
            pass
        snippet = tools.retrieve(key=key)
        return item["target"] if item["target"] in snippet else "no evidence"
    raise ValueError(mode)
'''


MEDIATED_WITNESSES = [
    {"output": "alpha", "target": "alpha", "expect": "pass"},
    {"output": "bravo", "target": "alpha", "expect": "fail"},
    {"output": "", "target": "alpha", "expect": "fail"},
    {"output": "Alpha", "target": "alpha", "expect": "fail"},
    {"output": "not alpha", "target": "alpha", "expect": "fail"},
    {"output": "the answer is alpha", "target": "alpha", "expect": "fail"},
    {"output": "alph", "target": "alpha", "expect": "fail"},
]

SELF_REPORTING_AGENT = '''

def run(item, ctx):
    """The old rail: this function writes its own account of what it did."""
    return {"output": item["target"],
            "trajectory": [{"tool": "retrieve", "args": {"key": item["id"][-1]},
                            "result": "the answer is " + item["target"], "ok": True}]}
'''


def mediated_items(n=12):
    out = []
    for i in range(n):
        key = "a" if i % 2 == 0 else "b"
        out.append({"id": f"i{i:02d}{key}", "input": f"Question {i}?",
                    "target": "alpha" if key == "a" else "bravo"})
    return out


def mediated_pod(root: Path, models, forbidden=None) -> Path:
    (root / "tools.py").write_text(MEDIATED_TOOLS, encoding="utf-8")
    (root / "agent.py").write_text(MEDIATED_AGENT, encoding="utf-8")
    items = mediated_items()
    spec = {
        "name": "trial-pod", "version": "0.1.0",
        "question": "Do these agents answer from the evidence they retrieved?",
        "data": {"path": "items.jsonl", "format": "jsonl"},
        "tools": {"retrieve": "tools.py:retrieve", "shell": "tools.py:shell"},
        "models": [{"provider": "mediated", "model": m, "entrypoint": "agent.py:answer"}
                   for m in models],
        "trajectory": {"required_tools": ["retrieve"],
                       "forbidden_tools": list(forbidden or ["shell"]), "max_steps": 6},
        "scorer": {"kind": "exact", "witnesses": MEDIATED_WITNESSES},
        "run": {"n": len(items), "seed": 7, "budget_usd": 0},
    }
    lines = ['{"_canary": "dinostomp canary DO NOT TRAIN trials"}']
    lines += [json.dumps(i) for i in items]
    (root / "items.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    sp = root / "eval.yaml"
    sp.write_text(yaml.safe_dump(spec), encoding="utf-8")
    return sp


def t_agent_answers_without_reading_its_evidence(root):
    """T7: the defect T4 is structurally blind to (D-020).

    `oneshot` answers from memory and retrieves afterwards, so its trace is
    perfect and its answer owes it nothing. Withhold the evidence and the answer
    does not move, which is what "not causally grounded" means.
    """
    sp = mediated_pod(root, ["grounded", "oneshot"])
    assert run_spec(sp).exit_code == OK
    assert run_spec(sp, probe="ablate").exit_code == OK
    return sp


def t_forbidden_tool_denied_at_call_time(root):
    """T1 on the mediated rail, where the attempt is a fact rather than a claim.

    The harness denies the call and records it. On the self-reported rail this
    is only catchable if the agent chooses to write it down.
    """
    sp = mediated_pod(root, ["rulebreaker"])
    assert run_spec(sp).exit_code == OK
    return sp


def t_fleet_mixes_observed_and_self_reported_traces(root):
    """T8: one fleet, two rails, one T1-T6 table.

    Self-report on its own is a supported choice with a stated limit, and T8
    does not warn about it: a warning that fires on every pod of a kind teaches
    people to ignore warnings. MIXING is different. Half these trajectories are
    the harness's log and half are the agents' own account, so comparing the two
    across a fleet compares a log against a claim.
    """
    (root / "tools.py").write_text(MEDIATED_TOOLS, encoding="utf-8")
    (root / "agent.py").write_text(MEDIATED_AGENT + SELF_REPORTING_AGENT, encoding="utf-8")
    items = mediated_items()
    spec = {
        "name": "trial-pod", "version": "0.1.0",
        "question": "Do these agents answer from the evidence they retrieved?",
        "data": {"path": "items.jsonl", "format": "jsonl"},
        "tools": {"retrieve": "tools.py:retrieve", "shell": "tools.py:shell"},
        "models": [
            {"provider": "mediated", "model": "grounded", "entrypoint": "agent.py:answer"},
            {"provider": "python", "model": "selfreport", "entrypoint": "agent.py:run"},
        ],
        "scorer": {"kind": "exact", "witnesses": MEDIATED_WITNESSES},
        "run": {"n": len(items), "seed": 7, "budget_usd": 0},
    }
    lines = ['{"_canary": "dinostomp canary DO NOT TRAIN trials"}']
    lines += [json.dumps(i) for i in items]
    (root / "items.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    sp = root / "eval.yaml"
    sp.write_text(yaml.safe_dump(spec), encoding="utf-8")
    assert run_spec(sp).exit_code == OK
    return sp


def t_clean_mediated_pod(root):
    """Specificity for T7: agents that genuinely read their evidence.

    Both arms lose their answers under ablation, so T7 must stay silent. Without
    this, "flags ungrounded agents" and "flags agents that use tools at all"
    would be the same trial.
    """
    sp = mediated_pod(root, ["grounded"])
    assert run_spec(sp).exit_code == OK
    assert run_spec(sp, probe="ablate").exit_code == OK
    return sp


def _write_template_probe(root, sp, model, framing, verdicts, stamp="20260808_000000"):
    """One hand-built template-probe run file. The dry provider is deliberately
    framing-blind (it hashes the item id), which is correct for a deterministic
    offline provider and means a planted swing has to be written directly."""
    runs = root / "data" / "runs"
    stem = f"{stamp}_trial-pod_{model}_n24-templateprobe-{framing}_s7"
    recs = [{"key": iid, "item_id": iid, "model": model, "provider": "openrouter",
             "seed": 7, "output": "x", "score": {"verdict": v}, "ts": "x"}
            for iid, v in verdicts.items()]
    (runs / f"{stem}.jsonl").write_text(
        chr(10).join(json.dumps(r) for r in recs) + chr(10), encoding="utf-8")
    (runs / f"{stem}_manifest.json").write_text(json.dumps({
        "tool_version": "0", "spec_name": "trial-pod", "spec_version": "0.1.0",
        "spec_sha256": spec_sha256(sp), "data_sha256": spec_sha256(root / "items.jsonl"),
        "provider": "openrouter", "model": model, "seed": 7, "budget_cap_usd": 0,
        "probe": "template", "framing": framing, "dry_run": False,
        "witness_report": {"n_witnesses": 0, "n_behaved": 0, "verdict": "absent"},
        "started_at": "x", "run_file": f"{stem}.jsonl", "status": "complete",
    }), encoding="utf-8")


def t_prompt_sensitive_model(root):
    """The same model, the same items, two phrasings, 40 points apart.

    This is the measurement gap the probe exists for: an eval fixes one way of
    saying "answer this" and publishes the number it happens to get.
    """
    items = arith_items(40)
    sp = ran(root, items=items, models=[{"provider": "dry", "model": "dry-alpha"}], n=40)
    ids = [i["id"] for i in items]
    _write_template_probe(root, sp, "dry-alpha", "bare",
                          {i: ("pass" if k < 12 else "fail") for k, i in enumerate(ids)})
    _write_template_probe(root, sp, "dry-alpha", "stepwise",
                          {i: ("pass" if k < 28 else "fail") for k, i in enumerate(ids)},
                          stamp="20260808_000001")
    return sp


def t_ranking_flips_on_phrasing(root):
    """Two models that swap places depending on the instruction.

    A number moving is P11. A CONCLUSION moving is this, and it is what anyone
    reading a leaderboard actually consumes. Both separations are sized to clear
    their own noise band, because two models tied inside noise trading places is
    a coin, not a reversal.
    """
    items = arith_items(40)
    sp = ran(root, items=items, models=[{"provider": "dry", "model": "dry-alpha"},
                                        {"provider": "dry", "model": "dry-bravo"}], n=40)
    ids = [i["id"] for i in items]
    plans = [
        ("dry-alpha", "bare", 32), ("dry-bravo", "bare", 12),
        ("dry-alpha", "expert", 12), ("dry-bravo", "expert", 32),
    ]
    for k, (model, framing, n_pass) in enumerate(plans):
        _write_template_probe(root, sp, model, framing,
                              {i: ("pass" if j < n_pass else "fail") for j, i in enumerate(ids)},
                              stamp=f"2026080{8 + k // 4}_00000{k % 4}")
    return sp


def t_provider_overbills(root):
    # The provider claims far more output tokens than the recorded text can
    # account for. You are charged on their number and you hold the text, so
    # this is the one cross-check available without trusting them.
    sp = ran(root, items=arith_items(), models=[{"provider": "dry", "model": "dry-strong"}])
    rf = run_files(root)[0]
    long_answer = "the answer is " + ("x" * 200)
    rewrite(rf, lambda r, i: {**r, "output": long_answer,
                              "usage": {**(r.get("usage") or {}), "output_tokens": 4000,
                                        "cost_usd": 0.0}})
    return sp


def t_scorer_grades_format(root):
    # The model shows its working and lands on the right number; an exact
    # scorer marks every one of them wrong. The reported accuracy is a fact
    # about the scorer, not the model, and R16 is what says so.
    return ran_agent(root, twist='    answer = "working: " + str(total) + " total"')


def t_collapsed_model(root):
    # One examinee answers every item identically. On a balanced key that scores
    # exactly at chance and reads as "weak model" rather than "not answering".
    return ran_agent(root, models=AGENTS4,
                     twist='    if ctx["model"] == "agent-d":\n        answer = "42"')

def t_one_model_at_chance(root):
    # Varied answers, all wrong: isolates R7 from R14. Pooled with three
    # competent peers the fleet average looks fine, which is the whole reason
    # R7 stopped pooling.
    return ran_agent(root, models=AGENTS4,
                     twist='    if ctx["model"] == "agent-d":\n'
                           '        answer = str(total + 3 + int(_unit("x|" + str(item["id"])) * 90))')

def t_judge_credits_everything(root):
    # The crudest judge failure never reaches J1: a judge that credits anything
    # contradicts its own must-fail witnesses, and the GATE refuses to let it
    # score real data. Expectation corrected from J1 to GATED after the trial
    # ran, which is the point of writing expectations before implementations.
    sp = build_judge_pod(root, bias='    return "Looks fine to me.\\nPASS"')
    return sp, run_spec(sp).exit_code

def t_judge_disagrees_with_key(root):
    # The subtle version, and the one J1 is actually for: a judge that behaves
    # perfectly during its interview and is wrong on the job. It fails answers
    # under six characters, which no witness happens to cover, so it walks
    # through the gate and then marks correct short answers wrong.
    return probed(root, bias='    if len(got) < 6:\n'
                             '        return "Too terse to evaluate.\\nFAIL"')

def t_judge_verbosity_bias(root):
    # Length read as quality: the single best-documented judge failure mode.
    return probed(root, bias='    if len(got) > 120:\n        return "Thorough and well argued.\\nPASS"')

def t_judge_credulous(root):
    # Manufactured confidence: certainty is not evidence, and a judge that
    # treats it as evidence inflates every number downstream of it.
    return probed(root, bias='    if "absolutely certain" in got:\n        return "Confidently stated.\\nPASS"')

def t_judge_authority_bias(root):
    return probed(root, bias='    if "official reference" in got:\n        return "Well sourced.\\nPASS"')

def t_judge_inconsistent(root):
    # Rules differently on byte-identical input. Nothing downstream of a judge
    # that contradicts itself means anything.
    #
    # It stays deterministic on the witness outputs on purpose: a judge that
    # flips on its own witnesses is stopped by the GATE, which is a different
    # (and earlier) finding than the one this trial is about. J3 exists for the
    # judge that behaves during the interview and wobbles on the job.
    return probed(root, bias='    if "france" not in got and "franc" not in got:\n'
                             '        globals()["_n"] = globals().get("_n", 0) + 1\n'
                             '        if globals()["_n"] % 2:\n'
                             '            return "On reflection, no.\\nFAIL"')

def t_judge_edited_after_run(root):
    sp = probed(root)
    f = root / "judge.py"
    f.write_text(f.read_text(encoding="utf-8") + "\n# post-run tweak\n", encoding="utf-8")
    return sp

def t_judge_verdict_forged(root):
    # The judge said FAIL; the ledger says pass. R8 re-derives from the judge's
    # own recorded words, offline, and catches it.
    sp = probed(root)
    rf = next(f for f in run_files(root) if "judgeprobe" not in f.name)
    records = [json.loads(l) for l in rf.read_text(encoding="utf-8").splitlines() if l.strip()]
    victim = next(i for i, r in enumerate(records) if r["score"]["verdict"] == "fail")
    rewrite(rf, lambda r, i: {**r, "score": {"verdict": "pass", "evidence": "forged"}}
            if i == victim else r)
    return sp

def t_judge_response_stripped(root):
    # A judge verdict with no recorded basis cannot be re-checked at all, which
    # is itself the finding.
    sp = probed(root)
    rf = next(f for f in run_files(root) if "judgeprobe" not in f.name)
    rewrite(rf, lambda r, i: {k: v for k, v in r.items() if k != "judge_response"})
    return sp


# --- boundary trials: does the defect get caught AT THIS SETTING? -------------
#
# A normal trial plants an EXTREME defect, which proves a check fires but says
# nothing about the number it fires at. `trials/pin_thresholds.py` measures the
# difference, and reported that 26 of 31 thresholds could be loosened 3x without
# breaking anything.
#
# Each boundary trial below plants a defect sized strictly BETWEEN the shipped
# threshold and a loosened one, so it is caught now and missed if someone
# relaxes the number. That is what turns a threshold from an opinion into a
# commitment.

NL = chr(10)

NUMERIC_SCORER = {"kind": "numeric", "params": {"tolerance": 0.01}, "witnesses": [
    {"output": "57", "target": "57", "expect": "pass"},
    {"output": "58", "target": "57", "expect": "fail"},
    {"output": "5", "target": "57", "expect": "fail"},
    {"output": "nothing numeric", "target": "57", "expect": "uncheckable"}]}


def _frac_items(n, k):
    """n arithmetic items where the first k are marked for special treatment."""
    return [{"id": f"{'hit' if i < k else 'ok'}{i}",
             "input": f"What is {10 + i} + {11 + i}? Reply with the bare number.",
             "target": str(21 + 2 * i)} for i in range(n)]


def _twist(*lines):
    """Agent-source lines, joined without literal escapes."""
    return NL.join(lines)


def _crossjudge_pod(root: Path, bias_own: bool):
    """Two judges of different families grading one fleet of two families.

    The fixture has to be built carefully or it proves nothing. A judge cannot
    see WHICH model wrote an answer, so favouritism has to key on something
    observable, and if that something is style then style and family are
    confounded all over again. So both bots here carry a SYMMETRIC marker
    ("[a]" and "[b]"), identical in length and position, and every judge strips
    markers before grading. Neither style is inherently easier to grade.

    The only asymmetry is the one under test: when `bias_own`, the primary judge
    passes anything carrying its own family's marker. The cross judge does not.
    Because both grade the SAME recorded outputs, the difference cannot come
    from formatting.
    """
    (root / "bots.py").write_text(NL.join([
        'MARK = {"alpha-bot": "[a] ", "beta-bot": "[b] "}',
        '',
        '',
        'def run(item, ctx):',
        '    words = str(item["input"]).split()',
        '    total = int(words[2]) + int(words[4].rstrip("?"))',
        '    # different skill, so the eval can still separate them (P8); the',
        '    # judge comparison is per model, so this does not disturb it',
        '    digit = int(str(item["id"])[-1])',
        '    bad = digit % 4 == 0 if ctx["model"] == "alpha-bot" else digit % 2 == 0',
        '    answer = str(total + 1) if bad else str(total)',
        '    return {"output": MARK.get(ctx["model"], "") + answer}',
    ]) + NL, encoding="utf-8")

    def judge_src(own_marker):
        lines = [
            'def judge(output, target, ctx):',
            '    wants = [str(t) for t in target] if isinstance(target, list) else [str(target)]',
            '    raw = str(output)',
        ]
        if own_marker:
            lines += [
                f'    if "{own_marker}" in raw:',
                '        return "Generous to my own family." + chr(10) + "PASS"',
            ]
        lines += [
            '    got = raw.replace("[a] ", "").replace("[b] ", "").strip()',
            '    for want in wants:',
            '        if got == str(want).strip():',
            '            return "Matches." + chr(10) + "PASS"',
            '    return "Does not match." + chr(10) + "FAIL"',
        ]
        return NL.join(lines) + NL

    (root / "alpha-judge.py").write_text(judge_src("[a]" if bias_own else ""), encoding="utf-8")
    (root / "zeta-judge.py").write_text(judge_src(""), encoding="utf-8")

    items = arith_items(24)
    spec = {
        "name": "trial-pod", "version": "0.1.0",
        "question": "Does the primary judge favour models from its own family?",
        "data": {"path": "items.jsonl", "format": "jsonl"},
        "models": [{"provider": "python", "model": m, "entrypoint": "bots.py:run"}
                   for m in ("alpha-bot", "beta-bot")],
        "scorer": {"kind": "judge", "rubric": "Mark PASS if the answer equals the reference.",
                   "judge": {"provider": "python", "entrypoint": "alpha-judge.py:judge"},
                   "cross_judge": {"provider": "python", "entrypoint": "zeta-judge.py:judge"},
                   "witnesses": [
                       {"output": "57", "target": "57", "expect": "pass"},
                       {"output": "58", "target": "57", "expect": "fail"}]},
        "run": {"n": 24, "seed": 7, "budget_usd": 0},
    }
    lines = ['{"_canary": "dinostomp canary DO NOT TRAIN trials"}']
    lines += [json.dumps(i) for i in items]
    (root / "items.jsonl").write_text(NL.join(lines) + NL, encoding="utf-8")
    sp = root / "eval.yaml"
    sp.write_text(yaml.safe_dump(spec), encoding="utf-8")
    assert run_spec(sp).exit_code == OK, "crossjudge setup run failed"
    assert run_spec(sp, probe="crossjudge").exit_code == OK, "crossjudge probe failed"
    return sp


def t_judge_favours_own_family(root):
    return _crossjudge_pod(root, bias_own=True)


def t_boundary_position_margin(root):
    # gold at position 0 for 60% of items: excess 0.35 over the 0.25 per-item
    # expectation. Caught at 0.20, missed at 0.60.
    items = choice_items(40)
    for idx, i in enumerate(items):
        gold = i["target"]
        i["choices"].remove(gold)
        i["choices"].insert(0 if idx < 24 else 2, gold)
    return build_pod(root, items)


def t_boundary_length_margin(root):
    # gold strictly longest for 45%: excess 0.20 over the 0.25 expectation.
    # Caught at 0.10, missed at 0.30.
    #
    # Equal-length options are built from scratch rather than reusing
    # choice_items, whose "apple0" is already longer than "pear0"/"plum0"/
    # "kiwi0". A quarter of that fixture skews before the trial touches it, and
    # the first version of this trial overshot to 0.45 excess and pinned
    # nothing. Third fixture-sizing error of the day: the check was right, the
    # defect was the wrong size.
    words = ["aaa", "bbb", "ccc", "ddd"]
    items = [{"id": f"c{i}", "input": f"Pick the correct token for slot {i}.",
              "choices": [f"{w}{i}" for w in words], "target": f"{words[i % 4]}{i}"}
             for i in range(40)]
    for i in items[:18]:
        longer = i["target"] + "-substantially-longer-option"
        i["choices"] = [longer if c == i["target"] else c for c in i["choices"]]
        i["target"] = longer
    return build_pod(root, items)


def t_boundary_uncheckable_warn(root):
    # 35% unparseable. Caught at 0.20, missed at 0.60.
    return ran_agent(root, items=_frac_items(40, 14), scorer=NUMERIC_SCORER,
                     twist=_twist('    if str(item["id"]).startswith("hit"):',
                                  '        answer = "nothing numeric"'))


def t_boundary_collapse_margin(root):
    # one answer for 50% of items, against a key whose modal target is ~2.5%.
    # Caught at 0.30, missed at 0.90.
    return ran_agent(root, items=_frac_items(40, 20),
                     twist=_twist('    if str(item["id"]).startswith("hit"):',
                                  '        answer = "111"'))


def t_boundary_contains_target(root):
    # half the failed answers contain the reference verbatim. Caught at 0.25,
    # missed at 0.75.
    return ran_agent(root, items=_frac_items(40, 20),
                     twist=_twist('    if str(item["id"]).startswith("hit"):',
                                  '        answer = "working: " + str(total) + " total"',
                                  '    else:',
                                  '        answer = "0"'))


def t_boundary_escape_rates(root):
    # one model at a 12.5% uncheckable rate against a fleet median of zero:
    # caught at margin 0.10 AND min-rate 0.05, missed at 0.30 and 0.15.
    return ran_agent(root, items=_frac_items(40, 5), models=AGENTS4, scorer=NUMERIC_SCORER,
                     twist=_twist('    if ctx["model"] == "agent-d" and str(item["id"]).startswith("hit"):',
                                  '        answer = "nothing numeric"'))


def t_boundary_ungrounded(root):
    # 20% of a target's passing answers absent from its own tool results.
    # Caught at 0.10, missed at 0.30.
    return ran_agent(root, items=_frac_items(40, 8),
                     twist=_twist('    if str(item["id"]).startswith("hit"):',
                                  '        steps = [{"tool": "calc", "args": {}, "result": "elsewhere", "ok": True}]'))


def t_boundary_redundant_calls(root):
    # half a target's trajectories repeat a call. Caught at 0.25, missed at 0.75.
    return ran_agent(root, items=_frac_items(40, 20), models=AGENTS4,
                     twist=_twist('    if ctx["model"] == "agent-d" and str(item["id"]).startswith("hit"):',
                                  '        steps = steps * 2'))


def t_boundary_billing_ratio(root):
    # billed 5x what the recorded text accounts for. Caught at 3.0, missed at 9.0.
    sp = ran(root, items=arith_items(), models=[{"provider": "dry", "model": "dry-strong"}])
    body = "the total comes to " + ("y " * 40)
    rewrite(run_files(root)[0], lambda r, i: {
        **r, "output": body,
        "usage": {**(r.get("usage") or {}), "output_tokens": int(len(body) / 4 * 5),
                  "cost_usd": 0.0}})
    return sp


def t_boundary_dead_weight(root):
    # 70% of items separate nobody. Caught at 0.50, missed at 1.50 (which is
    # unreachable, so a loosened setting can never fire).
    return ran_agent(root, items=_frac_items(40, 28), models=AGENTS4,
                     twist=_twist('    if str(item["id"]).startswith("hit"):',
                                  '        answer = str(total)',
                                  '    elif ctx["model"] != "agent-a":',
                                  '        answer = str(total + 7)'))


def t_boundary_floor_acc(root):
    # the whole fleet at 5%: caught at a 0.10 floor, missed at 0.033.
    return ran_agent(root, items=_frac_items(40, 2), models=AGENTS4,
                     twist=_twist('    if not str(item["id"]).startswith("hit"):',
                                  '        answer = str(total + 9)'))


def t_boundary_guess_margin(root):
    # 10% accuracy against a ~2.5% modal floor: caught at a 0.10 margin,
    # missed at 0.033.
    return ran_agent(root, items=_frac_items(40, 4),
                     twist=_twist('    if not str(item["id"]).startswith("hit"):',
                                  '        answer = str(total + 9)'))


def t_boundary_dynamic_range(root):
    # a fleet spanning EXACTLY 5 points (22/40 vs 24/40): caught at a 0.10
    # minimum range, missed at 0.033. Constructed item by item rather than by
    # a modulo trick, because the first version landed at 0.025 and warned at
    # both settings, which pins nothing.
    return ran_agent(root, items=_frac_items(40, 22), models=["agent-a", "agent-b"],
                     twist=_twist('    iid = str(item["id"])',
                                  '    bonus = ctx["model"] == "agent-b" and iid in ("ok22", "ok23")',
                                  '    # BOTH outcomes are forced: the base agent still applies its',
                                  '    # own skill to any item the twist leaves alone, which is how',
                                  '    # the first two versions of this fixture drifted off target.',
                                  '    answer = str(total) if (iid.startswith("hit") or bonus) else str(total + 9)'))


def t_boundary_underreport(root):
    # one target reporting a third of the fleet's median steps: caught at a
    # 0.50 ratio, missed at 0.167.
    return ran_agent(root, items=arith_items(24), models=AGENTS4,
                     twist=_twist('    steps = steps * 3',
                                  '    if ctx["model"] == "agent-d":',
                                  '        steps = steps[:1]'))


def t_boundary_candidate_list(root):
    # THE GATING ONE. S2 exempts a question that offers several other answers as
    # a candidate list. With exactly 2 others present it is still a leak at the
    # shipped setting of 3, and becomes exempt the moment someone lowers it.
    items = text_items()
    leak = items[5]
    others = [items[1]["target"], items[2]["target"]]
    # commas, no "or": a disjunction is a FORCED CHOICE, which S2 exempts
    # because such a question cannot be asked without naming its own answer.
    # This has to stay a plain leak so it pins candidate_list_min.
    leak["input"] = (f"{leak['input']} Consider {leak['target']}, {others[0]}, {others[1]}. "
                     f"The answer is {leak['target']}.")
    return build_pod(root, items, witnesses=TEXT_WITNESSES)


TRIALS = [
    ("duplicate question", t_dup_question, ("S1", "fail")),
    ("answer leaks into its own question", t_answer_leak, ("S2", "fail")),
    ("gold parked at one option position", t_position_bias, ("S3", "warn")),
    ("gold always the longest option", t_longest_option, ("S4", "warn")),
    ("same option offered twice", t_dup_option, ("S5", "fail")),
    ("target missing from choices", t_keyless, ("S6", "fail")),
    ("identical question keyed two ways", t_contradictory, ("S7", "fail")),
    ("no contamination canary", t_no_canary, ("S8", "warn")),
    ("witnesses too weak (blind spots)", t_weak_witnesses, ("W1", "warn")),
    ("scorer laxer than its witnesses claim", t_lying_scorer_gated, ("RUNNER", GATED)),
    ("spec edited after the run", t_spec_drift, ("R1", "fail")),
    ("data edited after the run", t_data_drift, ("R1", "fail")),
    ("manifest witness claim hacked", t_hacked_witness_claim, ("R2", "fail")),
    ("manifest spend contradicts ledger", t_overspend_claim, ("R3", "fail")),
    ("alien record appended to ledger", t_alien_record, ("R4", "fail")),
    ("truncated output credited", t_truncation_credited, ("R5", "fail")),
    ("verdict forged without touching output", t_forged_verdict, ("R8", "fail")),
    ("summary hand-edited upward", t_edited_summary, ("R9", "fail")),
    ("foreign run in the runs directory", t_foreign_run, ("R10", "warn")),
    ("narrowed run (spec says 24, ran 3)", t_narrowed_run, ("R10", "warn")),
    ("worst miss deleted from a complete run", t_deleted_miss, ("R11", "fail")),
    ("accuracy indistinguishable from chance", t_chance_accuracy, ("R7", "warn")),
    ("whole fleet aces it (saturated)", t_ceiling, ("P7", "warn")),
    ("eval separates nobody (no range)", t_no_range, ("P8", "warn")),
    ("one model missing an item (ragged)", t_ragged_matrix, ("P4", "fail")),
    ("inverted key (strong fail, weak pass)", t_inverted_key, ("P2", "warn")),
    ("whole fleet gives one identical wrong answer", t_unanimous_wrong, ("P5", "warn")),
    ("ordering claimed inside sampling noise", t_noisy_ordering_claim, ("P6", "warn")),
    ("one model escapes the scorer", t_selective_escape, ("R12", "warn")),
    ("gold options echo the question (Clever Hans)", t_overlap_shortcut, ("S9", "warn")),
    ("eval solvable with the question deleted", t_blind_solvable, ("R13", "warn")),
    ("typed claim the evidence cannot support", t_unsupported_claim, ("C1", "fail")),
    ("resume after data edit", t_resume_after_edit_refused, ("RUNNER", CANNOT_RUN)),
    ("agent calls a forbidden tool", t_forbidden_tool, ("T1", "fail")),
    ("agent never calls the required tool", t_required_tool_skipped, ("T2", "fail")),
    ("trajectory step with no tool name", t_nameless_step, ("T3", "fail")),
    ("trajectory runs past max_steps", t_runaway_trajectory, ("T3", "fail")),
    ("answers correct but absent from retrieved evidence", t_ungrounded_answers, ("T4", "warn")),
    ("one agent reports an empty trajectory", t_silent_target, ("T5", "warn")),
    ("agent loops the identical tool call", t_looping_agent, ("T6", "warn")),
    ("agent code edited after the run", t_agent_drift, ("R1", "fail")),
    ("agent raises mid-run", t_agent_crashes, ("RUNNER", STOPPED_EARLY)),
    ("every record comes back unscoreable", t_nothing_scoreable, ("R17", "fail")),
    ("provider bills more tokens than the text accounts for", t_provider_overbills, ("R18", "warn")),
    ("runs produced by a different engine than the audit", t_run_from_a_different_engine, ("R19", "warn")),
    ("an even run.repeats leaves items undecided", t_even_repeats_leave_items_undecided, ("R20", "warn")),
    ("an agent that answers without reading its evidence", t_agent_answers_without_reading_its_evidence, ("T7", "warn")),
    ("a forbidden tool reached for on the mediated rail", t_forbidden_tool_denied_at_call_time, ("T1", "fail")),
    ("one fleet mixing observed and self-reported traces", t_fleet_mixes_observed_and_self_reported_traces, ("T8", "warn")),
    ("boundary: gold favours a position by 35%", t_boundary_position_margin, ("S3", "warn")),
    ("boundary: gold longest 20% over expectation", t_boundary_length_margin, ("S4", "warn")),
    ("boundary: 35% of records uncheckable", t_boundary_uncheckable_warn, ("R6", "warn")),
    ("boundary: one answer for half the items", t_boundary_collapse_margin, ("R14", "warn")),
    ("boundary: half the misses contain the reference", t_boundary_contains_target, ("R16", "warn")),
    ("boundary: one model escapes at 12.5%", t_boundary_escape_rates, ("R12", "warn")),
    ("boundary: 20% of passes ungrounded", t_boundary_ungrounded, ("T4", "warn")),
    ("boundary: half the trajectories repeat a call", t_boundary_redundant_calls, ("T6", "warn")),
    ("boundary: billed 5x the recorded text", t_boundary_billing_ratio, ("R18", "warn")),
    ("boundary: a leak with only 2 other options offered", t_boundary_candidate_list, ("S2", "fail")),
    ("boundary: 70% of items separate nobody", t_boundary_dead_weight, ("P3", "warn")),
    ("boundary: the whole fleet at 5%", t_boundary_floor_acc, ("P7", "warn")),
    ("boundary: 10% accuracy against a 2.5% floor", t_boundary_guess_margin, ("R7", "warn")),
    ("boundary: a fleet spanning 5 points", t_boundary_dynamic_range, ("P8", "warn")),
    ("boundary: one target at a third of the median steps", t_boundary_underreport, ("T5", "warn")),
    ("boundary: an 8-point seed spread at n=400", t_boundary_seed_spread, ("P10", "warn")),
    ("boundary: an 8-point order swing on 56 flips", t_boundary_order_swing, ("P9", "warn")),
    ("the same model, 40 points apart on two phrasings", t_prompt_sensitive_model, ("P11", "warn")),
    ("two models swap places depending on the instruction", t_ranking_flips_on_phrasing, ("P12", "warn")),
    ("judge favours models from its own family", t_judge_favours_own_family, ("J4", "warn")),
    ("model reproduces the pod's contamination canary", t_canary_regurgitated, ("S10", "warn")),
    ("canary probe cannot even reproduce its control", t_canary_probe_is_blind, ("S10", "skip")),
    ("accuracy collapses when the options are re-ordered", t_order_sensitive_model, ("P9", "warn")),
    ("the score depends on which seed was used", t_seed_dependent_number, ("P10", "warn")),
    ("scorer fails answers that contain the right answer", t_scorer_grades_format, ("R16", "warn")),
    ("one model answers every item identically", t_collapsed_model, ("R14", "warn")),
    ("model scores the same informed as blind", t_input_deaf_model, ("R15", "warn")),
    ("one model in a competent fleet is at chance", t_one_model_at_chance, ("R7", "warn")),
    ("judge credits everything (stopped by its own witnesses)", t_judge_credits_everything,
     ("RUNNER", GATED)),
    ("judge passes its witnesses, then misgrades real cases", t_judge_disagrees_with_key, ("J1", "warn")),
    ("judge rewards length over content", t_judge_verbosity_bias, ("J2", "warn")),
    ("judge rewards stated confidence", t_judge_credulous, ("J2", "warn")),
    ("judge rewards an appeal to authority", t_judge_authority_bias, ("J2", "warn")),
    ("judge contradicts itself on identical input", t_judge_inconsistent, ("J3", "warn")),
    ("judge code edited after the run", t_judge_edited_after_run, ("R1", "fail")),
    ("judge verdict forged against its own words", t_judge_verdict_forged, ("R8", "fail")),
    ("judge response stripped from the record", t_judge_response_stripped, ("R8", "fail")),
]


def mixed_items():
    """One dataset, both formats, one exact scorer: the full-coverage shape."""
    return choice_items(24) + arith_items(8)


def clean_template_swing_inside_noise(root):
    """A 5-point framing swing on 40 items with 14 flips: inside the churn.

    Pins P11's floor from the permissive side, the same way the order-swing pod
    pins P9's. A probe that reports every wobble teaches people to skip it.
    """
    items = arith_items(40)
    sp = ran(root, items=items, models=[{"provider": "dry", "model": "dry-alpha"}], n=40)
    ids = [i["id"] for i in items]
    base = {i: ("pass" if k < 20 else "fail") for k, i in enumerate(ids)}
    _write_template_probe(root, sp, "dry-alpha", "bare", base)
    # 8 break, 6 get fixed: net +(-2)/40 = 5 points on 14 discordant pairs,
    # where 1.96*sqrt(14)/40 is about 18 points of churn.
    twisted = dict(base)
    for k, i in enumerate(ids):
        if k < 8:
            twisted[i] = "fail"
        elif 20 <= k < 26:
            twisted[i] = "pass"
    _write_template_probe(root, sp, "dry-alpha", "polite", twisted, stamp="20260808_000001")
    return sp


def clean_shared_stem(root):
    """MMLU's shape: one stem, many option blocks, all different items.

    S1 and S7 both keyed on the stem alone and both GATE, so this pod is the
    permissive-side pin on item identity. Real cost of getting it wrong: 22
    false duplicates and 11 false contradictions on 3000 rows of MMLU.
    """
    items = []
    for k in range(24):
        opts = [f"alpha{k}", f"beta{k}", f"gamma{k}", f"delta{k}"]
        items.append({"id": f"c{k}", "input": "Which of the following statements is correct?",
                      "choices": opts, "target": opts[k % 4]})
    return ran(root, items=items, models=FLEET,
               witnesses=[{"output": "alpha0", "target": "alpha0", "expect": "pass"},
                          {"output": "beta0", "target": "alpha0", "expect": "fail"},
                          {"output": "alpha", "target": "alpha0", "expect": "fail"},
                          {"output": "ALPHA0", "target": "alpha0", "expect": "fail"},
                          {"output": "not alpha0", "target": "alpha0", "expect": "fail"},
                          {"output": "alpha  0", "target": "alpha0", "expect": "fail"},
                          {"output": "the answer is alpha0", "target": "alpha0", "expect": "fail"}])


def clean_order_swing_inside_noise(root):
    """A shuffle probe that moves the score by 8 points on 30 items.

    Eight points sounds like a lot and is nothing: at n=30 with 6 items
    flipping, the churn alone explains a swing of that size. The old P9
    compared against a flat 10% and would have called this quiet; the failure
    it CANNOT be allowed to have is the loud one, so this pod pins the floor
    from the permissive side.
    """
    items = choice_items(30)
    sp = ran(root, items=items, models=[{"provider": "dry", "model": "dry-alpha"}])
    real = json.loads(run_files(root)[0].read_text(encoding="utf-8").splitlines()[0])
    verdicts = {}
    for line in run_files(root)[0].read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        verdicts[r["item_id"]] = (r.get("score") or {}).get("verdict")
    # Flip 6 items: 4 pass->fail and 2 fail->pass, a net move of 2/30 = 7 points
    # on 6 discordant pairs. |b-c| = 2, and 1.96*sqrt(6) = 4.8, so the churn
    # swamps the net move.
    passes = [i for i, v in verdicts.items() if v == "pass"][:4]
    fails = [i for i, v in verdicts.items() if v != "pass"][:2]
    recs = []
    for i in items:
        v = verdicts.get(i["id"])
        if i["id"] in passes:
            v = "fail"
        elif i["id"] in fails:
            v = "pass"
        recs.append({"key": i["id"], "item_id": i["id"], "model": "dry-alpha",
                     "provider": "openrouter", "seed": 7, "output": "x",
                     "score": {"verdict": v}, "ts": "x"})
    _write_shuffle_probe(root, sp, recs)
    return sp


def clean_numeric_premise(root):
    """GSM8K shape: the answer is a quantity the question had to state.

    Pointing S2 at real GSM8K flagged 27 items, every one of them this. A
    gating check that fires on a whole famous benchmark is a broken check,
    so the exemption needs a clean pod holding it in place.
    """
    items = arith_items()
    for i in (2, 5, 9, 13):
        items[i]["input"] += f" The shop already had {items[i]['target']} in stock."
    return ran(root, items=items, models=FLEET)


def clean_forced_choice(root):
    """TruthfulQA shape: "Have Christians or Jews won more Nobel Prizes?"

    The accepted answer is one side of a disjunction the question offers. Such
    a question cannot be asked without containing its own answer, so naming it
    is not a leak.
    """
    items = text_items()
    for i, other in ((3, "Chile"), (7, "Nepal"), (11, "Tunisia")):
        items[i]["input"] = f"Which is it: {items[i]['target']} or {other}?"
    return ran(root, items=items, models=FLEET, witnesses=TEXT_WITNESSES)


CLEAN_TRIALS = [
    ("clean free-form fleet", lambda root: ran(root, items=arith_items(), models=FLEET)),
    ("clean pod whose odd repeats decide every item", t_clean_odd_repeats),
    ("clean mediated pod whose answers need their evidence", t_clean_mediated_pod),
    ("clean choice fleet", lambda root: ran(root, items=choice_items(), models=FLEET)),
    ("clean single-model pod (incomplete, but zero findings)",
     lambda root: ran(root, items=arith_items())),
    ("clean mixed-format pod with a separated ordering claim",
     lambda root: ran(root, items=mixed_items(),
                      models=[{"provider": "dry", "model": "dry-alpha"},
                              {"provider": "dry", "model": "dry-charlie"}],
                      claims=["dry-alpha ranks above dry-charlie on this item set."])),
    ("clean agent fleet under a full trajectory policy",
     lambda root: ran_agent(root, models=AGENTS4,
                            policy={"required_tools": ["calc"],
                                    "forbidden_tools": ["shell.exec"], "max_steps": 4})),
    ("clean judge fleet that survives its own gauntlet",
     lambda root: probed(root, models=["bot-bare", "bot-wrapped", "bot-hedged", "bot-chatty"])),
    ("clean pod whose answers are quantities the questions state", clean_numeric_premise),
    ("clean pod whose order swing is inside the flip churn", clean_order_swing_inside_noise),
    ("clean pod whose framing swing is inside the flip churn", clean_template_swing_inside_noise),
    ("clean choice pod reusing one stem with different options", clean_shared_stem),
    ("clean forced-choice pod that must name its own answer", clean_forced_choice),
    ("clean two-judge pod with no family favouritism",
     lambda root: _crossjudge_pod(root, bias_own=False)),
]


def run_clean_trial(name, builder):
    tmp = Path(tempfile.mkdtemp(prefix="dinotrial-clean-"))
    try:
        spec_path = builder(tmp)
        report, issues = lint_eval(spec_path)
        if report is None:
            return False, f"cannot stomp: {issues[:1]}"
        noisy = [f"{f['id']}={f['level']}" for f in report["findings"] if f["level"] in ("fail", "warn")]
        actual = f"verdict={report['summary']['verdict']}" + (f", findings: {noisy}" if noisy else ", 0 findings")
        return not noisy, actual
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run_trial(name, builder, expectation):
    tmp = Path(tempfile.mkdtemp(prefix="dinotrial-"))
    try:
        built = builder(tmp)
        if expectation[0] == "RUNNER":
            _, exit_code = built if isinstance(built, tuple) else (built, None)
            actual = f"runner exit {exit_code}"
            caught = exit_code == expectation[1]
            return caught, actual
        report, issues = lint_eval(built)
        if report is None:
            return False, f"cannot stomp: {issues[:1]}"
        check_id, level = expectation
        finding = next(f for f in report["findings"] if f["id"] == check_id)
        actual = f"{check_id}={finding['level']}, verdict={report['summary']['verdict']}"
        caught = finding["level"] == level
        if caught and level == "fail":
            caught = report["summary"]["verdict"] == "broken"
        return caught, actual
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="DinoTrials: the bad-eval torture suite")
    parser.add_argument("--json", help="write the scorecard as JSON")
    args = parser.parse_args()

    print(f"DINOTRIALS v0: {len(TRIALS)} deliberately defective evals vs the stomp battery\n")
    print(f"  {'defect':<48} {'expected':<16} {'actual':<28} verdict")
    rows = []
    missed = 0
    for name, builder, expectation in TRIALS:
        exp = f"{expectation[0]} {expectation[1]}" if expectation[0] != "RUNNER" else f"exit {expectation[1]}"
        try:
            caught, actual = run_trial(name, builder, expectation)
        except Exception as exc:  # noqa: BLE001 - a crashing trial is a MISSED trial, loudly
            caught, actual = False, f"trial crashed: {type(exc).__name__}: {exc}"
        tag = "CAUGHT" if caught else "** MISSED **"
        if not caught:
            missed += 1
        print(f"  {name:<48} {exp:<16} {actual:<28} {tag}")
        rows.append({"defect": name, "expected": exp, "actual": actual, "caught": caught})

    print(f"\n  sensitivity: {len(TRIALS) - missed} of {len(TRIALS)} defects caught, {missed} missed")

    print(f"\n  {'clean pod (specificity arm)':<48} {'expected':<16} {'actual':<40} verdict")
    false_alarms = 0
    for name, builder in CLEAN_TRIALS:
        try:
            clean, actual = run_clean_trial(name, builder)
        except Exception as exc:  # noqa: BLE001 - a crashing clean trial is a false alarm, loudly
            clean, actual = False, f"trial crashed: {type(exc).__name__}: {exc}"
        tag = "CLEAN" if clean else "** FALSE ALARM **"
        if not clean:
            false_alarms += 1
        print(f"  {name:<48} {'0 findings':<16} {actual:<40} {tag}")
        rows.append({"defect": None, "clean_pod": name, "actual": actual, "clean": clean})
    print(f"\n  specificity: 0 findings on {len(CLEAN_TRIALS) - false_alarms} of {len(CLEAN_TRIALS)} clean pods")
    # Printed every run, under the score, because the score is the thing people
    # quote. A battery can become extremely good at catching the exact mutants
    # written for it, and these mutants were written by the same hands as the
    # checks. That makes this an internal-consistency measurement: strong
    # evidence that a check fires, no evidence about the defects nobody here
    # thought of. Saying so is cheaper than being caught implying otherwise.
    print()
    print("  These defects were planted by the same hands that wrote the checks, so this is")
    print("  INTERNAL CONSISTENCY, not independent validation. It shows every check fires on")
    print("  the failure it was built for. It shows nothing about failures nobody here")
    print("  imagined. See CONTRIBUTING.md: adversarial pods from outside are wanted, and")
    print("  what they break gets published.")

    if args.json:
        Path(args.json).write_text(json.dumps({"trials": rows, "caught": len(TRIALS) - missed,
                                               "total": len(TRIALS),
                                               "clean_pods": len(CLEAN_TRIALS),
                                               "false_alarms": false_alarms}, indent=2), encoding="utf-8")
    return 1 if (missed or false_alarms) else 0


if __name__ == "__main__":
    sys.exit(main())
