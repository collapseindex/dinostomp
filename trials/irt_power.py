"""Should dinostomp add an IRT check? Measured answer: no.

    python trials/irt_power.py

WHY THIS EXISTS. The battery scores 0% on the blind-spot classes, and the two
biggest are `wrong-key` and `multiple-correct`. Item response theory is what the
literature reaches for there: Land & Bikel report 95% precision in their top 200
flagged examples using 114 models, Truong et al. up to 84% across nine
benchmarks. The obvious upgrade is to fit a 2PL and flag negative
discrimination.

Before building it, the question worth asking is not "does IRT work" but "does
IRT beat the point-biserial this repo ALREADY ships, at the fleet sizes a
practitioner has". This measures that, and the answer is no in every world
tried.

THE BASELINE IS THE REAL ONE. `point_biserials` is imported from
`dinostomp.psychometrics`, not reimplemented, for the same reason the ciFAIR and
MT-Bench comparisons import the real checks: a benchmark that scores a
reimplementation is measuring the benchmark.

TWO IRT VARIANTS, because a negative result about a bad fit is worth nothing.
The naive fit estimates ability and difficulty once. The refit variant
re-estimates the ability scale after dropping suspects, since an inverted key
corrupts both the abilities and its own difficulty: an easy item everyone
"fails" looks hard, and the slope is then measured against a corrupted scale.

FOUR WORLDS, from friendliest-to-correlation to hardest:
  * clean 2PL, keys fully inverted
  * plus a 0.25 guessing floor (four-option multiple choice)
  * plus two latent skills instead of one
  * plus partial key errors, where the key points at a strong distractor so a
    capable solver is usually but not always marked wrong

WHAT THIS DOES NOT SHOW. It does not contradict Land & Bikel, who never claimed
IRT beats point-biserial; they claimed IRT finds real mislabels at high
precision, on real data, with 114 models and expert review. Both can be true.
Nor does it rule out a better IRT: this is joint maximum likelihood in pure
Python, without marginal ML, priors, or an estimated guessing parameter. What it
does show is that the specific upgrade proposed for THIS battery does not pay,
which is enough to not build it.
"""

from __future__ import annotations

import math
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dinostomp.psychometrics import point_biserials  # noqa: E402

N_ITEMS = 200
INVERT_SHARE = 0.10
TRIALS = 30
GUESS = 0.25
N_DIMS = 2
PARTIAL_ERROR_RATE = 0.75
FLEET_SIZES = (6, 20, 40, 80)


def _sig(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))


def simulate(n_models, rng, guessing=False, multidim=False, partial=False):
    """A response matrix with a known set of inverted answer keys."""
    dims = N_DIMS if multidim else 1
    theta = [[rng.gauss(0, 1) for _ in range(dims)] for _ in range(n_models)]
    diff = [rng.gauss(0, 1) for _ in range(N_ITEMS)]
    disc = [rng.uniform(0.6, 2.0) for _ in range(N_ITEMS)]
    load = [rng.randrange(dims) for _ in range(N_ITEMS)]
    inverted = set(rng.sample(range(N_ITEMS), int(N_ITEMS * INVERT_SHARE)))
    c = GUESS if guessing else 0.0

    matrix = {}
    for m in range(n_models):
        row = {}
        for i in range(N_ITEMS):
            p = c + (1 - c) * _sig(disc[i] * (theta[m][load[i]] - diff[i]))
            ok = 1 if rng.random() < p else 0
            if i in inverted:
                if partial:
                    ok = (1 - ok) if rng.random() < PARTIAL_ERROR_RATE else ok
                else:
                    ok = 1 - ok
            row[f"i{i:03d}"] = ok
        matrix[f"m{m:02d}"] = row
    return matrix, {f"i{i:03d}" for i in inverted}


