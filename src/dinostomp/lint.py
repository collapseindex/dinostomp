"""The stomp battery: checks over a spec, its dataset, and its runs.

Two layers of verification:

  INPUTS  - the drift boundary: spec, data, and scorer code are hashed into
            every manifest; any post-run edit is a gated finding.
  RESULTS - nothing downstream of the run is trusted either: witnesses are
            replayed, recorded verdicts are re-scored against the current
            scorer, summaries are recomputed from records, records are
            attributed through their manifests, and the seeded item
            selection is re-derived and compared against the ledger.

Reporter discipline:

  - every check reports how many units it examined; a pass that examined
    zero units is recorded as a skip, never a pass
  - checks that do not apply to this eval leave the coverage denominator
    as n/a; the report still states how many of the full battery applied
  - the verdict is coverage-honest: `clean` requires zero gated findings
    AND every applicable check ran
"""

from __future__ import annotations

import json
import math
import unicodedata
from itertools import combinations
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

import dinostomp
from dinostomp.claims import evaluate_claims
from dinostomp.items import load_items
from dinostomp.providers import ProviderError
from dinostomp.judging import PERTURBATIONS, REPEAT_TAG, family_of, judge_family
from dinostomp.mutation import run_gauntlet, run_shape_gauntlet
from dinostomp.overlap import find_overlap, load_reference
from dinostomp.psychometrics import (
    negative_rpb_null,
    BOOTSTRAP_TRIALS,
    MIN_EVIDENCE,
    bootstrap_rank_stability,
    common_items,
    dead_items,
    kr20,
    majority,
    min_detectable_effect,
    point_biserials,
)
from dinostomp.runner import (CHARS_PER_TOKEN_EST, judge_entrypoint, mount_hashes,
                              select_items, summarize, target_entrypoint)
from dinostomp.scorers import make_scorer, run_witnesses
from dinostomp.evidence import missing_for, skip_reason, survey
from dinostomp.extensions import discover, run_extensions
from dinostomp.dataset import (DATA_SUFFIXES, build_items, infer_mapping,
                               leak_candidates, looks_like_dataset, read_rows,
                               repair_items, sniff_separator, target_is_classlike,
                               unrepairable_findings)
from dinostomp import modality, perceptual, results as results_mod
from dinostomp.fingerprint import engine_fingerprint
from dinostomp.spec import Issue, jsonl_lines, load_spec, spec_sha256, validate_obj

# (id, display name, gating).
#
# The constitutional line: GATING checks establish deterministic facts
# (a duplicate exists, a hash changed, a ledger does not re-derive) and break
# the verdict. Non-gating checks are DIAGNOSTICS: statistical inference over
# thresholds (bias margins, reliability, discrimination). Diagnostics warn,
# expose their underlying values, and never pretend a heuristic is a proof.
CHECKS: list[tuple[str, str, bool, str]] = [
    ("S1", "questions are unique", True, "always"),
    ("S2", "no answer leaks into its own question", True,
     "free-form items (non-numeric, outside a forced choice) and multiple-choice stems"),
    ("S3", "gold answer does not favour an option position", False, "20+ keyed choice items"),
    ("S4", "gold answer is not systematically the longest option", False, "20+ keyed choice items"),
    ("S5", "no option offered twice in one item", True, "choice items present"),
    ("S6", "every target is among its choices", True, "choice items present"),
    ("S7", "no identical question with contradictory targets", True, "always"),
    ("S8", "a contamination canary travels with the data", False, "jsonl data"),
    ("S9", "no surface feature predicts the gold answer", False, "20+ keyed choice items"),
    ("S10", "no model reproduces the contamination canary", False, "canary probe on disk"),
    ("S11", "no item already appears in a reference dataset", False,
     "a reference corpus supplied with --against"),
    ("S12", "every referenced asset resolves and still hashes the same", True,
     "items carrying input_ref"),
    ("S13", "no asset's own path gives away its label", True, "items carrying input_ref"),
    ("S14", "no asset appears in two splits", True, "input_ref items declaring a split"),
    ("S15", "no near-duplicate assets", False, "input_ref images, with the vision extra installed"),
    ("S16", "the eval is not authored in a circle", False, "a provenance block is declared"),
    ("S17", "no single column all but determines the target", False,
     "a raw dataset audit with a class-like target and feature columns"),
    ("S18", "no two options are the same number written differently", False,
     "choice items whose options include two or more numbers"),
    ("S19", "no two items are the same question in different encodings", False,
     "two or more items carrying a textual question"),
    ("W1", "witnesses kill the mutant scorers", False, "always"),
    ("W2", "a correct answer survives its surface form", False,
     "a scorer that accepts a constructible baseline form"),
    ("W3", "a graded scorer witnesses its gradation", True,
     "a scorer that emits intermediate partial credit on its witnesses"),
    ("C1", "every typed claim's evidence requirements hold", True, "typed claims declared"),
    ("R1", "runs match the spec, data, and scorer on disk (no drift)", True, "runs on disk"),
    ("R2", "the witness gate replays clean", True, "always"),
    ("R3", "ledger spend agrees with the manifest and the spec cap", True, "runs on disk"),
    ("R4", "every run record is schema-valid, unique, and its manifest's own", True, "runs on disk"),
    ("R5", "truncated outputs are never credited", True, "runs on disk"),
    ("R6", "uncheckable rate is sane", False, "runs on disk"),
    ("R7", "accuracy is distinguishable from guessing", False, "20+ checkable records per model"),
    ("R8", "recorded verdicts re-score identically", True, "runs on disk"),
    ("R9", "summaries match their run records", True, "runs on disk"),
    ("R10", "runs cover the spec's declared scope, nothing foreign", False, "runs on disk"),
    ("R11", "records cover exactly the seeded selection", True, "runs on disk"),
    ("R12", "no model selectively escapes the scorer", False, "2+ models on disk"),
    ("R13", "the eval is not solvable blind", False, "blind probe runs from a real provider"),
    ("R14", "no model collapses onto one answer", False, "20+ checkable records per model"),
    ("R15", "each model beats its own blind baseline", False, "blind probe plus real runs"),
    ("R16", "failed answers do not contain the reference", False, "5+ failed records per model"),
    ("R17", "every model produced something scoreable", True, "runs on disk"),
    ("R18", "billed output tokens match the recorded text", False, "20+ records with usage"),
    ("R19", "the runs were produced by this engine", False, "runs recording a tool_sha256"),
    ("R20", "repeated items reached a verdict", False, "runs with run.repeats > 1"),
    ("R21", "graded scores stay in range", True, "records carrying a graded value"),
    ("R22", "no failed answer numerically equals its target", False,
     "failed records whose target is a number"),
    ("T1", "no forbidden tool is called", True, "forbidden_tools declared"),
    ("T2", "every required tool is actually called", True, "required_tools declared"),
    ("T3", "trajectories are well-formed", True, "python-target runs on disk"),
    ("T4", "passing answers are grounded in tool evidence", False, "trajectories carrying tool results"),
    ("T5", "no model under-reports its trajectory", False, "2+ python-target models on disk"),
    ("T6", "tool calls are not redundant", False, "python-target runs on disk"),
    ("T7", "passing answers CHANGE when their evidence is withheld", False,
     "a mediated agent plus an ablation probe"),
    ("T8", "the trajectory was observed, not self-reported", False, "target runs on disk"),
    ("J1", "the judge agrees with cases whose answer is known", False, "judge probe on disk"),
    ("J2", "the judge is invariant to content-free perturbations", False, "judge probe on disk"),
    ("J3", "the judge agrees with itself on identical input", False, "judge probe on disk"),
    ("J4", "the judge does not favour its own family", False, "cross-judge probe on disk"),
    ("P1", "fleet score totals are reliable (KR-20)", False, "4+ models, 5+ common items"),
    ("P2", "no item anti-correlates with fleet skill", False, "4+ models, 5+ common items"),
    ("P3", "dead-weight items stay a minority", False, "4+ models, 5+ common items"),
    ("P4", "every model was asked the same items", True, "2+ models on disk"),
    ("P5", "no unanimous identical wrong answers", False, "3+ models on disk"),
    ("P6", "entitled ordering claims are separated beyond sampling noise", False, "entitled ordering claim"),
    ("P7", "the fleet is not pinned at a ceiling or floor", False, "2+ models on disk"),
    ("P8", "the eval separates the fleet (dynamic range)", False, "2+ models on disk"),
    ("P9", "answers survive re-ordering the options", False, "shuffle probe plus real runs"),
    ("P10", "the number survives changing the seed", False, "run.seeds declared"),
    ("P11", "the number survives re-phrasing the instruction", False, "template probe on disk"),
    ("P12", "the fleet ORDERING survives re-phrasing the instruction", False,
     "template probe plus 2+ models"),
]
GATING = {cid: hard for cid, _, hard, _ in CHECKS}
NAMES = {cid: name for cid, name, _, _ in CHECKS}

# Single source of truth for every threshold the battery uses.
THRESHOLDS = {
    "position_margin": 0.20,   # gold-position share above expectation that trips S3
    "length_margin": 0.10,     # strictly-longest share above expectation that trips S4
    "uncheckable_warn": 0.20,  # share of uncheckable records that trips R6
    "guess_margin": 0.10,      # accuracy above chance required to beat R7
    "min_choice_items": 20,    # S3/S4/S9 need at least this many keyed choice items
    "min_checkable": MIN_EVIDENCE,   # R7/R13/C1 need at least this many scored units
    "min_leak_len": 2,         # S2 ignores 1-char targets (too many false hits)
    "near_dup_bits": 5,        # S15: dHash Hamming distance counting as a near-duplicate
    "kr20_min": 0.50,          # P1 warns below this reliability
    "negative_discrimination": -0.20,  # P2 flags items at or below this r_pb
    "dead_weight_max": 0.50,   # P3 warns when more than half the items separate nobody
    "min_fleet": 4,            # P1/P2/P3 need at least this many models
    # Below this many examinees P2's fixed-margins null is nearly degenerate and
    # the check has little power. Measured, not guessed: 0/5 detections at 6
    # examinees, 5/5 at 40, with no false alarms at any size.
    "min_fleet_discrimination": 12,
    "min_fleet_agree": 3,      # P5 needs at least this many models
    "min_items_psycho": 5,     # P1/P2/P3 need at least this many common items
    "spend_tolerance_usd": 1e-6,  # rounding slack when re-summing ledgers
    "candidate_list_min": 3,   # S2: this many OTHER answer-space values in a question = candidate list, not a leak
    "ordering_flip_rate": 0.05,   # P6: adjacent pair flips in more than this share of resamples = within noise
    "bootstrap_trials": BOOTSTRAP_TRIALS,   # P6 paired bootstrap resamples
    "ceiling_acc": 0.90,          # P7: whole fleet at or above this = saturated
    "floor_acc": 0.10,            # P7: whole fleet at or below this = broken or impossibly hard
    "min_dynamic_range": 0.10,    # P8: fleet spread below this separates nobody
    "escape_margin": 0.10,        # R12: uncheckable rate this far above the fleet median = escaping
    "escape_min_rate": 0.05,      # R12: and at least this absolute rate, so tiny fleets don't false-fire
    "shortcut_z": 3.0,            # S9: z-score vs the per-item 1/k null required to call a shortcut
    "shortcut_lift": 0.10,        # S9: and at least this absolute lift over the null mean
    "target_leak_nmi": 0.50,      # S17: normalized MI of a single column with the target, above which it is a candidate leak
    "collapse_margin": 0.30,      # R14: modal-answer share this far above the key's own modal share
    "blind_lift_min": 0.10,       # R15: informed accuracy must clear a model's OWN blind score by this
    "collapse_exclude_share": 0.95,  # psychometrics drop a model only when it is THIS constant
    "seed_spread_min": 0.05,      # P10: spread below this is not worth reporting even if significant
    "min_billed_chars": 40,       # R18: shorter outputs make chars/4 too noisy to bill against
    "billing_ratio_max": 3.0,     # R18: billed output tokens vs what the text accounts for
    "order_swing_min": 0.05,
    # P11: an accuracy move under a re-phrased instruction below this is not
    # worth reporting even when it clears the noise band.
    "template_swing_min": 0.05,      # P9: swing below this is not worth reporting even if significant
    # How many standard errors a move has to clear before it is called a move
    # rather than the sample. A FIXED percentage cannot do this job: 10 points
    # at n=120 is inside the noise band, and at n=5000 it is far outside it, so
    # one constant is simultaneously too loud and too quiet. Found when P10 was
    # about to warn on a spread of 1.7 SE on the first real benchmark this tool
    # was ever pointed at.
    "noise_z": 1.96,
    "contains_target_max": 0.25,  # R16: share of a model's FAILED answers containing the reference
    "min_scored_misses": 5,       # R16: failed records a model needs before its misses are judged
    "ungrounded_max": 0.10,       # T4: share of one model's PASSING answers absent from its own tool results
    "min_grounding_evidence": 5,  # T4: passing records a model needs before its grounding is judged
    "underreport_ratio": 0.50,    # T5: mean steps below this fraction of the fleet median = under-reporting
    "redundant_call_max": 0.25,   # T6: share of trajectories repeating an identical call
    "judge_agreement_min": 0.90,  # J1: agreement with construction-known verdicts below this warns
    "self_preference_max": 0.10,  # J4: own-family generosity gap vs a second judge
    "judge_inconsistency_max": 0.05,  # J3: self-disagreement rate on byte-identical input
}

TRUNCATION_REASONS = {"length", "max_tokens", "max_output_tokens"}

# A denied mention is not a mention: a scorer that fails "not 46" is correct.
NEGATORS = {"not", "no", "never", "isn't", "rather", "instead", "unlikely", "hardly"}

# A purely numeric target, and a question that offers alternatives.
NUMERIC_RE = re.compile(r"-?\d+(?:[.,]\d+)*")

# Single-token number words S18 recognises. Kept to single tokens on purpose: a
# compound like "twelve hundred" needs a grammar, and the risk of a grammar is
# parsing something that was never meant as a number. "dozen"/"score" are common
# enough in option lists to earn a place; anything ambiguous stays unparsed.
_NUM_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
    "hundred": 100, "thousand": 1000, "million": 1_000_000, "dozen": 12,
}


def _as_number(text) -> float | None:
    """The numeric VALUE of an option string, or None if it is not cleanly one.

    Conservative on purpose: it recognises plain integers and decimals, thousands
    separators (1,000), a trailing percent (50% -> 0.5), a simple integer
    fraction (1/2 -> 0.5), and a single number word (twelve -> 12). Anything else,
    a formula, a genotype, a range, a compound phrase, returns None and is never
    compared, because a false "same number" on a gating-adjacent finding is the
    flattering direction this project refuses.
    """
    s = str(text).strip().lower()
    if not s:
        return None
    if s in _NUM_WORDS:
        return float(_NUM_WORDS[s])
    percent = s.endswith("%")
    if percent:
        s = s[:-1].strip()
    # A simple integer fraction, but not if it is really a date or a path.
    m = re.fullmatch(r"(-?\d+)\s*/\s*(\d+)", s)
    if m and int(m.group(2)) != 0:
        val = int(m.group(1)) / int(m.group(2))
        return val / 100 if percent else val
    # Thousands separators: commas between groups of digits. Reject anything with
    # a stray comma that is not a clean separator so "1,2,3" (a list) stays None.
    if re.fullmatch(r"-?\d{1,3}(?:,\d{3})+(?:\.\d+)?", s):
        s = s.replace(",", "")
    try:
        val = float(s)
    except ValueError:
        return None
    return val / 100 if percent else val
DISJUNCTION_RE = re.compile(r"\s+or\s+")
# How close to the "or" a target has to sit to count as one of the alternatives
# on offer. Wide enough for a real disjunct ("Have Christians or Jews won..."),
# narrow enough that an unrelated "or" elsewhere in a long question exempts
# nothing.
OFFER_WINDOW_CHARS = 60

# Stable, human-readable names for every check.
#
# The ids stay the primary key: they are short, they sort, and every trial and
# threshold is keyed on them. But `S1` in a finding makes a reader go look
# something up, and that cost lands hardest on the LLM-authoring loop, where a
# model correcting a spec against "dup-questions: 90 duplicated" needs no table
# in its context and a model reading "S1 fail" needs the whole registry.
#
# These are an API. Renaming one breaks anybody's `--only` flag and any saved
# report, so a rename is a breaking change and gets a MAJOR bump.
SLUGS = {
    "S1": "dup-questions", "S2": "answer-leak", "S3": "position-bias",
    "S4": "length-bias", "S5": "dup-options", "S6": "target-not-offered",
    "S7": "conflicting-keys", "S8": "canary-present", "S9": "surface-shortcut",
    "S10": "canary-regurgitated", "S11": "corpus-overlap",
    "S12": "asset-drift", "S13": "label-in-path", "S14": "split-leak",
    "S15": "near-dup-assets", "S16": "authorship-circularity", "S17": "target-leak",
    "S18": "numeric-dup-options", "S19": "lookalike-questions",
    "W1": "witness-coverage", "W2": "surface-form", "W3": "graded-witness",
    "C1": "claim-evidence",
    "R1": "input-drift", "R2": "witness-replay", "R3": "spend-ledger",
    "R4": "record-integrity", "R5": "truncation-credit", "R6": "uncheckable-rate",
    "R7": "above-guessing", "R8": "verdict-rederive", "R9": "summary-rederive",
    "R10": "run-scope", "R11": "selection-coverage", "R12": "scorer-escape",
    "R13": "blind-solvable", "R14": "response-collapse", "R15": "input-blind",
    "R16": "scorer-artifact", "R17": "nothing-scoreable", "R18": "billing-mismatch",
    "R19": "engine-drift", "R20": "repeat-ties", "R21": "graded-range",
    "R22": "numeric-miss",
    "T1": "forbidden-tool", "T2": "required-tool", "T3": "trajectory-shape",
    "T4": "answer-grounding", "T5": "trace-underreport", "T6": "redundant-calls",
    "T7": "answer-grounding-causal", "T8": "trace-observed",
    "J1": "judge-agreement", "J2": "judge-bias", "J3": "judge-consistency",
    "J4": "judge-self-preference",
    "P1": "fleet-reliability", "P2": "item-discrimination", "P3": "dead-weight",
    "P4": "matrix-complete", "P5": "unanimous-wrong", "P6": "ordering-noise",
    "P7": "ceiling-floor", "P8": "dynamic-range", "P9": "order-stability",
    "P10": "seed-stability", "P11": "prompt-stability", "P12": "ranking-stability",
}

BY_SLUG = {v: k for k, v in SLUGS.items()}


# Which checks each SCOPE is answerable for. A verdict is only as broad as the
# evidence it was given, and saying so is cheaper than an asterisk.
SCOPE_CHECKS = {
    "data": {"S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S11",
             "S12", "S13", "S14", "S15", "S17", "S18", "S19"},
}
SCOPE_CHECKS["pod"] = {cid for cid, *_ in CHECKS}

SCOPE_BLURB = {
    "data": "the dataset at rest",
    "pod": "the dataset, the scorer, and every run on disk",
}


# Where each threshold's NUMBER came from. A dial at 0.10 and a dial at 1.96 are
# not the same kind of object, and a reader deciding whether to trust a finding
# deserves to know which they are looking at.
#
#   derived     statistical theory fixes it. Changing it means disagreeing with
#               the maths, not with a preference.
#   calibrated  measured on real data in this repo, with the measurement on
#               record in CHANGELOG or FINDINGS.
#   convention  a value the surrounding literature uses. Defensible by citation
#               rather than by derivation.
#   judgment    the author picked it. This is the honest label for "it seemed
#               about right", and it is the largest class, which is itself worth
#               knowing.
#   structural  not a sensitivity dial at all: it changes what an eval IS, or
#               how much compute a probe spends.
THRESHOLD_PROVENANCE = {
    "noise_z": ("derived", "1.96 standard errors is the 95% two-sided normal quantile"),
    "bootstrap_trials": ("structural", "how many resamples a bootstrap draws"),
    "spend_tolerance_usd": ("structural", "floating-point slack on a money comparison"),
    "shortcut_z": ("convention", "3 sigma against the per-item chance null, the usual bar for "
                                 "calling a surface feature real"),
    "target_leak_nmi": ("judgment", "0.5 normalized mutual information: a column that resolves "
                                    "half the target's entropy is worth a human's eye. A candidate, "
                                    "not a verdict; only the author knows if it exists at predict time"),
    "kr20_min": ("convention", "0.5 is the low end of what psychometrics calls usable "
                               "reliability; 0.7+ is the textbook bar and would skip most fleets"),
    "negative_discrimination": ("convention", "item analysis treats r_pb below about -0.2 as a "
                                              "candidate key error"),
    "min_checkable": ("judgment", "20 records before a per-model rate is worth reporting"),
    "min_items_psycho": ("judgment", "5 common items before a matrix means anything"),
    "min_fleet": ("judgment", "4 examinees before fleet statistics are attempted"),
    "min_fleet_agree": ("judgment", "3 models before unanimity is a word worth using"),
    "min_choice_items": ("judgment", "20 keyed choice items before position or length skew"),
    "min_fleet_discrimination": ("calibrated", "measured: 0/5 detections at 6 examinees, 5/5 at "
                                               "40, on 200 items with 10% of keys inverted"),
    "guess_margin": ("calibrated", "found live: a 1B model answering one label constantly sat at "
                                   "exactly chance and pooling hid it"),
    "seed_spread_min": ("judgment", "a practical floor beneath the noise band, so a significant "
                                    "2-point move at huge n is not reported as a finding"),
    "order_swing_min": ("judgment", "same practical floor, for presentation order"),
    "template_swing_min": ("judgment", "same practical floor, for instruction framing"),
    "candidate_list_min": ("judgment", "3 other answer-space values before a question counts as "
                                       "offering a candidate list"),
    "position_margin": ("calibrated", "measured against clean data by dinocorpus: the margin is "
                        "ABSOLUTE and applied to each of k positions with no multiplicity "
                        "correction, so on clean 4-option data a dataset trips S3 by chance 16.3% "
                        "of the time at 20 items, 8.7% at 24, 3.3% at 30 and 0.4% at 50. "
                        "min_choice_items=20 admits the noisiest end of that. Not retuned on one "
                        "measurement; S3 warns and never gates, and the warning now states the "
                        "rate at the size it fired on. Full curve: D-046."),
    "near_dup_bits": ("calibrated", "5 of 64 bits is conventional in the perceptual-hash "
                      "literature, and is now MEASURED against a human annotation: on ciFAIR's "
                      "hand-labelled CIFAR-10 duplicates it recovers 28.1% of them (70 of 249) "
                      "and flags 158 test/train pairs across 60,000 images, while every "
                      "byte-level check recovers 0%. 8 bits nearly doubles recall to 52.6% for "
                      "3.2x the candidates and starts flagging images the annotators judged "
                      "similar but NOT duplicates. The default stays at 5: that curve is one "
                      "dataset of 32x32 photographs, and it is not a licence to reset a default "
                      "for documents or spectrograms. Full curve: N-017, and "
                      "`benchmarks/cifair/compare.py --sweep` re-derives it."),
    "min_leak_len": ("judgment", "2 characters before a target is long enough to 'appear' in a "
                                 "question"),
    "collapse_exclude_share": ("judgment", "95% identical before a model is called constant"),
    "min_billed_chars": ("calibrated", "below 40 characters chars/4 is too noisy to bill against"),
}
# Everything not named above is author judgment, and saying so is the point.
DEFAULT_PROVENANCE = ("judgment", "author judgment; no derivation or calibration on record")


