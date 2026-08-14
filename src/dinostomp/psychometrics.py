"""Fleet psychometrics over the response matrix.

Judge-free by construction: models are examinees, never judges. When a fleet
answers the same items, item statistics expose problems no single run can
see: an item that strong models miss and weak models hit is a candidate key
error (negative point-biserial), an item everyone gets right or everyone
gets wrong measures nothing (dead weight), and score totals that do not
separate the fleet are unreliable (KR-20). No model is ever asked whether an
answer key is correct; the correlations do the inference.

Matrix shape: {model: {item_id: 0 or 1}}.
"""

from __future__ import annotations

import hashlib
import json
import random
from statistics import fmean, pvariance

Matrix = dict[str, dict[str, int]]

# Two-sided alpha=0.05 and 80% power, the conventional pair.
Z_ALPHA = 1.9600
Z_POWER = 0.8416

# Single sources of truth, referenced by the lint THRESHOLDS table and by
# claims.py (which cannot import lint without a cycle).
BOOTSTRAP_TRIALS = 400
MIN_EVIDENCE = 20  # checkable units below this cannot entitle or diagnose anything

# P13: how far observed single-axis concentration must clear the fixed-margins
# null before it counts as specialisation. A diagnostic that fires on a hair
# above the 95th percentile cries wolf on the last unidimensional fleet; the
# margin is what buys a clean false-alarm rate on a six-model fleet. Single
# source, referenced by the lint THRESHOLDS table.
DIMENSION_MARGIN = 0.10


def content_seed(matrix: "Matrix", base_seed: int) -> int:
    """Bootstrap RNG seed derived from the DATA plus the run seed, so a
    borderline result cannot be seed-shopped: changing the seed changes the
    item selection and therefore the matrix, which changes this hash too."""
    payload = json.dumps({m: sorted(matrix[m].items()) for m in sorted(matrix)}, sort_keys=True)
    return int(hashlib.sha256(f"{base_seed}|{payload}".encode()).hexdigest()[:16], 16)


def n_for_effect(gap: float) -> int:
    """Items needed to detect an accuracy gap at 80% power, two-sided 0.05,
    unpaired worst case p=0.5. Inverse of min_detectable_effect."""
    return int(round(((Z_ALPHA + Z_POWER) ** 2 * 0.5) / max(gap, 1e-9) ** 2))


def majority(votes: list[int]) -> int | None:
    """The item-majority outcome over repeats: 1, 0, or None for a TIE.

    Defined once and imported by both consumers, because the summary and the
    fleet matrix disagreeing about what a repeated item scored would be a parity
    break in the one number everybody reads.

    A tie is `None`, not `0`, and that distinction is the point. With an EVEN
    `run.repeats`, scoring ties as failures does not add noise, it reports a
    different quantity: at repeats=2 a model whose true per-item rate is p
    scores p squared, so a genuinely 50% model reports 25% behind a confidence
    interval that excludes the truth. Measured rather than derived; see N-008 in
    FINDINGS.md. Callers decide what an undecided item means. The summary calls
    it `uncheckable`, which is the treatment every other "the instrument did not
    reach a verdict" case already gets here.
    """
    if not votes:
        return None
    if 2 * sum(votes) > len(votes):
        return 1
    if 2 * sum(votes) < len(votes):
        return 0
    return None


def common_items(matrix: Matrix) -> list[str]:
    """Item ids answered by every model in the matrix."""
    sets = [set(d) for d in matrix.values()]
    return sorted(set.intersection(*sets)) if sets else []


def kr20(matrix: Matrix) -> float | None:
    """Kuder-Richardson 20 reliability of fleet score totals.

    None when undefined: fewer than 2 items or models, or zero variance in
    totals (a fleet the test cannot separate has no measurable reliability).
    """
    models = sorted(matrix)
    items = common_items(matrix)
    k = len(items)
    if k < 2 or len(models) < 2:
        return None
    totals = [sum(matrix[m][i] for i in items) for m in models]
    var = pvariance(totals)
    if var == 0:
        return None
    pq = 0.0
    for i in items:
        p = fmean(matrix[m][i] for m in models)
        pq += p * (1.0 - p)
    return (k / (k - 1.0)) * (1.0 - pq / var)


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 3:
        return None
    mx, my = fmean(xs), fmean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return sxy / (sxx * syy) ** 0.5


