"""W4 scorer-fit: an exact scorer keyed to sentence-length free-text answers
marks every paraphrase wrong, so a model that answered correctly in its own
words scores near zero for a formatting reason. W2 stays silent on exact scorers
by design; W4 asks the question W2 does not, whether exact is the right tool for
these answers. Diagnostic, negative-tested on the mismatch and the three shapes
where it does not apply.
"""
import yaml

from tests.test_lint import arith_items, choice_items, finding, stomp, write_eval


def _prose_items(n=24):
    return [{"id": f"p{i}", "input": f"In one sentence, explain topic number {i} to me please?",
             "target": f"topic number {i} is best understood as a fairly long explanatory sentence here"}
            for i in range(n)]


def test_w4_warns_on_an_exact_scorer_with_prose_answers(tmp_path):
    report = stomp(write_eval(tmp_path, _prose_items()))
    w4 = finding(report, "W4")
    assert w4["level"] == "warn", w4
    assert w4["evidence"]["median_answer_words"] >= 6
    # a diagnostic must never break the verdict on its own
    assert report["summary"]["verdict"] != "broken"


def test_w4_passes_on_an_exact_scorer_with_short_answers(tmp_path):
    # arith targets are single numbers: exact match is exactly the right tool.
    assert finding(stomp(write_eval(tmp_path, arith_items())), "W4")["level"] == "pass"


def test_w4_na_on_a_non_exact_scorer(tmp_path):
    # The fix path: a containment scorer on the same prose answers. W4 is about
    # the exact-match mismatch specifically, so a non-exact scorer is n/a.
    spec_path = write_eval(tmp_path, _prose_items())
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    tgt = "topic number 0 is best understood as a fairly long explanatory sentence here"
    spec["scorer"] = {"kind": "includes", "witnesses": [
        {"output": f"the answer is {tgt}", "target": tgt, "expect": "pass"},
        {"output": "nope", "target": tgt, "expect": "fail"}]}
    spec_path.write_text(yaml.safe_dump(spec), encoding="utf-8")
    assert finding(stomp(spec_path), "W4")["level"] == "n/a"


def test_w4_na_on_a_choice_pod(tmp_path):
    # An exact scorer on multiple-choice options is comparing short canonical
    # strings; there is no prose to mismatch.
    assert finding(stomp(write_eval(tmp_path, choice_items())), "W4")["level"] == "n/a"