def threshold_provenance(name: str) -> tuple[str, str]:
    return THRESHOLD_PROVENANCE.get(name, DEFAULT_PROVENANCE)


# The field this tool can never fill.
#
# Fifty-four checks sounds comprehensive, and the ways an eval can be invalid
# are unbounded: task selection, ecological validity, distribution mismatch,
# benchmark saturation, contamination nobody can observe, strategic behaviour,
# whether the thing being measured is the thing anyone cares about. A reader who
# sees "54 of 54 ran" will reason "so there probably is not much wrong", and
# that inference is the most dangerous thing this tool could cause.
#
# So the boundary is ARCHITECTURAL rather than rhetorical. Every report carries
# this field, it is a constant, and there is deliberately no code path that can
# set it to anything else. A caveat in a paragraph gets skimmed. A field in the
# artifact that permanently reads NOT ESTABLISHED does not.
CONSTRUCT_VALIDITY = {
    "measures_the_intended_construct": "NOT ESTABLISHED BY DINOSTOMP",
    "why": ("This battery checks mechanical integrity: that the data is not self-incriminating, "
            "the scorer can fail, the runs are honest, the numbers survive noise, and the claims "
            "have their evidence. None of that establishes that the eval measures what its author "
            "means it to measure. A trivial eval, a mis-aimed eval, and a saturated eval can all "
            "pass every check here."),
    "what_would": ("construct validity is argued, not computed: task analysis, comparison against "
                   "an external criterion, and evidence that the score moves with the ability it "
                   "claims to track. No tool can hand you that, and one that implied it could "
                   "would be the worst instrument in this repository."),
}


RUN_CHECK_IDS = ("R1", "R3", "R4", "R5", "R6", "R8", "R9", "R10", "R11", "R12", "R14", "R16", "R17",
                 "R18", "R19", "R20", "R21", "R22")
PSYCHO_CHECK_IDS = ("P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8")
# P9 lives with the probes, not the fleet matrix: it needs a probe run, not more models.
TRAJECTORY_CHECK_IDS = ("T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8")
JUDGE_CHECK_IDS = ("J1", "J2", "J3", "J4")

# entitled_claims phrases that assert one model beats another; P6 only
# applies when the spec actually makes such a claim.
ORDERING_WORDS = ("ordering", "ranking", "rank", "better than", "beats", "outperform")

PERTURBATION_NAMES = [p.name for p in PERTURBATIONS]

SMALL_FLEET = 10  # below this many examinees, reliability estimates get a printed caveat


@dataclass
class Finding:
    id: str
    check: str
    level: str  # pass | fail | warn | skip | n/a
    gating: bool
    detail: str
    witnesses: int = 0
    examples: list[str] = field(default_factory=list)
    evidence: dict = field(default_factory=dict)

    @property
    def slug(self) -> str:
        return SLUGS[self.id]

    def to_dict(self) -> dict:
        out = {
            "id": self.id,
            "slug": self.slug,
            "check": self.check,
            "level": self.level,
            "gating": self.gating,
            "detail": self.detail,
            "witnesses": self.witnesses,
        }
        if self.examples:
            out["examples"] = self.examples[:8]
        if self.evidence:
            out["evidence"] = self.evidence
        return out


class Reporter:
    """Records one Finding per declared check and computes the honest verdict."""

    def __init__(self):
        self.findings: dict[str, Finding] = {}

    def check(self, cid: str, ok: bool, detail: str, n: int, examples: list[str] | None = None,
              evidence: dict | None = None) -> None:
        # A check the evidence contract already disqualified must not be
        # revived by a later pass computing a vacuous pass over zero rows.
        if self.findings.get(cid) is not None and self.findings[cid].level == "skip"                 and self.findings[cid].evidence.get("missing_evidence"):
            return
        if ok and n == 0:
            self.skip(cid, "nothing examined; a zero-witness pass is not a pass")
            return
        gating = GATING[cid]
        level = "pass" if ok else ("fail" if gating else "warn")
        self.findings[cid] = Finding(cid, NAMES[cid], level, gating, detail, n,
                                     list(examples or []), dict(evidence or {}))

    def skip(self, cid: str, reason: str, missing: list | None = None) -> None:
        # A contract skip already named the MISSING FIELD. A later skip from the
        # check's own body describes the consequence of that absence, not its
        # cause, and overwriting loses the only actionable half. R16 shipped this
        # bug: with no `output` anywhere it reported "no model has 5+ failed
        # records to inspect" over 966 failed records, sending a reader off to
        # collect more failures when no number of them would ever have helped.
        prior = self.findings.get(cid)
        if (missing is None and prior is not None and prior.level == "skip"
                and prior.evidence.get("missing_evidence")):
            return
        self.findings[cid] = Finding(cid, NAMES[cid], "skip", GATING[cid], reason,
                                     evidence={"missing_evidence": [n.field for n in missing]}
                                     if missing else {})

    def not_applicable(self, cid: str, reason: str) -> None:
        self.findings[cid] = Finding(cid, NAMES[cid], "n/a", GATING[cid], reason)

    def report(self, target: str, *, inputs: dict | None = None, runs: list[dict] | None = None,
               entitled_claims: list[str] | None = None, power: dict | None = None,
               scope: str = "pod", extensions: list[dict] | None = None,
               loaded_extensions: list | None = None) -> dict:
        # Any declared check never reached is a skip: coverage self-audit.
        for cid, *_ in CHECKS:
            if cid not in self.findings:
                self.skip(cid, "not reached")
        ordered = [self.findings[cid] for cid, *_ in CHECKS]

        n_a = [f for f in ordered if f.level == "n/a"]
        skipped = [f for f in ordered if f.level == "skip"]
        ran = [f for f in ordered if f.level in ("pass", "fail", "warn")]
        fails = sum(1 for f in ordered if f.level == "fail")
        warns = sum(1 for f in ordered if f.level == "warn")

        # SCOPE, not just coverage.
        #
        # `incomplete` is the right default for a pod: the run checks are
        # reachable and simply were not reached, so exiting nonzero is what
        # stops a pipeline accepting thin evidence. It is the WRONG answer for
        # someone who asked to audit a CSV. That audit is structurally
        # incomplete forever, and punishing it teaches people to pass
        # --allow-incomplete by reflex, which is the exact habit the flag
        # exists to prevent. So a data-scoped audit reports at data scope, and
        # says which scope it reported at.
        in_scope_skips = [f for f in skipped if scope == "pod" or f.id in SCOPE_CHECKS[scope]]
        if fails:
            verdict = "broken"
        elif in_scope_skips:
            verdict = "incomplete"
        elif warns:
            verdict = "ok"
        else:
            verdict = "sound"

        # Extensions merge in AFTER the core has decided. Their findings can make
        # a verdict redder and can never make it greener: only findings from
        # VALIDATED extensions affect the verdict at all, and core findings are
        # compared before and after to prove nothing touched them.
        ext_findings = list(extensions or [])
        for f in ext_findings:
            if f["validated"] and f["level"] == "fail":
                fails += 1
                verdict = "broken"
            elif f["validated"] and f["level"] == "warn" and verdict == "sound":
                warns += 1
                verdict = "ok"
            elif f["validated"] and f["level"] == "warn":
                warns += 1
        report = {
            "tool": "dinostomp",
            "version": dinostomp.__version__,
            "target": target,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "thresholds": {k: {"value": float(v), "source": "default",
                               "provenance": threshold_provenance(k)[0],
                               "basis": threshold_provenance(k)[1]}
                           for k, v in THRESHOLDS.items()},
            "coverage": {
                "declared_total": len(CHECKS),
                "declared": len(CHECKS) - len(n_a),
                "ran": len(ran),
                "skipped": [{"id": f.id, "reason": f.detail} for f in skipped],
                "not_applicable": [{"id": f.id, "reason": f.detail} for f in n_a],
            },
            "summary": {"fail": fails, "warn": warns, "skip": len(skipped),
                        "verdict": verdict, "scope": scope},
            # Constant. There is no argument, no flag and no code path that
            # fills this in, and tests/test_construct_validity.py enforces that.
            "construct_validity": dict(CONSTRUCT_VALIDITY),
            "findings": [f.to_dict() for f in ordered],
        }
        if loaded_extensions:
            # The verdict names its inputs. A SOUND produced with extensions
            # loaded is a claim about a specific set of code, or it is not a
            # claim at all.
            report["extensions"] = [e.to_dict() for e in loaded_extensions]
            report["extension_findings"] = ext_findings
            counted = sum(1 for e in loaded_extensions if e.validated)
            report["coverage"]["extensions"] = {
                "loaded": len(loaded_extensions),
                "validated": counted,
                "unvalidated": len(loaded_extensions) - counted,
            }
        if inputs:
            report["inputs"] = inputs
        if runs is not None:
            report["runs"] = runs
        if entitled_claims:
            report["entitled_claims"] = entitled_claims
        if power:
            report["power"] = power
        return report


def _whole_mention(text: str, needle: str) -> int | None:
    """Where `needle` appears in `text` as a WHOLE value, or None.

    Substring matching would make R16 a false-alarm machine on numbers: target
    46 occurs inside 460, 146 and 46.5, none of which is the answer. Digits get
    digit boundaries, words get word boundaries.
    """
    if not needle:
        return None
    if re.fullmatch(r"-?\d+(?:\.\d+)?", needle):
        pattern = rf"(?<![\d.]){re.escape(needle)}(?![\d.]|\d)"
    else:
        pattern = rf"(?<!\w){re.escape(needle)}(?!\w)"
    m = re.search(pattern, text)
    return m.start() if m else None



# Phrases that introduce a value AS THE ANSWER. A number is exempt from the leak
# check unless one of these precedes it: see the note in S2 for why the blanket
# numeric exemption was too wide.
_DISCLOSING = re.compile(
    r"(?:answer|result|total|equals|it is|that is|which is|gives|yields|=)\s*"
    r"(?:is\s*)?[:=]?\s*\$?NUMBER(?![0-9])", re.I)


def _numeric_disclosed(question: str, value: str) -> bool:
    """Is this number introduced as the answer rather than stated as a premise?"""
    pattern = _DISCLOSING.pattern.replace("NUMBER", re.escape(value))
    return re.search(pattern, question, re.I) is not None


def _is_offered_alternative(question: str, targets: set[str]) -> bool:
    """Is the target one side of an "A or B?" the question itself offers?

    A forced-choice question cannot be asked without naming its own answer:
    "Have Christians or Jews won more Nobel Prizes?" has to contain the word
    "Christians". That is format, not leakage.

    Keyed on THIS question's disjuncts rather than the dataset's answer space,
    because the alternatives of a forced choice are usually not targets of any
    other item. The first version of this rule counted global answer-space
    values and exempted nothing on TruthfulQA, where it was needed.

    The target must sit NEXT TO the "or". Splitting the whole question and
    accepting a hit in any segment is the same thing as exempting every
    question containing the word, which on a gating check is an invitation:
    append " or something" to a leaky question and the gate opens.
    """
    for m in DISJUNCTION_RE.finditer(question):
        window = question[max(0, m.start() - OFFER_WINDOW_CHARS):m.end() + OFFER_WINDOW_CHARS]
        if any(t in window for t in targets):
            return True
    return False


def _norm(text) -> str:
    return " ".join(str(text).lower().split())


def _targets_of(item: dict) -> list[str]:
    t = item["target"]
    return [str(x) for x in t] if isinstance(t, list) else [str(t)]


# The cross-script characters that most often stand in for a Latin letter, in
# their casefolded form. This is the small high-value core of the Unicode
# confusables table, not the whole thing: it is what a real contamination or
# obfuscation uses (Cyrillic and Greek that read as Latin), and keeping it small
# keeps a genuine Cyrillic or Greek question from being mangled into a false
# collision. Anything not here survives NFKC and casefolding untouched.
_CONFUSABLES = {
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c",
    "у": "y", "х": "x", "к": "k", "м": "m", "т": "t",
    "в": "b", "н": "h", "і": "i", "ј": "j", "ѕ": "s",
    "ԁ": "d", "ԛ": "q", "ѡ": "w",  # Cyrillic
    "α": "a", "ο": "o", "ρ": "p", "ε": "e", "ν": "v",
    "τ": "t", "χ": "x", "ι": "i", "κ": "k", "μ": "m",
    "υ": "u", "β": "b",  # Greek
}


def _skeleton(text) -> str:
    """A string reduced to what it LOOKS like, for near-duplicate detection.

    NFKC folds compatibility forms (fullwidth, ligatures) and canonical ones
    (NFD's decomposed accents recompose), casefold lowers across scripts, a small
    confusables map turns Cyrillic/Greek lookalikes into Latin, and everything
    that is not a letter or digit is dropped, so a smart quote, a hyphen, or a
    trailing space cannot make two identical questions look distinct. What is
    left is a skeleton: "What's" and "What’s" and "Whаt's" (Cyrillic a) all
    become "whats".
    """
    s = unicodedata.normalize("NFKC", str(text)).casefold()
    s = "".join(_CONFUSABLES.get(ch, ch) for ch in s)
    return "".join(ch for ch in s if ch.isalnum())


def _skeleton_key(item: dict) -> str | None:
    """S19's key: the skeleton of the question plus its option skeletons.

    Mirrors _item_key so a shared MMLU stem over different options is NOT a
    near-duplicate (the options are half the item), and returns None for an item
    with no textual question at all, because near-duplicate ASSETS are S15's job
    and a bare image has no text skeleton to compare.

    An ASSET-backed item is skipped even when it carries a prompt, because its
    identity is the image, not the text: a classification pod asks "what shape is
    in this image?" over and over on different pictures, and those are distinct
    items sharing a stem, not encoding duplicates. Found by the trials specificity
    arm, where the clean image pod tripped a false alarm.
    """
    if modality.ref_of(item):
        return None
    if not isinstance(item.get("input"), str) or not item["input"].strip():
        return None
    parts = [_skeleton(item["input"])]
    choices = item.get("choices")
    if isinstance(choices, list):
        parts.append("|".join(sorted(_skeleton(c) for c in choices)))
    return "||".join(parts)


def _item_key(item: dict) -> str:
    """What makes an item the SAME item.

    For a free-form item that is the question. For a multiple-choice item it is
    the question PLUS its options, because the options are half the question:
    MMLU asks "Which of the following statements is correct?" over and over
    with entirely different option blocks, and those are different items that
    happen to share a stem. Keying on the stem alone called 22 of them
    duplicates and 11 of them contradictory, both on GATING checks.

    Options are compared as a SET. Two items offering the same four options in
    a different order are the same item presented differently, which is what
    S1 is for; P9 is the check that cares about order.

    An ASSET-backed item is identified by its asset's BYTES, and by its prompt
    too when it has one. Both halves matter and dropping either fabricates a
    finding on a gating check:

      * keying on the uri instead of the bytes calls two paths to the same
        photograph two different items, which is the leakage S1 and S7 exist to
        catch.
      * keying on the prompt alone collapses every item behind a shared prompt
        ("What is in this image?") into one duplicate pile, which is a whole
        dataset reported as duplicated. Same shape as D-016 and D-039: an
        assumption about somebody's data, presented as a property of it.
    """
    parts = []
    ref = modality.ref_of(item)
    if ref:
        # The sha256 is the DECLARED one. S12 is what proves the file still
        # matches it, and a pod where S12 fails is already BROKEN before these
        # are read. With no declared hash the uri is all there is, and that is
        # weaker: it is why S12 counts unpinned assets out loud.
        digest = str(ref.get("sha256") or "").lower()
        parts.append(f"asset:{digest}" if digest else f"uri:{_norm(ref['uri'])}")
    if isinstance(item.get("input"), str):
        parts.append(_norm(item["input"]))
    key = " ++ ".join(parts)
    choices = item.get("choices")
    if isinstance(choices, list):
        key += " || " + " | ".join(sorted(_norm(c) for c in choices))
    return key


# --------------------------------------------------------------------------- items


def _duplicate_option_checks(rep: Reporter, choice_items: list[dict]) -> None:
    """S5 and S6: facts about an item's own option list.

    Lifted out of the main flow because they still apply when every item
    shares one label set, unlike position and length bias.
    """
    # S5: same option twice in one item.
    #
    # Exact comparison, PLUS one narrow case-insensitive rule. The history is
    # worth keeping because both halves were measured rather than argued.
    #
    # Naive case-folding was tried first and rejected: MMLU's genetics items
    # offer 'BB Bb' against 'Bb bb' and its predicate-logic items offer
    # 'Sc = Ej' against 'sC = eJ', where the case IS the content. It called four
    # correct items defective.
    #
    # Scoring the check against MMLU-Redux's human annotation (N-012) showed the
    # rejection was costing a real catch: one of those four, the predicate-logic
    # item, is labelled `multiple_correct_answers` by the annotators. So the
    # question was never "fold case or not", it was how to tell the two apart.
    #
    # THE DISCRIMINATOR IS HOW MANY OPTIONS COLLAPSE. Where case carries the
    # content, folding it merges nearly everything: 'BB BB', 'BB Bb', 'Bb Bb',
    # 'Bb bb' become one string, and a four-way collapse means the case is the
    # answer. A genuine duplicate collapses exactly ONE pair. Measured both
    # ways: on the repo's MMLU copy the pair rule flags the true positive and
    # none of the three genetics items; on Redux it keeps every catch the naive
    # version had.
    #
    # Also measured and REJECTED, with their numbers, so the next person does
    # not have to re-derive them: stripping punctuation costs 75 extra false
    # positives on Redux for 2 extra catches (formal logic, where '(F • L) • ~C'
    # and 'F • L • ~C' are different formulas), and substring containment costs
    # 481 for 3.
    def _folded(text) -> str:
        return re.sub(r"\s+", " ", str(text).strip().lower())

    dup_opts, case_only = [], []
    for i in choice_items:
        ch = list(i["choices"])
        if len(set(ch)) < len(ch):
            dup_opts.append(str(i["id"]))
        elif len({_folded(c) for c in ch}) == len(ch) - 1:
            dup_opts.append(str(i["id"]))
            case_only.append(str(i["id"]))
    detail = f"{len(dup_opts)} item(s) offer a duplicate option"
    if case_only:
        detail += (f" ({len(case_only)} differing only in case or spacing, where exactly one "
                   f"pair collapses; a wider collapse is treated as case carrying the content)")
    rep.check("S5", not dup_opts, detail, n=len(choice_items), examples=dup_opts)

    # S6: target among choices
    keyless = [str(i["id"]) for i in choice_items if not any(t in i["choices"] for t in _targets_of(i))]
    rep.check("S6", not keyless, f"{len(keyless)} item(s) whose target is not among their choices",
              n=len(choice_items), examples=keyless)

    # S18: two options that are the SAME NUMBER written differently.
    #
    # S5 above is EXACT (plus a narrow case rule), by a decision it measured:
    # stripping punctuation or folding substrings cost 75 and 481 false positives
    # on MMLU-Redux. Numeric equivalence is the tighter signal those rules were
    # too blunt to reach: it fires ONLY when two option strings both parse as
    # numbers AND those numbers are equal, so a formula ('(F . L)'), a genotype
    # ('BB Bb'), or a chemistry string never trips it, which is exactly what
    # killed the punctuation and substring rules. "1,000" and "1000" are one
    # answer wearing two coats; if one is the key, a model that computes it and
    # picks the other coat is marked wrong while being right (the F-002 failure,
    # reached through arithmetic instead of a repeated string).
    #
    # Diagnostic, not a gate: a notation question ("which is written with a
    # thousands separator?") could legitimately offer 1000 and 1,000 as distinct,
    # so the tool surfaces the pair and the human decides, rather than failing the
    # item. Emphasised louder when one of the pair is the gold, because that is
    # the case that mis-scores.
    numeric_dups = []
    for i in choice_items:
        seen: dict[float, str] = {}
        gold = {str(t) for t in _targets_of(i)}
        for c in i["choices"]:
            val = _as_number(c)
            if val is None:
                continue
            key = round(val, 9)
            prior = seen.get(key)
            if prior is not None and str(c) != prior:
                on_key = str(c) in gold or prior in gold
                numeric_dups.append(
                    f"{i['id']}: {prior!r} and {str(c)!r} are the same number"
                    + (" (one of them is the keyed answer)" if on_key else ""))
                break
            seen.setdefault(key, str(c))
    scanned_numeric = sum(1 for i in choice_items
                          if sum(_as_number(c) is not None for c in i["choices"]) >= 2)
    if not scanned_numeric:
        rep.not_applicable("S18", "no item offers two options that both parse as numbers, so there "
                                  "is no numeric equivalence to check")
    else:
        rep.check("S18", not numeric_dups,
                  f"{len(numeric_dups)} of {scanned_numeric} item(s) with numeric options offer the "
                  f"same number twice in different writing",
                  n=scanned_numeric, examples=numeric_dups)


def _asset_checks(rep: Reporter, items: list[dict], base_dir: Path | None) -> None:
    """S12 to S15: facts about inputs that live in FILES.

    All four are skipped, not passed, on a dataset with no `input_ref`. A text
    eval has no assets to drift, and reporting `pass` on zero assets is the
    zero-witness pass this project treats as a defect everywhere else.
    """
    refs = [i for i in items if modality.ref_of(i)]
    if not refs:
        for cid in ("S12", "S13", "S14", "S15"):
            rep.not_applicable(cid, "no item carries an `input_ref`; nothing points at a file")
        return

    if base_dir is None:
        # A bare `dinostomp stomp data.jsonl` knows where the data file is, so
        # this only happens if a caller forgets to pass it. Skipping loudly
        # beats resolving against the working directory, which would read
        # whatever happened to be there.
        for cid in ("S12", "S13", "S14", "S15"):
            rep.skip(cid, "no pod directory to resolve asset paths against")
        return

    # S12: the assets are there, they are inside the pod, and they still hash
    # to what the dataset says they hash to.
    problems, digests = modality.verify_refs(refs, base_dir)
    unpinned = [str(i["id"]) for i in refs if not modality.ref_of(i).get("sha256")]
    detail = f"{len(problems)} asset(s) missing, unreadable, or changed since the dataset was written"
    if unpinned:
        detail += (f"; {len(unpinned)} of {len(refs)} carry NO sha256, so their bytes are "
                   f"unverifiable and only their presence was checked")
    rep.check("S12", not problems, detail, n=len(refs),
              examples=[f"{p.item_id}: {p.kind}, {p.detail}" for p in problems[:8]],
              evidence={"unpinned": len(unpinned), "assets": len(refs),
                        "by_kind": dict(Counter(p.kind for p in problems))})

    # S13: the label in the asset's own path. Not a defect in the dataset; a
    # defect waiting to happen in any pipeline that shows the model a filename.
    leaks = []
    for item in refs:
        found = modality.path_leaks_label(str(modality.ref_of(item)["uri"]), _targets_of(item))
        if found:
            leaks.append(f"{item['id']}: {modality.ref_of(item)['uri']} contains {found!r}")
    rep.check("S13", not leaks,
              f"{len(leaks)} asset path(s) contain their own answer as a path segment",
              n=len(refs), examples=leaks[:8])

    # S14: the same asset in two splits. This is the leakage form that vision
    # benchmarks actually suffer from, and no text check looks for it because a
    # text pod is one split.
    split_of: dict[str, set] = {}
    for item in refs:
        ref = modality.ref_of(item)
        split = ref.get("split")
        digest = digests.get(str(item["id"])) or str(ref.get("sha256") or "")
        if split and digest:
            split_of.setdefault(digest, set()).add(str(split))
    if not split_of:
        rep.not_applicable("S14", "no asset declares a `split`; there are no splits to leak between")
    else:
        crossers = [d for d, splits in split_of.items() if len(splits) > 1]
        rep.check("S14", not crossers,
                  f"{len(crossers)} asset(s) appear in more than one split",
                  n=len(split_of),
                  examples=[f"{d[:12]}...: {', '.join(sorted(split_of[d]))}" for d in crossers[:8]])

    # S15: near-duplicates. Needs pixels, so needs the optional extra, and says
    # so rather than passing.
    images = [i for i in refs if modality.ref_of(i).get("kind") == "image"]
    if not images:
        rep.not_applicable("S15", "no image assets; near-duplicate detection is image-only")
    elif not perceptual.available():
        rep.skip("S15", perceptual.missing_reason())
    else:
        hashes, undecodable = {}, []
        for item in images:
            path = modality.resolve(str(modality.ref_of(item)["uri"]), base_dir)
            h = perceptual.dhash(path) if path and path.is_file() else None
            if h is None:
                undecodable.append(str(item["id"]))
            else:
                hashes[str(item["id"])] = h
        # Byte-identical pairs are S1's finding, not this one. Reporting them
        # here as well would double-count one defect across two checks and
        # inflate the ledger.
        exact = {}
        for item in images:
            d = digests.get(str(item["id"]))
            if d:
                exact.setdefault(d, []).append(str(item["id"]))
        same_bytes = {tuple(sorted(g)) for g in exact.values() if len(g) > 1}
        pairs = [(a, b, d) for a, b, d in
                 perceptual.near_duplicate_pairs(hashes, int(THRESHOLDS["near_dup_bits"]))
                 if (a, b) not in {p[:2] for p in same_bytes} and tuple(sorted((a, b))) not in same_bytes]
        detail = (f"{len(pairs)} candidate near-duplicate pair(s) at Hamming distance "
                  f"<= {int(THRESHOLDS['near_dup_bits'])} of 64, beyond the byte-identical ones S1 reports")
        if undecodable:
            detail += f"; {len(undecodable)} image(s) did not decode and were not compared"
        rep.check("S15", not pairs, detail, n=len(hashes),
                  examples=[f"{a} ~ {b} ({d} bits)" for a, b, d in pairs[:8]],
                  evidence={"undecodable": len(undecodable), "compared": len(hashes),
                            "max_bits": int(THRESHOLDS["near_dup_bits"])})


