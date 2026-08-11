# 🦖 stomp report: eval.yaml

**INCOMPLETE**: no failures, but only 38 of 42 checks ran (38 of 42 ran; 19 n/a of 61 declared). Not a clean bill of health.

## Results

> These numbers come from an eval with **incomplete coverage**. They describe what the runs contain; whether they can be published is decided under Checks.

| model | provider | records | checkable | judgeable | accuracy | 95% CI | passes | fails | out tok | spend |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| agent-grounded | python | 26 | 26 | 100% | 92.3% | [0.759, 0.979] | 24 | 2 | 0 | $0.0000 |
| agent-lazy | python | 26 | 26 | 100% | 100.0% | [0.871, 1.000] | 26 | 0 | 0 | $0.0000 |
| agent-narrow | python | 26 | 26 | 100% | 34.6% | [0.194, 0.538] | 9 | 17 | 0 | $0.0000 |
| agent-partial | python | 26 | 26 | 100% | 61.5% | [0.425, 0.776] | 16 | 10 | 0 | $0.0000 |

Accuracy is ON CHECKABLE output: `judgeable` is the share the scorer reached a verdict on at all, and 80% accurate on 60%-judgeable output is not 80% accurate.

**4 model(s) x 26 item(s)**, mean 72.1%, spanning 34.6% to 100.0% (65% spread), KR-20 0.96.

9 item(s) every model passed and 0 every model failed: 35% of the set separated nobody in this fleet.

At 26 items an UNPAIRED comparison resolves gaps down to about 39%; smaller differences between the models above are not distinguishable from sampling noise by that test.

<details><summary>Item difficulty: the 25 hardest of 26, hardest first</summary>

| item | target | p | discrimination | missed by | most common wrong answer |
|---|---|---:|---:|---|---|
| cap-santiago | Chile | 25% | +0.58 | agent-grounded, agent-narrow, agent-partial | unknown |
| cap-tunis | Tunisia | 25% | +0.58 | agent-grounded, agent-narrow, agent-partial | unknown |
| cap-athens | Greece | 50% | +0.91 | agent-narrow, agent-partial | unknown |
| cap-budapest | Hungary | 50% | +0.91 | agent-narrow, agent-partial | unknown |
| cap-cairo | Egypt | 50% | +0.91 | agent-narrow, agent-partial | unknown |
| cap-havana | Cuba | 50% | +0.91 | agent-narrow, agent-partial | unknown |
| cap-kathmandu | Nepal | 50% | +0.91 | agent-narrow, agent-partial | unknown |
| cap-lima | Peru | 50% | +0.91 | agent-narrow, agent-partial | unknown |
| cap-rabat | Morocco | 50% | +0.91 | agent-narrow, agent-partial | unknown |
| cap-reykjavik | Iceland | 50% | +0.91 | agent-narrow, agent-partial | unknown |
| cap-amman | Jordan | 75% | +0.81 | agent-narrow | unknown |
| cap-copenhagen | Denmark | 75% | +0.81 | agent-narrow | unknown |
| cap-dublin | Ireland | 75% | +0.81 | agent-narrow | unknown |
| cap-helsinki | Finland | 75% | +0.81 | agent-narrow | unknown |
| cap-stockholm | Sweden | 75% | +0.81 | agent-narrow | unknown |
| cap-vienna | Austria | 75% | +0.81 | agent-narrow | unknown |
| cap-warsaw | Poland | 75% | +0.81 | agent-narrow | unknown |
| cap-canberra | Australia | 100% | - | - | - |
| cap-hanoi | Vietnam | 100% | - | - | - |
| cap-lisbon | Portugal | 100% | - | - | - |
| cap-nairobi | Kenya | 100% | - | - | - |
| cap-oslo | Norway | 100% | - | - | - |
| cap-ottawa | Canada | 100% | - | - | - |
| cap-paris | France | 100% | - | - | - |
| cap-quito | Ecuador | 100% | - | - | - |

