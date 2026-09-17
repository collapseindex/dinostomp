# Jevlike on Wikispeedia: a one-pass scorer as a dinostomp examinee

    repo        https://github.com/vinnylarouge/jevlike @ 94f5fd1 (created 2026-09-16)
    data        Wikispeedia next-click JSONL, built by the repo's own script from the
                SNAP archives (West and Leskovec, WWW 2012); test split 4,373 rows
    checkpoint  wikispeedia.pt, trained here from scratch: tiny byte encoder, 3 epochs,
                CPU, seed 42, best validation NLL 3.150, about nine minutes
    runs        2026-09-17, four arms x (informed, blind), 6,000 hosted calls, $0.19

Ledger entries [N-034](../../FINDINGS.md#n-034) and
[N-035](../../FINDINGS.md#n-035), and two defects the hosted arms found in
dinostomp itself, [D-097](../../FINDINGS.md#d-097) and
[D-098](../../FINDINGS.md#d-098). The control-leak material that used to sit
here ([F-051](../../FINDINGS.md#f-051)) was removed; it is in the history at
`122b708`.

A Jev-like model takes a context and a list of options and returns one
probability per option in a single pass. Its whole job is to extract signal
from the menu, which is exactly the thing an eval can reward by accident. So
the model is mounted as a `python` examinee and the same battery that audits
an LLM eval audits this one: the dataset at rest, the run, and the gap between
the model's informed run and its own blind run. Three hosted LLMs then answer
the same 1,000 items through the same spec, so the one-pass model has a
comparison on identical items rather than a number in a README.

## What the battery says

```
DATA (4,373 items)
  [FAIL] dup-questions       305 duplicated question(s) among 4373
  [FAIL] conflicting-keys    131 question(s) appear with conflicting targets
  [FAIL] answer-leak         17 of 4373 item(s) leak their answer into the question
  [ok]   position-bias, length-bias, surface-shortcut, key-skew

RUN (1,000 items, seed 42; accuracy on checkable output)
  jevlike-scratch-3ep              informed 29.8%  [0.270, 0.327]   blind 5.0%
  qwen/qwen3-30b-a3b-instruct-2507 informed 29.8%  [0.269, 0.328]   blind 6.4%
  openai/gpt-5.6-luna              informed 22.8%  [0.203, 0.255]   blind 1.4%
  meta-llama/llama-3.1-8b-instruct informed 17.4%  [0.151, 0.200]   blind 3.4%
                                   uniform floor 3.6% (median 46 options)
  [ok]   above-guessing, blind-solvable, input-blind (every arm clears its own blind run)
  [ok]   uncheckable-rate, no model selectively escapes the scorer
  [ok]   verdict-rederive, summary-rederive, truncation-credit, same-engine
  [ok]   KR-20 0.96; 31 items every model passed, 436 every model failed
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

## Three hosted models on the same items

The question is not whether a from-scratch byte encoder is a good model. It is
whether "one pass, four seconds, no API" is buying its speed with reading, or
with the menu. The blind run answers that for the one-pass model. The hosted
arms put the same question to models that read the whole page, at temperature
0, through the same rendered prompt: the article excerpt, the menu labelled
A..Z, AA..BL, and "answer with exactly one of the options above, copied
verbatim".

| arm | with the page | menu only | checkable | wall | cost (informed + blind) |
|---|---:|---:|---:|---:|---:|
| Jev-like scorer, from scratch, one pass | **29.8%** [27.0, 32.7] | 5.0% | 1,000 | 4 s | $0.00 |
| Qwen3 30B-A3B instruct (2507) | **29.8%** [26.9, 32.8] | 6.4% | 913 | 22.5 min | $0.037 + $0.010 |
| GPT-5.6 Luna, `reasoning_effort: none` | **22.8%** [20.3, 25.5] | 1.4% | 994 | 17.9 min | $0.078 + $0.016 |
| Llama 3.1 8B instruct | **17.4%** [15.1, 20.0] | 3.4% | 921 | 11.7 min | $0.037 + $0.011 |

Wall time is first record to last record on one machine, sequential calls,
no concurrency; cost is summed from the records at OpenRouter's listed rates
that day. Uniform guessing is 3.6%.

**Reading the table honestly.**

- Every arm clears its own blind run, so no arm is scoring off the menu. The
  hosted models' blind numbers sit at or under the floor for a reason worth
  stating: Luna answered 659 of the 1,000 blind items with an empty string
  (scored as a fail), Llama picked the first option 220 times, Qwen picked the
  last 108 times. A menu with no page is a prompt these models mostly decline
  or default on.
- At n=1,000 an **unpaired** comparison resolves gaps of about 6 points. The
  one-pass model and Qwen are indistinguishable; the one-pass model over Luna
  (7 points) is borderline; over Llama (12 points) is not in doubt. The task
  is to predict what a *human* clicked, which is not the same as picking the
  best link, and a model that reads better does not automatically match a
  person's next click.
- **Accuracy is on checkable output.** Llama returned a bare menu letter 79
  times and Qwen 87 times ("P" where the spec asked for the option text); the
  scorer never sees the menu, so it cannot map a letter to a text and reports
  those as uncheckable. Mapping them by hand through each item's own menu
  order (a sensitivity number, not the headline): Qwen's 87 letters were right
  44 times, which reads 31.6% on all 1,000; Llama's 79 were right 14 times,
  17.4% on all 1,000; Luna's 6 were all wrong. The ordering does not move.
- Most hosted answers copied the label as well as the text ("E. Japan"): 875
  of Llama's, 884 of Qwen's, 504 of Luna's. `score.py` strips one leading
  label and stays strict on everything else (case, spacing, wrappers,
  negation, each pinned by a witness). Under the plain exact scorer the first
  132 Llama answers had scored 1 of 132: a format result, not a reading
  result, and the reason this pod is at v0.3.0.
- Overlap: 31 items every arm got, 436 no arm got. The one-pass model and
  Qwen agree on 171 of their roughly 300 correct items each; the one-pass
  model and Luna on 123.
- Single sample per item, temperature 0, dinostomp's rendering and nothing
  tuned. A better prompt would move the hosted numbers; it would not make the
  one-pass model slower or dearer.

**What the hosted arms found in the tool.** Menus here run to 64 options,
and dinostomp's option labels ran out of letters at 27 and out of printable
characters at 59 ([D-097](../../FINDINGS.md#d-097)); the hosted arms had
been reading a block whose tail no model could label. And with `max_tokens:
256` Luna spent every output token on hidden reasoning and returned nothing,
billed in full ([D-098](../../FINDINGS.md#d-098)); the spec gained
`params.reasoning_effort`. Both fixed before the paid run, both in the
engine's own ledger.

## Honest scoping

- One checkpoint, trained here, three epochs. Nothing is claimed about
  Jevlike's quality as a model, or about the three hosted models' quality in
  general, and the report says `NOT ESTABLISHED BY DINOSTOMP` where it always
  does. What is claimed is about the eval, the control, and four numbers on
  identical items, and all of it re-derives from the files.
- The blind and informed runs are unpaired (separate runs on the same 1,000
  items); at n=1,000 an unpaired comparison resolves gaps of about 6 points.
- The whole probability vector, option by option, is recorded in every
  one-pass trajectory (`data/runs/*jevlike-scratch-3ep*.jsonl`; each step's
  `result` is a JSON string with `top`, `p_top`, `p_target` and a
  `distribution` map, under the target rail's 4,000-character cap on every
  record) as evidence and asserted on by nothing. It was captured before any
  check that reads it was designed, and the records are committed and hashed
  here for that reason: a check family built later (calibration, mass split
  across S18-equivalent options, divergence between the informed and blind
  distributions) can be tested against numbers it could not have shaped.
- `data/runs/` holds the eight v0.3.0 runs the table reads. The two v0.1.0
  runs (the one-pass model alone, plain exact scorer, no rendered menu) are in
  `data/runs-v0.1.0/`; their numbers, 29.8% and 5.0%, are the ones the v0.3.0
  one-pass arm reproduces, because the rendered option block never reaches
  the examinee (it reads `choices` directly and its encoder sees the first
  192 bytes of the context).
- `items.jsonl` (4,374 lines with the canary, built one to one from Jevlike's
  test split) is not committed for size; its SHA-256 is in every run
  manifest as `data_sha256`, and `build_pod.py` regenerates it byte for byte.

## Picture

`four_models.png` (from `models_chart.py`): the four arms with and without
the page. The script carries its numbers typed from this file, so the picture
cannot drift from the text without somebody noticing.

## Reproduce

```bash
git clone https://github.com/vinnylarouge/jevlike && cd jevlike && git checkout 94f5fd1
pip install -e .                                   # numpy, torch
scripts/get_wikispeedia.sh                         # SNAP download + JSONL build
python <dinostomp>/audits/jevlike/build_pod.py data/wikispeedia/jsonl/test.jsonl <pod>
cp <dinostomp>/audits/jevlike/{examinee.py,eval.yaml,score.py,wikispeedia.pt} <pod>/
export OPENROUTER_API_KEY=...                      # three hosted arms; about $0.20 for both sweeps
cd <pod> && dinostomp run eval.yaml && dinostomp run eval.yaml --probe blind
dinostomp report eval.yaml --trust-code
```

`wikispeedia.pt` is the checkpoint used here (168 KB), so the one-pass arm
re-derives without retraining; retraining with the flags above gives a
checkpoint of the same shape and a number inside the interval, not the same
bytes. The hosted arms re-derive to within sampling noise at temperature 0
and to the cent at the listed rates, for as long as OpenRouter serves those
three model identifiers; once `build_pod.py` has rebuilt `items.jsonl`,
`dinostomp verify` re-scores every committed record offline without any of
them.
