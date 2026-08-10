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

**Machine-readable**: [`findings.json`](findings.json) carries every entry with
its id, checks, date, status and subject, generated from this file. The index
and cross-reference tables below are generated too, by
`python scripts/index_findings.py`; the prose entries are the source of truth
and are written by hand. Two hand-kept copies drifted twice, so the derivable
half is now derived and CI fails if it goes stale.

**Reproducing anything here** needs no API key and no spend unless the entry says
otherwise:

```bash
python benchmarks/fetch.py                    # downloads the datasets, prints their SHA-256
dinostomp stomp benchmarks/<name>/eval.yaml   # re-derives the finding
```

## Index

<!-- INDEX:BEGIN -->

| id | subject | finding | status |
|---|---|---|---|
| [F-001](#f-001) | iris | two byte-identical measurement vectors | confirmed |
| [F-002](#f-002) | MMLU | a subtraction item keyed to two correct options | confirmed |
| [F-003](#f-003) | MMLU | 90 duplicate rows in the first 3000 | confirmed |
| [F-004](#f-004) | TruthfulQA | an item passable by restating the question | confirmed, scoped |
| [F-005](#f-005) | GSM8K | two of four models move beyond sampling noise on seed alone | confirmed costs $0.06 to reproduce |
| [F-006](#f-006) | GSM8K | unfinished responses credited as correct | confirmed |
| [F-007](#f-007) | GSM8K | a formatting gap that reads as a capability gap | confirmed |
| [F-008](#f-008) | CommonsenseQA | 24 items with a repeated option; 6 repeat the keyed answer | confirmed |
| [F-009](#f-009) | MedMCQA | 16 items with a repeated option, 4 of them the answer | confirmed |
| [F-010](#f-010) | SciQ | 9 items with a repeated option | confirmed |
| [F-011](#f-011) | MMLU-Pro | 64 duplicate rows in the first 3000 | confirmed |
| [F-012](#f-012) | MMLU-Pro vs MMLU | 158 of 3000 items reuse an MMLU question; 22 are unchanged | confirmed, expected |
| [F-013](#f-013) | SciQ | the gold option reuses a question word no distractor does | confirmed, narrow |
| [F-014](#f-014) | a judge (qwen3-30b) | stated confidence and authority flip its verdicts, always toward FAIL | confirmed [examples/hedge](examples/hedge/) |
| [F-015](#f-015) | four small models | 87% to 97% preserve a source's hedge; the eval cannot separate them | confirmed, underpowered costs $0.02 to reproduce |
| [F-016](#f-016) | llama-3.2-3b | "You are an expert." is worth 10 points, marginally | confirmed, marginal [examples/presentation](examples/presentation/) |
| [F-017](#f-017) | a RAG agent | grounding it in its own retrieval made it 25 points WORSE | confirmed [examples/live-agent](examples/live-agent/) costs $0.02 |
| [F-018](#f-018) | MMLU-Redux 2.0 | two verbatim double-keyed items the human annotators marked `ok` | confirmed |
| [F-019](#f-019) | LogiQA | 8 items with a duplicated option; 3 offer the same option four times | confirmed |
| [F-020](#f-020) | DROP | 86 duplicated questions, 37 keyed to different accepted answers | confirmed |
| [F-021](#f-021) | MATH-500 | 2 problems whose answer is written in the question | confirmed, scoped |
| [F-022](#f-022) | RACE | an item offering the same option twice | confirmed |
| [F-023](#f-023) | AQuA-RAT | 7 items with a duplicated option, most of them double-keyed | confirmed |
| [F-024](#f-024) | Iranian driving test | the answer is the longest option 45% of the time | confirmed |
| [N-015](#n-015) | MedQA-USMLE | a licensing exam passed every applicable check | negative |
| [N-001](#n-001) | HellaSwag, ARC, MMLU | no position, length, or shortcut bias found | negative |
| [N-002](#n-002) | dinostomp | the uncheckable path was untested, and said so | later closed by [F-007](#f-007) |
| [N-003](#n-003) | ARC, OpenBookQA, HellaSwag, WinoGrande | no repeated options in four datasets | negative |
| [N-004](#n-004) | six dataset pairs | no cross-benchmark reuse found | negative |
| [N-005](#n-005) | four models | re-ordering the options moved nobody beyond noise | negative, underpowered |
| [N-006](#n-006) | four models | probe demonstrably sensitive, and no canary reproduced | negative |
| [N-007](#n-007) | lm-eval-harness log | both reported metrics re-derive from the raw log-probs | negative |
| [N-008](#n-008) | dinostomp | an even `run.repeats` reported p-squared, not p | measured, fixed |
| [N-009](#n-009) | dinostomp | T4 sees 0%, T7 sees 100%, on the same agent | measured |
| [N-010](#n-010) | dinostomp | what a process boundary buys, one claim at a time | measured |
| [N-011](#n-011) | Inspect AI | the second foreign format cost one defect, not five | measured |
| [N-012](#n-012) | dinostomp | scored against humans: 5% recall, and 2 items they missed | measured |
| [N-013](#n-013) | LLM-as-judge | capability buys precision and costs recall; first version retracted | measured **supersedes this entry's first version, which was wrong** |
| [N-014](#n-014) | dinostomp | nine adversarial pods, nine caught, one check found blind | measured |
| [F-025](#f-025) | Pharmacist Licensure Exam | 16 items offer the same option twice | confirmed |
| [N-016](#n-016) | NCLEX nursing | clean, on 28 items; the battery cannot read the other 58 | negative, underpowered |
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
| [D-011](#d-011) | dinostomp | published reports only verified on the author's machine | fixed found by CI |
| [D-012](#d-012) | dinostomp | line-ending translation is drift | fixed found by CI |
| [D-013](#d-013) | dinostomp | smaller ones: a wrong hint, two wrong witnesses, a near-miss | fixed |
| [D-014](#d-014) | dinostomp | the overlap check compared questions and ignored options | fixed |
| [D-015](#d-015) | dinostomp | position and length bias reported class balance on a fixed label set | fixed |
| [D-016](#d-016) | dinostomp | the SciQ fetcher put the answer at index 0 on every item | fixed |
| [D-017](#d-017) | dinostomp | a truncated judge was diagnosed as a judge with no opinion | fixed |
| [D-018](#d-018) | dinostomp | EVERY non-judge probe crashed the CLI, not just cross-judge | fixed |
| [D-019](#d-019) | dinostomp | the docs claimed a 28-point swing with no run behind it | **WITHDRAWN** |
| [D-020](#d-020) | dinostomp | the grounding check undercounts by 6x, by construction | scoped, not fixed |
| [D-021](#d-021) | dinostomp | the most common eval-log shape in the field was unimportable | fixed in v0.40.0 |
| [D-022](#d-022) | dinostomp | a check overwrote the contract's skip reason with a false one | fixed in v0.40.0 |
| [D-023](#d-023) | dinostomp | a rival score column was chosen silently, and it was the wrong one | fixed in v0.40.0 |
| [D-024](#d-024) | dinostomp | `run --dry` would fabricate records for a model it cannot call | fixed in v0.40.0 |
| [D-025](#d-025) | dinostomp | an error message named a flag nobody can type | fixed in v0.40.0 |
| [D-026](#d-026) | dinostomp | the item-majority estimator was never run live until now | fixed in v0.41.0 |
| [D-027](#d-027) | dinostomp | two defects in the pod written to demonstrate the new rail | fixed in v0.42.0 |
| [D-028](#d-028) | dinostomp | the line-ending guard could not see a file until after it shipped | fixed in v0.42.1 |
| [D-029](#d-029) | dinostomp | "policy is enforced at call time" held only for agents that asked | corrected in v0.43.0 |
| [D-030](#d-030) | dinostomp | `inspect` called a pod codeless while it shipped an agent and tools | fixed in v0.43.1 |
| [D-031](#d-031) | dinostomp | an imported trajectory could never reach the checks that read one | fixed in v0.44.0 |
| [D-032](#d-032) | dinostomp | a valid JSONL file it refused to read, blaming the data | fixed in v0.45.0 |
| [D-033](#d-033) | dinostomp | D-017 again, in the harness written by the person who wrote D-017 | fixed |
| [D-034](#d-034) | dinostomp | a loader that discarded 96% of a split, and the findings computed on the rest | fixed |
| [D-035](#d-035) | dinostomp | refused a valid file for a byte-order mark, naming the fix it did not apply | fixed in v0.48.0 |
| [D-036](#d-036) | dinostomp | told a semicolon-CSV user their columns were badly named | fixed in v0.48.0 |
| [D-037](#d-037) | dinostomp | the leak check was blind to every numeric-answer dataset | fixed in v0.49.0 |
| [D-038](#d-038) | dinostomp | announced a `choices` mapping it then silently ignored | fixed in v0.49.1 |
| [D-039](#d-039) | dinostomp | A loader that mis-keyed a whole exam by one, then reported the artifact as a finding | fixed in v0.50.0 |
| [D-040](#d-040) | dinostomp | the findings feed was published for two releases with no schema | fixed in v0.52.0 |
| [D-041](#d-041) | dinostomp | a numeric scorer default scored a live model 0.000 against a real 0.438, uncited for six releases | scoped, not fixed |
| [D-042](#d-042) | dinostomp | the bare-file path dropped `input_ref`, reporting ten distinct photographs as one duplicate | fixed in v0.53.0 |
| [D-043](#d-043) | dinostomp | S15's false-positive class: images sharing one gradient direction all hash alike | scoped, documented, not fixed |
| [N-017](#n-017) | CIFAR-10 / ciFAIR | 28% recall against a human duplicate annotation; byte-level checks get 0% | measured |
| [D-044](#d-044) | dinostomp | the asset-path guard asked the local OS what absolute means, and got two answers | fixed in v0.53.1 |
| [D-045](#d-045) | dinocorpus | the corpus's first scored run found three defects in the corpus | fixed in v0.55.0 |
| [D-046](#d-046) | dinostomp | S3 warns on 1 clean dataset in 6 at the size its own rule admits | measured, scoped, not retuned |
| [D-047](#d-047) | dinocorpus | the withheld split was public arithmetic, and fixing it silently rewrote the public split | fixed in v0.56.0 |

<!-- INDEX:END -->

<!-- Generated by `python scripts/index_findings.py`. FINDINGS.md is the source of
     truth: the prose entries are written by hand and everything derivable from them
     is generated, because two hand-kept copies drifted twice. -->

## Cross-reference

<!-- XREF:BEGIN -->

### By check

Every finding a given check has produced. This is the view to read BEFORE changing
a check: it is that check's own track record, including the times it was the thing
at fault.

| check | findings |
|---|---|
| `J1` | [D-017](#d-017) |
| `J2` | [F-014](#f-014) |
| `P2` | [D-003](#d-003), [D-008](#d-008) |
| `P9` | [N-005](#n-005), [D-007](#d-007) |
| `P10` | [F-005](#f-005), [D-007](#d-007) |
| `P11` | [F-016](#f-016) |
| `R1` | [D-012](#d-012) |
| `R3` | [D-001](#d-001) |
| `R5` | [F-006](#f-006) |
| `R6` | [F-007](#f-007) |
| `R7` | [D-002](#d-002) |
| `R8` | [N-007](#n-007) |
| `R13` | [D-006](#d-006) |
| `R15` | [D-006](#d-006) |
| `R16` | [D-022](#d-022), [D-041](#d-041) |
| `R20` | [N-008](#n-008) |
| `S1` | [F-001](#f-001), [F-003](#f-003), [F-011](#f-011), [F-020](#f-020), [D-005](#d-005), [D-027](#d-027), [D-042](#d-042) |
| `S2` | [F-004](#f-004), [F-021](#f-021), [D-004](#d-004), [D-037](#d-037) |
| `S3` | [N-001](#n-001), [D-015](#d-015), [D-016](#d-016), [D-046](#d-046) |
| `S4` | [F-024](#f-024), [N-001](#n-001), [D-015](#d-015) |
| `S5` | [F-002](#f-002), [F-008](#f-008), [F-009](#f-009), [F-010](#f-010), [F-018](#f-018), [F-019](#f-019), [F-022](#f-022), [F-023](#f-023), [N-003](#n-003), [N-012](#n-012), [F-025](#f-025) |
| `S7` | [F-020](#f-020), [D-005](#d-005), [D-042](#d-042) |
| `S9` | [F-013](#f-013), [N-001](#n-001), [D-015](#d-015) |
| `S10` | [N-006](#n-006) |
| `S11` | [F-012](#f-012), [N-004](#n-004), [D-014](#d-014) |
| `S12` | [D-044](#d-044) |
| `S15` | [D-043](#d-043), [N-017](#n-017) |
| `T1` | [D-027](#d-027) |
| `T4` | [N-009](#n-009), [D-020](#d-020) |
| `T7` | [N-009](#n-009) |
| `T8` | [D-031](#d-031) |
| `(no check id)` | [F-015](#f-015), [F-017](#f-017), [N-015](#n-015), [N-002](#n-002), [N-010](#n-010), [N-011](#n-011), [N-013](#n-013), [N-014](#n-014), [N-016](#n-016), [D-009](#d-009), [D-010](#d-010), [D-011](#d-011), [D-013](#d-013), [D-018](#d-018), [D-019](#d-019), [D-021](#d-021), [D-023](#d-023), [D-024](#d-024), [D-025](#d-025), [D-026](#d-026), [D-028](#d-028), [D-029](#d-029), [D-030](#d-030), [D-032](#d-032), [D-033](#d-033), [D-034](#d-034), [D-035](#d-035), [D-036](#d-036), [D-038](#d-038), [D-039](#d-039), [D-040](#d-040), [D-045](#d-045), [D-047](#d-047) |

### By subject

| subject | findings |
|---|---|
| dinostomp | [N-002](#n-002), [N-008](#n-008), [N-009](#n-009), [N-010](#n-010), [N-012](#n-012), [N-014](#n-014), [D-001](#d-001), [D-002](#d-002), [D-003](#d-003), [D-004](#d-004), [D-005](#d-005), [D-006](#d-006), [D-007](#d-007), [D-008](#d-008), [D-009](#d-009), [D-010](#d-010), [D-011](#d-011), [D-012](#d-012), [D-013](#d-013), [D-014](#d-014), [D-015](#d-015), [D-016](#d-016), [D-017](#d-017), [D-018](#d-018), [D-019](#d-019), [D-020](#d-020), [D-021](#d-021), [D-022](#d-022), [D-023](#d-023), [D-024](#d-024), [D-025](#d-025), [D-026](#d-026), [D-027](#d-027), [D-028](#d-028), [D-029](#d-029), [D-030](#d-030), [D-031](#d-031), [D-032](#d-032), [D-033](#d-033), [D-034](#d-034), [D-035](#d-035), [D-036](#d-036), [D-037](#d-037), [D-038](#d-038), [D-039](#d-039), [D-040](#d-040), [D-041](#d-041), [D-042](#d-042), [D-043](#d-043), [D-044](#d-044), [D-046](#d-046) |
| GSM8K | [F-005](#f-005), [F-006](#f-006), [F-007](#f-007) |
| dinocorpus | [D-045](#d-045), [D-047](#d-047) |
| four models | [N-005](#n-005), [N-006](#n-006) |
| MMLU | [F-002](#f-002), [F-003](#f-003) |
| SciQ | [F-010](#f-010), [F-013](#f-013) |
| a judge (qwen3-30b) | [F-014](#f-014) |
| a RAG agent | [F-017](#f-017) |
| AQuA-RAT | [F-023](#f-023) |
| ARC, OpenBookQA, HellaSwag, WinoGrande | [N-003](#n-003) |
| CIFAR-10 / ciFAIR | [N-017](#n-017) |
| CommonsenseQA | [F-008](#f-008) |
| DROP | [F-020](#f-020) |
| four small models | [F-015](#f-015) |
| HellaSwag, ARC, MMLU | [N-001](#n-001) |
| Inspect AI | [N-011](#n-011) |
| Iranian driving test | [F-024](#f-024) |
| iris | [F-001](#f-001) |
| llama-3.2-3b | [F-016](#f-016) |
| LLM-as-judge | [N-013](#n-013) |
| lm-eval-harness log | [N-007](#n-007) |
| LogiQA | [F-019](#f-019) |
| MATH-500 | [F-021](#f-021) |
| MedMCQA | [F-009](#f-009) |
| MedQA-USMLE | [N-015](#n-015) |
| MMLU-Pro | [F-011](#f-011) |
| MMLU-Pro vs MMLU | [F-012](#f-012) |
| MMLU-Redux 2.0 | [F-018](#f-018) |
| NCLEX nursing | [N-016](#n-016) |
| Pharmacist Licensure Exam | [F-025](#f-025) |
| RACE | [F-022](#f-022) |
| six dataset pairs | [N-004](#n-004) |
| TruthfulQA | [F-004](#f-004) |

<!-- XREF:END -->

---

## Findings in other people's evals

### F-001
**iris · two byte-identical measurement vectors**
`dup-questions` (S1) · 2026-07 · confirmed

The battery's first contact with real data was the most famous dataset in
statistics. Transcript re-run under the current 61-check battery; the original
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
MECHANICALLY SOUND: no integrity findings, full coverage (29 of 29 ran; 32 n/a of 61 declared)
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

### F-019
**LogiQA · 8 items with a duplicated option, and 3 offer the same option four times**
`dup-options` (S5) · 2026-08-09 · confirmed

`lucasmccabe/logiqa`, test split, 650 items fetched. Eight carry a duplicated
option. Three of them are worse than a duplicate:

```
lq-00246   options: ['.', '.', '.', '.']     target: '.'
lq-00285   options: ['.', '.', '.', '.']     target: '.'
lq-00598   options: ['.', '.', '.', '.']     target: '.'
```

All four options are a single full stop. There is no answerable question there,
and any model scores 25% by construction while the item contributes nothing.

Five more have the KEYED ANSWER duplicated, which is multiple-correct-answers by
construction:

```
lq-00090   ['No guest invited.', 'guest.', 'guests.', 'guests.']       key 'guests.'
lq-00489   ['unconfirmed.', 'people.', 'people.', 'people.']           key 'people.'
lq-00643   ['kinds.', 'types.', 'types.', 'types.']                    key 'types.'
```

The pattern is option text truncated to its last word or its final punctuation.
The CONTEXT of those items is intact (`lq-00246` carries 526 characters of
premises), so this is not a transport truncation on the way in; the options
column of this copy is damaged.

**A correction I had to make mid-analysis.** A first pass counted "items with an
option shorter than 3 characters" and reported 3.5%. That was wrong: `['E.',
'G.', 'I.', 'K.']` is a perfectly good option set when the puzzle names patients
E through K, and this dataset is full of those. The finding is the DUPLICATION,
which is 8 items, not the shortness.

---

### F-020
**DROP · 86 duplicated questions, 37 of them keyed to different accepted answers**
`dup-questions` (S1), `conflicting-keys` (S7) · 2026-08-09 · confirmed

`ucinlp/drop`, validation split, first 2000 items. 86 passage+question pairs
appear more than once, and 37 of those pairs carry DIFFERENT accepted-answer
sets, so the same question is graded against different keys depending on which
copy a sampler happens to draw:

```
drop-00267  "How many yards was the longest field goal?"   accepted: ['26', '26-yard']
drop-00268  (same passage, same question)                  accepted: '26'
```

Not a contradiction about the world, an inconsistency in annotation: one copy
accepts two phrasings and the other accepts one. A model answering `26-yard`
is correct on one copy and wrong on the other.

**S7 is stricter than the naive check, in the right direction.** An ad-hoc pass
written to verify this reported 38, because it compared target lists as ordered
sequences and counted `['2','3']` against `['3','2']` as a conflict. S7 sorts
targets before comparing, so it does not. The tool was more careful than the
check written to audit it, which is the second time in one session.

---

### F-021
**MATH-500 · two problems whose answer is written in the question**
`answer-leak` (S2) · 2026-08-09 · confirmed, scoped

The first FREE-FORM dataset audited here, and the first to reach the answer-leak
path at all: thirteen multiple-choice benchmarks never did.

```
m500-00277  "What is $\sqrt{53}$ in simplest radical form?"        answer: \sqrt{53}
m500-00373  "...he accidentally missed the minus sign, finding
             $\frac{3+4i}{1+2i}=...$  What answer should he have..."   answer: 1+2i
```

**Scoped, because the first is arguably fine.** `\sqrt{53}` in simplest radical
form IS `\sqrt{53}`; the question is a genuine test of recognising that, and the
answer appearing in it is unavoidable. The second is the real one: `1+2i` is the
denominator the problem hands you, so a model that echoes a fragment of the
prompt scores correct without doing the division.

**The check was more careful than my verification, again.** A naive substring
pass over the same 500 items flagged 75, because `'9'` occurs inside `'196'`.
S2 requires a whole-token mention, exempts negated mentions, and weighs how many
other answer-space values are present, which is why it reports 2 and one of the
two is still worth arguing about.

---

### F-022
**RACE · an item offering the same option twice**
`dup-options` (S5) · 2026-08-09 · confirmed

`ehovy/race`, high-school test split, 1500 items fetched, one flagged:

```
race-01213  ["He didn't say he was sorry.",
             "He pushed her away when she tried to take his arm.",
             "He didn't say he was sorry.",          <- the same option again
             "He wouldn't let her touch him."]       <- the key
```

The key is not the duplicated option, so this is not a double-correct item. It
is a four-option question that offers three, which changes the guessing floor
for that item from 25% to 33% and is invisible in any accuracy number.

One item in 1500 is a low rate, and it is reported for the same reason the
others are: it costs nothing to find and nobody was looking.

---

### F-023
**AQuA-RAT · 7 items offer a duplicated option, and most of them are double-keyed**
`dup-options` (S5) · 2026-08-10 · confirmed

AQuA-RAT is a quantitative reasoning set in the style of graduate admissions
tests. Seven of 254 test items offer the same option twice, and the duplicate is
usually the KEY, verified against the source rows rather than the repackaging:

```
aqua-00117  ['A)8.75', 'B)8.79', 'C)8.75', 'D)8.71', 'E)8.72']      key C  -> A and C identical
aqua-00124  ['A)15 kmph', 'B)6 kmph', ..., 'E)6 kmph']              key E  -> B and E identical
aqua-00126  ['A)69:91', 'B)59:91', 'C)59:90', 'D)59:91', ...]       key B  -> B and D identical
aqua-00120  ['A)277', 'B)288', 'C)200', 'D)277', 'E)168']           key E  -> A and D identical
```

On the first three, a model that computes the right number and picks the OTHER
option holding it is marked wrong for choosing a correct answer. On the fourth
the key is unaffected, so it is a five-option item offering four.

**Checked against the source, because the loader was a suspect.** This pod strips
the `"A)"` label so the target is the answer and not its letter, and a stripping
bug could manufacture duplicates. The rows above are quoted from
`deepmind/aqua_rat` before any processing.

---

### F-024
**Iranian driving licence test · the correct answer is the longest option 45% of the time**
`length-bias` (S4) · 2026-08-10 · confirmed

126 items, four options each, so the gold answer should be the longest roughly
25% of the time. It is the longest in **57 of 126, 45%**, which is +11% over the
per-item expectation after accounting for ties.

This is the oldest tell in multiple-choice writing: the correct option carries
the qualifications and the exceptions, so it grows. It means a candidate who
knows no road law can beat chance by picking the longest answer.

**The first non-English item set audited here**, and a reminder of what the
battery does and does not need: length is measured in characters and required no
comprehension of Persian.

**Scope.** This audits one redistributed copy of the question bank, not the
examination as administered, and 126 items is a small sample: the finding is
about this artifact. It is included because a statutory road-safety test is the
kind of assessment nobody thinks to lint.

---

### N-015
**MedQA-USMLE · a professionally written licensing exam passed every applicable check**
the data-scope battery · 2026-08-10 · negative

1,273 USMLE-style items, four options each, from the exam family that decides
who practises medicine in the United States.

```
MECHANICALLY SOUND AT DATA SCOPE: no integrity findings across 7 of 10 data checks
```

No duplicate questions, no duplicated options, no target missing from its own
option list, no conflicting keys, no answer leakage, no position bias, no length
bias. Of the eighteen ML benchmarks audited here, several fail at least one of
those.

**What this is NOT evidence for.** It is one dataset, and a clean result on 7 of
10 checks is not a clean result on 10. It cannot support "professional item
writing is better than ML benchmark construction" as a general claim: the
comparison is uncontrolled, the sets differ in size, subject and age, and the
three checks that did not run are not free passes. Two of the human exams
audited in the same batch did produce findings ([F-023](#f-023),
[F-024](#f-024)), which is the strongest argument against reading this as a
verdict on human-written exams.

What it does establish is narrower and still worth having: **the battery's
findings are not an artifact of pointing it at anything.** A dataset can pass.
That matters because a linter which flags something in every corpus it meets is
measuring its own thresholds, and until now nothing large had come back clean.

---

### N-001
**HellaSwag, ARC, MMLU · no position, length, or shortcut bias found**
`position-bias` (S3), `length-bias` (S4), `surface-shortcut` (S9) · 2026-08-09 · negative

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
`dup-options` (S5) · 2026-08-09 · negative

Zero items with a repeated option across 2376 + 1172 + 500 + 10042 + 1267 items.
Recorded because [F-008](#f-008) to [F-010](#f-010) make repeated options look
endemic and they are not: five of the nine choice datasets audited here are
clean on this axis.

### N-004
**Six dataset pairs · no cross-benchmark reuse found**
`corpus-overlap` (S11) · 2026-08-09 · negative

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
**Capability buys PRECISION and costs RECALL. No judge tested is both.**
`semdup` extension · 2026-08-09 · measured · **supersedes this entry's first version, which was wrong**

[N-012](#n-012) measured where a byte comparison runs out: of 39 items humans
label `multiple_correct_answers`, the deterministic check reaches 2. The other
37 are semantic, so the obvious move is to ask a model. This is what asking
costs, on 39 human-confirmed positives and 250 human-labelled `ok` items sampled
at seed 7.

| judge | recall | precision | FPR on clean items | false flags per 3,000 |
|---|---|---|---|---|
| llama-3.1-8b | **97%** | 13% | 80.8% | ~2,420 |
| qwen3-30b | 33% | 42% | 6.0% | ~180 |
| claude-opus-4.8 | 10% | **60%** | **0.8%** | **~24** |

**Precision rises monotonically with capability and recall collapses.** The
small model says yes to almost everything: 97% recall, and 2,400 false flags to
find them. The frontier model is the mirror image: it almost never false-alarms,
and it almost never fires. Neither is a usable dataset check on its own, and the
failure mode is opposite at each end.

**WHAT THIS ENTRY GOT WRONG THE FIRST TIME, and it was the headline.** The first
version reported precision of 14%, 18%, 18% across three configurations and
concluded:

> Changing the prompt and the model tier slides recall and the false-positive
> rate along one curve without improving the DISCRIMINATION, which is the
> signature of a task limit rather than a prompt limit.

That claim is **retracted**. Precision moves from 13% to 60%, which is a large
capability effect, and the flatness that produced the conclusion was
substantially an artifact of the harness (see [D-033](#d-033)): a 40-token cap
truncated every model that reasons before answering, and the truncations were
counted as "no opinion". The structural story about confusable distractors is
still a reasonable account of why precision is 60% rather than 95%. It is no
longer an account of why the approach fails, because at the frontier it does not
fail in the way the entry claimed.

**Is it shippable now?** At 60% precision and 24 false flags per 3,000 items,
the frontier configuration is a defensible ADVISORY check: the reading cost is
tolerable and every flag it raised was worth looking at. Two caveats keep it
marked not-recommended by default. It caught 3 of the 29 positives it managed to
judge, so it is nearly blind, and 3 is a number with enormous error bars. And it
cost $1.42 to judge 289 items, which is roughly $15 per 3,000-item benchmark, to
surface a handful of items.

**One of its two false alarms is not one.** `high_school_physics-02754` offers
`['0.16 N', '0.16 N', '0.32 N', '0.36 N']`. Redux labels it `ok`; the option is
duplicated verbatim and the core's own S5 flags it. Counting it against the
judge is scoring it against an annotation error, which is the same asymmetry
[F-018](#f-018) records in the other direction.

**Scope.** One dataset, one task, three judges, 289 items, and the frontier row
rests on 3 true positives out of 29 judgeable ones. It is enough to say the
capability/recall trade exists and nowhere near enough to put a number on where
it crosses. Reproduce with `SEMDUP_JUDGE=<model> python extensions/semdup/validate.py`.

Total spend across every version of this experiment: about $1.50.

---

### N-014
**Nine adversarial pods, nine caught, and one check found blind**
`trials`, by hand · 2026-08-10 · measured

`CONTRIBUTING.md` asks outsiders to build a pathological pod and report what it
breaks. Nobody has, so this is the author doing it from the SPEC side: pods
written by someone who wants a green badge and is willing to be creative.

| attack | outcome |
|---|---|
| a scorer that returns `pass` unconditionally | refused, witness gate |
| witnesses that only ever assert `pass` | refused, gate cannot close |
| a 99% accuracy claim on 24 dry items | `BROKEN`, claim-evidence |
| one item repeated 24 times | `BROKEN`, duplicate questions |
| a claim naming a model that never ran | refused at load |
| a superiority claim of a model over itself | refused at load |
| every target identical (`yes` on all 24) | caught: "no better than guessing, chance ~100%" |
| no canary in the data | caught, warned |
| **the answer written into every question** | **MISSED** ([D-037](#d-037)) |

**None obtained a clean verdict**, which is the result that matters: nine pods
built to cheat, nine refused or gated or warned. Four were refused before
anything ran, which is the cheapest place to catch a bad pod.

The ninth is the finding. It came back `INCOMPLETE` with **no failures at all**
while every one of its 24 items disclosed its own answer, because S2 exempts
numeric targets wholesale. The pod was not cleared, it was simply not caught for
the reason it was built.

**Two things worth separating.** A tool that refuses a cheating pod is doing its
job. A tool that refuses a cheating pod *for the wrong reason* is getting lucky,
and the difference only shows up when someone writes the pod on purpose. This is
the first time anyone has.

Reproduce: `extensions`-free, offline, nine pods, about ninety seconds.

---

### F-025
**2023 Chinese Pharmacist Licensure Examination · 16 items offer the same option twice**
`dup-options` (S5) · 2026-08-10 · confirmed

431 single-key items from the pharmacy track of a national professional
licensing examination. Eighteen offer a duplicated option, and the two causes
separate cleanly:

**16 are duplicated option TEXT**, in items with no images involved:

```
pharm-00223  ['卡维地洛片', '卡维地洛片', '赖诺普利片', ...]        carvedilol tablets, twice
pharm-00330  ['美托洛尔片', '格列吡嗪片', '赖诺普利片', '格列吡嗪片', ...]   glipizide tablets, twice
pharm-00107  ['口崩片', '咀嚼片', '多层片', '肠溶片', '多层片']       multi-layer tablet, twice
```

**2 are a transcription artifact**: the source replaced each formula image with
the literal string `img`, so two distinct mathematical options both became
`'img'`. Those two items are unusable in this copy and say nothing about the
examination.

**None of the eighteen has the KEY duplicated**, which is the honest limit of
this finding: no candidate is marked wrong for choosing a correct answer. The
effect is smaller and still real. A five-option item that offers four raises the
guessing floor for that item from 20% to 25%, and a candidate who spots the
repeat can eliminate a slot for free.

**Scope, and it is doing real work here.** This audits one redistributed copy,
and the `img` cases prove the copy is lossy. A duplicate could in principle be
the same lossiness in a form I cannot detect. What can be said is that sixteen
of them are ordinary drug names and patient descriptions with no image content
anywhere in the item, so a transcription explanation would have to be a
different and stranger one.

---

### N-016
**NCLEX-style nursing items · clean, on a sample too small to lean on**
the data-scope battery · 2026-08-10 · negative, underpowered

```
MECHANICALLY SOUND AT DATA SCOPE: no integrity findings across 7 of 10 data checks
```

The second human licensing exam to come back clean, after
[N-015](#n-015). Recorded with its limit in the title because the limit is
severe: **28 items**. That is a sample where the absence of a defect at any of
the rates found elsewhere in this file would be unsurprising by chance alone.

The 28 are what survives of 86 rows, and the arithmetic is not a filter bug:

```
33  the key is a LIST, not one option   ("Select All That Apply")
25  fewer than two options              (fill-in-the-blank, hot spot, matrix, ...)
28  single-key multiple choice          -> kept
```

The bank carries ten item types and only one is the shape this pod scores. A
`Select All That Apply` key COULD be stored as a list target, since the items
schema allows one, and it must not be: a list target means "any of these is
acceptable" and SATA means "all of these are required". Conflating them would
invent a grading rule the examination does not use, which is the same error as
[D-039](#d-039) in a different costume.

**What the ten item types say about the battery, which is more interesting than
the clean bill.** Most of a modern nursing licensure exam is not four options and
one key. It is highlighting, ordering, grids, bow-ties and exhibits. Every
check here reads a question, options and a target, so **the battery has nothing
to say about 58 of these 86 items** and did not pretend otherwise. That is the
honest ceiling on auditing assessments this way, and it is a bigger caveat than
any number in this entry.

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

### D-033
**D-017 again, in the validation harness, written by the person who wrote D-017**
`extensions/semdup/validate.py` · 2026-08-09 · fixed

[D-017](#d-017) was a judge scoring 50% agreement because a 200-token cap ate
its verdict before it could state one. It is written up in this file, two days
old at the time, with the lesson in its own title.

The validation harness for [N-013](#n-013) capped the judge at **40 tokens** and
parsed the FIRST line of the reply. Claude Opus reasons before answering, so it
was cut off mid-sentence on 24 of 289 items:

```
'Options A and B both describe charges flowing in one direction. Option A adds
 "steadily," but the core assertion is the same-charges'          <- truncated
```

That is a correct DUPLICATE verdict on `conceptual_physics-01237`, a known
positive, counted as "no opinion". The reported recall of 11% was an artifact of
the cap. Worse, the artifact was one-sided by construction: it penalised exactly
the models that reason, which are the ones the experiment existed to test, and
it produced the flat precision curve that the first version of N-013 built its
headline on.

Fixed three ways rather than one, because a cap is not the only thing that can
eat a verdict: the reply must end with a tagged `VERDICT:` line, the parser
reads the LAST such line so reasoning before it is fine, and the cap is 300. A
genuinely truncated reply still returns `None` and is counted as unparseable
rather than guessed at, which is why the corrected table still reports 13 to 42
unparseable replies per judge instead of hiding them.

The lesson is not "raise the cap". It is that a known defect, documented in this
repository, with a title that names it, was reproduced two days later by its own
author in a harness built to measure something else. A finding written down is
not a finding internalised, and the only thing that caught it was reading the
raw replies before trusting the numbers.

---

### D-034
**A loader that discarded 96% of a split, and the findings computed on what was left**
`benchmarks/fetch.py` · 2026-08-09 · fixed

The DROP builder kept only items whose answer was a SINGLE span. DROP's spans are
alternative acceptable phrasings from different annotators, not parts of one
answer, so that filter threw away nineteen rows in twenty: **83 items from 2000
rows**.

The audit ran on those 83 and produced findings:

```
83-item sample     1 duplicated question,  17 answer-leaks,  1 conflicting key
full 2000 items   86 duplicated questions,  0 answer-leaks, 37 conflicting keys
```

Every number was wrong, and the answer-leak finding was wrong in the most
embarrassing direction: 17 of 83 looked like a real defect and was an artifact of
sampling the tail of a filter. Those numbers were computed and read before the
loader was checked.

What caught it was the item count on the console: 83 from a 2000-row request.
The fix is a list target, which the items schema has always supported and
describes as "a list means any listed answer is acceptable" — exactly DROP's
semantics.

This is the third loader defect in this file (see the SciQ position-bias note in
`fetch.py` and [D-016](#d-016)), and they share a shape: **a fetcher decision that
looks like tidiness is a claim about the data.** Dropping multi-span answers
looked like avoiding an ambiguous scoring contract. It was silently choosing a
4% subsample and then reporting its properties as the dataset's.

---

### D-035
**Refused a valid file over three bytes, in an error that named its own fix**
`items.py`, `dataset.py`, `contamination.py` · 2026-08-10 · fixed in v0.48.0

Found by installing the tool from scratch into an empty virtualenv, outside the
repo, and pointing it at the kind of file a stranger actually has. Every run in
this project's history had been from a clone with `pip install -e`.

```
$ dinostomp stomp mydata.jsonl
CANNOT STOMP:
  [data] mydata.jsonl:1: invalid JSON: Unexpected UTF-8 BOM (decode using utf-8-sig)
```

The file was valid JSONL. The only difference was a three-byte prefix that
**Excel, Notepad and PowerShell's `Out-File` all write by default**, which makes
this close to the most likely first-file failure a Windows user can hit.

The error even names the remedy, `utf-8-sig`, and the reader did not apply it.
Reading with `utf-8-sig` strips a BOM when present and is a no-op otherwise, so
it is strictly more permissive and changes nothing about a file that lacks one.

Fixed for user-supplied data only, via `spec.read_data_text`. Writing stays on
plain `utf-8`, because writing with `utf-8-sig` would ADD a BOM to every
artifact this tool produces and change the exact bytes the drift boundary
hashes.

Same family as [D-032](#d-032), which was the same reader blaming the same kind
of user for a `\x85` it could have handled. Two of these now, both found by
pointing the tool at somebody else's file rather than one it wrote itself.

---

### D-036
**Told a semicolon-CSV user their columns were badly named**
`dataset.py` · 2026-08-10 · fixed in v0.48.0

From the same fresh-install pass:

```
$ dinostomp stomp export.csv
  [fields] --input-field: no column looks like the input.
           did you mean one of: id;input;target?
           Columns are: id;input;target. Pass --input-field.
```

It is offering the entire header line as a candidate column name. The file is
not badly named; it is semicolon-delimited, which is **the default Excel export
in every locale that uses a comma as the decimal separator**, so this is an
ordinary file rather than an exotic one.

The message diagnosed the wrong thing and the suggested fix, `--input-field
'id;input;target'`, would not have worked. A one-column header containing a
common delimiter is now named as a parsing problem:

```
  [fields] --separator: this file has ONE column, whose name contains
           semicolons: 'id;input;target'. It is most likely semicolon-delimited
           rather than comma-delimited, so no field was split out at all.
```

Negative-tested: a genuine single-column file with no delimiter in its name does
NOT get the hint, or the guard would fire on every narrow file.

---

### D-037
**The leak check was blind to every numeric-answer dataset, by an exemption whose cost was never measured**
`answer-leak` (S2) · 2026-08-10 · fixed in v0.49.0

Found by writing pods that try to CHEAT rather than pods that are broken, which
is the contribution `CONTRIBUTING.md` asks outsiders for. One of them put the
answer in the question, in plain text, on every item:

```
"What is 10 + 11? (It is 21.)"     target: 21
```

S2 reported **0 of 24**. The cause is one line, and it is documented:

```python
# A bare NUMBER appearing in a question is not evidence of leakage.
own = {o for o in own if not NUMERIC_RE.fullmatch(o)}
```

The exemption is well-motivated. Without it, S2 called 27 GSM8K items leaks
because a word problem's quantities collide with its answer: "15 litres of
pineapple drink", answer 15. **Its benefit was measured when it was added. Its
cost was not, and its cost was total**: S2 could not detect answer leakage in
GSM8K, MATH, DROP, or any arithmetic dataset, which is a large share of what
anyone actually audits.

That is the [N-012](#n-012) lesson turned inward. A check's false-positive rate
gets measured because false positives are loud; its recall does not, because
misses are silent by construction.

**The fix is a discriminator, not a reversal.** A number stated as a premise
stays exempt; a number introduced by an answer-disclosing phrase does not:

| question | target | flagged |
|---|---|---|
| `What is 10 + 11? (It is 21.)` | 21 | **yes** |
| `What is 10 + 11? The answer is 21.` | 21 | **yes** |
| `Sally bought 15 litres of pineapple drink...` | 15 | no |
| `A shop sold 21 apples on Monday...` | 21 | no |

Measured on both sides before shipping, which is what the original exemption
skipped:

```
adversarial pod   0 of 24  ->  24 of 24     the blatant case, now caught
GSM8K             0 of 1319 -> 0 of 1319    the 27 false positives stay gone
MATH-500          2 of 500  -> 2 of 500
DROP              0 of 2000 -> 0 of 2000
TruthfulQA        1 of 790  -> 1 of 790
```

Zero new false positives across 4,609 real items, and the digit boundary is
tested so a disclosed `210` does not satisfy a search for `21`.

---

### D-038
**Announced a `choices` mapping it then silently ignored**
`dataset.py` · 2026-08-10 · fixed in v0.49.1

Spotted during the fuzz pass and left unfixed for a few hours, which is why it
is written down rather than quietly patched.

A file whose `choices` column holds a delimited STRING rather than a list:

```
{"id": "c1", "input": "q", "choices": "a|b|c", "target": "a"}
```

produced this:

```
  choices  <- choices                                    <- announced
  [ok] answer-leak   0 of 2 FREE-FORM item(s) leak ...   <- and not used
```

The mapping line says the column was understood. The audit then treated every
item as free-form and skipped the five option checks without saying so. A reader
sees `choices <- choices` and concludes the option checks ran.

This is the inverse of the rule the dataset audit is built on, that a guess the
user cannot see is a guess the user cannot correct. Here the guess was shown and
the fact that it was DISCARDED was not.

Fixed by naming it, and naming the remedy, because the usual cause is a CSV
export and `data.separator` exists precisely to split one:

```
  the 'choices' column was mapped to `choices` but yielded none, so every item
  was audited as FREE-FORM and the option checks did not run. The values look
  delimited ('a|b|c'); declare `data.separator: "|"` in a spec to split them.
```

Negative-tested: a working choice pod produces no such note.

---

### D-039
**A loader that mis-keyed a whole exam by one, then reported the artifact as a finding**
`benchmarks/fetch.py` · 2026-08-10 · fixed in v0.50.0

The Iranian driving-test answers are 1-indexed strings: `"4"` means the fourth of
four options. The loader assumed 0-indexing:

```python
elif text.isdigit() and 0 <= int(text) < len(opts):
    target = opts[int(text)]        # "3" -> opts[3] -> the FOURTH option
```

Two consequences, and the second is much worse than the first. Every item keyed
to the last option was DROPPED, because `4 < 4` is false, which is why 126 rows
became 75. And every surviving item was silently MIS-KEYED by one.

The audit then reported:

```
[warn] position-bias   gold overshoots position 3 by +20% over expectation (34 of 75)
```

which is exactly what an off-by-one produces, and it is a finding about the
loader wearing the costume of a finding about a driving test. Re-fetched with
the base derived from the split rather than assumed, the position warning
disappears and a genuine length-bias warning takes its place ([F-024](#f-024)).

**A wrong key is worse than a dropped row.** [D-034](#d-034) dropped 96% of DROP
and the numbers were wrong; this INVERTED numbers while looking plausible, and a
plausible wrong finding is the one that gets published. The index base is now
derived from the whole split, and if it cannot be determined the loader resolves
nothing numeric rather than guessing.

Fifth loader defect in this file. They keep sharing a shape: **an assumption
about somebody else's data, made silently, that the report then presents as a
property of that data.**

---

### D-040
**A machine-readable feed published for two releases with no contract, a `date` field that is not always a date, and a silently blank subject**
`scripts/index_findings.py` · 2026-08-10 · fixed in v0.52.0

`findings.json` shipped as "one record per entry, for anyone who would rather
query than read 2,000 lines of markdown" and was then treated as a convenience
dump rather than as an interface. Three consequences, found by writing the
schema that should have existed first:

**1. `date` is not a date.** One entry is dated `first live fleet`, and two dozen
carry a month with no day. Anything doing the obvious thing:

```python
sorted(feed["findings"], key=lambda f: date.fromisoformat(f["date"]))   # raises
```

breaks on the first entry it meets. The feed now publishes `date_iso`, which is
**null** whenever the ledger did not carry a full day, alongside
`date_precision` and the verbatim `date`. A null is the ledger declining to
claim a precision it has not got. Inventing a day would have made every consumer
sortable and a quarter of them wrong.

**2. A blank subject passed silently, and the schema caught it on its first
run.** [D-039](#d-039) reached the index with an empty subject cell, because the
generator PRESERVES editorial fields (correctly, it must not invent prose) and
never checked that one was there. The cross-reference filed it under
`(unattributed)` and said nothing. The very first validation run rejected it:

```
findings.json violates docs/findings.schema.json at findings/79/subject [D-039]:
  '' should be non-empty
```

**3. No version, so no way to depend on it.** A consumer had no signal for
"this field changed meaning". The feed now carries `schema_version`, the tool
version and the engine fingerprint that produced it, and the compatibility rule
is stated in `docs/findings.schema.json` rather than implied: within a major
version, fields are only added.

**The general shape, which is the point of the entry.** This file argues that a
published number needs a checkable contract, and then published a data file
without one for two releases. `status_class` is where that lesson is applied
hardest: it buckets a free-text status, and an unrecognised status raises
instead of falling into an `"other"` bin, because a silent catch-all is exactly
how a mis-typed status becomes a finding nobody can filter for. Every
default-shaped bug in this ledger has been the flattering one.

---

### D-041
**The numeric scorer's default scored a live model 0.000 whose real accuracy was 0.438, and the case lived in a source comment instead of this file**
`scorer-artifact` (R16) · 2026-08-10 · scoped, not fixed

`scorer: {kind: numeric}` extracts the FIRST number in the output. That is the
conservative reading of "reply with the number", and it is a trap on any model
that shows its working:

```
"12*3 = 36, 8*5 = 40, 36+40 = 76"      ->  extracted 12
```

Found live, in a real fleet, where it scored one model **0.000** against a real
accuracy of **0.438** and ranked it LAST in a fleet it was actually leading.
Nothing about the model was wrong. The eval was reading the first token of its
reasoning as its answer.

**Why this is `scoped, not fixed`.** The default stays `first`, because
`extract: last` is a trap in the other direction on any model that restates the
question or appends a check. There is no default that is right for both, so the
pod declares one and R16 exists to catch the case where the declaration is
wrong: it fires when failed answers contain the reference string, which is what
a scorer artifact looks like from the outside. `extract: last` is the knob.

**The reason this entry exists at all is worse than the defect.** This case was
documented in a comment in `scorers.py` and in one CHANGELOG line, and the
README cited it as a headline example under the sentence *"Every row is a real
finding with a receipt in FINDINGS.md."* There was no receipt. It was found
while restructuring the README around the ledger, by trying to put a finding id
next to the claim and discovering there was none to put.

A ledger only works if things go INTO it. The rule that follows, and is now in
[CONTRIBUTING.md](CONTRIBUTING.md): **a case good enough to cite in a README is
good enough to number.** If it is worth quoting, it gets an id, and if it is not
worth an id it does not go in the README.

---

### D-042
**The bare-file path silently dropped `input_ref`, so ten distinct photographs were reported as one duplicated item**
`dup-questions` (S1), `conflicting-keys` (S7) · 2026-08-10 · fixed in v0.53.0

The first image pod ever run through `dinostomp stomp` came back like this, on
ten pictures that share nothing but a prompt:

```
[FAIL] dup-questions     1 duplicated question(s) among 10
         - which shape is in this image? || blob | gradient | square | stripe
[FAIL] conflicting-keys  1 question(s) appear with conflicting targets
```

`build_items` constructs a fresh dict from the columns it recognises rather than
copying the row, so anything it does not name is gone. It did not name
`input_ref`. Every item then keyed on the prompt alone, every prompt was
identical, and both gating checks fired on a dataset with no defect in it.

**The docstring for the function that broke had described this exact failure,
one commit earlier.** `_item_key` was written with a paragraph explaining that
keying an asset item on its prompt collapses a whole dataset into one duplicate
pile. Knowing the failure mode and writing it down did not prevent it, because
the loss happened two files away in code that predates the feature.

Fifth defect in this ledger of the form **an assumption about the shape of
somebody's data, made silently, that the report then presents as a property of
that data** ([D-016](#d-016), [D-034](#d-034), [D-038](#d-038),
[D-039](#d-039)). The other four were about datasets this tool read. This one
was about a dataset this tool WROTE, which is worse, and it is the argument for
the example pod being in the repository rather than in a test fixture: it was
found by looking at real output.

---

### D-043
**S15's first specificity trial called ten distinct images near-duplicates, and it was not wrong**
`near-dup-assets` (S15) · 2026-08-10 · scoped, documented, not fixed

The clean-pod arm of the trials exists so a new check has to prove it stays
quiet on good data. S15 failed it immediately:

```
clean image pod: distinct pictures, pinned, no split overlap
  0 findings   ->   verdict=incomplete, findings: ['S15=warn']   ** FALSE ALARM **
```

The ten fixtures were `(seed*37 + x*11 + y*29) % 256`: ramps that differ only in
PHASE. dHash compares each pixel to its right-hand neighbour, so it encodes
gradient DIRECTION and discards absolute values. Every one of those images has
the same gradient direction everywhere, so their hashes are identical, and by
the only definition the check has they are duplicates.

**The fixture was wrong AND the limitation is real**, and separating the two
took building a second fixture out of blocks at varying positions and sizes,
which comes back silent. So:

  * the clean pod now uses structurally distinct images, and the ramp helper
    carries a comment saying what it must not be used for.
  * **S15 stays a DIAGNOSTIC.** It warns, it prints the Hamming distance for
    every pair, and it never gates a verdict. A check with a known
    false-positive class must not be able to turn a report `BROKEN`.
  * the false-positive class is named in `perceptual.py`: a corpus whose images
    share one dominant gradient (documents, spectrograms, plots on white) will
    read as mutually near-duplicate, and on that kind of data this check is
    measuring its own threshold rather than the dataset.

Recorded because a false-positive class found by the author, before release, in
the arm built to find it, is the cheapest one anybody will ever find. The
alternative is that a stranger finds it in their own corpus and concludes the
tool is noisy.

---

### N-017
**Scored against a human answer key in a modality it was never built for: S15 finds 28% of the duplicates people found, and every byte-level check finds 0%**
`near-dup-assets` (S15) · 2026-08-10 · measured

Barz & Denzler hand-annotated every CIFAR-10 test image that has a
near-duplicate in the training set and published the pairs with judgment codes
(ciFAIR, CC-BY-SA). That is an answer key for a defect class this battery claims
to detect, written by people who had never heard of it. Second entry of this
kind, after [N-012](#n-012).

**RECALL, and it is the unflattering half.** 249 pairs are judged genuine
duplicates: the same camera shot, differently post-processed.

```
 bits      genuine duplicates    very similar
    0            0/249 = 0.0%            0/37
    3          27/249 = 10.8%            0/37
    5          70/249 = 28.1%            0/37   <- shipped threshold
    8         131/249 = 52.6%            5/37
   12         193/249 = 77.5%           10/37
   16         225/249 = 90.4%           20/37
```

At the shipped threshold the check recovers **fewer than one duplicate in
three**. Anyone reading `no near-duplicate assets` on an image dataset should
read it as "none of the kind this finds", and the check's own output now prints
the distance for every pair so the threshold is visible rather than implied.

**The 0.0% at zero bits is the other half, and it is why the check exists.** Not
one of the 286 annotated pairs is byte-identical. `dup-questions` (S1),
`conflicting-keys` (S7) and `split-leak` (S14) all key on the asset's SHA-256,
so on this dataset they find **nothing at all**. The comparison at the shipped
threshold is not 28% against some better check. It is 28% against zero.

**PRECISION, and the pod flatters it.** Two measurements, and the difference
between them is the point.

On the constructed 3,563-image pod: 77 candidate pairs, 73 test-to-train, and
**70 of the 73 are the exact edge ciFAIR annotated**. That looks like 96%
precision and it is an artifact of the sample. The pod is built AROUND the
annotated duplicates, so almost everything it can find is already labelled.

On the full 60,000 images, at the same threshold:

```
158 test/train pairs flagged
  70  an edge ciFAIR annotated
   3  two images ciFAIR annotated as duplicates, joined by an edge it did not list
  85  at least one image ciFAIR never annotated
```

**The 85 are unverified and are not a finding.** They are either false positives
or duplicates the annotation missed, and nothing here can tell those apart
without someone looking at 170 pictures. Quoting the pod's 96% as the precision
of this check would have been reading a number off the sample designed to
produce it.

The 3 in the middle are worth recording for how they nearly went wrong. All are
the same white car:

```
cifar-test-03520 ~ cifar-train-46237  (4 bits)
cifar-test-08356 ~ cifar-train-33063  (5 bits)
cifar-test-02929 ~ cifar-train-49426  (5 bits)
```

The first reading was "three duplicates ciFAIR missed". Checking whether those
ids appear in the annotation under a DIFFERENT partner killed it: every one of
the six is annotated, just linked to another member of its own cluster. ciFAIR
publishes pairs, not cliques. `compare.py` now computes that three-way split
itself, so the distinction between a result and an overclaim is a line of output
rather than something the next person has to think of.

**What this is NOT.** It is not a finding against CIFAR-10. That CIFAR-10 has
train/test duplicates is Barz & Denzler's result, published in 2020, and filing
it in the `F` series would be claiming their work as this tool's. There is no F
entry for CIFAR-10 in this file on purpose.

**What it changes.** `near_dup_bits` moves from `convention` to `calibrated` in
the threshold table: it was a citation to common practice and it is now a
measurement with a curve behind it. The default STAYS at 5 despite 8 buying
almost twice the recall, for the reason recorded when the MMLU-Redux comparison
nearly reversed a case-folding decision: **a measurement on one dataset is not a
licence to reset a default for every other.** 32x32 photographs are not
documents, screenshots or spectrograms. The curve is published, the dial is
named, and the next dataset to be measured is what would move it.

---

### D-044
**The asset-path guard asked the local operating system what "absolute" means, so it refused a path on Windows and accepted it on Linux**
`asset-drift` (S12) · 2026-08-10 · fixed in v0.53.1

`resolve()` began with `Path(uri).is_absolute()`, which answers for the CURRENT
platform. `C:/Windows/System32/drivers/etc/hosts` is absolute on Windows and, on
Linux, is an ordinary relative path whose first segment happens to be called
`C:`. The same dataset therefore got two different answers on two machines.

The test suite asserted the refusal. It passed here and failed in CI within a
minute of the first push:

```
E   AssertionError: 'C:/Windows/System32/drivers/etc/hosts' was allowed to resolve
E   assert PosixPath('/tmp/pytest-.../C:/Windows/System32/drivers/etc/hosts') is None
```

**SCOPE, and it is smaller than the headline sounds.** Nothing escaped. The
resolved path was `<pod>/C:/Windows/...`, still inside the pod, because the
CONTAINMENT test after it is what actually confines a read and it was never
fooled. What failed was the earlier, cheaper guard whose job is to refuse a
non-portable path outright. The consequence was a pod that a Windows user could
not build and a Linux user could, quietly, by reading a directory literally
named `C:`.

The fix tests absoluteness under BOTH conventions plus the two forms neither
`is_absolute` catches everywhere: root-anchored-without-drive (`/etc/passwd`
read by Windows) and UNC shares (`\\host\share`). The suite now runs the
Windows and UNC shapes on every platform, and a second test asserts the guard
does NOT refuse ordinary relative paths, including the backslash form a
Windows-authored pod produces.

**Third defect in this ledger that only a second operating system could find**,
after the line-ending pair ([D-002](#d-002), [D-014](#d-014)). All three have
the same shape: a platform-dependent primitive used where a platform-independent
answer was meant, on a machine that only ever sees one platform. The standing
lesson is not "test on Linux". It is that **the local suite is structurally
incapable of catching this class**, and CI on a different OS is not redundancy
here, it is the only instrument.

---

### D-045
**The corpus's first scored run found three defects in the corpus and none in the battery**
`corpus/generate.py`, `corpus/basepool.py` · 2026-08-10 · fixed in v0.55.0

`corpus/` is a benchmark for detectors of broken evals: 204 instances, each a
small dataset with exactly one planted defect. Scoring dinostomp on it the first
time produced three numbers that all turned out to be about the generator.

**1. The clean pool was not clean.** 20 of 51 instances labelled CLEAN were
flagged by `position-bias` (S3), and S3 was right on every one. Arithmetic
options were sorted numerically and the distractors straddle the answer, so the
gold landed in a middle slot far more often than chance:

```
gold overshoots position 2 by +21% over its per-item expectation (11 of 24)
```

A control arm with a real defect in it makes every false-alarm number
meaningless, and the false-alarm number is half of what this corpus reports.

**2. A defect planted where the check cannot look.** `answer-leak` scored 0%
recall. S2 is `n/a` on multiple-choice items ON PURPOSE, because an option list
already names every candidate answer and treating that as a leak is a
false-positive machine. The planter appended the answer to a choice item and
then labelled S2 as the check that should catch it. Planted into a free-form
item, recall is 100%.

**3. A shortcut that was not a shortcut.** `surface-shortcut` scored 0%. The
planter wrote `[orrin]` into the stem and `orrin` into the gold option; S9
tokenises on whitespace WITHOUT stripping punctuation, so `[orrin]` and `orrin`
never matched. That rule is deliberate and measured: stripping punctuation costs
75 extra false positives on MMLU-Redux for 2 extra catches. The generator was
what had to change.

**Every one of the three was in the direction that makes the battery look
worse**, which is worth recording precisely because it is the unusual direction.
The standing pattern in this file is that a measurement error flatters whoever
made it ([D-004](#d-004), [D-008](#d-008), [D-033](#d-033) and the rest). A new
instrument scoring its author's tool has the opposite incentive, and got the
opposite bias. The lesson generalises to anyone submitting a detector here: **the
first run of a new instrument measures the instrument.**

---

### D-046
**S3 warns on one clean dataset in six at exactly the size its own applicability rule admits**
`position-bias` (S3) · 2026-08-10 · measured, scoped, not retuned

The corpus's clean arm is 51 datasets with nothing wrong with them. S3 fired on
8, a rate of 15.7%. That is not a bug in the corpus this time: it is the check's
designed behaviour, and the rate is calculable.

S3 trips when a position's gold count exceeds its per-item expectation by 20% of
n. The margin is ABSOLUTE and it is applied to each of four positions with no
multiplicity correction, so on clean four-option data:

```
  n items   threshold   P(a clean dataset trips S3)
       20           9                        16.3%
       24          11                         8.7%
       30          14                         3.3%
       50          23                         0.4%
      100          45                         0.0%
```

The analytic rate at n=24 is 8.5%, inside the 95% interval on the observed 8 of
51 ([5.7%, 25.7%]), so the corpus and the maths agree.

**The uncomfortable part is the interaction with the applicability rule.**
`min_choice_items = 20` is the threshold at which S3 starts running, and n=20 is
where **one clean dataset in six warns**. The check switches itself on precisely
where it is noisiest, and the rate does not become negligible until about 50
items. At n=20 the margin sits roughly two standard deviations from the mean,
with four chances to cross it.

**Not retuned, deliberately.** S3 is a DIAGNOSTIC: it warns, it never gates, and
it prints the underlying counts so a reader can see 11 of 24 and judge it. A
Bonferroni correction across the four positions, or raising `min_choice_items`,
would each fix it, and picking one on a single measurement is the move this
ledger has warned against since the MMLU-Redux comparison nearly reversed a
case-folding decision on one dataset. `position_margin` moves from `judgment` to
`calibrated` and the curve is published; the dial is named and the next
measurement is what should move it.

What changes today is what the report says. A `position-bias` warning on a
20-item set is now qualified with the rate at that size, because a reader
deserves to know that one clean dataset in six produces the line they are
reading.

---

### D-047
**The corpus shipped a "withheld" split whose labels anyone could print, and the fix silently rewrote the public one**
`corpus/generate.py` · 2026-08-10 · fixed in v0.56.0

Two defects, twenty minutes apart, in the machinery meant to make a benchmark
resistant to being gamed.

**1. There was no held-out split.** v0.55.0's README and `SPLITS.md` both
described a split with withheld labels. Seeds were derived from public
arithmetic and nothing else:

```python
digest = hashlib.sha256(f"dinocorpus/{split}/{index}".encode()).hexdigest()
```

so `python corpus/generate.py --split test` reconstructed the labels exactly.
The class each instance carried was worse: `plantable[index % len(plantable)]`,
computable with no code at all. What shipped was not a withheld split, it was a
differently named public one, and the documentation claimed otherwise.

The fix is a nonce read from `DINOCORPUS_NONCE`, mixed into every seed AND into
the class schedule, plus a refusal to generate a non-public split without one.
A withheld split now publishes its instances and a **SHA-256 commitment to its
labels**, so when it is revealed anyone can check the answer key was not edited
after the submissions arrived. `score.py` refuses to score labels that do not
match their commitment, which was negative-tested by editing one.

**2. The fix rewrote the public split.** Threading the secret through as

```python
f"dinocorpus/{split}/{index}/{secret}"
```

appended a trailing slash even when the secret was empty, so every hash in the
PUBLIC split changed and `dev` became a different 204 datasets under the same
name. Nothing failed. The only symptom was the published scorecard moving from a
15.7% false-alarm rate to 5.9% with no edit to any check, which is exactly the
kind of number that gets accepted as noise.

**This one is worth more than the first.** `corpus/SPLITS.md`, written that same
hour, opens with "splits are archived, never replaced", and the reason given is
that quietly overwriting a split makes every published number unverifiable. The
document was accurate and the code broke its rule within thirty minutes,
silently, in the direction of a better-looking score.

The seed material now appends the secret only when there is one, so `dev` is
byte-identical to the split v0.55.0 published, and
`test_the_dev_split_has_not_changed_identity` pins its labels hash. A split's
identity is its contents; a promise that a split will not change needs something
that fails when it does.

---

## The honest scorecard

**One external check.** [N-012](#n-012) is the only entry here scored against a ground truth this project did not produce: 5,700 MMLU items annotated by hand at Edinburgh. Against the one error type a data-at-rest check can reach, the battery scores precision 25% and **recall 5%**, up from 14% and 3% before this measurement was used to fix it. It also found two double-keyed items the annotators marked `ok` ([F-018](#f-018)). Both directions are the finding; neither on its own is.

**Twenty-five benchmark pods**, all fetched from their authors and none
vendored: MMLU, MMLU-Pro, HellaSwag, ARC-Easy, ARC-Challenge, GSM8K,
TruthfulQA, CommonsenseQA, OpenBookQA, BoolQ, WinoGrande, SciQ, MedMCQA, RACE,
MuSR, LogiQA, MATH-500, DROP, AQuA-RAT, CIFAR-10, and an imported lm-eval log.

**Five of them are assessments written for PEOPLE** rather than for models
(MedQA-USMLE, NCLEX, the 2023 Chinese pharmacist licensure exam, an Iranian
driving licence test, AQuA-RAT), and three of those five decide whether somebody
may practise a profession.

Count it precisely.

| series | count |
|---|---|
| findings in other people's evals (**F**) | **25** |
| &nbsp;&nbsp;of which receipt-backed dataset defects | 10 (F-001 to F-004, F-008 to F-013) |
| &nbsp;&nbsp;of which findings about a judge, model or agent | 4 (F-014 to F-017) |
| &nbsp;&nbsp;of which findings about running one | 3 (F-005, F-006, F-007) |
| negative results, recorded rather than dropped (**N**) | **17** |
| defects in dinostomp itself (**D**) | **47** |

Forty-seven to twenty-five. That ratio is the useful number to publish, and it is the
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
