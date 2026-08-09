"""Typed claims: executable specifications of required evidence.

A prose entitled_claim is a promise the reader must interpret. A typed claim
compiles into concrete evidence requirements the battery checks off:

    claims:
      - {type: accuracy, model: dry-alpha, min: 0.80, confidence: 0.95}
      - {type: superiority, better: dry-alpha, worse: dry-charlie,
         min_effect: 0.20, confidence: 0.95}

The accuracy claim requires a complete run, enough checkable evidence, and
the confidence interval's LOWER bound clearing the declared minimum (a point
estimate above the bar with an interval straddling it is not entitlement).
The superiority claim requires complete runs for both models, enough paired
items, and a seeded paired bootstrap in which the gap clears min_effect in
at least the declared fraction of resamples.

C1 gates on these. Rationale for gating a statistical procedure, recorded:
the spec chose its own bar by declaring the claim; failing a self-chosen bar
has no legitimate explanation, unlike the advisory diagnostics whose
thresholds are ours.

Honest scope, stated for the paper as much as for the reader: C1 verifies
that declared evidence bars are met ON THIS DATA. It is confirmation on the
generating sample, not an independent test; nothing distinguishes a claim
written before the run from one written after (editing claims does break the
drift boundary and forces a re-run, which re-samples responses for
stochastic providers over the same seeded items, but reproduces dry runs
bit-for-bit: provenance hygiene, not statistical pre-registration). No
multiplicity correction is applied across claims; the C1 detail line says so
whenever more than one claim is declared. The confirmation convention for a
strong claim is a second run under a different run.seed.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from dinostomp.psychometrics import BOOTSTRAP_TRIALS, MIN_EVIDENCE, common_items, content_seed, wilson_ci
from dinostomp.runner import summarize

Z_BY_CONFIDENCE = {0.90: 1.6449, 0.95: 1.9600, 0.99: 2.5758}


@dataclass
class Requirement:
    name: str
    ok: bool
    detail: str

    def to_dict(self) -> dict:
        return {"name": self.name, "ok": self.ok, "detail": self.detail}


@dataclass
class ClaimResult:
    description: str
    supported: bool
    requirements: list[Requirement] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"description": self.description, "supported": self.supported,
                "requirements": [r.to_dict() for r in self.requirements]}


def describe(claim: dict) -> str:
    if claim["type"] == "accuracy":
        base = f"accuracy of {claim['model']}"
        if "min" in claim:
            base += f" is at least {claim['min']:.0%}"
        return base + f" ({claim.get('confidence', 0.95):.0%} confidence)"
    return (f"{claim['better']} beats {claim['worse']} by at least "
            f"{claim.get('min_effect', 0.0):.0%} ({claim.get('confidence', 0.95):.0%} confidence)")


def _pooled_records(mine: list[dict]) -> dict[str, list[dict]]:
    pools: dict[str, list[dict]] = {}
    for entry in mine:
        m = entry["manifest"]
        if m is None:
            continue
        pools.setdefault(str(m.get("model")), []).extend(entry["records"])
    return pools


def _complete_models(mine: list[dict]) -> set[str]:
    return {str(e["manifest"].get("model")) for e in mine
            if e["manifest"] and e["manifest"].get("status") == "complete"}


def _accuracy_requirements(claim: dict, model: str, pools, complete) -> list[Requirement]:
    reqs = [Requirement("complete run on disk", model in complete,
                        f"{model}: {'complete' if model in complete else 'no complete run'}")]
    records = pools.get(model, [])
    summary = summarize(records) if records else None
    n = summary["n_checkable"] if summary else 0
    reqs.append(Requirement("enough checkable evidence", n >= MIN_EVIDENCE,
                            f"{n} checkable unit(s); need {MIN_EVIDENCE}"))
    if "min" in claim and summary and n:
        z = Z_BY_CONFIDENCE.get(claim.get("confidence", 0.95))
        if z is None:  # schema enum should prevent this; fail the claim, never crash
            reqs.append(Requirement("supported confidence level", False,
                                    f"confidence {claim.get('confidence')!r} has no z-value"))
            return reqs
        passes = summary.get("n_passes", 0)
        ci = wilson_ci(passes, n, z=z)
        low = ci[0] if ci else 0.0
        reqs.append(Requirement(
            "interval lower bound clears the declared minimum",
            low >= claim["min"],
            f"lower bound {low:.1%} vs declared minimum {claim['min']:.0%}"))
    elif "min" in claim:
        reqs.append(Requirement("interval lower bound clears the declared minimum", False,
                                "no evidence to compute an interval from"))
    return reqs


def _superiority_requirements(claim: dict, matrix: dict, complete, seed: int) -> list[Requirement]:
    better, worse = claim["better"], claim["worse"]
    min_effect = float(claim.get("min_effect", 0.0))
    confidence = float(claim.get("confidence", 0.95))
    reqs = [Requirement("complete runs for both models",
                        better in complete and worse in complete,
                        f"{better}: {'ok' if better in complete else 'missing'}; "
                        f"{worse}: {'ok' if worse in complete else 'missing'}")]
    if better not in matrix or worse not in matrix:
        reqs.append(Requirement("paired observations", False, "one or both models absent from the matrix"))
        return reqs
    pair = {better: matrix[better], worse: matrix[worse]}
    common = common_items(pair)
    reqs.append(Requirement("paired observations", len(common) >= MIN_EVIDENCE,
                            f"{len(common)} common item(s); need {MIN_EVIDENCE}"))
    if len(common) < MIN_EVIDENCE:
        return reqs
    rng = random.Random(content_seed(pair, seed))
    n = len(common)
    cleared = 0
    for _ in range(BOOTSTRAP_TRIALS):
        sample = [common[rng.randrange(n)] for _ in range(n)]
        gap = (sum(matrix[better][i] for i in sample) - sum(matrix[worse][i] for i in sample)) / n
        if gap >= min_effect:
            cleared += 1
    frac = cleared / BOOTSTRAP_TRIALS
    reqs.append(Requirement(
        "paired bootstrap clears min_effect at the declared confidence",
        frac >= confidence,
        f"gap >= {min_effect:.0%} in {frac:.0%} of {BOOTSTRAP_TRIALS} resamples; need {confidence:.0%}"))
    return reqs


def evaluate_claims(spec: dict, mine: list[dict], matrix: dict) -> list[ClaimResult]:
    """Compile and evaluate every typed claim against the pod's real runs."""
    pools = _pooled_records(mine)
    complete = _complete_models(mine)
    seed = int(spec["run"]["seed"])
    model_names = [mc["model"] for mc in spec["models"]]
    results = []
    for claim in spec.get("claims") or []:
        if claim["type"] == "accuracy":
            targets = model_names if claim["model"] == "each" else [claim["model"]]
            for model in targets:
                reqs = _accuracy_requirements({**claim, "model": model}, model, pools, complete)
                results.append(ClaimResult(describe({**claim, "model": model}),
                                           all(r.ok for r in reqs), reqs))
        else:
            reqs = _superiority_requirements(claim, matrix, complete, seed)
            results.append(ClaimResult(describe(claim), all(r.ok for r in reqs), reqs))
    return results
