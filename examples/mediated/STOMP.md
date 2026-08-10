# 🦖 stomp report: eval.yaml

**INCOMPLETE**: no failures, but only 33 of 42 checks ran (33 of 42 ran; 19 n/a of 61 declared). Not a clean bill of health.

## Results

> These numbers come from an eval with **incomplete coverage**. They describe what the runs contain; whether they can be published is decided under Checks.

| model | provider | records | checkable | judgeable | accuracy | 95% CI | passes | fails | out tok | spend |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| greedy | mediated | 24 | 24 | 100% | 100.0% | [0.862, 1.000] | 24 | 0 | 0 | $0.0000 |
| grounded | mediated | 24 | 24 | 100% | 100.0% | [0.862, 1.000] | 24 | 0 | 0 | $0.0000 |
| oneshot | mediated | 24 | 24 | 100% | 75.0% | [0.551, 0.880] | 18 | 6 | 0 | $0.0000 |

Accuracy is ON CHECKABLE output: `judgeable` is the share the scorer reached a verdict on at all, and 80% accurate on 60%-judgeable output is not 80% accurate.

**3 model(s) x 24 item(s)**, mean 91.7%, spanning 75.0% to 100.0% (25% spread), KR-20 0.87.

18 item(s) every model passed and 0 every model failed: 75% of the set separated nobody in this fleet.

At 24 items an UNPAIRED comparison resolves gaps down to about 40%; smaller differences between the models above are not distinguishable from sampling noise by that test.

<details><summary>Item difficulty: all 24 item(s), hardest first</summary>

| item | target | p | discrimination | missed by | most common wrong answer |
|---|---|---:|---:|---|---|
| m019 | lower | 67% | +1.00 | oneshot | concentration |
| m020 | lower | 67% | +1.00 | oneshot | concentration |
| m021 | lower | 67% | +1.00 | oneshot | concentration |
| m022 | activation | 67% | +1.00 | oneshot | energy |
| m023 | activation | 67% | +1.00 | oneshot | energy |
| m024 | activation | 67% | +1.00 | oneshot | energy |
| m001 | chloroplasts | 100% | - | - | - |
| m002 | chloroplasts | 100% | - | - | - |
| m003 | chloroplasts | 100% | - | - | - |
| m004 | mitochondria | 100% | - | - | - |
| m005 | mitochondria | 100% | - | - | - |
| m006 | mitochondria | 100% | - | - | - |
| m007 | stomata | 100% | - | - | - |
| m008 | stomata | 100% | - | - | - |
| m009 | stomata | 100% | - | - | - |
| m010 | two | 100% | - | - | - |
| m011 | two | 100% | - | - | - |
| m012 | two | 100% | - | - | - |
| m013 | four | 100% | - | - | - |
| m014 | four | 100% | - | - | - |
| m015 | four | 100% | - | - | - |
| m016 | higher | 100% | - | - | - |
| m017 | higher | 100% | - | - | - |
| m018 | higher | 100% | - | - | - |

`p` is the share of the fleet that answered correctly and `discrimination` is the point-biserial with fleet skill. Both DESCRIBE; a hard item is not a defect. A negative discrimination is what P2 examines.

</details>

**Cost**: $0.0000 across 0 input and 0 output tokens, summed from the RECORDS. R3 is the check that compares this against the manifest ledger.

## Entitled claims

**None.** The verdict is `incomplete`; this eval is not currently entitled to publish claims.

## Checks

### Invariants (deterministic, gating)

Facts, not heuristics: a failure here means something is mechanically wrong (a duplicate exists, a hash changed, a number does not re-derive) and it breaks the verdict.