`p` is the share of the fleet that answered correctly and `discrimination` is the point-biserial with fleet skill. Both DESCRIBE; a hard item is not a defect. A negative discrimination is what P2 examines. All 26 rows are in [STOMP.json](STOMP.json).

</details>

**Cost**: $0.0000 across 0 input and 0 output tokens, summed from the RECORDS. R3 is the check that compares this against the manifest ledger.

## Entitled claims

**None.** The verdict is `incomplete`; this eval is not currently entitled to publish claims.
Typed claims, compiled to evidence requirements and checked off:

- **SUPPORTED**: accuracy of agent-grounded is at least 70% (95% confidence)
  - [x] complete run on disk: agent-grounded: complete
  - [x] enough checkable evidence: 26 checkable unit(s); need 20
  - [x] interval lower bound clears the declared minimum: lower bound 75.9% vs declared minimum 70%
- **SUPPORTED**: agent-lazy beats agent-narrow by at least 20% (95% confidence)
  - [x] complete runs for both models: agent-lazy: ok; agent-narrow: ok
  - [x] paired observations: 26 common item(s); need 20
  - [x] paired bootstrap clears min_effect at the declared confidence: gap >= 20% in 100% of 400 resamples; need 95%

## Checks

### Invariants (deterministic, gating)

Facts, not heuristics: a failure here means something is mechanically wrong (a duplicate exists, a hash changed, a number does not re-derive) and it breaks the verdict.

| | check | witnesses | detail |
|---|---|---:|---|
| ok | questions are unique | 26 | 0 duplicated question(s) among 26 |
| ok | no answer leaks into its own question | 26 | 0 of 26 free-form item(s) leak their answer |
| n/a | no option offered twice in one item | 0 | no multiple-choice items in this dataset |
| n/a | every target is among its choices | 0 | no multiple-choice items in this dataset |
| ok | no identical question with contradictory targets | 26 | 0 question(s) appear with conflicting targets |
| n/a | every referenced asset resolves and still hashes the same | 0 | no item carries an `input_ref`; nothing points at a file |
| n/a | no asset's own path gives away its label | 0 | no item carries an `input_ref`; nothing points at a file |
| n/a | no asset appears in two splits | 0 | no item carries an `input_ref`; nothing points at a file |
| ok | every typed claim's evidence requirements hold | 6 | 2 of 2 typed claim(s) supported across 6 evidence requirement(s) (no multiplicity correction across 2 claims) |
| ok | runs match the spec, data, and scorer on disk (no drift) | 4 | 0 of 4 run(s) no longer match the spec, data, or scorer on disk |
| ok | the witness gate replays clean | 9 | replayed 5 witness(es): 5 behaved; 4 run manifest(s) checked |
| ok | ledger spend agrees with the manifest and the spec cap | 4 | 0 money discrepanc(ies) across 4 run(s) |
| ok | every run record is schema-valid, unique, and its manifest's own | 104 | 0 integrity problem(s) across 104 record(s) |
| ok | truncated outputs are never credited | 104 | 0 truncated output(s) scored as pass; a cut-off response can still have stated its answer, so read these before raising max_tokens and re-running |
| ok | recorded verdicts re-score identically | 104 | 0 of 104 recorded verdict(s) do not reproduce under the current scorer |
| ok | summaries match their run records | 4 | 0 summary discrepanc(ies) across 4 run(s) |
| ok | records cover exactly the seeded selection | 4 | 0 of 4 run(s) do not cover their seeded selection |
| ok | every model produced something scoreable | 4 | 0 of 4 model(s) produced nothing scoreable |
| ok | no forbidden tool is called | 104 | 0 forbidden tool call(s) across 104 trajector(ies) |
| ok | every required tool is actually called | 104 | 0 of 104 trajector(ies) skipped a required tool |
| ok | trajectories are well-formed | 104 | 0 malformed trajector(ies) of 104 |
| ok | every model was asked the same items | 4 | 0 of 4 model(s) were asked a different item set |

### Diagnostics (statistical, advisory)

