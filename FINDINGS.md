# Findings

A ledger, not an essay. Every entry has an id, a subject, a check that produced
it, and a receipt you can re-derive.

Three series, because they are different kinds of claim and averaging them would
be the first dishonest thing in this file:

| series | what it records |
|---|---|
| **F** | a defect found in someone else's eval, dataset, or scoring |
| **D** | a defect found in dinostomp itself |
| **N** | a negative result: a check that found nothing, recorded anyway |

Ids are permanent. A withdrawn entry keeps its id and gains a `WITHDRAWN` status
with the evidence that killed it, because deleting a claim you have already made
is how a findings page becomes a marketing page.

**Reproducing anything here** needs no API key and no spend unless the entry says
otherwise:

```bash
python benchmarks/fetch.py                    # downloads the datasets, prints their SHA-256
dinostomp stomp benchmarks/<name>/eval.yaml   # re-derives the finding
```

## Index

| id | subject | finding | status |
|---|---|---|---|
| [F-001](#f-001) | iris | two byte-identical measurement vectors | confirmed |
| [F-002](#f-002) | MMLU | a subtraction item keyed to two correct options | confirmed |
| [F-003](#f-003) | MMLU | 90 duplicate rows in the first 3000 | confirmed |
| [F-004](#f-004) | TruthfulQA | an item passable by restating the question | confirmed, scoped |
| [F-005](#f-005) | GSM8K | two of four models move beyond sampling noise on seed alone | confirmed |
| [F-006](#f-006) | GSM8K | unfinished responses credited as correct | confirmed |
| [F-007](#f-007) | GSM8K | a formatting gap that reads as a capability gap | confirmed |
| [F-008](#f-008) | CommonsenseQA | 24 items with a repeated option; 6 repeat the keyed answer | confirmed |
| [F-009](#f-009) | MedMCQA | 16 items with a repeated option, 4 of them the answer | confirmed |
| [F-010](#f-010) | SciQ | 9 items with a repeated option | confirmed |
| [F-011](#f-011) | MMLU-Pro | 64 duplicate rows in the first 3000 | confirmed |
| [F-012](#f-012) | MMLU-Pro vs MMLU | 158 of 3000 items reuse an MMLU question; 22 are unchanged | confirmed, expected |
| [F-013](#f-013) | SciQ | the gold option reuses a question word no distractor does | confirmed, narrow |
| [F-014](#f-014) | a judge (qwen3-30b) | stated confidence and authority flip its verdicts, always toward FAIL | confirmed |
| [F-015](#f-015) | four small models | 87% to 97% preserve a source's hedge; the eval cannot separate them | confirmed, underpowered |
| [F-016](#f-016) | llama-3.2-3b | "You are an expert." is worth 10 points, marginally | confirmed, marginal |
| [F-017](#f-017) | a RAG agent | grounding it in its own retrieval made it 25 points WORSE | confirmed |
| [F-018](#f-018) | MMLU-Redux 2.0 | two verbatim double-keyed items the human annotators marked `ok` | confirmed |
| [N-001](#n-001) | HellaSwag, ARC, MMLU | no position, length, or shortcut bias found | negative |
| [N-002](#n-002) | dinostomp | the uncheckable path was untested, and said so | negative, later closed |
| [N-003](#n-003) | ARC, OpenBookQA, HellaSwag, WinoGrande | no repeated options in four datasets | negative |
| [N-004](#n-004) | six dataset pairs | no cross-benchmark reuse found | negative |
| [N-005](#n-005) | four models | re-ordering the options moved nobody beyond noise | negative, underpowered |
| [N-006](#n-006) | four models | probe demonstrably sensitive, and no canary reproduced | negative |
| [N-007](#n-007) | lm-eval-harness log | both reported metrics re-derive from the raw log-probs | negative |
| [N-008](#n-008) | dinostomp | an even `run.repeats` reported p-squared, not p | measured, fixed |
| [N-009](#n-009) | dinostomp | T4 sees 0%, T7 sees 100%, on the same agent | measured |
| [N-010](#n-010) | dinostomp | what a process boundary buys, one claim at a time | measured |
| [N-011](#n-011) | Inspect AI | the second foreign format cost one defect, not five | measured |
| [N-012](#n-012) | dinostomp | scored against humans: 5% recall, and 2 items they missed | measured, acted on |
| [N-013](#n-013) | LLM-as-judge | the obvious AI fix for N-012 does not work, across 3 framings | measured, not shipped |
| [D-001](#d-001) | dinostomp | the money invariant had only ever run at zero | fixed |
| [D-002](#d-002) | dinostomp | pooling hid a model that never read the question | fixed |
| [D-003](#d-003) | dinostomp | a collapsed model manufactured 8 phantom key errors | fixed |
| [D-004](#d-004) | dinostomp | a gating check returned BROKEN on all of GSM8K | fixed |
| [D-005](#d-005) | dinostomp | a choice item was keyed on its question alone | fixed |
| [D-006](#d-006) | dinostomp | any probe was read as the blind probe | fixed |
| [D-007](#d-007) | dinostomp | moves were compared to a flat percentage, not to noise | fixed |
| [D-008](#d-008) | dinostomp | 31 manufactured key errors, and a flattering first fix | fixed, scoped |
| [D-009](#d-009) | dinostomp | `plan` understated a bill by 3x | fixed |
| [D-010](#d-010) | dinostomp | the engine hashed itself and nothing read it | fixed |
| [D-011](#d-011) | dinostomp | published reports only verified on the author's machine | fixed |
| [D-012](#d-012) | dinostomp | line-ending translation is drift | fixed |
| [D-013](#d-013) | dinostomp | smaller ones: a wrong hint, two wrong witnesses, a near-miss | fixed |
| [D-014](#d-014) | dinostomp | the overlap check compared questions and ignored options | fixed |
| [D-015](#d-015) | dinostomp | position and length bias reported class balance on a fixed label set | fixed |
| [D-016](#d-016) | dinostomp | the SciQ fetcher put the answer at index 0 on every item | fixed |
| [D-017](#d-017) | dinostomp | a truncated judge was diagnosed as a judge with no opinion | fixed |
| [D-018](#d-018) | dinostomp | EVERY non-judge probe crashed the CLI, not just cross-judge | fixed |
| [D-019](#d-019) | dinostomp | the docs claimed a 28-point swing with no run behind it | WITHDRAWN |
| [D-020](#d-020) | dinostomp | the grounding check undercounts by 6x, by construction | superseded by T7 |
| [D-021](#d-021) | dinostomp | the most common eval-log shape in the field was unimportable | fixed |
| [D-022](#d-022) | dinostomp | a check overwrote the contract's skip reason with a false one | fixed |
| [D-023](#d-023) | dinostomp | a rival score column was chosen silently, and it was the wrong one | fixed |
| [D-024](#d-024) | dinostomp | `run --dry` would fabricate records for a model it cannot call | fixed |
| [D-025](#d-025) | dinostomp | an error message named a flag nobody can type | fixed |
| [D-026](#d-026) | dinostomp | the item-majority estimator was never run live until now | fixed |
| [D-027](#d-027) | dinostomp | two defects in the pod written to demonstrate the new rail | fixed |
| [D-028](#d-028) | dinostomp | the line-ending guard could not see a file until after it shipped | fixed |
| [D-029](#d-029) | dinostomp | "policy is enforced at call time" held only for agents that asked | corrected |
| [D-030](#d-030) | dinostomp | `inspect` called a pod codeless while it shipped an agent and tools | fixed |
| [D-031](#d-031) | dinostomp | an imported trajectory could never reach the checks that read one | fixed |
| [D-032](#d-032) | dinostomp | a valid JSONL file it refused to read, blaming the data | fixed |

---

## Findings in other people's evals

### F-001
**iris · two byte-identical measurement vectors**
`dup-questions` (S1) · 2026-07 · confirmed

The battery's first contact with real data was the most famous dataset in
statistics. Transcript re-run under the current 57-check battery; the original
catch happened at 23 checks.

```
  [FAIL] dup-questions   questions are unique    1 duplicated question(s) among 150
           - sepal length 5.8 cm, sepal width 2.7 cm, petal length 5.1 cm, petal width 1.9 cm
```

The commonly distributed iris (the UCI/scikit-learn lineage, which is what the
pod's `data_sha256` pins; it differs from Fisher's 1936 table in two rows, see
Bezdek et al. 1999, *Will the real iris data please stand up?*) contains two
identical vectors: rows 101 and 142, 0-indexed, known to R users as 102/143.
Whether that was one virginica measured twice or two flowers landing on the same
millimetre grid is unknowable from the data. Either way it is one item carrying
double weight.

**Scope it honestly.** This is a known curiosity; one line of R finds it, and
deduplication tutorials use it. That is the point. Nobody runs `duplicated()` on
their eval data unless they remember to.

The bundled [iris pod](examples/iris/) ships the deduplicated 149 and its
published report, which is what the fix looks like from the other side:

```
  [ok]   dup-questions   questions are unique   0 duplicated question(s) among 149
MECHANICALLY SOUND: no integrity findings, full coverage (29 of 29 ran; 28 n/a of 57 declared)
```

### F-002
**MMLU · a subtraction item keyed to two correct options**
`dup-options` (S5) · 2026-08-09 · confirmed

```
Q: Subtract. 2,396 - 1,709
choices: ['687', '687', '1,493', '1,695']
keyed:   '687'
```

2396 minus 1709 is 687, and 687 is on the list twice. Under the letter-keyed
protocol everyone uses, a model that computes the right answer picks the wrong
letter half the time. Two more of the same shape: `mmlu-01941` offers
`0.015 joule.` twice, `mmlu-00389` offers `Employee rights` twice.

Reproduce: `dinostomp stomp benchmarks/mmlu/eval.yaml`, item `mmlu-02178`.

### F-003
**MMLU · 90 duplicate rows in the first 3000**
`dup-questions` (S1) · 2026-08-09 · confirmed

Ninety items appear twice with identical question, identical options and
identical key. Three percent of that slice carries double weight. Example:
`mmlu-00488` and `mmlu-01258` both ask *"The key attribute in successful
marathon running is:"* over `['strength.', 'power.', 'stride length.',
'stamina.']`.

This is what survived [D-005](#d-005). Before that fix the count was inflated by
22 items that shared a stem but had different options, which are not duplicates
at all.

### F-004
**TruthfulQA · an item passable by restating the question**
`answer-leak` (S2) · 2026-08-09 · confirmed, scoped

```
  [FAIL] answer-leak   1 of 790 free-form item(s) leak their answer
           - tqa-0000: target 'you eat watermelon seeds' appears in its question
```

`tqa-0000` asks *"What happens to you if you eat watermelon seeds?"* and its
accepted-answer list includes *"You eat watermelon seeds"*.

**Scope it precisely.** TruthfulQA's own protocol uses a trained judge or the
multiple-choice split, not substring matching against `Correct Answers`. This is
a scoring choice interacting with the dataset. It is also the scoring choice a
quick harness makes.

### F-005
**GSM8K · two of four models move beyond sampling noise on seed alone**
`seed-stability` (P10) · 2026-08-09 · confirmed · costs $0.06 to reproduce

Four models, 120 problems, three seeds, 1440 calls.

```
llama-3.1-8b    78% at seed 11 vs 90% at seed 23   (12.5 points, band 9)
ministral-8b    81% at seed 11 vs 92% at seed 23   (10.8 points, band 9)
llama-3.2-3b    38.5% to 50.0%                     (11.5 points, band 13)  quiet
```

Nothing changed but which 120 problems were drawn. The third model has the
**largest raw spread** and is the one the check stays quiet about, because at its
accuracy and smaller checkable denominator the band is wider. A flat threshold
would have reported the noisiest-looking model and missed the two real ones: see
[D-007](#d-007).

### F-006
**GSM8K · unfinished responses credited as correct**
`truncation-credit` (R5) · 2026-08-09 · confirmed

Nine truncated responses scored as passes. Reading all nine: four had stated a
final answer and were cut off closing a LaTeX brace; **five were genuinely
unfinished**, still mid-reasoning, credited because `extract: last` found an
intermediate number that happened to equal the target. `gsm-0181` was on the
words *"The problem states that"* when it ran out of tokens, and scored a pass.

The check hands you the list rather than trying to tell the two apart:
distinguishing them needs a regex for "final answer" in whatever language the
model replied in, and a gating check does not get to depend on that.

### F-007
**GSM8K · a formatting gap that reads as a capability gap**
`uncheckable-rate` (R6) · 2026-08-09 · confirmed

The 3B model loses 8 to 16 items per run to unparseable output; the other three
lose none. Those leave the denominator instead of counting as wrong, which is
why it reads 0.455 and not 0.417. A harness that scored them wrong would report
part of a formatting gap as a capability gap.

### F-008
**CommonsenseQA · 24 items with a repeated option, 6 of them the keyed answer**
`dup-options` (S5) · 2026-08-09 · confirmed

```
cs-00022: Though the thin film seemed fragile, for it's intended purpose it was ...
  choices: ['indestructible', 'durable', 'undestroyable', 'indestructible', 'unbreakable']
  keyed:   'indestructible'
```

Five options, two of which are the same word, and that word is the answer. A
model that picks correctly has two letters to choose between and one of them is
scored wrong. Eighteen more items repeat a **distractor** rather than the
answer, which is milder: the item offers four distinct options while presenting
five.

### F-009
**MedMCQA · 16 items with a repeated option, 4 of them the answer**
`dup-options` (S5) · 2026-08-09 · confirmed

```
mm-00161: Tonsils developed from:
  choices: ['Ventral part of 3rd pouch.', 'Ventral part of 2nd pouch.',
            'Dorsal part of 2nd pouch.', 'Ventral part of 3rd pouch.']
  keyed:   'Ventral part of 2nd pouch.'
```

Also `mm-00044`, whose option list is `['Africas', 'Caucians', 'Not Recalled',
'Not Recalled']` — a repeated placeholder, and the keyed answer is `'Africas'`.

### F-010
**SciQ · 9 items with a repeated option**
`dup-options` (S5) · 2026-08-09 · confirmed

```
sq-00067: Solute potential is also called osmotic potential because ...
  choices: ['osmosis', 'permeability', 'electrolysis', 'electrolysis']
  keyed:   'osmosis'
```

Seven repeat a distractor; two repeat the answer.

**One thing this pod cannot tell you.** SciQ ships the correct answer and three
distractors as separate columns, so option ORDER is reconstructed here rather
than given. The pod's `position-bias` result is therefore about the
reconstruction and not about SciQ, and the spec says so in a comment. It is
excluded from the findings above for that reason.

### F-011
**MMLU-Pro · 64 duplicate rows in the first 3000**
`dup-questions` (S1) · 2026-08-09 · confirmed

Sixty-four items appear twice with identical question, identical options and
identical key: 2.1% of the slice carrying double weight. None of the pairs
disagree on the answer. First pair: `mp-00816` and `mp-00817`.

### F-012
**MMLU-Pro vs MMLU · 158 of 3000 items reuse an MMLU question**
`corpus-overlap` (S11) · 2026-08-09 · confirmed, expected

| | count |
|---|---|
| the same item (question **and** options identical) | 22 |
| the same question, options rewritten | 136 |
| near-verbatim | 0 |

**Expected, and the magnitude is still worth publishing.** MMLU-Pro is
documented as built from MMLU plus other sources, so this is a derivation and
not a defect. What it means for a reader is concrete: a model evaluated on both
is not being evaluated twice, and 5.3% of this slice is shared.

The 22 identical items are the more interesting number. MMLU-Pro's stated method
expands each question to ten options; these twenty-two carry MMLU's original
four, unchanged. Receipt:

```
mp-02693 == mmlu-02786   "Which of the following statements is NOT correct about apoptosis?"
   MMLU-Pro options (4) == MMLU options (4), same key
```

Reproduce with `dinostomp stomp benchmarks/mmlu-pro/eval.yaml --against
benchmarks/mmlu/items.jsonl`.

### F-013
**SciQ · the gold option reuses a question word that no distractor does**
`surface-shortcut` (S9) · 2026-08-09 · confirmed, narrow

```
Q: Which two major innovations allowed seed plants to reproduce without water?
   options: ['root and pollen', 'salt and pollen', 'bee and pollen', 'seed and pollen']
   gold:    'seed and pollen'   <- the only option containing "seed"
```

On the 64 items where one option clearly shares most words with the question,
that option is the gold answer **32 times against a chance expectation of 16**
(z = 4.6). A model that never reads past the overlap gets those right.

**Scope it narrowly.** Only 64 of 1000 items are decidable this way, so this is
not "SciQ is guessable"; it is a measurable lean on 6% of it. The check reports
the decidable subset rather than the whole set for exactly that reason.

This finding only became visible after [D-016](#d-016): while the fetcher put
the answer at index 0 on every item, position dominated and this was buried
under an artifact of my own making.

### F-014
**A judge (qwen3-30b) · stated confidence and appeals to authority flip its verdicts**
`judge-bias` (J2) · 2026-08-09 · confirmed · [examples/hedge](examples/hedge/)

Regrading 16 known cases under six perturbations that change no meaning, three
perturbations moved the judge:

```
confidence on settled-01: pass->fail      authority on settled-08: pass->fail
confidence on hedged-05:  pass->fail      verbosity  on settled-01: pass->fail
confidence on settled-09: pass->fail
confidence on hedged-15:  pass->fail
```

**Every flip is pass to fail.** That direction matters: this judge is not being
flattered into leniency, it is being made stricter by a response sounding more
confident. For an eval whose whole subject is epistemic stance, a judge that
punishes confident phrasing is measuring something adjacent to what it was asked
to measure.

The check reports the direction because a fail-to-pass flip is the one that
manufactures accuracy, and these are not that. It is still a bias.

### F-015
**Four small models · 87% to 97% preserve a source's hedge, and the eval cannot separate them**
`hedge-survival` · 2026-08-09 · confirmed, underpowered · costs $0.02 to reproduce

| model | preserved stance |
|---|---|
| qwen3-30b-a3b | 0.967 [0.83, 0.99] |
| ministral-8b | 0.933 [0.79, 0.98] |
| llama-3.1-8b | 0.867 [0.70, 0.95] |
| llama-3.2-3b | 0.867 [0.70, 0.95] |

**The honest reading is the interval, not the ordering.** At n=30 the minimum
detectable effect is about 36 points and the spread is 10, so this ranking is
not a result. What the numbers do support is narrow and still worth having: all
four models keep the source's stance most of the time, and none is near a floor
that would make the task look impossible.

`fleet-reliability` (KR-20 0.15) says the same thing from the other side: these
30 items do not reliably order these four models. That is a property of the item
set, and the fix is more items, not a stronger claim.

### F-016
**llama-3.2-3b · "You are an expert." is worth 10 points, marginally**
`prompt-stability` (P11) · 2026-08-09 · confirmed, marginal · [examples/presentation](examples/presentation/)

Same 40 items, same options, six instruction framings that change no meaning:

| model | worst framing | best framing | spread | noise band |
|---|---|---|---|---|
| llama-3.2-3b | `bare` 85% | `expert` 95% | **10.0** | 10.0 |
| llama-3.1-8b | `polite` | `instructed` | 5.0 | 6.9 |
| ministral-8b | — | — | 0.0 | — |
| qwen3-30b | — | — | 0.0 | — |

Prefixing *"You are an expert. Answer the following question."* moved the 3B
model from 85% to 95%. Ten points, from a sentence carrying no information about
any of the questions.

**Report it as marginal, because it is.** The spread is 10.0 and the band is
10.0: it clears by a hair, on four items that flipped. One more flip either way
and this is noise. What makes it worth an entry is not the significance, it is
that the *only* model it moved is the smallest, and it moved in the direction
that flatters the persona.

The other three models did not move at all, and no pair of models swapped places
under any framing ([ranking-stability](#n-005) reports 0 of 6 reversals). So on
this instrument the phrasing changes a score and does not change a conclusion.

### F-017
**A RAG agent · grounding it in its own retrieval made it 25 points worse**
`live-agent` · 2026-08-09 · confirmed · [examples/live-agent](examples/live-agent/) · costs $0.02

Three configurations of one agent, same corpus, same tool, same 24 questions,
same backend for two of the three:

| configuration | what it does | accuracy |
|---|---|---|
| `live-grounded` | retrieves, then answers **using only the snippet** | **0.542** [0.35, 0.72] |
| `live-oneshot` | answers from memory, then retrieves anyway | 0.792 [0.60, 0.91] |
| `live-greedy` | retrieves three topics, then answers from them | 0.833 [0.64, 0.93] |

The configuration that is forced to use its evidence is the **worst** one, by 25
points against the configuration that ignores it. The mechanism is visible in
the traces: when the model picks the wrong corpus topic, the grounded prompt
tells it to say the reference does not contain the answer, and it obediently
does, on questions it can answer from memory perfectly well.

**Do not read this as "RAG is bad".** It is one corpus, one tool, one retrieval
strategy, and 24 questions chosen to be answerable from that corpus. What it
does show is that "ground the model in retrieved evidence" is a change with a
cost, and an eval that only reports the grounded number would show the strategy
in its worst light without ever saying why.

---

## Negative results

### F-018
**MMLU-Redux 2.0 · two items whose keyed answer is offered twice, labelled `ok` by the annotators**
`dup-options` (S5) · 2026-08-09 · confirmed

MMLU-Redux is 5,700 MMLU items re-read and labelled by hand (Gema et al., 2024).
It is the ground truth this repository is scored against in
[N-012](#n-012), and running the battery over the same file turned up two items
it does not flag.

```
international_law-03425      human label: ok
  keyed answer: "All the members of the arbitral tribunal are appointed by the parties"
  that exact string is offered TWICE in the option list

sociology-05313              human label: ok
  keyed answer: "debt repayments with interest can be greater than the amount of money received"
  that exact string is offered TWICE in the option list
```

Both are `multiple_correct_answers` by construction: the answer key points at a
string that appears twice, so two options are correct and a model that picks the
right ANSWER can still be marked wrong for picking the wrong LETTER. No subject
knowledge is needed to see it and no judgement call is involved; it is a string
comparison.

Redux caught the third item of this shape (`high_school_macroeconomics-02425`)
and labelled it `multiple_correct_answers`, so the category was in use and these
two were missed rather than excluded by definition.

**Scope, and it matters.** This is a defect in an ANNOTATION, on two items out of
5,700, in a paper whose entire contribution is finding defects other people
missed. It is offered as a receipt that mechanical and human auditing catch
different things, which is also the finding in N-012 pointing the other way: the
same comparison shows the humans catching 38 items the battery cannot see.
Reproduce with `python benchmarks/mmlu-redux/compare.py`.

---

### N-001
**HellaSwag, ARC, MMLU · no position, length, or shortcut bias found**
`position-bias` (S3), `length-bias` (S4), `surface-shortcut` (S9) · 2026-08-09

All three checks came out clean on all three multiple-choice sets. HellaSwag's
correct ending is strictly longest **1% below** its per-item expectation, the
opposite of the folk claim that longer endings are the tell. ARC and MMLU sit
within 3 points of expectation on position and length.

Recorded because a validator that only publishes hits is telling you what it is
willing to look for. These datasets are well built on the axes measured here.

### N-002
**dinostomp · the uncheckable path was untested, and said so**
first live study · 2026-08 · later closed by [F-007](#f-007)

Judgeability was 1.000 for every model and not one of 720 responses was
unparseable, so the uncheckable branch had never run in anger. The study
recorded that as a failed prediction and named what would fix it: a free-form
task rather than smaller models. It was right; the GSM8K run exercised it.

### N-003
**ARC-Easy, ARC-Challenge, OpenBookQA, HellaSwag, WinoGrande · no repeated options**
`dup-options` (S5) · 2026-08-09

Zero items with a repeated option across 2376 + 1172 + 500 + 10042 + 1267 items.
Recorded because [F-008](#f-008) to [F-010](#f-010) make repeated options look
endemic and they are not: five of the nine choice datasets audited here are
clean on this axis.

### N-004
**Six dataset pairs · no cross-benchmark reuse found**
`corpus-overlap` (S11) · 2026-08-09

OpenBookQA against ARC-Easy and ARC-Challenge, SciQ against both, CommonsenseQA
against OpenBookQA, WinoGrande against HellaSwag, MedMCQA against MMLU: no
shared items and no shared questions. Only [F-012](#f-012) turned anything up,
and that pair is documented as derived.

Stated limit, which the check prints itself: overlap is evidence about the
corpora compared. Finding none here is **not** evidence about training data.

### N-005
**Four models · re-ordering the options moved nobody beyond noise**
`order-stability` (P9) · 2026-08-09 · negative, underpowered

| model | moves | items that flipped | noise band |
|---|---|---|---|
| llama-3.2-3b | 0.0 | 6 | 12.0 |
| llama-3.1-8b | −2.5 | 3 | 8.5 |
| ministral-8b | −2.5 | 1 | 4.9 |
| qwen3-30b | 0.0 | 0 | 0.0 |

Permuting the option block moved no model further than the flip churn explains.
Also 0 of 6 model pairs swapped places under re-phrasing.

**This is a weak negative and the reason is on the record.** Two of the four
models score 100% on these 40 items, and `dead-weight` reports 82% of items
separating nobody. An instrument at the ceiling cannot show a swing, so "no
order sensitivity" here means "none detectable with these models on these
items", not "option order does not matter". Harder items would make this a real
test; these do not.

It is recorded anyway because it is the only live shuffle probe this repository
has ever run, and it is what forced [D-019](#d-019).

### N-006
**Four models · the probe proved it can detect memorisation, then found none**
`canary-regurgitated` (S10) · 2026-08-09 · negative

| model | controls reproduced | this pod's canary |
|---|---|---|
| llama-3.2-3b | 3/3 | 0/1 |
| llama-3.1-8b | 3/3 | 0/1 |
| ministral-8b | 3/3 | 0/1 |
| qwen3-30b | 3/3 | 0/1 |

Every model completed *"To be, or not to be, that is the"*, *"We hold these
truths to be self-evident, that all men are created"* and *"The quick brown fox
jumps over the lazy"*. None completed this pod's canary.

**This is the strongest shape a negative result can take**: the instrument
demonstrated on the same call that it detects the thing it was looking for, and
then did not find it. A canary probe whose controls fail is blind, and S10
correctly skips rather than reporting a clean bill; that path has a trial of its
own. Here it did not need to.

**What it does and does not license.** It says these four models cannot complete
a string authored for this repository, which is what you would expect of a
canary minted after their training cutoffs. It says nothing about whether the
*items* were memorised, only the canary that travels with them, and nothing at
all about any other model.

**The canary is now partly spent**, which is the documented cost of running this
probe: the string went to a provider and sits in their logs. For this pod the
marginal cost is small, because publishing the repository published the canary
anyway, and that is the design: a canary is meant to be findable later.

---

## Defects in dinostomp itself

Every one of these was in the flattering direction. That is not a coincidence
worth being proud of, it is the direction bugs in a validator take by default:
a check that fires too little looks like a clean bill, and nobody investigates a
clean bill.

### N-007
**lm-evaluation-harness · both reported metrics re-derive exactly from the raw log-probabilities**
`verdict-rederive` (R8), by hand · 2026-08-09 · negative

The artifact: `open-llm-leaderboard-old/details_Corianas__111m`, file
`details_harness|arc:challenge|25_2023-07-19T13:48:53.093937.parquet`. 1172
ARC-Challenge items, 25-shot, run in July 2023 by people who had never heard of
this tool. The underlying ARC data is CC-BY-SA-4.0 (Clark et al. 2018).

Each row ships the per-choice log-probabilities alongside the verdicts, so both
reported metrics can be recomputed from the same file rather than trusted:

| claim | rows disagreeing |
|---|---|
| `acc` = `argmax(predictions) == gold` | **0 of 1172** |
| `acc_norm` = `argmax(predictions / len(choice)) == gold` | **0 of 1172** |

Nothing was found, and that is the result. A harness that publishes its raw
scores next to its derived ones is auditable by anyone, and this one survives the
audit exactly.

**Two things that also came back clean, worth recording because they are the
ones that usually bite.** Every row delivers all 25 requested few-shot examples
(counted in `full_prompt`), and no row is truncated. An earlier reading of this
file claimed a hard clip: 943 of 1172 prompts are exactly 2048 tokens long, which
looks like a context limit shearing the few-shot prefix. It is batch padding.
Subtracting the recorded `padded` count gives a clean unimodal 738 to 1316 tokens
with nothing at the ceiling. **The finding was killed before it was written
down**, and it is recorded here because a plausible artifact story that survives
one query and dies on the second is the normal case, not a rare one.

**Scope.** One details file from one run says nothing about lm-evaluation-harness
as software, and the model's score (17.6% / 19.7% against a 25% floor) is a fact
about a 111M model in 2023, not a number anyone should cite.
`num_effective_few_shots` is `-1` on every row, an unpopulated sentinel; that is
a gap in the record, not a defect in the run, since the prompt text shows the
shots arrived.

---

### N-008
**An even `run.repeats` reported p-squared instead of p, behind a confident interval**
`repeat-ties` (R20), measured against a known ground truth · 2026-08-09 · measured, fixed

`run.repeats` re-asks each item several times and scores the item by majority
vote. The rule was "strict majority, ties score 0". Ties only happen when the
repeat count is EVEN, and nothing in the tool warned about that, so the rule had
never been examined against a target whose true rate was known.

The instrument: a python target with a fixed, known per-item pass probability,
deterministic given call order, over 120 items. Ground truth is not estimated
here, it is set.

| true per-item rate | repeats=2 | repeats=3 | repeats=4 |
|---|---|---|---|
| **0.5** | **0.242** `[0.17, 0.33]` | 0.500 | **0.300** `[0.23, 0.39]` |
| **0.9** | 0.833 | 0.975 | 0.958 |
| **0.2** | 0.025 | 0.100 | 0.033 |

Read the top row. A model whose true per-item accuracy is 50% published **24% at
repeats=2**, and the Wilson interval around it **excluded the truth**. It is not
a conservative estimate, it is a different quantity: with ties scored 0,
repeats=2 reports the probability of passing an item TWICE, which is p squared.
At repeats=4 the same model reports 30%. The headline number moved 26 points on
a parameter whose entire purpose is to REDUCE noise, and all 54 checks were
silent about it.

**The fix, and why it is this one.** A tie is `uncheckable`, not `fail`. That is
not a new idea invented for this bug, it is the treatment every other
"the instrument reached no verdict" case in this tool already gets: excluded
from the accuracy denominator, reported on its own line, and surfaced through
`judgeability`. After the change the same runs report:

```
repeats=2  coin  acc 0.500 [0.38, 0.62] on 58 checkable (62 uncheckable excluded)
repeats=4  coin  acc 0.480 [0.37, 0.59] on 75 checkable (45 uncheckable excluded)
repeats=3  coin  acc 0.500 [0.41, 0.59] on 120 checkable (0 uncheckable excluded)
```

Odd repeats cannot tie, so **every existing pod using them is unaffected**, which
is why the fix is safe to apply to published evidence rather than only to new
runs.

**New check R20 `repeat-ties`**, diagnostic, reporting how much of a pod is
undecided, since "50% on 58 items" is only honest when the 62 it could not call
are printed next to it. R20 is n/a when nothing on disk repeats an item. Both
tails have a trial: an even-repeats pod that must warn, and an odd-repeats pod
that must stay silent, so "warns on ties" is not the same experiment as "warns
whenever repeats are set".

**Scope.** This says the estimator now reports the majority-vote rate over
DECIDED items. Majority-vote-of-k accuracy is still not the same quantity as
per-item accuracy, and for k > 1 it is deliberately more extreme than p: that is
what voting is for. What changed is that the number no longer depends on whether
k happened to be even.

---

### N-009
**The same agent, the same run: co-occurrence says 0%, the counterfactual says 100%**
`answer-grounding` (T4) against `answer-grounding-causal` (T7) · 2026-08-09 · measured

D-020 said T4 undercounts causally ungrounded answers by construction, and
estimated the gap at 6x from a live pod. The mediated rail can measure it
directly instead, because it can withhold the evidence and re-ask.

[examples/mediated](examples/mediated/) runs three agents over 24 items.
`oneshot` answers from memory FIRST and retrieves the right topic afterwards,
so its trace is immaculate and its answer owes that trace nothing:

```
[ok]   answer-grounding         0 of 3 target(s) pass items whose answer does not APPEAR ...
[warn] answer-grounding-causal  1 of 3 agent(s) answer identically with their evidence withheld
         - oneshot: 18 of 18 passing answer(s) (100%) are unchanged when the evidence is withheld
```

**T4: 0 of 18. T7: 18 of 18.** Not a 6x gap, a total one, on this pod. T4 is not
wrong about what it measures; it measures whether the answer APPEARS in the
retrieved text, and here it always did, because `oneshot` retrieves the correct
topic every time. Appearing is not using.

**Why this is a negative result and not a victory lap.** T7 caught this on a
SCRIPTED agent built to be caught, so what it demonstrates is that the
instrument distinguishes two agents whose traces are identical, not that it
finds ungrounded behaviour in the wild. The live-agent pod that produced D-020
is on the self-reported rail and cannot be ablated without being rewritten.

**T7's limits, one-sided in the same direction as T4's.** A nondeterministic
agent differs between the two arms by chance, which makes T7 UNDERSTATE
ungroundedness; it needs a deterministic agent or repeats. And an identical
answer proves the evidence made no difference to THAT answer, not that the agent
could never use evidence.

---

### N-010
**What the process boundary actually buys, measured claim by claim**
`tests/test_sandbox.py` · 2026-08-09 · measured

`isolation: subprocess` runs a mediated agent in a child with a stripped
environment, no tool code, a replaced `socket` module and an enforced timeout.
Every claim below is a test with a CONTROL: the same agent, on the same pod,
with `isolation: inprocess`. Without the control, "the key was not visible"
could just mean nobody set one.

| claim | sandboxed | in-process control | verdict |
|---|---|---|---|
| reads `OPENROUTER_API_KEY` | `NO-KEY-VISIBLE` | `sk-do-not-leak-this` | **stopped** |
| calls the FORBIDDEN tool via `tools._registry` | `NOTHING-TO-REACH` | `ran rm -rf /` | **stopped** |
| opens a socket | `SOCKET-DENIED` | (not attempted) | **stopped** |
| prints a forged protocol message | answer intact | n/a | **stopped** |
| hangs forever | killed at `timeout_s` | would hang the run | **stopped** |
| re-execs a fresh interpreter to get a socket | works | works | **NOT stopped** |
| reads the tool file with `open()` | works | works | **NOT stopped** |

The last two rows are the point of the table. They are asserted as PASSING tests,
so strengthening the boundary later breaks them and forces the documentation to
be rewritten on purpose instead of quietly drifting into an overclaim.

**The honest summary**: `subprocess` is CONTAINMENT, not confinement. It defends
a run against an agent that is careless, buggy, or quietly overreaching. It does
not defend a machine against a hostile one, and nothing written in Python would.
Untrusted agent code belongs in a VM.

**Cost, since it is not free**: about 130ms per item for process startup, on a
24-item three-agent pod that is 9.5s instead of under a second. `inprocess`
stays the default for that reason.

---

### N-011
**Inspect AI · the second foreign format cost one defect, where the first cost five**
`dinostomp import` (adapter) · 2026-08-09 · measured

The evidence contract claims *anything that can write conforming evidence is
auditable*. After the lm-evaluation-harness import that claim rested on n=1, and
n=1 had produced [D-021](#d-021) to [D-025](#d-025). Five defects on first
contact is evidence that first contact is expensive, not evidence that the
contract generalises. This is the second data point.

**The artifact**: Inspect AI, the UK AI Security Institute's eval framework.
Four real logs from `UKGovernmentBEIS/inspect_ai` (MIT), fetched by
`benchmarks/inspect-import/fetch.py` and not vendored: a `.eval` archive
(MMLU), two `.json` task logs, and one agent run with real browser tool calls.

**What did NOT transfer, and needed adapter code rather than a fix:**

| Inspect | what it needed |
|---|---|
| nested document, not a table | an adapter; the flat column mapper cannot read one at all |
| verdicts are `C` / `I` / `P` / `N` | `C`/`I` map; **`P` and `N` do not** and import as `uncheckable` |
| several scorers per task | the [D-023](#d-023) rule again, in a new costume: listed, and the caller chooses |
| `epoch` | Inspect's word for a repeat, so it becomes `repeat` and R20 applies |
| tool `events` | a real trajectory, which is what makes T1-T6 reachable |

The partial-credit case is the one worth naming. Inspect distinguishes a PARTIAL
score and a NOANSWER from an incorrect answer, and this battery's verdict is
binary. Rounding either into a pass or a fail would invent a number, so both
import as `uncheckable` and stay out of the accuracy denominator, which is
machinery that already existed for exactly this.

**What it cost: one defect, [D-031](#d-031).** Not five. The record schema, the
witness gate, the drift boundary, the unprivileged-manifest rule and the
absent-field-means-skip rule all held without modification against a format
shaped nothing like the first one.

**Scope, since one more data point is still two data points.** Both formats are
batch eval logs from the Python ML ecosystem. A streaming log, a database-backed
runner, or a harness with a genuinely different unit of work (a conversation
rather than an item) has not been tried, and this says nothing about those. The
honest claim is narrow: the contract survived a format that shares none of the
first one's shape, and the second cost 20% of what the first did.

---

### N-012
**dinostomp scored against human annotation: 5% recall, 25% precision, and 2 items the humans missed**
`dup-options` (S5) vs MMLU-Redux 2.0 · 2026-08-09 · measured

Every other entry in this ledger is self-graded: a defect dinostomp found that
nobody independently confirmed, or a defect in dinostomp found by dinostomp. The
scorecard below says so in its own words. This is the first entry that is not.

**The ground truth**: MMLU-Redux 2.0, 5,700 MMLU items re-read and labelled by
people at Edinburgh who had never heard of this tool. 370 of 5,700 (6.5%) carry
a defect label.

**What is even reachable.** The data-scope checks read a dataset AT REST. Of
Redux's six error types, one is within reach and only its verbatim subset:

| Redux error type | n | reachable by a data-at-rest check? |
|---|---|---|
| `bad_question_clarity` | 132 | no, needs judgement |
| `wrong_groundtruth` | 106 | no, needs the truth or a fleet |
| **`multiple_correct_answers`** | **39** | **the verbatim subset only** |
| `no_correct_answer` | 36 | no, needs the truth |
| `expert` | 32 | no, needs an expert |
| `bad_options_clarity` | 25 | no, needs judgement |

**The numbers, in the framing that flatters least first.** As first measured,
and after the fix this measurement paid for:

```
                                              as measured        after the fix
S5 dup-options vs ANY human defect        precision 14% / recall 0%    25% / 1%
S5 dup-options vs multiple_correct        precision 14% / recall 3%    25% / 5%
```

**5% recall.** 37 of the 39 items are SEMANTIC duplicates, and no byte
comparison finds those: *"steadily in one direction"* against *"in one
direction"*, or a logic item whose options are equivalent under a notation
convention. A mechanical data audit does not substitute for reading the
questions, and this is the number that says by how much.

**The precision figure is the wrong reading of the 8 flags.** Splitting them on
the question that decides whether a flag is a defect, is the DUPLICATED option
the one the key points at:

- **4 of 8 have the keyed answer duplicated.** Two identical correct options, by
  construction. Humans labelled **2 of those 4 as `ok`** ([F-018](#f-018)).
- **4 of 8 duplicate a non-key option.** A four-option item effectively offering
  three. A real defect, and outside Redux's taxonomy, so `ok` is not wrong there
  and counting them as false positives is not either.

### What this measurement bought, which is the point of taking it

A 3% recall is not a verdict, it is a starting number, and having it made the
next step an experiment instead of an argument. 38 misses, sorted by whether
anything mechanical could reach them:

| class | n | reachable |
|---|---|---|
| genuinely semantic | 30 | no |
| substring containment | 5 | yes, at a price |
| punctuation-only | 2 | yes, at a price |
| case or spacing only | 1 | yes |

Each candidate rule was then run against BOTH Redux and the repo's own MMLU
copy, and the prices are why three of them are not in the tool:

| rule | extra catches | extra false positives |
|---|---|---|
| **case/spacing, one collapsed pair** | **+1** | **0** |
| naive case-folding | +1 | +3 (MMLU genetics: `BB Bb` vs `Bb bb`) |
| strip punctuation | +2 | +75 (formal logic: `(F • L) • ~C` vs `F • L • ~C`) |
| substring containment | +3 | +481 |

S5 now folds case and spacing ONLY when exactly one pair collapses. Where case
carries the content, folding merges nearly everything (MMLU's Punnett items fold
four options into one), and a wide collapse is the signal that the case IS the
answer. That distinction is the whole fix, and it is worth eleven precision
points and one real catch.

**The near-miss worth recording.** S5 already carried a comment saying
case-folding had been tried and rejected. The Redux measurement said folding was
free, and acting on that alone would have shipped three false positives into a
GATING check, because Redux's 5,700-item sample does not happen to contain the
genetics items the original decision was made on. The prior decision was right;
it was the SCOPE that was wrong. Checking the old claim against the repo's own
MMLU copy before overriding it is what caught that, and the general form is: a
measurement on one sample is not a licence to reverse a decision made on
another.

**S1 is reported and not scored.** It flags 32 duplicated keys covering 64
items, all labelled `ok`. Redux annotates whether an item is ANSWERABLE, not
whether it is UNIQUE, so those are not false positives; the two instruments are
answering different questions. Printing "0% precision" for that would be a
number that looks like a measurement and is not one.

**What this establishes**, stated narrowly because the temptation is to state it
widely: on the one axis where the two overlap, mechanical auditing and human
auditing each caught items the other missed. It says nothing about the other 47
checks in the battery, which need runs rather than a dataset, and nothing about
any dataset other than MMLU.

Reproduce: `python benchmarks/mmlu-redux/fetch.py && python benchmarks/mmlu-redux/compare.py`.
The script asserts its reproduced rules against the battery's own counts before
comparing anything, because a comparison that quietly scores a different rule
would be worse than no comparison.

---

### N-013
**The obvious AI fix does not work: 14-18% precision across three framings and two model tiers**
`semdup` extension · 2026-08-09 · measured, NOT shipped

[N-012](#n-012) measured where a byte comparison runs out: of 39 items humans
label `multiple_correct_answers`, the deterministic check reaches 2, and the
other 37 are semantic. Recognising *"steadily in one direction"* against *"in
one direction"* needs a reader, so the obvious next move is to ask a model.

It was built, validated against the human labels BEFORE shipping, and it does
not work.

**The set**: all 39 human-confirmed positives, plus 250 human-labelled `ok`
items sampled at seed 7. The negatives are the ones that matter. A check that
flags everything has perfect recall, and a real 3,000-item benchmark contains
~50x more clean items than dirty ones, so the false-positive rate decides
whether a check is usable at all.

| framing | judge | recall | precision | FPR on clean items | false flags per 3,000 |
|---|---|---|---|---|---|
| "do any two mean the same?" | llama-3.1-8b | 100% | 14% | **98.4%** | ~2,950 |
| "do any two mean the same?" | qwen3-30b | 38% | 18% | **27.6%** | ~830 |
| "is any OTHER option also correct?" | qwen3-30b | 95% | 18% | **69.2%** | ~2,080 |

To find roughly 37 real defects.

**The diagnostic is that precision does not move.** 14%, 18%, 18%. Changing the
prompt and the model tier slides recall and the false-positive rate along one
curve without improving the DISCRIMINATION, which is the signature of a task
limit rather than a prompt limit. Three attempts is not a proof, and it is
enough to stop before publishing a tool.

**Why, and it is structural.** The false positives are sets like:

```
econometrics: ['Unbiased and consistent', 'Biased but consistent',
               'Biased and inconsistent', ...]
```

Those distractors are DESIGNED to be confusable; that is what makes a
multiple-choice item discriminate. So "could a second option be defended as
correct?" is close to the question the item exists to ask, and a judge answering
it reliably would be a judge that can sit the exam. The prior probability of a
false positive is structurally high in a way no wording fixes.

**Not shipped, and kept.** The extension stays in `extensions/semdup/` with its
numbers in its README, its module docstring, and in the text of every finding it
emits. Three reasons: "use an LLM to find duplicate options" is an obvious idea
someone will have again; the apparatus (per-pod opt-in, verdicts cached by
(item, judge) so re-runs are free and offline, a spend cap priced from recorded
usage, a skip rather than a crash without a key) is reusable for a check that
does work; and a plugin that is wrong four times in five should be discoverable
as such rather than quietly absent.

**What would change this.** Precision above ~80% on this set. The harness takes
`SEMDUP_JUDGE=<model>`, so a frontier judge is one command away, and this entry
should be replaced by whoever gets that number.

**Scope.** One dataset, one task, three framings, two judges, 289 items. It says
nothing about LLM-as-judge in general, and it is not evidence that judges are
bad at semantics. It is evidence that THIS question, on data engineered to be
confusable, is not answerable at a precision that makes a check worth running.

Total cost of finding this out: about 3 cents.

---

### D-001
**The money invariant had only ever run at zero**
`spend-ledger` (R3) · first live fleet · fixed

Per-record costs rounded to six decimals. Small models bill fractions of a
microdollar per call, and 120 of those rounding errors accumulated thirty times
the tolerance for drift between a manifest's total and the sum of its own
records. Every dry pod had passed because every dry cost was exactly `0.00`.
Ledger precision went to nine decimals.

### D-002
**Pooling hid a model that never read the question**
`above-guessing` (R7) · first live fleet · fixed

One 1B model answered the same label to all 120 items. On a balanced key that is
exactly 50%, which reads as chance-level performance rather than as not
answering. Pooled across the fleet, accuracy was 71% and the check passed.

Now judged per model. This was the **fourth** time this project found the same
pooling defect, after R13, T4 and T6: treat any fleet-level statistic as guilty
until checked.

### D-003
**A collapsed model manufactured 8 phantom key errors**
`item-discrimination` (P2) · first live fleet · fixed

P2 flagged eight items in a real dataset as candidate key errors. Excluding one
constant answerer dropped it to one: a model giving the same answer to
everything scores full marks on every item keyed to that answer regardless of
difficulty, dragging their point-biserials negative. The psychometric checks now
exclude near-constant models and say so in the finding.

### D-004
**A gating check returned BROKEN on all of GSM8K**
`answer-leak` (S2) · 2026-08-09 · fixed

27 of 1319 items flagged as answer leaks; **all 27 false positives**. The
reference answer was a number the question had to state: `gsm-0020` answers `15`
and its question says "15 liters of pineapple drink".

S2 **gates**, so this is not a nuisance warning. A battery that returns BROKEN on
a whole famous benchmark teaches users to ignore the gate. Purely numeric targets
are now exempt, and GSM8K reads `0 of 1319`. TruthfulQA went 3 to 1 the same way:
two were forced choices that cannot be asked without naming their own answer.

The forced-choice exemption is deliberately narrow, requiring the target within
60 characters of the "or", because splitting the question and accepting a hit
anywhere would mean appending `" or something"` opens a gating check. A negative
test does exactly that and asserts the gate stays shut.

### D-005
**A choice item was keyed on its question alone**
`dup-questions` (S1), `conflicting-keys` (S7) · 2026-08-09 · fixed

MMLU asks *"Which of the following statements is correct?"* many times over
completely different option blocks. Keyed on the stem alone, 22 were called
duplicates and 11 called contradictory, on two more **gating** checks.

Item identity is now question plus options, compared as a set so a permutation is
still the same item. [F-003](#f-003) is what survived the fix.

### D-006
**Any probe was read as the blind probe**
`blind-solvable` (R13), `input-blind` (R15) · 2026-08-09 · fixed

The judge, canary, crossjudge and shuffle probes all run with the inputs
**intact**. R13 filtered on "is a probe" rather than "is the blind probe", so a
shuffle probe scoring 77% became *"this eval is solvable WITHOUT the question"*:
a fabricated blind accuracy, stated confidently, derived from a run that had the
question. The other three probe readers filtered by type. This one never did.

**The first regression test for this passed against the unfixed code**, because a
mismatched run-file stem made the probe invisible to discovery. It had to be
rebuilt before it proved anything.

### D-007
**Moves were compared to a flat percentage, not to noise**
`order-stability` (P9), `seed-stability` (P10) · 2026-08-09 · fixed

Both warned above 10 points regardless of sample size. At n=120 a 10-point move
is inside the noise band; at n=5000 it is far outside. One constant cannot be
right at both ends, and P10 was about to warn on a seed spread of 1.7 standard
errors on the first real benchmark this tool was ever pointed at.

Both now compare against sampling noise at the actual n: unpaired for P10, since
each seed draws its own items; McNemar for P9, since the shuffle probe re-runs
the same ones and the pairing was being discarded. Both also require a practical
floor, because a 2-point move at n=20000 clears significance and is still not a
finding. [F-005](#f-005) is what the fixed check found.

### D-008
**31 manufactured key errors, and a first fix that was itself flattering**
`item-discrimination` (P2) · 2026-08-09 · fixed, scoped

On a real 4-model GSM8K fleet, P2 flagged 31 of 303 items as candidate key
errors. They are not findings: a point-biserial over four examinees can take only
a handful of values, and an item that only the weakest model got is strongly
negative by construction.

Choosing the null is the whole problem, and two obvious ones are wrong in
opposite directions. Redrawing each model's outcomes from its own accuracy
destroys item difficulty and expects 65, hiding five inverted keys. Permuting
which models passed each item destroys fleet skill and expects 114, hiding
everything. The null holding **both margins fixed**, sampled by flipping 2x2
checkerboards, expects 31 against an observed 31.

**That last sentence is a trap, and it took a second measurement to see it.**
"Expected 31, observed 31" reads like a null landing on the data. It is closer to
the opposite: with four examinees a fixed-margins null is nearly degenerate, so
it tracks whatever it is handed. Inverting 45 of the 303 keys, 15% of the
dataset, moves the observation and the null by the same amount and P2 still says
nothing.

Measured power, 200 items, 10% of keys inverted, five replicates:

| examinees | detects | false alarms |
|---|---|---|
| 6 | 0/5 | 0/5 |
| 12 | 2/5 | 0/5 |
| 24 | 3/5 | 0/5 |
| 40 | 5/5 | 0/5 |

**P2 is one-sided.** When it fires, believe it: no false alarms at any size. When
it is quiet on a small fleet it has told you nothing, and its pass message now
says so. The first fix was flattering in its own right: swapping a check that
manufactures findings for one that cannot see is an honesty gain and a power
loss, and shipping it as a clean win would have been the same error one level up.

### D-009
**`plan` understated a bill by 3x**
`plan` · 2026-08-09 · fixed

`run.seeds` repeats the whole eval once per extra seed and every one of those
calls is billed. The forecast counted one pass. The cap was never at risk, being
checked against actual spend before every call, but `plan` exists so nobody
learns this from the bill.

### D-010
**The engine hashed itself and nothing read it**
`engine-drift` (R19, new) · 2026-08-09 · fixed

`tool_sha256` was written into every manifest and read by no check, making the
engine the one input inside the drift boundary that could change without anyone
being told.

Its first act was to catch this repository. The committed iris pod's `CLEAN`
report had been computed over twelve run files from **two different engines**,
six from tool 0.24.0 sitting beside six fresh ones. Thirty of the fifty-five
committed example runs were stale that way.

### D-011
**Published reports only verified on the author's machine**
`verify` · 2026-08-09 · fixed · found by CI

The first CI run on a machine that was not the author's failed all six jobs, and
it was right to. Reports embedded the **absolute path** of the spec, so the
re-derived `target` read `C:\Users\...` here and `/home/runner/...` there and the
byte-comparison failed. That contradicted the claim the command itself prints:
that a stranger can check a published verdict without trusting the publisher.

The local suite could not have caught it, because it always verified each pod
exactly where it was generated. The new test copies every pod to a fresh
directory first, which is what a stranger has.

### D-012
**Line-ending translation is drift**
`input-drift` (R1) · 2026-08-09 · fixed · found by CI

Every writer used Python's default newline handling, which turns `\n` into
`\r\n` on Windows. The drift boundary hashes **exact bytes**, so a pod generated
on Windows and checked out anywhere else hashed differently.

The badge failing was the tell: a badge carries only the verdict and the
coverage, so a check had to be changing result across platforms, not just a
rendering detail.

Every writer now pins `newline="\n"` and a `.gitattributes` marks the byte-exact
artifacts `-text`. **The first `.gitattributes` did nothing**: the catch-all
`* text=auto` was written last, and the last matching pattern wins, so
`git check-attr` still reported `auto` on every file it was meant to protect. CI
was green anyway because the writer fix was carrying it alone.

### D-013
**Smaller ones: a wrong hint, two wrong witnesses, and a near-miss**
various · 2026-08-09 · fixed

- **W1's whitespace-mutant hint** told you to write a witness that cannot kill
  that mutant, which collapses runs of whitespace rather than removing it.
- **The witness gate caught the author twice** while writing the GSM8K pod, over
  two witnesses declared `fail` that a numeric scorer actually returns
  `uncheckable`. It has not judged the answer wrong; it has not judged it.
- **A near-miss, measured before shipping.** The obvious follow-up to
  [F-002](#f-002) is comparing options case-insensitively. It calls four correct
  MMLU items defective, because their case **is** the answer: `Bb Bb` against
  `BB Bb` in the genetics items, `Sc ⊃ Ej` against `sC ≡ eJ` in the
  predicate-logic ones. `dup-options` stays exact, with a test pinning it.

### D-014
**The overlap check compared questions and ignored options**
`corpus-overlap` (S11) · 2026-08-09 · fixed

Pointing S11 at nine datasets reported ARC-Easy and ARC-Challenge as sharing an
item. They do not. Both ask *"Which is NOT an example of a chemical change?"*
over completely different option blocks with different keys:

```
ARC-Easy       choices: ['Melting ice', 'corroding silver', 'Burning match', 'Rotting vegetation']
ARC-Challenge  choices: ['Boiling water', 'Rusting iron', 'Burning wood', 'Baking bread']
```

**Same defect class as [D-005](#d-005), in a check written three releases later.**
Knowing about a bug is not the same as not writing it again.

The fix is not simply "add the options", because this check answers two
questions that want different keys:

- *is this literally the same item?* wants question **and** options.
- *could a model have memorised this?* wants the **question alone**. A memorised
  question survives an option rewrite, which is exactly what MMLU-Pro did to
  MMLU.

Collapsing those into one number would make a contamination finding mean
different things depending on which dataset produced it. Both are now computed
and reported separately, which is how [F-012](#f-012) can say 22 and 136 rather
than one misleading 158.

### D-015
**Position and length bias reported class balance on a fixed label set**
`position-bias` (S3), `length-bias` (S4), `surface-shortcut` (S9) · 2026-08-09 · fixed

BoolQ offers `["yes", "no"]` on all 3000 items. "yes" is longer than "no", and
BoolQ's answer is yes 62% of the time, so `length-bias` reported *"gold is
strictly longest, +12% over expectation"* while actually measuring the class
distribution.

Those checks are about how each item's **distractors were written**. With one
vocabulary shared by every item there are no per-item distractors, so they are
now `n/a` with the class balance stated instead:

```
[n/a] length-bias   every item offers the same options, so position and length are
                    properties of the label set rather than of how each item's
                    distractors were written. What varies is class balance:
                    'yes' is the answer 62% of the time
```

`dup-options` and `target-not-offered` still run, because those are facts about
an item's own option list either way.

### D-016
**The SciQ fetcher put the answer at index 0 on every item**
`position-bias` (S3) · 2026-08-09 · fixed

SciQ ships the answer and three distractors as separate columns, so option order
has to be reconstructed. Keeping the source column order put gold first on all
1000 items, and the check duly reported it overshooting position 0 by **75%**.

That was a finding about the loader, not about SciQ, and it cascaded: it also
drove the shortcut check. **A report whose findings are about its own loader is
worse than no report.** The pod's spec had a comment saying the order was
reconstructed, which is not the same as not publishing the artifact.

Options are now shuffled per item from a seed derived from the item id:
deterministic, reproducible, and position carries no information. Position bias
dropped from +75% to +3%, the nine real duplicate options survived, and
[F-013](#f-013) became visible underneath.

### D-017
**A truncated judge was diagnosed as a judge with no opinion**
`judge-agreement` (J1) · 2026-08-09 · fixed

The first real hosted judge run scored **50% agreement on cases whose verdict is
known by construction**, which reads as "this judge cannot do the task". It was
not. 39 of 128 gradings came back `uncheckable` with the message *"judge response
contains no PASS/FAIL verdict"*, and the actual cause was a 200-token cap.

The judge prompt asks for **reasoning, then the ruling on the last line**. That
is the right order for grading quality and it means the single token that matters
is the first thing truncation takes. The generic message sent the author to look
at the rubric instead of at the cap.

The parse now distinguishes the two, using the provider's own `finish_reason`
rather than guessing:

```
judge response ends mid-sentence after 1031 chars with no PASS/FAIL; it was
almost certainly truncated. Raise scorer.judge.params.max_tokens: this prompt
asks for reasoning before the ruling, so a short cap loses the ruling
```

Raising the cap took agreement from 50% to **100%** with no change to the judge
or the rubric.

### D-018
**Every non-judge probe crashed the CLI, not just cross-judge**
`--probe crossjudge`, `--probe canary` · 2026-08-09 · fixed

`KeyError: 'accuracy_on_checkable'`. The CLI special-cased the judge probe's
summary shape and no other, so any probe whose summary carries no accuracy
reached the line that prints one.

Found on `--probe crossjudge`. **The scope was wider than that entry first
said**: running `--probe canary` a release later showed its summary has no
`accuracy_on_checkable` either, so pre-fix it would have raised the same
KeyError. The fallback added for cross-judge is what caught it, which is the
only reason the canary run printed a line instead of a traceback.

These probes had only ever been exercised by trials calling the runner directly.
Nobody had typed the commands. Now every probe shape prints as a probe, and the
fallback names the probe rather than assuming a field.

### D-019
**The docs claimed a 28-point swing with no run behind it**
METHODOLOGY.md · 2026-08-09 · **WITHDRAWN**

METHODOLOGY said, of the shuffle probe: *"On real models that swing reached 28
points."* Going to run that probe for real turned up the problem: **there were
zero live shuffle runs on disk.** The number came from an early study that
predates this repository's receipts, and P9 has since been rebuilt around a
McNemar noise band, so it is not even clear the same figure would be reported
today.

An unbacked number in the docs of a tool whose entire argument is receipts is
the worst place to have one. The claim is withdrawn rather than softened, and
replaced with the measured figure: **at most 2.5 points, inside the noise band
on all four models** ([N-005](#n-005)).

The general lesson is the one this project keeps paying for: a claim survives in
prose long after the evidence for it stops being reachable. The only reason this
surfaced is that someone finally typed the command.

### D-020
**The grounding check undercounts by 6x, by construction**
`answer-grounding` (T4) · 2026-08-09 · scoped, not fixed

`live-oneshot` generates its answer **before** it calls `retrieve` at all. By
construction, 100% of its correct answers are causally ungrounded. T4 reports
**16%**.

```
live-oneshot: 19 passing answers
  answer text appears in the retrieved snippet: 16   <- T4 calls these grounded
  answer text absent:                            3   <- T4 flags these
```

The gap is not a bug in the implementation, it is what the check measures. T4
asks whether the answer **appears in** the trace's tool results. It cannot ask
whether the answer **came from** them, because a trace records what was fetched
and not what was used. When an agent answers from memory and retrieves the right
topic anyway, the two coincide and the check sees nothing.

**SUPERSEDED in v0.42.0 by T7 `answer-grounding-causal`.** The fix named here
was right and is now built: the mediated rail holds the tools, so `--probe
ablate` can withhold every tool result and re-ask. An answer that does not move
did not depend on the evidence. On a pod where T4 reports 0 of 18, T7 reports 18
of 18 ([N-009](#n-009)).

T4 is NOT removed and NOT softened. It is the only grounding check available on
the self-reported rail, which is where most agent pods live, and its finding
still says what it measures and which way it errs.

What changes now is the claim. T4's finding text and METHODOLOGY said grounding
was checked; they now say what is actually checked, which is co-occurrence, and
name the direction of the error: **T4 undercounts ungrounded answers and never
overcounts them.** A T4 warning is therefore a floor, and its silence is not a
clean bill.

---

### D-021
**The most common eval-log shape in the field could not be imported at all**
`dinostomp import` · 2026-08-09 · fixed in v0.40.0

`output` was a required record field. A loglikelihood-ranking harness never
produces one: it scores candidate continuations by log-probability and takes the
argmax, and the model emits no text whatsoever. That is how ARC, MMLU and
HellaSwag are scored on the Open LLM Leaderboard, so the refusal covered a large
share of the eval logs that actually exist.

The importer's whole stated purpose is that the battery consumes *schemas*, not
"whatever `dinostomp run` wrote". It had never been tested against a log with a
genuinely different shape, and the first one it met was rejected at the door.

Fixed by making `output` optional, so R8, R14 and R16 skip **naming the field**
and the coverage line shortens honestly. An absent output is **omitted**, never
written as `""`: an empty string is the claim that the model answered with
nothing, which is a result, and absence is the claim that it never emitted text,
which is not.

---

### D-022
**A check overwrote the evidence contract's skip reason with a false one**
`scorer-artifact` (R16) · 2026-08-09 · fixed in v0.40.0

With `output` absent on all 1172 records, R16 skipped and reported:

```
[skip] scorer-artifact   no model has 5+ failed records to inspect
```

There were **966 failed records**. The statement was false, and the action it
implied (collect more failures) would never have helped, because no quantity of
failed records carries text that is not there. The contract had already recorded
the true reason; R16's body then called `skip()` a second time and replaced it.

`Reporter.check()` already refused to revive a contract-disqualified check.
`Reporter.skip()` had no such guard, so any check that skips from its own body
could silently overwrite the only actionable half of the message.

This is the recurring defect class in this ledger, again: **a check that compared
the wrong thing and returned a confident answer about it.** Here it compared "how
many failed records survived my filter" against a threshold and reported that as
the reason, when the filter was what had removed them.

Fixed, and negative-tested in both directions: a body skip can no longer replace
a contract skip, and an ordinary skip is still overwritable, or the first reason
any check gave would freeze in place and hide better ones.

---

### D-023
**A rival score column was chosen silently, and it was the one nobody published**
`dinostomp import` · 2026-08-09 · fixed in v0.40.0

The log carries two per-item verdicts, `acc` and `acc_norm`. Only `acc` was in
the candidate list, so the mapping took it without comment:

```
  score    <- acc
```

They disagree on **221 of 1172 items**: 17.6% against 19.7%. The Open LLM
Leaderboard ranked ARC by **`acc_norm`**, the one that was not chosen. dinostomp
would have imported, audited and published a headline number nobody reported,
behind a mapping line that looked like it had told you everything.

Fixed by refusing. Any unmapped column whose every value reads as a verdict is a
rival, and the refusal fires only when it actually **disagrees**, so a log
carrying a duplicate of the same verdict still imports clean. The rule needs no
list of known harness column names, which matters because the next harness will
not use these ones.

**The guard has a guard.** The first version fired on `truncated`, which is `0`
on all 1172 rows and therefore "disagreed" with the score on exactly the rows
that passed. A column that never varies is a flag, not a rival verdict, and is
now excluded. Caught on the first live run of the new rule.

---

### D-024
**`run --dry` would have fabricated a full set of records for a model it cannot call**
`dinostomp run` · 2026-08-09 · fixed in v0.40.0

There was no way to declare a model whose evidence comes from somewhere else: the
provider enum had no value for it, so the imported pod could not be written at
all. Adding `imported` exposed the sharper problem. `--dry` substitutes the
offline deterministic provider for whatever the spec declares, *before* any
provider dispatch. A `run --dry` on an imported pod would therefore have written
1172 schema-valid records, with a real model's name on every one, containing
answers that model never gave.

Refused before the substitution rather than after, and tested on both the live
and the `--dry` path. The two failure modes are not the same and only one of them
is quiet.

---

### D-025
**An error message named a flag nobody can type**
`dinostomp import` · 2026-08-09 · fixed in v0.40.0

```
[import] --item_id-field: no column looks like the item_id. ... Pass --item_id-field.
```

The flag is `--item-id-field`. The message was built by interpolating the
canonical field name, which uses an underscore, so copy-pasting the tool's own
instruction produced an argparse error. Small, and it was the first thing the
first foreign log printed.

---

### D-026
**The item-majority estimator shipped for eleven versions without ever running live**
`dinostomp run` · 2026-08-09 · fixed in v0.41.0

N-008 is the number. This entry is how it survived.

`run.repeats` had unit tests, a fleet-matrix implementation, a docstring
explaining the estimator discipline, and a reviewer-note citation. It had never
been executed end to end by a real runner against a target that could disagree
with itself. Every pod in this repository, every trial, and every benchmark ran
at `repeats: 1`, where the code path is dead.

The unit test that covered it asserted the bug. Its own comment read
**"the b tie scores 0, conservative"** — the wrong word, chosen while writing the
test rather than while measuring anything, and then trusted for eleven versions
because a green test looks the same whichever behaviour it pins.

Two structural fixes, not just the arithmetic:

- **The tie rule now exists once**, as `psychometrics.majority()`, imported by
  both the summary and the fleet matrix. It was implemented twice before. They
  happened to agree, which is luck, not parity.
- **Every count the item-majority estimator prints is in ITEMS.** Fixing the
  ties first produced a summary whose numerator was items and whose
  `n_uncheckable` was records, which would have put two units on one line.
  Caught by the test rewrite, before it shipped.

The lesson is the one this ledger keeps recording: a code path with tests but no
live execution is untested, and the flattering direction is always the one that
survives. Here it survived behind a comment that said the number was
conservative.

---

### D-027
**Two defects in the pod written to demonstrate the new rail**
`dup-questions` (S1), `forbidden-tool` (T1) · 2026-08-09 · fixed in v0.42.0

The first run of `examples/mediated` came back **BROKEN, 2 gated findings**, in a
pod written that hour by the person who wrote the checks:

- **8 duplicated questions among 24.** The items were generated as three
  repetitions of eight topics. The intent was three phrasings each; the loop
  emitted the same phrasing three times. A pod meant to demonstrate careful
  measurement shipped a third of the dataset as copies.
- **24 forbidden tool calls.** A `rulebreaker` agent was included to show
  call-time denial working, which gated the pod. Correct behaviour, wrong place:
  a planted violation belongs in the trials, where the expectation is recorded,
  not in a committed example whose verdict then reads BROKEN forever.

Fixed by writing 24 genuinely distinct questions and moving the denial
demonstration into `trials/run_trials.py`, where it now has an expectation
(`T1 fail`) that the suite enforces.

Recorded because the tool caught its own author, immediately, on the pod built
to advertise it, and because the alternative was to notice neither and publish a
duplicate-riddled example as a showcase.

---

### D-028
**The line-ending guard could not see a file until the commit that broke it had happened**
`tests/test_examples_verify.py` · 2026-08-09 · fixed in v0.42.1

`examples/mediated/eval.yaml` was committed with CRLF. The local suite passed on
the very run that produced it, 413 of 413. CI failed a minute later.

The guard listed candidates with `git ls-files`, which reports only files that
are ALREADY TRACKED. A brand-new pod is untracked until its first commit, so the
check was blind to precisely the files most likely to carry a fresh mistake: new
ones. It was not a weak check, it was an OFF check, and it looked green while
being off.

```
local  (before commit):  413 passed          <- eval.yaml untracked, not examined
CI     (after commit):   committed artifacts carry CRLF: ['examples/mediated/eval.yaml']
```

This matters here rather than being cosmetic because `.gitattributes` marks
`*.yaml -text`: git stores those bytes verbatim, so a CRLF spec travels into
every clone, where `spec_sha256` no longer matches the runs it was produced
under and every published report fails to re-derive. That is D-012 again, from a
new direction.

Fixed by adding `git ls-files --others --exclude-standard`, so untracked files
are checked too. Negative-tested by planting an untracked CRLF file and watching
it fire, then removing it.

**And a latent one found while fixing it.** Pod CODE is hashed as well
(`target_sha256`, `tool_sha256_by_name`, a custom scorer's hash), and `*.py` was
left on `text=auto`. A Windows clone with `autocrlf` would have received CRLF
agent code, hashed it differently, and failed to re-derive a report that
verifies perfectly on Linux. Nobody had hit it; every pod `.py` in the repo
happened to be LF. `*.py` is now `-text` alongside the artifacts, for the same
reason and against the same failure.

---

### D-029
**"Policy is enforced at call time" was true only for an agent that asked**
`harness.py` · 2026-08-09 · corrected in v0.43.0

v0.42.0 shipped the mediated rail with this in its release notes:

> **Policy is enforced at call time.** `forbidden_tools` and `max_steps` are
> refused when the agent reaches for them, not audited afterwards.

True for any agent that goes through `tools.call`. `Tools` keeps the live
callables on `self._registry`, so an in-process agent reaches the forbidden tool
in one attribute access:

```python
tools._registry["shell"](cmd="rm -rf /")     # runs. policy never consulted.
```

**And the trace is empty afterwards**, because nothing went through `call`, so
the harness has no idea it happened. A pod doing this looks cleaner than one
that asked politely and was refused.

Found by writing the control for the subprocess rail rather than by reasoning:
the test asks the same agent to do the same thing on both rails and compares.

**Corrected rather than patched.** The in-process registry is not being hidden,
because hiding it in Python is theatre: a closure is still reachable through
`__closure__`, and shipping "harder to reach" as though it were "prevented" is
the exact move this project exists to object to. What changed is the claim.
Mediation buys TRACE integrity; only the process boundary buys POLICY integrity,
and `isolation: subprocess` now exists for that. Both are stated in
METHODOLOGY, in the module docstring, and in the test that demonstrates the
bypass.

**A second one, caught in the same hour and never shipped.** The first version
of the sandbox child did `sys.path.insert(0, base_dir)`, which let the agent
`import tools` and take the corpus and the forbidden function directly. That
made the SANDBOXED child weaker than the in-process rail on that axis, in the
module whose whole purpose was to be stronger. The pod directory is off the
child's path now; the agent module is loaded by file path and needs no entry.

---

### D-030
**The consent mechanism told you a pod ships no code, while it shipped an agent and its tools**
`dinostomp inspect` · 2026-08-09 · fixed in v0.43.1

`inspect` exists so `--trust-code` can be an informed decision: it reads a pod's
Python statically and reports what it reaches for. It collected paths from the
scorer, the judge, and `provider == "python"` targets. The mediated rail was
added in v0.42.0 and nobody extended the list.

```
$ dinostomp inspect examples/mediated/eval.yaml
mediated-grounding: ships no pod-local Python. Nothing here can run on your machine.
```

That pod ships `agent.py` and `tools.py`.

Two things make this worse than a missing feature. The sentence is not silence,
it is an **active reassurance**, and it is the single most flattering thing the
tool could have said. And the code it hid includes **tools**, which are the most
privileged code in a pod: they are imported and called in dinostomp's own
process, and that stays true under `isolation: subprocess`, because the boundary
exists to keep the AGENT away from the tools rather than to contain them. The
one file a reader most needs to see before typing `--trust-code` was the file it
did not mention.

Fixed: `inspect` now covers both target rails and every tool, and labels tools
`[runs in the PARENT process]` so their privilege is legible rather than
inferred.

**The test is written against the SPEC, not against a list of providers.** The
bug was a list someone had to remember to extend, so a test that also enumerates
providers would reproduce it. It asserts instead that any spec naming pod-local
Python anywhere must produce a listing, which the next rail cannot quietly slip
past.

Same shape as [D-028](#d-028) four hours earlier: a checker that skipped the
newest surface, looked green, and was off rather than weak.

---

### D-031
**An imported trajectory could never reach the six checks that read a trajectory**
`trajectory` policy, T1-T6, `trace-observed` (T8) · 2026-08-09 · fixed in v0.44.0

The Inspect adapter's best feature is that Inspect records real tool calls, so
an imported agent run can reach T1-T6. It could not. Two gates, both keyed on the
PROVIDER STRING rather than on the evidence:

```
$ dinostomp import demo/eval.yaml browser.json
CANNOT IMPORT:
  [trajectory] a trajectory policy is declared but no model uses a python or
               mediated target; nothing in this spec can produce a trajectory
```

A pod with `provider: imported` could not declare a trajectory policy at all, so
`forbidden_tools` and `required_tools` were unwritable for exactly the runs an
agent-log import exists to bring in. Past that, the linter selected trajectory
runs by provider too, so the checks would have skipped even with a policy in
place.

And T8, whose entire job is to say WHOSE trace you are reading, reported:

```
[n/a] trace-observed   this spec runs no code targets; nothing produces a trajectory
```

on a run carrying 4 recorded browser calls. The check that exists to name a
trace's provenance went silent on the one provenance a reader cannot guess.

**Fixed by gating on evidence rather than on a provider name.** An imported run
joins the trajectory checks if its records actually carry a trace, so a
loglikelihood import does not acquire six vacuous trajectory findings while an
agent import does get audited. T8 gained a third source, `foreign_observed`,
because the two it had could not express this:

```
[ok] trace-observed  all 1 run(s) carry a trajectory recorded by ANOTHER harness and
                     imported here. That is stronger than an agent's self-report, because
                     the exporting harness is a third party to the agent, and it is still
                     not this engine's own observation: T1-T6 are reading somebody else's log
```

Third time this week that a gate keyed on a NAME rather than on the thing it
cares about: [D-028](#d-028) listed tracked files instead of files,
[D-030](#d-030) listed providers instead of code, and this listed providers
instead of traces. All three looked green while being off.

---

### D-032
**A valid JSONL file it refused to read, and the error blamed the data**
`items.py`, and seven other readers · 2026-08-09 · fixed in v0.45.0

Pointing the battery at 5,700 real MMLU questions produced:

```
invalid JSON: Unterminated string starting at: line 1 column 37 (char 36)
```

The file was fine. Split on `\n`, all 5,702 lines parse. The reader used
`str.splitlines()`, which also splits on `\x0b`, `\x0c`, `\x1c`, `\x1d`,
`\x1e`, `\x85`, U+2028 and U+2029. `json.dumps(..., ensure_ascii=False)` does
not escape any of those and they are legal inside a JSON string, so a line
containing one gets torn in half and the fragment fails to parse.

**MMLU contains `\x85` (NEL) twice.** That is all it took. Any JSONL file
carrying one of those characters in a question was unreadable, and the error
pointed at the dataset rather than at the reader, which is the direction that
costs a user the most time: it says "your data is broken" when the truth is
"this tool cannot read your data".

Eight readers had it: `items.py`, `dataset.py`, `contamination.py`, two in
`lint.py`, two in `runlog.py`, and one in `runner.py`. All eight now go through
`spec.jsonl_lines`, which splits on `\n` and strips a trailing `\r` so a CRLF
file still reads.

Found by pointing the tool at somebody else's real data for the fifth time this
week. Every check in the battery had passed on every dataset in this repository,
because every one of those was written by this tool.

---

## The honest scorecard

**One external check.** [N-012](#n-012) is the only entry here scored against a ground truth this project did not produce: 5,700 MMLU items annotated by hand at Edinburgh. Against the one error type a data-at-rest check can reach, the battery scores precision 25% and **recall 5%**, up from 14% and 3% before this measurement was used to fix it. It also found two double-keyed items the annotators marked `ok` ([F-018](#f-018)). Both directions are the finding; neither on its own is.

**Thirteen benchmarks audited**, all fetched from their authors and none
vendored: MMLU, MMLU-Pro, HellaSwag, ARC-Easy, ARC-Challenge, GSM8K,
TruthfulQA, CommonsenseQA, OpenBookQA, BoolQ, WinoGrande, SciQ, MedMCQA.

Count it precisely.

| | |
|---|---|
| findings in other people's evals (**F**) | **18** |
| &nbsp;&nbsp;of which receipt-backed dataset defects | 10 (F-001 to F-004, F-008 to F-013) |
| &nbsp;&nbsp;of which findings about a judge, model or agent | 4 (F-014 to F-017) |
| &nbsp;&nbsp;of which findings about running one | 3 (F-005, F-006, F-007) |
| negative results, recorded rather than dropped (**N**) | **13** |
| defects in dinostomp itself (**D**) | **32** |

Thirty-two to eighteen. That ratio is the useful number to publish, and it is the
one to expect from any validator meeting data it did not author. The reason to
run it anyway is the direction every self-defect took: three made **gating**
checks fire on correct data, one fabricated a blind accuracy, two were about to
call sampling noise a finding, one let this repository publish a clean bill of
health over runs from two different engines, two were caught only when the tool
ran somewhere its author's assumptions did not hold, and one
([D-014](#d-014)) was a bug the project had already found and fixed elsewhere,
written again three releases later in a different check.

The most common shape across all twenty is worth stating once: **a check that
compared the wrong thing and returned a confident answer about it.**

## Adding an entry

Findings from outside are wanted, and they are the highest-value thing anyone can
contribute. See [CONTRIBUTING.md](CONTRIBUTING.md#break-it-please): build a
pathological pod from the schemas **without reading the check implementations**,
and open an issue with it.

An entry needs an id in the right series, a subject, the check that produced it
(or the check that *should* have and did not), a date, a status, and a receipt
someone else can re-derive. Misses get an entry here next to the tool's own
defects, with attribution, rather than being quietly patched.
