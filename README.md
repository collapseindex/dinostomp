<p align="center">
  <img src="docs/dinostomp.png" alt="dinostomp" width="360">
</p>

# 🦖 dinostomp

**Everything in your eval gets stomped before it gets believed.**

<sub>v0.62.0 · Apache-2.0 · engine `2f8e5ac5ce45f2d6` · [what it found](FINDINGS.md) · [how it works](METHODOLOGY.md) · [writing evals](AUTHORING.md) · [security](SECURITY.md)</sub>

An eval is an instrument. Almost nobody checks the instrument.

## What it found

Across **31 benchmark pods**, five of them assessments written for people, three of
those professional licensing examinations:

- MMLU keys "Subtract. 2,396 − 1,709" over `['687', '687', '1,493', '1,695']`. The answer is on the option list twice, so a model that computes it correctly picks the wrong letter half the time ([F-002](FINDINGS.md#f-002))
- A national pharmacist licensing exam offers the same drug twice in one five-option list, on 16 items ([F-025](FINDINGS.md#f-025))
- An Iranian driving-licence test keys the longest option 45% of the time, where chance is 25%: you can beat it knowing no road law ([F-024](FINDINGS.md#f-024))
- A numeric scorer scored a live model `0.000` whose real accuracy was `0.438`, and ranked it last in a fleet it led ([D-041](FINDINGS.md#d-041))
- Two GSM8K models moved 78→90% and 81→92% on the random seed alone ([F-005](FINDINGS.md#f-005))

Each of those is one entry in **[FINDINGS.md](FINDINGS.md)**, with the item id,
the verbatim data and the command that reproduces it. Every `F` re-derives in
seconds, offline, for free, using the command in the next section.

**[FINDINGS.md](FINDINGS.md): 135 entries, all permanent, none deleted.**

| series | count | what it records |
|---|--:|---|
| **F** | 39 | findings in other people's evals |
| **D** | 70 | defects in dinostomp itself |
| **N** | 26 | negative results, recorded rather than dropped |

**Seventy of the 135 are against this tool**, which is the number to
read first. A validator that only publishes other people's mistakes is telling
you which mistakes it is willing to look for. Included there: the entry it
retracted after its own killer control killed it ([N-013](FINDINGS.md#n-013)),
the loader bug that manufactured a finding about a driving test
([D-039](FINDINGS.md#d-039)), and a defect in the findings feed itself
([D-040](FINDINGS.md#d-040)).

One caveat belongs up here rather than at the bottom: **three of the 121 were
graded against an answer key somebody outside this repo wrote**
([N-012](FINDINGS.md#n-012) against MMLU-Redux, [N-017](FINDINGS.md#n-017)
against ciFAIR's hand-annotated CIFAR-10 duplicates, and
[N-019](FINDINGS.md#n-019) against MT-Bench's human preference votes). All three
produced the least flattering numbers in the file, which is the argument for
more of them. Seventy self-found defects is still self-grading, and that
number moves when an outsider runs it rather than when the total goes up.
[Break it, please](CONTRIBUTING.md#break-it-please).

The same ledger as data, versioned and validated against
[`docs/findings.schema.json`](docs/findings.schema.json) before it is written:

```bash
jq '.findings[] | select(.series=="F" and .status_class=="confirmed") | .subject' findings.json
```

## What it is

dinostomp is a **verification layer for AI evaluations**. Not another harness:
it checks every boundary an eval's evidence crosses, including the ones in
somebody else's harness.

```
   items  ──▶  runner  ──▶  records  ──▶  scorer  ──▶  aggregate  ──▶  claim
     │           │            │             │             │             │
   data       spend,       integrity,    witnesses,     noise,       evidence
  checks     coverage      truncation,   mutation      seeds,       required by
                           drift          gauntlet     phrasing     the claim
```

One invariant runs under all of it: **nothing becomes evidence merely because an
earlier stage said it was.** Summaries are recomputed from records, verdicts are
re-scored from recorded text, and the engine hashes itself into its own output.

Sixty-one checks, each negative-tested to prove it fires, most invisible until
something breaks. Each stage above is a place the ledger has a receipt from:

| stage | what goes wrong there |
|---|---|
| **your data** | duplicate items, answers leaking into questions, an item with two correct options |
| **your scorer** | a scorer that cannot fail; one that grades format instead of capability |
| **your runs** | truncated answers credited, spend disagreeing with the ledger, a model that stopped reading the question |
| **your number** | seed noise read as a result; a ranking that is really about prompt phrasing |
| **your claim** | a published claim the evidence cannot support: a pod claiming 80% accuracy and a 20-point win, handed evidence for one model at 75%, goes `BROKEN` |
| **this tool** | the auditor drifting, and nobody noticing: a `CLEAN` report computed over runs from two different engines |

## Why your harness did not catch any of that

**Harnesses run evaluations. They do not read them.**

<details>
<summary>The M16 had this exact problem in 1964, and it is the clearest version of it</summary>

When the 5.56mm M193 cartridge was adopted in September 1963, one propellant was
approved for it: DuPont's IMR 4475. It could not be mass-produced inside the
specification. Remington withdrew it in March 1964 and manufacturers balked at
bidding under the existing pressure and velocity requirements, so on 28 April
1964 the Army approved loading M193 with Olin Mathieson's **WC 846** ball powder
instead.

The spec did not change. The component passed it. But WC 846 ran higher gas port
pressure and left carbon fouling, and gas port pressure is what drives the
rifle's cyclic rate. A property nobody was measuring moved, because it belonged
to the *composition* rather than to either part.

**The signal was not missed. It was explained away.** Colt observed the increased
cyclic rate in March 1964. In April, Colt's senior product engineer wrote in an
internal report that the higher gas port pressures were "in no way harmful to
the AR-15" and would lead to "more positive functioning of the rifle." The
Ichord Committee later recommended withdrawing WC 846 and chrome-lining
chambers.

That second part is why this repo keeps [a ledger of its own
defects](FINDINGS.md) and records which *direction* each error ran in. "Higher
port pressure means more positive functioning" is the same sentence as "the
check passed, so the data is clean." Both are a real anomaly read in the
direction that makes the system look fine, by the party with the incentive.

An eval pipeline is the same shape. Your dataset is fine, your scorer is fine,
your judge is fine, your model is fine, your aggregation is fine, and **the
number they produce together is not therefore trustworthy**. That is the claim
this tool exists to stop you from making by default.

<sub>Verified against [American Rifleman](https://www.americanrifleman.org/content/u-s-m16/)
and [Daniel Watters' commentary](https://www.thefirearmblog.com/blog/2015/01/09/jim-sullivan-m16-vietnam/);
primary source is the [1968 Report of the M16 Rifle Review Panel](https://apps.dtic.mil/sti/tr/pdf/ADA953116.pdf).
Two claims often repeated with this story are deliberately absent because they
could not be checked against a primary source: that the 1964 propellant tests
omitted cyclic-rate measurement, and a specific ball-versus-stick round count
for Vietnam.</sub>

</details>

Six tools were audited on one fixed rubric ([the full table, with per-cell
citations](trials/CROSSTOOL.md)): lm-eval, openai/evals, Inspect, HELM,
promptfoo and Braintrust. Their coverage concentrates in run mechanics,
provenance and regression tracking, which they do well. The families about
whether the benchmark itself measures anything are near-empty across **all six**:

| nobody checks this by default | what it looks like when it bites |
|---|---|
| duplicate / contradictory items | DROP ships 86 duplicated questions, 37 keyed to different accepted answers |
| answers leaking into their own prompt | the question contains its own key |
| MCQ key bias at rest | a licensing exam keys the longest option 45% of the time, chance is 25% |
| shortcut / partial-input solvability | the benchmark is answerable without reading the question |
| contamination | test items already sitting in a training split |
| statistical floors and saturation | a "win" that is inside seed noise |
| fleet key-error flags | an item every model gets identically wrong |

That is the gap this fills, and it is not a criticism of those tools. They were
built to run things, and reading the thing you are running is a different job.

**What they do better than dinostomp**, because a survey run by the author of one
of the tools is exactly where credit goes missing: lm-eval ships default standard
errors and an unconditional provenance echo. Inspect has typed logs with a
published schema and a per-sample cost limit enforced *before* the call. HELM
offers radical artifact transparency and the only surfaced contamination
registry. openai/evals PR-gates smoke evals on contributions. promptfoo is the
strongest CI gating substrate. Braintrust has immutable experiments and always-on
dataset versioning. dinostomp does none of those, and it is a layer over your
harness rather than a replacement for it.

**Read that table with its limits.** It is a documentation audit done on one
date, so a blank means *not found in the docs that day*, never *the tool cannot
do this*. Docs lag code everywhere, including here. Two families are marked
unaudited rather than scored, because an open question is not a low score.

## Two ways in

**Thirty seconds, on data you already have.** No spec, no key, no spend:

```bash
dinostomp stomp mydata.csv
```

```
DATASET AUDIT: mmlu.jsonl  (3000 items from 3000 rows)
  input    <- question      target <- answer      choices <- choices

  [FAIL] dup-questions     questions are unique        90 duplicated question(s) among 3000
  [FAIL] dup-options       no option offered twice     3 item(s) offer a duplicate option
           - mmlu-02178

BROKEN AT DATA SCOPE: 2 gated finding(s) in the dataset itself
```

That is a real run against the real MMLU test split, and `mmlu-02178` is the
subtraction item above: the answer is on its option list twice, so a model that
computes it correctly picks the wrong letter half the time. Fifteen of the
sixty-six checks read data at rest, which is why this costs nothing.

**Five minutes, for the other fifty-one.** They need evidence: outputs, a
scorer, a ledger, a claim.

```bash
dinostomp new my-eval               # scaffold a pod
dinostomp plan  my-eval/eval.yaml   # power, cost, witness preview BEFORE money
dinostomp run   my-eval/eval.yaml
dinostomp stomp my-eval/eval.yaml
```

```
  [FAIL] truncation-credit   9 truncated output(s) scored as pass
  [warn] seed-stability      2 of 4 model(s) move between seeds by more than the item sample explains
           - llama-3.1-8b: 78% at seed 11 vs 90% at seed 23 (spread 12%, vs 9% explainable by the sample)
  [warn] engine-drift        12 of 12 run(s) were produced by a different engine than the one auditing them
```

That is the same command against a real 4-model GSM8K run. None of those three
findings is visible in the dataset, and none of them is visible in an accuracy
number.

## Install

```bash
pip install git+https://github.com/collapseindex/dinostomp
```

Or from a clone, which is what you want if you intend to run the trials:

```bash
git clone https://github.com/collapseindex/dinostomp && cd dinostomp
pip install -e '.[dev]'
```

On PyPI: `pip install dinostomp`. Also installable from git (above) or a clone. Python 3.10+, two
dependencies: `jsonschema`, `PyYAML`.

## The pod: one folder, one eval

One folder is one eval: a spec, its items, and its receipts. Everything the run
depended on is hashed into every manifest, including the engine itself, so
editing any of it afterwards turns the verdict `BROKEN` until you re-run.

**The spec is machine-authorable and mechanically verifiable.** The schemas are
the contract and the validator returns every problem at once as a JSON path plus
a sentence, so the loop is write / validate / fix / repeat with no prose in the
way. That makes it comfortable for an LLM to author, which is the common case
today, but the durable property is the verifiability rather than the producer.
Point whoever is holding the keyboard at **[AUTHORING.md](AUTHORING.md)**.

Four things then happen that you did not ask for, and they are the product:

- **Your scorer has to prove it can fail.** Specs ship witness cases including
  outputs the scorer must *reject*, executed before any real data. Stuck writing
  them? `dinostomp suggest-witnesses <spec>` proposes cases and writes nothing,
  then reports what your *own* witnesses catch separately from what the
  suggestions catch, because a suite that only holds up with generated cases in
  it is a suite nobody thought about.
- **Numbers are compared against noise, not vibes.** A model moving 12 points
  between seeds is a finding; another moving 11.5 points is not, if its sample
  is smaller. The battery does that arithmetic so nobody has to eyeball it.
- **Coverage is stated, always.** `MECHANICALLY SOUND: no integrity findings,
  full coverage (29 of 29 ran; 37 n/a of 66 declared)` is a different claim from
  a green tick, and the difference is printed every time.
- **Nothing is trusted downstream of the run.** Summaries are recomputed from
  records, verdicts are re-scored offline, and hand-editing either is a gated
  finding.


## More you can ask of a dataset

The thirty-second audit does more than duplicates.

**Take the repaired file, not just the verdict.**

```bash
dinostomp stomp items.jsonl --emit-fixes
```

```
  fixes: 93 item(s) dropped, 2907 kept
  wrote: mmlu.fixed.jsonl
  wrote: mmlu.fixed.fixes.txt   (one line per dropped item, with the check that condemned it)
```

Repairs delete and deduplicate. Nothing invents an answer or rewrites a
question, so the diff is checkable by eye, and anything a mechanical fix cannot
touch is printed with the reason plus **"The repaired file is not a clean file."**

**Check it against corpora you have.**

```bash
dinostomp stomp mine.jsonl --against mmlu.jsonl --against arc.jsonl
```

Verbatim and near-verbatim overlap: the contamination question for data that
already exists, since a canary protects only what you are about to publish. The
finding states its own limit: overlap is evidence about the corpora compared,
and **finding none is not evidence about training data**.

**Point it at a raw file and it works out the columns.** Options in one column,
or split across `choice_1..4`, `ending0..3`, `answer_a..d`. An answer key given
as the option text, a zero- or one-based index, a letter label, a single-element
list, or the name of the column that holds the answer. The index base is decided
over the whole file rather than per row, because a one-based key read as
zero-based resolves three options in four to the wrong text while only the
fourth falls out loudly.

**The mapping it chose prints above the findings**, because every finding rests
on it and you have to be able to disagree with it. When a file is genuinely
ambiguous it refuses instead of picking: TruthfulQA ships both a `Best Answer`
and a `Correct Answers` column, and choosing one silently would put every
finding on a coin flip. Each refusal names the columns and the flag that settles
it, so `--target-field` ends the argument in one flag.

<details>
<summary>Why it refuses instead of picking the column that scores best</summary>

The tempting rule is to keep whichever target column makes the answers land
inside the options. That selects the mapping with the cleanest verdict, which is
exactly how a genuinely wrong answer key becomes invisible, so it is not used.

Every guard here was written after a mapping error produced confident findings
about the wrong columns ([D-057](FINDINGS.md#d-057),
[D-064](FINDINGS.md#d-064), [D-065](FINDINGS.md#d-065),
[D-066](FINDINGS.md#d-066)). The tell each time was a check firing on nearly
every row: real defects are rare and clustered, mapping errors are total. So a
`solution` column beside a `correct_option` one is refused, because that name is
the answer in a maths dataset and a worked derivation in an exam dataset; a
target holding objects is refused, because that is an extractive span and not a
choice; and a question column whose values barely repeat is refused, because
that is a category label.
</details>

## dinocorpus: a benchmark this tool cannot win

`corpus/` is 1,956 small datasets across five scored splits (dev plus four
withheld), each with exactly one planted defect, labelled with what was
planted and where. Ground truth is a fact about how the file was
written rather than a judgement about it, so it needs no annotators and no
judge.

**Nine of its twenty-one defect classes have no corresponding check here, on
purpose.** dinostomp finds none of them:

```
DINOCORPUS dev: dinostomp 0.62.0

  recall, classes it has a check for   100.0% of 72
  recall, classes it does NOT            4.9% of 81
    of which name the planted item       0.0%
  false alarms on clean instances       15.7% of 51
```

The blind-spot classes are not exotic. *The keyed answer is simply wrong* and
*two options are both correct* are the two most common defects in the
benchmark-error literature, and neither leaves a structural trace a single-file
linter can see. Two of the twenty-one classes come from this repo's own check
registry; the other nineteen come from the literature or from real audits, and a
test fails if that ratio starts to invert.

Splits rotate, and a withheld split is withheld: seeds take a nonce from the
environment, the labels never ship, and the manifest publishes a **SHA-256
commitment** to them so a revealed answer key can be proved unedited. Held-back
defect classes are counted in every manifest and never named, which is the only
defence against someone reading the taxonomy and writing one checker per class.

Two splits are live: `dev` with labels, and `heldout-2026-08` (400 instances)
whose labels are withheld behind a published commitment. Scores are
**[corpus/LEADERBOARD.md](corpus/LEADERBOARD.md)**, never sorted by a single
number, because a leaderboard ranked on recall rewards a detector that flags
everything.

The first scored run found three defects in the corpus and one in the battery
([D-045](FINDINGS.md#d-045), [D-046](FINDINGS.md#d-046)). Details, the split
registry and the submission format: **[corpus/README.md](corpus/README.md)**.

## The report is an evaluation report, not just an audit

`dinostomp report` writes `STOMP.md`, `STOMP.json` and a badge into the pod. The
report opens with what the models actually DID, because that is what the eval
was run to find out:

```
| model       | provider | records | checkable | judgeable | accuracy | 95% CI         |
| dry-alpha   | dry      |      24 |        24 |      100% |   100.0% | [0.862, 1.000] |
| dry-charlie | dry      |      24 |        24 |      100% |    37.5% | [0.212, 0.573] |

6 model(s) x 24 item(s), mean 69.4%, spanning 37.5% to 100.0%, KR-20 0.94.
9 item(s) every model passed: 38% of the set separated nobody in this fleet.
At 24 items an UNPAIRED comparison resolves gaps down to about 40%.
```

Then item difficulty and discrimination, hardest first, with who missed each one
and the most common wrong answer. Then accuracy sliced by every metadata field
the items carry, which on MMLU is accuracy by subject. Then cost and tokens,
summed from the records. Then the claims, then all sixty-one checks, then the
receipts and the provenance.

Three rules hold that section together:

- **Accuracy is on CHECKABLE output**, and `judgeable` sits in the same row. 80%
  accurate on 60%-judgeable output is not 80% accurate.
- **Every number is recomputed from the records**, never read from a summary. A
  summary on disk is a derived artifact this tool treats as untrusted
  everywhere else, and a results table that trusted one would be the single
  place a hand-edited number survives. A test asserts the accuracy here equals
  the accuracy the checks report, on the same runs.
- **Nothing in Results can gate.** A hard item is not a defect and an expensive
  model is not a defect. Findings come from the checks; this describes.

## When the input is a file: images and audio

A text eval carries its input in the dataset. A vision or audio eval carries a
POINTER, and the thing pointed at can change without the dataset changing. An
item declares its asset and its hash:

```json
{"id": "cifar-test-00042", "input": "Which of these ten classes is shown?",
 "input_ref": {"kind": "image", "uri": "images/test/test-00042.png",
               "sha256": "9f3c...", "split": "test"},
 "choices": ["airplane", "automobile", "..."], "target": "cat"}
```

Most of the battery never looks at the modality. Every run check, every claim
check, the witness gate and the mutation gauntlet are unchanged. What changes is
that **an asset-backed item is identified by its asset's bytes**, so
`dup-questions` and `conflicting-keys` work on pictures for free, and four
checks exist that a text pod has no use for:

| check | what it catches |
|---|---|
| `asset-drift` | the file is there, inside the pod, and still hashes to what the dataset says |
| `label-in-path` | one directory per class is how image datasets ship, and it puts the answer in the filename |
| `split-leak` | the same asset in train and in test |
| `near-dup-assets` | the same picture twice, at different bytes |

The first three need nothing but the standard library. Only the last one needs
pixels:

```bash
pip install 'dinostomp[vision]'
```

Without it that check **skips and says so**, because "no near-duplicates found"
and "I cannot look for near-duplicates" are different sentences and only one of
them is true. The core keeps its two dependencies.

A ten-image demonstration ships with the repo, real PNGs and all, so the checks
can be watched firing without downloading anything:

```bash
dinostomp stomp examples/shapes/items.jsonl
```

```
  [FAIL] dup-questions     1 duplicated question(s) among 10
  [FAIL] split-leak        1 asset(s) appear in more than one split
           - bcb1988d1f76...: test, train
  [warn] near-dup-assets   2 candidate near-duplicate pair(s) at Hamming distance <= 5 of 64
           - shape-002 ~ shape-007 (0 bits)
```

**Scored against a human answer key.** Barz & Denzler hand-annotated every
CIFAR-10 test image with a near-duplicate in the training set and published the
pairs. `benchmarks/cifair/` runs the battery's own detector against that
annotation, which is the second time anything here has been graded by someone
outside this repo:

```bash
python benchmarks/cifair/fetch.py --meta      # the annotation alone, 10 KB
python benchmarks/cifair/compare.py --sweep   # recall, and what each threshold costs
```

## Beyond plain completions

**Agents** mount as examinees: a pod-local `run(item, ctx) -> {output,
trajectory}` gets the budget cap, the ledger, the witness gate and six
trajectory checks. Stated plainly and repeated in the code: a trajectory is
**self-reported**, so those checks verify the record, not the execution.

**LLM judges** have to earn it. `--probe judge` grades cases whose verdict is
known *by construction*, then regrades them under six perturbations that change
no meaning and names every bias that flips one. The judge's verbatim response is
recorded, so every verdict re-derives offline.

**Prompt phrasing** is a free parameter nobody registers. `--probe template`
re-asks the same items under six instruction framings and reports whether your
*ranking* changes, not just your number.

**Someone else's runner** is fine too. The battery consumes the record and
manifest schemas, not this runner, and each check declares which fields it
reads. `dinostomp import <spec> <their-log.jsonl>` brings a foreign log in as
conforming evidence; `dinostomp evidence <spec>` shows exactly which checks that
evidence unlocks and which fields the rest are waiting on. Imported evidence is
unprivileged: schema-validated at the boundary, inside the same drift boundary,
claiming no engine fingerprint it did not earn, and nothing is invented to fill
a gap. Pointing your scorer at their outputs re-derives their verdicts
independently, which is a real check on someone else's scoring for free.

That claim has now been tested on a log this project did not write.
[benchmarks/lm-eval-import](benchmarks/lm-eval-import/) is a real lm-evaluation-harness details
file for ARC-Challenge, 1172 items, published by the Open LLM Leaderboard in
2023. It carries **no generated text at all**, because it scores candidate
continuations by log-probability, which is how ARC, MMLU and HellaSwag are
scored there. Three checks now skip naming `output`, the coverage line shortens,
and nothing is invented to cover the gap. Getting there cost five defects in
dinostomp itself, written up as D-021 to D-025. The log's own numbers came back
clean: both metrics it reports re-derive exactly from the raw log-probabilities
in the same file (N-007).

A **second** format followed, and that is the one that says whether the contract
generalises: [Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai), the UK
AI Security Institute's framework. Nested documents rather than tables, `C`/`I`
verdicts rather than 0/1, and real tool events, so an imported agent run reaches
the trajectory checks. It cost **one** defect where the first cost five (N-011).
An imported trace is labelled `foreign_observed`, never `harness_observed`: the
exporting harness watched those calls, this engine did not.

## Agents: audit the execution, not the diary

Point a spec at pod-local Python and it mounts as an examinee, with the budget
cap, the ledger, the witness gate and the whole battery applied unchanged. Two
rails, and the difference is who writes the trace.

On the **self-reported** rail the agent writes its own trajectory, and an agent
that omits a call from its trace cannot be caught by reading it. On the
**mediated** rail the harness holds the tools:

```yaml
tools:
  retrieve: tools.py:retrieve
models:
  - {provider: mediated, model: grounded, entrypoint: agent.py:answer}
```

Now the trajectory is a log, a forbidden tool is denied when the agent reaches
for it rather than noticed afterwards, and evidence can be **withheld**:

```bash
dinostomp run examples/mediated/eval.yaml --probe ablate
```

```
[ok]   answer-grounding         0 of 3 target(s) pass items whose answer does not APPEAR ...
[warn] answer-grounding-causal  1 of 3 agent(s) answer identically with their evidence withheld
         - oneshot: 18 of 18 passing answer(s) (100%) are unchanged when the evidence is withheld
```

The first check asks whether the answer *appears* in the retrieved evidence, and
an agent answering from memory that retrieves the right thing anyway sails past
it. The second takes the evidence away and asks whether the answer changes. It
did not, for any of them.

Mediation makes the trace trustworthy. It does **not** make the agent
trustworthy: in-process, `tools._registry` reaches a forbidden tool in one
attribute access and leaves the trajectory empty. For that, put a process
boundary in the way:

```yaml
isolation: {mode: subprocess, timeout_s: 60}
```

The agent runs in a child with a credential-stripped environment, no tool code,
a denied `socket` module and an enforced timeout. Every claim is tested against
an in-process control, **including the two escapes that still work**: a re-exec
gets a socket, and `open()` still reads the tool file. Those are asserted as
passing tests so the boundary cannot quietly grow a reputation it has not
earned.

It is containment, not confinement: it defends a run against a careless agent,
not a machine against a hostile one. Untrusted code belongs in a VM.

## Extending it

The core is small and owns what `BROKEN` means. Two rails grow around it, and
both pay the same evidence tax the core pays itself.

**Checks.** A package exposing a `dinostomp.checks` entry point adds checks to
the battery. Its entry fee is the core's own: a planted defect the check must
catch and a clean pod it must stay quiet on. Ship neither and your checks still
run and are still reported, but they are labelled `UNVALIDATED`, excluded from
coverage, and **they do not vote on the verdict**.

**Adapters.** Because the battery consumes the schemas rather than this runner,
anything that writes conforming evidence is auditable. Other harnesses' adapters
can live in other people's repos; `dinostomp import` is the reference one.

**The rule that makes this safe, and it is enforced in code:**

> An extension may **add** findings. It may never remove or soften one.

No hook runs before the core, filters findings, or moves a threshold.
Extensions get a write-only collector, `THRESHOLDS` is fingerprinted around
their execution, and core findings are compared before and after. Every loaded
extension is named, versioned and hashed in the report, so a `SOUND` is always a
claim about a specific set of code.

The full contract, including why an extension is trusted when a stranger's pod
is not, is in **[METHODOLOGY.md](METHODOLOGY.md)** along with all sixty-one
checks and why each one exists.

## In CI

`stomp` already exits the way CI wants: `0` sound or ok, `1` broken, `4`
incomplete, and `--json` writes the machine-readable report.

```bash
dinostomp stomp evals/refusal/eval.yaml --json stomp-report.json
```

The packaged Action is [action.yml](action.yml):

```yaml
- uses: collapseindex/dinostomp@v0.62.0
  with:
    target: evals/refusal/eval.yaml
```

It fails the job on a gated finding and posts the findings as a PR comment.
`allow-incomplete` and `trust-code` both default to **false**, because an
unattended pipeline must not accept thin coverage or import a stranger's Python
because a default said so.

It installs dinostomp from PyPI by default. To pin a git ref instead, pass
`version:`:

```yaml
    version: "git+https://github.com/collapseindex/dinostomp@v0.62.0"
```

That is stated rather than hidden because a copy-pasteable block that fails for
the first person who tries it is a credibility wound in a document whose whole
thesis is receipts.

`dinostomp report` also writes `stomp-badge.svg`, which carries the verdict and
its coverage fraction together (`sound 57/57`) so a badge on a README cannot
outrun the evidence behind it.

## Before you trust it

**A pod is code.** A custom scorer, judge, or target is a file that gets
imported, and importing runs it. So `stomp`, `report` and `verify` refuse to
import pod-local Python by default; the affected checks skip, loudly, and the
verdict says so. `dinostomp inspect <spec>` reads a stranger's Python *without*
importing it. Full statement: [SECURITY.md](SECURITY.md).

**`MECHANICALLY SOUND` is a narrow claim, and the report says so in a field it
can never fill.** Every report carries:

```
measures the intended construct: NOT ESTABLISHED BY DINOSTOMP
```

That is a constant. There is no flag and no code path that sets it to anything
else, and a test walks the source to keep it that way. This battery checks
mechanical integrity; construct validity is argued, not computed, and a trivial,
mis-aimed, or saturated eval can pass every check here. Sixty-one is not a
number that bounds the ways an eval can be invalid.

**The self-tests are not independent validation.** 100 of 100 caught means every
check fires on the failure it was built for. Those failures were planted by the
same hands that wrote the checks, so it says nothing about defects nobody here
imagined, and the scorecard prints that caveat under its own score. The next
real credibility jump is outsiders breaking it: see
[CONTRIBUTING.md](CONTRIBUTING.md), where the ask is a pathological pod built
from the schemas *without* reading the check implementations. Misses get
published next to the tool's own defects.

**The battery ships with its own validation, and you can run it.**

```bash
python trials/run_trials.py        # 100 planted defects, 16 pods that must stay clean
python trials/pin_thresholds.py    # which of its own thresholds are load-bearing
```

The current answers are 100 of 100 caught, 0 false alarms, and 34 of 35 thresholds
pinned. That last number is published because it is uncomfortable: one
thresholds could be quietly loosened today without a single trial noticing, and
the tool names them.

## Docs

- **[AUTHORING.md](AUTHORING.md)** — writing a spec, or having a model write one: the schema contract and the self-correction loop
- **[FINDINGS.md](FINDINGS.md)** — what it found, in MMLU, GSM8K, TruthfulQA, and in itself
- **[METHODOLOGY.md](METHODOLOGY.md)** — the sixty-one checks, the pod format, the philosophy, the self-audit
- **[SECURITY.md](SECURITY.md)** — pod code, untrusted model output, money, what this does not do
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — the entry fee for a new check is a planted defect, not an argument
- **[findings.json](findings.json)** — the ledger as data: versioned, validated against [docs/findings.schema.json](docs/findings.schema.json) before it is written
- **[REFERENCES.md](REFERENCES.md)** — where the borrowed methods come from, what the audited benchmarks are, and what this deliberately does not borrow
- **[CHANGELOG.md](CHANGELOG.md)** — every release, including the ones that fixed its own flattering bugs

## Authenticity

<sub>The engine fingerprint is the SHA-256 of dinostomp's own code and schema pack (`2f8e5ac5ce45f2d6b8bfe3df03e33606b38b4074d3c48b349cae45304b83db28`). Recompute it with `dinostomp fingerprint`; if it differs, you are not running the code these docs describe. It is recorded in every run manifest as `tool_sha256`, because an auditing tool is an input to its own verdicts and should be hashed like every other input. When you cite a RESULT rather than the tool, quote the fingerprint alongside the version.</sub>

## Citing, contributing, license

`CITATION.cff` carries the citation metadata. `CONTRIBUTING.md` states the entry
fee for a new check and the rules a patch may not remove. [Apache-2.0](LICENSE).

<sub>Built and maintained by one person, unfunded. If it caught something in your
eval, [sponsorship](https://github.com/sponsors/collapseindex) buys time to keep
pointing it at real benchmarks and publishing what it finds, including the seventy
findings against itself. Adversarial pods and bug reports are worth more than
money and are always free:
[break it, please](CONTRIBUTING.md#break-it-please).</sub>