def _item_checks(rep: Reporter, items: list[dict], *, tabular: bool = False) -> None:
    # An asset-backed item may carry no inline `input` at all: a classification
    # pod's item IS the image. Those are excluded from the free-form pool rather
    # than defaulted to an empty string, because an empty question makes every
    # such item look identical to every other and S2's answer-space collapses.
    # S13 is the leak check that applies to them.
    text_items = [i for i in items if "choices" not in i and isinstance(i.get("input"), str)]
    choice_items = [i for i in items if "choices" in i]

    # S1: duplicate items (question, plus options when it has them)
    counts = Counter(_item_key(i) for i in items)
    dups = [q for q, c in counts.items() if c > 1]
    rep.check("S1", not dups, f"{len(dups)} duplicated question(s) among {len(items)}",
              n=len(items), examples=[d[:80] for d in dups])

    # S19: items that are the same question wearing a different ENCODING. S1 is
    # exact (casefold plus whitespace), so two copies that differ only by a smart
    # quote, an NFC-vs-NFD accent, or a Cyrillic letter that reads as Latin sail
    # past it as distinct, which is precisely how a padded benchmark or a
    # train/test overlap hides from a dedup pass. S19 groups items by their
    # SKELETON and flags a group whose members are not already exact duplicates,
    # so it reports only what S1 could not see.
    #
    # Diagnostic, not a gate, and for a real reason: a collision after folding
    # confusable characters CAN be legitimate (a question ABOUT Cyrillic, a
    # typography item), so the tool surfaces the group and the author decides,
    # rather than failing an item S1 was right to pass. The MIN_SKELETON guard
    # keeps two short, genuinely different items ("2+2?" / "2-2?") from colliding
    # on a handful of shared letters.
    MIN_SKELETON = 12
    skels: dict[str, list] = {}
    for i in items:
        sk = _skeleton_key(i)
        if sk is not None and len(sk.replace("|", "")) >= MIN_SKELETON:
            skels.setdefault(sk, []).append(i)
    lookalikes = []
    for group in skels.values():
        if len(group) > 1 and len({_item_key(i) for i in group}) > 1:
            ids = ", ".join(str(i["id"]) for i in group)
            # A lookalike group keyed to DIFFERENT answers is not just a duplicate,
            # it is a contradiction, and S7 (which gates on it) cannot see it,
            # because S7 keys on the exact question and these differ by an encoding
            # variant. Say so loudly: this is the more dangerous half of the finding.
            targets = {" | ".join(sorted(_targets_of(i))) for i in group}
            conflict = (" and their ANSWERS CONFLICT, a contradiction S7 cannot see because "
                        "the questions are not byte-identical") if len(targets) > 1 else ""
            lookalikes.append(f"{ids}: same question after folding lookalike characters"
                              f"{conflict} ({str(group[0]['input'])[:60]!r})")
    if len(items) < 2:
        rep.not_applicable("S19", "a single item cannot collide with another")
    else:
        rep.check("S19", not lookalikes,
                  f"{len(lookalikes)} group(s) of items are the same question in different encodings",
                  n=len(items), examples=lookalikes)

    # S7: identical item with contradictory targets
    by_q: dict[str, set] = {}
    for i in items:
        by_q.setdefault(_item_key(i), set()).add(tuple(sorted(_targets_of(i))))
    contra = [q[:80] for q, targets in by_q.items() if len(targets) > 1]
    rep.check("S7", not contra, f"{len(contra)} question(s) appear with conflicting targets",
              n=len(items), examples=contra)

    # S2: answer leaks into its own question (free-form items only).
    # Candidate-list rule: a question that also names several OTHER values
    # from the dataset's answer space ("answer yes or no") is offering
    # options, not leaking the key. Without this rule the check is mostly
    # false positives on instruction-style prompts.
    if tabular:
        # In a tabular audit the "question" is a synthesized join of the feature
        # values, so the target's own value is present in it by construction.
        # Reading that as an answer-in-question leak double-counts S17's finding
        # as a hard gate. Leak detection on a feature table is S17's job.
        rep.not_applicable(
            "S2", "this is a tabular audit; the synthesized question is a join of the "
                  "feature values, so label leakage is scored by S17 (target-leak), not here")
    else:
        answer_space = {_norm(t) for i in text_items for t in _targets_of(i)
                        if len(t) >= THRESHOLDS["min_leak_len"]}
        exempt_at = min(int(THRESHOLDS["candidate_list_min"]), max(1, len(answer_space) - 1))
        leaks = []
        for i in text_items:
            q = _norm(i["input"])
            own = {_norm(t) for t in _targets_of(i) if len(t) >= THRESHOLDS["min_leak_len"]}
            # A bare NUMBER appearing in a question is not evidence of leakage.
            # Word problems are full of quantities, and a two-digit answer
            # colliding with an input value is coincidence, not disclosure.
            # Found by pointing this check at GSM8K, where it called 27 items
            # leaks: every one was the target number appearing as a premise
            # ("15 litres of pineapple drink", answer 15).
            # ...UNLESS an answer-disclosing phrase introduces it. The blanket
            # exemption made S2 structurally blind to leakage in every
            # numeric-answer dataset (GSM8K, MATH, DROP, any arithmetic set): an
            # adversarial pod whose every question ended "(It is 21.)" scored 0
            # of 24 leaks (D-037). The exemption's benefit was measured when it
            # was added; its cost was not, and its cost was total.
            #
            # "15 litres of pineapple drink" is still a premise, because nothing
            # introduces the 15 as an answer. "The answer is 15" is disclosure.
            own = {o for o in own
                   if not NUMERIC_RE.fullmatch(o) or _numeric_disclosed(q, o)}
            if not own or not any(_word_in(t, q) for t in own):
                continue
            others_present = sum(1 for t in answer_space - own if _word_in(t, q))
            if others_present >= exempt_at:
                continue  # candidate list, not a leak
            # A forced-choice question has to name its own answer: "Have
            # Christians or Jews won more Nobel Prizes?" cannot be asked without
            # containing the word "Christians". The candidate-list rule already
            # intends to exempt offered options; a disjunction offers exactly
            # two, below its bar. Found on TruthfulQA.
            if _is_offered_alternative(q, own):
                continue
            leaked = next(t for t in own if _word_in(t, q))
            leaks.append(f"{i['id']}: target {leaked!r} appears in its question "
                         f"(only {others_present} other answer-space value(s) present)")

        # Multiple-choice stems get their OWN leak rule, because the free-form
        # rule cannot see them: an MCQ item carries `choices`, so it never enters
        # text_items, and a whole MCQ set left S2 n/a. Fable's first outside
        # red-team planted exactly this ("The Treaty of Versailles was signed in
        # 1919. In what year was the Treaty of Versailles signed?", answer 1919
        # among the options) and it sailed through: a numeric answer the
        # free-form path is right to leave alone, in a scope the free-form path
        # never reached.
        #
        # The DISTRACTOR is the control the free-form rule lacks. A leak names
        # only its own answer in the stem; a reading-comprehension passage or a
        # comparison names several options at once. So flag iff the correct
        # option appears in the stem and NOT ONE distractor does. That control is
        # what makes gating a numeric answer safe here: "1919" in the stem with
        # 1918/1920/1921 absent is disclosure; "5" in "which is larger, 3 or 5?"
        # is exempt because 3 is present too.
        choice_leaks = []
        for i in choice_items:
            if not isinstance(i.get("input"), str):
                continue  # asset-backed stem: the leak to look for is in the PATH (S13)
            q = _norm(i["input"])
            gold_texts = {_norm(t) for t in _targets_of(i)}
            options = [_norm(c) for c in i["choices"]]
            gold = {c for c in options if c in gold_texts}
            if not gold:
                continue  # cannot identify the keyed option; S8 owns key integrity
            hit = [g for g in gold if len(g) >= THRESHOLDS["min_leak_len"] and _word_in(g, q)]
            if not hit:
                continue
            distractors = [c for c in options if c not in gold]
            if any(len(d) >= THRESHOLDS["min_leak_len"] and _word_in(d, q) for d in distractors):
                continue  # the stem names a distractor too: a passage, not a leak
            choice_leaks.append(f"{i['id']}: correct option {hit[0]!r} appears in the stem "
                                f"and no distractor does")

        if not text_items and not choice_items:
            asset_only = sum(1 for i in items if modality.ref_of(i))
            rep.not_applicable(
                "S2", f"no free-form or multiple-choice items in this dataset"
                      + (f"; {asset_only} carry their input in a file, where the leak to look for is "
                         f"the label in the PATH (S13), not in the question" if asset_only else ""))
        else:
            found = leaks + choice_leaks
            scanned = len(text_items) + len(choice_items)
            rep.check("S2", not found,
                      f"{len(found)} of {scanned} item(s) leak their answer into the question",
                      n=scanned, examples=found)

    if not choice_items:
        for cid in ("S3", "S4", "S5", "S6", "S9", "S18"):
            rep.not_applicable(cid, "no multiple-choice items in this dataset")
        return

    # A GLOBAL label set (yes/no, true/false, entailment/neutral/contradiction)
    # degenerates position and length bias into class balance. BoolQ offers
    # ["yes", "no"] on all 3000 items, "yes" is longer than "no", and its answer
    # is yes 62% of the time, so `length-bias` reported "gold is strictly longest
    # +12% over expectation" while actually measuring the class distribution.
    #
    # Those checks are about how each item's DISTRACTORS were written. With one
    # vocabulary shared by every item there are no per-item distractors, so the
    # honest answer is n/a plus the class balance, not a bias finding.
    option_sets = {tuple(sorted(str(c) for c in i["choices"])) for i in choice_items}
    if len(option_sets) == 1 and len(choice_items) > 1:
        share = Counter(str(_targets_of(i)[0]) for i in choice_items).most_common(1)[0]
        for cid in ("S3", "S4", "S9"):
            rep.not_applicable(
                cid, f"every item offers the same options, so position and length are properties "
                     f"of the label set rather than of how each item's distractors were written. "
                     f"What varies is class balance: {share[0]!r} is the answer "
                     f"{share[1] / len(choice_items):.0%} of the time")
        _duplicate_option_checks(rep, choice_items)
        return

    _duplicate_option_checks(rep, choice_items)

    # S3/S4/S9 need enough keyed items to say anything.

    # S3/S4 operate on items with a resolvable gold position. Expectations are
    # computed per item (1/k for that item's own k), so mixed-arity datasets
    # are judged against the right baseline instead of the modal k.
    keyed = [i for i in choice_items if any(t in i["choices"] for t in _targets_of(i))]
    if len(keyed) < THRESHOLDS["min_choice_items"]:
        for cid in ("S3", "S4", "S9"):
            rep.skip(cid, f"only {len(keyed)} keyed choice item(s); need {THRESHOLDS['min_choice_items']}")
        return

    _shortcut_check(rep, keyed)

    pos_counts: Counter = Counter()
    exp_counts: dict[int, float] = {}
    longest = 0
    exp_longest = 0.0
    for i in keyed:
        k = len(i["choices"])
        gold = next(t for t in _targets_of(i) if t in i["choices"])
        pos_counts[i["choices"].index(gold)] += 1
        for p in range(k):
            exp_counts[p] = exp_counts.get(p, 0.0) + 1.0 / k
        exp_longest += 1.0 / k
        if all(len(gold) > len(c) for c in i["choices"] if c != gold):
            longest += 1

    n_keyed = len(keyed)
    excess_by_pos = {p: (pos_counts.get(p, 0) - exp_counts.get(p, 0.0)) / n_keyed for p in exp_counts}
    worst_pos, worst_excess = max(excess_by_pos.items(), key=lambda kv: kv[1])
    # A reader deciding what to do about a position-bias warning needs to know how
    # often clean data produces one at THIS size. Measured by dinocorpus (D-046):
    # the margin is absolute and unadjusted for the k positions it is tried
    # against, so small sets warn by chance at a rate worth stating out loud.
    chance_rate = _s3_chance_rate(n_keyed, k)
    caveat = (f"; at {n_keyed} items a dataset with no position bias at all trips this "
              f"about {chance_rate:.0%} of the time, so read the counts before acting"
              if chance_rate >= 0.03 else "")
    rep.check(
        "S3", worst_excess < THRESHOLDS["position_margin"],
        f"gold overshoots position {worst_pos} by {worst_excess:+.0%} over its per-item expectation "
        f"({pos_counts.get(worst_pos, 0)} of {n_keyed}){caveat}",
        n=n_keyed, evidence={"position": worst_pos, "excess": round(worst_excess, 4),
                             "chance_rate_at_this_n": round(chance_rate, 4)},
    )
    lexcess = (longest - exp_longest) / n_keyed
    rep.check(
        "S4", lexcess < THRESHOLDS["length_margin"],
        f"gold is strictly longest {lexcess:+.0%} over its per-item expectation ({longest} of {n_keyed})",
        n=n_keyed, evidence={"excess": round(lexcess, 4)},
    )


# --------------------------------------------------------------------------- runs


def _s3_chance_rate(n: int, k: int) -> float:
    """How often clean k-option data of this size trips S3 by chance.

    Analytic, not simulated, so the report costs nothing to produce it: the
    per-position count is Binomial(n, 1/k), the check trips if ANY of the k
    positions clears the absolute margin, and the positions are treated as
    independent. That last step overstates slightly (the counts sum to n and so
    are weakly negatively correlated), which is the conservative direction for a
    caveat: it never understates the chance of a false alarm.
    """
    from math import exp, lgamma, log

    if n <= 0 or k <= 0:
        return 0.0
    threshold = n / k + THRESHOLDS["position_margin"] * n
    need = int(threshold) + (0 if threshold == int(threshold) else 1)
    if need > n:
        return 0.0
    p = 1.0 / k

    # IN LOG SPACE, and not for elegance. The first version wrote this as
    # `comb(n, x) * p**x * (1-p)**(n-x)`, which is the textbook form and
    # raises OverflowError from n around 1,200: comb(1200, 300) is an integer
    # of some 300 digits and CPython refuses to coerce it to a float. So the
    # battery CRASHED on any dataset with roughly twelve hundred or more keyed
    # choice items -- that is, on exactly the large public benchmarks it is
    # most useful against, while every corpus instance (24 items) and every
    # unit test stayed comfortably inside the working range. Found by pointing
    # the audit at real datasets rather than at fixtures (D-058).
    #
    # lgamma(n+1) is log(n!), so log C(n,x) is a subtraction and each term is
    # exponentiated only after it is small.
    log_c = lgamma(n + 1)
    one = 0.0
    for x in range(need, n + 1):
        term = (log_c - lgamma(x + 1) - lgamma(n - x + 1)
                + x * log(p) + (n - x) * log(1.0 - p))
        if term > -745.0:                 # below this, exp() is 0.0 anyway
            one += exp(term)
    return 1.0 - (1.0 - min(one, 1.0)) ** k


def _word_in(needle: str, haystack: str) -> bool:
    """Is `needle` present in `haystack` as a WHOLE word or phrase?

    Plain `needle in haystack` reported a leak whenever a short answer happened
    to be spelled inside a longer word. ASDiv keys a yes/no problem "No" and
    asks "Does he have enough to buy a book" -- and "e-NO-ugh" contains it. That
    is a false accusation against somebody else's dataset, produced by a
    substring test standing in for a word test (D-059).

    Boundaries are non-alphanumeric on both sides, so multi-word answers like
    "Mrs. Hilt" still match and "no" no longer matches inside "enough".
    """
    import re as _re

    if not needle:
        return False
    return _re.search(rf"(?<![0-9a-z]){_re.escape(needle)}(?![0-9a-z])", haystack) is not None


def _shortcut_check(rep: Reporter, keyed: list[dict]) -> None:
    """S9: can a model-free heuristic find the gold option? For each surface
    feature, predict argmax(feature) per item and compare accuracy against
    the analytic per-item 1/k null (binomial z plus an absolute lift floor,
    which is what keeps this from being a false-positive machine). An item
    with no unique argmax counts as a miss, never as excluded: a feature
    that cannot decide is a feature that cannot cheat."""
    def overlap(item, choice):
        q_tokens = set(_norm(item["input"]).split())
        return len(q_tokens & set(_norm(choice).split()))

    # TOKENISATION IS WHITESPACE, AND NOT EVERY SCRIPT USES IT. Chinese, Japanese
    # and Thai write without word separators, so `split()` returns the whole stem
    # as ONE token and the overlap feature can only fire on identical strings. On
    # a real Chinese pharmacist licensing exam that produced a confident `pass`
    # over 400 items, and a shortcut S9 catches in English is invisible in the
    # Chinese version of the same planted file (D-061).
    #
    # A check that cannot discriminate SKIPS. That is this project's rule
    # everywhere else, and a pass here would be a clean bill of health the check
    # has no means to earn.
    if keyed:
        avg_tokens = sum(len(_norm(i["input"]).split()) for i in keyed) / len(keyed)
        avg_chars = sum(len(_norm(i["input"])) for i in keyed) / len(keyed)
        if avg_tokens < 2.0 and avg_chars > 10:
            rep.skip("S9", f"stems average {avg_tokens:.1f} whitespace token(s) over "
                           f"{avg_chars:.0f} characters, so this text is not space-separated and "
                           f"the token-overlap feature cannot discriminate. Scripts written "
                           f"without spaces need a segmenter this check does not have, and a "
                           f"pass here would mean nothing")
            return

    findings = []
    features = {
        "highest question-overlap": overlap,
        "shortest option": lambda item, c: -len(c),
    }
    n = len(keyed)
    for fname, score in features.items():
        # The null only covers items the feature can actually DECIDE (a unique
        # argmax). Items with a tied argmax contribute 0 to observed hits and
        # must contribute 0 to the expected null too, or z is deflated and the
        # check silently under-flags tie-heavy features.
        hits = 0
        exp = 0.0
        var = 0.0
        decidable = 0
        for i in keyed:
            gold = next(t for t in _targets_of(i) if t in i["choices"])
            scores = [score(i, c) for c in i["choices"]]
            best = max(scores)
            if scores.count(best) != 1:
                continue
            decidable += 1
            k = len(i["choices"])
            exp += 1.0 / k
            var += (1.0 / k) * (1 - 1.0 / k)
            if i["choices"][scores.index(best)] == gold:
                hits += 1
        z = (hits - exp) / (var ** 0.5) if var > 0 else 0.0
        lift = (hits - exp) / decidable if decidable else 0.0
        if z >= THRESHOLDS["shortcut_z"] and lift >= THRESHOLDS["shortcut_lift"]:
            findings.append(f"{fname} finds gold in {hits} of {decidable} decidable items "
                            f"(null expects ~{exp:.0f}, z={z:.1f}); guessable without reading the question")
    rep.check("S9", not findings,
              f"{len(findings)} surface feature(s) beat the per-item chance null on {n} keyed item(s)",
              n=n, examples=findings)


def _blind_check(rep: Reporter, probes: list[dict], real_runs: list[dict], chance: dict) -> None:
    """R13: if the eval was probed blind (inputs stripped, real provider),
    accuracy meaningfully above the informed-guesser floor means the items
    are solvable by shortcut. Dry probes are meaningless (the dry provider
    reads the key) and dry-only pods are n/a, not nagged."""
    # `probe == "blind"`, not merely "is a probe". The judge, canary, crossjudge
    # and shuffle probes all ran with the inputs INTACT, and reading one of them
    # as blind evidence reports a fabricated blind accuracy: a shuffle probe
    # scoring 77% became "this eval is solvable WITHOUT the question". Loud,
    # confident, and wrong, which is the worst direction for a diagnostic. The
    # other three probe readers filtered by type; this one never did.
    live_probes = [e for e in probes
                   if e["manifest"] and e["manifest"].get("probe") == "blind"
                   and not e["manifest"].get("dry_run")]
    if not live_probes:
        for cid in ("R13", "R15"):
            if not probes and not real_runs:
                rep.skip(cid, "no runs on disk yet")
            elif any(e["manifest"] and not e["manifest"].get("dry_run") for e in real_runs):
                rep.skip(cid, "no blind probe on disk; run `dinostomp run <spec> --probe blind` to unlock")
            else:
                rep.not_applicable(cid, "blind probes need a real provider; this pod's runs are all dry")
        return
    # Per model, not pooled: one blind-solver in a fleet answers "yes, solvable
    # blind" even when the others sit at the floor. Pooling would let honest
    # models mask one shortcut.
    floor = chance["floor"]
    bar = floor + THRESHOLDS["guess_margin"]
    by_model: dict[str, list[str]] = {}
    for e in live_probes:
        model = str(e["manifest"].get("model"))
        for r in e["records"]:
            v = (r.get("score") or {}).get("verdict")
            if v in ("pass", "fail", "flag"):
                by_model.setdefault(model, []).append(v)
    scored = {m: (vs.count("pass") / len(vs), len(vs)) for m, vs in by_model.items()
              if len(vs) >= THRESHOLDS["min_checkable"]}
    if not scored:
        for cid in ("R13", "R15"):
            rep.skip(cid, f"no model has {THRESHOLDS['min_checkable']}+ checkable blind records")
        return
    solvers = [f"{m}: blind accuracy {acc:.0%} on {nn} record(s) vs floor {floor:.0%}"
               for m, (acc, nn) in sorted(scored.items()) if acc > bar]
    rep.check("R13", not solvers,
              f"{len(solvers)} of {len(scored)} model(s) solve the eval blind, above the informed-guesser "
              f"floor {floor:.0%}; the items are answerable WITHOUT the question",
              n=len(scored), examples=solvers, evidence={"floor": round(floor, 4)})

    # R15: the other half of the same evidence. R13 asks whether the EVAL is
    # answerable without its questions; this asks whether each MODEL actually
    # used them. A model whose informed accuracy does not clear its OWN blind
    # baseline contributed no signal, however respectable its raw score looks
    # against the chance floor. Found live: a 1B model scored exactly its blind
    # accuracy across 120 items, and the only other checks that caught it
    # depended on the answer key happening to be balanced.
    informed: dict[str, list[str]] = {}
    for e in real_runs:
        m = str((e["manifest"] or {}).get("model"))
        for r in e["records"]:
            v = (r.get("score") or {}).get("verdict")
            if v in ("pass", "fail", "flag"):
                informed.setdefault(m, []).append(v)
    paired = {m: (vs.count("pass") / len(vs), scored[m][0])
              for m, vs in informed.items()
              if m in scored and len(vs) >= THRESHOLDS["min_checkable"]}
    if not paired:
        rep.skip("R15", "no model has both a real run and a blind probe with "
                        f"{THRESHOLDS['min_checkable']}+ checkable records")
        return
    deaf = [f"{m}: informed {real:.0%} vs its own blind {bl:.0%} (lift {real - bl:+.0%})"
            for m, (real, bl) in sorted(paired.items())
            if real - bl <= THRESHOLDS["blind_lift_min"]]
    rep.check("R15", not deaf,
              f"{len(deaf)} of {len(paired)} model(s) score no better informed than blind; their "
              f"numbers are not evidence about this task (unpaired: separate runs)",
              n=len(paired), examples=deaf,
              evidence={"lift": {m: round(real - bl, 4) for m, (real, bl) in paired.items()}})