def point_biserials(matrix: Matrix) -> dict[str, float | None]:
    """Per item: correlation between getting it right and the rest-score.

    Rest-score (total minus this item) avoids the self-correlation inflation
    of naive item-total correlation. None for degenerate items (everyone
    right, everyone wrong, or no rest-score spread).
    """
    models = sorted(matrix)
    items = common_items(matrix)
    totals = {m: sum(matrix[m][i] for i in items) for m in models}
    out: dict[str, float | None] = {}
    for i in items:
        xs = [float(matrix[m][i]) for m in models]
        rest = [float(totals[m] - matrix[m][i]) for m in models]
        out[i] = _pearson(xs, rest)
    return out


def wilson_ci(k: int, n: int, z: float = Z_ALPHA) -> tuple[float, float] | None:
    """Wilson score interval for a binomial proportion. None when n == 0.

    Every reported accuracy carries one of these: a point estimate on 24
    items is a shrug, not a measurement.
    """
    if n == 0:
        return None
    p = k / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    half = z * ((p * (1 - p) / n + z2 / (4 * n * n)) ** 0.5) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def min_detectable_effect(n: int) -> float | None:
    """Smallest accuracy gap between two models detectable on n items at
    80% power, two-sided alpha 0.05, worst case p=0.5. Pure arithmetic;
    printed next to every report so nobody claims a 3-point win on 24 items.
    """
    if n <= 0:
        return None
    return (Z_ALPHA + Z_POWER) * ((2 * 0.25 / n) ** 0.5)


def bootstrap_rank_stability(matrix: Matrix, seed: int, trials: int = BOOTSTRAP_TRIALS) -> list[tuple[str, str, float]]:
    """Paired item bootstrap over the common items: for each adjacent pair in
    the observed ranking, the fraction of resamples in which the order flips
    or ties. Paired resampling is far tighter than comparing two independent
    intervals, because every model is scored on the same resampled items.

    Deterministic for a given seed. Returns [(better, worse, flip_rate)].
    """
    models = sorted(matrix)
    items = common_items(matrix)
    if len(models) < 2 or not items:
        return []
    n = len(items)
    observed = sorted(((sum(matrix[m][i] for i in items) / n, m) for m in models), reverse=True)
    order = [m for _, m in observed]
    pairs = list(zip(order, order[1:]))
    flips = dict.fromkeys(pairs, 0)
    rng = random.Random(content_seed(matrix, seed))
    for _ in range(trials):
        sample = [items[rng.randrange(n)] for _ in range(n)]
        acc = {m: sum(matrix[m][i] for i in sample) for m in models}
        for a, b in pairs:
            if acc[a] <= acc[b]:
                flips[(a, b)] += 1
    return [(a, b, flips[(a, b)] / trials) for a, b in pairs]


def dead_items(matrix: Matrix) -> tuple[list[str], list[str]]:
    """(all_right, all_wrong): items that separate nobody."""
    models = sorted(matrix)
    items = common_items(matrix)
    all_right = [i for i in items if all(matrix[m][i] == 1 for m in models)]
    all_wrong = [i for i in items if all(matrix[m][i] == 0 for m in models)]
    return all_right, all_wrong