| | check | witnesses | detail |
|---|---|---:|---|
| ok | questions are unique | 24 | 0 duplicated question(s) among 24 |
| ok | no answer leaks into its own question | 24 | 0 of 24 free-form item(s) leak their answer |
| n/a | no option offered twice in one item | 0 | no multiple-choice items in this dataset |
| n/a | every target is among its choices | 0 | no multiple-choice items in this dataset |
| ok | no identical question with contradictory targets | 24 | 0 question(s) appear with conflicting targets |
| n/a | every referenced asset resolves and still hashes the same | 0 | no item carries an `input_ref`; nothing points at a file |
| n/a | no asset's own path gives away its label | 0 | no item carries an `input_ref`; nothing points at a file |
| n/a | no asset appears in two splits | 0 | no item carries an `input_ref`; nothing points at a file |
| n/a | every typed claim's evidence requirements hold | 0 | no typed claims declared |
| ok | runs match the spec, data, and scorer on disk (no drift) | 3 | 0 of 3 run(s) no longer match the spec, data, or scorer on disk |
| ok | the witness gate replays clean | 9 | replayed 6 witness(es): 6 behaved; 3 run manifest(s) checked |
| ok | ledger spend agrees with the manifest and the spec cap | 3 | 0 money discrepanc(ies) across 3 run(s) |
| ok | every run record is schema-valid, unique, and its manifest's own | 72 | 0 integrity problem(s) across 72 record(s) |
| ok | truncated outputs are never credited | 72 | 0 truncated output(s) scored as pass; a cut-off response can still have stated its answer, so read these before raising max_tokens and re-running |
| ok | recorded verdicts re-score identically | 72 | 0 of 72 recorded verdict(s) do not reproduce under the current scorer |
| ok | summaries match their run records | 3 | 0 summary discrepanc(ies) across 3 run(s) |
| ok | records cover exactly the seeded selection | 3 | 0 of 3 run(s) do not cover their seeded selection |
| ok | every model produced something scoreable | 3 | 0 of 3 model(s) produced nothing scoreable |
| ok | no forbidden tool is called | 72 | 0 forbidden tool call(s) across 72 trajector(ies) |
| ok | every required tool is actually called | 72 | 0 of 72 trajector(ies) skipped a required tool |
| ok | trajectories are well-formed | 72 | 0 malformed trajector(ies) of 72 |
| ok | every model was asked the same items | 3 | 0 of 3 model(s) were asked a different item set |

### Diagnostics (statistical, advisory)

Threshold-based signals: they warn, expose their underlying values, and can have legitimate explanations. A warning is evidence of possible trouble, never a proof of invalidity.