Threshold-based signals: they warn, expose their underlying values, and can have legitimate explanations. A warning is evidence of possible trouble, never a proof of invalidity.

| | check | witnesses | detail |
|---|---|---:|---|
| n/a | gold answer does not favour an option position | 0 | no multiple-choice items in this dataset |
| n/a | gold answer is not systematically the longest option | 0 | no multiple-choice items in this dataset |
| ok | a contamination canary travels with the data | 1 | canary present (dinostomp-agent-capitals-canary-7f3a9c21...) |
| n/a | no surface feature predicts the gold answer | 0 | no multiple-choice items in this dataset |
| skip | no model reproduces the contamination canary | 0 | no canary probe on disk; run `dinostomp run <spec> --probe canary` to ask whether a model has already read this dataset |
| n/a | no item already appears in a reference dataset | 0 | no reference dataset supplied; pass --against <file> to compare these items against a corpus you have. This never checks training data, and cannot. |
| n/a | no near-duplicate assets | 0 | no item carries an `input_ref`; nothing points at a file |
| ok | witnesses kill the mutant scorers | 6 | 0 of 6 applicable mutant scorer(s) survive the witness suite |
| ok | uncheckable rate is sane | 104 | 0% of 104 record(s) are uncheckable |
| ok | accuracy is distinguishable from guessing | 4 | 0 of 4 model(s) score no better than guessing; fleet spans 35% to 100% vs chance ~4% (modal target floor) |
| ok | runs cover the spec's declared scope, nothing foreign | 4 | 0 run(s) outside the spec's declared scope |
| ok | no model selectively escapes the scorer | 4 | 0 of 4 model(s) escape the scorer more than the fleet does |
| ok | the eval is not solvable blind | 4 | 0 of 4 model(s) solve the eval blind, above the informed-guesser floor 4%; the items are answerable WITHOUT the question |
| warn | no model collapses onto one answer | 4 | 2 of 4 model(s) answer with one response far more often than any target warrants |
| ok | each model beats its own blind baseline | 4 | 0 of 4 model(s) score no better informed than blind; their numbers are not evidence about this task (unpaired: separate runs) |
| ok | failed answers do not contain the reference | 2 | 0 of 2 model(s) are failed on answers that contain the reference; the scorer may be grading format, not correctness |
| n/a | billed output tokens match the recorded text | 0 | no model produced 20+ answers of at least 40 characters; short-answer evals cannot be billed against reliably |
| warn | the runs were produced by this engine | 4 | 4 of 4 run(s) were produced by a different engine than the one auditing them (now 8aeee044dc7fd094); re-run to get numbers this report can stand behind |
| n/a | repeated items reached a verdict | 0 | no run on disk repeats an item; a single pass per item cannot tie |
| ok | passing answers are grounded in tool evidence | 4 | 0 of 4 target(s) pass items whose answer does not APPEAR in their own evidence (2 such answer(s) in total). This is co-occurrence, not causation: an answer recalled from memory that also happens to appear in a retrieved snippet counts as grounded here, so this count is a floor |
| ok | no model under-reports its trajectory | 4 | 0 of 4 target(s) report far fewer steps than the fleet (median 1.2); a thin trace can be efficiency OR omission |
| ok | tool calls are not redundant | 4 | 0 of 4 target(s) repeat identical calls in more than 25% of their trajectories |
| n/a | passing answers CHANGE when their evidence is withheld | 0 | no mediated agent on disk; only the harness can withhold a tool result, and a self-reporting target calls its own functions |
| ok | the trajectory was observed, not self-reported | 4 | all 4 target(s) write their own trajectory, so T1-T6 verify the RECORD and not the EXECUTION: a target that omits a call from its own trace cannot be caught by reading it. Supported and stated, not a defect. Provider `mediated` moves the tools into the harness if you want the trace to be a log |
| n/a | the judge agrees with cases whose answer is known | 0 | this eval does not score with a judge |
| n/a | the judge is invariant to content-free perturbations | 0 | this eval does not score with a judge |
| n/a | the judge agrees with itself on identical input | 0 | this eval does not score with a judge |
| n/a | the judge does not favour its own family | 0 | this eval does not score with a judge |
| ok | fleet score totals are reliable (KR-20) | 104 | KR-20 0.96 across 4 models x 26 items; small fleet (4 examinees), treat as a noisy estimate |
| ok | no item anti-correlates with fleet skill | 26 | 0 item(s) that strong models miss and weak models hit, against 0 expected by chance at this fleet size; candidate key errors; at 4 examinees this check has little power, so a quiet result is NOT evidence of a clean answer key |
| ok | dead-weight items stay a minority | 26 | 35% of 26 item(s) separate nobody (9 all-right, 0 all-wrong); 20% would be dead at 4 examinees even with no difficulty structure, so part of this is fleet size |
| ok | no unanimous identical wrong answers | 26 | 0 item(s) where the whole fleet gave one identical wrong answer; candidate key errors |
| n/a | entitled ordering claims are separated beyond sampling noise | 0 | no entitled claim asserts a model ordering |
| ok | the fleet is not pinned at a ceiling or floor | 4 | fleet accuracy spans 35% to 100% on 26 item(s) |
| ok | the eval separates the fleet (dynamic range) | 4 | fleet spread 65% across 4 model(s) on 26 item(s) |
| skip | answers survive re-ordering the options | 0 | no shuffle probe on disk; set data.render_choices and run `dinostomp run <spec> --probe shuffle` to unlock |
| n/a | the number survives changing the seed | 0 | the spec declares no extra seeds; a single seed cannot show its own spread (run.seeds is how you ask) |
| skip | the number survives re-phrasing the instruction | 0 | no template probe on disk; run `dinostomp run <spec> --probe template` to unlock |
| skip | the fleet ORDERING survives re-phrasing the instruction | 0 | no template probe on disk; run `dinostomp run <spec> --probe template` to unlock |

