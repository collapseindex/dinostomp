"""Every number the paper states, checked against the repository.

    python writeup/numbers.py            # print what the repo says
    python writeup/numbers.py --check    # fail if main.tex has gone stale

WHY THIS EXISTS. A paper quoting a number that the code no longer produces is
the exact defect this project audits other people for, and it is the easiest one
in the world to commit: the tool moves, the draft does not, and nobody notices
because nothing re-derives the prose. The repository already refuses to publish
a report whose summary does not recompute from its records. The paper gets the
same treatment.

WHAT IT CANNOT DO. It checks that stated numbers match the repository as it
stands NOW. It cannot tell you the paper's claims are true, only that they are
current, and a number can be current and still be the wrong number to have
quoted.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "corpus"))


# Artifacts this script needs that are NOT in the repository, with the command
# that produces each. The pods are fetched from their authors and never
# vendored, so a fresh clone legitimately lacks them.
FETCHED = {
    "benchmarks/mmlu-redux/labels.jsonl": "python benchmarks/mmlu-redux/fetch.py",
    "benchmarks/mmlu-redux/items.jsonl": "python benchmarks/mmlu-redux/fetch.py",
}


def require_fetched() -> None:
    """Say what is missing and how to get it, instead of raising FileNotFoundError.

    This script is the receipt for the preprint's claim that every number
    re-derives from a pinned commit, and until now a reader who cloned that
    commit and ran it got a traceback out of `_redux_reachable`. The battery's
    own rule is that a check which cannot run reports what is missing rather
    than guessing; the script that measures the battery was not following it.
    """
    missing = {rel: cmd for rel, cmd in FETCHED.items() if not (ROOT / rel).is_file()}
    if not missing:
        return
    print("cannot re-derive: these artifacts are fetched, not vendored\n",
          file=sys.stderr)
    for rel in sorted(missing):
        print(f"  missing  {rel}", file=sys.stderr)
    print("\nrun, from the repository root:", file=sys.stderr)
    for cmd in sorted(set(missing.values())):
        print(f"  {cmd}", file=sys.stderr)
    print("\nThe fetch needs a network. Everything after it, including every\n"
          "number in the paper, runs offline with no model.", file=sys.stderr)
    sys.exit(3)


def gather() -> dict:
    """Every quantity the paper is allowed to state, read from the artifacts."""
    import taxonomy
    from dinostomp import __version__
    from dinostomp.fingerprint import engine_fingerprint
    from dinostomp.lint import CHECKS, SCOPE_CHECKS, _s3_chance_rate
    from trials.run_trials import CLEAN_TRIALS, TRIALS

    def load(rel):
        return json.loads((ROOT / rel).read_text(encoding="utf-8"))

    feed = load("findings.json")
    dev, held = load("corpus/instances/dev/MANIFEST.json"), \
        load("corpus/instances/heldout-2026-08/MANIFEST.json")
    held_b = load("corpus/instances/heldout-2026-08b/MANIFEST.json")
    s_dev = load("corpus/scorecards/dinostomp.json")
    s_held = load("corpus/scorecards/dinostomp-heldout.json")
    s_held_b = load("corpus/scorecards/dinostomp-heldout-08b.json")
    s_assets = load("corpus/scorecards/dinostomp-assets-b.json")
    s_shapes = load("corpus/scorecards/dinostomp-shapes.json")
    shapes_man = load("corpus/instances/heldout-shapes-2026-08/MANIFEST.json")
    assets_man = load("corpus/instances/heldout-assets-2026-08b/MANIFEST.json")
    pods = [p.name for p in (ROOT / "benchmarks").iterdir()
            if p.is_dir() and (p / "eval.yaml").is_file()]
    tax = taxonomy.summary()

    return {
        "version": __version__,
        "engine16": engine_fingerprint()[:16],
        "checks": len(CHECKS),
        "data_checks": len(SCOPE_CHECKS["data"]),
        "gating": sum(1 for c in CHECKS if c[2]),
        "trials": len(TRIALS),
        "clean_trials": len(CLEAN_TRIALS),
        "F": feed["counts"]["F"], "D": feed["counts"]["D"], "N": feed["counts"]["N"],
        "findings_total": feed["counts"]["total"],
        "benchmark_pods": len(pods),
        "corpus_classes": tax["n_classes"],
        "corpus_blind": tax["n_blind_spots"],
        "corpus_from_own_checks": tax["by_source"].get("own-checks", 0),
        "corpus_from_literature": tax["by_source"].get("literature", 0),
        "corpus_from_wild": tax["by_source"].get("wild", 0),
        "dev_instances": dev["n_instances"],
        "heldout_instances": held["n_instances"],
        "dev_covered": s_dev["recall_covered"],
        "dev_blind": s_dev["recall_blind_spot"],
        "held_blind": s_held["recall_blind_spot"],
        "dev_blind_strict": s_dev["recall_blind_spot_strict"],
        "dev_false_alarm": s_dev["false_alarm_rate_on_clean"],
        "held_covered": s_held["recall_covered"],
        "held_blind_strict": s_held["recall_blind_spot_strict"],
        "held_false_alarm": s_held["false_alarm_rate_on_clean"],
        # S3's chance rate at four options, as the tool computes it at report
        # time. Quoted in three places in the paper and, until now, only
        # whitelisted as strings -- so the superseded simulated values sat in
        # the allow-list and a wrong analytic rate would have passed.
        "s3_at_20": _s3_chance_rate(20, 4),
        "s3_at_24": _s3_chance_rate(24, 4),
        "s3_at_50": _s3_chance_rate(50, 4),
        "heldout_b_instances": held_b["n_instances"],
        "heldout_b_covered": s_held_b["recall_covered"],
        "heldout_b_blind": s_held_b["recall_blind_spot"],
        "heldout_b_blind_strict": s_held_b["recall_blind_spot_strict"],
        "heldout_b_false_alarm": s_held_b["false_alarm_rate_on_clean"],
        "assets_instances": assets_man["n_instances"],
        "assets_covered": s_assets["recall_covered"],
        "assets_blind": s_assets["recall_blind_spot"],
        "assets_blind_strict": s_assets["recall_blind_spot_strict"],
        "assets_false_alarm": s_assets["false_alarm_rate_on_clean"],
        "classes_unplanted": len(assets_man["classes_declared_not_yet_planted"]),
        "shapes_instances": shapes_man["n_instances"],
        "shapes_covered": s_shapes["recall_covered"],
        "shapes_blind": s_shapes["recall_blind_spot"],
        "shapes_blind_strict": s_shapes["recall_blind_spot_strict"],
        "shapes_false_alarm": s_shapes["false_alarm_rate_on_clean"],
        "n_shape_arms": len(shapes_man.get("shapes", [])),
        **_redux_reachable(),
        **_judge_calibration(load),
        # Pooled over the THREE TEXT splits. The image-backed split is excluded
        # on purpose: its instances mix four-option and two-option items, so
        # S3's analytic chance rate is not defined for them in the same closed
        # form, and pooling would compare a rate against a prediction that does
        # not cover it.
        **_pooled(["dev", "heldout-2026-08", "heldout-2026-08b"],
                  s_dev, s_held, s_held_b),
        # EVERY split, including the shape-varied one. These are counts and a
        # composition claim, both of which are legitimately pooled across all
        # five; only the RATE compared against S3's analytic prediction is not.
        **_all_splits_composition([s_dev, s_held, s_held_b, s_assets, s_shapes]),
    }


def _judge_calibration(load) -> dict:
    """The MT-Bench judge calibration, read from the result it wrote.

    Derived like everything else. The comparison that matters -- judge vs
    human on the SAME statistic -- is the one a careless draft gets wrong by
    reaching for annotator unanimity instead, so both sides are pinned.
    """
    r = load("benchmarks/mt-bench-judge/RESULT.json")
    return {"judge_agreement": r["judge_agreement"],
            "judge_human_baseline": r["human_leave_one_out_agreement"],
            "judge_scored_n": r["comparisons_scored"],
            "judge_threshold": r["judge_threshold"]}


def _redux_reachable() -> dict:
    """What share of MMLU-Redux's annotated errors a file-only check could reach.

    The ceiling on this entire class of tool, and the number that decides
    whether running one is worth anything. Derived from the annotation rather
    than stated, because a hand-typed ceiling is the easiest number in the
    paper to quietly round in our favour.

    Exactly one of Redux's six error types leaves a trace in the file, and
    only its verbatim subset; the reachability call is the benchmark's own,
    documented in benchmarks/mmlu-redux/compare.py.
    """
    from collections import Counter

    path = ROOT / "benchmarks" / "mmlu-redux" / "labels.jsonl"
    kinds = Counter(json.loads(l)["error_type"]
                    for l in path.open(encoding="utf-8") if l.strip())
    flawed = sum(v for k, v in kinds.items() if k not in ("", "ok"))
    reachable = kinds["multiple_correct_answers"]
    return {"redux_flawed": flawed, "redux_reachable": reachable,
            "redux_reachable_share": reachable / flawed}


def _all_splits_composition(scorecards) -> dict:
    """Clean instances and blind-spot instances across EVERY split.

    Separate from `_pooled` because these two quantities are legitimately
    computed over all four splits (they are counts and a composition claim)
    while the false-alarm RATE compared against S3's prediction is not.
    """
    ck = sum(round(s["false_alarm_rate_on_clean"] * s["n_clean"]) for s in scorecards)
    cn = sum(s["n_clean"] for s in scorecards)
    bk = sum(round(s["recall_blind_spot"] * s["n_blind_spot"]) for s in scorecards)
    bn = sum(s["n_blind_spot"] for s in scorecards)
    return {"all_clean_n": cn, "all_clean_k": ck, "all_false_alarm": ck / cn,
            "all_blind_n": bn, "all_blind": bk / bn}


def _pooled(splits: list[str], *scorecards) -> dict:
    """The clean-arm and blind-arm rates pooled across every split.

    Derived, not transcribed. The paper's central false-alarm claim is that the
    pooled rate agrees with a rate computable in advance from S3's threshold
    rule, and a claim of that shape is worthless if either side is a number
    somebody typed. Both sides are computed here.
    """
    import math

    from dinostomp.lint import _s3_chance_rate

    k = sum(round(s["false_alarm_rate_on_clean"] * s["n_clean"]) for s in scorecards)
    n = sum(s["n_clean"] for s in scorecards)
    p, z = k / n, 1.96
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d

    bk = sum(round(s["recall_blind_spot"] * s["n_blind_spot"]) for s in scorecards)
    bn = sum(s["n_blind_spot"] for s in scorecards)

    # Instance sizes are 24 or 25 items throughout; the prediction is the
    # size-weighted mix, read off the corpus rather than assumed.
    #
    # Scoped to the splits actually being pooled. It used to scan every split on
    # disk, so adding a fourth split reweighted the PREDICTION by instances whose
    # false alarms were not in the RATE it is compared against. The two numbers
    # happened to still agree at one decimal place, which is exactly how a
    # definition drifts without anyone noticing.
    sizes = _instance_sizes(splits)
    total = sum(sizes.values())
    predicted = sum(_s3_chance_rate(size, 4) * count for size, count in sizes.items()) / total

    return {"pooled_clean_n": n, "pooled_clean_k": k, "pooled_false_alarm": p,
            "pooled_ci_lo": max(0.0, centre - half), "pooled_ci_hi": centre + half,
            "pooled_blind_n": bn, "pooled_blind": bk / bn,
            "s3_predicted_for_corpus": predicted}


def _instance_sizes(splits: list[str]) -> dict[int, int]:
    """Items per instance across the NAMED splits, counted from the files."""
    from collections import Counter

    sizes: Counter = Counter()
    for name in splits:
        split = ROOT / "corpus" / "instances" / name
        if not split.is_dir():
            raise SystemExit(f"pooled split {name!r} is not on disk")
        for pod in split.iterdir():
            items = pod / "items.jsonl"
            if items.is_file():
                sizes[sum(1 for line in items.open(encoding="utf-8") if line.strip())] += 1
    return dict(sizes)


WORDS = {0: "zero", 2: "two", 5: "five", 9: "nine", 14: "fourteen", 16: "sixteen",
         17: "seventeen", 21: "twenty-one", 22: "twenty-two", 25: "twenty-five",
         47: "forty-seven", 61: "sixty-one", 89: "eighty-nine", 92: "ninety-two"}


def forms(n: int) -> list[str]:
    """A count written as a digit and as a word.

    Prose spells small numbers out and tables use digits; both are correct and a
    checker that insisted on one would push the paper into writing badly to
    satisfy it.
    """
    out = [str(n)]
    if n in WORDS:
        out += [WORDS[n], WORDS[n].capitalize()]
    return out


def flatten(tex: str) -> str:
    r"""Normalise LaTeX for literal matching.

    Collapse whitespace, unescape \%, and drop \phantom{0}, which is column
    alignment rather than content. Without that last step, adding one digit to a
    table column silently un-checks every row that gained a phantom.
    """
    tex = tex.replace(r"\phantom{0}", "")
    return " ".join(tex.replace(chr(92) + "%", "%").split())


# (description, the literal string that MUST appear in main.tex)
def expectations(n: dict) -> list[tuple[str, str]]:
    return [
        ("pinned version", f"\\newcommand{{\\pinnedversion}}{{{n['version']}}}"),
        ("pinned engine", f"\\newcommand{{\\pinnedengine}}{{{n['engine16']}}}"),
        ("battery size", f"{n['checks']}-check"),
        ("data-scope checks", f"({n['data_checks']} checks)"),
        ("gating checks", f"{n['gating']} are \\emph{{invariants}}"),
        ("trials", f"{n['trials']} planted defects"),
        ("trials score", f"{n['trials']}/{n['trials']} and {n['clean_trials']}/{n['clean_trials']}"),
        ("clean pods", f"{n['clean_trials']} pods that must stay silent"),
        ("ledger total", f"{n['findings_total']} permanent entries"),
        ("ledger F", f"{n['F']} findings in other people's"),
        ("ledger D", f"\\textbf{{{n['D']} defects in the battery}}"),
        ("ledger N", f"{n['N']} negative results"),
        # The two counts genuinely differ: one finding is in a published
        # statistical release rather than a benchmark pod, and stating both
        # without the reason read as a contradiction.
        # Pods and findings are DIFFERENT quantities and this expectation used to
        # conflate them, which only looked right while the two counts coincided.
        # The moment pods outgrew findings it demanded "31 of the ledger's 29".
        ("benchmark pods", f"{n['benchmark_pods']} benchmark pods, all fetched from their"),
        ("findings in pods", f"all but one of the ledger's {n['F']} findings"),
        ("corpus classes", f"{n['corpus_classes']} defect classes"),
        ("corpus blind arm", None),   # checked as either-form below
        ("corpus sources", f"{n['corpus_from_literature']} come from the published"),
        ("corpus own-checks", f"\\textbf{{{n['corpus_from_own_checks']} from our own checks}}"),
        ("dev row", f"& {n['dev_instances']} & {n['dev_covered']:.1%} &"),
        ("heldout row", f"& {n['heldout_instances']} & {n['held_covered']:.1%} &"),
        ("dev false alarms", rf"{n['dev_false_alarm']:.1%} false alarms on \texttt{{dev}}"),
        ("heldout false alarms", f"{n['held_false_alarm']:.1%} on"),
        ("dev generous blind", f"& {n['dev_blind']:.1%} & {n['dev_blind_strict']:.1%}"),
        ("heldout generous blind", f"& {n['held_blind']:.1%} & {n['held_blind_strict']:.1%}"),
        ("S3 chance at 20", f"{n['s3_at_20']:.1%} of the time at 20 items"),
        ("S3 chance at 24", f"{n['s3_at_24']:.1%} at 24"),
        ("S3 chance at 50", f"{n['s3_at_50']:.1%} by 50"),
        ("third split row",
         f"& {n['heldout_b_instances']} & {n['heldout_b_covered']:.1%} & "
         f"{n['heldout_b_blind']:.1%} & {n['heldout_b_blind_strict']:.1%}"),
        ("third split false alarms", f"{n['heldout_b_false_alarm']:.1%}"),
        ("pooled clean arm", f"& {n['pooled_clean_n']} & {n['pooled_clean_k']} & "
                             f"{n['pooled_false_alarm']:.1%}"),
        ("pooled CI", f"95\\% CI [{n['pooled_ci_lo']:.1%}, {n['pooled_ci_hi']:.1%}]"),
        ("blind arm, all splits", f"{n['all_blind']:.1%} of {n['all_blind_n']}"),
        ("S3 predicted for the corpus", f"{n['s3_predicted_for_corpus']:.1%}"),
        ("judge agreement", f"{n['judge_agreement']:.1%} agreement"),
        ("judge human baseline",
         r"Humans manage \textbf{" + f"{n['judge_human_baseline']:.1%}" + "}"),
        ("judge scored n", f"{n['judge_scored_n']:,}".replace(",", "{,}") + " comparisons"),
        ("redux flawed items", f"annotates {n['redux_flawed']} flawed items"),
        ("redux reachable share", f"{n['redux_reachable_share']:.1%} reachable"),
        ("all-splits clean arm",
         f"all {n['all_clean_n']} clean instances in all five splits, every one of "
         f"the {n['all_clean_k']} false alarms is S3"),
        ("all-splits blind arm", f"{n['all_blind']:.1%} of {n['all_blind_n']}"),
        ("all-splits false alarms", f"{n['all_false_alarm']:.1%} clean-arm"),
        ("shape split row",
         f"& {n['shapes_instances']} & {n['shapes_covered']:.1%} & "
         f"{n['shapes_blind']:.1%} & {n['shapes_blind_strict']:.1%}"),
        ("shape split false alarms", f"{n['shapes_false_alarm']:.1%}"),
        ("shape covered in the abstract",
         f"the covered arm drops to {n['shapes_covered']:.0%}"),
        ("asset split row",
         f"& {n['assets_instances']} & {n['assets_covered']:.1%} & "
         f"{n['assets_blind']:.1%} & {n['assets_blind_strict']:.1%}"),
        ("asset split false alarms", f"{n['assets_false_alarm']:.1%}"),
    ]


def either_form(n: dict) -> list[tuple[str, list[str]]]:
    """Quantities the paper may state as a digit OR as a word."""
    return [
        ("blind-spot classes", [f"{f} classes have no" for f in forms(n["corpus_blind"])]
                               + [f"{f} defect classes our battery has no"
                                  for f in forms(n["corpus_blind"])]),
        ("uncovered arm named in the abstract",
         [f"{f} defect classes our battery has no check for" for f in forms(n["corpus_blind"])]),
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="fail if main.tex disagrees")
    args = ap.parse_args()

    require_fetched()
    live = gather()
    if not args.check:
        print(json.dumps(live, indent=2))
        return 0

    # THE PAPER IS FROZEN. Its numbers were measured at one commit and it is not
    # edited to chase the repository afterwards, so checking it against a LIVE
    # repo would fail on the next benchmark added and invite exactly the edit
    # the freeze exists to prevent. `frozen.json` is that commit's measurement.
    # Drift against it is reported as information, never as an error, because
    # the repository moving on is the expected outcome and not a defect.
    frozen_path = HERE / "frozen.json"
    n = live
    drift: list[str] = []
    if frozen_path.is_file():
        n = json.loads(frozen_path.read_text(encoding="utf-8"))
        drift = [f"{k}: paper {n[k]}, repo now {live[k]}"
                 for k in sorted(n) if k in live and n[k] != live[k]]

    # Same reason as selfcheck.py: the preprint's source is distributed by
    # arXiv, not by this repository, so --check is the one mode a fresh clone
    # cannot run. Plain `numbers.py` re-derives and prints every quantity, which
    # is what a reader checking the paper's numbers actually needs.
    tex_path = HERE / "main.tex"
    if not tex_path.is_file():
        print("cannot --check: main.tex is not in this repository.\n\n"
              "  The preprint's LaTeX source is distributed by arXiv. Download the\n"
              "  e-print source, put main.tex beside this file, and re-run.\n\n"
              "  To just re-derive the numbers, run this script with no flags.",
              file=sys.stderr)
        return 3
    tex = tex_path.read_text(encoding="utf-8")
    flat = flatten(tex)
    missing = []
    for label, needle in expectations(n):
        if needle is None:
            continue
        if flatten(needle) not in flat:
            missing.append(f"{label}: main.tex does not state {needle!r}")
    for label, options in either_form(n):
        if not any(flatten(o) in flat for o in options):
            missing.append(f"{label}: main.tex states none of {options!r}")

    # Any percentage in the paper that looks like one of ours but is not the
    # current value. Catches a stale headline that the positive checks above
    # would miss because the sentence was reworded.
    current = {f"{v:.1%}" for k, v in n.items() if isinstance(v, float)}
    plausible = set(re.findall(r"\b(\d{1,3}\.\d)\\%", tex))
    known = {p.rstrip("%") for p in current} | {
        # ciFAIR sweep rows and the pooled clean-arm rate. A value NOT in this
        # set is either stale or undocumented, and both need fixing.
        "10.8", "28.1", "52.6", "45.0", "25.0", "5.0", "0.0", "100.0",
        "8.6", "4.9", "8.0", "15.7",
        # The SIMULATED S3 rates. The paper quotes the analytic ones (now
        # derived above, so they arrive via `current`) and gives these once, in
        # the parenthesis that exists to explain the difference between them.
        "16.3", "8.7",
        # HISTORICAL, and unrecomputable on purpose: S6's recall on the asset
        # split BEFORE D-053 was fixed. The repository now scores 100% there, so
        # no artifact in it can produce this number, and that is precisely why
        # the paper states it -- the paragraph is about a hole that a fixed tool
        # cannot demonstrate. Pinned here so it cannot drift silently.
        "88.9",
        # Also historical: the covered-arm figure on the split that found the
        # loader hole, before it was fixed. The split is spent and the fixed
        # tool scores 100%, so nothing in the repository can reproduce it.
        "99.1",
        # Annotator unanimity. Quoted once, in the sentence explaining that it
        # is the wrong baseline and that reaching for it first was the error.
        "59.8"}
    stray = sorted(p for p in plausible if p not in known)
    if stray:
        missing.append(f"unrecognised percentages in main.tex: {stray}. Either they are stale "
                       f"or numbers.py does not know about them yet; both need fixing.")

    if missing:
        print("the paper and its frozen measurement disagree:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        return 1
    print(f"main.tex agrees with its frozen measurement at v{n['version']} "
          f"({len(expectations(n))} quantities checked)")
    if drift:
        print(f"\n  the repository has moved on in {len(drift)} quantity/quantities "
              f"since the freeze. This is expected and is NOT an error; the paper "
              f"reports v{n['version']}, engine {n['engine16']}.")
        for d in drift[:12]:
            print(f"    {d}")
        if len(drift) > 12:
            print(f"    ... and {len(drift) - 12} more")
    return 0


if __name__ == "__main__":
    sys.exit(main())
