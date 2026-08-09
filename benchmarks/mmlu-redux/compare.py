"""Score dinostomp's data-scope battery against human annotation.

Every other finding in this repository is self-graded. This one is not:
MMLU-Redux 2.0 is 5,700 MMLU items re-read and labelled by people at Edinburgh
who had never heard of this tool. Running the battery over the same items gives
a confusion matrix against a ground truth nobody here produced.

    python benchmarks/mmlu-redux/fetch.py
    python benchmarks/mmlu-redux/compare.py

WHAT THIS CAN AND CANNOT MEASURE, stated before any number appears.

The data-scope checks read a dataset AT REST. They can see that two options are
byte-identical. They cannot see that an option is semantically equivalent to
another, that a stated answer is factually wrong, or that a question is
ambiguous, because none of that is visible without knowing the subject. Of
Redux's six error types, exactly one is within reach, and only its verbatim
subset:

    multiple_correct_answers   <- reachable, VERBATIM subset only
    no_correct_answer          <- needs the truth
    wrong_groundtruth          <- needs the truth, or a fleet (P2/P5)
    bad_question_clarity       <- needs judgement
    bad_options_clarity        <- needs judgement
    expert                     <- needs an expert

So the headline recall number is going to be bad, and publishing it without that
paragraph would be dishonest in the tool's favour. Publishing only the good
framing would be dishonest in the other direction. Both are printed.

One thing this script does NOT do is score S1 as precision. Redux's taxonomy has
no category for a DUPLICATED ITEM, so an S1 flag landing on an item Redux calls
`ok` is not a false positive; the two are answering different questions. Calling
it 0% precision would be a number that looks like a measurement and is not one.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from dinostomp.lint import _item_key, lint_dataset  # noqa: E402
from dinostomp.spec import jsonl_lines  # noqa: E402

HERE = Path(__file__).resolve().parent


def load(name):
    return [json.loads(l) for l in jsonl_lines((HERE / name).read_text(encoding="utf-8"))
            if l.strip()]


def duplicated_options(item) -> list[str]:
    ch = [str(c) for c in (item.get("choices") or [])]
    return [c for c, n in Counter(ch).items() if n > 1]


def rule_dup_questions(items):
    """S1's rule, using the battery's OWN key function.

    Returns (items in a duplicate group, number of duplicated KEYS). Re-deriving
    the key by hand got this wrong first time: S1 keys on the question PLUS its
    options, and question-only found 48 duplicated texts where the battery finds
    32. The faithfulness assertion below is what caught it.
    """
    seen = Counter(_item_key(i) for i in items)
    dup_keys = {k for k, n in seen.items() if n > 1}
    return {str(i["id"]) for i in items if _item_key(i) in dup_keys}, len(dup_keys)


def show(title, flagged, truth, universe, note=""):
    tp, fp, fn = len(flagged & truth), len(flagged - truth), len(truth - flagged)
    p = f"{tp / (tp + fp):.0%}" if tp + fp else "n/a"
    r = f"{tp / (tp + fn):.0%}" if tp + fn else "n/a"
    print(f"\n  {title}")
    print(f"    flagged and confirmed : {tp:>5}")
    print(f"    flagged, humans say ok: {fp:>5}")
    print(f"    MISSED                : {fn:>5}")
    print(f"    precision {p}   recall {r}")
    if note:
        print(f"    {note}")


def main() -> int:
    if not (HERE / "items.jsonl").is_file():
        print("run `python benchmarks/mmlu-redux/fetch.py` first", file=sys.stderr)
        return 2
    items = {str(i["id"]): i for i in load("items.jsonl") if "id" in i}
    labels = {str(x["id"]): x for x in load("labels.jsonl")}
    universe = set(items)
    print(f"{len(items)} items, {len(labels)} human labels")

    counts = Counter(labels[i]["error_type"] for i in universe)
    flawed = {i for i in universe if labels[i]["error_type"] not in ("", "ok")}
    multi = {i for i in universe if labels[i]["error_type"] == "multiple_correct_answers"}
    print(f"humans flagged {len(flawed)} of {len(universe)} ({len(flawed) / len(universe):.1%})")
    for k, v in counts.most_common():
        print(f"    {v:>5}  {k or '(blank)'}")

    report, issues, _ = lint_dataset(HERE / "items.jsonl")
    if report is None:
        print("the battery refused the file:", [i.message for i in issues][:3])
        return 1
    by_id = {f["id"]: f for f in report["findings"]}
    print(f"\nbattery verdict: {report['summary']['verdict']}")
    for cid in ("S1", "S5"):
        if cid in by_id:
            print(f"  {cid} [{by_id[cid]['level']}] {by_id[cid]['detail'][:90]}")

    dup_opt = {i for i, it in items.items() if duplicated_options(it)}
    dup_q, dup_q_keys = rule_dup_questions(list(items.values()))
    # The reproduced rules must agree with the battery's own counts, or
    # everything below is scoring something the battery does not do.
    assert f"{len(dup_opt)} item(s) offer a duplicate option" in by_id["S5"]["detail"], \
        f"reproduced S5 ({len(dup_opt)}) disagrees: {by_id['S5']['detail']}"
    assert f"{dup_q_keys} duplicated question(s)" in by_id["S1"]["detail"], \
        f"reproduced S1 ({dup_q_keys} keys) disagrees: {by_id['S1']['detail']}"
    print("  (reproduced rules agree with the battery's own counts)")

    print("\n=== S5 dup-options, scored against human annotation ===")
    show("vs multiple_correct_answers (the only reachable type)", dup_opt, multi, universe,
         "recall is over ALL such items, including the semantic ones no byte comparison can see")
    show("vs ANY human-annotated defect", dup_opt, flawed, universe,
         "the ceiling on what a data-at-rest audit can claim, stated because it is unflattering")

    # The question that decides whether a flag is a defect: is the DUPLICATED
    # option the one the answer key points at? If so the item has two correct
    # answers by construction, and no judgement is needed to say so.
    print("\n=== every S5 flag, and whether the duplicate IS the keyed answer ===")
    key_dup, opt_dup = [], []
    for iid in sorted(dup_opt):
        it, lab = items[iid], labels[iid]
        ch = [str(c) for c in it["choices"]]
        ans_i = lab.get("answer_index")
        ans = ch[ans_i] if isinstance(ans_i, int) and 0 <= ans_i < len(ch) else None
        dupes = duplicated_options(it)
        (key_dup if ans in dupes else opt_dup).append((iid, lab["error_type"], dupes, ans))
        print(f"  {iid}  human={lab['error_type']}")
        print(f"    duplicated  : {dupes}")
        print(f"    keyed answer: {ans!r}   ANSWER IS THE DUPLICATE: {ans in dupes}")

    missed_by_humans = [x for x in key_dup if x[1] == "ok"]
    print(f"\n  {len(key_dup)} of {len(dup_opt)} flags have the KEYED ANSWER duplicated.")
    print(f"  Those items have two identical correct options: multiple correct answers by")
    print(f"  construction, verifiable by string comparison, no subject knowledge required.")
    print(f"  Humans labelled {len(missed_by_humans)} of those {len(key_dup)} as 'ok'.")
    for iid, _, dupes, _ in missed_by_humans:
        print(f"    - {iid}: {dupes}")
    print(f"\n  The other {len(opt_dup)} duplicate a NON-key option. Still a defect (a 4-option")
    print(f"  item effectively offering 3), but outside Redux's taxonomy, so 'ok' is not wrong.")

    print("\n=== the misses: multiple_correct_answers the battery could not see ===")
    missed = sorted(multi - dup_opt)
    print(f"  {len(missed)} of {len(multi)}. Every one is a SEMANTIC duplicate:")
    for iid in missed[:3]:
        print(f"    - {iid}: {[str(c) for c in items[iid]['choices']]}")
        reason = (labels[iid].get("potential_reason") or "").strip()
        if reason:
            print(f"      human reason: {reason[:100]}")

    print("\n=== S1 dup-questions: out of Redux's taxonomy, reported not scored ===")
    print(f"  {dup_q_keys} duplicated key(s) covering {len(dup_q)} item(s).")
    print(f"  {len(dup_q & flawed)} of them carry a Redux defect label; the rest are 'ok'.")
    print("  Redux annotates whether an item is ANSWERABLE, not whether it is UNIQUE, so")
    print("  these are not false positives. A benchmark shipping the same item twice")
    print("  double-weights it, which is a real defect that this ground truth cannot score.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
