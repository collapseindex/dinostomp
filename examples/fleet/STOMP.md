# 🦖 stomp report: eval.yaml

**OK**: no failures, 1 warning(s) (31 of 31 ran; 38 n/a of 69 declared)

> All runs used the offline dry provider; results exercise the benchmark, not any real model.

## Results

| model | provider | records | checkable | judgeable | accuracy | 95% CI | passes | fails | out tok | spend |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| dry-alpha | dry | 24 | 24 | 100% | 100.0% | [0.862, 1.000] | 24 | 0 | 24 | $0.0000 |
| dry-bravo | dry | 24 | 24 | 100% | 75.0% | [0.551, 0.880] | 18 | 6 | 24 | $0.0000 |
| dry-charlie | dry | 24 | 24 | 100% | 37.5% | [0.212, 0.573] | 9 | 15 | 24 | $0.0000 |
| dry-delta | dry | 24 | 24 | 100% | 100.0% | [0.862, 1.000] | 24 | 0 | 24 | $0.0000 |
| dry-echo | dry | 24 | 24 | 100% | 50.0% | [0.314, 0.686] | 12 | 12 | 24 | $0.0000 |
| dry-foxtrot | dry | 24 | 24 | 100% | 54.2% | [0.351, 0.721] | 13 | 11 | 24 | $0.0000 |

Accuracy is ON CHECKABLE output: `judgeable` is the share the scorer reached a verdict on at all, and 80% accurate on 60%-judgeable output is not 80% accurate.

**6 model(s) x 24 item(s)**, mean 69.4%, spanning 37.5% to 100.0% (62% spread), KR-20 0.94.

9 item(s) every model passed and 0 every model failed: 38% of the set separated nobody in this fleet.

At 24 items an UNPAIRED comparison resolves gaps down to about 40%; smaller differences between the models above are not distinguishable from sampling noise by that test.

<details><summary>Item difficulty: all 24 item(s), hardest first</summary>

| item | target | p | discrimination | missed by | most common wrong answer |
|---|---|---:|---:|---|---|
| a13 | 27 | 33% | +0.87 | dry-bravo, dry-charlie, dry-echo, dry-foxtrot | 28 |
| a22 | 45 | 33% | +0.87 | dry-bravo, dry-charlie, dry-echo, dry-foxtrot | 47 |
| a25 | 51 | 33% | +0.87 | dry-bravo, dry-charlie, dry-echo, dry-foxtrot | 54 |
| a30 | 61 | 33% | +0.87 | dry-bravo, dry-charlie, dry-echo, dry-foxtrot | 66 |
| a31 | 63 | 33% | +0.87 | dry-bravo, dry-charlie, dry-echo, dry-foxtrot | 66 |
| a33 | 67 | 33% | +0.87 | dry-bravo, dry-charlie, dry-echo, dry-foxtrot | 71 |
| a14 | 29 | 50% | +0.90 | dry-charlie, dry-echo, dry-foxtrot | 36 |
| a18 | 37 | 50% | +0.90 | dry-charlie, dry-echo, dry-foxtrot | 42 |
| a19 | 39 | 50% | +0.90 | dry-charlie, dry-echo, dry-foxtrot | 44 |
| a20 | 41 | 50% | +0.90 | dry-charlie, dry-echo, dry-foxtrot | 43 |
| a29 | 59 | 50% | +0.90 | dry-charlie, dry-echo, dry-foxtrot | 61 |
| a26 | 53 | 67% | +0.71 | dry-charlie, dry-echo | 58 |
| a10 | 21 | 83% | +0.54 | dry-charlie | 28 |
| a12 | 25 | 83% | +0.54 | dry-charlie | 29 |
| a15 | 31 | 83% | +0.54 | dry-charlie | 33 |
| a11 | 23 | 100% | - | - | - |
| a16 | 33 | 100% | - | - | - |
| a17 | 35 | 100% | - | - | - |
| a21 | 43 | 100% | - | - | - |
| a23 | 47 | 100% | - | - | - |
| a24 | 49 | 100% | - | - | - |
| a27 | 55 | 100% | - | - | - |
| a28 | 57 | 100% | - | - | - |
| a32 | 65 | 100% | - | - | - |

`p` is the share of the fleet that answered correctly and `discrimination` is the point-biserial with fleet skill. Both DESCRIBE; a hard item is not a defect. A negative discrimination is what P2 examines.

