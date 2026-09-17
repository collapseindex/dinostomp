# Jevlike on Wikispeedia: a one-pass scorer as a dinostomp examinee

    repo        https://github.com/vinnylarouge/jevlike @ 94f5fd1 (created 2026-09-16)
    data        Wikispeedia next-click JSONL, built by the repo's own script from the
                SNAP archives (West and Leskovec, WWW 2012); test split 4,373 rows
    checkpoint  wikispeedia.pt, trained here from scratch: tiny byte encoder, 3 epochs,
                CPU, seed 42, best validation NLL 3.150, about nine minutes
    run         2026-09-17, 0 API calls, $0.00

Ledger entries [F-051](../../FINDINGS.md#f-051) and [N-034](../../FINDINGS.md#n-034).

A Jev-like model takes a context and a list of options and returns one
probability per option in a single pass. Its whole job is to extract signal
from the menu, which is exactly the thing an eval can reward by accident. So
the model is mounted as a `python` examinee and the same battery that audits
an LLM eval audits this one: the dataset at rest, the run, and the gap between
the model's informed run and its own blind run.

## What the battery says

```
DATA (4,373 items)
  [FAIL] dup-questions       305 duplicated question(s) among 4373
  [FAIL] conflicting-keys    131 question(s) appear with conflicting targets
  [FAIL] answer-leak         17 of 4373 item(s) leak their answer into the question
  [ok]   position-bias, length-bias, surface-shortcut, key-skew

RUN (1,000 items, seed 42)
  jevlike-scratch-3ep   informed 29.8%  [0.270, 0.327]
                        blind     5.0%  [0.04, 0.07]     uniform floor 3.6%
  [ok]   above-guessing, blind-solvable, input-blind (lift +24.8 points)
  [ok]   verdict-rederive, summary-rederive, truncation-credit
BROKEN: 3 gated finding(s) at data scope
```

**The model beats its own blind run by 25 points.** With the page withheld
and only the menu shown, the same checkpoint scores 5.0% against a 3.6%
uniform floor; the menu alone is worth a point or two, the page is worth the
rest. Jevlike's README reports about 29% for a from-scratch model; this
checkpoint reproduces that (29.8% on the sample, 27.0% top-1 on the full
split under Jevlike's own evaluator).

**The three data gates are real and small.** Wikispeedia rows are one step
of one human path; two people who reached the same page with the same menu
and clicked differently produce two rows with the same question and different
keys. 131 states conflict, covering 356 items (8.1%). The majority-vote
ceiling that implies is 96.2% (96.5% on the sampled 1,000), so the gates do
not explain a 30% score. The 17 leaks are whole-word matches of the clicked
link's title inside the 2 KB article excerpt where no other link's title
appears ("wrist watch", "watch battery" for the link *Watch*); weak by
construction, reported at its size. Position and length bias do not fire: the
builder's seeded menu shuffle does its job.

## The control is the finding

Jevlike's evaluator prints a shuffled-context control: each menu scored
against a *wrong* page, on the reasoning that a useful model should beat it.
On this checkpoint the control reads **14.9%** top-1. The blind run above,
with **no** page, reads **5.0%**. Those should be close, and they are not,
and the reason is mechanical:

- The control is `context.roll(1, dims=0)` inside each batch of 64: every
  menu is paired with the page of the row before it.
- The test split is bucketed by target article (all rows for one target land
  in one split) and written in path order. 314 targets cover 4,373 rows; the
  largest target has 149 rows.
- So the "wrong" page is the page of a neighbour, and neighbours share
  targets: **39.4% of shuffled partners carry the same `Target article:`
  line**, which is the most informative line in the context. Same current
  page, 5.8%. A random permutation within the batch would leak 7.2%; a
  permutation across the split, or a blanked context, would not leak at all.

On the same 1,000 sampled items, in their original order, Jevlike's evaluator
reads informed 29.8% (identical to the dinostomp run) and shuffled-context
11.7%; the leak on that subset is 17.9%, lower than the full split's 39.4%
because sampling one row in four breaks the runs of same-target neighbours.
The blank-page run is 5.0% either way. So the four numbers that belong on one
picture, all on identical items: uniform 3.6%, no page 5.0%, their control
11.7%, informed 29.8%.

The control therefore measures "the model given the right target and a wrong
page" for two rows in five, and the number it prints is the model's real
lift understated: 27.0 against 14.9 reads as twelve points of signal, when
27.0 against 5.0 is twenty-two. The README's "about 8% for shuffled and
random-encoder controls" was measured on a different checkpoint and is not
re-derived here; the mechanism is the same evaluator and the same split, so
the direction of the bias is.

Direction: **against the model, in the control's favour.** A control that
leaks the answer's most useful feature is not a stricter test; it is a
different test with a flattering name.

## Honest scoping

- One checkpoint, trained here, three epochs. Nothing is claimed about
  Jevlike's quality as a model, and the report says `NOT ESTABLISHED BY
  DINOSTOMP` where it always does. What is claimed is about the eval and the
  control, and both re-derive from the files.
- The blind and informed runs are unpaired (separate runs on the same 1,000
  items); at n=1,000 an unpaired comparison resolves gaps of about 6 points,
  and this one is 25.
- The whole probability vector, option by option, is recorded in every
  trajectory (`data/runs/*.jsonl`; each step's `result` is a JSON string with
  `top`, `p_top`, `p_target` and a `distribution` map, under the target rail's
  4,000-character cap on every record) as evidence and asserted on by nothing. It was captured before any check that reads it was
  designed, and the records are committed and hashed here for that reason: a
  check family built later (calibration, mass split across S18-equivalent
  options, divergence between the informed and blind distributions) can be
  tested against numbers it could not have shaped.
- `items.jsonl` (4,374 lines with the canary, built one to one from Jevlike's
  test split) is not committed for size; its SHA-256 is in every run
  manifest as `data_sha256`, and `build_pod.py` regenerates it byte for byte.

## Reproduce

```bash
git clone https://github.com/vinnylarouge/jevlike && cd jevlike && git checkout 94f5fd1
pip install -e .                                   # numpy, torch
scripts/get_wikispeedia.sh                         # SNAP download + JSONL build
python <dinostomp>/audits/jevlike/build_pod.py data/wikispeedia/jsonl/test.jsonl <pod>
cp <dinostomp>/audits/jevlike/{examinee.py,eval.yaml,wikispeedia.pt} <pod>/
cd <pod> && dinostomp run eval.yaml && dinostomp run eval.yaml --probe blind
dinostomp report eval.yaml --trust-code
python <dinostomp>/audits/jevlike/control_leak.py <jevlike>/data/wikispeedia/jsonl/test.jsonl
```

`wikispeedia.pt` is the checkpoint used here (168 KB), so the run re-derives
without retraining; retraining with the flags above gives a checkpoint of the
same shape and a number inside the interval, not the same bytes.
