# 🦖 stomp report: eval.yaml

**INCOMPLETE**: no failures, but only 18 of 28 checks ran (18 of 28 ran; 33 n/a of 61 declared). Not a clean bill of health.

> All runs used the offline dry provider; results exercise the benchmark, not any real model.

## Results

> These numbers come from an eval with **incomplete coverage**. They describe what the runs contain; whether they can be published is decided under Checks.

| model | provider | records | checkable | judgeable | accuracy | 95% CI | passes | fails | out tok | spend |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| dry-strong | dry | 6 | 6 | 100% | 100.0% | [0.610, 1.000] | 6 | 0 | 6 | $0.0000 |

Accuracy is ON CHECKABLE output: `judgeable` is the share the scorer reached a verdict on at all, and 80% accurate on 60%-judgeable output is not 80% accurate.

**1 model(s) x 6 item(s)**, mean 100.0%.

6 item(s) every model passed and 0 every model failed: 100% of the set separated nobody in this fleet.

At 6 items an UNPAIRED comparison resolves gaps down to about 81%; smaller differences between the models above are not distinguishable from sampling noise by that test.

<details><summary>Item difficulty: all 6 item(s), hardest first</summary>

| item | target | p | discrimination | missed by | most common wrong answer |
|---|---|---:|---:|---|---|
| a1 | 57 | 100% | - | - | - |
| a2 | 62 | 100% | - | - | - |
| a3 | 90 | 100% | - | - | - |
| a4 | 91 | 100% | - | - | - |
| a5 | 72 | 100% | - | - | - |
| a6 | 80 | 100% | - | - | - |

`p` is the share of the fleet that answered correctly and `discrimination` is the point-biserial with fleet skill. Both DESCRIBE; a hard item is not a defect. A negative discrimination is what P2 examines.

</details>

## Entitled claims

**None.** The verdict is `incomplete`; this eval is not currently entitled to publish claims.

## Checks

### Invariants (deterministic, gating)

Facts, not heuristics: a failure here means something is mechanically wrong (a duplicate exists, a hash changed, a number does not re-derive) and it breaks the verdict.

| | check | witnesses | detail |
|---|---|---:|---|
| ok | questions are unique | 6 | 0 duplicated question(s) among 6 |
| ok | no answer leaks into its own question | 6 | 0 of 6 free-form item(s) leak their answer |
| n/a | no option offered twice in one item | 0 | no multiple-choice items in this dataset |
| n/a | every target is among its choices | 0 | no multiple-choice items in this dataset |
| ok | no identical question with contradictory targets | 6 | 0 question(s) appear with conflicting targets |
| n/a | every referenced asset resolves and still hashes the same | 0 | no item carries an `input_ref`; nothing points at a file |
| n/a | no asset's own path gives away its label | 0 | no item carries an `input_ref`; nothing points at a file |
| n/a | no asset appears in two splits | 0 | no item carries an `input_ref`; nothing points at a file |
| n/a | every typed claim's evidence requirements hold | 0 | no typed claims declared |
| ok | runs match the spec, data, and scorer on disk (no drift) | 1 | 0 of 1 run(s) no longer match the spec, data, or scorer on disk |
| ok | the witness gate replays clean | 6 | replayed 5 witness(es): 5 behaved; 1 run manifest(s) checked |
| ok | ledger spend agrees with the manifest and the spec cap | 1 | 0 money discrepanc(ies) across 1 run(s) |
| ok | every run record is schema-valid, unique, and its manifest's own | 6 | 0 integrity problem(s) across 6 record(s) |
| ok | truncated outputs are never credited | 6 | 0 truncated output(s) scored as pass; a cut-off response can still have stated its answer, so read these before raising max_tokens and re-running |
| ok | recorded verdicts re-score identically | 6 | 0 of 6 recorded verdict(s) do not reproduce under the current scorer |
| ok | summaries match their run records | 1 | 0 summary discrepanc(ies) across 1 run(s) |
| ok | records cover exactly the seeded selection | 1 | 0 of 1 run(s) do not cover their seeded selection |
| ok | every model produced something scoreable | 1 | 0 of 1 model(s) produced nothing scoreable |
| n/a | no forbidden tool is called | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| n/a | every required tool is actually called | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| n/a | trajectories are well-formed | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| skip | every model was asked the same items | 0 | only 1 model(s) on disk; run a fleet of 4+ to unlock psychometrics |

### Diagnostics (statistical, advisory)

Threshold-based signals: they warn, expose their underlying values, and can have legitimate explanations. A warning is evidence of possible trouble, never a proof of invalidity.

