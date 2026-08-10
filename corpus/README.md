# dinocorpus

**A benchmark for detectors of broken evals, built so its author's tool cannot win it.**

```bash
python corpus/generate.py          # rebuild the dev split, deterministically
python corpus/score.py             # score dinostomp on it
python corpus/score.py --submission yourtool.json
```

Every instance is a small dataset with **exactly one planted defect**, labelled
with what was planted and where. The ground truth is a fact about how the file
was written, not a judgement about it, so this scales without annotators and
without a judge.

## The number that matters

```
DINOCORPUS dev: dinostomp 0.57.1

  recall, classes it has a check for   100.0% of 72
  recall, classes it does NOT            4.9% of 81
    of which name the planted item       0.0%
  false alarms on clean instances       15.7% of 51
```

**Nine of the twenty-one defect classes have no corresponding check**, planted on
purpose, and dinostomp finds none of them. That is the point. A benchmark whose
author scores 100% measures the author, and the blind-spot arm is what stops
this being a marketing asset.

The blind-spot classes are not exotic. Two of them, *the keyed answer is simply
wrong* and *two options are both correct*, are the most common defects in the
benchmark-error literature, and neither leaves a structural trace that any
single-file linter can see. Finding them needs a fleet of solvers, or a human.

Scored on the withheld split (`heldout-2026-08`, 400 instances) the shape holds:
100.0% covered, 0.0% blind under strict scoring, 5.0% false alarms. Current
numbers for every detector: **[LEADERBOARD.md](LEADERBOARD.md)**.

## Why the taxonomy is not the check registry

Each class declares where it came from:

| source | classes | meaning |
|---|---:|---|
| `literature` | 14 | a defect class described in published work on benchmark errors |
| `wild` | 5 | found by auditing a real benchmark; carries the F-number that established it |
| `own-checks` | 2 | exists because a dinostomp check exists |

Two of twenty-one from the check registry. If that ratio ever inverts, this
corpus has stopped measuring anything.

## Reading the score honestly

**Recall here is an UPPER BOUND.** The items are synthetic (see `basepool.py`)
and cleaner, shorter and more regular than real benchmark items. A detector is
being given an easier problem than a real dataset poses.

**Recall alone is half a number.** A detector that flags everything scores 100%
recall; the clean arm is what says so. One instance in four has nothing wrong
with it and both figures are always printed together.

**Generous and strict scoring differ, and strict is the honest one.** On a
blind-spot instance there is no expected check, so "any finding" counts as a
catch. The first scored run credited dinostomp with four blind-spot catches
that were all the same unrelated position-bias warning firing by chance. Strict
scoring requires the finding to name an item the defect was actually planted in.
Under it, the blind-spot recall is 0.0%.

## What the first scored run found

It found three defects in **the corpus**, and one in **the battery**.

The corpus's clean pool was not clean: arithmetic options were sorted
numerically, so with distractors straddling the answer the gold landed in a
middle slot far more often than chance, and S3 flagged 20 of 51 supposedly
clean instances. It was right every time. The answer-leak planter put its defect
in a multiple-choice item, where S2 is `n/a` by design, and then labelled S2 as
the check that should catch it. The surface-shortcut planter wrote `[orrin]`
into the stem and `orrin` into the option, and S9 tokenises without stripping
punctuation, so the planted shortcut was not one.

All three are in [FINDINGS.md](../FINDINGS.md) as D-045. The lesson is the
ordinary one: **the first run of a new instrument measures the instrument.**

The finding against the battery is D-046. S3's false-alarm rate on clean
four-option data is a function of item count, and its own applicability floor
admits the noisiest range:

```
  n items   threshold   P(a clean dataset trips S3)
       20           9                        16.3%
       24          11                         8.7%
       30          14                         3.3%
       50          23                         0.4%
      100          45                         0.0%
```

`min_choice_items = 20` is where S3 starts running, and it is where one clean
dataset in six warns. The margin is absolute (+20% of n) and applied to each of
four positions with no multiplicity correction, so at small n it is roughly two
standard deviations from the mean and four chances to cross it.

