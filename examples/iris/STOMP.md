# 🦖 stomp report: eval.yaml

**OK**: no failures, 1 warning(s) (29 of 29 ran; 25 n/a of 54 declared)

> All runs used the offline dry provider; results exercise the benchmark, not any real model.

## Entitled claims

This result is entitled to claim:

- Exact one-word accuracy with a 95% interval on the UCI-lineage iris measurements, per model.
- Nothing about botany: the dry fleet answers from skill hashes, not petals.


## Checks

### Invariants (deterministic, gating)

Facts, not heuristics: a failure here means something is mechanically wrong (a duplicate exists, a hash changed, a number does not re-derive) and it breaks the verdict.

| | check | witnesses | detail |
|---|---|---:|---|
| ok | questions are unique | 149 | 0 duplicated question(s) among 149 |
| n/a | no answer leaks into its own question | 0 | no free-form items in this dataset |
| ok | no option offered twice in one item | 149 | 0 item(s) offer a duplicate option |
| ok | every target is among its choices | 149 | 0 item(s) whose target is not among their choices |
| ok | no identical question with contradictory targets | 149 | 0 question(s) appear with conflicting targets |
| n/a | every typed claim's evidence requirements hold | 0 | no typed claims declared |
| ok | runs match the spec, data, and scorer on disk (no drift) | 6 | 0 of 6 run(s) no longer match the spec, data, or scorer on disk |
| ok | the witness gate replays clean | 13 | replayed 7 witness(es): 7 behaved; 6 run manifest(s) checked |
| ok | ledger spend agrees with the manifest and the spec cap | 6 | 0 money discrepanc(ies) across 6 run(s) |
| ok | every run record is schema-valid, unique, and its manifest's own | 894 | 0 integrity problem(s) across 894 record(s) |
| ok | truncated outputs are never credited | 894 | 0 truncated output(s) scored as pass; a cut-off response can still have stated its answer, so read these before raising max_tokens and re-running |
| ok | recorded verdicts re-score identically | 894 | 0 of 894 recorded verdict(s) do not reproduce under the current scorer |
| ok | summaries match their run records | 6 | 0 summary discrepanc(ies) across 6 run(s) |
| ok | records cover exactly the seeded selection | 6 | 0 of 6 run(s) do not cover their seeded selection |
| ok | every model produced something scoreable | 6 | 0 of 6 model(s) produced nothing scoreable |
| n/a | no forbidden tool is called | 0 | this spec runs no python targets; nothing produces a trajectory |
| n/a | every required tool is actually called | 0 | this spec runs no python targets; nothing produces a trajectory |
| n/a | trajectories are well-formed | 0 | this spec runs no python targets; nothing produces a trajectory |
| ok | every model was asked the same items | 6 | 0 of 6 model(s) were asked a different item set |

### Diagnostics (statistical, advisory)

Threshold-based signals: they warn, expose their underlying values, and can have legitimate explanations. A warning is evidence of possible trouble, never a proof of invalidity.