def _swap_null_matrices(matrix: Matrix, trials: int, seed: int):
    """Yield `trials` matrices from the fixed-margins null.

    Every model keeps its exact score and every item its exact difficulty; the
    only thing destroyed is WHICH model got which item. That is sampled by swap
    randomisation: find a 2x2 checkerboard and flip it, the one move that
    changes the matrix without moving any margin. The chain PERSISTS across
    trials, so only the first sample needs full mixing; after that a lighter
    shuffle between samples is enough, and the difference is a trial suite that
    runs in 10s instead of 29s.

    Fixed seed: a lint that returns a different verdict on a second run is not a
    lint. Shared by P2 (negative_rpb_null) and P13 (dimensionality_null) so the
    one null both lean on is defined once.
    """
    rng = random.Random(seed)
    models = sorted(matrix)
    items = common_items(matrix)
    if len(models) < 2 or len(items) < 2:
        return
    grid = [[int(matrix[m][i]) for i in items] for m in models]
    n_rows, n_cols = len(grid), len(grid[0])
    burn_in = max(500, 8 * n_rows * n_cols)
    between = max(100, n_rows * n_cols)
    for t in range(trials):
        for _ in range(burn_in if t == 0 else between):
            r1, r2 = rng.randrange(n_rows), rng.randrange(n_rows)
            c1, c2 = rng.randrange(n_cols), rng.randrange(n_cols)
            if r1 == r2 or c1 == c2:
                continue
            a, b, c, d = grid[r1][c1], grid[r1][c2], grid[r2][c1], grid[r2][c2]
            if a == d and b == c and a != b:      # the checkerboard
                grid[r1][c1], grid[r1][c2] = b, a
                grid[r2][c1], grid[r2][c2] = d, c
        yield {m: {i: grid[ri][ci] for ci, i in enumerate(items)}
               for ri, m in enumerate(models)}


def negative_rpb_null(matrix: Matrix, threshold: float, trials: int, seed: int = 20260809) -> int:
    """The 95th-percentile count of negative point-biserials under the null.

    P2's raw count means nothing without one. With four examinees a
    point-biserial can take only a handful of values, and an item that just the
    weakest model happened to get is strongly negative by construction. On a
    real 4-model GSM8K fleet P2 called 31 of 303 items candidate key errors.

    Choosing the null is the whole problem, and two obvious ones are both wrong:

      - redraw each model's outcomes from its overall accuracy: preserves fleet
        skill, DESTROYS item difficulty, expects 65 on that GSM8K fleet. Too
        permissive; it hides five inverted keys.
      - permute which models passed each item: preserves item difficulty,
        DESTROYS fleet skill, expects 114. Worse, and for the opposite reason.

    The null that answers the actual question holds BOTH margins fixed (see
    `_swap_null_matrices`), so every model keeps its exact score and every item
    keeps its exact difficulty, and the only thing destroyed is which model got
    which item.
    """
    if len(matrix) < 2 or len(common_items(matrix)) < 2:
        return 0
    counts = [sum(1 for v in point_biserials(fake).values()
                  if v is not None and v <= threshold)
              for fake in _swap_null_matrices(matrix, trials, seed)]
    counts.sort()
    return counts[min(len(counts) - 1, int(0.95 * len(counts)))]


def _top_eigenvalue(cov: list[list[float]], iters: int = 300) -> float:
    """Largest eigenvalue of a small symmetric PSD matrix, by power iteration.

    Deterministic: a fixed, non-degenerate start vector (never the all-ones
    direction, which is this matrix's structural zero eigenvector), so the lint
    cannot return two answers. Only the value is needed, for a variance share,
    not the vector; the Rayleigh quotient reads it off the converged iterate.
    """
    n = len(cov)
    v = [1.0 / (i + 2) for i in range(n)]
    for _ in range(iters):
        w = [sum(cov[i][j] * v[j] for j in range(n)) for i in range(n)]
        norm = sum(x * x for x in w) ** 0.5
        if norm == 0:
            return 0.0
        v = [x / norm for x in w]
    cv = [sum(cov[i][j] * v[j] for j in range(n)) for i in range(n)]
    return sum(v[i] * cv[i] for i in range(n))