def collapsed_models(runs: list[dict], modal_share: float,
                    min_share: float | None = None) -> dict[str, tuple[str, float, int]]:
    """{model: (its one answer, that answer's share, n)} for examinees that give
    essentially one response to everything.

    Two different bars, on purpose. R14 REPORTS at `collapse_margin`, because a
    model answering one label 86% of the time is worth knowing about. The
    psychometric checks EXCLUDE only at `min_share`, near-constant, because a
    biased model still discriminates a little while a constant one carries no
    difficulty signal at all and manufactures phantom key errors. Throwing out
    everything merely biased would cost more fleet than it buys.
    """
    by_model: dict[str, list[str]] = {}
    for entry, r in ((e, r) for e in runs for r in e["records"]):
        if (r.get("score") or {}).get("verdict") in ("pass", "fail", "flag") and "output" in r:
            by_model.setdefault(str((entry["manifest"] or {}).get("model")), []).append(
                _norm(r.get("output") or ""))
    out = {}
    for model, outs in by_model.items():
        if len(outs) < THRESHOLDS["min_checkable"]:
            continue
        top, count = Counter(outs).most_common(1)[0]
        share = count / len(outs)
        if share - modal_share > THRESHOLDS["collapse_margin"] and (
                min_share is None or share >= min_share):
            out[model] = (top, share, len(outs))
    return out


def _trajectory_checks(rep: Reporter, mine: list[dict], spec: dict, items: list[dict],
                       probes: list[dict] | None = None) -> None:
    """T1-T6: the agent rail's battery, over SELF-REPORTED execution traces.

    Scope discipline, because this is the easiest place in the toolkit to
    overclaim: these checks verify the RECORD, not the EXECUTION. A target that
    silently omits a tool call from its trace cannot be caught by reading the
    trace. T1/T2/T3 are therefore gating facts about what was reported, and T5
    is the only instrument aimed at the omission itself, by fleet comparison.
    """
    policy = spec.get("trajectory") or {}
    required = [t for t in (policy.get("required_tools") or [])]
    forbidden = set(policy.get("forbidden_tools") or [])
    max_steps = policy.get("max_steps")

    # BOTH code rails produce a trajectory. They differ in who WROTE it, which
    # is T8's job to state, not a reason to skip the other seven.
    CODE_RAILS = ("python", "mediated")

    def carries_trace(entry: dict) -> bool:
        """An IMPORTED run joins on EVIDENCE, not on its provider string.

        A foreign harness can record tool calls, and an Inspect import brings
        them in. Gating on the provider made T1-T6 unreachable for every
        imported agent run, which is most of what importing an agent log is
        FOR (D-031). An imported run with no trace still stays out, so a
        loglikelihood import does not acquire six vacuous trajectory findings.
        """
        return any(r.get("trajectory") for r in entry.get("records") or ())

    eligible = [e for e in mine
                if e["manifest"] and not e["manifest"].get("probe")
                and (e["manifest"].get("provider") in CODE_RAILS or carries_trace(e))]
    if not any(mc.get("provider") in CODE_RAILS for mc in spec["models"]) and not eligible:
        for cid in TRAJECTORY_CHECK_IDS:
            rep.not_applicable(cid, "this spec runs no code targets and no imported run carries a "
                                    "trajectory; nothing here produces or carries one")
        return

    agentic = eligible
    if not agentic:
        for cid in TRAJECTORY_CHECK_IDS:
            rep.skip(cid, "no code-target runs on disk yet")
        return

    recs = [(e, r) for e in agentic for r in e["records"]]
    n_recs = len(recs)

    def steps_of(record: dict) -> list[dict]:
        traj = record.get("trajectory")
        return traj if isinstance(traj, list) else []

    def where(entry: dict, record: dict) -> str:
        return f"{record.get('item_id')} ({(entry['manifest'] or {}).get('model')})"

    # A python target need not be an agent: it can be a plain answerer that
    # reports no trace at all. With no trace anywhere AND no policy demanding
    # one, this is not an agent eval, and the trajectory checks are structurally
    # inapplicable rather than vacuously passing on empty traces. If a policy IS
    # declared they still run and fail, because a spec that requires a tool has
    # already said the trace matters.
    if not any(steps_of(r) for _, r in recs) and not (required or forbidden or max_steps):
        for cid in TRAJECTORY_CHECK_IDS:
            rep.not_applicable(cid, "no python target reported a trajectory and no trajectory "
                                    "policy is declared; this pod is not an agent eval")
        return

    # T1: a banned tool was called. Gating: this is a fact about the trace.
    if not forbidden:
        rep.not_applicable("T1", "no forbidden_tools declared in the spec")
    else:
        hits = [f"{where(e, r)}: called {s.get('tool')!r}"
                for e, r in recs for s in steps_of(r) if s.get("tool") in forbidden]
        rep.check("T1", not hits,
                  f"{len(hits)} forbidden tool call(s) across {n_recs} trajector(ies)",
                  n=n_recs, examples=hits)

    # T2: a mandatory tool was never called (the RAG pipeline that answered
    # without retrieving anything).
    if not required:
        rep.not_applicable("T2", "no required_tools declared in the spec")
    else:
        missing = []
        for e, r in recs:
            called = {s.get("tool") for s in steps_of(r)}
            absent = [t for t in required if t not in called]
            if absent:
                missing.append(f"{where(e, r)}: never called {', '.join(absent)}")
        rep.check("T2", not missing,
                  f"{len(missing)} of {n_recs} trajector(ies) skipped a required tool",
                  n=n_recs, examples=missing)

    # T3: the trace is coherent. Nameless steps are recorded, never repaired,
    # precisely so this check can see them.
    problems = []
    for e, r in recs:
        steps = steps_of(r)
        nameless = sum(1 for s in steps if not s.get("tool"))
        if nameless:
            problems.append(f"{where(e, r)}: {nameless} step(s) with no tool name")
        if max_steps and len(steps) > int(max_steps):
            problems.append(f"{where(e, r)}: {len(steps)} steps, past max_steps {max_steps}")
    rep.check("T3", not problems, f"{len(problems)} malformed trajector(ies) of {n_recs}",
              n=n_recs, examples=problems)

    # T4: the Clever Hans of tool use. An answer scored PASS whose target
    # appears in no tool result was not read out of the evidence; it came from
    # somewhere else (parametric memory, a lucky guess, or a leaky prompt).
    # Per model, never pooled: one ungrounded agent in an honest fleet would
    # vanish into the average, which is the same flattering-pooling defect R13
    # was fixed for. Each target answers for itself.
    by_id = {str(i["id"]): i for i in items}
    pools: dict[str, list[tuple[dict, dict]]] = {}
    for e, r in recs:
        if ((r.get("score") or {}).get("verdict") == "pass"
                and str(r.get("item_id")) in by_id
                and any("result" in s for s in steps_of(r))):
            pools.setdefault(str((e["manifest"] or {}).get("model")), []).append((e, r))
    judged = {m: p for m, p in pools.items() if len(p) >= THRESHOLDS["min_grounding_evidence"]}
    if not judged:
        rep.skip("T4", f"no model has {THRESHOLDS['min_grounding_evidence']}+ passing records "
                       "carrying a tool result to ground against")
    else:
        flagged, receipts = [], []
        for model, pool in sorted(judged.items()):
            loose = []
            for e, r in pool:
                targets = [_norm(t) for t in _targets_of(by_id[str(r["item_id"])])]
                blob = _norm(" ".join(str(s.get("result") or "") for s in steps_of(r)))
                if not any(t and t in blob for t in targets):
                    loose.append(f"{where(e, r)}: passed, but its answer appears in no tool result")
            share = len(loose) / len(pool)
            receipts.extend(loose)
            if share > THRESHOLDS["ungrounded_max"]:
                flagged.append(f"{model}: {len(loose)} of {len(pool)} passing answer(s) ({share:.0%}) "
                               "appear in no retrieved evidence")
        # This measures CO-OCCURRENCE, not causation, and the difference is
        # large. A live agent that answered from memory and retrieved the right
        # topic afterwards was 100% causally ungrounded and T4 reported 16%: the
        # answer appeared in the snippet it never read. The error is one-sided,
        # so a warning here is a FLOOR and silence is not a clean bill, and the
        # finding says so rather than leaving a reader to assume otherwise.
        rep.check("T4", not flagged,
                  f"{len(flagged)} of {len(judged)} target(s) pass items whose answer does not "
                  f"APPEAR in their own evidence ({len(receipts)} such answer(s) in total). This "
                  "is co-occurrence, not causation: an answer recalled from memory that also "
                  "happens to appear in a retrieved snippet counts as grounded here, so this "
                  "count is a floor",
                  n=len(judged), examples=flagged + receipts,
                  evidence={"models_judged": len(judged), "ungrounded_records": len(receipts),
                            "measures": "co-occurrence in the recorded trace, not causal use"})

    # T7: the CAUSAL question T4 cannot ask.
    #
    # T4 asks whether a passing answer APPEARS in the trace's tool results. That
    # is co-occurrence: an agent answering from memory that also retrieved the
    # right topic scores as grounded, and on a live pod that gap was 6x (D-020).
    # No amount of reading the trace harder closes it, because a trace records
    # what was fetched and not what was read.
    #
    # The ablation probe asks the counterfactual instead. Same agent, same items,
    # same tool calls, every RESULT withheld. An answer that comes out identical
    # did not depend on the evidence: not "might not have", did not. The only
    # thing that differed between the two runs is whether the agent could see
    # what came back.
    # The probe list is passed separately because `mine` is real runs only, by
    # design: a probe must never pool with a result. T7 is the one check here
    # that needs BOTH arms, since a counterfactual is a comparison.
    ablate = [e for e in (probes or []) if (e["manifest"] or {}).get("probe") == "ablate"]
    real = agentic
    if not any((e["manifest"] or {}).get("provider") == "mediated" for e in mine):
        rep.not_applicable(
            "T7", "no mediated agent on disk; only the harness can withhold a tool result, and a "
                  "self-reporting target calls its own functions")
    elif not ablate:
        rep.skip("T7", "no ablation probe on disk; run `dinostomp run <spec> --probe ablate` to "
                       "unlock the causal grounding question")
    else:
        def answers(entries):
            out = {}
            for e in entries:
                model = str((e["manifest"] or {}).get("model"))
                for r in e["records"]:
                    out.setdefault(model, {})[str(r.get("item_id"))] = r
            return out

        withheld, normal = answers(ablate), answers(real)
        flagged, receipts, judged = [], [], {}
        for model, base in sorted(normal.items()):
            paired = withheld.get(model) or {}
            # Only PASSING answers. An answer that was wrong anyway tells us
            # nothing about whether evidence was used to get it right.
            pool = [(i, r) for i, r in base.items()
                    if (r.get("score") or {}).get("verdict") == "pass" and i in paired]
            if len(pool) < THRESHOLDS["min_grounding_evidence"]:
                continue
            judged[model] = pool
            unmoved = [i for i, r in pool
                       if _norm(r.get("output") or "") == _norm(paired[i].get("output") or "")]
            share = len(unmoved) / len(pool)
            receipts.extend(f"{model}/{i}: identical answer with its evidence withheld"
                            for i in sorted(unmoved)[:3])
            if share > THRESHOLDS["ungrounded_max"]:
                flagged.append(f"{model}: {len(unmoved)} of {len(pool)} passing answer(s) "
                               f"({share:.0%}) are unchanged when the evidence is withheld")
        if not judged:
            rep.skip("T7", f"no model has {THRESHOLDS['min_grounding_evidence']}+ passing answers "
                           "present in both the real run and the ablation probe")
        else:
            rep.check("T7", not flagged,
                      f"{len(flagged)} of {len(judged)} agent(s) answer identically with their "
                      f"evidence withheld, so those answers did not causally depend on it. Unlike "
                      f"T4 this is a counterfactual, not a co-occurrence: the two runs differ only "
                      f"in whether the agent could see what its tools returned",
                      n=len(judged), examples=flagged + receipts,
                      evidence={"models_judged": len(judged),
                                "measures": "causal dependence, by withholding tool results"})

    # T8: which rail produced the trace, stated rather than assumed.
    #
    # Six checks read the trajectory. On the self-reported rail all six read an
    # examinee's testimony; on the mediated rail they read the harness's log.
    # That difference was documented only in prose, which meant a reader of a
    # REPORT could not tell which they were holding. It is recorded now, and
    # printed whatever the level.
    #
    # It WARNS on a mixed fleet, not on self-report. Self-report is a supported
    # choice with a stated limit, and a warning that fires on every pod of a
    # kind teaches people to ignore warnings. A pod that mixes rails is a
    # different thing: T1-T6 then mean different things for different models in
    # one table, and comparing them across the fleet compares a log to a claim.
    sources: dict[str, list[str]] = {}
    isolations: set[str] = set()
    for e in mine:
        m = e["manifest"] or {}
        # An IMPORTED run counts here too, and this is the case T8 exists for:
        # a foreign trace is the one whose provenance a reader cannot guess.
        # Gating on the code rails made it go n/a exactly when the answer was
        # "somebody else observed this" (D-031).
        imported_trace = bool(m.get("imported")) and any(
            r.get("trajectory") for r in e.get("records") or ())
        if m.get("provider") in CODE_RAILS or imported_trace:
            default = "foreign_observed" if imported_trace else "self_reported"
            sources.setdefault(m.get("trajectory_source") or default, []).append(
                str(m.get("model")))
            isolations.add(str(m.get("isolation") or "inprocess")
                           if m.get("provider") == "mediated" else "n/a")
    if not sources:
        rep.not_applicable("T8", "this spec runs no code targets; nothing produces a trajectory")
    else:
        observed = sorted(set(sources.get("harness_observed") or ()))
        testified = sorted(set(sources.get("self_reported") or ()))
        foreign = sorted(set(sources.get("foreign_observed") or ()))
        mixed = len([g for g in (observed, testified, foreign) if g]) > 1
        if mixed:
            parts = []
            if observed:
                parts.append(f"{len(observed)} harness-observed")
            if foreign:
                parts.append(f"{len(foreign)} imported from another harness")
            if testified:
                parts.append(f"{len(testified)} self-reported")
            detail = (f"this fleet mixes trajectory sources ({', '.join(parts)}). T1-T6 therefore "
                      f"mean different things per model in one table, and a fleet comparison over "
                      f"them compares evidence of different strengths")
        elif foreign:
            detail = (f"all {len(foreign)} run(s) carry a trajectory recorded by ANOTHER harness "
                      f"and imported here. That is stronger than an agent's self-report, because "
                      f"the exporting harness is a third party to the agent, and it is still not "
                      f"this engine's own observation: T1-T6 are reading somebody else's log")
        elif testified:
            detail = (f"all {len(testified)} target(s) write their own trajectory, so T1-T6 verify "
                      f"the RECORD and not the EXECUTION: a target that omits a call from its own "
                      f"trace cannot be caught by reading it. Supported and stated, not a defect. "
                      f"Provider `mediated` moves the tools into the harness if you want the trace "
                      f"to be a log")
        else:
            sandboxed = isolations == {"subprocess"}
            how = ("in a child process, with the tools left in the parent"
                   if sandboxed else "in this process")
            caveat = ("Containment, not confinement: the filesystem is not confined and the "
                      "network denial is defeatable"
                      if sandboxed else
                      "Mediation is not isolation: it makes the trace trustworthy, not the agent, "
                      "and `isolation: subprocess` is the stronger setting")
            detail = (f"all {len(observed)} agent(s) reached their tools through the harness, "
                      f"running {how}, so T1-T6 read an observed log rather than testimony. "
                      f"{caveat}")
        rep.check("T8", not mixed, detail,
                  n=sum(len(set(v)) for v in sources.values()),
                  examples=([f"{m}: harness-observed" for m in observed]
                            + [f"{m}: imported (foreign harness)" for m in foreign]
                            + [f"{m}: self-reported" for m in testified]) if mixed else [],
                  evidence={"trajectory_sources": {k: sorted(set(v)) for k, v in sources.items()},
                            "isolation": sorted(isolations - {"n/a"}) or ["n/a"]})

    # T5: the only instrument pointed at the trust boundary itself. A target
    # that under-reports its trace looks exactly like an honest one when read
    # alone, and looks like an outlier when read against its fleet.
    steps_by_model: dict[str, list[int]] = {}
    for e, r in recs:
        steps_by_model.setdefault(str((e["manifest"] or {}).get("model")), []).append(len(steps_of(r)))
    if len(steps_by_model) < 2:
        rep.not_applicable("T5", "only 1 python-target model on disk; under-reporting is fleet-relative")
    else:
        means = {m: sum(v) / len(v) for m, v in steps_by_model.items() if v}
        fleet_median = median(means.values())
        bar = fleet_median * THRESHOLDS["underreport_ratio"]
        quiet = [f"{m}: {mu:.1f} step(s) per item vs fleet median {fleet_median:.1f}"
                 for m, mu in sorted(means.items()) if fleet_median > 0 and mu < bar]
        rep.check("T5", not quiet,
                  f"{len(quiet)} of {len(means)} target(s) report far fewer steps than the fleet "
                  f"(median {fleet_median:.1f}); a thin trace can be efficiency OR omission",
                  n=len(means), examples=quiet, evidence={"fleet_median_steps": round(fleet_median, 3)})

    # T6: the same call, with the same arguments, more than once in one
    # trajectory. Cheap to detect, and it is what a stuck loop looks like.
    # Per model for the same reason as T4: a fleet average hides the one agent
    # that loops.
    churn: dict[str, list[str]] = {}
    totals: Counter = Counter()
    for e, r in recs:
        model = str((e["manifest"] or {}).get("model"))
        totals[model] += 1
        seen = Counter((s.get("tool"), json.dumps(s.get("args") or {}, sort_keys=True))
                       for s in steps_of(r))
        repeats = sum(c - 1 for c in seen.values() if c > 1)
        if repeats:
            churn.setdefault(model, []).append(f"{where(e, r)}: {repeats} repeated identical call(s)")
    loopers = []
    for model, total in sorted(totals.items()):
        share = len(churn.get(model, [])) / total if total else 0.0
        if share > THRESHOLDS["redundant_call_max"]:
            loopers.append(f"{model}: {len(churn[model])} of {total} trajector(ies) ({share:.0%}) "
                           "repeat an identical call")
    rep.check("T6", not loopers,
              f"{len(loopers)} of {len(totals)} target(s) repeat identical calls in more than "
              f"{THRESHOLDS['redundant_call_max']:.0%} of their trajectories",
              n=len(totals), examples=loopers + [x for v in churn.values() for x in v[:3]])


def _judge_checks(rep: Reporter, probes: list[dict], mine: list[dict], spec: dict) -> None:
    """J1-J3: who evaluated your evaluator?

    A judge is a model, so it has model failure modes, and they are invisible in
    the number it produces. J1 and J2 read the judge probe, whose cases have a
    correct verdict BY CONSTRUCTION, so the judge can be graded without a second
    judge. J3 reads the real runs and asks a different question: not whether the
    judge is right, but whether it is EVENLY wrong across the fleet.
    """
    if (spec["scorer"].get("kind")) != "judge":
        for cid in JUDGE_CHECK_IDS:
            rep.not_applicable(cid, "this eval does not score with a judge")
        return

    judge_runs = [e for e in probes if (e["manifest"] or {}).get("probe") == "judge"]
    if not judge_runs:
        for cid in ("J1", "J2", "J3"):
            rep.skip(cid, "no judge probe on disk; run `dinostomp run <spec> --probe judge` "
                          "to make the judge earn the right to judge")
    else:
        records = [r for e in judge_runs for r in e["records"]]
        graded = [r for r in records if r.get("polarity")]

        # J1: does the judge agree with cases whose answer is known by
        # construction? Inflation is reported on its own line, because a judge
        # that passes wrong answers manufactures accuracy, while one that fails
        # right answers merely wastes it.
        baseline = [r for r in graded if not r.get("perturbation")]
        if not baseline:
            rep.skip("J1", "the judge probe recorded no baseline (unperturbed) cases")
        else:
            wrong, false_pass = [], 0
            for r in baseline:
                want = "pass" if r["polarity"] == "correct" else "fail"
                got = (r.get("score") or {}).get("verdict")
                if got != want:
                    wrong.append(f"{r.get('key')}: expected {want}, judge said {got}")
                    if got == "pass":
                        false_pass += 1
            agreement = 1 - len(wrong) / len(baseline)
            rep.check("J1", agreement >= THRESHOLDS["judge_agreement_min"],
                      f"the judge agrees with {agreement:.0%} of {len(baseline)} case(s) whose "
                      f"verdict is known by construction ({false_pass} wrong answer(s) passed)",
                      n=len(baseline), examples=wrong,
                      evidence={"agreement": round(agreement, 4), "false_passes": false_pass})

        # J2: the gauntlet. A perturbation that changes no meaning must not
        # change a verdict; every flip is a named bias with the case that
        # caused it, and inflating flips are called out separately.
        by_case = {(r.get("item_id"), r.get("polarity")): r for r in graded if not r.get("perturbation")}
        flips: dict[str, list[str]] = {}
        compared = 0
        for r in graded:
            name = r.get("perturbation")
            if not name or name == REPEAT_TAG:   # the identity regrade belongs to J3
                continue
            base_rec = by_case.get((r.get("item_id"), r.get("polarity")))
            if base_rec is None:
                continue
            compared += 1
            was = (base_rec.get("score") or {}).get("verdict")
            now = (r.get("score") or {}).get("verdict")
            if now != was:
                direction = "INFLATES" if (was, now) == ("fail", "pass") else f"{was}->{now}"
                flips.setdefault(name, []).append(f"{name} on {r.get('item_id')}: {direction}")
        biased = sorted(flips)
        inflating = sorted(n for n, v in flips.items() if any("INFLATES" in x for x in v))
        detail = (f"{len(biased)} of {len(PERTURBATION_NAMES)} content-free perturbation(s) change "
                  f"the judge's mind across {compared} regraded case(s)")
        if inflating:
            detail += f"; INFLATING: {', '.join(inflating)}"
        rep.check("J2", not biased, detail, n=compared,
                  examples=[x for name in biased for x in flips[name][:4]],
                  evidence={"biased_perturbations": biased, "inflating": inflating})

        # J3: does the judge agree with ITSELF? Every baseline case is graded a
        # second time on byte-identical input. A judge that rules differently on
        # the same input twice is not measuring a property of the response, and
        # every number downstream inherits that noise. Trivially clean for a
        # deterministic judge; it exists for hosted ones at temperature, where
        # it is the cheapest real finding available.
        #
        # What this deliberately is NOT: self-preference detection. Measuring
        # whether a judge favours its own family needs either a second judge or
        # human labels, because "this model's answers get overridden more" is
        # confounded by formatting (a model that wraps its answers fails strict
        # matching even when correct). An unsound check is worse than none, so
        # the claim is not made. See the README limitations.
        rerun = [r for r in graded if r.get("perturbation") == REPEAT_TAG]
        if not rerun:
            rep.skip("J3", "the judge probe recorded no repeat gradings")
        else:
            disagreed = []
            for r in rerun:
                base_rec = by_case.get((r.get("item_id"), r.get("polarity")))
                if base_rec is None:
                    continue
                was = (base_rec.get("score") or {}).get("verdict")
                now = (r.get("score") or {}).get("verdict")
                if was != now:
                    disagreed.append(f"{r.get('item_id')} ({r.get('polarity')}): "
                                     f"{was} then {now} on byte-identical input")
            rate = len(disagreed) / len(rerun)
            rep.check("J3", rate <= THRESHOLDS["judge_inconsistency_max"],
                      f"the judge contradicts itself on {len(disagreed)} of {len(rerun)} case(s) "
                      f"({rate:.0%}) regraded on byte-identical input",
                      n=len(rerun), examples=disagreed,
                      evidence={"inconsistency": round(rate, 4)})


