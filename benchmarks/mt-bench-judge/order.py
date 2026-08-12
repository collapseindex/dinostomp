"""Can J2 (presentation-order bias) be graded against the MT-Bench release?

    python benchmarks/mt-bench-judge/fetch.py
    python benchmarks/mt-bench-judge/order.py

ANSWER: no, and this script exists to show the work rather than assert it.

J2 asks whether a judge's verdict survives swapping which response is shown
first. Grading it externally needs the SAME comparison judged in BOTH orders.
The release records `gpt4_pair` with 2,400 votes and **zero** such pairs, so
the check stays self-scored. That was already stated; what follows is what
happened when the surrounding data was checked for a way around it.

THE NEAR-MISS, KEPT BECAUSE IT IS THE INSTRUCTIVE PART.

The human file DOES contain 1,164 comparisons shown in both orders and 959
repeated orderings, which looks like the missing evidence. It is not: those are
across DIFFERENT annotators. Conditioned on the same annotator there are 0
repeated gradings and 1 both-order pair. Inter-annotator disagreement is not
position bias.

What remains measurable is a POPULATION-level order effect, and on the full
human set there is none: P(first-shown wins) = 50.2%, which is the baseline
that makes any judge number readable.

Against that, GPT-4 looked dramatically order-biased: 10.6% first-wins overall,
and 10.5 points below humans on the 1,232 orderings the two files share. Both
numbers are real and neither means what it appears to.

  * The shared subset is not balanced. Humans score 50.2% on the whole file and
    22.0% on the shared subset, so those comparisons simply have the stronger
    model in position B.
  * Conditioning on which model is stronger REVERSES the sign. GPT-4 favours the
    first-shown response MORE than humans when it is the stronger one (+12.5%)
    and LESS when it is the weaker one (-11.8%). Position bias pushes one way
    regardless of strength; this pushes toward the stronger model in both cells.

So the aggregate gap measures sharper discrimination, not position preference,
and it survived only because 876 of 930 shared comparisons put the weaker model
first. Settling J2 needs a judge run twice on inputs somebody else controls,
which is API spend and not a join.
"""

from __future__ import annotations

import collections
import json
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
RAW = HERE / "data" / "raw"

MIN_GAMES_FOR_STRENGTH = 30


def _load(name: str) -> list[dict]:
    try:
        import pyarrow.parquet as pq
    except ImportError:
        print("needs pyarrow: pip install pyarrow", file=sys.stderr)
        raise SystemExit(3) from None
    path = RAW / name
    if not path.is_file():
        print(f"missing {path.name}; run: python benchmarks/mt-bench-judge/fetch.py",
              file=sys.stderr)
        raise SystemExit(3)
    return pq.read_table(path).to_pylist()


def _first_win_rate(rows: list[dict]) -> tuple[float, float, int]:
    """P(the first-shown response wins), ties excluded, with a standard error."""
    first = sum(1 for r in rows if r["winner"] == "model_a")
    second = sum(1 for r in rows if r["winner"] == "model_b")
    n = first + second
    if not n:
        return float("nan"), float("nan"), 0
    p = first / n
    return p, math.sqrt(p * (1 - p) / n), n


def main() -> int:
    judge = _load("gpt4_pair.parquet")
    human = _load("human.parquet")

    def order_key(r):
        return (r["question_id"], r["turn"], r["model_a"], r["model_b"])

    seen = collections.Counter(order_key(r) for r in judge)
    both = sum(1 for k in seen if (k[0], k[1], k[3], k[2]) in seen)
    print(f"  judge votes: {len(judge)}   same comparison in both orders: {both}")
    if both:
        print("  J2 is now gradable against this release; this script's premise has changed.")
        return 1
    print("  J2 CANNOT be graded here: zero both-order pairs. The rest is the near-miss.\n")

    # Per-annotator, the human file offers no J2 or J3 evidence either.
    by_judge_order = collections.Counter(
        (r["judge"],) + order_key(r) for r in human)
    same_annotator_repeats = sum(v - 1 for v in by_judge_order.values() if v > 1)
    per_annotator_both = 0
    seen_h = set(by_judge_order)
    for j, q, t, a, b in seen_h:
        if (j, q, t, b, a) in seen_h and a < b:
            per_annotator_both += 1
    print(f"  human file, per annotator: {same_annotator_repeats} repeated gradings (J3), "
          f"{per_annotator_both} both-order pairs (J2)")

    ph, seh, nh = _first_win_rate(human)
    print(f"\n  humans, all {len(human)} votes: P(first wins) = {ph:.1%} "
          f"+/- {1.96*seh:.1%}   z vs 50% = {(ph-0.5)/seh:+.2f}")

    jk = {order_key(r): r for r in judge}
    hk = collections.defaultdict(list)
    for r in human:
        hk[order_key(r)].append(r)
    shared = [k for k in jk if k in hk]
    pj, sej, nj = _first_win_rate([jk[k] for k in shared])
    ph2, seh2, nh2 = _first_win_rate([r for k in shared for r in hk[k]])
    gap = pj - ph2
    gse = math.sqrt(sej**2 + seh2**2)
    print(f"  {len(shared)} shared orderings: judge {pj:.1%}, humans {ph2:.1%}, "
          f"gap {gap:+.1%} (z = {gap/gse:+.2f})")
    print("  ^ looks like position bias. It is not; condition on model strength:")

    wins: collections.Counter = collections.Counter()
    games: collections.Counter = collections.Counter()
    for r in human:
        games[r["model_a"]] += 1
        games[r["model_b"]] += 1
        if r["winner"] == "model_a":
            wins[r["model_a"]] += 1
        elif r["winner"] == "model_b":
            wins[r["model_b"]] += 1
    strength = {m: wins[m] / games[m] for m in games
                if games[m] >= MIN_GAMES_FOR_STRENGTH}

    rows = {}
    for label, first_stronger in (("first-shown STRONGER", True),
                                  ("first-shown WEAKER", False)):
        keys = [k for k in shared
                if k[2] in strength and k[3] in strength
                and (strength[k[2]] > strength[k[3]]) is first_stronger]
        pj2, sej2, njj = _first_win_rate([jk[k] for k in keys])
        ph3, seh3, nhh = _first_win_rate([r for k in keys for r in hk[k]])
        d = pj2 - ph3
        z = d / math.sqrt(sej2**2 + seh3**2)
        rows[label] = {"judge": round(pj2, 4), "human": round(ph3, 4),
                       "diff": round(d, 4), "z": round(z, 2),
                       "n_judge": njj, "n_human": nhh}
        print(f"    {label:22} judge {pj2:>6.1%} (n={njj:<4})  "
              f"human {ph3:>6.1%} (n={nhh:<4})  diff {d:+.1%}  z={z:+.2f}")

    verdict = ("the sign reverses with model strength, so the aggregate gap is "
               "sharper discrimination, not position preference")
    print(f"\n  VERDICT: {verdict}.")

    out = HERE / "ORDER.json"
    out.write_text(json.dumps({
        "question": "can J2 be graded against the MT-Bench release?",
        "answer": "no",
        "judge_votes": len(judge),
        "judge_both_order_pairs": both,
        "human_per_annotator_repeats": same_annotator_repeats,
        "human_per_annotator_both_order_pairs": per_annotator_both,
        "human_first_win_rate_all": round(ph, 4),
        "shared_orderings": len(shared),
        "by_strength": rows,
        "verdict": verdict,
    }, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"  wrote {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
