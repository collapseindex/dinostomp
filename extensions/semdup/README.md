# semdup — measured across three capability tiers

**Not recommended by default, and the reason is more interesting than a verdict:
capability buys PRECISION and costs RECALL, and no judge tested is both.**

## What it was for

Scoring the core's `dup-options` (S5) against MMLU-Redux's human annotation
([N-012](../../FINDINGS.md#n-012)) measured where a byte comparison runs out. Of
39 items humans labelled `multiple_correct_answers`, S5 reaches 2. The other 37
are semantic:

```
['steadily in one direction', 'in one direction', 'to and fro', 'All of these']
```

Recognising those needs a reader. So: ask a model, and measure what asking costs.

## What it scores

39 human-confirmed positives, 250 human-labelled `ok` items sampled at seed 7,
from MMLU-Redux 2.0. Identical prompt, cap and parser across all three.
Reproduce with `SEMDUP_JUDGE=<model> python extensions/semdup/validate.py`.

| judge | recall | precision | FPR on clean items | false flags per 3,000 | cost per 289 |
|---|---|---|---|---|---|
| llama-3.1-8b | **97%** | 13% | 80.8% | ~2,420 | $0.004 |
| qwen3-30b | 33% | 42% | 6.0% | ~180 | $0.010 |
| claude-opus-4.8 | 10% | **60%** | **0.8%** | **~24** | $1.42 |

The small model says yes to almost everything. The frontier model almost never
false-alarms and almost never fires. The failure mode is opposite at each end,
and neither is a dataset check you would want running unattended.

## Why it is still not recommended

The frontier row is genuinely usable as an *advisory*: 24 false flags per 3,000
items is a tolerable reading cost, and everything it flagged was worth a look.
Two things keep the default off:

- **It caught 3 of the 29 positives it managed to judge.** Nearly blind, and 3
  is a number with enormous error bars.
- **$1.42 per 289 items** is about $15 for a 3,000-item benchmark, to surface a
  handful of items the deterministic check missed.

One of its two "false alarms" is not one: `high_school_physics-02754` offers
`['0.16 N', '0.16 N', ...]`, which Redux labels `ok` and the core's own S5
flags. Scoring that against the judge is scoring it against an annotation error.

## What the first version of this file claimed, and why it was wrong

It reported precision of 14/18/18% and concluded the approach hit a *task* limit
that no prompt or model would move. **Retracted.** Precision moves 13% to 60%.

The flat curve was substantially an artifact of this harness: a 40-token cap
truncated every model that reasons before answering, and each truncation was
counted as "no opinion". That is [D-017](../../FINDINGS.md#d-017) reproduced by
its own author, and it is written up as [D-033](../../FINDINGS.md#d-033).

The structural story about distractors being *designed* to be confusable still
explains why the frontier judge lands at 60% rather than 95%. It no longer
explains a failure, because at the frontier it does not fail the way that
version claimed.

## If you want to build on it

Per-pod opt-in via `metadata.semdup`; verdicts cached by `(item, judge)` so
re-runs are free and offline; a spend cap priced from recorded usage; a skip
rather than a crash when there is no key; and every finding carries its own
measured false-positive rate so it cannot be quoted without one.

The open problem is **recall at usable precision**. If you get a judge above,
say, 50% recall while holding the false-positive rate near 1%, that is a real
result and this directory should be replaced with it.

## The rule it obeys regardless

Findings are `warn`, never gating. A model's opinion must not be able to turn
anybody's dataset `BROKEN`.