| | check | witnesses | detail |
|---|---|---:|---|
| n/a | gold answer does not favour an option position | 0 | no multiple-choice items in this dataset |
| n/a | gold answer is not systematically the longest option | 0 | no multiple-choice items in this dataset |
| ok | a contamination canary travels with the data | 1 | canary present (dinostomp canary DO NOT TRAIN mediated-g...) |
| n/a | no surface feature predicts the gold answer | 0 | no multiple-choice items in this dataset |
| skip | no model reproduces the contamination canary | 0 | no canary probe on disk; run `dinostomp run <spec> --probe canary` to ask whether a model has already read this dataset |
| n/a | no item already appears in a reference dataset | 0 | no reference dataset supplied; pass --against <file> to compare these items against a corpus you have. This never checks training data, and cannot. |
| n/a | no near-duplicate assets | 0 | no item carries an `input_ref`; nothing points at a file |
| warn | witnesses kill the mutant scorers | 6 | 1 of 6 applicable mutant scorer(s) survive the witness suite |
| ok | uncheckable rate is sane | 72 | 0% of 72 record(s) are uncheckable |
| ok | accuracy is distinguishable from guessing | 3 | 0 of 3 model(s) score no better than guessing; fleet spans 75% to 100% vs chance ~12% (modal target floor) |
| ok | runs cover the spec's declared scope, nothing foreign | 3 | 0 run(s) outside the spec's declared scope |
| ok | no model selectively escapes the scorer | 3 | 0 of 3 model(s) escape the scorer more than the fleet does |
| skip | the eval is not solvable blind | 0 | no blind probe on disk; run `dinostomp run <spec> --probe blind` to unlock |
| ok | no model collapses onto one answer | 3 | 0 of 3 model(s) answer with one response far more often than any target warrants |
| skip | each model beats its own blind baseline | 0 | no blind probe on disk; run `dinostomp run <spec> --probe blind` to unlock |
| ok | failed answers do not contain the reference | 1 | 0 of 1 model(s) are failed on answers that contain the reference; the scorer may be grading format, not correctness |
| n/a | billed output tokens match the recorded text | 0 | no model produced 20+ answers of at least 40 characters; short-answer evals cannot be billed against reliably |
| ok | the runs were produced by this engine | 3 | 0 of 3 run(s) were produced by a different engine than the one auditing them (now f55e58da3a42578d); re-run to get numbers this report can stand behind |
| n/a | repeated items reached a verdict | 0 | no run on disk repeats an item; a single pass per item cannot tie |
| ok | passing answers are grounded in tool evidence | 3 | 0 of 3 target(s) pass items whose answer does not APPEAR in their own evidence (0 such answer(s) in total). This is co-occurrence, not causation: an answer recalled from memory that also happens to appear in a retrieved snippet counts as grounded here, so this count is a floor |
| ok | no model under-reports its trajectory | 3 | 0 of 3 target(s) report far fewer steps than the fleet (median 1.0); a thin trace can be efficiency OR omission |
| warn | tool calls are not redundant | 3 | 1 of 3 target(s) repeat identical calls in more than 25% of their trajectories |
| warn | passing answers CHANGE when their evidence is withheld | 3 | 1 of 3 agent(s) answer identically with their evidence withheld, so those answers did not causally depend on it. Unlike T4 this is a counterfactual, not a co-occurrence: the two runs differ only in whether the agent could see what its tools returned |
| ok | the trajectory was observed, not self-reported | 3 | all 3 agent(s) reached their tools through the harness, running in this process, so T1-T6 read an observed log rather than testimony. Mediation is not isolation: it makes the trace trustworthy, not the agent, and `isolation: subprocess` is the stronger setting |
| n/a | the judge agrees with cases whose answer is known | 0 | this eval does not score with a judge |
| n/a | the judge is invariant to content-free perturbations | 0 | this eval does not score with a judge |
| n/a | the judge agrees with itself on identical input | 0 | this eval does not score with a judge |
| n/a | the judge does not favour its own family | 0 | this eval does not score with a judge |
| skip | fleet score totals are reliable (KR-20) | 0 | 3 model(s) x 24 common item(s); need 4+ models and 5+ items to unlock |
| skip | no item anti-correlates with fleet skill | 0 | 3 model(s) x 24 common item(s); need 4+ models and 5+ items to unlock |
| skip | dead-weight items stay a minority | 0 | 3 model(s) x 24 common item(s); need 4+ models and 5+ items to unlock |
| ok | no unanimous identical wrong answers | 24 | 0 item(s) where the whole fleet gave one identical wrong answer; candidate key errors |
| n/a | entitled ordering claims are separated beyond sampling noise | 0 | no entitled claim asserts a model ordering |
| ok | the fleet is not pinned at a ceiling or floor | 3 | fleet accuracy spans 75% to 100% on 24 item(s) |
| ok | the eval separates the fleet (dynamic range) | 3 | fleet spread 25% across 3 model(s) on 24 item(s) |
| skip | answers survive re-ordering the options | 0 | no shuffle probe on disk; set data.render_choices and run `dinostomp run <spec> --probe shuffle` to unlock |
| n/a | the number survives changing the seed | 0 | the spec declares no extra seeds; a single seed cannot show its own spread (run.seeds is how you ask) |
| skip | the number survives re-phrasing the instruction | 0 | no template probe on disk; run `dinostomp run <spec> --probe template` to unlock |
| skip | the fleet ORDERING survives re-phrasing the instruction | 0 | no template probe on disk; run `dinostomp run <spec> --probe template` to unlock |

### Receipts

<details><summary>[warn] witnesses kill the mutant scorers</summary>

- prefix-lenient (credits a truncated answer) survives; add a witness giving a strict prefix of the target, expect: fail
- evidence: `{"killed": ["always-pass", "always-fail", "case-blind", "substring-lenient", "negation-blind"], "not_applicable": ["space-blind", "uncheckable-credit"]}`

</details>
<details><summary>[ok] uncheckable rate is sane</summary>

- evidence: `{"rate": 0.0}`

</details>
<details><summary>[ok] accuracy is distinguishable from guessing</summary>

