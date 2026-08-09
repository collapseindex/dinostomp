# semdup — measured, and NOT recommended

**This extension does not work well enough to use. That is the finding.**

It is kept here because the apparatus is reusable and the negative result is
worth more than another untested plugin: "use an LLM to find semantically
duplicate options" is an obvious idea, and this is what it costs when somebody
measures it instead of shipping it.

## What it was for

Scoring the core's `dup-options` (S5) against MMLU-Redux's human annotation
([N-012](../../FINDINGS.md#n-012)) showed exactly where a byte comparison runs
out. Of 39 items humans labelled `multiple_correct_answers`, S5 reaches 2. The
other 37 are semantic:

```
['steadily in one direction', 'in one direction', 'to and fro', 'All of these']
```

Recognising those needs a reader. So: ask a model.

## What it scores

39 human-confirmed positives, 250 human-labelled `ok` items sampled at seed 7,
from MMLU-Redux 2.0. Reproduce with `python extensions/semdup/validate.py`.

| framing | judge | recall | precision | FPR on clean items |
|---|---|---|---|---|
| "do any two mean the same?" | llama-3.1-8b | 100% | 14% | **98.4%** |
| "do any two mean the same?" | qwen3-30b | 38% | 18% | **27.6%** |
| "is any OTHER option also correct?" | qwen3-30b | 95% | 18% | **69.2%** |

On a 3,000-item benchmark those false-positive rates are roughly **2,950, 830
and 2,080 false flags**. To find ~37 real ones.

## Why it fails, which is the interesting part

**Precision sits at 14–18% across three framings and two model tiers.** Changing
the prompt slides recall and the false-positive rate along one curve without
improving the discrimination. That is the signature of a task limit rather than
a prompt limit.

The reason is structural, and visible in what it flags:

```
econometrics: ['Unbiased and consistent', 'Biased but consistent',
               'Biased and inconsistent', ...]
```

Those options are *designed* to be confusable. A well-written multiple-choice
question has distractors that are near-misses, so "could a second option be
defended as correct?" is close to the question the item exists to ask. A judge
answering it well would be answering the exam.

## If you want to build on it

The pieces are honest and reusable: per-pod opt-in via `metadata.semdup`,
verdicts cached by `(item, judge)` so a re-run is free and offline, a spend cap
priced from recorded usage, and a skip rather than a crash when there is no key.
`validate.py` is the harness; point it at a different judge with
`SEMDUP_JUDGE=<model>`.

If you get precision above ~80% on this set, that is a real result and this
directory should be replaced with it.

## The rule it obeys anyway

Findings are `warn`, never gating, and every finding carries the measured
false-positive rate in its own text. A check that spends money, and is wrong
four times in five, must not be able to make anybody's dataset `BROKEN`, and
must not be quotable without its error rate attached.
