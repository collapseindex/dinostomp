# 🦖 stomp report: eval.yaml

**INCOMPLETE**: no failures, but only 32 of 41 checks ran (32 of 41 ran; 16 n/a of 57 declared). Not a clean bill of health.

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
| n/a | every typed claim's evidence requirements hold | 0 | no typed claims declared |
| ok | runs match the spec, data, and scorer on disk (no drift) | 3 | 0 of 3 run(s) no longer match the spec, data, or scorer on disk |
| ok | the witness gate replays clean | 10 | replayed 7 witness(es): 7 behaved; 3 run manifest(s) checked |
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
| ok | a contamination canary travels with the data | 1 | canary present (dinostomp canary DO NOT TRAIN live-agent...) |
| n/a | no surface feature predicts the gold answer | 0 | no multiple-choice items in this dataset |
| skip | no model reproduces the contamination canary | 0 | no canary probe on disk; run `dinostomp run <spec> --probe canary` to ask whether a model has already read this dataset |
| n/a | no item already appears in a reference dataset | 0 | no reference dataset supplied; pass --against <file> to compare these items against a corpus you have. This never checks training data, and cannot. |
| warn | witnesses kill the mutant scorers | 5 | 1 of 5 applicable mutant scorer(s) survive the witness suite |
| ok | uncheckable rate is sane | 72 | 0% of 72 record(s) are uncheckable |
| ok | accuracy is distinguishable from guessing | 3 | 0 of 3 model(s) score no better than guessing; fleet spans 54% to 83% vs chance ~8% (modal target floor) |
| ok | runs cover the spec's declared scope, nothing foreign | 3 | 0 run(s) outside the spec's declared scope |
| ok | no model selectively escapes the scorer | 3 | 0 of 3 model(s) escape the scorer more than the fleet does |
| skip | the eval is not solvable blind | 0 | no blind probe on disk; run `dinostomp run <spec> --probe blind` to unlock |
| ok | no model collapses onto one answer | 3 | 0 of 3 model(s) answer with one response far more often than any target warrants |
| skip | each model beats its own blind baseline | 0 | no blind probe on disk; run `dinostomp run <spec> --probe blind` to unlock |
| warn | failed answers do not contain the reference | 2 | 2 of 2 model(s) are failed on answers that contain the reference; the scorer may be grading format, not correctness |
| n/a | billed output tokens match the recorded text | 0 | no model produced 20+ answers of at least 40 characters; short-answer evals cannot be billed against reliably |
| warn | the runs were produced by this engine | 3 | 3 of 3 run(s) were produced by a different engine than the one auditing them (now 2761032f11bcb3d4); re-run to get numbers this report can stand behind |
| n/a | repeated items reached a verdict | 0 | no run on disk repeats an item; a single pass per item cannot tie |
| warn | passing answers are grounded in tool evidence | 3 | 2 of 3 target(s) pass items whose answer does not APPEAR in their own evidence (6 such answer(s) in total). This is co-occurrence, not causation: an answer recalled from memory that also happens to appear in a retrieved snippet counts as grounded here, so this count is a floor |
| ok | no model under-reports its trajectory | 3 | 0 of 3 target(s) report far fewer steps than the fleet (median 1.0); a thin trace can be efficiency OR omission |
| warn | tool calls are not redundant | 3 | 1 of 3 target(s) repeat identical calls in more than 25% of their trajectories |
| n/a | passing answers CHANGE when their evidence is withheld | 0 | no mediated agent on disk; only the harness can withhold a tool result, and a self-reporting target calls its own functions |
| ok | the trajectory was observed, not self-reported | 3 | all 3 target(s) write their own trajectory, so T1-T6 verify the RECORD and not the EXECUTION: a target that omits a call from its own trace cannot be caught by reading it. Supported and stated, not a defect. Provider `mediated` moves the tools into the harness if you want the trace to be a log |
| n/a | the judge agrees with cases whose answer is known | 0 | this eval does not score with a judge |
| n/a | the judge is invariant to content-free perturbations | 0 | this eval does not score with a judge |
| n/a | the judge agrees with itself on identical input | 0 | this eval does not score with a judge |
| n/a | the judge does not favour its own family | 0 | this eval does not score with a judge |
| skip | fleet score totals are reliable (KR-20) | 0 | 3 model(s) x 24 common item(s); need 4+ models and 5+ items to unlock |
| skip | no item anti-correlates with fleet skill | 0 | 3 model(s) x 24 common item(s); need 4+ models and 5+ items to unlock |
| skip | dead-weight items stay a minority | 0 | 3 model(s) x 24 common item(s); need 4+ models and 5+ items to unlock |
| ok | no unanimous identical wrong answers | 24 | 0 item(s) where the whole fleet gave one identical wrong answer; candidate key errors |
| n/a | entitled ordering claims are separated beyond sampling noise | 0 | no entitled claim asserts a model ordering |
| ok | the fleet is not pinned at a ceiling or floor | 3 | fleet accuracy spans 54% to 83% on 24 item(s) |
| ok | the eval separates the fleet (dynamic range) | 3 | fleet spread 29% across 3 model(s) on 24 item(s) |
| skip | answers survive re-ordering the options | 0 | no shuffle probe on disk; set data.render_choices and run `dinostomp run <spec> --probe shuffle` to unlock |
| n/a | the number survives changing the seed | 0 | the spec declares no extra seeds; a single seed cannot show its own spread (run.seeds is how you ask) |
| skip | the number survives re-phrasing the instruction | 0 | no template probe on disk; run `dinostomp run <spec> --probe template` to unlock |
| skip | the fleet ORDERING survives re-phrasing the instruction | 0 | no template probe on disk; run `dinostomp run <spec> --probe template` to unlock |