def rasch_theta(matrix, items, iters=40):
    """Joint ML ability and difficulty under a Rasch model (slope fixed at 1)."""
    models = sorted(matrix)
    b = {i: 0.0 for i in items}
    th = {m: 0.0 for m in models}
    for _ in range(iters):
        for m in models:
            num = den = 0.0
            for i in items:
                p = _sig(th[m] - b[i])
                num += matrix[m][i] - p
                den += p * (1 - p)
            if den > 1e-9:
                th[m] += max(-1.0, min(1.0, num / den))
        for i in items:
            num = den = 0.0
            for m in models:
                p = _sig(th[m] - b[i])
                num += matrix[m][i] - p
                den += p * (1 - p)
            if den > 1e-9:
                b[i] -= max(-1.0, min(1.0, num / den))
        centre = statistics.fmean(b.values())
        for i in items:
            b[i] -= centre
    return th, b


def _slopes(matrix, items, th, b):
    """Per-item discrimination. Negative means the item anti-correlates with skill."""
    models = sorted(matrix)
    out = {}
    for i in items:
        a = 1.0
        for _ in range(25):
            num = den = 0.0
            for m in models:
                p = _sig(a * (th[m] - b[i]))
                d = th[m] - b[i]
                num += (matrix[m][i] - p) * d
                den += p * (1 - p) * d * d
            if den < 1e-9:
                break
            a = max(-4.0, min(4.0, a + max(-1.0, min(1.0, num / den))))
        out[i] = a
    return out


def _difficulty_on_scale(matrix, item, th):
    models = sorted(matrix)
    x = 0.0
    for _ in range(30):
        num = den = 0.0
        for m in models:
            p = _sig(th[m] - x)
            num += matrix[m][item] - p
            den += p * (1 - p)
        if den < 1e-9:
            break
        x -= max(-1.0, min(1.0, num / den))
    return x


def irt_refit(matrix, items, rounds=3):
    """2PL slopes with the ability scale re-estimated after dropping suspects."""
    n_bad = max(1, int(len(items) * INVERT_SHARE))
    suspect: set = set()
    disc: dict = {}
    for _ in range(rounds):
        keep = [i for i in items if i not in suspect] or list(items)
        th, b_keep = rasch_theta(matrix, keep)
        b = dict(b_keep)
        for i in items:
            if i not in b:
                b[i] = _difficulty_on_scale(matrix, i, th)
        disc = _slopes(matrix, items, th, b)
        suspect = set(sorted(items, key=lambda i: disc[i])[:n_bad])
    return disc


def precision_at_k(ranked, truth, k):
    return len(set(ranked[:k]) & truth) / k if k else 0.0


def _world(label, **kw):
    print(f"\n  {label}")
    print(f"  {'fleet':>6} {'point-biserial':>16} {'2PL IRT':>10} {'delta':>8}")
    rows = []
    for n_models in FLEET_SIZES:
        pb_s, rf_s = [], []
        for t in range(TRIALS):
            rng = random.Random(7000 * n_models + t)
            matrix, truth = simulate(n_models, rng, **kw)
            items = sorted(next(iter(matrix.values())))
            k = len(truth)
            rpb = point_biserials(matrix)
            pb_s.append(precision_at_k(
                sorted(items, key=lambda i: (rpb[i] if rpb[i] is not None else 9)),
                truth, k))
            d = irt_refit(matrix, items)
            rf_s.append(precision_at_k(sorted(items, key=lambda i: d[i]), truth, k))
        pb, rf = statistics.fmean(pb_s), statistics.fmean(rf_s)
        rows.append((n_models, pb, rf))
        print(f"  {n_models:>6} {pb:>15.1%} {rf:>9.1%} {rf - pb:>+8.1%}")
    return rows


def main() -> int:
    print(f"  {N_ITEMS} items, {int(N_ITEMS * INVERT_SHARE)} keys inverted, "
          f"{TRIALS} trials per cell")
    print("  precision@k, k = the number of truly inverted keys")
    worlds = [
        ("clean 2PL, full inversion", {}),
        ("+ guessing floor 0.25", {"guessing": True}),
        ("+ two latent skills", {"guessing": True, "multidim": True}),
        ("+ partial key errors", {"guessing": True, "multidim": True, "partial": True}),
    ]
    best = -1.0
    for label, kw in worlds:
        for _n, pb, rf in _world(label, **kw):
            best = max(best, rf - pb)
    print(f"\n  best IRT advantage in any world at any fleet size: {best:+.1%}")
    print("  VERDICT: no IRT check. The shipped point-biserial is not beaten.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
