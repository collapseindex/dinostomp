"""Score the judge against human annotation, before anyone trusts it.

No check in the core shipped with an external precision/recall number. This one
cannot ship without one, because it is a MODEL'S OPINION about somebody's
dataset and the only honest way to offer that is with its error rates attached.

    set OPENROUTER_API_KEY, then:
    python extensions/semdup/validate.py

The set: all 39 items MMLU-Redux labels `multiple_correct_answers`, plus a
seeded random sample of items it labels `ok`. The negatives matter more than the
positives here. A check that flags everything has perfect recall, and a check
run over a real 3,000-item benchmark will meet ~50x more clean items than dirty
ones, so its false-positive rate is what decides whether it is usable at all.

Verdicts are cached by (item, model), so a re-run costs nothing and the numbers
below are reproducible without re-paying.
"""

from __future__ import annotations

import json
import os
import random
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dinostomp.providers import make_provider  # noqa: E402
from dinostomp.spec import jsonl_lines  # noqa: E402
from dinostomp_semdup import _ask, _key, _save  # noqa: E402

REDUX = REPO / "benchmarks" / "mmlu-redux"
CACHE = (Path(__file__).resolve().parent
         / f"validation-cache-{(os.environ.get(chr(83)+chr(69)+chr(77)+chr(68)+chr(85)+chr(80)+chr(95)+chr(74)+chr(85)+chr(68)+chr(71)+chr(69)) or chr(56)+chr(98)).replace(chr(47), chr(45))}.json")
MODEL = os.environ.get("SEMDUP_JUDGE") or "meta-llama/llama-3.1-8b-instruct"
RATE_IN, RATE_OUT = 0.05, 0.08          # USD per Mtok, as OpenRouter lists it
N_NEGATIVES = 250
SEED = 7
BUDGET_USD = 0.25                        # a hard stop; this should cost ~1 cent


def load(name):
    return [json.loads(l) for l in jsonl_lines((REDUX / name).read_text(encoding="utf-8"))
            if l.strip()]


def main() -> int:
    if not (REDUX / "items.jsonl").is_file():
        print("run `python benchmarks/mmlu-redux/fetch.py` first", file=sys.stderr)
        return 2
    items = {str(i["id"]): i for i in load("items.jsonl") if "id" in i}
    labels = {str(x["id"]): x for x in load("labels.jsonl")}

    positives = sorted(i for i in items if labels[i]["error_type"] == "multiple_correct_answers")
    ok_pool = sorted(i for i in items if labels[i]["error_type"] == "ok")
    negatives = random.Random(SEED).sample(ok_pool, min(N_NEGATIVES, len(ok_pool)))
    subset = positives + negatives
    print(f"{len(positives)} positives + {len(negatives)} negatives = {len(subset)} items")

    cache = {}
    if CACHE.is_file():
        cache = json.loads(CACHE.read_text(encoding="utf-8"))
    todo = [i for i in subset if _key(items[i], MODEL) not in cache]
    print(f"{len(todo)} not cached")

    if todo:
        if not os.environ.get("OPENROUTER_API_KEY"):
            print("OPENROUTER_API_KEY is not set; cannot judge the uncached items",
                  file=sys.stderr)
            return 2
        provider = make_provider("openrouter", MODEL)
        spent = 0.0
        for n, iid in enumerate(todo, 1):
            try:
                verdict, usage_in, usage_out, raw = _ask(
                    provider, items[iid], {"temperature": 0, "max_tokens": 40})
            except Exception as exc:  # noqa: BLE001 - keep what was paid for
                print(f"stopped after {n - 1}: {exc}", file=sys.stderr)
                break
            cache[_key(items[iid], MODEL)] = {"dup": verdict, "raw": raw[:200]}
            # Priced from the RECORDED usage. The first version added 0.0 here,
            # so the cap below could never fire: a budget that cannot stop a run
            # is worse than no budget, because it reads like a guarantee.
            spent += (usage_in * RATE_IN + usage_out * RATE_OUT) / 1e6
            if n % 50 == 0:
                print(f"  {n}/{len(todo)}")
                _save(CACHE, cache)
            if spent > BUDGET_USD:
                print(f"budget cap {BUDGET_USD} reached at {n}", file=sys.stderr)
                break
        _save(CACHE, cache)

    got = {i: cache[_key(items[i], MODEL)] for i in subset if _key(items[i], MODEL) in cache}
    pos = [i for i in positives if i in got]
    neg = [i for i in negatives if i in got]
    tp = sum(1 for i in pos if got[i]["dup"] is True)
    fn = sum(1 for i in pos if got[i]["dup"] is False)
    fp = sum(1 for i in neg if got[i]["dup"] is True)
    tn = sum(1 for i in neg if got[i]["dup"] is False)
    und = sum(1 for i in got if got[i]["dup"] is None)

    print(f"\njudge: {MODEL}   judged {len(got)} of {len(subset)}")
    print(f"  on the {len(pos)} human-confirmed multiple_correct_answers:")
    print(f"    caught  : {tp}")
    print(f"    missed  : {fn}")
    print(f"  on the {len(neg)} human-labelled 'ok':")
    print(f"    false alarms: {fp}")
    print(f"    correct pass: {tn}")
    print(f"  unparseable replies: {und}")
    if tp + fn:
        print(f"\n  recall    {tp / (tp + fn):.0%}   (core S5 reaches 5%)")
    if tp + fp:
        print(f"  precision {tp / (tp + fp):.0%}")
    if neg:
        print(f"  false-positive rate on clean items: {fp / len(neg):.1%}")
        print(f"  -> on a 3,000-item benchmark that is ~{fp / len(neg) * 3000:.0f} false flags")

    print("\n  examples it caught:")
    for i in [x for x in pos if got[x]["dup"] is True][:3]:
        print(f"    {i}: {[str(c) for c in items[i]['choices']]}")
    print("\n  examples it flagged that humans called ok:")
    for i in [x for x in neg if got[x]["dup"] is True][:5]:
        print(f"    {i}: {[str(c) for c in items[i]['choices']]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