</details>

## Entitled claims

This result is entitled to claim:

- Exact-match accuracy with a 95% interval on these 24 addition items, bare-number format, per model.

Typed claims, compiled to evidence requirements and checked off:

- **SUPPORTED**: accuracy of dry-alpha is at least 80% (95% confidence)
  - [x] complete run on disk: dry-alpha: complete
  - [x] enough checkable evidence: 24 checkable unit(s); need 20
  - [x] interval lower bound clears the declared minimum: lower bound 86.2% vs declared minimum 80%
- **SUPPORTED**: dry-alpha beats dry-charlie by at least 20% (95% confidence)
  - [x] complete runs for both models: dry-alpha: ok; dry-charlie: ok
  - [x] paired observations: 24 common item(s); need 20
  - [x] paired bootstrap clears min_effect at the declared confidence: gap >= 20% in 100% of 400 resamples; need 95%

## Checks

### Invariants (deterministic, gating)

Facts, not heuristics: a failure here means something is mechanically wrong (a duplicate exists, a hash changed, a number does not re-derive) and it breaks the verdict.

| | check | witnesses | detail |
|---|---|---:|---|
| ok | questions are unique | 24 | 0 duplicated question(s) among 24 |
| ok | no answer leaks into its own question | 24 | 0 of 24 item(s) leak their answer into the question |
| n/a | no option offered twice in one item | 0 | no multiple-choice items in this dataset |
| n/a | every target is among its choices | 0 | no multiple-choice items in this dataset |
| ok | no identical question with contradictory targets | 24 | 0 question(s) appear with conflicting targets |
| n/a | every referenced asset resolves and still hashes the same | 0 | no item carries an `input_ref`; nothing points at a file |
| n/a | no asset's own path gives away its label | 0 | no item carries an `input_ref`; nothing points at a file |
| n/a | no asset appears in two splits | 0 | no item carries an `input_ref`; nothing points at a file |
| n/a | a graded scorer witnesses its gradation | 0 | this scorer does not emit intermediate partial credit, so there is no gradation to witness |
| ok | every typed claim's evidence requirements hold | 6 | 2 of 2 typed claim(s) supported across 6 evidence requirement(s) (no multiplicity correction across 2 claims) |
| ok | runs match the spec, data, and scorer on disk (no drift) | 6 | 0 of 6 run(s) no longer match the spec, data, or scorer on disk |
| ok | the witness gate replays clean | 11 | replayed 5 witness(es): 5 behaved; 6 run manifest(s) checked |
| ok | ledger spend agrees with the manifest and the spec cap | 6 | 0 money discrepanc(ies) across 6 run(s) |
| ok | every run record is schema-valid, unique, and its manifest's own | 144 | 0 integrity problem(s) across 144 record(s) |
| ok | truncated outputs are never credited | 144 | 0 truncated output(s) scored as pass; a cut-off response can still have stated its answer, so read these before raising max_tokens and re-running |
| ok | recorded verdicts re-score identically | 144 | 0 of 144 recorded verdict(s) do not reproduce under the current scorer |
| ok | summaries match their run records | 6 | 0 summary discrepanc(ies) across 6 run(s) |
| ok | records cover exactly the seeded selection | 6 | 0 of 6 run(s) do not cover their seeded selection |
| ok | every model produced something scoreable | 6 | 0 of 6 model(s) produced nothing scoreable |
| n/a | graded scores stay in range | 0 | no record carries a graded value |
| n/a | no forbidden tool is called | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| n/a | every required tool is actually called | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| n/a | trajectories are well-formed | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| ok | every model was asked the same items | 6 | 0 of 6 model(s) were asked a different item set |

### Diagnostics (statistical, advisory)

Threshold-based signals: they warn, expose their underlying values, and can have legitimate explanations. A warning is evidence of possible trouble, never a proof of invalidity.