### Receipts

<details><summary>[warn] witnesses kill the mutant scorers</summary>

- space-blind (ignores whitespace differences) survives; add a witness whose output differs from the target only by a RUN of internal whitespace (e.g. a doubled space), with the expected verdict pinned
- evidence: `{"killed": ["always-pass", "always-fail", "case-blind", "prefix-lenient"], "not_applicable": ["substring-lenient", "negation-blind", "uncheckable-credit"]}`

</details>
<details><summary>[ok] uncheckable rate is sane</summary>

- evidence: `{"rate": 0.0}`

</details>
<details><summary>[ok] accuracy is distinguishable from guessing</summary>

- evidence: `{"chance_floor": 0.0833, "modal": 0.0833, "modal_target": "oxygen", "per_model_accuracy": {"live-greedy": 0.8333, "live-grounded": 0.5417, "live-oneshot": 0.7917}, "uniform": 0.0}`

</details>
<details><summary>[ok] no model selectively escapes the scorer</summary>

- evidence: `{"rates": {"live-greedy": 0.0, "live-grounded": 0.0, "live-oneshot": 0.0}}`

</details>
<details><summary>[warn] failed answers do not contain the reference</summary>

- live-grounded: 6 of 11 failed answer(s) (55%) contain the reference answer verbatim
- live-oneshot: 3 of 5 failed answer(s) (60%) contain the reference answer verbatim

</details>
<details><summary>[warn] the runs were produced by this engine</summary>

- engine be4c83d7129cec32: live-grounded seed 7 (tool 0.38.0), live-oneshot seed 7 (tool 0.38.0), live-greedy seed 7 (tool 0.38.0)
- evidence: `{"engines": {"be4c83d7129cec32": 3}}`

</details>
<details><summary>[warn] passing answers are grounded in tool evidence</summary>

- live-greedy: 3 of 20 passing answer(s) (15%) appear in no retrieved evidence
- live-oneshot: 3 of 19 passing answer(s) (16%) appear in no retrieved evidence
- la-01 (live-greedy): passed, but its answer appears in no tool result
- la-16 (live-greedy): passed, but its answer appears in no tool result
- la-17 (live-greedy): passed, but its answer appears in no tool result
- la-01 (live-oneshot): passed, but its answer appears in no tool result
- la-04 (live-oneshot): passed, but its answer appears in no tool result
- la-07 (live-oneshot): passed, but its answer appears in no tool result
- evidence: `{"measures": "co-occurrence in the recorded trace, not causal use", "models_judged": 3, "ungrounded_records": 6}`

</details>
<details><summary>[ok] no model under-reports its trajectory</summary>

- evidence: `{"fleet_median_steps": 1.0}`

</details>
<details><summary>[warn] tool calls are not redundant</summary>

- live-greedy: 24 of 24 trajector(ies) (100%) repeat an identical call
- la-00 (live-greedy): 2 repeated identical call(s)
- la-01 (live-greedy): 2 repeated identical call(s)
- la-02 (live-greedy): 1 repeated identical call(s)

</details>
<details><summary>[ok] the trajectory was observed, not self-reported</summary>

- evidence: `{"isolation": ["n/a"], "trajectory_sources": {"self_reported": ["live-greedy", "live-grounded", "live-oneshot"]}}`

</details>
<details><summary>[ok] the fleet is not pinned at a ceiling or floor</summary>

- evidence: `{"max": 0.8333, "min": 0.5417}`

</details>
<details><summary>[ok] the eval separates the fleet (dynamic range)</summary>

- evidence: `{"spread": 0.2917}`

</details>

## Runs

| run file | model | reported as | provider | dry | seed | records | uncheckable |
|---|---|---|---|---|---:|---:|---:|
| 20260809_120340_live-agent_live-grounded_n24_s7.jsonl | live-grounded | (same) | python | no | 7 | 24 | 0 |
| 20260809_120411_live-agent_live-oneshot_n24_s7.jsonl | live-oneshot | (same) | python | no | 7 | 24 | 0 |
| 20260809_120447_live-agent_live-greedy_n24_s7.jsonl | live-greedy | (same) | python | no | 7 | 24 | 0 |

## Provenance

- tool: dinostomp 0.47.0
- statistical power: at n=24 items, an UNPAIRED comparison (worst case p=0.5) resolves gaps down to ~40% accuracy (80% power, two-sided alpha 0.05); the paired bootstrap behind P6/C1 resolves smaller gaps when model errors overlap
- spec_sha256: `40ec29a2e7b222d3ab5988e6140f4f51f1250a60ed5584b3683e6a03065c216f`
- data_sha256: `308236893b61320ddd8b4e45a4c36f00173d2f43ffc98736fa8b65d22cef3120`
- target_sha256: `{'live-grounded': '4f8a7f8a8f09e4607d3fda36ccf78651c05e3536fd3f6820e760098bfda03ce6', 'live-oneshot': '4f8a7f8a8f09e4607d3fda36ccf78651c05e3536fd3f6820e760098bfda03ce6', 'live-greedy': '4f8a7f8a8f09e4607d3fda36ccf78651c05e3536fd3f6820e760098bfda03ce6'}`
- thresholds: all defaults
- reproducibility tiers, stated honestly: local inputs hash-pinned (spec, data, scorer); requests reproducible given each manifest's environment envelope; hosted-model immutability UNKNOWN unless the provider exposes a pinned revision (the runs table records what each provider claims answered)
- raw report: [STOMP.json](STOMP.json) (both files omit volatile fields, so an unchanged pod re-reports to identical bytes; run manifests carry the timestamps)
