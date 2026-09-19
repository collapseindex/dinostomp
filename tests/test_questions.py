"""`dinostomp jev`: a Jev question file tested like an if-statement.

A fake decisions provider stands in for the network. Each test plants one
property (lopsided examples, a flip under rewording, a confidently wrong
example, a model update between runs) and asserts the report names it.
"""
import json
from argparse import Namespace

import pytest

from dinostomp import questions
from dinostomp.providers import Completion
from dinostomp.questions import (QuestionFileError, compare, load_question, previous_result,
                                 render, run_question, save_result, summarize, verdict)


class FakeJev:
    """p(yes) from a function of the state; the model name is settable so a
    'model update' between runs can be planted."""
    provider_name = "typesafe"

    def __init__(self, p_yes, model="jev-1.13.0", choice=None):
        self.p_yes, self.model_reported, self.choice = p_yes, model, choice
        self.calls = []

    def complete(self, item, seed, params):
        self.calls.append((item["input"], params))
        if params.get("question") == "noul":
            p = self.p_yes(item["input"])
            dist = {"yes": p, "no": 1 - p}
        else:
            dist = self.choice(item["input"], item["choices"])
        return Completion(text=max(dist, key=dist.get), finish_reason="stop", input_tokens=10,
                          output_tokens=1, model_reported=self.model_reported,
                          trajectory=[{"tool": "decisions", "args": {},
                                       "result": json.dumps({"distribution": dist}), "ok": True}])


def write(tmp_path, body: str, name="q.jev.yaml"):
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


URGENT = ["payouts failing", "checkout down", "charged twice", "account hijacked", "api 401",
          "locked out", "duplicate shipments", "wrong bank details", "export stuck", "data leak"]
CALM = ["thanks", "theme color", "nice feature", "csv someday", "holiday hours",
        "old invoices", "invite teammate", "nonprofit discount", "small font", "update logo"]


def urgency_file(tmp_path, extra="", yes=URGENT, no=CALM):
    lines = ["question:", "  type: noul", '  instructions: "Does this need a human today?"',
             "  criteria:", '    true: "broken now"', '    false: "can wait"', extra, "examples:"]
    lines += [f'  - {{state: "{s}", expect: yes}}' for s in yes]
    lines += [f'  - {{state: "{s}", expect: no}}' for s in no]
    return write(tmp_path, "\n".join(lines) + "\n")


def honest(state):
    s = state.strip().strip("`").strip()
    s = s.replace(" I hope this helps, and thank you for your patience!", "").strip()
    if s == "":
        return 0.2
    return 0.95 if s in URGENT else 0.05


# --- the file ----------------------------------------------------------------


def test_bare_yes_and_no_are_labels_and_criteria_keys_stay_words(tmp_path):
    q = load_question(urgency_file(tmp_path))
    assert {e["expect"] for e in q.examples} == {"yes", "no"}      # YAML read them as booleans
    assert q.criteria == {"true": "broken now", "false": "can wait"}
    assert q.labels == ["yes", "no"] and q.model == "jev-latest"


@pytest.mark.parametrize("body, field", [
    ("question: {type: vibes, instructions: x}\nexamples: [{state: a, expect: yes}, {state: b, expect: no}]",
     "question.type"),
    ("question: {type: noul}\nexamples: [{state: a, expect: yes}, {state: b, expect: no}]",
     "question.instructions"),
    ("question: {type: noul, instructions: x}\nexamples: [{state: a, expect: maybe}, {state: b, expect: no}]",
     "examples[0].expect"),
    ("question: {type: noul, instructions: x}\nexamples: [{state: a, expect: yes}]", "examples:"),
    ("question: {type: choice, instructions: x, criteria: {a: A}}\nexamples: [{state: a, expect: a}, {state: b, expect: a}]",
     "question.criteria"),
    ("question: {type: noul, instructions: x}\nrewording: [shouting]\nexamples: [{state: a, expect: yes}, {state: b, expect: no}]",
     "rewording"),
])
def test_a_malformed_file_is_refused_naming_the_field(tmp_path, body, field):
    with pytest.raises(QuestionFileError, match=field.replace("[", r"\[").replace("]", r"\]")):
        load_question(write(tmp_path, body))


