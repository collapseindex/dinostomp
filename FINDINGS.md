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
| [N-001](#n-001) | HellaSwag, ARC, MMLU | no position, length, or shortcut bias found | negative |
| [N-002](#n-002) | dinostomp | the uncheckable path was untested, and said so | negative, later closed |
| [N-003](#n-003) | ARC, OpenBookQA, HellaSwag, WinoGrande | no repeated options in four datasets | negative |
| [N-004](#n-004) | six dataset pairs | no cross-benchmark reuse found | negative |
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

---

## Findings in other people's evals

### F-001
**iris · two byte-identical measurement vectors**
`dup-questions` (S1) · 2026-07 · confirmed

The battery's first contact with real data was the most famous dataset in
statistics. Transcript re-run under the current 54-check battery; the original
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
MECHANICALLY SOUND: no integrity findings, full coverage (29 of 29 ran; 25 n/a of 54 declared)
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

---

## Negative results

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

---

## Defects in dinostomp itself

Every one of these was in the flattering direction. That is not a coincidence
worth being proud of, it is the direction bugs in a validator take by default:
a check that fires too little looks like a clean bill, and nobody investigates a
clean bill.

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

---

## The honest scorecard

**Thirteen benchmarks audited**, all fetched from their authors and none
vendored: MMLU, MMLU-Pro, HellaSwag, ARC-Easy, ARC-Challenge, GSM8K,
TruthfulQA, CommonsenseQA, OpenBookQA, BoolQ, WinoGrande, SciQ, MedMCQA.

Count it precisely.

| | |
|---|---|
| findings in other people's evals (**F**) | **13** |
| &nbsp;&nbsp;of which receipt-backed dataset defects | 10 (F-001 to F-004, F-008 to F-013) |
| &nbsp;&nbsp;of which findings about running one | 3 (F-005, F-006, F-007) |
| negative results, recorded rather than dropped (**N**) | **4** |
| defects in dinostomp itself (**D**) | **16** |

Sixteen to thirteen. That ratio is the useful number to publish, and it is the
one to expect from any validator meeting data it did not author. The reason to
run it anyway is the direction every self-defect took: three made **gating**
checks fire on correct data, one fabricated a blind accuracy, two were about to
call sampling noise a finding, one let this repository publish a clean bill of
health over runs from two different engines, two were caught only when the tool
ran somewhere its author's assumptions did not hold, and one
([D-014](#d-014)) was a bug the project had already found and fixed elsewhere,
written again three releases later in a different check.

The most common shape across all sixteen is worth stating once: **a check that
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