def concentration(matrix: Matrix) -> float | None:
    """Share of fleet-differentiation variance on the single dominant axis.

    Item-centre the response matrix (removing item difficulty), form the
    model-by-model covariance of the residuals, and return lambda1 / trace. On
    its own the number means little: strong single-factor skill and strong
    specialisation both raise it. It becomes a reading only against the
    fixed-margins null (`dimensionality_null`), which preserves each model's
    skill and each item's difficulty. Structure the margins DETERMINE (a
    unidimensional skill axis) survives into the null and cancels; structure
    the margins do NOT determine (a coherent item cluster only one subgroup
    solves) does not, and shows up as concentration in excess of the null. That
    excess is the construct-validity signal: the aggregate score is blending
    abilities that rank the fleet differently.

    None when it cannot be formed: fewer than 3 models, fewer than 2 common
    items, or a fleet with no differentiation at all (identical rows).
    """
    models = sorted(matrix)
    items = common_items(matrix)
    k, n = len(models), len(items)
    if k < 3 or n < 2:
        return None
    col_mean = {i: fmean(matrix[m][i] for m in models) for i in items}
    resid = [[matrix[m][i] - col_mean[i] for i in items] for m in models]
    cov = [[sum(resid[a][t] * resid[b][t] for t in range(n)) / n for b in range(k)]
           for a in range(k)]
    trace = sum(cov[a][a] for a in range(k))
    if trace <= 1e-12:
        return None
    return _top_eigenvalue(cov) / trace


def _item_correlations(matrix: Matrix, items: list[str]) -> dict[tuple[str, str], float]:
    """Every pair of items, correlated across the fleet. Computed once so the
    permutation null re-partitions the same numbers instead of recomputing
    them per shuffle (the difference between a fast check and an O(n^2 * trials)
    one)."""
    models = sorted(matrix)
    cols = {i: [float(matrix[m][i]) for m in models] for i in items}
    corr: dict[tuple[str, str], float] = {}
    for a in range(len(items)):
        for b in range(a + 1, len(items)):
            r = _pearson(cols[items[a]], cols[items[b]])
            if r is not None:
                corr[(items[a], items[b])] = r
    return corr


def _separation(corr: dict[tuple[str, str], float], label_of: dict[str, str]) -> float | None:
    """Mean within-subskill item correlation minus mean across-subskill."""
    within, across = [], []
    for (i, j), r in corr.items():
        (within if label_of[i] == label_of[j] else across).append(r)
    if not within or not across:
        return None
    return fmean(within) - fmean(across)


def subskill_discriminability(matrix: Matrix, labels: dict[str, str],
                              trials: int = BOOTSTRAP_TRIALS,
                              seed: int = 20260809) -> tuple[float, float] | None:
    """(observed separation, label-permutation null 95th percentile), or None.

    The judge-free discriminant-validity question: do items sharing a declared
    subskill cohere more than items from different subskills? Observed
    separation ABOVE the null means the declared subskills carve the response
    space (they measure distinct things); at or below it, they do not, and a
    per-subskill leaderboard is reporting redundant scores. Never says what any
    subskill IS; only whether the declared partition shows up in the responses.

    None when it cannot be formed: fewer than 2 common labelled items, fewer
    than 2 distinct subskills, or a degenerate correlation structure.
    """
    items = sorted(set(common_items(matrix)) & set(labels))
    if len(items) < 2:
        return None
    label_of = {i: labels[i] for i in items}
    if len(set(label_of.values())) < 2:
        return None
    corr = _item_correlations(matrix, items)
    observed = _separation(corr, label_of)
    if observed is None:
        return None
    labs = [label_of[i] for i in items]
    rng = random.Random(seed)
    vals = []
    for _ in range(trials):
        shuffled = labs[:]
        rng.shuffle(shuffled)
        v = _separation(corr, dict(zip(items, shuffled)))
        if v is not None:
            vals.append(v)
    if not vals:
        return None
    vals.sort()
    null_95 = vals[min(len(vals) - 1, int(0.95 * len(vals)))]
    return observed, null_95


def dimensionality_null(matrix: Matrix, trials: int, seed: int = 20260809) -> float | None:
    """95th-percentile concentration under the fixed-margins null.

    A real fleet always has SOME single-axis dominance by chance; this is how
    much, when the only structure present is each model's skill and each item's
    difficulty. Observed concentration above this (by the P13 margin) is a
    coherent item cluster the margins do not explain. None if the null cannot be
    built.
    """
    vals = [c for c in (concentration(fake) for fake in _swap_null_matrices(matrix, trials, seed))
            if c is not None]
    if not vals:
        return None
    vals.sort()
    return vals[min(len(vals) - 1, int(0.95 * len(vals)))]