def test_an_oversized_state_is_refused_before_any_call(tmp_path):
    body = ("question: {type: noul, instructions: x}\nexamples:\n"
            f"  - {{state: \"{'a' * (questions.MAX_STATE_CHARS + 1)}\", expect: yes}}\n"
            "  - {state: b, expect: no}\n")
    with pytest.raises(QuestionFileError, match=r"examples\[0\]\.state"):
        load_question(write(tmp_path, body))


# --- the report ----------------------------------------------------------------


def test_an_honest_question_is_ready(tmp_path):
    q = load_question(urgency_file(tmp_path))
    fake = FakeJev(honest)
    r = run_question(q, provider_factory=lambda p, m: fake)
    s = summarize(r)
    assert s["accuracy"] == 1.0 and s["flips"] == 0 and s["n"] == 20
    assert s["blank"] == {"answer": "no", "p": 0.8, "accuracy_if_always": 0.5}
    assert s["cut"]["at_0.50"] == 1.0
    ok, failures, advice = verdict(q, s)
    assert ok and not failures and not advice
    # every example, one blank, then 20 sampled x 3 rewordings
    assert len(fake.calls) == 20 + 1 + 20 * 3
    assert fake.calls[20][0] == "", "the blank-input call sends an empty state"
    assert fake.calls[0][1]["criteria"] == {"true": "broken now", "false": "can wait"}
    assert "ready" in render(r, s, None, None)


def test_lopsided_examples_are_named_even_at_high_accuracy(tmp_path):
    q = load_question(urgency_file(tmp_path, yes=URGENT[:2], no=CALM + [f"calm {i}" for i in range(8)]))
    s = summarize(run_question(q, rewording=False, provider_factory=lambda p, m: FakeJev(honest)))
    assert s["accuracy"] == 1.0 and s["blank"]["accuracy_if_always"] == 0.9
    _, _, advice = verdict(q, s)
    assert any("scores 90%" in a for a in advice), advice


def test_a_flip_under_rewording_fails_a_zero_flip_requirement(tmp_path):
    def fence_sensitive(state):
        return 0.9 if state.startswith("```") else honest(state)
    q = load_question(urgency_file(tmp_path, extra="require: {flips: 0}"))
    r = run_question(q, provider_factory=lambda p, m: FakeJev(fence_sensitive))
    s = summarize(r)
    assert s["flips"] == 10 and all(f.startswith("formatting on example") for f in r.flips)
    ok, failures, _ = verdict(q, s)
    assert not ok and "10 rewording flip(s), 0 allowed" in failures[0]


def test_sure_and_wrong_examples_are_listed_first(tmp_path):
    def overconfident_on_one(state):
        return 0.98 if state == "small font" else honest(state)
    q = load_question(urgency_file(tmp_path))
    r = run_question(q, rewording=False, provider_factory=lambda p, m: FakeJev(overconfident_on_one))
    out = render(r, summarize(r), None, None)
    assert "wrong (1 of 1 while sure" in out and "yes at 0.98, expected no: 'small font'" in out


def test_unsure_misses_and_close_calls_are_listed_too(tmp_path):
    def edgy(state):
        return {"small font": 0.62, "payouts failing": 0.58, "checkout down": 0.7}.get(state, honest(state))
    q = load_question(urgency_file(tmp_path))
    r = run_question(q, rewording=False, provider_factory=lambda p, m: FakeJev(edgy))
    out = render(r, summarize(r), None, None)
    assert "wrong (0 of 1 while sure" in out and "yes at 0.62, expected no: 'small font'" in out
    close = out.split("close calls")[1]
    assert close.index("payouts failing") < close.index("checkout down"), "closest call first"


