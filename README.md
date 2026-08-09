<p align="center">
  <img src="docs/dinostomp.png" alt="dinostomp" width="360">
</p>

# 🦖 dinostomp

**Everything in your eval gets stomped before it gets believed.**

<sub>v0.41.0 · Apache-2.0 · engine `4beacd9962bd02c8` · [what it found](FINDINGS.md) · [how it works](METHODOLOGY.md) · [writing evals](AUTHORING.md) · [security](SECURITY.md)</sub>

An eval is an instrument. Almost nobody checks the instrument.

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

Fifty-five checks, each negative-tested to prove it fires, most invisible until
something breaks.

| stage | what goes wrong there | something it caught |
|---|---|---|
| **your data** | duplicate items, answers leaking into questions, an item with two correct options | MMLU keys "Subtract. 2,396 − 1,709" over `['687', '687', '1,493', '1,695']` |
| **your scorer** | a scorer that cannot fail; one that grades format instead of capability | a numeric scorer scored a model `0.000` whose real accuracy was `0.438`, and ranked it last in a fleet it led |
| **your runs** | truncated answers credited, spend disagreeing with the ledger, a model that stopped reading the question | 5 unfinished GSM8K responses scored correct |
| **your number** | seed noise read as a result; a ranking that is really about prompt phrasing | two models moved 78→90% and 81→92% on the seed alone |
| **your claim** | a published claim the evidence cannot support | a pod claiming 80% accuracy and a 20-point win, handed evidence for one model at 75%, goes `BROKEN` |
| **this tool** | the auditor drifting, and nobody noticing | a `CLEAN` report computed over runs from two different engines |

Every row is a real finding with a receipt in **[FINDINGS.md](FINDINGS.md)**,
including the last one. A validator that only publishes other people's mistakes
is telling you which mistakes it is willing to look for.

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
computes it correctly picks the wrong letter half the time. Ten of the
fifty-five checks read data at rest, which is why this costs nothing.

**Five minutes, for the other forty-four.** They need evidence: outputs, a
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

Not on PyPI yet, so there is no `pip install dinostomp`. Python 3.10+, two
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
  full coverage (29 of 29 ran; 26 n/a of 55 declared)` is a different claim from
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

**The mapping is a guess, and it says so.** It prints above the findings because
every finding rests on it, and when a dataset is genuinely ambiguous the tool
refuses rather than picking: TruthfulQA ships both a `Best Answer` and a
`Correct Answers` column, and choosing one silently would put every finding on a
coin flip.

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
is not, is in **[METHODOLOGY.md](METHODOLOGY.md)** along with all fifty-five
checks and why each one exists.

## In CI

`stomp` already exits the way CI wants: `0` sound or ok, `1` broken, `4`
incomplete, and `--json` writes the machine-readable report.

```bash
dinostomp stomp evals/refusal/eval.yaml --json stomp-report.json
```

The packaged Action is [action.yml](action.yml):

```yaml
- uses: collapseindex/dinostomp@v0.41.0
  with:
    target: evals/refusal/eval.yaml
```

It fails the job on a gated finding and posts the findings as a PR comment.
`allow-incomplete` and `trust-code` both default to **false**, because an
unattended pipeline must not accept thin coverage or import a stranger's Python
because a default said so.

It installs dinostomp from PyPI by default, which does not exist yet, so pass
`version:` pointing at this repo until it does:

```yaml
    version: "git+https://github.com/collapseindex/dinostomp@v0.41.0"
```

That is stated rather than hidden because a copy-pasteable block that fails for
the first person who tries it is a credibility wound in a document whose whole
thesis is receipts.

`dinostomp report` also writes `stomp-badge.svg`, which carries the verdict and
its coverage fraction together (`sound 55/55`) so a badge on a README cannot
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
mis-aimed, or saturated eval can pass every check here. Fifty-five is not a
number that bounds the ways an eval can be invalid.

**The self-tests are not independent validation.** 83 of 83 caught means every
check fires on the failure it was built for. Those failures were planted by the
same hands that wrote the checks, so it says nothing about defects nobody here
imagined, and the scorecard prints that caveat under its own score. The next
real credibility jump is outsiders breaking it: see
[CONTRIBUTING.md](CONTRIBUTING.md), where the ask is a pathological pod built
from the schemas *without* reading the check implementations. Misses get
published next to the tool's own defects.

**The battery ships with its own validation, and you can run it.**

```bash
python trials/run_trials.py        # 83 planted defects, 13 pods that must stay clean
python trials/pin_thresholds.py    # which of its own thresholds are load-bearing
```

The current answers are 83 of 83 caught, 0 false alarms, and 25 of 33 thresholds
pinned. That last number is published because it is uncomfortable: eight
thresholds could be quietly loosened today without a single trial noticing, and
the tool names them.

## Docs

- **[AUTHORING.md](AUTHORING.md)** — writing a spec, or having a model write one: the schema contract and the self-correction loop
- **[FINDINGS.md](FINDINGS.md)** — what it found, in MMLU, GSM8K, TruthfulQA, and in itself
- **[METHODOLOGY.md](METHODOLOGY.md)** — the fifty-five checks, the pod format, the philosophy, the self-audit
- **[SECURITY.md](SECURITY.md)** — pod code, untrusted model output, money, what this does not do
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — the entry fee for a new check is a planted defect, not an argument
- **[REFERENCES.md](REFERENCES.md)** — where the borrowed methods come from, what the audited benchmarks are, and what this deliberately does not borrow
- **[CHANGELOG.md](CHANGELOG.md)** — every release, including the ones that fixed its own flattering bugs

## Authenticity

<sub>The engine fingerprint is the SHA-256 of dinostomp's own code and schema pack (`4beacd9962bd02c88c5e5a102e630431621b2689120ac4d3bc26dd6eda3de364`). Recompute it with `dinostomp fingerprint`; if it differs, you are not running the code these docs describe. It is recorded in every run manifest as `tool_sha256`, because an auditing tool is an input to its own verdicts and should be hashed like every other input. When you cite a RESULT rather than the tool, quote the fingerprint alongside the version.</sub>

## Citing, contributing, license

`CITATION.cff` carries the citation metadata. `CONTRIBUTING.md` states the entry
fee for a new check and the rules a patch may not remove. [Apache-2.0](LICENSE).
