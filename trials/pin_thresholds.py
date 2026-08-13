"""Which thresholds could be quietly loosened without anyone noticing?

DinoTrials answers "does this defect get caught". It does not answer "does this
defect get caught AT THIS SETTING", and the difference is the attack surface of
an audited battery. Every threshold in `THRESHOLDS` is a number someone can
edit. If loosening one does not break a single trial, then whoever extends this
tool (a contributor, a future maintainer, an LLM asked to "make the pod pass")
can relax it and the whole suite stays green.

The engine fingerprint proves the code CHANGED. It says nothing about whether it
changed in a self-serving direction. This does.

Method: loosen each threshold one at a time in the permissive direction, re-run
the full trial suite, and record whether anything failed. A threshold no trial
notices is reported as UNPINNED, which is a request for a boundary trial rather
than an accusation: some are unpinned because nothing in the suite exercises
that shape yet.

Run:  python trials/pin_thresholds.py [--factor 3] [--json PATH]

Slow by construction: it re-runs the whole suite once per threshold.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dinostomp.lint import THRESHOLDS  # noqa: E402
from trials import run_trials  # noqa: E402

# Thresholds where a LARGER number means the check fires less often. Everything
# else is a minimum-evidence bar, where SMALLER means it fires less often, and
# the two directions must not be confused or the probe tests nothing.
LOOSEN_UPWARD = {
    # Margins and ceilings: a BIGGER number means the check fires less often.
    "position_margin", "length_margin", "uncheckable_warn", "negative_discrimination",
    "dead_weight_max", "ordering_flip_rate", "ceiling_acc", "escape_margin", "escape_min_rate",
    "shortcut_z", "shortcut_lift", "ungrounded_max", "redundant_call_max", "collapse_margin",
    "contains_target_max", "judge_inconsistency_max", "self_preference_max",
    "seed_spread_min", "order_swing_min",
    "noise_z",
    "billing_ratio_max",
    # Minimum-evidence bars: RAISING them means fewer models qualify to be
    # judged at all, which is looser. Getting this backwards tests the check in
    # the STRICT direction, where a "pinned" result only means some clean pod
    # started false-alarming. Three thresholds were misclassified this way on
    # the first run, and their results were meaningless.
    "min_checkable", "min_billed_chars", "min_grounding_evidence", "min_scored_misses",
}

# Structural constants rather than sensitivity dials: moving them changes what
# an eval IS, not how loudly a check complains.
STRUCTURAL = {"bootstrap_trials", "spend_tolerance_usd", "min_leak_len", "min_items_psycho",
              "min_fleet", "min_fleet_agree", "min_choice_items", "collapse_exclude_share",
              # a POWER statement, not a sensitivity dial: it changes only whether P2
              # admits it cannot see, never whether it fires
              "min_fleet_discrimination"}


def suite_green() -> bool:
    """Run the whole trial suite, silently. True when nothing missed.

    sys.argv is swapped out first: run_trials parses it, so without this the
    probe's own --json flag is consumed by the suite and every iteration
    overwrites the scorecard we are trying to write. Found the hard way.
    """
    buf = io.StringIO()
    saved = sys.argv
    sys.argv = ["run_trials"]
    try:
        with contextlib.redirect_stdout(buf):
            return run_trials.main() == 0
    except Exception:  # noqa: BLE001 - a crashed suite is not a green suite
        return False
    finally:
        sys.argv = saved


def main() -> int:
    ap = argparse.ArgumentParser(description="find thresholds no trial pins")
    ap.add_argument("--factor", type=float, default=3.0,
                    help="how far to loosen each threshold (default 3x)")
    ap.add_argument("--json", help="write the scorecard as JSON")
    args = ap.parse_args()

    if not suite_green():
        print("BASELINE IS NOT GREEN. Fix the trials before asking what they pin.")
        return 2

    dials = [k for k, v in sorted(THRESHOLDS.items())
             if isinstance(v, (int, float)) and k not in STRUCTURAL]
    print(f"Loosening {len(dials)} threshold(s) by {args.factor}x, one at a time.")
    print("A threshold no trial notices can be relaxed by whoever extends this tool.\n")
    print(f"  {'threshold':<26} {'now':>10} {'loosened':>10}  pinned by a trial?")

    rows, unpinned = [], []
    for key in dials:
        original = THRESHOLDS[key]
        if key in LOOSEN_UPWARD:
            loosened = original * args.factor if original > 0 else 0.5
        else:
            loosened = max(0, original / args.factor)
        THRESHOLDS[key] = loosened
        try:
            pinned = not suite_green()
        finally:
            THRESHOLDS[key] = original
        rows.append({"threshold": key, "value": original, "loosened": loosened, "pinned": pinned})
        if not pinned:
            unpinned.append(key)
        print(f"  {key:<26} {original:>10} {loosened:>10.4g}  {'yes' if pinned else 'NO'}")

    print(f"\n  pinned:   {len(rows) - len(unpinned)} of {len(rows)}")
    print(f"  UNPINNED: {len(unpinned)}")
    for key in unpinned:
        print(f"    - {key}")
    if unpinned:
        print("\nEach of these wants a boundary trial: a planted defect sized so that it is "
              "caught at the shipped setting and missed at a looser one.")
    if args.json:
        Path(args.json).write_text(json.dumps(
            {"factor": args.factor, "rows": rows, "unpinned": unpinned}, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