### Receipts

<details><summary>[ok] witnesses kill the mutant scorers</summary>

- evidence: `{"killed": ["always-pass", "always-fail", "case-blind", "substring-lenient", "prefix-lenient", "negation-blind"], "not_applicable": ["space-blind", "uncheckable-credit"]}`

</details>
<details><summary>[ok] uncheckable rate is sane</summary>

- evidence: `{"rate": 0.0}`

</details>
<details><summary>[ok] accuracy is distinguishable from guessing</summary>

- evidence: `{"chance_floor": 0.0385, "modal": 0.0385, "modal_target": "france", "per_model_accuracy": {"agent-grounded": 0.9231, "agent-lazy": 1.0, "agent-narrow": 0.3462, "agent-partial": 0.6154}, "uniform": 0.0}`

</details>
<details><summary>[ok] no model selectively escapes the scorer</summary>

- evidence: `{"rates": {"agent-grounded": 0.0, "agent-lazy": 0.0, "agent-narrow": 0.0, "agent-partial": 0.0}}`

</details>
<details><summary>[ok] the eval is not solvable blind</summary>

- evidence: `{"floor": 0.0385}`

</details>
<details><summary>[warn] no model collapses onto one answer</summary>

- agent-narrow: gave 'unknown' to 65% of 26 item(s), while the most common target covers only 4%
- agent-partial: gave 'unknown' to 38% of 26 item(s), while the most common target covers only 4%

</details>
<details><summary>[ok] each model beats its own blind baseline</summary>

- evidence: `{"lift": {"agent-grounded": 0.9231, "agent-lazy": 1.0, "agent-narrow": 0.3462, "agent-partial": 0.6154}}`

</details>
<details><summary>[warn] the runs were produced by this engine</summary>

- engine 050e2f343915e1b9: agent-grounded seed 42 (tool 0.57.1), agent-lazy seed 42 (tool 0.57.1), agent-narrow seed 42 (tool 0.57.1) and 1 more
- evidence: `{"engines": {"050e2f343915e1b9": 4}}`

