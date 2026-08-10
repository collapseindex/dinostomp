"""Score a detector against the corpus.

    python corpus/score.py                          # score dinostomp itself
    python corpus/score.py --submission mine.json   # score somebody else's tool

THE HEADLINE IS TWO NUMBERS, NEVER ONE. Recall without a false-alarm rate is
half a result: a detector that flags every instance scores 100% recall and is
useless, and the clean arm is what says so. Both are printed together and
neither is reported alone.

THE SECOND HEADLINE IS THE BLIND-SPOT ARM. 53% of the defective instances are
classes dinostomp has no check for, planted deliberately. Its recall there is
expected to be near zero, and publishing that number is the entire reason this
corpus is worth anything to somebody who did not write it. A benchmark whose
author scores 100% measures the author.

SUBMISSION FORMAT, for any other tool:

    {"dev-00008": {"detected": true, "checks": ["my-key-checker"]},
     "dev-00009": {"detected": false}}

`detected` means "this instance has something wrong with it". Instances absent
from the submission count as not detected, so a partial submission is scored on
the whole corpus rather than on the part somebody chose to answer.

WHAT COUNTS AS A CATCH. For a class with an expected check, that check must
fire. For a blind-spot class there is no expected check, so ANY finding counts,
which is deliberately generous to the detector. On a clean instance any finding
at all is a false alarm.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

FIRED = ("fail", "warn")


def load_labels(split: str) -> list[dict]:
    """Labels for a split, public or withheld, verified against the commitment.

    A withheld split ships no labels: the scorekeeper holds
    `labels.WITHHELD.jsonl` and the repository holds only a SHA-256 of it,
    published before any submission was scored. Re-checking that hash here is
    what makes the scorekeeper auditable by their own tooling. If the labels
    were edited after the commitment, scoring REFUSES rather than quietly
    producing a number, because a benchmark whose author can change the answer
    key after seeing the answers is not a benchmark.
    """
    folder = HERE / "instances" / split
    public, withheld = folder / "labels.jsonl", folder / "labels.WITHHELD.jsonl"
    path = public if public.is_file() else withheld
    if not path.is_file():
        raise SystemExit(f"no labels at {folder}; run `python corpus/generate.py --split {split}`")
    text = path.read_text(encoding="utf-8")

    manifest_path = folder / "MANIFEST.json"
    if manifest_path.is_file():
        committed = json.loads(manifest_path.read_text(encoding="utf-8")).get("labels_sha256")
        if committed:
            import hashlib

            actual = hashlib.sha256(text.encode()).hexdigest()
            if actual != committed:
                raise SystemExit(
                    f"{path.name} does not match the commitment in MANIFEST.json.\n"
                    f"  committed {committed}\n  actual    {actual}\n"
                    "The labels changed after they were committed to. Refusing to score: a "
                    "number computed against an edited answer key is worse than no number.")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def run_dinostomp(split: str, labels: list[dict]) -> dict[str, dict]:
    """The built-in adapter, so this repository's own number is always current.

    Calls the same data-scope audit `dinostomp stomp <file>` runs. Offline,
    free, no model.
    """
    from dinostomp.lint import lint_dataset

    out = {}
    for i, label in enumerate(labels, 1):
        path = HERE / "instances" / split / label["id"] / "items.jsonl"
        report, issues, _ctx = lint_dataset(path)
        if report is None:
            # A dataset the audit cannot read at all is not a detection: the
            # tool said nothing about the planted defect, it said it could not
            # look. Counting that as a catch would be scoring a crash.
            out[label["id"]] = {"detected": False, "checks": [], "unreadable": True}
            continue
        fired = [f["id"] for f in report["findings"] if f["level"] in FIRED]
        # Which ITEMS the tool pointed at, so strict scoring can ask whether it
        # found the planted defect or merely found something.
        located = []
        for f in report["findings"]:
            if f["level"] in FIRED:
                located += [str(x).split(":")[0].strip() for x in (f.get("examples") or [])]
        out[label["id"]] = {"detected": bool(fired), "checks": fired, "located": located}
        if i % 50 == 0:
            print(f"  ... {i}/{len(labels)}", file=sys.stderr)
    return out


def judge(label: dict, answer: dict, strict: bool = False) -> bool:
    """Did the detector catch THIS instance?

    Two modes, and the difference between them is a real correction rather than
    a knob. GENEROUS credits any finding on a blind-spot instance, since there
    is no expected check to name. That over-credits: on the first scored run,
    every blind-spot instance dinostomp appeared to catch was the SAME
    unrelated position-bias warning firing by chance, and a coincidence counted
    as a detection four times.

    STRICT requires the finding to name an item the defect was actually planted
    in. A detector that flags the file for an unrelated reason has not found the
    defect, and a corpus that says it has is flattering its own author first.
    """
    if label["clean"]:
        return bool(answer.get("detected"))  # the caller reads this as a false alarm
    expected = label.get("detectable_by")
    checks = answer.get("checks") or []
    if expected:
        return expected in checks
    if not strict:
        return bool(answer.get("detected"))
    located = {str(x) for x in (answer.get("located") or [])}
    return bool(located & set(label.get("location") or []))


def score(labels: list[dict], answers: dict[str, dict]) -> dict:
    by_class: dict[str, list[bool]] = defaultdict(list)
    covered, blind, clean_flags, blind_strict = [], [], [], []
    for label in labels:
        answer = answers.get(label["id"]) or {"detected": False, "checks": []}
        hit = judge(label, answer)
        if label["clean"]:
            clean_flags.append(hit)
            continue
        by_class[label["class"]].append(hit)
        (blind if label["detectable_by"] is None else covered).append(hit)
        if label["detectable_by"] is None:
            blind_strict.append(judge(label, answer, strict=True))

    def rate(xs):
        return round(sum(xs) / len(xs), 4) if xs else None

    return {
        "n_scored": len(labels),
        "recall_overall": rate(covered + blind),
        "recall_covered": rate(covered),
        "n_covered": len(covered),
        # The number that decides whether this corpus is an instrument.
        "recall_blind_spot": rate(blind),
        "recall_blind_spot_strict": rate(blind_strict),
        "n_blind_spot": len(blind),
        "false_alarm_rate_on_clean": rate(clean_flags),
        "n_clean": len(clean_flags),
        "by_class": {c: {"n": len(v), "recall": rate(v)} for c, v in sorted(by_class.items())},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", default="dev")
    ap.add_argument("--submission", help="a tool's answers as JSON; omit to score dinostomp")
    ap.add_argument("--json", help="write the scorecard here")
    args = ap.parse_args()

    labels = load_labels(args.split)
    if args.submission:
        answers = json.loads(Path(args.submission).read_text(encoding="utf-8"))
        who = Path(args.submission).stem
    else:
        print(f"scoring dinostomp on {len(labels)} instances ...", file=sys.stderr)
        answers = run_dinostomp(args.split, labels)
        from dinostomp import __version__
        who = f"dinostomp {__version__}"

    card = score(labels, answers)
    card["detector"] = who
    card["split"] = args.split

    print(f"\nDINOCORPUS {args.split}: {who}\n")
    print(f"  recall, classes it has a check for   {card['recall_covered']:.1%} "
          f"of {card['n_covered']}")
    blind = card["recall_blind_spot"]
    strict = card["recall_blind_spot_strict"]
    print(f"  recall, classes it does NOT          {blind:.1%} of {card['n_blind_spot']}"
          if blind is not None else "  recall, blind-spot arm               n/a")
    print(f"    of which name the planted item     {strict:.1%}"
          if strict is not None else "")
    fa = card["false_alarm_rate_on_clean"]
    print(f"  false alarms on clean instances      {fa:.1%} of {card['n_clean']}")
    if blind is not None and fa is not None and blind <= fa:
        print()
        print(f"  NOTE: blind-spot recall ({blind:.1%}) is at or below the false-alarm rate on")
        print(f"  clean data ({fa:.1%}), so it is not distinguishable from the detector firing")
        print("  at random. The strict figure above is the one to read.")
    print(f"\n  overall {card['recall_overall']:.1%} of "
          f"{card['n_covered'] + card['n_blind_spot']} defective instances\n")
    print(f"  {'class':<32} {'n':>4}  recall")
    for name, row in card["by_class"].items():
        expected = next((lab["detectable_by"] for lab in labels if lab["class"] == name), None)
        mark = expected or "BLIND"
        print(f"  {name:<32} {row['n']:>4}  {row['recall']:>6.1%}   {mark}")
    print("\n  Recall here is an UPPER BOUND: the items are synthetic and cleaner than "
          "real\n  benchmark items. See corpus/basepool.py.")

    if args.json:
        Path(args.json).write_text(json.dumps(card, indent=2) + "\n",
                                   encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