| | check | witnesses | detail |
|---|---|---:|---|
| n/a | gold answer does not favour an option position | 0 | every item offers the same options, so position and length are properties of the label set rather than of how each item's distractors were written. What varies is class balance: 'setosa' is the answer 34% of the time |
| n/a | gold answer is not systematically the longest option | 0 | every item offers the same options, so position and length are properties of the label set rather than of how each item's distractors were written. What varies is class balance: 'setosa' is the answer 34% of the time |
| ok | a contamination canary travels with the data | 1 | canary present (dinostomp canary DO NOT TRAIN 1d1aaee8f1...) |
| n/a | no surface feature predicts the gold answer | 0 | every item offers the same options, so position and length are properties of the label set rather than of how each item's distractors were written. What varies is class balance: 'setosa' is the answer 34% of the time |
| n/a | no model reproduces the contamination canary | 0 | regurgitation probes need a hosted model; this pod's runs are all local |
| n/a | no item already appears in a reference dataset | 0 | no reference dataset supplied; pass --against <file> to compare these items against a corpus you have. This never checks training data, and cannot. |
| ok | witnesses kill the mutant scorers | 6 | 0 of 6 applicable mutant scorer(s) survive the witness suite |
| ok | uncheckable rate is sane | 894 | 0% of 894 record(s) are uncheckable |
| ok | accuracy is distinguishable from guessing | 6 | 0 of 6 model(s) score no better than guessing; fleet spans 44% to 100% vs chance ~34% (modal target floor) |
| ok | runs cover the spec's declared scope, nothing foreign | 6 | 0 run(s) outside the spec's declared scope |
| ok | no model selectively escapes the scorer | 6 | 0 of 6 model(s) escape the scorer more than the fleet does |
| n/a | the eval is not solvable blind | 0 | blind probes need a real provider; this pod's runs are all dry |
| ok | no model collapses onto one answer | 6 | 0 of 6 model(s) answer with one response far more often than any target warrants |
| n/a | each model beats its own blind baseline | 0 | blind probes need a real provider; this pod's runs are all dry |
| ok | failed answers do not contain the reference | 5 | 0 of 5 model(s) are failed on answers that contain the reference; the scorer may be grading format, not correctness |
| n/a | billed output tokens match the recorded text | 0 | no model produced 20+ answers of at least 40 characters; short-answer evals cannot be billed against reliably |
| warn | the runs were produced by this engine | 6 | 6 of 6 run(s) were produced by a different engine than the one auditing them (now 756abde76ddfa908); re-run to get numbers this report can stand behind |
| n/a | passing answers are grounded in tool evidence | 0 | this spec runs no python targets; nothing produces a trajectory |
| n/a | no model under-reports its trajectory | 0 | this spec runs no python targets; nothing produces a trajectory |
| n/a | tool calls are not redundant | 0 | this spec runs no python targets; nothing produces a trajectory |
| n/a | the judge agrees with cases whose answer is known | 0 | this eval does not score with a judge |
| n/a | the judge is invariant to content-free perturbations | 0 | this eval does not score with a judge |
| n/a | the judge agrees with itself on identical input | 0 | this eval does not score with a judge |
| n/a | the judge does not favour its own family | 0 | this eval does not score with a judge |
| ok | fleet score totals are reliable (KR-20) | 894 | KR-20 0.99 across 6 models x 149 items; small fleet (6 examinees), treat as a noisy estimate |
| ok | no item anti-correlates with fleet skill | 149 | 0 item(s) that strong models miss and weak models hit, against 0 expected by chance at this fleet size; candidate key errors; at 6 examinees this check has little power, so a quiet result is NOT evidence of a clean answer key |
| ok | dead-weight items stay a minority | 149 | 44% of 149 item(s) separate nobody (66 all-right, 0 all-wrong); 9% would be dead at 6 examinees even with no difficulty structure, so part of this is fleet size |
| ok | no unanimous identical wrong answers | 149 | 0 item(s) where the whole fleet gave one identical wrong answer; candidate key errors |
| n/a | entitled ordering claims are separated beyond sampling noise | 0 | no entitled claim asserts a model ordering |
| ok | the fleet is not pinned at a ceiling or floor | 6 | fleet accuracy spans 44% to 100% on 149 item(s) |
| ok | the eval separates the fleet (dynamic range) | 6 | fleet spread 56% across 6 model(s) on 149 item(s) |
| n/a | answers survive re-ordering the options | 0 | presentation-order probes need a real provider; this pod's runs are all local |
| n/a | the number survives changing the seed | 0 | the spec declares no extra seeds; a single seed cannot show its own spread (run.seeds is how you ask) |
| n/a | the number survives re-phrasing the instruction | 0 | instruction-framing probes need runs on disk |
| n/a | the fleet ORDERING survives re-phrasing the instruction | 0 | instruction-framing probes need runs on disk |

### Receipts

<details><summary>[ok] witnesses kill the mutant scorers</summary>

- evidence: `{"killed": ["always-pass", "always-fail", "case-blind", "substring-lenient", "prefix-lenient", "negation-blind"], "not_applicable": ["space-blind", "uncheckable-credit"]}`

</details>
<details><summary>[ok] uncheckable rate is sane</summary>

- evidence: `{"rate": 0.0}`