</details>
<details><summary>[ok] passing answers are grounded in tool evidence</summary>

- cap-santiago (agent-lazy): passed, but its answer appears in no tool result
- cap-tunis (agent-lazy): passed, but its answer appears in no tool result
- evidence: `{"measures": "co-occurrence in the recorded trace, not causal use", "models_judged": 4, "ungrounded_records": 2}`

</details>
<details><summary>[ok] no model under-reports its trajectory</summary>

- evidence: `{"fleet_median_steps": 1.231}`

</details>
<details><summary>[ok] the trajectory was observed, not self-reported</summary>

- evidence: `{"isolation": ["n/a"], "trajectory_sources": {"self_reported": ["agent-grounded", "agent-lazy", "agent-narrow", "agent-partial"]}}`

</details>
<details><summary>[ok] fleet score totals are reliable (KR-20)</summary>

- evidence: `{"excluded_collapsed": [], "kr20": 0.9561, "n_examinees": 4}`

</details>
<details><summary>[ok] no item anti-correlates with fleet skill</summary>

- evidence: `{"chance_95th": 0, "excluded_collapsed": [], "n_examinees": 4, "negative_rpb": 0, "underpowered": true}`

</details>
<details><summary>[ok] dead-weight items stay a minority</summary>

- evidence: `{"independence_floor": 0.1966, "n_examinees": 4, "share": 0.3462}`

</details>
<details><summary>[ok] the fleet is not pinned at a ceiling or floor</summary>

- evidence: `{"max": 1.0, "min": 0.3462}`

</details>
<details><summary>[ok] the eval separates the fleet (dynamic range)</summary>

- evidence: `{"spread": 0.6538}`

</details>

## Runs

| run file | model | reported as | provider | dry | seed | records | uncheckable |
|---|---|---|---|---|---:|---:|---:|
| 20260810_110459_agent-capitals_agent-grounded_n26_s42.jsonl | agent-grounded | (same) | python | no | 42 | 26 | 0 |
| 20260810_110459_agent-capitals_agent-lazy_n26_s42.jsonl | agent-lazy | (same) | python | no | 42 | 26 | 0 |
| 20260810_110459_agent-capitals_agent-narrow_n26_s42.jsonl | agent-narrow | (same) | python | no | 42 | 26 | 0 |
| 20260810_110459_agent-capitals_agent-partial_n26_s42.jsonl | agent-partial | (same) | python | no | 42 | 26 | 0 |

## Provenance

- tool: dinostomp 0.59.0
- statistical power: at n=26 items, an UNPAIRED comparison (worst case p=0.5) resolves gaps down to ~39% accuracy (80% power, two-sided alpha 0.05); the paired bootstrap behind P6/C1 resolves smaller gaps when model errors overlap
- spec_sha256: `66a70cdee88cac64a2400c41b4a919c92d4e2e8345f4b4257b9433215195aeb1`
- data_sha256: `5dfd19b1348d90405cd81c07540d53a4583e766dfbb690420cf78bdeb5cb530c`
- target_sha256: `{'agent-grounded': '56f6fd64ffda736e33f3c48b5232b8b9a13f071c4a13c343f961e021da40694c', 'agent-partial': '56f6fd64ffda736e33f3c48b5232b8b9a13f071c4a13c343f961e021da40694c', 'agent-narrow': '56f6fd64ffda736e33f3c48b5232b8b9a13f071c4a13c343f961e021da40694c', 'agent-lazy': '56f6fd64ffda736e33f3c48b5232b8b9a13f071c4a13c343f961e021da40694c'}`
- thresholds: all defaults
- reproducibility tiers, stated honestly: local inputs hash-pinned (spec, data, scorer); requests reproducible given each manifest's environment envelope; hosted-model immutability UNKNOWN unless the provider exposes a pinned revision (the runs table records what each provider claims answered)
- raw report: [STOMP.json](STOMP.json) (both files omit volatile fields, so an unchanged pod re-reports to identical bytes; run manifests carry the timestamps)
