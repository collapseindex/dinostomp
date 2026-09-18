"""Calibration of a reported probability: does confidence mean what it says?

A one-pass model (a decisions model like Jev, a cross-encoder chooser, a
loglikelihood ranker) answers with a probability per option rather than with
text. That vector is evidence text never carries: it says how sure the model
was, so it can be checked against how often it was right. Two questions,
because they fail independently:

  * calibration: when the model says 0.9, is it right about 90% of the time?
    Expected calibration error (Naeini et al. 2015; Guo et al. 2017), the
    confidence-weighted gap between stated confidence and observed accuracy.
    A sharp, well-ordered model can still fail this by being uniformly too
    sure, which temperature scaling fixes without moving one answer.
  * discrimination: are the right answers the confident ones at all? The
    probability that a random pass outranks a random fail on confidence,
    which is the AUROC, which is the Mann-Whitney U divided by its maximum.
    A model can be perfectly calibrated in aggregate and carry no information
    per item; that model's confidence is not worth acting on.

WHERE THE VECTOR LIVES. A record carries it as one trajectory step whose
`result` is a JSON object with a `distribution` mapping every option to a
probability. The jev provider writes that step (`decisions.choice`) and so
does any python target that scores a menu; nothing else on the record is
inspected. `probability_vector` is the one reader of that convention.
"""

from __future__ import annotations

import json
import math

ECE_BINS = 10
# Accuracy-when-acting at these confidence floors. Reported, never gated.
COVERAGE_THRESHOLDS = (0.5, 0.7, 0.8, 0.9, 0.95)
# A distribution is a distribution when it sums to one within this.
MASS_TOLERANCE = 0.02


def probability_vector(record: dict) -> dict[str, float] | None:
    """The per-option probabilities a record carries, or None.

    Reads the first trajectory step whose result is a JSON object with a
    `distribution` of numbers that sum to one. Anything else (a tool log, a
    truncated result, a vector over the wrong keys) is not a vector, and the
    record is treated as carrying none rather than as a malformed one: the
    trajectory shape checks own well-formedness.
    """
    for step in record.get("trajectory") or ():
        if not isinstance(step, dict) or step.get("result_truncated"):
            continue
        try:
            result = json.loads(step.get("result") or "")
        except (TypeError, ValueError):
            continue
        dist = result.get("distribution") if isinstance(result, dict) else None
        if not isinstance(dist, dict) or not dist:
            continue
        try:
            vector = {str(k): float(v) for k, v in dist.items()}
        except (TypeError, ValueError):
            continue
        if any(v < 0 or v != v for v in vector.values()):
            continue
        if abs(sum(vector.values()) - 1.0) > MASS_TOLERANCE:
            continue
        return vector
    return None


def confidence_points(records: list[dict]) -> list[tuple[float, bool]]:
    """(confidence in the answer given, was it right) for every checkable
    record whose vector covers the answer it gave.

    Confidence is the probability the model put on ITS OWN answer, which is
    the number a caller acting on that answer would read. A record whose
    output is not a key of its vector says nothing about calibration and is
    dropped rather than guessed at.
    """
    out = []
    for r in records:
        verdict = (r.get("score") or {}).get("verdict")
        if verdict not in ("pass", "fail", "flag"):
            continue
        vector = probability_vector(r)
        if vector is None:
            continue
        answer = str(r.get("output") if r.get("output") is not None else "")
        if answer not in vector:
            continue
        out.append((vector[answer], verdict == "pass"))
    return out


def expected_calibration_error(points: list[tuple[float, bool]], bins: int = ECE_BINS) -> float:
    """Confidence-weighted mean |accuracy - confidence| over equal-width bins."""
    if not points:
        return 0.0
    buckets: list[list[tuple[float, bool]]] = [[] for _ in range(bins)]
    for conf, ok in points:
        buckets[min(bins - 1, int(conf * bins))].append((conf, ok))
    n = len(points)
    return sum(len(b) / n * abs(sum(c for c, _ in b) / len(b) - sum(ok for _, ok in b) / len(b))
               for b in buckets if b)


def coverage_table(points: list[tuple[float, bool]]) -> dict[str, dict[str, float | None]]:
    """Share of records the model would act on at each confidence floor, and
    its accuracy on those. The operating curve a deployer actually chooses from."""
    n = len(points)
    table = {}
    for t in COVERAGE_THRESHOLDS:
        kept = [ok for conf, ok in points if conf >= t]
        table[f"{t:.2f}"] = {"coverage": round(len(kept) / n, 4) if n else 0.0,
                             "accuracy": round(sum(kept) / len(kept), 4) if kept else None}
    return table


def auroc(points: list[tuple[float, bool]]) -> tuple[float, float] | None:
    """(AUROC, z against 0.5) of confidence as a ranker of right over wrong.

    Mann-Whitney U with tie handling, normal approximation for the z-score;
    None when either class is empty, since a ranking needs both. The z is
    what a caller compares to its noise bar, so a 0.55 at n=30 and a 0.55 at
    n=3,000 are told apart.
    """
    passes = sorted(c for c, ok in points if ok)
    fails = sorted(c for c, ok in points if not ok)
    n1, n0 = len(passes), len(fails)
    if n1 == 0 or n0 == 0:
        return None
    # U = number of (pass, fail) pairs where the pass is more confident, ties half.
    u = 0.0
    j_lt = j_le = 0
    for c in passes:
        while j_lt < n0 and fails[j_lt] < c:
            j_lt += 1
        while j_le < n0 and fails[j_le] <= c:
            j_le += 1
        u += j_lt + 0.5 * (j_le - j_lt)
    area = u / (n1 * n0)
    sigma = math.sqrt(n1 * n0 * (n1 + n0 + 1) / 12.0)
    z = (u - n1 * n0 / 2.0) / sigma if sigma > 0 else 0.0
    return area, z