## Withheld splits, rotation, and held-back classes

**Rotation is nearly free here and impossible for hand-annotated benchmarks.**
Refreshing MMLU-Redux or ciFAIR costs an annotation budget every time, which is
why they do not. A new split here is one command. But rotation defends against
exactly one thing, and it is not the main threat:

- **Instance memorisation** matters for the MODEL task, where a solver can
  memorise what it has seen. Rotation is the right answer.
- **Taxonomy overfitting** is the threat to the TOOL task, and rotation does
  nothing about it. A rule-based detector cannot memorise an instance; it is
  written against the class. Someone who reads `taxonomy.py` and writes
  twenty-one checkers scores well on every rotation forever.

**Held-back classes** are the defence against the second. `corpus/holdback.py`
is gitignored and absent from this repository; when present, its classes are
planted into splits and never appear in the published taxonomy. What is
published either way is the COUNT
(`n_held_back_classes_present` in each manifest), so a submitter knows they
exist and how many, and only ever that.

**A withheld split needs a nonce**, or it is not withheld:

```bash
export DINOCORPUS_NONCE="$(python -c 'import secrets;print(secrets.token_hex(32))')"
python corpus/generate.py --split heldout-2026-09 -n 400
```

The nonce is mixed into every instance seed AND into the class schedule, and
generating a non-public split without one is refused. It has to be: the first
version derived seeds from public arithmetic, so `--split test` printed the
labels of the split whose labels were supposed to be withheld (D-047).

**The commitment is what makes the scorekeeper auditable.** A withheld split
publishes its instances and a SHA-256 of its labels, before any submission is
scored. When the split is revealed anyone can hash the labels and check they are
the ones committed to, and `score.py` refuses to score labels that do not match.
A benchmark whose author can edit the answer key after seeing the answers is not
a benchmark, and that includes this one.

Every split ever released, with its commitment: **[SPLITS.md](SPLITS.md)**.
Scores are only meaningful with a split id attached.

## Layout

```
corpus/
  taxonomy.py     21 defect classes, each with its source and its check-or-None
  basepool.py     clean items to plant into, and why they are synthetic
  generate.py     one pod per instance, one defect, deterministic from a seed
  score.py        recall, blind-spot recall, false alarms; scores any tool
  instances/dev/  the public split: pods, labels.jsonl, MANIFEST.json
  SPLITS.md       every split ever released, and its label commitment
  holdback.py     gitignored; defect classes that are never published
```

## Scope, stated

This split is **data-scope only**: defects visible in items at rest. Run-scope,
scorer-scope and judge-scope defects (truncation credited, a scorer that grades
format, a judge that flips on authority) are not here yet, and they are the part
of dinostomp with the least prior art, so their absence understates the space.

Four declared classes have no planter yet and are named in `MANIFEST.json`
rather than quietly omitted: `train-test-overlap`, `near-duplicate-asset`,
`label-in-path`, `asset-drift`. All four need assets on disk.

## Submitting a detector

```json
{"dev-00008": {"detected": true, "checks": ["my-key-checker"], "located": ["ke-0005"]},
 "dev-00009": {"detected": false}}
```

- `detected` is required and must be a boolean. Absent is indistinguishable from
  false, so it has to be explicit.
- `checks` names whatever your tool calls the rule that fired. For a class with
  an expected check, that check must be the one named.
- `located` names the ITEM ids you flagged. It is what strict scoring reads: a
  finding that names a different item has not found the planted defect.
- Instances you omit count as not detected, so a partial submission is scored on
  the whole corpus rather than on the part you chose to answer. The row says how
  many you answered.

`score.py` **refuses** a malformed submission rather than scoring it. An unknown
instance id and a missing `detected` look exactly like "found nothing", and
publishing a 0% about somebody's tool because of a typo is the worst thing this
corpus could do.

**Open an issue** with the [corpus submission
template](../.github/ISSUE_TEMPLATE/corpus-submission.md). Your number is
published as measured, and if the corpus turns out to be wrong it goes in
FINDINGS.md as a defect in the corpus. Three already are (D-045).