| | check | witnesses | detail |
|---|---|---:|---|
| n/a | gold answer does not favour an option position | 0 | no multiple-choice items in this dataset |
| n/a | gold answer is not systematically the longest option | 0 | no multiple-choice items in this dataset |
| ok | a contamination canary travels with the data | 1 | canary present (dinostomp canary DO NOT TRAIN 4e3844fb6f...) |
| n/a | no surface feature predicts the gold answer | 0 | no multiple-choice items in this dataset |
| n/a | no model reproduces the contamination canary | 0 | regurgitation probes need a hosted model; this pod's runs are all local |
| n/a | no item already appears in a reference dataset | 0 | no reference dataset supplied; pass --against <file> to compare these items against a corpus you have. This never checks training data, and cannot. |
| n/a | no near-duplicate assets | 0 | no item carries an `input_ref`; nothing points at a file |
| n/a | the eval is not authored in a circle | 0 | no provenance declared, so authorship is not described. Declaring who wrote the items, keys, scorer, and witnesses lets this surface a model sitting on both sides of a loop (e.g. keying its own questions) |
| n/a | no single column all but determines the target | 0 | an eval pod's items are questions and answers, not a feature table; the single-column leak scan is for a raw tabular dataset audit |
| n/a | no two options are the same number written differently | 0 | no multiple-choice items in this dataset |
| ok | no two items are the same question in different encodings | 24 | 0 group(s) of items are the same question in different encodings |
| ok | witnesses kill the mutant scorers | 5 | 0 of 5 applicable mutant scorer(s) survive the witness suite |
| n/a | a correct answer survives its surface form | 0 | this scorer compares exactly rather than extracting, so surface-form robustness is not a property it claims |
| ok | uncheckable rate is sane | 144 | 0% of 144 record(s) are uncheckable |
| ok | accuracy is distinguishable from guessing | 6 | 0 of 6 model(s) score no better than guessing; fleet spans 38% to 100% vs chance ~4% (modal target floor) |
| ok | runs cover the spec's declared scope, nothing foreign | 6 | 0 run(s) outside the spec's declared scope |
| ok | no model selectively escapes the scorer | 6 | 0 of 6 model(s) escape the scorer more than the fleet does |
| n/a | the eval is not solvable blind | 0 | blind probes need a real provider; this pod's runs are all dry |
| ok | no model collapses onto one answer | 6 | 0 of 6 model(s) answer with one response far more often than any target warrants |
| n/a | each model beats its own blind baseline | 0 | blind probes need a real provider; this pod's runs are all dry |
| ok | failed answers do not contain the reference | 4 | 0 of 4 model(s) are failed on answers that contain the reference; the scorer may be grading format, not correctness |
| n/a | billed output tokens match the recorded text | 0 | no model produced 20+ answers of at least 40 characters; short-answer evals cannot be billed against reliably |
| warn | the runs were produced by this engine | 6 | 6 of 6 run(s) were produced by a different engine than the one auditing them (now 552065c84ca60d98); re-run to get numbers this report can stand behind |
| n/a | repeated items reached a verdict | 0 | no run on disk repeats an item; a single pass per item cannot tie |
| ok | no failed answer numerically equals its target | 44 | 0 of 44 numeric-target failure(s) equal their target as a number; the scorer may be rejecting a correct value in the wrong form |
| n/a | passing answers are grounded in tool evidence | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| n/a | no model under-reports its trajectory | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| n/a | tool calls are not redundant | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| n/a | passing answers CHANGE when their evidence is withheld | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| n/a | the trajectory was observed, not self-reported | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| n/a | the judge agrees with cases whose answer is known | 0 | this eval does not score with a judge |
| n/a | the judge is invariant to content-free perturbations | 0 | this eval does not score with a judge |
| n/a | the judge agrees with itself on identical input | 0 | this eval does not score with a judge |
| n/a | the judge does not favour its own family | 0 | this eval does not score with a judge |
| ok | fleet score totals are reliable (KR-20) | 144 | KR-20 0.94 across 6 models x 24 items; small fleet (6 examinees), treat as a noisy estimate |
| ok | no item anti-correlates with fleet skill | 24 | 0 item(s) that strong models miss and weak models hit, against 0 expected by chance at this fleet size; candidate key errors; at 6 examinees this check has little power, so a quiet result is NOT evidence of a clean answer key |
| ok | dead-weight items stay a minority | 24 | 38% of 24 item(s) separate nobody (9 all-right, 0 all-wrong); 8% would be dead at 6 examinees even with no difficulty structure, so part of this is fleet size |
| ok | no unanimous identical wrong answers | 24 | 0 item(s) where the whole fleet gave one identical wrong answer; candidate key errors |
| n/a | entitled ordering claims are separated beyond sampling noise | 0 | no entitled claim asserts a model ordering |
| ok | the fleet is not pinned at a ceiling or floor | 6 | fleet accuracy spans 38% to 100% on 24 item(s) |
| ok | the eval separates the fleet (dynamic range) | 6 | fleet spread 62% across 6 model(s) on 24 item(s) |
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
<details><summary>[ok] accuracy is distinguishable from guessing</summary>