- evidence: `{"chance_floor": 0.125, "modal": 0.125, "modal_target": "chloroplasts", "per_model_accuracy": {"greedy": 1.0, "grounded": 1.0, "oneshot": 0.75}, "uniform": 0.0}`

</details>
<details><summary>[ok] no model selectively escapes the scorer</summary>

- evidence: `{"rates": {"greedy": 0.0, "grounded": 0.0, "oneshot": 0.0}}`

</details>
<details><summary>[ok] the runs were produced by this engine</summary>

- evidence: `{"engines": {"f55e58da3a42578d": 3}}`

</details>
<details><summary>[ok] passing answers are grounded in tool evidence</summary>

- evidence: `{"measures": "co-occurrence in the recorded trace, not causal use", "models_judged": 3, "ungrounded_records": 0}`

</details>
<details><summary>[ok] no model under-reports its trajectory</summary>

- evidence: `{"fleet_median_steps": 1.0}`

</details>
<details><summary>[warn] tool calls are not redundant</summary>

- greedy: 24 of 24 trajector(ies) (100%) repeat an identical call
- m001 (greedy): 1 repeated identical call(s)
- m002 (greedy): 1 repeated identical call(s)
- m003 (greedy): 1 repeated identical call(s)

</details>
<details><summary>[warn] passing answers CHANGE when their evidence is withheld</summary>

- oneshot: 18 of 18 passing answer(s) (100%) are unchanged when the evidence is withheld
- oneshot/m001: identical answer with its evidence withheld
- oneshot/m002: identical answer with its evidence withheld
- oneshot/m003: identical answer with its evidence withheld
- evidence: `{"measures": "causal dependence, by withholding tool results", "models_judged": 3}`

</details>
<details><summary>[ok] the trajectory was observed, not self-reported</summary>

- evidence: `{"isolation": ["inprocess"], "trajectory_sources": {"harness_observed": ["greedy", "grounded", "oneshot"]}}`

</details>
<details><summary>[ok] the fleet is not pinned at a ceiling or floor</summary>

- evidence: `{"max": 1.0, "min": 0.75}`

</details>
<details><summary>[ok] the eval separates the fleet (dynamic range)</summary>

- evidence: `{"spread": 0.25}`

</details>

## Runs

| run file | model | reported as | provider | dry | seed | records | uncheckable |
|---|---|---|---|---|---:|---:|---:|
| 20260810_082456_mediated-grounding_greedy_n24_s7.jsonl | greedy | (same) | mediated | no | 7 | 24 | 0 |
| 20260810_082456_mediated-grounding_grounded_n24_s7.jsonl | grounded | (same) | mediated | no | 7 | 24 | 0 |
| 20260810_082456_mediated-grounding_oneshot_n24_s7.jsonl | oneshot | (same) | mediated | no | 7 | 24 | 0 |

## Provenance

- tool: dinostomp 0.54.0
- statistical power: at n=24 items, an UNPAIRED comparison (worst case p=0.5) resolves gaps down to ~40% accuracy (80% power, two-sided alpha 0.05); the paired bootstrap behind P6/C1 resolves smaller gaps when model errors overlap
- spec_sha256: `ae79cfd0e8319d80f9c565515d96632b8b952160f7f84a8c94f34075d9a6c15a`
- data_sha256: `36fe2258536e2eb42b78699d92ab85fff93108c55cea33795f90f40f7be53c27`
- target_sha256: `{'grounded': 'f22417f9d9c11c1183e5489c3960fcd0e3c0ee3e52ada32d6870d7a2f70aa488', 'oneshot': 'f22417f9d9c11c1183e5489c3960fcd0e3c0ee3e52ada32d6870d7a2f70aa488', 'greedy': 'f22417f9d9c11c1183e5489c3960fcd0e3c0ee3e52ada32d6870d7a2f70aa488'}`
- thresholds: all defaults
- reproducibility tiers, stated honestly: local inputs hash-pinned (spec, data, scorer); requests reproducible given each manifest's environment envelope; hosted-model immutability UNKNOWN unless the provider exposes a pinned revision (the runs table records what each provider claims answered)
- raw report: [STOMP.json](STOMP.json) (both files omit volatile fields, so an unchanged pod re-reports to identical bytes; run manifests carry the timestamps)