</details>
<details><summary>[ok] accuracy is distinguishable from guessing</summary>

- evidence: `{"chance_floor": 0.3356, "modal": 0.3356, "modal_target": "setosa", "per_model_accuracy": {"dry-alpha": 0.8792, "dry-bravo": 0.7114, "dry-charlie": 0.443, "dry-delta": 1.0, "dry-echo": 0.557, "dry-foxtrot": 0.557}, "uniform": 0.3333}`

</details>
<details><summary>[ok] no model selectively escapes the scorer</summary>

- evidence: `{"rates": {"dry-alpha": 0.0, "dry-bravo": 0.0, "dry-charlie": 0.0, "dry-delta": 0.0, "dry-echo": 0.0, "dry-foxtrot": 0.0}}`

</details>
<details><summary>[warn] the runs were produced by this engine</summary>

- engine b1fa98e4f374809f: dry-alpha seed 42 (tool 0.39.0), dry-bravo seed 42 (tool 0.39.0), dry-charlie seed 42 (tool 0.39.0) and 3 more
- evidence: `{"engines": {"b1fa98e4f374809f": 6}}`

</details>
<details><summary>[ok] fleet score totals are reliable (KR-20)</summary>

- evidence: `{"excluded_collapsed": [], "kr20": 0.9872, "n_examinees": 6}`

</details>
<details><summary>[ok] no item anti-correlates with fleet skill</summary>

- evidence: `{"chance_95th": 0, "excluded_collapsed": [], "n_examinees": 6, "negative_rpb": 0, "underpowered": true}`

</details>
<details><summary>[ok] dead-weight items stay a minority</summary>

- evidence: `{"independence_floor": 0.086, "n_examinees": 6, "share": 0.443}`

</details>
<details><summary>[ok] the fleet is not pinned at a ceiling or floor</summary>

- evidence: `{"max": 1.0, "min": 0.443}`

</details>
<details><summary>[ok] the eval separates the fleet (dynamic range)</summary>

- evidence: `{"spread": 0.557}`

</details>

## Runs

| run file | model | reported as | provider | dry | seed | records | uncheckable |
|---|---|---|---|---|---:|---:|---:|
| 20260809_120806_iris-species_dry-alpha_n149_s42.jsonl | dry-alpha | (same) | dry | yes | 42 | 149 | 0 |
| 20260809_120807_iris-species_dry-bravo_n149_s42.jsonl | dry-bravo | (same) | dry | yes | 42 | 149 | 0 |
| 20260809_120807_iris-species_dry-charlie_n149_s42.jsonl | dry-charlie | (same) | dry | yes | 42 | 149 | 0 |
| 20260809_120807_iris-species_dry-delta_n149_s42.jsonl | dry-delta | (same) | dry | yes | 42 | 149 | 0 |
| 20260809_120807_iris-species_dry-echo_n149_s42.jsonl | dry-echo | (same) | dry | yes | 42 | 149 | 0 |
| 20260809_120807_iris-species_dry-foxtrot_n149_s42.jsonl | dry-foxtrot | (same) | dry | yes | 42 | 149 | 0 |

## Provenance

- tool: dinostomp 0.39.1
- statistical power: at n=149 items, an UNPAIRED comparison (worst case p=0.5) resolves gaps down to ~16% accuracy (80% power, two-sided alpha 0.05); the paired bootstrap behind P6/C1 resolves smaller gaps when model errors overlap
- spec_sha256: `b6443a36d9d3b0e15c9885a555de15cfffc25e25a646884f4f4d460787b6bc60`
- data_sha256: `153c4dcefb332e38221e8a27b3f46b179d6dbf46ef834bbd87e188b0acda5942`
- thresholds: all defaults
- reproducibility tiers, stated honestly: local inputs hash-pinned (spec, data, scorer); requests reproducible given each manifest's environment envelope; hosted-model immutability UNKNOWN unless the provider exposes a pinned revision (the runs table records what each provider claims answered)
- raw report: [STOMP.json](STOMP.json) (both files omit volatile fields, so an unchanged pod re-reports to identical bytes; run manifests carry the timestamps)