- evidence: `{"chance_floor": 0.0417, "modal": 0.0417, "modal_target": "21", "per_model_accuracy": {"dry-alpha": 1.0, "dry-bravo": 0.75, "dry-charlie": 0.375, "dry-delta": 1.0, "dry-echo": 0.5, "dry-foxtrot": 0.5417}, "uniform": 0.0}`

</details>
<details><summary>[ok] no model selectively escapes the scorer</summary>

- evidence: `{"rates": {"dry-alpha": 0.0, "dry-bravo": 0.0, "dry-charlie": 0.0, "dry-delta": 0.0, "dry-echo": 0.0, "dry-foxtrot": 0.0}}`

</details>
<details><summary>[warn] the runs were produced by this engine</summary>

- engine 050e2f343915e1b9: dry-alpha seed 42 (tool 0.57.1), dry-bravo seed 42 (tool 0.57.1), dry-charlie seed 42 (tool 0.57.1) and 3 more
- evidence: `{"engines": {"050e2f343915e1b9": 6}}`

</details>
<details><summary>[ok] fleet score totals are reliable (KR-20)</summary>

- evidence: `{"excluded_collapsed": [], "kr20": 0.9443, "n_examinees": 6}`

</details>
<details><summary>[ok] no item anti-correlates with fleet skill</summary>

- evidence: `{"chance_95th": 0, "excluded_collapsed": [], "n_examinees": 6, "negative_rpb": 0, "underpowered": true}`

</details>
<details><summary>[ok] dead-weight items stay a minority</summary>

- evidence: `{"independence_floor": 0.0762, "n_examinees": 6, "share": 0.375}`

</details>
<details><summary>[ok] the fleet is not pinned at a ceiling or floor</summary>

- evidence: `{"max": 1.0, "min": 0.375}`

</details>
<details><summary>[ok] the eval separates the fleet (dynamic range)</summary>

- evidence: `{"spread": 0.625}`

</details>

## Runs

| run file | model | reported as | provider | dry | seed | records | uncheckable |
|---|---|---|---|---|---:|---:|---:|
| 20260810_110453_fleet-arith_dry-alpha_n24_s42.jsonl | dry-alpha | (same) | dry | yes | 42 | 24 | 0 |
| 20260810_110453_fleet-arith_dry-bravo_n24_s42.jsonl | dry-bravo | (same) | dry | yes | 42 | 24 | 0 |
| 20260810_110453_fleet-arith_dry-charlie_n24_s42.jsonl | dry-charlie | (same) | dry | yes | 42 | 24 | 0 |
| 20260810_110453_fleet-arith_dry-delta_n24_s42.jsonl | dry-delta | (same) | dry | yes | 42 | 24 | 0 |
| 20260810_110454_fleet-arith_dry-echo_n24_s42.jsonl | dry-echo | (same) | dry | yes | 42 | 24 | 0 |
| 20260810_110454_fleet-arith_dry-foxtrot_n24_s42.jsonl | dry-foxtrot | (same) | dry | yes | 42 | 24 | 0 |

## Provenance

- tool: dinostomp 0.62.0
- statistical power: at n=24 items, an UNPAIRED comparison (worst case p=0.5) resolves gaps down to ~40% accuracy (80% power, two-sided alpha 0.05); the paired bootstrap behind P6/C1 resolves smaller gaps when model errors overlap
- spec_sha256: `cc280622dc0f91aa3809e0072bf4125add1a99825319f4f97a681fb4e23657cc`
- data_sha256: `742d30fda48436edace090596fe7659588d02761e788be1acdd3fbf2573437dd`
- thresholds: all defaults
- reproducibility tiers, stated honestly: local inputs hash-pinned (spec, data, scorer); requests reproducible given each manifest's environment envelope; hosted-model immutability UNKNOWN unless the provider exposes a pinned revision (the runs table records what each provider claims answered)
- raw report: [STOMP.json](STOMP.json) (both files omit volatile fields, so an unchanged pod re-reports to identical bytes; run manifests carry the timestamps)
