"""How often Jevlike's shuffled-context control hands a menu a page that names
the SAME target article. The control is `context.roll(1, dims=0)` inside each
batch of 64; the split is bucketed by target and written in path order.

    python audits/jevlike/control_leak.py data/wikispeedia/jsonl/test.jsonl [--batch 64]
"""

from __future__ import annotations

import argparse
import io
import json
import random


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl")
    ap.add_argument("--batch", type=int, default=64, help="Jevlike's evaluator batch size")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    rows = [json.loads(l) for l in io.open(args.jsonl, encoding="utf-8") if l.strip()]
    targets = [r["context"].split("\n", 1)[0] for r in rows]
    currents = [r["context"].split("\n")[1] if "\n" in r["context"] else "" for r in rows]
    rng = random.Random(args.seed)
    n = same_target_roll = same_target_perm = same_current_roll = 0
    for start in range(0, len(rows), args.batch):
        idx = list(range(start, min(start + args.batch, len(rows))))
        if len(idx) < 2:
            continue
        roll = idx[1:] + idx[:1]          # what roll(1) pairs each row with
        perm = idx[:]
        rng.shuffle(perm)                 # what a random within-batch permutation would pair
        for a, b, c in zip(idx, roll, perm):
            n += 1
            same_target_roll += targets[a] == targets[b]
            same_current_roll += currents[a] == currents[b]
            same_target_perm += targets[a] == targets[c]
    print(f"rows {len(rows)} | distinct targets {len(set(targets))} | largest target group "
          f"{max(targets.count(t) for t in set(targets))}")
    print(f"shuffled partner names the SAME TARGET: roll-by-one {same_target_roll / n:.1%}, "
          f"random permutation within batch {same_target_perm / n:.1%}")
    print(f"shuffled partner is the SAME CURRENT PAGE under roll: {same_current_roll / n:.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