def _regurgitation_check(rep: Reporter, probes: list[dict], real_runs: list[dict]) -> None:
    """S10: did any model reproduce this pod's canary?

    The sensitivity rule is the whole design. A fresh canary is a random string
    no model has seen, so a probe against it comes back clean whether the model
    is contaminated or not AND whether the probe works or not. That green is
    unfalsifiable. Every probe therefore also asks for a passage certainly in
    training data, and a model that cannot produce the CONTROL has not
    demonstrated it could produce the canary either: the check skips on that
    model rather than crediting it with a clean bill of health.
    """
    canary_runs = [e for e in probes if (e["manifest"] or {}).get("probe") == "canary"]
    if not canary_runs:
        if any(e["manifest"] and not e["manifest"].get("dry_run") for e in real_runs):
            rep.skip("S10", "no canary probe on disk; run `dinostomp run <spec> --probe canary` "
                            "to ask whether a model has already read this dataset")
        else:
            rep.not_applicable("S10", "regurgitation probes need a hosted model; this pod's runs "
                                      "are all local")
        return

    blind, contaminated, tested = [], [], 0
    for entry in canary_runs:
        model = str((entry["manifest"] or {}).get("model"))
        controls = [r for r in entry["records"] if r.get("canary_kind") == "control"]
        canaries = [r for r in entry["records"] if r.get("canary_kind") == "canary"]
        hit_control = sum(1 for r in controls if (r.get("score") or {}).get("verdict") == "flag")
        if not controls or not hit_control:
            blind.append(f"{model}: reproduced 0 of {len(controls)} control passage(s), so this "
                         "probe has no demonstrated sensitivity on it")
            continue
        tested += 1
        if any((r.get("score") or {}).get("verdict") == "flag" for r in canaries):
            contaminated.append(f"{model}: continued this pod's canary; it has seen this dataset")
    if not tested:
        rep.skip("S10", "; ".join(blind) or "the canary probe recorded nothing usable")
        return
    detail = (f"{len(contaminated)} of {tested} model(s) with a DEMONSTRATED-sensitive probe "
              f"reproduced this pod's canary")
    if blind:
        detail += f"; {len(blind)} model(s) skipped as insensitive"
    rep.check("S10", not contaminated, detail, n=tested, examples=contaminated + blind)



def _self_preference_check(rep: Reporter, probes: list[dict], mine: list[dict],
                           spec: dict) -> None:
    """J4: does the judge favour its OWN family?

    Only answerable with a SECOND judge, which is why this needs the cross-judge
    probe and why the check did not exist until one was available.

    The one-judge proxy ("does this judge override strict matching more often
    for model X?") is confounded by FORMATTING: a model that wraps its answers
    fails strict matching even when right, collecting overrides for a reason
    that has nothing to do with favouritism. Two judges make it measurable
    because both grade the SAME recorded outputs, so a model's formatting
    applies to both and cancels. What survives is the difference of differences:
    judge A's pass rate minus judge B's, for models in A's family versus
    everyone else.

    It reports a GAP, not a motive. A family gap may be favouritism, or a family
    style one judge genuinely reads better. The finding names both.
    """
    scorer_cfg = spec["scorer"]
    if scorer_cfg.get("kind") != "judge":
        rep.not_applicable("J4", "this eval does not score with a judge")
        return
    if not scorer_cfg.get("cross_judge"):
        rep.not_applicable("J4", "no `cross_judge` declared; self-preference is not measurable "
                                 "with one judge, so this is a missing instrument rather than a "
                                 "clean result")
        return

    cross_runs = [e for e in probes if (e["manifest"] or {}).get("probe") == "crossjudge"]
    if not cross_runs:
        rep.skip("J4", "no cross-judge probe on disk; run "
                       "`dinostomp run <spec> --probe crossjudge` to re-grade the recorded "
                       "outputs with the second judge")
        return

    primary: dict[str, dict[str, str]] = {}
    for e in mine:
        model = str((e["manifest"] or {}).get("model"))
        for r in e["records"]:
            v = (r.get("score") or {}).get("verdict")
            if v in ("pass", "fail"):
                primary.setdefault(model, {})[str(r.get("key", r.get("item_id")))] = v

    secondary: dict[str, dict[str, str]] = {}
    for e in cross_runs:
        for r in e["records"]:
            v = (r.get("score") or {}).get("verdict")
            if v in ("pass", "fail"):
                key = str(r.get("key", "")).split("#", 1)[-1]
                secondary.setdefault(str(r.get("graded_model")), {})[key] = v

    own_family = judge_family(scorer_cfg.get("judge") or {})
    deltas = {}
    for model, a_rows in primary.items():
        b_rows = secondary.get(model) or {}
        shared = set(a_rows) & set(b_rows)
        if len(shared) < THRESHOLDS["min_checkable"]:
            continue
        a = sum(1 for k in shared if a_rows[k] == "pass") / len(shared)
        b = sum(1 for k in shared if b_rows[k] == "pass") / len(shared)
        deltas[model] = a - b

    own = {m: d for m, d in deltas.items() if family_of(m) == own_family}
    other = {m: d for m, d in deltas.items() if family_of(m) != own_family}
    if not own or not other:
        rep.skip("J4", "the fleet has no model from the judge's own family alongside models from "
                       f"others (judge family: {own_family!r}); there is nothing to compare")
        return

    gap = (sum(own.values()) / len(own)) - (sum(other.values()) / len(other))
    rep.check("J4", abs(gap) <= THRESHOLDS["self_preference_max"],
              f"the judge is {gap:+.0%} more generous to its own family ({own_family}) than to "
              "others, relative to a second judge. That is a GAP, not a motive: it may be "
              "favouritism, or a family style this judge reads better",
              n=len(deltas),
              examples=[f"{m}: {d:+.0%} vs the cross judge"
                        for m, d in sorted(deltas.items(), key=lambda kv: -kv[1])],
              evidence={"gap": round(gap, 4), "judge_family": own_family,
                        "deltas": {m: round(d, 4) for m, d in deltas.items()}})


def _is_human(author: str) -> bool:
    return author.strip().lower().startswith("human:")


def _authorship_check(rep: Reporter, spec: dict) -> None:
    """S16: report where a MODEL sits on both sides of an authorship loop.

    A model that wrote the questions and also wrote their keys graded its own
    questions; a model that wrote the scorer and also wrote its witnesses fitted
    the W1/W2/W3 gauntlet to its own output. Those are the loops worth surfacing,
    and this states them as facts. Solo HUMAN authorship is not one of them:
    one expert writing their own eval is ordinary practice, so this records it
    and moves on rather than lecturing about it. The check is diagnostic and
    takes no position on whether a given eval is sound; it reads the declared
    provenance, and where a model closes a loop with no `review_by`, it says so.
    """
    prov = spec.get("provenance")
    if not prov:
        rep.not_applicable("S16", "no provenance declared, so authorship is not described. Declaring who "
                                  "wrote the items, keys, scorer, and witnesses lets this surface a model "
                                  "sitting on both sides of a loop (e.g. keying its own questions)")
        return
    items_by = str(prov.get("items_by") or "").strip()
    keys_by = str(prov.get("keys_by") or "").strip()
    scorer_by = str(prov.get("scorer_by") or "").strip()
    witnesses_by = str(prov.get("witnesses_by") or "").strip()
    review_by = str(prov.get("review_by") or "").strip()

    authored = {k: v for k, v in
                (("items", items_by), ("keys", keys_by),
                 ("scorer", scorer_by), ("witnesses", witnesses_by)) if v}

    model_loops, human_notes = [], []

    def loop(who, msg):
        (model_loops if not _is_human(who) else human_notes).append((who, msg))

    one_author = len(set(authored.values())) == 1 and len(authored) >= 3
    if one_author and not review_by:
        who = next(iter(authored.values()))
        loop(who, f"{who} is credited with {', '.join(authored)}, and no review_by is declared: "
                  f"one author, no declared independent check")
    else:
        if items_by and keys_by and items_by == keys_by:
            loop(items_by, f"items and keys are both credited to {items_by}: the keys are not "
                           f"declared as independently verified")
        if scorer_by and witnesses_by and scorer_by == witnesses_by:
            loop(scorer_by, f"scorer and witnesses are both credited to {scorer_by}: the witness "
                            f"gauntlet is not declared as independently written")

    # A model on both sides of a loop is the warn. Human-only loops are recorded,
    # not flagged: independent verification is good practice, not a requirement.
    warn_msgs = [f"a model closes an authorship loop: {m}" for _, m in model_loops]
    if human_notes and not model_loops:
        detail = (f"{len(human_notes)} authorship loop(s), all human-authored and recorded, "
                  f"not flagged (e.g. {human_notes[0][1]})")
    else:
        detail = (f"{len(model_loops)} loop(s) closed by a model" if model_loops
                  else "no model sits on both sides of an authorship loop")
    rep.check(
        "S16", not model_loops, detail,
        n=len(authored),
        examples=warn_msgs,
        evidence={k: v for k, v in prov.items() if isinstance(v, str)},
    )


def _canary_check(rep: Reporter, base: Path, data_cfg: dict) -> None:
    """S8: a `{"_canary": "<unique string>"}` line inside the data file lets a
    trained-on copy of the benchmark be detected later (the BIG-bench canary
    convention, per-pod). The loader skips these lines; the hash covers them."""
    if data_cfg["format"] != "jsonl":
        rep.not_applicable("S8", "canary lines are only supported in jsonl data")
        return
    canary = None
    try:
        for line in jsonl_lines((base / data_cfg["path"]).read_text(encoding="utf-8")):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and obj.get("_canary"):
                canary = str(obj["_canary"])
                break
    except OSError:
        pass
    rep.check("S8", canary is not None,
              (f"canary present ({canary[:40]}...)" if canary and len(canary) > 40
               else f"canary present ({canary})" if canary
               else 'no {"_canary": ...} line in the data file; add one so trained-on copies are detectable'),
              n=1)


def _modal_target_share(items: list[dict]) -> tuple[float, str]:
    """Informed-guesser floor: the largest share of items a single constant
    answer would pass. Because a scorer accepts ANY listed target, the floor
    is the max over distinct target VALUES of the share of items that accept
    that value, not the share of the most common target SET."""
    per_value: Counter = Counter()
    for i in items:
        for v in set(_norm(t) for t in _targets_of(i)):
            per_value[v] += 1
    value, count = per_value.most_common(1)[0]
    return count / len(items), value