| | check | witnesses | detail |
|---|---|---:|---|
| n/a | gold answer does not favour an option position | 0 | no multiple-choice items in this dataset |
| n/a | gold answer is not systematically the longest option | 0 | no multiple-choice items in this dataset |
| ok | a contamination canary travels with the data | 1 | canary present (dinostomp canary DO NOT TRAIN 7091a9242d...) |
| n/a | no surface feature predicts the gold answer | 0 | no multiple-choice items in this dataset |
| n/a | no model reproduces the contamination canary | 0 | regurgitation probes need a hosted model; this pod's runs are all local |
| n/a | no item already appears in a reference dataset | 0 | no reference dataset supplied; pass --against <file> to compare these items against a corpus you have. This never checks training data, and cannot. |
| n/a | no near-duplicate assets | 0 | no item carries an `input_ref`; nothing points at a file |
| ok | witnesses kill the mutant scorers | 5 | 0 of 5 applicable mutant scorer(s) survive the witness suite |
| ok | uncheckable rate is sane | 6 | 0% of 6 record(s) are uncheckable |
| skip | accuracy is distinguishable from guessing | 0 | no model has 20+ checkable records (6 in total) |
| ok | runs cover the spec's declared scope, nothing foreign | 1 | 0 run(s) outside the spec's declared scope |
| skip | no model selectively escapes the scorer | 0 | needs at least 2 models to compare uncheckable rates |
| n/a | the eval is not solvable blind | 0 | blind probes need a real provider; this pod's runs are all dry |
| ok | no model collapses onto one answer | 1 | 0 of 1 model(s) answer with one response far more often than any target warrants |
| n/a | each model beats its own blind baseline | 0 | blind probes need a real provider; this pod's runs are all dry |
| skip | failed answers do not contain the reference | 0 | no model has 5+ failed records to inspect |
| n/a | billed output tokens match the recorded text | 0 | no model produced 20+ answers of at least 40 characters; short-answer evals cannot be billed against reliably |
| ok | the runs were produced by this engine | 1 | 0 of 1 run(s) were produced by a different engine than the one auditing them (now 9e3b8f138082fd93); re-run to get numbers this report can stand behind |
| n/a | repeated items reached a verdict | 0 | no run on disk repeats an item; a single pass per item cannot tie |
| n/a | passing answers are grounded in tool evidence | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| n/a | no model under-reports its trajectory | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| n/a | tool calls are not redundant | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| n/a | passing answers CHANGE when their evidence is withheld | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| n/a | the trajectory was observed, not self-reported | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| n/a | the judge agrees with cases whose answer is known | 0 | this eval does not score with a judge |
| n/a | the judge is invariant to content-free perturbations | 0 | this eval does not score with a judge |
| n/a | the judge agrees with itself on identical input | 0 | this eval does not score with a judge |
| n/a | the judge does not favour its own family | 0 | this eval does not score with a judge |
| skip | fleet score totals are reliable (KR-20) | 0 | only 1 model(s) on disk; run a fleet of 4+ to unlock psychometrics |
| skip | no item anti-correlates with fleet skill | 0 | only 1 model(s) on disk; run a fleet of 4+ to unlock psychometrics |
| skip | dead-weight items stay a minority | 0 | only 1 model(s) on disk; run a fleet of 4+ to unlock psychometrics |
| skip | no unanimous identical wrong answers | 0 | only 1 model(s) on disk; run a fleet of 4+ to unlock psychometrics |
| n/a | entitled ordering claims are separated beyond sampling noise | 0 | no entitled claim asserts a model ordering |
| skip | the fleet is not pinned at a ceiling or floor | 0 | only 1 model(s) on disk; run a fleet of 4+ to unlock psychometrics |
| skip | the eval separates the fleet (dynamic range) | 0 | only 1 model(s) on disk; run a fleet of 4+ to unlock psychometrics |
| n/a | answers survive re-ordering the options | 0 | presentation-order probes need a real provider; this pod's runs are all local |
| n/a | the number survives changing the seed | 0 | the spec declares no extra seeds; a single seed cannot show its own spread (run.seeds is how you ask) |
| n/a | the number survives re-phrasing the instruction | 0 | instruction-framing probes need runs on disk |
| n/a | the fleet ORDERING survives re-phrasing the instruction | 0 | instruction-framing probes need runs on disk |

### Receipts

<details><summary>[ok] witnesses kill the mutant scorers</summary>

- evidence: `{"killed": ["always-pass", "always-fail", "substring-lenient", "prefix-lenient", "negation-blind"], "not_applicable": ["case-blind", "space-blind", "uncheckable-credit"]}`

</details>
<details><summary>[ok] uncheckable rate is sane</summary>

- evidence: `{"rate": 0.0}`

</details>
<details><summary>[ok] the runs were produced by this engine</summary>

- evidence: `{"engines": {"9e3b8f138082fd93": 1}}`

</details>

## Runs

| run file | model | reported as | provider | dry | seed | records | uncheckable |
|---|---|---|---|---|---:|---:|---:|
| 20260810_094134_smoke-arith_dry-strong_n6_s42.jsonl | dry-strong | (same) | dry | yes | 42 | 6 | 0 |

## Provenance

- tool: dinostomp 0.57.0
- statistical power: at n=6 items, an UNPAIRED comparison (worst case p=0.5) resolves gaps down to ~81% accuracy (80% power, two-sided alpha 0.05); the paired bootstrap behind P6/C1 resolves smaller gaps when model errors overlap
- spec_sha256: `fca7dbcadb153b3133b04982dca162ac942495b32d1738505fb5f91e560219a9`
- data_sha256: `0b56432c320054896104625b1a31ce453976ad63564baa96c5571ce414c9b623`
- thresholds: all defaults
- reproducibility tiers, stated honestly: local inputs hash-pinned (spec, data, scorer); requests reproducible given each manifest's environment envelope; hosted-model immutability UNKNOWN unless the provider exposes a pinned revision (the runs table records what each provider claims answered)
- raw report: [STOMP.json](STOMP.json) (both files omit volatile fields, so an unchanged pod re-reports to identical bytes; run manifests carry the timestamps)
