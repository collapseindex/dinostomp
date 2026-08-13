# How dinostomp works

The [README](README.md) is what the tool does. This is how, and why it is built
the way it is. Read it if you are extending the battery, auditing the auditor,
or deciding whether to believe a verdict it produced.

[What it found](FINDINGS.md) is the evidence that any of this works.

## Contents

- [Contents](#contents)
- [A worked example, end to end](#a-worked-example-end-to-end)
- [The trials](#the-trials)
- [Philosophy](#philosophy)
- [What gets stomped](#what-gets-stomped)
- [The check table](#the-check-table)
- [Who checks the checker?](#who-checks-the-checker)
- [Spec anatomy](#spec-anatomy)
- [Organization](#organization)
- [Configuration](#configuration)
- [Testing](#testing)
- [Status](#status)
- [The evidence contract](#the-evidence-contract)
- [The rails: extending without becoming a framework](#the-rails-extending-without-becoming-a-framework)
- [Roadmap](#roadmap)
- [Agents get stomped too](#agents-get-stomped-too)
- [Who evaluated your evaluator?](#who-evaluated-your-evaluator)

## A worked example, end to end

The bundled examples run offline, for free (`dry` is the built-in deterministic offline provider: zero network, zero spend):

```bash
dinostomp run examples/smoke/eval.yaml
dinostomp stomp examples/smoke/eval.yaml
dinostomp report examples/smoke/eval.yaml   # writes STOMP.md + STOMP.json + badge into the pod
dinostomp verify examples/smoke/eval.yaml   # re-derive the published report offline: verified or mismatch
dinostomp plan   examples/smoke/eval.yaml   # power, cost, and witness preview BEFORE any money
```

`stomp` on this pod **exits 4, not 0**, and that is the intended answer: the
smoke pod is one model on six items, so most checks cannot run and the verdict
is `INCOMPLETE`. Thin coverage is nonzero by default, so an unattended pipeline
cannot accept it by forgetting a flag; `--allow-incomplete` is the explicit
escape hatch and the full exit-code table is at the end of this document. Said
here because the first example in the docs exiting nonzero, with the explanation
eight hundred lines away, reads as a broken example rather than a designed one.

```
smoke-arith | dry-strong | complete | acc 1.000 [0.61, 1.00] on 6 checkable (0 uncheckable excluded) | $0.0000
...
  [skip] fleet score totals are reliable (KR-20)    only 1 model(s) on disk; run a fleet of 4+ to unlock psychometrics
INCOMPLETE: no failures, but only 18 of 28 checks ran (37 n/a of 65 declared). Not a clean bill of health.
  note: all runs used the offline dry provider; results exercise the benchmark, not any real model.
```

Reading the verdict line: a check **ran** (pass/fail/warn), was **skipped** (applicable, but locked until you provide more evidence, and the reason says what unlocks it), or is **n/a** (structurally inapplicable to this eval's shape, e.g. choice checks on a free-form dataset). Only n/a leaves the denominator, and the full battery size is always printed beside it.

Note what just happened: a green single-model run is not called clean, and every accuracy carries a 95% Wilson interval (a point estimate on 6 items is a shrug, not a measurement). The fleet example runs six dry models over 24 items:

```bash
dinostomp run examples/fleet/eval.yaml
dinostomp stomp examples/fleet/eval.yaml
```

```
fleet-arith | dry-alpha   | complete | acc 1.000 [0.86, 1.00] on 24 checkable (0 uncheckable excluded) | $0.0000
fleet-arith | dry-charlie | complete | acc 0.375 [0.21, 0.57] on 24 checkable (0 uncheckable excluded) | $0.0000
...
  [ok]   fleet score totals are reliable (KR-20)    KR-20 0.94 across 6 models x 24 items; small fleet (6 examinees), treat as a noisy estimate
  [ok]   accuracy is distinguishable from guessing   0 of 6 model(s) score no better than guessing; fleet spans 38% to 100% vs chance ~4% (modal target floor)
  [ok]   the fleet is not pinned at a ceiling or floor  fleet accuracy spans 38% to 100% on 24 item(s)
STOMPED CLEAN (29 of 29 ran; 36 n/a of 65 declared)
  note: all runs used the offline dry provider; results exercise the benchmark, not any real model.
  this result is entitled to claim:
    - Exact-match accuracy with a 95% interval on these 24 addition items, bare-number format, per model.
  typed claim [SUPPORTED]: accuracy of dry-alpha is at least 80% (95% confidence)
  typed claim [SUPPORTED]: dry-alpha beats dry-charlie by at least 20% (95% confidence)
```

Why no ordering claim? Two dry models tie at 100% on this item set, so a claimed ranking would sit inside sampling noise, and the P6 diagnostic exists to say so: a spec whose `entitled_claims` assert an ordering gets that ordering re-tested under a paired item bootstrap (400 seeded resamples), and any adjacent pair that flips or ties too often is called out.

There is also a multiple-choice example on real data: [examples/iris](examples/iris/), the one that caught the iris duplicate (see "First blood" above), running the full choice-check battery (31 of 31 ran; the 19 n/a are S2, P6, R13/R15, C1, the six trajectory checks, and the three judge checks, since the pod declares no typed claims). P6's applicability rule, stated once: it is n/a unless the spec's `entitled_claims` assert a model ordering, in which case it runs the paired bootstrap; none of the bundled pods claims one.

## The trials

Eighty-two deliberately defective evals, each with a stated expectation of what the battery must do, run as an executable scorecard (`python trials/run_trials.py`):

```
  defect                                     expected   actual                     verdict
  duplicate question                         S1 fail    S1=fail, verdict=broken    CAUGHT
  verdict forged without touching output    R8 fail    R8=fail, verdict=broken    CAUGHT
  summary hand-edited upward                R9 fail    R9=fail, verdict=broken    CAUGHT
  worst miss deleted from a complete run    R11 fail   R11=fail, verdict=broken   CAUGHT
  one model escapes the scorer              R12 warn   R12=warn                   CAUGHT
  ...
  sensitivity: 94 of 94 defects caught, 0 missed
  specificity: 0 findings on 16 of 16 clean pods
```

The suite tests both tails: sensitivity (seventy-seven planted defects, drawn from described eval-defect classes (cited in [REFERENCES.md](REFERENCES.md)) plus this project's own adversarial reviews, NOT enumerated from the check registry) and specificity (seven expected-CLEAN pods asserted to produce zero findings, including a mixed-format pod with a bootstrap-separated ordering claim; current score 0 false alarms). The scorecard exits nonzero on a miss in either direction, and the scoring rubric is fixed: is the defect caught automatically, by default, with evidence preserved. Never "does the tool have feature X". During development, trial expectations had to be corrected because the battery behaved differently (better) than predicted, which is only possible when expectations come from outside the implementation.

## Philosophy

> dinostomp is not a Swiss army knife. It is a laser beam rifle with picatinny rails on every surface.

One beam, many rails. The core does exactly one thing: validated evals (spec in, stomped numbers out). It will never grow tracing, prompt playgrounds, prod observability, a proxy, or a hosted anything; tools that do everything validate nothing. Instead, every surface of the core is a rail: a small, documented, schema-stable interface that attachments mount onto without modifying the rifle.

The rails:

- **Data rail**: the five JSON Schemas (spec, items, records, manifest, report). Anything that emits or reads these mounts. This is also the LLM-authoring contract: models write specs against the schema and self-correct on the linter's machine-readable errors.
- **Scorer rail**: `kind: python` with `score(output, target)`. Any scorer mounts, but no scorer skips the witness gate; attachments get stomped like everything else.
- **Provider rail**: `complete(item, seed, params) -> Completion`. Any model backend mounts.
- **Judge rail**: `kind: judge` with a `judge` model block, or a pod-local `judge(output, target, ctx) -> str`. Any grader mounts, and none of them skip the witness gate or the judge probe. The judge entrypoint is hashed into every manifest like the scorer and the agent.
- **Target rail**: `run(item, ctx) -> {output, trajectory}`. Any bounded execution mounts as an examinee: an agent, a RAG pipeline, a workflow. The entrypoint file is hashed into every manifest, so the agent sits inside the drift boundary with the data and the scorer. This is how agents become first-class WITHOUT the core growing a tracing platform: dinostomp evaluates a bounded execution artifact, it does not observe production.
- **Check rail**: the check table plus the Reporter. Today adding a check means a pull request against the table; a public mounting API is planned. Either way the entry fee is fixed: an id, a gating flag, and a negative test proving the check fires. A check without a negative test does not mount.
- **Report rail**: `report.schema.json`. Renderers, UIs, and CI gates mount downstream of the JSON report. The planned local UI is itself an attachment, not the core.
- **Disk rail**: run files and manifests in `data/` are the on-disk interface. Exporters (GitHub, HF) and indexes mount here; files stay the source of truth.

Feature test for anything new: it is either the beam (makes evals faster to build or harder to fool) or a rail attachment behind an existing interface. If it is neither, it does not ship.

### "Does dinostomp have..."

- A prompt playground? No. Mount one.
- Tracing? No, and the distinction matters: an agent mounts on the target rail as an examinee, and dinostomp reads the trace it reports. Watching your production traffic is a different product.
- Agent evals? Yes, on the target rail, with six trajectory checks and their own trials.
- Agent-based red teaming? Mount it.
- A custom LLM judge? Yes, `kind: judge`, and it goes through the witness gate like every other scorer: show the cases it must reject, or it scores nothing. It also faces a gauntlet the other scorers do not, because it is a model: see "Who evaluated your evaluator?" above.
- A flag to disable the rule that a scorer must demonstrate it can reject something? **No. That part is the dinosaur.** 🦖

The rails are negotiable by design; that is what rails are for. The dinosaur is not: the witness gate, the zero-witness-pass rule, the coverage-honest verdict, required seed and budget, uncheckable staying out of denominators, and drift detection have no off switch, no config key, and no environment variable. If a fork removes them it is not dinostomp anymore, it is a swiss army knife with a dinosaur sticker.

## What gets stomped

Rules the engine enforces, not conventions it hopes for:

1. **Scorers get stomped first, and so are their witnesses.** A scorer that cannot fail is not a scorer: specs ship witness cases including outputs the scorer must reject, executed before real data, every time. And because witnesses are authored by the same party as the scorer, the W1 mutation gauntlet measures their adequacy: eight mutant scorers, each a known scoring-bug class (credits substrings, credits truncation, ignores case, ignores negation, converts uncheckable to pass, ...), are run against the witness suite. A mutant no witness catches is a named blind spot, reported with the exact witness that would close it. Equivalent mutants are excluded per dataset, so numeric pods are not nagged about case-blindness.
2. **Datasets get stomped for self-incrimination.** Duplicate questions, answers leaking into their own prompts, gold answers parked at one option position or always the longest option, contradictory answer keys. Partial-input solvability is measured from both sides: S9 sniffs surface-feature shortcuts offline (question-overlap, option length, against an analytic per-item chance null), and `dinostomp run --probe blind` re-runs the eval with every input stripped so R13 can compare blind accuracy against the informed-guesser floor. Run-time presentation sensitivity is measured too: with `data.render_choices` the tool owns the option block, `--probe shuffle` permutes it, and P9 reports how far each model moves. An earlier draft of this sentence claimed the swing "reached 28 points" on real models; that number had no run behind it in this repository and is withdrawn (see [D-019](FINDINGS.md#d-019)). The measured figure, on the one live shuffle probe there is a receipt for, is at most 2.5 points and inside the noise band on all four models.
3. **Runs get stomped for honesty.** Truncated outputs credited as correct, spend that disagrees with the ledger or the spec cap, records that fail their own schema or their manifest's identity, accuracy indistinguishable from guessing, and a model whose outputs increasingly evade the scorer (judgeability is reported beside accuracy; escaping the scorer must never look like skill).
4. **Results get re-derived, never trusted.** The battery replays the witness gate, re-scores every recorded output with the current scorer, recomputes every summary from its records, and re-derives the seeded item selection to confirm the ledger covers it. Hand-editing a verdict, a summary, or a ledger is a gated finding.
5. **Drift gets stomped forever.** Every run manifest carries the SHA-256 of the exact spec, data, scorer code, agent entrypoint, judge, and ENGINE that produced it. The engine is an input to its own verdicts, so it is hashed like everything else, published in this README, and recomputable with `dinostomp fingerprint`. Touch any of them after the run and the stomp verdict goes BROKEN until you re-run or revert. The planned export will carry the same guarantee into CI.
6. **The verdict itself gets stomped.** A check that examined zero things cannot pass, it skips. `clean` requires zero findings AND full coverage, and the full battery size is always printed ("17 n/a of 45 declared"), so a shrunken dataset never buys a cleaner-looking line. Dry-fleet reports say they are dry.
7. **Money rules are load-bearing.** `seed` and `budget_usd` are required fields, the cap is checked before every call, and an interrupted run resumes without re-paying a cent (and refuses to resume if any input changed, or if `--dry-run` would append synthetic outputs into a paid ledger).

8. **Uncertainty is part of the number.** Every reported accuracy carries a 95% Wilson interval, every report prints its minimum detectable effect, and the guessing floor is the informed-guesser cap (always answer the modal target), never a flattering uniform 1/k. Entitled ordering claims are re-tested under a paired item bootstrap (P6); a ranking that flips under resampling is inside sampling noise and the report says so. Known limitation, stated plainly: a spec pins one seed, which fixes item selection and dry outputs but does not measure run-to-run spread for stochastic providers; use `repeats` for within-run spread and `run.seeds` for between-seed spread, which P10 reports.

9. **Claims are executable specifications of required evidence.** A typed claim compiles into concrete requirements (complete runs, enough paired evidence, interval lower bounds, seeded bootstrap separation) that C1 checks off, and the report renders the checklist. A pod that declares a claim its evidence cannot support is BROKEN, because the bar was self-chosen.

10. **A judge earns the right to judge.** A judge scorer passes the witness gate, then faces a probe on cases whose verdict is known by construction and a gauntlet of perturbations that change no meaning. Its calls are priced and capped like any other calls. Its verbatim response is recorded, so every verdict re-derives offline and forging one is a gated finding; what cannot be re-derived (would it rule the same way twice?) is named as a limit instead of assumed away.

11. **Agents answer for their traces.** A target's tool policy is declared in the spec (`required_tools`, `forbidden_tools`, `max_steps`) and checked as fact, not opinion: a banned call, a skipped mandatory call, a nameless step, or a runaway trajectory is a gated finding. A correct answer that appears in none of the target's own tool results is flagged per model, so one ungrounded agent cannot hide inside an honest fleet. That check measures CO-OCCURRENCE and not causal use: on a live agent that answered from memory and retrieved afterwards, the true ungrounded rate was 100% and it reported 16% ([D-020](FINDINGS.md#d-020)). The error is one-sided, so its count is a floor and its silence is not a clean bill. **T7 asks the causal question instead**, by withholding the evidence and checking whether the answer moves; it needs the mediated rail, which is the section above. Money keeps its rules here too: a target that spends inside itself must report that spend, the ledger labels it `target_reported` rather than pretending it was metered, and the cap is enforced against it either way. The boundary is stated everywhere it matters: traces are self-reported, so these verify the record, not the execution.

Two tiers of check, and the report never blurs them. **Invariants** are deterministic facts (a duplicate exists, a hash changed, a summary does not re-derive): they gate, and a failure means mechanical invalidity. **Diagnostics** are statistical signals over thresholds (position bias, KR-20, discrimination, chance-level accuracy): they warn, expose their underlying values, and can have legitimate explanations. dinostomp treats every derived evaluation artifact as untrusted and re-derives it from the closest available primary evidence; where re-derivation is impossible and only inference remains, it says "suspicious," never "proven invalid."

## The check table

All 57 checks, their tier, and when they apply. The **slug** is what appears in output and in `--only`/`--skip`; it is an API, so renaming one is a MAJOR change. The id stays the primary key that every trial and threshold is wired to. (Reviewer note answered here once: R7 was choice-only until v0.11.0, when the informed-guesser floor made it universal; that is why the choice-only class shrank from five checks to four.)

| id | slug | check | tier | applies when |
|---|---|---|---|---|
| S1 | `dup-questions` | questions are unique | invariant (gates) | always |
| S2 | `answer-leak` | no answer leaks into its own question | invariant (gates) | free-form items with non-numeric targets, outside a forced choice |
| S3 | `position-bias` | gold answer does not favour an option position | diagnostic (warns) | 20+ keyed choice items |
| S4 | `length-bias` | gold answer is not systematically the longest option | diagnostic (warns) | 20+ keyed choice items |
| S5 | `dup-options` | no option offered twice in one item | invariant (gates) | choice items present |
| S6 | `target-not-offered` | every target is among its choices | invariant (gates) | choice items present |
| S7 | `conflicting-keys` | no identical question with contradictory targets | invariant (gates) | always |
| S8 | `canary-present` | a contamination canary travels with the data | diagnostic (warns) | jsonl data |
| S9 | `surface-shortcut` | no surface feature predicts the gold answer | diagnostic (warns) | 20+ keyed choice items |
| S10 | `canary-regurgitated` | no model reproduces the contamination canary | diagnostic (warns) | canary probe on disk |
| S11 | `corpus-overlap` | no item already appears in a reference dataset | diagnostic (warns) | a reference corpus supplied with --against |
| S12 | `asset-drift` | every referenced asset resolves and still hashes the same | invariant (gates) | items carrying input_ref |
| S13 | `label-in-path` | no asset's own path gives away its label | invariant (gates) | items carrying input_ref |
| S14 | `split-leak` | no asset appears in two splits | invariant (gates) | input_ref items declaring a split |
| S15 | `near-dup-assets` | no near-duplicate assets | diagnostic (warns) | input_ref images, with the vision extra installed |
| S16 | `authorship-circularity` | the eval is not authored in a circle | diagnostic (warns) | a provenance block is declared |
| W1 | `witness-coverage` | witnesses kill the mutant scorers | diagnostic (warns) | always |
| W2 | `surface-form` | a correct answer survives its surface form | diagnostic (warns) | a scorer that accepts a constructible baseline form |
| W3 | `graded-witness` | a graded scorer witnesses its gradation | invariant (gates) | a scorer that emits intermediate partial credit on its witnesses |
| C1 | `claim-evidence` | every typed claim's evidence requirements hold | invariant (gates) | typed claims declared |
| R1 | `input-drift` | runs match the spec, data, and scorer on disk (no drift) | invariant (gates) | runs on disk |
| R2 | `witness-replay` | the witness gate replays clean | invariant (gates) | always |
| R3 | `spend-ledger` | ledger spend agrees with the manifest and the spec cap | invariant (gates) | runs on disk |
| R4 | `record-integrity` | every run record is schema-valid, unique, and its manifest's own | invariant (gates) | runs on disk |
| R5 | `truncation-credit` | truncated outputs are never credited | invariant (gates) | runs on disk |
| R6 | `uncheckable-rate` | uncheckable rate is sane | diagnostic (warns) | runs on disk |
| R7 | `above-guessing` | accuracy is distinguishable from guessing | diagnostic (warns) | 20+ checkable records per model |
| R8 | `verdict-rederive` | recorded verdicts re-score identically | invariant (gates) | runs on disk |
| R9 | `summary-rederive` | summaries match their run records | invariant (gates) | runs on disk |
| R10 | `run-scope` | runs cover the spec's declared scope, nothing foreign | diagnostic (warns) | runs on disk |
| R11 | `selection-coverage` | records cover exactly the seeded selection | invariant (gates) | runs on disk |
| R12 | `scorer-escape` | no model selectively escapes the scorer | diagnostic (warns) | 2+ models on disk |
| R13 | `blind-solvable` | the eval is not solvable blind | diagnostic (warns) | blind probe runs from a real provider |
| R14 | `response-collapse` | no model collapses onto one answer | diagnostic (warns) | 20+ checkable records per model |
| R15 | `input-blind` | each model beats its own blind baseline | diagnostic (warns) | blind probe plus real runs |
| R16 | `scorer-artifact` | failed answers do not contain the reference | diagnostic (warns) | 5+ failed records per model |
| R17 | `nothing-scoreable` | every model produced something scoreable | invariant (gates) | runs on disk |
| R18 | `billing-mismatch` | billed output tokens match the recorded text | diagnostic (warns) | 20+ records with usage |
| R19 | `engine-drift` | the runs were produced by this engine | diagnostic (warns) | runs recording a tool_sha256 |
| R20 | `repeat-ties` | repeated items reached a verdict | diagnostic (warns) | runs with run.repeats > 1 |
| R21 | `graded-range` | graded scores stay in range | invariant (gates) | records carrying a graded value |
| T1 | `forbidden-tool` | no forbidden tool is called | invariant (gates) | forbidden_tools declared |
| T2 | `required-tool` | every required tool is actually called | invariant (gates) | required_tools declared |
| T3 | `trajectory-shape` | trajectories are well-formed | invariant (gates) | python-target runs on disk |
| T4 | `answer-grounding` | passing answers are grounded in tool evidence | diagnostic (warns) | trajectories carrying tool results |
| T5 | `trace-underreport` | no model under-reports its trajectory | diagnostic (warns) | 2+ python-target models on disk |
| T6 | `redundant-calls` | tool calls are not redundant | diagnostic (warns) | python-target runs on disk |
| T7 | `answer-grounding-causal` | passing answers CHANGE when their evidence is withheld | diagnostic (warns) | a mediated agent plus an ablation probe |
| T8 | `trace-observed` | the trajectory was observed, not self-reported | diagnostic (warns) | target runs on disk |
| J1 | `judge-agreement` | the judge agrees with cases whose answer is known | diagnostic (warns) | judge probe on disk |
| J2 | `judge-bias` | the judge is invariant to content-free perturbations | diagnostic (warns) | judge probe on disk |
| J3 | `judge-consistency` | the judge agrees with itself on identical input | diagnostic (warns) | judge probe on disk |
| J4 | `judge-self-preference` | the judge does not favour its own family | diagnostic (warns) | cross-judge probe on disk |
| P1 | `fleet-reliability` | fleet score totals are reliable (KR-20) | diagnostic (warns) | 4+ models, 5+ common items |
| P2 | `item-discrimination` | no item anti-correlates with fleet skill | diagnostic (warns) | 4+ models, 5+ common items |
| P3 | `dead-weight` | dead-weight items stay a minority | diagnostic (warns) | 4+ models, 5+ common items |
| P4 | `matrix-complete` | every model was asked the same items | invariant (gates) | 2+ models on disk |
| P5 | `unanimous-wrong` | no unanimous identical wrong answers | diagnostic (warns) | 3+ models on disk |
| P6 | `ordering-noise` | entitled ordering claims are separated beyond sampling noise | diagnostic (warns) | entitled ordering claim |
| P7 | `ceiling-floor` | the fleet is not pinned at a ceiling or floor | diagnostic (warns) | 2+ models on disk |
| P8 | `dynamic-range` | the eval separates the fleet (dynamic range) | diagnostic (warns) | 2+ models on disk |
| P9 | `order-stability` | answers survive re-ordering the options | diagnostic (warns) | shuffle probe plus real runs |
| P10 | `seed-stability` | the number survives changing the seed | diagnostic (warns) | run.seeds declared |
| P11 | `prompt-stability` | the number survives re-phrasing the instruction | diagnostic (warns) | template probe on disk |
| P12 | `ranking-stability` | the fleet ORDERING survives re-phrasing the instruction | diagnostic (warns) | template probe plus 2+ models |

## Who checks the checker?

Every mitigation in this repo is code someone added. The exposure that gets less attention is that someone can also **subtract**: loosen a threshold, widen an `n/a` condition, delete a trial. The suite stays green and the battery quietly gets weaker. The engine fingerprint proves the code changed; it says nothing about whether it changed in a self-serving direction. That is the failure mode to guard, and it applies whether the extender is a contributor, a future maintainer, or an LLM asked to "make the pod pass".

Three things push back on it, in increasing order of usefulness:

**The trials are two-tailed.** A battery tuned loud enough catches every planted defect and every innocent pod. Only the specificity arm, six pods asserted to produce zero findings, tells those apart, so quietly widening a check to silence a finding tends to show up as a false alarm elsewhere.

**`python trials/pin_thresholds.py` asks which numbers are actually load-bearing.** It loosens each threshold in turn, re-runs the whole suite, and reports the ones nothing notices. A threshold no trial pins can be relaxed without consequence, which makes it a request for a boundary trial: a planted defect sized so it is caught at the shipped setting and missed at a looser one.

Run on dinostomp itself, the first honest answer was **5 of 31 thresholds pinned**. The trials proved the checks fire; they said almost nothing about the numbers they fire at, so most of the battery's sensitivity was an unvalidated opinion. Eighteen boundary trials later it is **24 of 33**, and the remaining nine are listed by the tool rather than quietly omitted. The count went UP by two dials as well as by two pins: replacing P9's and P10's flat percentages with a noise band added `seed_spread_min`, `order_swing_min` and `noise_z`, and adding a dial without pinning it is how a battery stops guarding itself. The number is published because it is uncomfortable: a reader deserves to know how much of this battery guards its own settings.

**A threshold's number and its authority are different things.** A dial at 1.96
and a dial at 0.10 are not the same kind of object, and the report now says
which is which beside every value:

| provenance | count | what it means |
|---|---|---|
| `derived` | 1 | statistical theory fixes it; changing it means disagreeing with the maths |
| `calibrated` | 3 | measured on real data in this repo, with the measurement on record |
| `convention` | 3 | a value the surrounding literature uses, cited in [REFERENCES.md](REFERENCES.md) |
| `structural` | 2 | not a sensitivity dial: it changes what an eval IS, or what a probe spends |
| `judgment` | 34 | the author picked it |

Every `convention` threshold names its source in
[REFERENCES.md](REFERENCES.md), and a test fails the build if one does not:
an appeal to convention with nothing behind it is an unfalsifiable claim, which
is the thing this tool exists to object to.

Thirty-four of forty-three are author judgment. That is the honest label for "it
seemed about right", and it is by far the largest class. If a finding of yours
turns on one of them, the basis is printed in the report so you can disagree
with the right thing.

Sizing a boundary defect turns out to be the hard part, and getting it wrong is silent. Four fixtures landed off target before they landed on it: one reused a fixture whose gold answers were already the longest option, one let the base agent's own skill apply to items the twist did not override, and two simply overshot. In every case the check was right and the defect was the wrong size, which is the direction you want that to fail in.

Two corrections along the way are worth recording, because both produced confident wrong answers. The probe's first run consumed its own `--json` flag (the trial suite parses `sys.argv`) and wrote a well-formed scorecard containing entirely the wrong data. Its second run tested seven thresholds in the STRICT direction, where a "pinned" result only means some clean pod started false-alarming. Loosening is not a single direction: margins loosen upward, minimum-evidence bars loosen upward too but for the opposite reason, and several thresholds fire when a value falls BELOW them.

**The entry fee for a check is a planted defect, not an argument.** `CONTRIBUTING.md` states it: an id, a gating flag you have to justify, a negative test, and a trial. A check that cannot be given a defect is telling you something about the check.

None of that makes the battery tamper-proof, and it is not meant to. It makes tampering *visible in the artifact a reader already has*: the trials scorecard, the coverage line, and the fingerprint together say which battery ran, how loud it was, and what it was measured against.

## Spec anatomy

One YAML file per experiment:

```yaml
name: smoke-arith
version: 0.1.0
question: "Does the model answer two-digit addition with the bare number, exactly?"
entitled_claims:
  - "Exact-match accuracy on these 6 addition items, bare-number format."
data: {path: items.jsonl, format: jsonl}
models:
  - {provider: dry, model: dry-strong}
scorer:
  kind: exact
  witnesses:                # W1 measures witness coverage against known bug classes
    - {output: "57", target: "57", expect: pass}
    - {output: "The answer is 57", target: "57", expect: fail}   # wrappers
    - {output: "5", target: "57", expect: fail}                  # truncation
    - {output: "not 57", target: "57", expect: fail}             # negation
run: {n: 6, seed: 42, budget_usd: 0}
```

Typed claims (optional) are the precise form of entitlement: they compile into evidence requirements that C1 gates on. A claimed minimum requires the interval's LOWER bound to clear it; a claimed superiority requires a seeded paired bootstrap to clear `min_effect` at the declared confidence:

```yaml
claims:
  - {type: accuracy, model: dry-alpha, min: 0.80, confidence: 0.95}
  - {type: superiority, better: dry-alpha, worse: dry-charlie, min_effect: 0.20, confidence: 0.95}
```

Notable fields:

- `question`: the one question this eval answers. One sentence, required.
- `entitled_claims`: prose claims, human-interpreted. Anything not listed is an overclaim by definition.
- `claims`: typed claims, machine-checked. The spec chooses its own evidentiary bar by declaring one, which is why failing it gates: a self-chosen bar has no legitimate excuse.
- `scorer.witnesses`: concrete outputs the scorer must accept and reject before it may score real data.
- `provider: dry`: a deterministic offline provider, so every eval can run end to end at zero cost with no network.
- `provider: python` + `entrypoint: agent.py:run`: the target rail. The examinee is a pod-local callable receiving `(item, ctx)` and returning `{output, trajectory}`; `ctx` carries the model name, seed, and params, so one file can serve a fleet of configurations. The entrypoint is hashed into every manifest.
- `scorer.kind: judge` + `scorer.judge` + `scorer.rubric`: grade with a model. The judge's calls are priced and capped like any other calls, its verbatim response is recorded so verdicts re-derive offline, and `dinostomp run <spec> --probe judge` makes it earn the right to judge.
- `trajectory` (optional): declarative tool policy over the reported trace. `required_tools` and `forbidden_tools` gate; `max_steps` bounds a runaway. Unsatisfiable policies (a tool both required and forbidden) and policies with no target to produce a trace are rejected at load time.
- `run.repeats` (optional, default 1): query every item N times. Records carry a repeat index, and with repeats above 1 the summary switches estimators: each item takes the strict majority of its repeats (ties score 0, the conservative side, matching the fleet-matrix cells) and accuracy plus its Wilson interval are computed over item outcomes. The interval therefore brackets the same estimator the matrix reasons about, correlated repeats cannot narrow it, and the summary names its estimator (`per_record` or `item_majority`).

The full schemas live in [src/dinostomp/schemas/](src/dinostomp/schemas/) and are the contract for LLM-authored specs: validate, read the issues, fix, repeat.

## Organization

The unit of everything is the **pod**: one eval, one self-contained folder. `dinostomp new <dir>` scaffolds one:

```
memory-drift/            one pod = one eval
├── eval.yaml            the spec
├── items.jsonl          the data
├── scorer.py            optional pod-local custom scorer
├── agent.py             optional pod-local target (agent, RAG pipeline, workflow)
├── judge.py             optional pod-local judge
└── data/
    ├── runs/            ledgers + manifests (the receipts)
    └── results/         summaries
```

The pod is simultaneously the git unit, the export unit, and the drift unit. Everything the run depends on lives inside it and is hashed into every manifest (`spec_sha256`, `data_sha256`, `scorer_sha256`, `target_sha256`, `judge_sha256`, and `tool_sha256` for the engine itself); paths in specs are relative and traversal is rejected, so a pod is portable by construction: zip it, clone it, stomp it anywhere, receipts intact.

Pods live flat in a workspace, the **stomping grounds**: a plain private git repo, one directory per pod, no workspace config file (there is no config file). Pods never nest.

```
stomping-grounds/
├── smoke-arith/
├── memory-drift/
├── refusal-brittleness/
└── mounts/              shared personal attachments (see rule below)
```

Attachments come in two tiers. Real mods are Python packages mounting the rails (installable, versioned, independently shipped). Personal mods can live in a workspace `mounts/` folder, under one non-negotiable rule: **anything that influences a run gets its SHA-256 in the run's manifest.**

A path that leaves the pod is refused *unless it is declared*:

```yaml
mounts: ["../mounts/shared_scorer.py"]
scorer: {kind: python, code: ../mounts/shared_scorer.py, witnesses: [...]}
```

Declaring is what makes it legal, because declaring is what gets it hashed: every mount lands in each manifest as `mount_sha256`, so editing shared code between runs is drift exactly like editing the pod's own. An undeclared traversal is still refused, and the refusal says how to do it deliberately. Mounted Python is code from outside the pod, so it needs `--trust-code` like anything else.

The drift boundary is enforced in both directions: `dinostomp stomp` goes BROKEN when any hashed input changed after a run, and `dinostomp run --resume` refuses to continue a run whose spec, data, or scorer changed since the interruption (finished items would no longer mean the same thing).

## Configuration

No config file. Network providers read API keys from environment variables only (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`); keys are never stored, logged, or echoed in errors. The `dry` provider and everything else in the toolkit make zero network calls.

A model the built-in table does not price cannot run until you say what it costs, because a rate that cannot be priced cannot be capped, and an uncapped run is not a run this tool will start. Declare rates **per model, in the spec**:

```yaml
models:
  - {provider: openrouter, model: meta-llama/llama-3.1-8b-instruct, price_in: 0.05, price_out: 0.08}
```

Rates belong in the spec rather than on the command line for the same reason everything else does: `--price-in` is gone the moment the command scrolls away, while a rate in the spec is inside `spec_sha256`. It gets published with the pod, re-derived by anyone who verifies it, and quietly repricing history afterwards is drift that R1 catches. Each record's `rate_label` says where its price came from (`spec`, `explicit`, a table entry, or `target-reported`), so a number is never separated from the basis it was billed on. `--price-in` / `--price-out` still work for one-off runs and apply to every model at once, which is why a fleet with six different rates wants the spec.

## Testing

```bash
python -m pytest
```

The suite follows a house rule: every validator has a negative test that breaks something on purpose and asserts the breakage is caught. Beyond the unit suite, `python trials/run_trials.py` runs DinoTrials, both tails: 92 planted defects (sensitivity) and 16 expected-CLEAN pods (specificity), printed as a scorecard that exits nonzero on a miss in either direction.

## Status

Early. Currently shipped:

- **Schema pack** (v0.1.0): JSON Schemas for the five core artifacts (eval spec, items, run records, run manifest, check report), a spec loader with machine-readable errors, and a negative-tested validation suite.
- **Runner** (v0.2.0): witness gate before any real data, streamed fsynced JSONL ledger, hard USD budget checked before every call, idempotent resume that never re-pays (including after a hard kill mid-write), manifest sidecar with spec/rate/witness provenance, per-run summary with uncheckable excluded from every denominator. Scorers: exact, includes, regex, numeric, choice, custom python. Providers: dry (offline deterministic), anthropic, openai, openrouter.
- **Stomp battery** (v0.3.0): `dinostomp stomp` lints the spec, dataset, and every run on disk. Each check negative-tested, with witness counts, n/a awareness, coverage-honest verdicts (`clean` / `ok` / `incomplete` / `broken`), and a machine-readable report (`--json`). `--require-all` turns incomplete coverage into a CI failure.
- **Fleet psychometrics** (v0.4.0): five more checks (19 total) that unlock when 4+ models answered the same items: KR-20 reliability of fleet totals, negatively discriminating items (strong models miss them, weak models hit them: candidate key errors), dead-weight share, matrix completeness (gating), and unanimous identical wrong answers. Judge-free: models are examinees, the correlations do the inference. The `dry` provider fleet has real skill x difficulty structure, so all of it demos offline for free.
- **Pods and the full drift boundary** (v0.5.0): `dinostomp new` scaffolds a pod; manifests hash spec AND data AND scorer code; the drift check catches post-run edits to any of them; resume refuses to continue a run whose inputs changed.
- **Result verification** (v0.6.0): the battery grew to 23 checks and stopped trusting anything downstream of the run. Witness gate replayed, recorded verdicts re-scored, summaries recomputed, records attributed through their manifests, seeded selection re-derived and compared to the ledger, foreign and narrowed runs surfaced. Reports carry input hashes, a run inventory with dry-run visibility, and the spec's entitled claims.
- **Markdown reports** (v0.7.0): `dinostomp report` writes `STOMP.md` (GitHub/HF-native, receipts in collapsible blocks, entitled claims or an explicit refusal to claim), `STOMP.json` (the raw report published next to the rendering), and `stomp-badge.svg` for README headers. Markdown omits volatile fields, so an unchanged pod re-reports to identical bytes and reports diff cleanly in git. See it live: [examples/fleet/STOMP.md](examples/fleet/STOMP.md).
- **Constitutional split + strict exit codes** (v0.8.0): invariants (deterministic, gating) and diagnostics (statistical, advisory) are separated in the registry, the CLI summary, and the report; position/length bias moved to diagnostics where they belong. Incomplete coverage exits nonzero by default (`4`, distinct from broken's `1`); `--allow-incomplete` replaces `--require-all` as an explicit escape hatch instead of a hygiene flag someone has to remember.

- **External review round** (v0.9.0): Wilson intervals on every accuracy; the P6 ordering-vs-noise diagnostic; KR-20 small-fleet caveats; STOMP.json now byte-stable like STOMP.md (timestamps live in run manifests, where time actually happened); README de-overclaimed (privacy boundary, witness-gate scope, iris lineage and indexing convention). Battery: 24 checks.
- **Witness mutation gauntlet** (v0.10.0): W1 runs eight mutant scorers (known bug classes: substring credit, truncation credit, case/space/negation blindness, uncheckable-credit, constant verdicts) against the witness suite; survivors are named blind spots with the witness that would close them; equivalent mutants excluded per dataset. Witnesses may now `expect: uncheckable` to pin unparseable-output behavior. The gauntlet's first victims were this repo's own example pods and the `dinostomp new` template, all of which needed more witnesses. Battery: 25 checks.
- **Field-diff round** (v0.11.0): six upgrades from diffing the battery against the toolkit landscape and the benchmark-defect literature. Saturation and dynamic-range diagnostics (a fleet pinned at a ceiling, or one the eval cannot separate, is now visible); the guessing floor upgraded from uniform 1/k to the informed-guesser modal-target cap; the answer-leak check learned the candidate-list rule (a question offering its answer space is not leaking); P6 upgraded from interval overlap to a paired item bootstrap; every report prints its minimum detectable effect; contamination canaries are a first-class convention: a `_canary` line in the data file, skipped by the loader, covered by the data hash, scaffolded by `dinostomp new`. S8 checks presence; `--probe canary` then asks each hosted model to continue the canary and S10 reads the answer. Battery: 28 checks.

- **Uncheckable science + provenance envelope** (v0.12.0): summaries carry judgeability next to conditional accuracy (80% accurate on 90%-judgeable output never masquerades as plain 80%); the R12 diagnostic flags a model whose uncheckable rate is an outlier against the fleet (escaping the scorer must never look like skill); manifests carry an environment fingerprint (python, platform, package versions) and the model identifier the provider actually returned; reports state the reproducibility tiers honestly (inputs hash-pinned, requests reproducible given the envelope, hosted-model immutability unknown). DinoTrials shipped: an executable scorecard of deliberately defective evals (30 defects at that release, 30 of 30 caught; the suite has grown since). Battery: 29 checks. (v0.12.1: atomic renames retry through transient Windows file locks, found live when a virus scanner killed a run mid-manifest.)

- **Repeats estimator + published check table** (v0.13.0): with `repeats > 1` the summary switches to the item-majority estimator so the Wilson interval brackets what the fleet matrix reasons about; the check table is generated from the registry and parity-tested; DinoTrials grew its specificity arm. Battery: 32 checks.

- **Verify + plan** (v0.14.0): `dinostomp verify` re-derives a pod's published report offline and byte-compares it (a stranger can check a published verdict without trusting the publisher; a report that re-derives while BROKEN is honest and verifies). `dinostomp plan` states the minimum detectable effect, the sample size an entitled ordering claim needs, the mutants the witness suite would leave alive, and the worst-case cost against the budget cap, all before a single call is made.

- **Clever Hans instruments** (v0.15.0): S9 surface-feature shortcut sniffing (a model-free heuristic that finds the gold option means the dataset is guessable without reading it; analytic null, no permutation table) and blind probes: `dinostomp run --probe blind` strips every input, tags the run in its manifest so it can never pool with real results, and R13 compares blind accuracy against the informed-guesser floor. Dry pods are n/a for R13 (the dry provider reads the key); real-provider pods without a probe get an unlock hint. Battery: 31 checks.

- **Executable claims** (v0.16.0): typed `claims` (accuracy with a minimum the interval's lower bound must clear; superiority with min_effect under a seeded paired bootstrap) compile into evidence requirements gated by C1 and rendered as a checklist in STOMP.md; `dinostomp plan` says whether a superiority claim is even provable at the declared n before any money moves; authoring nonsense (phantom models, a model beating itself) dies at load time. The fleet example now ships two supported typed claims. Battery: 32 checks.

- **Freeze-review round** (v0.17.0): a three-lens pre-preprint pass (code smells, consistency, statistical confounds). Flattering-direction fixes: the informed-guesser floor now maxes over distinct target VALUES (multi-target items no longer split the floor); R13 checks blind solvability per model rather than pooling (one shortcut-solver in a fleet can no longer hide); the report's MDE uses the run's n, not the dataset size, and is labelled the unpaired worst case (the paired bootstrap behind P6/C1 resolves smaller gaps). Bootstraps are now seeded from a content hash so borderline results cannot be seed-shopped; C1's confirmation-on-the-generating-sample scope and lack of multiplicity correction are stated in-report and in the docstring. Schemas now declare every field the code emits (`status`, `claims`, `model_reported`, `uncheckable`). `dinostomp verify` runs green on the committed example pods, which now ship their run data so a fresh clone can re-derive them.

- **The agent rail** (v0.18.0): a target is any pod-local Python callable, mounted on the provider interface, so an agent or RAG pipeline is an examinee like any model and inherits the budget cap, the ledger, the witness gate, and the whole battery. Its entrypoint is hashed into every manifest, putting the agent inside the drift boundary. Six trajectory checks over the reported trace: forbidden tools, required tools, well-formedness and runaway length (all gating), plus grounding of passing answers in the target's own tool results, fleet-relative under-reporting, and redundant call loops (advisory). Grounding and churn are judged per model, never pooled, so one bad agent cannot hide in an honest fleet. A target that spends money inside itself reports it, and the manifest labels that spend `target_reported` instead of implying it was metered; the cap holds against it. DinoTrials grew to 42 defects (nine of them agent-shaped) and a fifth clean pod. Battery: 38 checks.

- **The judge gauntlet** (v0.19.0): `kind: judge` grades with a model, and the model has to earn it. `dinostomp run <spec> --probe judge` grades cases whose verdict is known BY CONSTRUCTION (removing the need for a second judge), then regrades each under six perturbations that change no meaning; J1 scores agreement, J2 names every bias that flips a verdict and flags fail->pass flips as INFLATING, J3 regrades on byte-identical input to catch a judge that contradicts itself. Judge calls are priced against the rate table, capped by `budget_usd`, and itemised per record; an unpriced judge model refuses to run. Scoring is split into the paid call and the deterministic parse, so records keep the judge's verbatim response and R8 re-derives every verdict OFFLINE: forging a verdict against the judge's own words gates, and so does stripping the response. A hosted judge makes `stomp` skip the witness replay and the mutation gauntlet with a stated reason rather than quietly spending money during a lint. W1 gained behavioural equivalent-mutant detection, ending a false-alarm class where it demanded a case witness from a scorer that is case-insensitive by design. Self-preference detection is deliberately NOT shipped: the available proxy is confounded by formatting. DinoTrials 42 -> 51 defects, 5 -> 6 clean pods. Battery: 41 checks.

- **Spec-declared pricing** (v0.20.0): `price_in`/`price_out` per model, inside `spec_sha256` rather than on a command line, so the rate a run was charged at is published with the pod and repricing history is drift. `rate_label` records where a price came from. W1 gained equivalence probes for the leniency mutants, which cannot fire against a scorer that answers `uncheckable` on the shapes they upgrade.

- **First live fleet** (v0.21.0): six real models found three flattering-direction defects in the shipped battery (see "What real models found" above). R7 became per-model, ledger precision went to nine decimals, and two checks were added: R14 (response collapse) and R15 (informed accuracy must clear a model's own blind baseline). The psychometric checks now exclude near-constant models, whose presence had manufactured eight phantom key errors in a real dataset. Battery: 43 checks; DinoTrials 54 defects.

- **Four eval shapes** (v0.22.0): free-form numeric, lettered multiple choice, tool-using agents, and a hosted judge, each aimed at a code path no real model had touched. A hosted judge was making `stomp` and `verify` demand an API key (and `plan` traceback), which silently broke offline third-party verification; the judge provider is built lazily now. Judges gained their own `price_in`/`price_out`, `plan` stopped printing `$0.0000` for agents that pay for their own inference, and P4 stopped treating an `uncheckable` answer as an unasked item. New check R16: failed answers that contain the reference, which separates a scorer artifact from real incapacity. Battery: 44 checks.

- **Round three** (v0.23.0): R5 ("truncated outputs are never credited") fired on real data for the first time since v0.3.0, on a pod built to produce the one response shape that is both truncated and still scoreable. Hosted judges now sample at temperature 0 by default, after the same 3B judge with the same witnesses was gated on one run and passed on the next, making the gate itself a coin flip. New check R17 (gating): every model produced something scoreable, because an eval where every record came back `uncheckable` was reporting INCOMPLETE with no failures. Battery: 45 checks; DinoTrials 56 defects.

## The evidence contract

The battery consumes the **record and manifest schemas**, not "whatever
`dinostomp run` wrote". That sentence used to be aspirational; it is now
enforced in two directions.

**Each check declares the fields it reads** beyond the schema-required core, in
[`src/dinostomp/evidence.py`](src/dinostomp/evidence.py), with a reason:

```python
"R5":  [Need(RECORD, "finish_reason", "a truncated response is identified by it")],
"R19": [Need(MANIFEST, "tool_sha256", "the engine that produced the run is compared to this one")],
```

A check whose fields are absent skips naming the **field**:

```
[skip] truncation-credit   no `finish_reason` on every record (a truncated response is
                           identified by it); 0 of 240 record(s) carry it
```

That replaces `no runs on disk yet`, which was unactionable in general and
simply false when there were runs on disk. `dinostomp evidence <spec>` prints
the whole contract against what you actually have, so a thin coverage line is
never a mystery.

Two rules keep the table honest. A check may not declare a field the schema
already requires, because a record missing one of those is schema-invalid and
`record-integrity` gates on it; hiding a gating finding behind a coverage line
would be strictly worse. And a check the contract disqualifies cannot be
revived by a later pass computing a vacuous green result over zero rows.

That last guarantee used to be half-true, which is worse than either half. A
disqualified check could not be revived into a **pass**, but its skip REASON
could still be overwritten by the check's own body, and R16 was doing exactly
that: with no `output` on any record it reported "no model has 5+ failed records
to inspect" across 966 failed records. The reason was false and the remedy it
implied did not exist. A body skip can no longer replace a skip that named
missing evidence (D-022); an ordinary skip is still overwritable, or the first
reason any check gave would freeze in place and hide better ones.

**Anything that can write conforming evidence is auditable.** `dinostomp import`
is the reference demonstration, not a privileged path:

```bash
dinostomp import my-eval/eval.yaml other-harness-log.jsonl --model llama-3.1-8b
```

```
  item_id  <- doc_id
  output   <- completion
  score    <- is_correct

  imported 24 record(s) from other-harness-log.jsonl
```

What the import gets, and does not get:

- records **schema-validated at the boundary**, so an import either yields
  readable evidence or fails loudly; a half-imported run is a lie about coverage
- the pod's **witness gate runs before anything lands**, because the scorer being
  validated is the one that will re-derive these verdicts offline
- `spec_sha256` and `data_sha256` from YOUR pod, so the drift boundary applies
  to imported evidence exactly as it does to native evidence
- **no `tool_sha256`**, because this engine did not produce these numbers, and
  `engine-drift` reports that absence instead of pretending otherwise
- **no invented fields.** If the log has no `finish_reason`, the import has
  none, `truncation-credit` skips, and coverage is one check shorter. A
  plausible fabricated value would make the report state something nobody
  measured, which is the failure this tool exists to catch.
- **no guessed verdicts.** A score it cannot read as pass/fail refuses the whole
  import rather than defaulting; defaulting to `fail` invents a number and
  defaulting to `pass` invents a flattering one.

What this buys, concretely: pointing the pod's own scorer at a foreign
harness's outputs re-derives their verdicts independently. On the worked
example, `verdict-rederive` passes, which is a real check on someone else's
scoring that costs nothing.

### What a real foreign log did to all of that

Everything above was written before this engine had ever read a log it did not
write, and the first one it met broke four things at once.
[benchmarks/lm-eval-import](benchmarks/lm-eval-import/) is that log: an lm-evaluation-harness
details file for ARC-Challenge, 1172 items, 25-shot, published by the Open LLM
Leaderboard in July 2023 for a third-party 111M model.

It is a **loglikelihood-ranking** record. The model never emitted an answer; the
harness scored four candidate continuations by log-probability and took the
argmax. There is no generated text anywhere in the file, which is also how MMLU
and HellaSwag are scored on that leaderboard. So the single most common eval-log
shape in open-weights ML met an importer that **required** an `output` column,
and was rejected at the door (D-021).

`output` is now optional. R8, R14 and R16 skip naming the field, and the coverage
line shortens, which is what the contract promised all along and had never been
asked to do. An absent output is **omitted rather than defaulted to `""`**: an
empty string is the claim that the model answered with nothing, and that is a
result, not an absence.

The other three were worse than a rejection, because each would have produced a
number:

- the log ships **both `acc` and `acc_norm`**; only one was in the candidate
  list, so the mapping took it silently. They disagree on **221 of 1172 items**,
  17.6% against 19.7%, and the leaderboard published the other one. Two verdict
  columns that disagree are now a refusal, not a coin flip (D-023).
- R16's skip reason was overwritten with a false one (D-022, above).
- `--dry` substitutes the offline provider for whatever a spec declares, so
  `run --dry` on a pod whose model cannot be called would have written 1172
  fabricated records under that model's name (D-024).

And the audit itself came back clean where it counted: both of that harness's
reported metrics re-derive **exactly** from the raw log-probabilities in the same
file, 0 disagreements in 1172 rows either way (N-007). A harness that publishes
its raw scores next to its derived ones can be checked by anyone, and this one
survives being checked.

## The rails: extending without becoming a framework

The core is small, frozen, and self-validating, and it owns what `BROKEN` means.
Everything else is a rail: a documented interface an attachment mounts onto
without modifying the rifle. Two of them are sanctioned growth surfaces, and
both pay the same evidence tax the core pays itself.

### The hard rule, before any API

**An extension may add findings. It may never remove or soften one.**

There is no hook that runs before the core, no hook that filters findings, no
hook that adjusts a threshold. The moment an extension can make a verdict
greener, every `SOUND` in the wild silently means "sound according to whatever
plugins that person happened to have installed", and the engine fingerprint
stops covering the thing that decided.

That rule is enforced in code, not requested in a style guide:

1. Extensions receive a **write-only collector**. There is no API to read, edit
   or delete a finding, including their own. A plugin that can read the verdict
   is one step from a plugin that shapes it.
2. `THRESHOLDS` is **fingerprinted before and after** extension code runs. A
   mutation aborts the audit rather than producing a report whose settings
   nobody can reconstruct.
3. Core findings are **snapshotted around the window where extension code
   executes** and compared afterwards. A changed core finding refuses the report.

Guard 3 is worth a note about how it was built. The first version compared core
findings before and after the *merge* loop, where no extension code runs, so it
could not fire; the test written to sabotage it is what proved that. It now
wraps the actual execution window. A guard nobody tried to defeat is a guard
nobody has tested.

### Rail one: checks

A check provider is a package exposing a `dinostomp.checks` entry point:

```python
NAME = "gsm8k-extras"
VERSION = "0.2.1"

CHECKS = [ExtensionCheck(
    id="X1", name="reasoning traces are not truncated mid-step",
    gating=False, applies_when="records carrying a trace",
    run=lambda ctx, out: out.finding("X1", "warn", "...", n=len(ctx["runs"])),
)]

TRIALS = [...]        # a planted defect these checks MUST catch
CLEAN_PODS = [...]    # a good eval they must stay quiet on
```

`TRIALS` and `CLEAN_PODS` are the entry fee, and they are the same fee the core
pays. Declare neither and your checks still **run and still get reported**,
because suppressing a finding would be its own kind of dishonesty, but they are
labelled `UNVALIDATED`, they are excluded from coverage, and **they do not vote
on the verdict**. A pile of unvalidated lint rules must not be able to wear this
tool's verdict.

Check ids are namespaced (`x:gsm8k-extras:X1`), so a finding's provenance is
never ambiguous and a third-party id can never collide with a core one. An id
that tries is refused at load time.

### Rail two: adapters

The [evidence contract](#the-evidence-contract) already made this possible: the
battery consumes the record and manifest schemas, so anything that can write
conforming evidence is auditable. `dinostomp import` is the reference adapter,
not a privileged path.

That is the point of the rail. Rather than this project maintaining
lm-eval-harness, Inspect and promptfoo adapters forever, each ecosystem's own
users can own theirs, and the maintenance surface here stays flat while the
compatibility surface grows. An adapter's entry fee is a **golden-file trial**:
a real log from that harness in, conforming records out, and every field
accounted for, including the ones it cannot supply.

### The verdict names its inputs

```
MECHANICALLY SOUND: no integrity findings, full coverage (29 of 29 ran; 36 n/a of 65 declared)
  extension: gsm8k-extras 0.2.1 (a41f9c22b7e05d18), 3 check(s), validated
```

Every loaded extension is named, versioned and hashed in the report, exactly as
the engine is. A `SOUND` produced with extensions loaded is a precise claim
about a specific set of code, or it is not a claim at all.

**A security note that follows from this project's own stance.** Pod-local
Python is not imported without `--trust-code`, and an installed extension *is*
imported Python with the same powers. The difference is consent: installing a
package is a deliberate act, while opening a stranger's pod is not, which is why
extensions are not gated the same way. That difference justifies loading them.
It does not justify hiding them, which is why every one appears in the report
with its hash. A verdict must never silently depend on code the reader does not
know is there.

## Roadmap

Ordered by dependency, and split by whether it lands before or after the first
public release.

**Before publishing.** Nothing on this list is required to publish; the
architecture below is.

- GitHub / HF export of a pod plus its receipts.
- Pairwise judging: position-swap stomping needs a pairwise judge shape, which
  the pointwise rail does not have.

**After publishing.** Deliberately after, because each one changes what the tool
claims rather than how well it does what it already claims.

- ~~A sandboxed agent harness, as a MOUNT.~~ **Shipped in v0.42.0 as the
  MEDIATED rail, and renamed on purpose.** See "The mediated rail" below: it
  does what this roadmap entry asked for, and it is not called a sandbox
  because in-process Python is not a security boundary and saying otherwise
  would be the flattering claim this whole document argues against.
- Local UI (Astro + SQLite index over files; files stay the source of truth).
- Importers for other runners' logs, on the contract above.

## The mediated rail: a trace the harness observed

Everything in the section below this one is the SELF-REPORTED rail. The target
writes its own trajectory, and `targets.py` has always said what that means: an
agent that omits a call from its trace cannot be caught by reading the trace.
Six checks read that trace, so for those pods all six read testimony.

The mediated rail moves the tools out of the agent and into the harness:

```yaml
tools:                                # the HARNESS holds these
  retrieve: tools.py:retrieve
  shell: tools.py:shell
models:
  - {provider: mediated, model: grounded, entrypoint: agent.py:answer}
trajectory:
  required_tools: [retrieve]
  forbidden_tools: [shell]            # DENIED at call time, not audited after
  max_steps: 6
```

```python
# agent.py. Three arguments, and the signature is the tell: `run(item, ctx)` is
# the self-reported rail, `answer(item, tools, ctx)` is this one.
def answer(item, tools, ctx):
    hit = tools.retrieve(key=item["topic"])     # recorded by the harness
    return extract(hit)
```

An agent on this rail **cannot** return a `trajectory`. Doing so stops the run,
rather than being ignored: steps the harness never saw are unverifiable evidence
sitting in a record that claims to be a log.

### What it buys, exactly

- **The trace is observed.** T1, T2, T3 and T6 stop reading testimony. The
  manifest records `trajectory_source`, and **T8** prints which kind of trace the
  T-checks read, so a report is legible without knowing the provider strings.
- **Policy is enforced when the agent reaches for the tool**, not noticed
  afterwards. The attempt is recorded either way: a denial that left no trace
  would make a thwarted agent look like a well-behaved one.
- **Evidence can be withheld**, which is the part that mattered.

### The ablation probe, and why D-020 needed it

T4 asks whether a passing answer APPEARS in the trace's tool results. That is
co-occurrence. An agent that answers from memory and retrieves the right topic
afterwards is 100% causally ungrounded and T4 reported **16%** on a live pod
([D-020](FINDINGS.md#d-020)). Reading the trace harder cannot fix it, because a
trace records what was FETCHED and not what was READ.

`--probe ablate` asks the counterfactual instead. Same agent, same items, same
calls, every RESULT replaced by a marker. **T7** compares the two arms: an answer
that comes out identical did not depend on the evidence. Not "might not have":
did not, because the only thing that differed was whether the agent could see
what came back.

On [examples/mediated](examples/mediated/), where one of three agents answers
from memory first and retrieves anyway:

```
[ok]   answer-grounding         0 of 3 target(s) pass items whose answer does not APPEAR ...
[warn] answer-grounding-causal  1 of 3 agent(s) answer identically with their evidence withheld
         - oneshot: 18 of 18 passing answer(s) (100%) are unchanged when the evidence is withheld
```

T4 sees nothing. T7 sees all of it. That gap is the reason the rail exists.

**T7's own limits, stated because they are real.** It needs a deterministic
agent or repeats: a nondeterministic agent differs between arms by chance, which
makes T7 UNDERSTATE ungroundedness, in the same one-sided direction as T4. And
an identical answer proves the evidence made no difference to THAT answer, not
that the agent has no way to use evidence at all.

### Two rails, and what each one actually buys

Mediation alone buys **trace integrity**. It does not buy **policy integrity**,
and v0.42.0 said it did, which was wrong. In-process, `Tools` keeps the live
callables on an attribute:

```python
tools._registry["shell"](cmd="rm -rf /")     # runs. policy never consulted.
                                             # and the trajectory stays EMPTY.
```

That is [D-029](FINDINGS.md#d-029). It is not patched, because hiding a registry
in Python is theatre: a closure is reachable through `__closure__`, and shipping
"harder to reach" as though it were "prevented" is the move this whole document
argues against. What changed is the claim.

`isolation: subprocess` is what buys policy integrity:

```yaml
isolation: {mode: subprocess, timeout_s: 60}
```

The agent runs in a child; the tools stay in the parent. Every row below is a
test with an in-process CONTROL, because "the key was not visible" could
otherwise just mean nobody set one ([N-010](FINDINGS.md#n-010)):

| an agent that tries to | sandboxed | in-process |
|---|---|---|
| read `OPENROUTER_API_KEY` | `NO-KEY-VISIBLE` | `sk-do-not-leak-this` |
| call the forbidden tool via `_registry` | `NOTHING-TO-REACH` | `ran rm -rf /` |
| open a socket | denied | (opens) |
| forge a `{"op":"done"}` line on stdout | ignored | n/a |
| hang forever | killed at `timeout_s` | hangs the run |
| **re-exec a fresh interpreter** | **works** | works |
| **read the tool file with `open()`** | **works** | works |

The last two rows are asserted as PASSING tests. Strengthening the boundary
later breaks them and forces this table to be rewritten deliberately.

**Still not a sandbox in the security sense.** `subprocess` is CONTAINMENT, not
confinement: it defends a RUN against an agent that is careless, buggy or quietly
overreaching, and it does not defend a MACHINE against a hostile one. The
filesystem is not confined and the network denial is defeatable. Untrusted agent
code belongs in a VM, and no amount of Python here changes that.

Cost: roughly 130ms per item of process startup, so `inprocess` remains the
default and `subprocess` is a choice you make when the agent is not yours.

## Agents get stomped too

An examinee does not have to be a model completion. Point a spec at a pod-local Python callable and it mounts on the same rail everything else uses, so a RAG pipeline, a tool-using agent, or a whole workflow gets the budget cap, the streamed ledger, the witness gate, the drift boundary, and the entire battery without a single new concept:

```yaml
models:
  - {provider: python, model: agent-grounded, entrypoint: agent.py:run}
trajectory:                          # declarative policy, judge-free
  required_tools: [retrieve]
  forbidden_tools: [shell.exec, http.get, write_file]
  max_steps: 6
```

```python
# agent.py, inside the pod. ctx carries model, seed, and params.
def run(item, ctx):
    hits = retrieve(item["input"])
    return {"output": answer(hits),
            "trajectory": [{"tool": "retrieve", "args": {...}, "result": hits[0], "ok": True}]}
```

[examples/agent](examples/agent/) runs four configurations of one retrieval agent over 26 capital-city questions, offline and free, and is the highest-coverage pod in the repo:

```bash
dinostomp run   examples/agent/eval.yaml
dinostomp run   examples/agent/eval.yaml --probe blind
dinostomp stomp examples/agent/eval.yaml
```

```
agent-capitals | agent-grounded | complete | acc 0.923 [0.76, 0.98] on 26 checkable (0 uncheckable excluded) | $0.0000
agent-capitals | agent-grounded | complete | acc 0.923 [0.76, 0.98] on 26 checkable (0 uncheckable excluded) | $0.0000
...
  [ok]   passing answers are grounded in tool evidence   0 of 4 target(s) pass items their own evidence does not support (2 such answer(s) in total)
           - cap-santiago (agent-lazy): passed, but its answer appears in no tool result
           - cap-tunis (agent-lazy): passed, but its answer appears in no tool result
INCOMPLETE: no failures, but only 38 of 42 checks ran (23 n/a of 65 declared).
```

`agent-lazy` is the pod's teaching case. It scores a perfect 100%, it calls the required tool on every single item, and every policy check passes it, because it really does retrieve. What T4 notices is that two of its correct answers appear in no retrieved evidence at all: it answered from memory and retrieved afterwards. That is the Clever Hans of tool use, and it is judge-free, since "does the answer occur in the tool output" is a fact rather than an opinion. Note also what the check did NOT do: two ungrounded answers out of twenty-six is under the threshold, so T4 passed, printed both receipts, and left the call to you.

**The trust boundary, stated plainly and repeated in the code:** a trajectory is SELF-REPORTED by the target. These checks verify the record, not the execution. An agent that simply omits a tool call from its trace cannot be caught by reading the trace, and no amount of parsing effort changes that. T5 is the one instrument aimed at the omission itself, and it works by comparison rather than inspection: a target whose trajectories are far thinner than its fleet's gets flagged, exactly the way R12 flags a model that escapes the scorer. Treat a trajectory as an examinee's testimony that other examinees can contradict, never as an execution log.

A pod that declares typed claims, runs a real provider, ships a blind probe, uses a target, and grades with a judge reaches the full 50 of 50; the agent example's 9 n/a are the five choice-only checks, P6, and the three judge checks.

## Who evaluated your evaluator?

An LLM judge is a scorer, so it goes through the witness gate like every other scorer: show the cases it must reject, or it grades nothing. But a judge is also a model, which means it has model failure modes, and none of them are visible in the number it produces. So a judge has to earn the right to judge:

```bash
dinostomp run examples/judge/eval.yaml --probe judge
```

```
judge-capitals | judge-control | complete | JUDGE PROBE | agrees with 100% of 16 known case(s), 128 grading(s) over 6 perturbation(s) | $0.0000
```

```
  [ok]   the judge agrees with cases whose answer is known   the judge agrees with 100% of 16 case(s) whose verdict is known by construction (0 wrong answer(s) passed)
  [ok]   the judge is invariant to content-free perturbations   0 of 6 content-free perturbation(s) change the judge's mind across 96 regraded case(s)
  [ok]   the judge agrees with itself on identical input   the judge contradicts itself on 0 of 16 case(s) (0%) regraded on byte-identical input
```

The probe grades cases whose correct verdict is known **by construction**, which is what removes the infinite regress: an answer that IS the reference answer must pass, and an answer that is a different item's reference answer must fail. No second judge required. Then it regrades every case under perturbations that change no meaning: padding, stated confidence, an appeal to authority, a markdown fence, whitespace, politeness. Every flip is a named bias reported with the case that caused it, and **fail → pass flips are called out separately as INFLATING**, because that is the direction that manufactures accuracy. J3 grades the same case twice on byte-identical input, since a judge that contradicts itself is not measuring a property of the response at all.

Two things fall out of the judge being a model:

**A judge is not free.** Its calls are priced against the same rate table, counted against the same `budget_usd` cap, and itemised per record as `judge_cost_usd`. A judge model with no known price refuses to run, on the grounds that a grader you cannot cap is not free, it is just unmeasured.

**A judge is nondeterministic and paid, and `stomp` is neither.** Re-scoring a recorded verdict normally means re-running the scorer, which for a judge would mean spending money during a lint and hoping the answer comes back the same. So scoring is split: the model call (paid, unrepeatable) and the parse of the judge's text into a verdict (deterministic). Records keep the judge's **verbatim response**, and R8 re-derives every verdict from that text offline. Forge a verdict against the judge's own words and R8 gates; strip the response and the verdict has no recorded basis, which gates too. What this cannot prove, and the report says so, is whether the judge would rule the same way if asked again. That is a reproducibility limit, named rather than papered over.

The bundled [examples/judge](examples/judge/) pod runs four bots that know identical facts and differ only in house style (bare, wrapped, hedged, chatty). Exact match would rank them by punctuation; the judge is there to see past the wrapper, and J1-J3 are what establish that this particular judge does.

**Self-preference, and why it needs two judges.** Whether a judge favours its own model family is the famous failure mode. The one-judge proxy (does the judge override strict matching more often for one model) is confounded by formatting: a model that wraps its answers fails strict matching even when it is right, collecting overrides for a reason that has nothing to do with favouritism. dinostomp refused to ship that, and said so.

Two judges make it measurable. Declare a `cross_judge` from a different family and run `dinostomp run <spec> --probe crossjudge`: it re-grades the SAME recorded outputs, so a model's formatting applies to both judges and cancels. What survives is the difference of differences, which is what **J4** reads. On the trial fixture the arithmetic is visible: with a fair judge both models show a delta of exactly `0.000`, and with a favouring one only its own family moves, to `+0.29`.

What J4 still cannot do is prove WHY. A family gap may be favouritism, or a family style one judge genuinely reads better, and the finding names both readings rather than picking one.

Edit the spec, the data, the scorer, the agent, or the judge after a run and stomp again:

```
  [FAIL] runs match the spec, data, and scorer on disk (no drift)  1 of 6 run(s) no longer match ...
           - 20260808_..._dry-alpha_n24_s42.jsonl: data changed since this run
BROKEN: 1 gated finding(s) (29 of 29 ran; 36 n/a of 65 declared)
```

Exit codes for `run`: `0` complete, `1` gated (witnesses failed, nothing ran), `2` cannot run (invalid spec or data, unpriced model, missing key), `3` stopped early (budget, provider, or scorer; partial on disk, resume with `--resume <run file>`). For `stomp` and `report`: `0` clean or ok, `1` broken, `2` cannot stomp, `4` incomplete. Incomplete is nonzero **by default**: an unattended pipeline must never accept thin coverage because someone forgot a flag; `--allow-incomplete` is the explicit, loudly-printed escape hatch.

From Python:

```python
from dinostomp import load_spec

spec, issues = load_spec("examples/smoke/eval.yaml")
for issue in issues:
    print(issue.loc, issue.message)   # empty: the example is green
```
