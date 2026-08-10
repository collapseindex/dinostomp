"""Score S15's near-duplicate detector against a human annotation.

    python benchmarks/cifair/compare.py            # recall at the shipped threshold
    python benchmarks/cifair/compare.py --sweep    # recall and cost across thresholds

THE QUESTION. Barz & Denzler annotated, by hand, every CIFAR-10 test image with
a near-duplicate in the training set. That is an answer key for a defect class
S15 claims to detect, written by people who had never heard of this tool. So:
of the duplicates a human found, how many does the battery find?

This is the second entry of its kind. The first (N-012, F-018) scored the data
checks against MMLU-Redux and produced the least flattering number in the ledger
along with two items Redux's own annotators had marked `ok`. The point of doing
it again in a different modality is that a recall figure measured once is a fact
about one dataset.

WHAT IS BEING SCORED. `dinostomp.perceptual.dhash_image` and
`near_duplicate_pairs`, imported and called, not reimplemented here. A benchmark
that scores a copy of the algorithm scores nothing.

THE DENOMINATOR, and it is a judgment call worth stating. The annotation carries
three codes. `1` (249 pairs) means the same camera shot, differently
post-processed: a genuine duplicate, and what recall is computed against. `2`
(37 pairs) means the contents are DIFFERENT but highly similar, which is not a
duplicate at all, so counting a miss there as a failure would punish the
detector for being right. Those 37 are reported separately and never folded into
the headline. There are no `0` (exact) pairs in CIFAR-10 train-to-test at all,
which is itself the important fact: not one of these is byte-identical, so hash
equality finds ZERO of them and only a perceptual comparison can see any.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "src"))

from dinostomp import perceptual  # noqa: E402

sys.path.insert(0, str(HERE))
from fetch import load_annotation, load_cifar  # noqa: E402

# Capped at 8. Beyond that the bucketed search's slices get narrow enough that
# the buckets hold thousands of images each and the comparison count runs into
# the billions, which is a fact about this implementation and not an argument
# that looser thresholds are uninteresting.
SWEEP = [0, 2, 3, 4, 5, 6, 7, 8]


def hash_all(images: list[bytes]) -> list[int | None]:
    """dHash every image, through the same path the battery uses."""
    from PIL import Image

    out = []
    for raw in images:
        out.append(perceptual.dhash_image(Image.frombytes("RGB", (32, 32), raw)))
    return out


def recall_at(pairs, train_h, test_h, bits: int) -> tuple[int, int]:
    """(detected, total) over the annotated pairs at this threshold."""
    hit = 0
    total = 0
    for p in pairs:
        a, b = test_h[p["test"]], train_h[p["train"]]
        if a is None or b is None:
            continue
        total += 1
        if perceptual.distance(a, b) <= bits:
            hit += 1
    return hit, total


def classify_flagged(pairs, annotation) -> tuple[int, int, int]:
    """(exact edge annotated, cluster-internal, outside the annotation entirely).

    The distinction is the difference between a result and an overclaim. Three
    flagged pairs on the pod looked at first like duplicates ciFAIR had missed;
    all six images turned out to be annotated, each linked to a DIFFERENT member
    of its own cluster. ciFAIR publishes pairs, not cliques, so an extra edge
    inside a cluster it already found is not a discovery.

    Only the third bucket could contain anything new, and nothing in it counts
    until a human has looked at the images.
    """
    edges = {(p["test"], p["train"]) for p in annotation}
    tests = {p["test"] for p in annotation}
    trains = {p["train"] for p in annotation}
    exact = internal = outside = 0
    for a, b, _ in pairs:
        ai, bi = int(a[1:]), int(b[1:])
        t, r = (ai, bi) if a[0] == "t" else (bi, ai)
        if (t, r) in edges:
            exact += 1
        elif t in tests and r in trains:
            internal += 1
        else:
            outside += 1
    return exact, internal, outside


def cross_split_costs(train_h, test_h, thresholds: list[int]) -> dict[int, int]:
    """{threshold: test-to-train pairs flagged} over the whole 60,000 images.

    The cost side. Recall alone would recommend a threshold of 64, where
    everything is a duplicate of everything and the check is useless.

    Searched ONCE at the largest threshold and counted down, rather than once
    per threshold. The search returns every pair with its distance, so smaller
    thresholds are a filter on the same result, and re-running it nine times
    would have been the same answer for nine times the work: at the loosest
    setting the buckets are wide enough that the comparison count grows into
    the billions.
    """
    combined = {}
    for i, h in enumerate(test_h):
        if h is not None:
            combined[f"t{i}"] = h
    for i, h in enumerate(train_h):
        if h is not None:
            combined[f"r{i}"] = h
    widest = max(thresholds)
    pairs = perceptual.near_duplicate_pairs(combined, max_bits=widest)
    cross = [(a, b, d) for a, b, d in pairs if a[0] != b[0]]
    cross_split_costs.pairs = cross
    return {t: sum(1 for _, _, d in cross if d <= t) for t in thresholds}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sweep", action="store_true",
                    help="recall and flagged-pair count across candidate thresholds")
    args = ap.parse_args()

    if not perceptual.available():
        raise SystemExit(perceptual.missing_reason())

    annotation = load_annotation()
    real = [p for p in annotation if p["judgment"] in (0, 1)]
    similar = [p for p in annotation if p["judgment"] == 2]
    print(f"annotation: {len(annotation)} pairs "
          f"({len(real)} genuine duplicates, {len(similar)} 'very similar', "
          f"{sum(1 for p in annotation if p['judgment'] == 0)} byte-exact)")

    train_x, _, test_x, _ = load_cifar()
    print(f"hashing {len(train_x) + len(test_x)} images ...")
    train_h, test_h = hash_all(train_x), hash_all(test_x)
    undecodable = sum(1 for h in train_h + test_h if h is None)
    if undecodable:
        print(f"  {undecodable} image(s) did not decode")

    shipped = perceptual.NEAR_DUP_BITS
    rows = SWEEP if args.sweep else [shipped]
    print("searching all 60,000 images for near-duplicate pairs ...")
    costs = cross_split_costs(train_h, test_h, rows)
    print()
    print(f"{'bits':>5}  {'recall on genuine duplicates':>30}  "
          f"{'also on very-similar':>21}  {'test/train pairs flagged':>25}")
    for bits in rows:
        hit, total = recall_at(real, train_h, test_h, bits)
        s_hit, s_total = recall_at(similar, train_h, test_h, bits)
        mark = "  <- shipped" if bits == shipped else ""
        print(f"{bits:>5}  {f'{hit}/{total} = {hit / total:.1%}':>30}  "
              f"{f'{s_hit}/{s_total}':>21}  {costs[bits]:>25}{mark}")

    at_shipped = [p for p in cross_split_costs.pairs if p[2] <= shipped]
    exact, internal, outside = classify_flagged(at_shipped, annotation)
    print()
    print(f"Of the {len(at_shipped)} test/train pairs flagged at {shipped} bits:")
    print(f"  {exact:>4} are an edge ciFAIR annotated")
    print(f"  {internal:>4} link two images ciFAIR annotated as duplicates, by an edge it did "
          f"not list (it publishes pairs, not cliques)")
    print(f"  {outside:>4} involve at least one image ciFAIR never annotated. Only these could "
          f"contain something new, and none of them is a finding until a human looks.")

    hit, total = recall_at(real, train_h, test_h, shipped)
    print()
    print(f"At the shipped threshold of {shipped} bits, S15 recovers {hit} of {total} "
          f"duplicates a human found ({hit / total:.1%}).")
    print("Every one of these is byte-DIFFERENT, so S1, S7 and S14 find none of them: "
          "the comparison is between a perceptual check and nothing at all.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