def _discover_runs(base: Path, spec_name: str) -> tuple[list[dict], list[dict]]:
    """(mine, foreign). Each entry: {path, manifest, records, bad_lines}.

    A run whose manifest names a different spec is foreign and excluded from
    every result-verification check (it would poison them), but reported by
    R10 so junk in the runs directory is never silent. A run with no readable
    manifest is MINE: unverifiable runs must fail loudly, not vanish.
    """
    mine: list[dict] = []
    foreign: list[dict] = []
    run_dir = base / "data" / "runs"
    if not run_dir.is_dir():
        return mine, foreign
    for rf in sorted(run_dir.glob("*.jsonl")):
        mf = rf.with_name(rf.stem + "_manifest.json")
        manifest = None
        if mf.is_file():
            try:
                manifest = json.loads(mf.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                manifest = None
        records = []
        bad_lines = 0
        try:
            lines = jsonl_lines(rf.read_text(encoding="utf-8"))
        except OSError:
            lines = []
            bad_lines += 1
        for line in lines:
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                bad_lines += 1
        entry = {"path": rf, "manifest": manifest, "records": records, "bad_lines": bad_lines}
        if manifest is not None and manifest.get("spec_name") != spec_name:
            foreign.append(entry)
        else:
            mine.append(entry)
    return mine, foreign


def _witness_check(rep: Reporter, spec: dict, scorer, runs: list[dict], refused: str = "") -> None:
    """R2: replay the witness gate now, and require every run's manifest to
    claim a fully-behaved gate. The replay is the proof; the manifest claim
    catches ledgers imported from a tool that skipped the gate."""
    witnesses = spec["scorer"]["witnesses"]
    if scorer is None:
        rep.skip("R2", refused or "no scorer available to replay the gate")
        return
    if not getattr(scorer, "offline_replayable", True):
        # Replaying a hosted judge would make `stomp` spend money and touch the
        # network, which it never does. The manifest claim is still audited.
        claims = [f"{e['path'].name}: manifest witness claim does not match the spec's gate"
                  for e in runs
                  if ((e["manifest"] or {}).get("witness_report") or {}).get("verdict") != "validated"
                  or ((e["manifest"] or {}).get("witness_report") or {}).get("n_witnesses") != len(witnesses)]
        if not runs:
            rep.skip("R2", "hosted judge: the gate cannot be replayed offline, and no run "
                           "manifest is on disk to audit its claim")
        else:
            rep.check("R2", not claims,
                      f"hosted judge: gate NOT replayed (that would spend money during a lint); "
                      f"audited the witness claim in {len(runs)} run manifest(s) instead",
                      n=len(runs), examples=claims)
        return
    replay = run_witnesses(scorer, witnesses)
    examples = [
        f"witness[{f['index']}]: expected {f['expected']}, got {f['got']} on {f['output']!r}"
        for f in replay.failures
    ]
    for entry in runs:
        m = entry["manifest"]
        wr = (m or {}).get("witness_report") or {}
        if (wr.get("verdict") != "validated"
                or wr.get("n_behaved") != wr.get("n_witnesses")
                or wr.get("n_witnesses") != len(witnesses)):
            examples.append(f"{entry['path'].name}: manifest witness claim does not match the spec's gate")
    rep.check("R2", not examples,
              f"replayed {replay.n_witnesses} witness(es): {replay.n_behaved} behaved; "
              f"{len(runs)} run manifest(s) checked",
              n=len(witnesses) + len(runs), examples=examples)


def _expected_hashes(spec_file: Path, spec: dict) -> dict:
    base = spec_file.parent
    expected = {
        "spec_sha256": spec_sha256(spec_file),
        "data_sha256": spec_sha256(base / spec["data"]["path"]),
    }
    if spec["scorer"]["kind"] == "python":
        expected["scorer_sha256"] = spec_sha256(base / spec["scorer"]["code"])
    judge_file = judge_entrypoint(spec)
    if judge_file and (base / judge_file).is_file():
        # A judge decides verdicts. Of every input in the pod, it is the one
        # that must not be allowed to change quietly after the fact.
        expected["judge_sha256"] = spec_sha256(base / judge_file)
    mounts = mount_hashes(spec, base)
    if mounts:
        expected["mount_sha256"] = mounts
    return expected


def _expected_target_hashes(spec_file: Path, spec: dict) -> dict[str, str]:
    """{model: sha256} for python targets. Per model, because two agents in one
    fleet are two different inputs to the drift boundary."""
    base = spec_file.parent
    out = {}
    for mc in spec["models"]:
        entry = target_entrypoint(mc)
        if not entry:
            continue
        path = base / entry
        if path.is_file():
            out[mc["model"]] = spec_sha256(path)
    return out


def _run_checks(rep: Reporter, mine: list[dict], foreign: list[dict], spec_file: Path,
                spec: dict, items: list[dict], chance: dict, scorer) -> None:
    if not mine:
        for cid in RUN_CHECK_IDS + ("R7",):
            rep.skip(cid, skip_reason(cid, survey([])) or "no evidence on disk")
        return

    # The evidence contract, applied before anything else: a check whose
    # declared fields are absent skips naming the FIELD, not the runner. "no
    # `finish_reason` on 240 of 240 records" is actionable; "no runs on disk"
    # is both unactionable and, here, false.
    ev = survey(mine)
    for cid in RUN_CHECK_IDS + ("R7",):
        gaps = missing_for(cid, ev)
        if gaps:
            rep.skip(cid, skip_reason(cid, ev), missing=gaps)

    expected = _expected_hashes(spec_file, spec)
    expected_targets = _expected_target_hashes(spec_file, spec)
    run_cfg = spec["run"]
    model_names = {mc["model"] for mc in spec["models"]}
    eps = THRESHOLDS["spend_tolerance_usd"]

    # R1: the drift boundary plus manifest integrity and spec cross-checks.
    drifted = []
    for entry in mine:
        rf, m = entry["path"], entry["manifest"]
        if m is None:
            drifted.append(f"{rf.name}: no readable manifest; nothing about this run is verifiable")
            continue
        reasons = [k.replace("_sha256", "") for k, v in expected.items() if m.get(k) != v]
        # The agent is an input: a target edited after its run is drift, exactly
        # like an edited scorer. Checked per model, since each has its own code.
        want_target = expected_targets.get(str(m.get("model")))
        if want_target is not None and m.get("target_sha256") != want_target:
            reasons.append("target")
        if validate_obj(m, "manifest"):
            reasons.append("manifest schema-invalid")
        declared_seeds = {run_cfg["seed"], *(int(s) for s in (run_cfg.get("seeds") or []))}
        if m.get("seed") not in declared_seeds:
            reasons.append("seed is not one the spec declares")
        if m.get("model") not in model_names:
            reasons.append(f"model {m.get('model')!r} not in spec")
        if m.get("repeats", 1) != run_cfg.get("repeats", 1):
            reasons.append("repeats differ from spec")
        if reasons:
            drifted.append(f"{rf.name}: {', '.join(reasons)} changed since this run"
                           if set(reasons) <= {"spec", "data", "scorer"}
                           else f"{rf.name}: {', '.join(reasons)}")
    rep.check("R1", not drifted,
              f"{len(drifted)} of {len(mine)} run(s) no longer match the spec, data, or scorer on disk",
              n=len(mine), examples=drifted)

    # R3: money honesty, audited against the SPEC's cap and the records themselves.
    over = []
    for entry in mine:
        rf, m, records = entry["path"], entry["manifest"], entry["records"]
        ledger = sum(float((r.get("usage") or {}).get("cost_usd") or 0.0) for r in records)
        cap = float(run_cfg["budget_usd"])
        if ledger > cap + eps:
            over.append(f"{rf.name}: records sum to ${ledger:.4f}, past the spec cap ${cap:.2f}")
        if m is not None:
            claimed = float(m.get("spend_usd") or 0.0)
            if abs(claimed - ledger) > eps:
                over.append(f"{rf.name}: manifest claims ${claimed:.6f}, records sum to ${ledger:.6f}")
            if float(m.get("budget_cap_usd", cap)) != cap:
                over.append(f"{rf.name}: manifest cap differs from the spec's budget_usd")
    rep.check("R3", not over, f"{len(over)} money discrepanc(ies) across {len(mine)} run(s)",
              n=len(mine), examples=over)

    all_records = [(entry, r) for entry in mine for r in entry["records"]]

    # R4: record integrity and attribution to the manifest's own identity.
    bad = []
    for entry in mine:
        rf, m, records = entry["path"], entry["manifest"], entry["records"]
        if entry["bad_lines"]:
            bad.append(f"{rf.name}: {entry['bad_lines']} unparseable line(s)")
        keys = Counter(r.get("key") for r in records)
        for key, c in keys.items():
            if c > 1:
                bad.append(f"{rf.name}: key {key!r} appears {c} times")
        for r in records:
            if validate_obj(r, "record"):
                bad.append(f"{rf.name}: schema-invalid record (key {r.get('key')!r})")
            elif m is not None:
                for fld in ("model", "provider", "seed"):
                    if r.get(fld) != m.get(fld):
                        bad.append(f"{rf.name}: record {r.get('key')!r} claims {fld} "
                                   f"{r.get(fld)!r} in a ledger of {m.get(fld)!r}")
    rep.check("R4", not bad, f"{len(bad)} integrity problem(s) across {len(all_records)} record(s)",
              n=len(all_records) + sum(e["bad_lines"] for e in mine), examples=bad)

    # R5: truncation credited
    credited = [f"{entry['path'].name}: {r.get('key')}" for entry, r in all_records
                if r.get("finish_reason") in TRUNCATION_REASONS
                and (r.get("score") or {}).get("verdict") == "pass"]
    # It GATES on purpose and it is deliberately not clever. Some of these are
    # legitimate: a model can state its answer and then get cut off closing a
    # LaTeX brace. On the GSM8K pod 4 of 9 were that, and the other 5 were the
    # thing this exists for, an unfinished response whose last intermediate
    # number happened to equal the target. Distinguishing them needs a regex
    # for "final answer" in whatever language the model replied in, and a
    # gating check does not get to depend on that. So it hands you the list:
    # the count is small by construction, and reading nine records is cheap.
    rep.check("R5", not credited,
              f"{len(credited)} truncated output(s) scored as pass; a cut-off response can still "
              "have stated its answer, so read these before raising max_tokens and re-running",
              n=len(all_records), examples=credited)

    # R21: graded scores stay in range. W3 proves gradation on the witnesses;
    # this holds the actual records to the same [0,1] bound, because a scorer
    # that behaves on its handful of witnesses can still emit a value of 1.7 or
    # a NaN on real output, and partial_score would then average nonsense.
    graded_records = [(entry, r, (r.get("score") or {}).get("value"))
                      for entry, r in all_records
                      if (r.get("score") or {}).get("value") is not None]
    bad_range = []
    for entry, r, val in graded_records:
        try:
            f = float(val)
            ok = 0.0 <= f <= 1.0 and f == f  # f==f rejects NaN
        except (TypeError, ValueError):
            ok = False
        if not ok:
            bad_range.append(f"{entry['path'].name}: {r.get('key')} value={val!r}")
    if not graded_records:
        rep.not_applicable("R21", "no record carries a graded value")
    else:
        rep.check("R21", not bad_range,
                  f"{len(bad_range)} of {len(graded_records)} graded value(s) outside [0,1] "
                  "or not a number",
                  n=len(graded_records), examples=bad_range[:8])

    # R6: uncheckable rate
    n_unch = sum(1 for _, r in all_records if (r.get("score") or {}).get("verdict") == "uncheckable")
    rate = n_unch / len(all_records) if all_records else 0.0
    rep.check("R6", rate <= THRESHOLDS["uncheckable_warn"],
              f"{rate:.0%} of {len(all_records)} record(s) are uncheckable",
              n=len(all_records), evidence={"rate": round(rate, 4)})

    # R8: re-score every recorded output with the current scorer. R1 proves
    # the scorer and data are unchanged, so any verdict that does not
    # reproduce was edited, forged, or written by a broken fork.
    item_by_id = {str(i["id"]): i for i in items}
    mismatches = []
    rescored = 0
    unscoreable = 0
    for entry, r in all_records:
        verdict = (r.get("score") or {}).get("verdict")
        if verdict not in ("pass", "fail", "uncheckable") or "output" not in r:
            continue
        item = item_by_id.get(str(r.get("item_id")))
        if item is None:
            mismatches.append(f"{entry['path'].name}: {r.get('key')!r} scores an item the dataset does not ship")
            continue
        # A judge cannot be re-run here: it is paid, possibly nondeterministic,
        # and `stomp` makes no network calls. So the verdict is re-derived from
        # the judge's OWN recorded words instead, which keeps R8 gating and
        # offline. What that cannot prove (would the judge rule the same way
        # again?) is a reproducibility limit, stated in the report, not a hole
        # quietly left open.
        offline = getattr(scorer, "rescore_offline", None)
        if scorer is None:
            # A judge verdict still re-derives: the parse is deterministic and
            # needs no pod code. Anything else genuinely cannot be re-scored
            # without importing what we refused to import.
            if spec["scorer"]["kind"] == "judge":
                from dinostomp.judging import parse_verdict
                text = r.get("judge_response")
                if not isinstance(text, str):
                    mismatches.append(f"{entry['path'].name}: {r.get('key')!r} is a judge verdict "
                                      "with no recorded judge response; nothing backs it")
                    continue
                fresh = parse_verdict(text)
            else:
                unscoreable += 1
                continue
        elif offline is not None:
            fresh = offline(r)
            if fresh is None:
                mismatches.append(f"{entry['path'].name}: {r.get('key')!r} is a judge verdict with "
                                  "no recorded judge response; nothing backs it")
                continue
        else:
            fresh = scorer(r.get("output") or "", item["target"])
        rescored += 1
        if fresh.verdict != verdict:
            mismatches.append(f"{entry['path'].name}: {r.get('key')!r} recorded {verdict}, re-scores {fresh.verdict}")
    if scorer is None and unscoreable:
        rep.skip("R8", f"{unscoreable} recorded verdict(s) cannot be re-scored without importing "
                       "this pod's scorer; re-run with --trust-code")
    else:
        basis = ("the judge's recorded responses"
                 if scorer is None or hasattr(scorer, "rescore_offline") else "the current scorer")
        rep.check("R8", not mismatches,
                  f"{len(mismatches)} of {rescored} recorded verdict(s) do not reproduce under {basis}",
                  n=rescored, examples=mismatches)

    # R9: recompute every summary from its own records.
    summary_problems = []
    results_dir = spec_file.parent / "data" / "results"
    for entry in mine:
        rf, m, records = entry["path"], entry["manifest"], entry["records"]
        if m is None or m.get("status") not in ("complete", "stopped_early"):
            continue
        spath = results_dir / (rf.stem + "_summary.json")
        if not spath.is_file():
            summary_problems.append(f"{rf.name}: no summary on disk for a finished run")
            continue
        try:
            published = json.loads(spath.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            summary_problems.append(f"{rf.name}: summary unreadable")
            continue
        fresh = summarize(records)
        for k, v in fresh.items():
            got = published.get(k)
            same = (abs(got - v) <= eps if isinstance(v, float) and isinstance(got, (int, float)) else got == v)
            if not same:
                summary_problems.append(f"{rf.name}: summary {k}={got!r}, records say {v!r}")
    rep.check("R9", not summary_problems,
              f"{len(summary_problems)} summary discrepanc(ies) across {len(mine)} run(s)",
              n=len(mine), examples=summary_problems)

    # R10 (soft): foreign runs and narrowed runs are visible, never silent.
    scope = [f"{e['path'].name}: foreign run (spec {e['manifest'].get('spec_name')!r}), ignored above"
             for e in foreign]
    n_expected = min(int(run_cfg["n"]), len(items))
    for entry in mine:
        m = entry["manifest"]
        if m is not None and int(m.get("n_items") or 0) < n_expected:
            scope.append(f"{entry['path'].name}: ran {m.get('n_items')} of the spec's {n_expected} item(s)")
    rep.check("R10", not scope, f"{len(scope)} run(s) outside the spec's declared scope",
              n=len(mine) + len(foreign), examples=scope)

    # R11: re-derive the seeded selection and demand the ledger cover it.
    selection_problems = []
    for entry in mine:
        rf, m, records = entry["path"], entry["manifest"], entry["records"]
        if m is None or m.get("n_items") is None or m.get("seed") is None:
            selection_problems.append(f"{rf.name}: selection unverifiable (manifest incomplete)")
            continue
        expected_ids = [str(i["id"]) for i in select_items(items, int(m["n_items"]), int(m["seed"]))]
        recorded_ids = list(dict.fromkeys(str(r["item_id"]) for r in records if "item_id" in r))
        if m.get("status") == "complete":
            ok = recorded_ids == expected_ids
        else:  # a clean partial is a prefix of the seeded order
            ok = recorded_ids == expected_ids[: len(recorded_ids)]
        if not ok:
            missing = [i for i in expected_ids if i not in set(recorded_ids)]
            extra = [i for i in recorded_ids if i not in set(expected_ids)]
            selection_problems.append(
                f"{rf.name}: ledger does not match the seeded selection "
                f"({len(missing)} missing, {len(extra)} unexpected, order-sensitive)")
    rep.check("R11", not selection_problems,
              f"{len(selection_problems)} of {len(mine)} run(s) do not cover their seeded selection",
              n=len(mine), examples=selection_problems)

    # R12: selective uncheckability. A model whose outputs the scorer
    # increasingly cannot judge can raise its conditional accuracy while
    # becoming less evaluable; escaping the scorer must never look like skill.
    per_model_rates = {}
    for entry in mine:
        m = entry["manifest"]
        if m is None or not entry["records"]:
            continue
        unch = sum(1 for r in entry["records"] if (r.get("score") or {}).get("verdict") == "uncheckable")
        model_name = str(m.get("model"))
        prev_u, prev_n = per_model_rates.get(model_name, (0, 0))
        per_model_rates[model_name] = (prev_u + unch, prev_n + len(entry["records"]))
    if len(per_model_rates) < 2:
        rep.skip("R12", "needs at least 2 models to compare uncheckable rates")
    else:
        rates = {m: u / n for m, (u, n) in per_model_rates.items()}
        med = median(rates.values())
        escaping = [f"{m}: {rate:.0%} uncheckable vs fleet median {med:.0%}"
                    for m, rate in sorted(rates.items())
                    if rate >= med + THRESHOLDS["escape_margin"] and rate >= THRESHOLDS["escape_min_rate"]]
        rep.check("R12", not escaping,
                  f"{len(escaping)} of {len(rates)} model(s) escape the scorer more than the fleet does",
                  n=len(rates), examples=escaping,
                  evidence={"rates": {m: round(r, 4) for m, r in rates.items()}})

    # R14: response collapse. A model that gives one answer to everything is
    # not performing at chance, it is not performing at all, and on a balanced
    # key the two are numerically identical. Compared against the DATASET's own
    # modal target share, so a legitimately skewed key does not trip it.
    judged_models = {str((e["manifest"] or {}).get("model")) for e in mine}
    if not judged_models:
        rep.skip("R14", "no runs with a readable manifest")
    elif chance["modal"] >= THRESHOLDS["collapse_margin"] + 1 - 1e-9:
        rep.not_applicable("R14", "the answer key is itself near-constant; collapse is undetectable here")
    else:
        found = collapsed_models(mine, chance["modal"])
        examples = [f"{m}: gave {top[:40]!r} to {share:.0%} of {n} item(s), while the most common "
                    f"target covers only {chance['modal']:.0%}"
                    for m, (top, share, n) in sorted(found.items())]
        rep.check("R14", not found,
                  f"{len(found)} of {len(judged_models)} model(s) answer with one response far more "
                  f"often than any target warrants",
                  n=len(judged_models), examples=examples)

    # R17: did this eval measure anything at all? A model whose every record
    # came back uncheckable produced no evidence, and its accuracy is None
    # rather than low. That is a deterministic FACT, not a threshold, so it
    # gates: "no failures" must never be the verdict on a run that measured
    # nothing. R6 still handles the graded question of how high a nonzero
    # uncheckable rate is.
    #
    # Found live by a CSV pod whose multi-target column loaded as the literal
    # string "46|46.0": every record was uncheckable, accuracy was None, and the
    # battery reported INCOMPLETE with no failures.
    scoreable: dict[str, int] = {}
    for entry, r in all_records:
        model = str((entry["manifest"] or {}).get("model"))
        scoreable.setdefault(model, 0)
        if (r.get("score") or {}).get("verdict") in ("pass", "fail", "flag"):
            scoreable[model] += 1
    mute = [f"{m}: 0 scoreable records; this model's accuracy is not low, it is absent"
            for m, n in sorted(scoreable.items()) if n == 0]
    rep.check("R17", not mute,
              f"{len(mute)} of {len(scoreable)} model(s) produced nothing scoreable",
              n=len(scoreable), examples=mute)

    # R18: is the provider billing you for text it did not send? Output tokens
    # are compared against what the RECORDED text can account for. You are
    # charged on the provider's number and you hold the text, so this is the one
    # cross-check available without trusting them.
    #
    # The confound is stated in the finding, because it is large: models that
    # bill hidden reasoning legitimately report far more output tokens than
    # their visible answer contains. That is why this warns rather than gates,
    # and why the threshold is generous. On a model with no hidden reasoning, a
    # persistent gap is worth taking to your invoice.
    billed = {}
    for entry, r in all_records:
        usage = r.get("usage") or {}
        reported = int(usage.get("output_tokens") or 0)
        text = str(r.get("output", ""))
        # A chars/4 estimate has enormous relative error on a two-character
        # answer: "56" is one token by the estimate and three or four in
        # practice once formatting is counted, which reads as 4x overbilling.
        # Judged only on records with enough text for the estimate to mean
        # something. Found by this check false-alarming on two real models.
        if reported <= 0 or len(text) < THRESHOLDS["min_billed_chars"]:
            continue
        accounted = max(1, len(text) / CHARS_PER_TOKEN_EST)
        model = str((entry["manifest"] or {}).get("model"))
        got, exp, n = billed.get(model, (0.0, 0.0, 0))
        billed[model] = (got + reported, exp + accounted, n + 1)
    judged_bills = {m: v for m, v in billed.items() if v[2] >= THRESHOLDS["min_checkable"]}
    if not judged_bills:
        # n/a, not skip. An eval whose answers are bare numbers can never
        # produce output long enough to bill-check: that is the SHAPE of the
        # eval, not a coverage gap the author could close by running more.
        rep.not_applicable("R18", f"no model produced {THRESHOLDS['min_checkable']}+ answers of at "
                                  f"least {THRESHOLDS['min_billed_chars']} characters; short-answer "
                                  "evals cannot be billed against reliably")
    else:
        inflated = []
        for model, (got, exp, n) in sorted(judged_bills.items()):
            ratio = got / exp if exp else 0.0
            if ratio > THRESHOLDS["billing_ratio_max"]:
                inflated.append(f"{model}: billed {got:.0f} output token(s) for text accounting for "
                                f"~{exp:.0f} across {n} record(s) ({ratio:.1f}x)")
        rep.check("R18", not inflated,
                  f"{len(inflated)} of {len(judged_bills)} model(s) report far more output tokens "
                  "than their recorded text accounts for (expected for hidden-reasoning models; "
                  "otherwise check your invoice)",
                  n=len(judged_bills), examples=inflated,
                  evidence={"billed_ratio": {m: round(g / e, 3) if e else None
                                             for m, (g, e, _) in judged_bills.items()}})

    # R19: were these runs produced by the engine that is auditing them?
    #
    # Every manifest already recorded `tool_sha256`. Nothing read it, which
    # made the engine the one input inside the drift boundary that could change
    # without anyone being told. It WARNS rather than gates, because upgrading
    # the tool is normal and bricking every pod on upgrade would teach people
    # to ignore the gate. What it is not allowed to do is stay silent: a scorer
    # fix between the run and the audit changes what the recorded verdicts mean,
    # and re-running is the only way to get numbers that match the report.
    current = engine_fingerprint()
    stamped = {}
    for e in mine:
        m = e["manifest"]
        if m is None or not m.get("tool_sha256"):
            continue
        stamped.setdefault(str(m["tool_sha256"]), []).append(
            f"{m.get('model')} seed {m.get('seed')} (tool {str(m.get('tool_version'))})")
    if not stamped:
        rep.not_applicable("R19", "no run manifest records a tool_sha256")
    else:
        stale = {k: v for k, v in stamped.items() if k != current}
        rep.check("R19", not stale,
                  f"{sum(len(v) for v in stale.values())} of {sum(len(v) for v in stamped.values())} "
                  f"run(s) were produced by a different engine than the one auditing them "
                  f"(now {current[:16]}); re-run to get numbers this report can stand behind",
                  n=sum(len(v) for v in stamped.values()),
                  examples=[f"engine {k[:16]}: {', '.join(v[:3])}"
                            + (f" and {len(v) - 3} more" if len(v) > 3 else "")
                            for k, v in sorted(stale.items())],
                  evidence={"engines": {k[:16]: len(v) for k, v in sorted(stamped.items())}})

    # R20: repeated items that reached no verdict.
    #
    # `run.repeats` exists to average out a nondeterministic target. With an EVEN
    # number of repeats a model can split its own votes, and what happens to
    # those items decides what the headline number MEANS.
    #
    # Measured rather than reasoned about: a target with a known 50% per-item
    # rate over 120 items, with ties scored as failures, reported 24% at
    # repeats=2 and 30% at repeats=4, both behind Wilson intervals that excluded
    # 50% (N-008). Ties are now undecided rather than failed, the same treatment
    # every other unreached verdict gets here, and this check reports how much of
    # the pod that covers. Silence would let a report say "50% on 60 items"
    # without mentioning the 60 items it could not call.
    tied: dict[str, tuple[int, int]] = {}
    any_repeated = False
    for entry in mine:
        m = entry.get("manifest") or {}
        by_item: dict[str, list[int]] = {}
        for r in entry["records"]:
            v = (r.get("score") or {}).get("verdict")
            if v in ("pass", "fail", "flag"):
                by_item.setdefault(str(r.get("item_id")), []).append(1 if v == "pass" else 0)
        if not any(len(v) > 1 for v in by_item.values()):
            continue
        any_repeated = True
        n_ties = sum(1 for v in by_item.values() if v and majority(v) is None)
        if n_ties:
            tied[str(m.get("model"))] = (n_ties, len(by_item))
    declared = int(run_cfg.get("repeats", 1) or 1)
    if not any_repeated:
        rep.not_applicable(
            "R20", "no run on disk repeats an item; a single pass per item cannot tie")
    else:
        share = max((t / n for t, n in tied.values()), default=0.0)
        rep.check("R20", not tied,
                  f"{len(tied)} model(s) left items undecided: their repeats split evenly, so the "
                  f"majority vote reached no verdict and those items are excluded from accuracy "
                  f"rather than scored 0. An ODD run.repeats decides every item and removes this "
                  f"entirely (this spec declares {declared})",
                  n=len(mine),
                  examples=[f"{m}: {t} of {n} item(s) tied ({t / n:.0%})"
                            for m, (t, n) in sorted(tied.items())],
                  evidence={"repeats": declared, "max_tied_share": round(share, 4)})

    # R16: is the SCORER the thing that is failing? An answer marked wrong whose
    # text plainly contains the reference answer was not necessarily wrong; the
    # scorer may be measuring format. One such record is a judgement call, but a
    # high RATE means the eval is measuring presentation and reporting it as
    # capability.
    #
    # Found live: a numeric scorer that extracts the FIRST number met models
    # that show their working ("7 notebooks at $4 = $28 ... total $46") and
    # scored almost every correct answer wrong. The battery reported "four of
    # five models are at chance" and never said why.
    #
    # A DENIED mention does not count: "not 46" contains 46 and a scorer is
    # right to fail it, which is exactly what the dry provider emits.
    misses: dict[str, list[int]] = {}
    for entry, r in all_records:
        if (r.get("score") or {}).get("verdict") != "fail" or "output" not in r:
            continue
        item = item_by_id.get(str(r.get("item_id")))
        if item is None:
            continue
        text = _norm(r.get("output") or "")
        present = 0
        for t in _targets_of(item):
            needle = _norm(t)
            at = _whole_mention(text, needle)
            if at is None:
                continue
            before = text[:at].split()
            if before and before[-1] in NEGATORS:
                continue
            present = 1
            break
        misses.setdefault(str((entry["manifest"] or {}).get("model")), []).append(present)
    judged_misses = {m: v for m, v in misses.items() if len(v) >= THRESHOLDS["min_scored_misses"]}
    if not judged_misses:
        rep.skip("R16", f"no model has {THRESHOLDS['min_scored_misses']}+ failed records to inspect")
    else:
        suspect = []
        for model, flags in sorted(judged_misses.items()):
            share = sum(flags) / len(flags)
            if share > THRESHOLDS["contains_target_max"]:
                suspect.append(f"{model}: {sum(flags)} of {len(flags)} failed answer(s) ({share:.0%}) "
                               "contain the reference answer verbatim")
        rep.check("R16", not suspect,
                  f"{len(suspect)} of {len(judged_misses)} model(s) are failed on answers that "
                  "contain the reference; the scorer may be grading format, not correctness",
                  n=len(judged_misses), examples=suspect)

    # R22: a failed answer that is the same NUMBER as its target. R16 above
    # catches a wrong answer that CONTAINS the reference as text; this catches the
    # one it cannot, where the strings differ but the numbers do not. An exact
    # scorer marks "1/2" wrong against a key of "0.5", or "1,000" wrong against
    # "1000", so a model that computed the right value is scored as if it missed.
    # The run-time mirror of S18, and the same F-002 severity: accuracy is
    # understated and a fleet ranking can flip on it.
    #
    # Diagnostic, not a gate: a task may deliberately require a specific FORM
    # ("write it as a fraction"), where "0.5" against a key of "1/2" is genuinely
    # wrong, so the tool surfaces the candidate and the author decides.
    numeric_fails, numeric_misses = 0, []
    for entry, r in all_records:
        if (r.get("score") or {}).get("verdict") != "fail" or "output" not in r:
            continue
        item = item_by_id.get(str(r.get("item_id")))
        if item is None:
            continue
        num_targets = [t for t in _targets_of(item) if _as_number(t) is not None]
        if not num_targets:
            continue
        numeric_fails += 1
        out_val = _as_number(r.get("output"))
        if out_val is None:
            continue
        if any(abs(out_val - _as_number(t)) <= 1e-9 * max(1.0, abs(_as_number(t))) for t in num_targets):
            model = str((entry["manifest"] or {}).get("model"))
            numeric_misses.append(f"{model} / {r.get('item_id')}: answer {str(r.get('output'))!r} "
                                  f"equals its target as a number, but was scored fail")
    if not numeric_fails:
        rep.not_applicable("R22", "no failed record has a numeric target, so there is no "
                                  "numeric-equivalent miss to look for")
    else:
        rep.check("R22", not numeric_misses,
                  f"{len(numeric_misses)} of {numeric_fails} numeric-target failure(s) equal their "
                  f"target as a number; the scorer may be rejecting a correct value in the wrong form",
                  n=numeric_fails, examples=numeric_misses[:8])

    # R7: distinguishable from guessing. The floor is the WORSE of uniform
    # per-item chance and the informed-guesser cap (always answer the modal
    # target): a skewed answer key makes 1/k flattery, not a baseline.
    #
    # PER MODEL, never pooled. A pooled fleet accuracy hides the one examinee
    # sitting at chance behind five competent ones, which is the same
    # flattering-pooling defect R13 was fixed for in v0.17.0 and T4/T6 were
    # built against. Found here by a live 1B model that answered every item
    # identically: pooled accuracy was 71% and this check passed.
    #
    # No early return: any check appended after R7 must still run.
    by_model: dict[str, list[str]] = {}
    for entry, r in all_records:
        v = (r.get("score") or {}).get("verdict")
        if v in ("pass", "fail", "flag"):
            by_model.setdefault(str((entry["manifest"] or {}).get("model")), []).append(v)
    judged = {m: v for m, v in by_model.items() if len(v) >= THRESHOLDS["min_checkable"]}
    total_checkable = sum(len(v) for v in by_model.values())
    if not judged:
        rep.skip("R7", f"no model has {THRESHOLDS['min_checkable']}+ checkable records "
                       f"({total_checkable} in total)")
        return
    floor = chance["floor"]
    source = "modal target" if chance["modal"] >= chance["uniform"] else "uniform choice"
    accs = {m: v.count("pass") / len(v) for m, v in judged.items()}
    guessers = [f"{m}: {acc:.0%} on {len(judged[m])} checkable, at or below the {floor:.0%} floor"
                for m, acc in sorted(accs.items()) if acc <= floor + THRESHOLDS["guess_margin"]]
    best, worst = max(accs.values()), min(accs.values())
    rep.check("R7", not guessers,
              f"{len(guessers)} of {len(accs)} model(s) score no better than guessing; fleet spans "
              f"{worst:.0%} to {best:.0%} vs chance ~{floor:.0%} ({source} floor)",
              n=len(accs), examples=guessers,
              evidence={"per_model_accuracy": {m: round(a, 4) for m, a in accs.items()},
                        "chance_floor": round(floor, 4),
                        "uniform": round(chance["uniform"], 4), "modal": round(chance["modal"], 4),
                        "modal_target": chance["modal_target"]})


# --------------------------------------------------------------------------- fleet


def _fleet_matrices(runs: list[dict]) -> tuple[dict, dict]:
    """(matrix, outputs) attributed through MANIFESTS, not record claims.

    Records in a manifest-less run are excluded (that run already fails R1),
    and records disagreeing with their manifest's identity are excluded here
    (they are flagged by R4). Repeat ties score 0: the conservative side.
    """
    votes: dict[str, dict[str, list[int]]] = {}
    outputs: dict[str, dict[str, str]] = {}
    for entry in runs:
        m = entry["manifest"]
        if m is None:
            continue
        model = str(m.get("model"))
        for r in entry["records"]:
            verdict = (r.get("score") or {}).get("verdict")
            if verdict not in ("pass", "fail"):
                continue
            if r.get("model") != m.get("model"):
                continue
            item_id = str(r.get("item_id"))
            votes.setdefault(model, {}).setdefault(item_id, []).append(1 if verdict == "pass" else 0)
            outputs.setdefault(model, {})[item_id] = _norm(r.get("output", ""))
    # Same tie rule as the summary, from the same function. A tied item is
    # ABSENT from that model's row rather than scored 0: an undecided cell is
    # not a failed cell, and P4 reports the raggedness rather than every fleet
    # mean quietly absorbing it.
    matrix = {
        m: {i: out for i, vs in d.items() if (out := majority(vs)) is not None}
        for m, d in votes.items()
    }
    return matrix, outputs


def _ordering_check(rep: Reporter, spec: dict, matrix: dict) -> None:
    """P6: a spec that entitles itself to an ordering claim must have the
    ordering survive a paired item bootstrap (far tighter than comparing two
    independent intervals, because every model is scored on the same
    resampled items). Specs that claim no ordering are n/a."""
    claims = [c.lower() for c in (spec.get("entitled_claims") or [])]
    if not any(w in c for c in claims for w in ORDERING_WORDS):
        rep.not_applicable("P6", "no entitled claim asserts a model ordering")
        return
    models = sorted(matrix)
    if len(models) < 2:
        rep.skip("P6", "an ordering claim needs at least 2 models on disk")
        return
    common = common_items(matrix)
    if not common:
        rep.skip("P6", "no common items across models")
        return
    pairs = bootstrap_rank_stability(matrix, int(spec["run"]["seed"]),
                                     trials=int(THRESHOLDS["bootstrap_trials"]))
    max_flip = THRESHOLDS["ordering_flip_rate"]
    blurred = [f"{a} vs {b}: order flips or ties in {rate:.0%} of {int(THRESHOLDS['bootstrap_trials'])} "
               f"paired resamples"
               for a, b, rate in pairs if rate > max_flip]
    rep.check("P6", not blurred,
              f"{len(blurred)} adjacent pair(s) in the claimed ordering are within sampling noise "
              f"on {len(common)} common item(s) (paired item bootstrap)",
              n=len(models), examples=blurred)


def _seed_check(rep: Reporter, runs: list[dict], spec: dict) -> None:
    """P10: how much of the number is the seed?

    A spec declaring `run.seeds` repeats the WHOLE eval under each one, so item
    selection and provider sampling both move. The spread across those runs is
    the honest error bar on a headline figure, and it is a different quantity
    from the Wilson interval: the interval covers sampling error on a FIXED item
    set, while this covers the choice of item set and the model's own
    variability together. A number that moves when only the seed moves was never
    the model's number.

    Per model. Pooling seeds would average away the very spread being measured.
    """
    declared = [int(s) for s in (spec["run"].get("seeds") or [])]
    if not declared:
        rep.not_applicable("P10", "the spec declares no extra seeds; a single seed cannot show "
                                  "its own spread (run.seeds is how you ask)")
        return
    by_model: dict[str, dict[int, tuple[int, int]]] = {}
    for e in runs:
        m = e["manifest"]
        if m is None or (m.get("status") != "complete"):
            continue
        model, seed = str(m.get("model")), m.get("seed")
        scored = [(r.get("score") or {}).get("verdict") for r in e["records"]]
        checkable = [v for v in scored if v in ("pass", "fail", "flag")]
        if len(checkable) < THRESHOLDS["min_checkable"]:
            continue
        by_model.setdefault(model, {})[seed] = (checkable.count("pass"), len(checkable))
    judged = {m: s for m, s in by_model.items() if len(s) >= 2}
    if not judged:
        rep.skip("P10", "fewer than 2 complete seeds per model on disk; run the spec again after "
                        "declaring run.seeds")
        return
    wobbly = []
    spreads = {}
    for model, seeds in sorted(judged.items()):
        accs = {s: p / n for s, (p, n) in seeds.items()}
        lo_s = min(accs, key=accs.get)
        hi_s = max(accs, key=accs.get)
        spread = accs[hi_s] - accs[lo_s]
        # Each seed draws its OWN item sample, so the two accuracies are
        # independent and the band is the unpaired one.
        band = _unpaired_band(accs[lo_s], seeds[lo_s][1], accs[hi_s], seeds[hi_s][1])
        spreads[model] = {"spread": round(spread, 4), "noise_band": round(band, 4)}
        # Both bars, deliberately: significant AND large enough to matter. A
        # 2-point spread at n=20000 clears the band and is still not a finding.
        if spread > band and spread > THRESHOLDS["seed_spread_min"]:
            wobbly.append(f"{model}: {accs[lo_s]:.0%} at seed {lo_s} vs {accs[hi_s]:.0%} at seed "
                          f"{hi_s} (spread {spread:.0%} across {len(accs)} seeds, "
                          f"vs {band:.0%} explainable by the item sample)")
    rep.check("P10", not wobbly,
              f"{len(wobbly)} of {len(judged)} model(s) move between seeds by more than the item "
              "sample explains; that much of the headline number belongs to the seed",
              n=len(judged), examples=wobbly, evidence={"seed_spread": spreads})


def _unpaired_band(p1: float, n1: int, p2: float, n2: int) -> float:
    """How far two accuracies from DIFFERENT item samples move on noise alone.

    Returns z standard errors of the difference. Anything inside this is a
    number the sample chose, not one the model earned.
    """
    se = math.sqrt(p1 * (1 - p1) / max(n1, 1) + p2 * (1 - p2) / max(n2, 1))
    return THRESHOLDS["noise_z"] * se


def _paired_band(discordant: int, n: int) -> float:
    """Same, for the SAME items scored twice (McNemar).

    Paired data is more sensitive than unpaired, because every item that scored
    the same way both times contributes nothing to the difference and nothing
    to its error. Only the discordant pairs carry either.
    """
    if n <= 0:
        return float("inf")
    return THRESHOLDS["noise_z"] * math.sqrt(max(discordant, 0)) / n


def _order_check(rep: Reporter, probes: list[dict], real_runs: list[dict]) -> None:
    """P9: does the model answer the QUESTION, or the position of the answer?

    Compares each model's accuracy on the pod's own option order against the
    same items with the options permuted. A model that only holds up in one
    arrangement was partly reading the layout, and the single-order number
    overstates it. Per model, never pooled.

    This measures INFERENCE-time presentation sensitivity, which is a different
    claim from S3's answer-key skew: S3 reads the dataset at rest, P9 needs the
    model in the loop, and a dataset can be clean on one and not the other.
    """
    shuffles = [e for e in probes if (e["manifest"] or {}).get("probe") == "shuffle"]
    if not shuffles:
        if any(e["manifest"] and not e["manifest"].get("dry_run") for e in real_runs):
            rep.skip("P9", "no shuffle probe on disk; set data.render_choices and run "
                           "`dinostomp run <spec> --probe shuffle` to unlock")
        else:
            rep.not_applicable("P9", "presentation-order probes need a real provider; this pod's "
                                     "runs are all local")
        return

    def verdicts(entries):
        """Per model, per ITEM. The pairing is the whole point: the shuffle
        probe re-runs the SAME items, and throwing the item ids away turns a
        paired comparison into a weaker unpaired one for no reason."""
        out: dict[str, dict[str, str]] = {}
        for e in entries:
            model = str((e["manifest"] or {}).get("model"))
            for r in e["records"]:
                v = (r.get("score") or {}).get("verdict")
                if v in ("pass", "fail", "flag"):
                    out.setdefault(model, {})[str(r.get("item_id"))] = v
        return out

    original, permuted = verdicts(real_runs), verdicts(shuffles)
    paired = {}
    for m, before in original.items():
        after = permuted.get(m)
        if not after:
            continue
        both = sorted(set(before) & set(after))
        if len(both) < THRESHOLDS["min_checkable"]:
            continue
        # McNemar: only items that CHANGED verdict carry the difference, and
        # only they carry its error.
        broke = sum(1 for i in both if before[i] == "pass" and after[i] != "pass")
        fixed = sum(1 for i in both if before[i] != "pass" and after[i] == "pass")
        n = len(both)
        paired[m] = (sum(1 for i in both if before[i] == "pass") / n,
                     sum(1 for i in both if after[i] == "pass") / n,
                     broke, fixed, n)
    if not paired:
        rep.skip("P9", f"no model has {THRESHOLDS['min_checkable']}+ items scored in BOTH "
                       "the original and the permuted order")
        return
    swung = []
    for m, (a, b, broke, fixed, n) in sorted(paired.items()):
        band = _paired_band(broke + fixed, n)
        if abs(a - b) > band and abs(a - b) > THRESHOLDS["order_swing_min"]:
            swung.append(f"{m}: {a:.0%} in the pod's order vs {b:.0%} permuted "
                         f"(moves {b - a:+.0%} on {broke + fixed} of {n} items that flipped, "
                         f"vs {band:.0%} explainable by that churn)")
    rep.check("P9", not swung,
              f"{len(swung)} of {len(paired)} model(s) move more than "
              "the flip churn explains when the options are re-ordered; that part of "
              "the score is layout, not knowledge",
              n=len(paired), examples=swung,
              evidence={"swing": {m: {"moves": round(b - a, 4), "flipped": broke + fixed,
                                       "noise_band": round(_paired_band(broke + fixed, n), 4)}
                                   for m, (a, b, broke, fixed, n) in paired.items()}})


def _psychometric_checks(rep: Reporter, runs: list[dict], spec: dict,
                         collapsed: dict | None = None) -> None:
    if not runs:
        for cid in PSYCHO_CHECK_IDS:
            rep.skip(cid, "no runs on disk yet")
        return

    matrix, outputs = _fleet_matrices(runs)
    models = sorted(matrix)
    collapsed = collapsed or {}
    _ordering_check(rep, spec, matrix)
    min_fleet = int(THRESHOLDS["min_fleet"])
    if len(models) < 2:
        hint = f"only {len(models)} model(s) on disk; run a fleet of {min_fleet}+ to unlock psychometrics"
        for cid in ("P1", "P2", "P3", "P4", "P5", "P7", "P8"):
            rep.skip(cid, hint)
        return

    # P4: matrix completeness (gating; a ragged matrix quietly biases every mean).
    #
    # Asked, not scored. An item whose answer came back UNCHECKABLE was still
    # put to the model: that is a scoring outcome, already excluded from every
    # denominator by design and already surfaced by R6 and R12. Gating on it
    # here would mean any pod where one model produces an unparseable answer
    # goes BROKEN, which contradicts the uncheckable doctrine outright. Found
    # live, firing on two of three real pods for exactly that wrong reason.
    # What P4 is actually for is a model that was never ASKED some item.
    asked: dict[str, set[str]] = {}
    for entry in runs:
        m = entry["manifest"]
        if m is None:
            continue
        for r in entry["records"]:
            if r.get("model") == m.get("model"):
                asked.setdefault(str(m.get("model")), set()).add(str(r.get("item_id")))
    union = set().union(*asked.values()) if asked else set()
    ragged = [f"{m}: never asked {len(union - asked.get(m, set()))} item(s)"
              for m in models if asked.get(m, set()) != union]
    rep.check("P4", not ragged, f"{len(ragged)} of {len(models)} model(s) were asked a different item set",
              n=len(models), examples=ragged)

    common = common_items(matrix)
    min_items = int(THRESHOLDS["min_items_psycho"])

    # P7/P8: is there anything left to measure here? A fleet pinned at a
    # ceiling (saturation, or a mis-keyed dataset scored leniently) or spread
    # across no range at all passes every other check while measuring nothing.
    if common:
        accs = {m: sum(matrix[m][i] for i in common) / len(common) for m in models}
        hi, lo = max(accs.values()), min(accs.values())
        pinned = []
        if lo >= THRESHOLDS["ceiling_acc"]:
            pinned.append(f"every model scores at or above {THRESHOLDS['ceiling_acc']:.0%} "
                          f"(min {lo:.0%}); the eval is saturated")
        if hi <= THRESHOLDS["floor_acc"]:
            pinned.append(f"every model scores at or below {THRESHOLDS['floor_acc']:.0%} "
                          f"(max {hi:.0%}); broken key or impossibly hard")
        rep.check("P7", not pinned, f"fleet accuracy spans {lo:.0%} to {hi:.0%} on {len(common)} item(s)",
                  n=len(models), examples=pinned, evidence={"min": round(lo, 4), "max": round(hi, 4)})
        spread = hi - lo
        rep.check("P8", spread >= THRESHOLDS["min_dynamic_range"],
                  f"fleet spread {spread:.0%} across {len(models)} model(s) on {len(common)} item(s)",
                  n=len(models), evidence={"spread": round(spread, 4)})
    else:
        rep.skip("P7", "no common items across models")
        rep.skip("P8", "no common items across models")

    # A collapsed examinee (one answer to everything, see R14) carries no
    # information about item difficulty, and including it actively DISTORTS
    # discrimination: it scores full marks on every item keyed to its constant
    # answer regardless of difficulty, which drags those items' point-biserials
    # negative and makes them look like key errors. Found live, and it mattered:
    # a constant-answering 1B model produced 8 phantom "candidate key errors"
    # that dropped to 1 the moment it was excluded. Dropping it is the
    # statistically correct call, and saying so out loud is the honest one.
    psycho_matrix = {m: row for m, row in matrix.items() if m not in collapsed}
    dropped = (f"; excluded {len(collapsed)} collapsed model(s) "
               f"({', '.join(sorted(collapsed))}), which carry no difficulty signal"
               if collapsed else "")
    psycho_models = sorted(psycho_matrix)
    psycho_common = common_items(psycho_matrix) if psycho_matrix else []

    if len(psycho_models) < min_fleet or len(psycho_common) < min_items:
        reason = (f"{len(psycho_models)} model(s) x {len(psycho_common)} common item(s); "
                  f"need {min_fleet}+ models and {min_items}+ items to unlock{dropped}")
        for cid in ("P1", "P2", "P3"):
            rep.skip(cid, reason)
    else:
        cells = len(psycho_models) * len(psycho_common)

        r = kr20(psycho_matrix)
        if r is None:
            rep.check("P1", False, "fleet score totals have no variance; reliability is undefined here", n=cells)
        else:
            caveat = (f"; small fleet ({len(psycho_models)} examinees), treat as a noisy estimate"
                      if len(psycho_models) < SMALL_FLEET else "")
            rep.check("P1", r >= THRESHOLDS["kr20_min"],
                      f"KR-20 {r:.2f} across {len(psycho_models)} models x {len(psycho_common)} "
                      f"items{caveat}{dropped}",
                      n=cells, evidence={"kr20": round(r, 4), "n_examinees": len(psycho_models),
                                         "excluded_collapsed": sorted(collapsed)})

        rpb = point_biserials(psycho_matrix)
        neg = [f"{i} (r_pb {v:.2f})" for i, v in sorted(rpb.items())
               if v is not None and v <= THRESHOLDS["negative_discrimination"]]
        # A raw count of negative discriminations is not a finding: it was
        # reporting 31 of 303 GSM8K items as candidate key errors, which is
        # what chance does at four examinees. P2 now clears the 95th percentile
        # of a null that holds BOTH margins fixed before it says anything.
        #
        # P2 IS ONE-SIDED, and the pass message says so rather than letting a
        # quiet result read as a clean answer key. Measured power, 200 items,
        # 10% of keys inverted, five replicates per point:
        #
        #     6 models   0/5 detected     0/5 false alarms
        #    12 models   2/5              0/5
        #    24 models   3/5              0/5
        #    40 models   5/5              0/5
        #
        # So: when it fires, believe it. When it is quiet on a small fleet, it
        # has told you nothing. A fixed-margins null is nearly degenerate with
        # few examinees, since holding every model total and every item total
        # fixed leaves almost no freedom to permute, and the null then tracks
        # whatever it is given. That is the cost of never false-alarming, and
        # the alternative was a check that manufactures findings.
        null_95 = negative_rpb_null(psycho_matrix, THRESHOLDS["negative_discrimination"],
                                    THRESHOLDS["bootstrap_trials"])
        fired = len(neg) > null_95
        underpowered = ("" if len(psycho_models) >= THRESHOLDS["min_fleet_discrimination"]
                        else f"; at {len(psycho_models)} examinees this check has little power, "
                             "so a quiet result is NOT evidence of a clean answer key")
        rep.check("P2", not fired,
                  f"{len(neg)} item(s) that strong models miss and weak models hit, against "
                  f"{null_95} expected by chance at this fleet size; candidate key "
                  f"errors{dropped}{'' if fired else underpowered}",
                  n=len(psycho_common), examples=neg[:12] if fired else [],
                  evidence={"excluded_collapsed": sorted(collapsed), "negative_rpb": len(neg),
                            "chance_95th": null_95, "n_examinees": len(psycho_models),
                            "underpowered": bool(underpowered)})

        all_right, all_wrong = dead_items(psycho_matrix)
        share = (len(all_right) + len(all_wrong)) / len(psycho_common)
        common = psycho_common
        # How much of this is just having a small fleet? With k examinees at
        # these accuracies and NO item-difficulty structure at all, this share
        # would still be dead. Reported beside the observation because dead
        # weight falls as the fleet grows, so the raw number is partly a
        # statement about how many models you ran. It is not subtracted: a real
        # dataset has difficulty structure, which pushes the true floor higher,
        # and quietly netting it off would understate the waste.
        skills = [sum(psycho_matrix[m][i] for i in common) / len(common)
                  for m in sorted(psycho_matrix)]
        floor = 1.0
        for p_i in skills:
            floor *= p_i
        wrong_floor = 1.0
        for p_i in skills:
            wrong_floor *= (1 - p_i)
        indep = floor + wrong_floor
        rep.check("P3", share <= THRESHOLDS["dead_weight_max"],
                  f"{share:.0%} of {len(common)} item(s) separate nobody "
                  f"({len(all_right)} all-right, {len(all_wrong)} all-wrong); "
                  f"{indep:.0%} would be dead at {len(skills)} examinees even with no difficulty "
                  "structure, so part of this is fleet size",
                  n=len(common), evidence={"share": round(share, 4),
                                           "independence_floor": round(indep, 4),
                                           "n_examinees": len(skills)})

    # P5: unanimous identical wrong answers (the fleet agrees; the key does not)
    if len(models) < int(THRESHOLDS["min_fleet_agree"]):
        rep.skip("P5", f"{len(models)} model(s); need {int(THRESHOLDS['min_fleet_agree'])}+ to call unanimity")
        return
    unanimous = []
    for i in common_items(matrix):
        if any(matrix[m][i] != 0 for m in models):
            continue
        texts = {outputs.get(m, {}).get(i) for m in models}
        if len(texts) == 1 and None not in texts:
            unanimous.append(f"{i}: every model answered {next(iter(texts))!r}")
    rep.check("P5", not unanimous,
              f"{len(unanimous)} item(s) where the whole fleet gave one identical wrong answer; candidate key errors",
              n=len(common_items(matrix)), examples=unanimous)


# --------------------------------------------------------------------------- entry


def pod_code_paths(spec: dict) -> list[str]:
    """Pod-local Python that LINTING would have to import, and therefore run.

    Only the scorer and a python judge are imported at lint time. A python
    TARGET is merely hashed here (it runs during `run`, not `stomp`), so it does
    not belong on this list.
    """
    out = []
    scorer = spec.get("scorer") or {}
    if scorer.get("kind") == "python" and scorer.get("code"):
        out.append(str(scorer["code"]))
    judge = scorer.get("judge") or {}
    if judge.get("provider") == "python" and judge.get("entrypoint"):
        out.append(str(judge["entrypoint"]))
    # A mounted .py is code from OUTSIDE the pod, which if anything deserves
    # more suspicion than the pod's own, so it faces the same refusal.
    out.extend(str(m) for m in (spec.get("mounts") or []) if str(m).endswith(".py"))
    return out


def lint_eval(spec_path: str | Path, trust_code: bool = False,
              references: dict[str, list[dict]] | None = None,
              use_extensions: bool = True) -> tuple[dict | None, list[Issue]]:
    """Stomp one eval pod. Returns (report, issues); report is None only when
    the spec, data, or scorer could not be loaded at all."""
    spec_file = Path(spec_path).resolve()
    spec, issues = load_spec(spec_file)
    if spec is None or issues:
        return None, issues
    base = spec_file.parent
    items, data_issues = load_items(spec["data"], base)
    if data_issues:
        return None, data_issues
    # SECURITY. Importing a pod's scorer or judge EXECUTES it, and the workflow
    # this tool advertises is "clone a stranger's pod and verify it". So the
    # default is to refuse, and to be coverage-honest about what that costs:
    # the checks that need the code SKIP with the reason, rather than the tool
    # silently running someone else's Python to reassure you about their
    # numbers. `--trust-code` is the deliberate opt-in.
    code_paths = pod_code_paths(spec)
    scorer = None
    code_refused = ""
    if code_paths and not trust_code:
        code_refused = ("this pod ships Python that linting would have to IMPORT and therefore "
                        f"RUN ({', '.join(code_paths)}); re-run with --trust-code if you have "
                        "read it and accept that")
    else:
        try:
            scorer = make_scorer(spec["scorer"], base)
        except (ValueError, ProviderError) as exc:
            return None, [Issue(loc="$.scorer", message=str(exc), check="scorer")]

    rep = Reporter()
    _item_checks(rep, items)
    _asset_checks(rep, items, base)
    _canary_check(rep, base, spec["data"])
    _authorship_check(rep, spec)
    rep.not_applicable("S17", "an eval pod's items are questions and answers, not a feature table; "
                              "the single-column leak scan is for a raw tabular dataset audit")
    # A pod's dataset deserves the overlap check as much as a bare file does.
    _overlap_check(rep, items, references or {})

    # W1: mutation-test the witnesses. The gate proves the scorer can fail;
    # this measures whether the witnesses would notice a scorer failing WRONG.
    if scorer is None:
        rep.skip("W1", code_refused)
        gauntlet = None
    elif not getattr(scorer, "offline_replayable", True):
        rep.skip("W1", "hosted judge: the mutation gauntlet would re-invoke it once per mutant "
                       "per witness, which a lint must never pay for; run the judge probe instead")
        gauntlet = None
    else:
        gauntlet = run_gauntlet(scorer, spec["scorer"]["witnesses"], items)
    if gauntlet is not None:
        rep.check(
            "W1", not gauntlet.survived,
            f"{len(gauntlet.survived)} of {gauntlet.n_applicable} applicable mutant scorer(s) "
            f"survive the witness suite",
            n=gauntlet.n_applicable,
            examples=[f"{m.name} ({m.bug_class}) survives; add {m.suggestion}" for m in gauntlet.survived],
            evidence={"killed": gauntlet.killed, "not_applicable": gauntlet.not_applicable},
        )

    # W2: W1 pointed the other way. W1 only catches a scorer that credits too
    # much; this catches one that LOSES a correct answer to the shape it arrived
    # in, which is invisible to the witness suite because no author writes a
    # witness for a form they never imagined a model would emit.
    if scorer is None:
        rep.skip("W2", code_refused)
    elif not getattr(scorer, "offline_replayable", True):
        rep.skip("W2", "hosted judge: re-invoking it once per shape per target is a cost "
                       "a lint must never incur; run the judge probe instead")
    else:
        shapes = run_shape_gauntlet(scorer, items)
        if shapes.n_applicable == 0:
            # n/a, not skip. A scorer that demands the bare string is a
            # comparator, not a parser: it rejects a trailing full stop on
            # purpose. That is a structural fact about the scorer, not evidence
            # we failed to gather, and calling it a skip would drag every
            # exact-match pod from "sound" to "incomplete" for no reason.
            rep.not_applicable("W2", "this scorer compares exactly rather than extracting, so "
                                     "surface-form robustness is not a property it claims")
        else:
            broken = shapes.lost + shapes.leaked
            rep.check(
                "W2", not broken,
                f"{len(shapes.lost)} surface form(s) lose a correct answer and "
                f"{len(shapes.leaked)} credit a decoy, of {shapes.n_applicable} applicable",
                n=shapes.n_applicable,
                examples=[f"{s.name} ({s.bug_class}); {s.suggestion}" for s in broken],
                evidence={"baseline_form": shapes.form, "held": shapes.held,
                          "not_applicable": shapes.not_applicable},
            )

    # W3: a scorer that hands out partial credit has to PROVE it grades. A
    # "graded" scorer that only ever returns 0/1 is a binary scorer wearing a
    # float, and the accuracy and the partial score would then be the same
    # number sold as two. So if the scorer emits an intermediate value on any
    # witness, at least one witness must pin an intermediate expect_value (which
    # R2 then verifies it actually hits), and every value it emits must be in
    # [0,1]. A scorer that never grades is n/a, not a pass.
    witnesses = spec["scorer"].get("witnesses") or []
    if scorer is None:
        rep.skip("W3", code_refused)
    elif not getattr(scorer, "offline_replayable", True):
        rep.skip("W3", "hosted judge: a graded judge's gradation is checked by the judge probe")
    else:
        emitted, out_of_range = [], []
        for w in witnesses:
            try:
                val = scorer(w["output"], w["target"]).value
            except Exception:  # noqa: BLE001 - a scorer that crashes here is W1/R2's problem
                continue
            if val is None:
                continue
            val = float(val)
            emitted.append(val)
            if not (0.0 <= val <= 1.0):
                out_of_range.append(val)
        graded = [v for v in emitted if 0.0 < v < 1.0]
        pinned_partial = [w for w in witnesses
                          if isinstance(w.get("expect_value"), (int, float))
                          and 0.0 < float(w["expect_value"]) < 1.0]
        if not graded and not out_of_range:
            rep.not_applicable("W3", "this scorer does not emit intermediate partial credit, so "
                                     "there is no gradation to witness")
        else:
            problems = []
            if out_of_range:
                problems.append(f"{len(out_of_range)} witness value(s) outside [0,1], "
                                f"e.g. {out_of_range[0]}")
            if graded and not pinned_partial:
                problems.append("emits partial credit but no witness pins an intermediate "
                                "expect_value (0<v<1), so the gradation is unproven")
            rep.check(
                "W3", not problems,
                "; ".join(problems) or "gradation is witnessed and in range",
                n=len(witnesses),
                examples=problems,
                evidence={"n_graded_witness_values": len(graded),
                          "n_partial_witnesses": len(pinned_partial)},
            )

    choice_items = [i for i in items if "choices" in i]
    uniform = (sum(1.0 / len(i["choices"]) for i in choice_items) / len(choice_items)
               if choice_items else 0.0)
    modal_share, modal_target = _modal_target_share(items)
    chance = {"uniform": uniform, "modal": modal_share,
              "modal_target": modal_target, "floor": max(uniform, modal_share)}

    discovered, foreign = _discover_runs(base, spec["name"])
    probes = [e for e in discovered if (e["manifest"] or {}).get("probe")]
    mine = [e for e in discovered if not (e["manifest"] or {}).get("probe")]
    _witness_check(rep, spec, scorer, mine, code_refused)
    _run_checks(rep, mine, foreign, spec_file, spec, items, chance, scorer)
    _blind_check(rep, probes, mine, chance)
    _regurgitation_check(rep, probes, mine)
    _order_check(rep, probes, mine)
    _seed_check(rep, mine, spec)
    _template_checks(rep, probes, mine)
    _trajectory_checks(rep, mine, spec, items, probes)
    _judge_checks(rep, probes, mine, spec)
    _self_preference_check(rep, probes, mine, spec)
    _psychometric_checks(rep, mine, spec,
                         collapsed_models(mine, chance['modal'],
                                          THRESHOLDS['collapse_exclude_share']))

    claim_results = None
    if not spec.get("claims"):
        rep.not_applicable("C1", "no typed claims declared")
    elif not mine:
        rep.skip("C1", "no runs on disk yet")
    else:
        matrix, _ = _fleet_matrices(mine)
        claim_results = evaluate_claims(spec, mine, matrix)
        failed = [f"{c.description}: {r.name} FAILED ({r.detail})"
                  for c in claim_results for r in c.requirements if not r.ok]
        n_reqs = sum(len(c.requirements) for c in claim_results)
        multi = (f" (no multiplicity correction across {len(claim_results)} claims)"
                 if len(claim_results) > 1 else "")
        rep.check("C1", not failed,
                  f"{sum(1 for c in claim_results if c.supported)} of {len(claim_results)} typed claim(s) "
                  f"supported across {n_reqs} evidence requirement(s){multi}",
                  n=n_reqs, examples=failed)

    inventory = [
        {
            "run_file": e["path"].name,
            "model": (e["manifest"] or {}).get("model"),
            "model_reported": (e["manifest"] or {}).get("model_reported"),
            "provider": (e["manifest"] or {}).get("provider"),
            "dry_run": bool((e["manifest"] or {}).get("dry_run")),
            "seed": (e["manifest"] or {}).get("seed"),
            "records": len(e["records"]),
            "uncheckable": sum(1 for r in e["records"]
                               if (r.get("score") or {}).get("verdict") == "uncheckable"),
            # Spend a target priced itself is a claim, not a meter reading; the
            # inventory says which so the report never implies it was audited.
            "spend_source": (e["manifest"] or {}).get("spend_source"),
            "trajectory_steps": sum(len(r.get("trajectory") or []) for r in e["records"]),
        }
        for e in mine
    ]
    run_n = min(int(spec["run"]["n"]), len(items))
    mde = min_detectable_effect(run_n)
    report_inputs = _expected_hashes(spec_file, spec)
    target_hashes = _expected_target_hashes(spec_file, spec)
    if target_hashes:
        report_inputs["target_sha256"] = target_hashes
    # Extensions widen what the battery looks for. They run last, they get a
    # write-only collector, and THRESHOLDS is fingerprinted around them.
    loaded, ext_findings, ext_problems = [], [], []
    if use_extensions:
        loaded, ext_problems = discover({cid for cid, *_ in CHECKS})
        if loaded:
            ctx = {"spec": spec, "items": items, "runs": mine, "probes": probes,
                   "spec_path": spec_file}
            # Snapshot around the window where extension code actually EXECUTES.
            # An earlier version compared before and after the merge loop, where
            # no extension code runs, so the guard could not fire; the test that
            # tried to sabotage it is what proved that.
            core_before = {cid: (f.level, f.detail) for cid, f in rep.findings.items()}
            ext_findings, run_problems = run_extensions(loaded, ctx, THRESHOLDS)
            if {cid: (f.level, f.detail) for cid, f in rep.findings.items()} != core_before:
                return None, [Issue(
                    loc="$.extensions", check="extensions",
                    message="a core finding changed while extensions ran; the report is refused. "
                            "Extensions add findings, they never touch one.")]
            ext_problems.extend(run_problems)

    report = rep.report(
        # The spec's name INSIDE the pod, never an absolute path. A published
        # report must re-derive on a stranger's machine, and an absolute path
        # made every report verify only where it was generated: the pod moved,
        # the string changed, the byte-comparison failed. Identity lives in
        # `inputs.spec_sha256`, which is what actually pins the artifact.
        spec_file.name,
        inputs=report_inputs,
        runs=inventory,
        entitled_claims=spec.get("entitled_claims"),
        power={"n_items": run_n,
               "mde_unpaired_80pct": round(mde, 4) if mde else None},
        extensions=ext_findings,
        loaded_extensions=loaded,
    )
    # The RESULTS half. Computed from the same records the checks read, and
    # attached after the verdict because it must never influence one: a hard
    # item is not a defect and an expensive model is not a defect.
    # `mine` excludes probe runs on purpose: a blind or ablate probe is a
    # control, not a result, and pooling one into the accuracy table would
    # report a deliberately handicapped run as the model's score.
    results_matrix, results_outputs = _fleet_matrices(mine)
    report["results"] = results_mod.compute(mine, items, results_matrix, results_outputs)
    if ext_problems:
        report["extension_problems"] = ext_problems
    if claim_results is not None:
        report["claims"] = [c.to_dict() for c in claim_results]
    return report, []


# --------------------------------------------------------------------- dataset


# Checks a bare dataset genuinely cannot reach, and the reason each one is out.
# Stated per group rather than as one blanket message, because "n/a" without a
# reason is how a coverage line stops meaning anything.
DATASET_NA = {
    "no scorer in a dataset audit; point this at an eval pod to reach it":
        ("W1", "R2"),
    "no runs in a dataset audit; point this at an eval pod to reach it":
        ("R1", "R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10", "R11", "R12", "R13",
         "R14", "R15", "R16", "R17", "R18", "R19", "S10",
         "T1", "T2", "T3", "T4", "T5", "T6", "J1", "J2", "J3", "J4",
         "P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10", "P11", "P12"),
    "no typed claims in a dataset audit; point this at an eval pod to reach it":
        ("C1",),
    "no spec in a dataset audit, so no provenance to read; point this at an eval pod to reach it":
        ("S16",),
}


def _dataset_extensions(path: Path, use_extensions: bool) -> tuple[list, list, list]:
    """Run installed extensions against a bare data file.

    Returns (loaded, findings, problems).

    Extensions get the PATH, and they get it before the core has decided whether
    it can read the file at all. Both halves matter. The core dataset audit
    builds a list of every row and so refuses anything over 100MB, which is the
    right rule for a reader that holds everything and the wrong reason for an
    audit not to happen: a check that streams does not care how large the file
    is. Nothing here weakens the cap, which still governs every core check. It
    stops being the reason a streaming extension never gets to look.
    """
    if not use_extensions:
        return [], [], []
    loaded, problems = discover({cid for cid, *_ in CHECKS})
    if not loaded:
        return [], [], problems
    ctx = {"data_path": str(path), "scope": "data", "spec": None, "items": [],
           "runs": [], "probes": [], "spec_path": path}
    findings, run_problems = run_extensions(loaded, ctx, THRESHOLDS)
    return loaded, findings, problems + run_problems


def _extension_only_report(path: Path, reason: str, loaded: list, ext_findings: list) -> dict:
    """A report for a file the core could not read but an extension could.

    Every core check is a skip carrying the reason, so coverage states plainly
    that the battery did not run. The verdict cannot be `sound`: skips make it
    `incomplete` before any extension finding is merged, and a validated
    extension failure takes it to `broken` from there.
    """
    rep = Reporter()
    for cid, *_ in CHECKS:
        rep.skip(cid, reason)
    return rep.report(path.name, inputs={"data_sha256": spec_sha256(path)}, scope="data",
                      extensions=ext_findings, loaded_extensions=loaded)


def lint_dataset(data_path: str | Path, *, field_overrides: dict | None = None,
                 separator: str | None = None,
                 references: dict[str, list[dict]] | None = None,
                 use_extensions: bool = True
                 ) -> tuple[dict | None, list[Issue], dict]:
    """Stomp a bare dataset: no spec, no scorer, no runs, no money.

    Returns (report, issues, context). `context` carries what was inferred so
    the caller can print it: a guess the user cannot see is a guess the user
    cannot correct, and every finding here rests on that guess being right.
    """
    path = Path(data_path).resolve()
    context: dict = {"path": str(path), "notes": [], "mapping": {}, "n_rows": 0}
    if not path.is_file():
        return None, [Issue(loc=str(path), message="file not found", check="data")], context
    if not looks_like_dataset(path):
        return None, [Issue(loc=str(path), check="data",
                            message=f"not a dataset file; expected one of "
                                    f"{', '.join(sorted(DATA_SUFFIXES))}")], context

    loaded, ext_findings, ext_problems = _dataset_extensions(path, use_extensions)
    # An extension that returned only `n/a` looked at the file and disclaimed it.
    # That is not a reason to publish a report the core could not produce.
    claimed = [f for f in ext_findings if f["level"] != "n/a"]

    rows, issues = read_rows(path)
    if issues:
        if claimed:
            context["notes"].append(
                f"the core could not read this file ({issues[0].message}); "
                f"{len(claimed)} finding(s) came from extensions that stream it")
            return _extension_only_report(path, issues[0].message, loaded,
                                          ext_findings), issues, context
        return None, issues, context
    if not rows:
        return None, [Issue(loc=str(path), check="data",
                            message="dataset is empty; an empty dataset must never look green")], context
    context["n_rows"] = len(rows)

    mapping, notes, issues = infer_mapping(rows, field_overrides)
    context["mapping"], context["notes"] = mapping, notes
    if issues:
        # No question/answer columns. For an eval dataset that is a dead end and
        # refusing to guess is the whole point. For a table that was never an
        # eval -- a statistical release, a log export -- an extension may still
        # know exactly what it is looking at.
        if claimed:
            notes.append(f"no eval mapping in this file, so no core check ran; "
                         f"{len(claimed)} finding(s) came from extensions")
            return _extension_only_report(path, issues[0].message, loaded,
                                          ext_findings), issues, context
        return None, issues, context

    # Tabular audit: synthesize the question from the feature values so the
    # duplicate-row and id checks still have an "item" to read, while the raw
    # columns stay available for the leak scan. A duplicate synthesized question
    # is a duplicate feature row, which is exactly what S1 should catch here.
    if mapping.get("_tabular"):
        feats = [c for c in (rows[0] if rows else {}) if c != mapping["target"]]
        for r in rows:
            r["_features"] = " | ".join(f"{c}={r.get(c)}" for c in feats)
        mapping["input"] = "_features"

    sep = separator or sniff_separator(rows, mapping)
    if sep and not separator:
        notes.append(f"multi-value cells look {sep!r}-separated; pass --separator to override")
    items, build_notes = build_items(rows, mapping, sep)
    notes.extend(build_notes)
    if not items:
        return None, [Issue(loc=str(path), check="data",
                            message="every row was dropped for an empty question or answer; "
                                    "the field mapping is probably wrong")], context

    dupe_ids = len(items) - len({i["id"] for i in items})
    if dupe_ids:
        # Not a finding, a fact about the id column: S1 is about questions.
        notes.append(f"{dupe_ids} row(s) share an id, so ids were left as row numbers "
                     "for this audit")
        for n, item in enumerate(items):
            item["id"] = f"row-{n:06d}"

    rep = Reporter()
    _item_checks(rep, items, tabular=bool(mapping.get("_tabular")))
    _asset_checks(rep, items, path.parent)
    _overlap_check(rep, items, references or {})

    # S17: the trench-coat detector. A raw table can carry a column that all but
    # determines the target and would not be known at prediction time. This is
    # the one check more at home in a dataset audit than a pod.
    target_col = mapping.get("target")
    hidden = {mapping.get("input"), mapping.get("id"), "_features"}
    feature_cols = [c for c in (rows[0] if rows else {}) if c != target_col and c not in hidden]
    if not target_col or not target_is_classlike(rows, target_col):
        rep.not_applicable("S17", "the target is free-text or single-valued, not a class label, so "
                                  "single-column predictivity is not meaningful; this is the leak "
                                  "scan for a tabular classification table")
    elif not feature_cols:
        rep.not_applicable("S17", "no feature columns beyond the question and target to scan")
    else:
        cands = leak_candidates(rows, target_col, skip=hidden,
                                nmi_min=THRESHOLDS["target_leak_nmi"])
        rep.check("S17", not cands,
                  f"{len(cands)} of {len(feature_cols)} column(s) all but determine the target; if "
                  "any is not known at prediction time it is a label leak, which only you can decide",
                  n=len(feature_cols),
                  examples=[f"{c['column']}: normalized MI {c['nmi']} with the target "
                            f"({c['kind']} pattern, {c['cardinality']} distinct value(s))"
                            for c in cands],
                  evidence={"candidates": cands, "target": target_col})

    for reason, cids in DATASET_NA.items():
        for cid in cids:
            rep.not_applicable(cid, reason)
    # S8 is the one run-free check that asks about the FILE rather than the
    # items, and a dataset someone handed you is not expected to carry this
    # project's canary convention.
    rep.not_applicable("S8", "a contamination canary is a convention for data you author; "
                             "a dataset audit does not expect one")

    report = rep.report(path.name, inputs={"data_sha256": spec_sha256(path)}, scope="data")
    report["dataset"] = {"rows": len(rows), "items": len(items), "mapping": mapping,
                         "separator": sep}
    context["items"] = items
    return report, [], context


def _template_checks(rep: Reporter, probes: list[dict], real_runs: list[dict]) -> None:
    """P11 and P12: what the instruction phrasing is worth.

    Every eval fixes one way of saying "answer this" and reports the number it
    gets. That phrasing is a free parameter nobody registered. P11 asks how far
    each model moves when it changes; P12 asks whether the fleet ORDER moves,
    which is the part a leaderboard turns into a decision.

    Both are PAIRED: the same items are asked under every framing, so the band
    comes from the items that actually flipped (McNemar), not from treating two
    accuracies as independent samples.
    """
    runs = [e for e in probes if (e["manifest"] or {}).get("probe") == "template"]
    if not runs:
        for cid in ("P11", "P12"):
            if any(e["manifest"] and not e["manifest"].get("dry_run") for e in real_runs):
                rep.skip(cid, "no template probe on disk; run `dinostomp run <spec> "
                              "--probe template` to unlock")
            else:
                rep.not_applicable(cid, "instruction-framing probes need runs on disk")
        return

    # model -> framing -> {item_id: verdict}
    by_model: dict[str, dict[str, dict[str, str]]] = {}
    for e in runs:
        m = e["manifest"]
        model, framing = str(m.get("model")), str(m.get("framing"))
        for r in e["records"]:
            v = (r.get("score") or {}).get("verdict")
            if v in ("pass", "fail", "flag"):
                by_model.setdefault(model, {}).setdefault(framing, {})[str(r.get("item_id"))] = v

    judged = {m: fr for m, fr in by_model.items() if len(fr) >= 2}
    if not judged:
        for cid in ("P11", "P12"):
            rep.skip(cid, "fewer than 2 framings per model on disk; the probe needs at least two "
                          "phrasings to compare")
        return

    def acc(verdicts: dict[str, str], items: list[str]) -> float:
        return sum(1 for i in items if verdicts[i] == "pass") / len(items)

    # --- P11: per-model swing -------------------------------------------------
    swung, swings = [], {}
    for model, framings in sorted(judged.items()):
        common = sorted(set.intersection(*(set(v) for v in framings.values())))
        if len(common) < THRESHOLDS["min_checkable"]:
            continue
        accs = {f: acc(v, common) for f, v in framings.items()}
        lo_f, hi_f = min(accs, key=accs.get), max(accs, key=accs.get)
        spread = accs[hi_f] - accs[lo_f]
        broke = sum(1 for i in common
                    if framings[lo_f][i] != "pass" and framings[hi_f][i] == "pass")
        fixed = sum(1 for i in common
                    if framings[lo_f][i] == "pass" and framings[hi_f][i] != "pass")
        band = _paired_band(broke + fixed, len(common))
        swings[model] = {"spread": round(spread, 4), "noise_band": round(band, 4),
                         "worst": lo_f, "best": hi_f, "framings": len(framings)}
        if spread > band and spread > THRESHOLDS["template_swing_min"]:
            swung.append(f"{model}: {accs[lo_f]:.0%} framed {lo_f!r} vs {accs[hi_f]:.0%} framed "
                         f"{hi_f!r} (spread {spread:.0%} over {len(framings)} phrasings, "
                         f"vs {band:.0%} explainable by the {broke + fixed} item(s) that flipped)")
    if not swings:
        rep.skip("P11", f"no model has {THRESHOLDS['min_checkable']}+ items scored under every "
                        "framing")
    else:
        rep.check("P11", not swung,
                  f"{len(swung)} of {len(swings)} model(s) move more than the flipped items "
                  "explain when the instruction is re-phrased; that part of the score belongs to "
                  "the prompt, not the model",
                  n=len(swings), examples=swung, evidence={"template_swing": swings})

    # --- P12: does the ORDER move? -------------------------------------------
    #
    # The swing above is a number moving. This is a CONCLUSION moving, which is
    # what anyone reading a leaderboard actually consumes. A pair counts only
    # when both orderings clear their own noise band: two models tied inside
    # noise trading places is not a reversal, it is a coin.
    models = sorted(judged)
    if len(models) < 2:
        rep.not_applicable("P12", "one model cannot have an ordering; a ranking needs a fleet")
        return
    shared_framings = sorted(set.intersection(*(set(judged[m]) for m in models)))
    if len(shared_framings) < 2:
        rep.skip("P12", "no two framings cover the whole fleet; P12 compares rankings over the "
                        "same sample or it compares nothing")
        return

    reversals = []
    for a, b in combinations(models, 2):
        signs = {}
        for f in shared_framings:
            common = sorted(set(judged[a][f]) & set(judged[b][f]))
            if len(common) < THRESHOLDS["min_checkable"]:
                continue
            aw = sum(1 for i in common if judged[a][f][i] == "pass" and judged[b][f][i] != "pass")
            bw = sum(1 for i in common if judged[b][f][i] == "pass" and judged[a][f][i] != "pass")
            gap = (aw - bw) / len(common)
            if abs(gap) > _paired_band(aw + bw, len(common)):
                signs[f] = (1 if gap > 0 else -1, gap)
        directions = {s for s, _ in signs.values()}
        if len(directions) > 1:
            wins_a = [f for f, (s, _) in signs.items() if s > 0]
            wins_b = [f for f, (s, _) in signs.items() if s < 0]
            reversals.append(
                f"{a} beats {b} framed {', '.join(wins_a)}; {b} beats {a} framed "
                f"{', '.join(wins_b)}. Both separations clear sampling noise, so the ranking is "
                "a property of the prompt")
    rep.check("P12", not reversals,
              f"{len(reversals)} model pair(s) out of {len(list(combinations(models, 2)))} swap "
              f"places depending on how the instruction is phrased, across "
              f"{len(shared_framings)} framing(s)",
              n=len(models), examples=reversals,
              evidence={"framings": shared_framings, "reversals": len(reversals)})


def _overlap_check(rep: Reporter, items: list[dict], references: dict) -> None:
    """S11: are these items already in a dataset you were handed?

    n/a without a reference, because "no overlap found against nothing" is the
    kind of pass that teaches people a green line means safety. The finding
    text carries the limit too: overlap is evidence about the corpora compared,
    and silence here is not evidence about a training set.
    """
    if not references:
        rep.not_applicable("S11", "no reference dataset supplied; pass --against <file> to "
                                  "compare these items against a corpus you have. This never "
                                  "checks training data, and cannot.")
        return
    hits, stats = find_overlap(items, references)
    named = ", ".join(f"{k} ({v} items)" for k, v in stats["references"].items())
    rep.check("S11", not hits,
              f"{len(hits)} of {len(items)} item(s) already appear in {named}: "
              f"{stats['exact']} the same item, {stats['stem_only']} the same question with "
              f"different options, {stats['near']} near-verbatim. Overlap is evidence "
              "about THESE corpora only; finding none is not evidence about training data",
              n=len(items),
              examples=[f"{h['id']}: {h['kind']} match of {h['where']}"
                        + (f" (similarity {h['similarity']})" if h["kind"] == "near" else "")
                        for h in hits[:12]],
              evidence={"exact": stats["exact"], "same_question": stats["stem_only"],
                        "near": stats["near"], "references": stats["references"]})