def test_the_best_cut_is_reported_only_when_it_beats_one_half(tmp_path):
    def shifted(state):                     # everything urgent sits at 0.45: the 0.5 cut misses them all
        return 0.45 if state in URGENT else 0.10 if state else 0.2
    q = load_question(urgency_file(tmp_path))
    r = run_question(q, rewording=False, provider_factory=lambda p, m: FakeJev(shifted))
    s = summarize(r)
    assert s["cut"]["at_0.50"] == 0.5 and s["cut"]["at_best"] == 1.0 and 0.10 < s["cut"]["best"] <= 0.45
    assert "best cut" in render(r, s, None, None)


def test_a_model_update_between_runs_is_one_printed_line(tmp_path):
    q = load_question(urgency_file(tmp_path))
    r1 = run_question(q, rewording=False, provider_factory=lambda p, m: FakeJev(honest))
    first = save_result(r1, summarize(r1))

    def drifted(state):
        return 0.4 if state in ("payouts failing", "checkout down") else honest(state)
    r2 = run_question(q, rewording=False, provider_factory=lambda p, m: FakeJev(drifted, model="jev-1.14.0"))
    s2 = summarize(r2)
    prev = previous_result(q)
    assert prev is not None and prev["model_reported"] == "jev-1.13.0"
    line = compare(prev, r2, s2)
    assert line.endswith("jev-1.13.0 -> jev-1.14.0): accuracy 100% -> 90%, 2 answer(s) changed")
    assert first.parent.name == "jev" and first.parent.parent.name == "data"
    assert first.name.endswith("_jev_q_jev-1.13.0_n20.json")


def test_an_edited_question_is_not_compared_with_the_old_one(tmp_path):
    q = load_question(urgency_file(tmp_path))
    r = run_question(q, rewording=False, provider_factory=lambda p, m: FakeJev(honest))
    save_result(r, summarize(r))
    edited = load_question(urgency_file(tmp_path, yes=URGENT[:-1]))
    assert previous_result(edited) is None


def test_a_choice_question(tmp_path):
    body = ("question:\n  type: choice\n  instructions: Which team?\n  criteria:\n"
            "    billing: money\n    engineering: bugs\n    sales: pricing\nexamples:\n"
            "  - {state: refund please, expect: billing}\n  - {state: app crashes, expect: engineering}\n"
            "  - {state: enterprise quote, expect: sales}\n")
    q = load_question(write(tmp_path, body))
    route = {"refund please": "billing", "app crashes": "engineering", "enterprise quote": "billing"}

    def choose(state, choices):
        top = route.get(state.strip(), "sales")
        return {c: (0.9 if c == top else 0.05) for c in choices}
    r = run_question(q, rewording=False, provider_factory=lambda p, m: FakeJev(None, choice=choose))
    s = summarize(r)
    assert s["correct"] == 2 and "cut" not in s
    assert "wrong (1 of 1 while sure" in render(r, s, None, None)


def test_the_command_exits_one_on_a_failed_requirement_and_two_on_a_bad_file(tmp_path, monkeypatch, capsys):
    path = urgency_file(tmp_path, extra="require: {accuracy: 0.99}")
    monkeypatch.setattr(questions, "make_provider",
                        lambda p, m: FakeJev(lambda s: 0.98 if s == "small font" else honest(s)))
    args = Namespace(file=str(path), model=None, provider="typesafe", no_rewording=True, no_save=True)
    assert questions.cmd_jev(args) == 1
    assert "FAIL  accuracy 95% is under the required 99%" in capsys.readouterr().out
    bad = write(tmp_path, "question: nope\n", "bad.jev.yaml")
    assert questions.cmd_jev(Namespace(file=str(bad), model=None, provider="typesafe",
                                       no_rewording=True, no_save=True)) == 2


def test_a_saved_result_is_lf_on_every_platform(tmp_path):
    q = load_question(urgency_file(tmp_path))
    r = run_question(q, rewording=False, provider_factory=lambda p, m: FakeJev(honest))
    assert b"\r\n" not in save_result(r, summarize(r)).read_bytes()
