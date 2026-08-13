# 🦖 stomp report: eval.yaml

**INCOMPLETE**: no failures, but only 37 of 39 checks ran (37 of 39 ran; 26 n/a of 65 declared). Not a clean bill of health.

## Results

> These numbers come from an eval with **incomplete coverage**. They describe what the runs contain; whether they can be published is decided under Checks.

| model | provider | records | checkable | judgeable | accuracy | 95% CI | passes | fails | out tok | spend |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| meta-llama/llama-3.1-8b-instruct | openrouter | 40 | 40 | 100% | 95.0% | [0.835, 0.986] | 38 | 2 | 342 | $0.0001 |
| meta-llama/llama-3.2-3b-instruct | openrouter | 40 | 40 | 100% | 87.5% | [0.739, 0.945] | 35 | 5 | 229 | $0.0002 |
| mistralai/ministral-8b-2512 | openrouter | 40 | 40 | 100% | 100.0% | [0.912, 1.000] | 40 | 0 | 244 | $0.0003 |
| qwen/qwen3-30b-a3b-instruct-2507 | openrouter | 40 | 40 | 100% | 100.0% | [0.912, 1.000] | 40 | 0 | 225 | $0.0001 |

Accuracy is ON CHECKABLE output: `judgeable` is the share the scorer reached a verdict on at all, and 80% accurate on 60%-judgeable output is not 80% accurate.

**4 model(s) x 40 item(s)**, mean 95.6%, spanning 87.5% to 100.0% (12% spread), KR-20 0.70.

33 item(s) every model passed and 0 every model failed: 82% of the set separated nobody in this fleet.

At 40 items an UNPAIRED comparison resolves gaps down to about 31%; smaller differences between the models above are not distinguishable from sampling noise by that test.

<details><summary>Item difficulty: the 25 hardest of 40, hardest first</summary>

| item | target | p | discrimination | missed by | most common wrong answer |
|---|---|---:|---:|---|---|
| pres-02 | Diamond | 75% | -0.14 | meta-llama/llama-3.1-8b-instruct | corundum |
| pres-10 | Igneous | 75% | +0.87 | meta-llama/llama-3.2-3b-instruct | b. |
| pres-12 | Electron | 75% | +0.87 | meta-llama/llama-3.2-3b-instruct | d. |
| pres-14 | Gravity | 75% | -0.14 | meta-llama/llama-3.1-8b-instruct | c. |
| pres-16 | Fission | 75% | +0.87 | meta-llama/llama-3.2-3b-instruct | b. |
| pres-31 | Merge sort | 75% | +0.87 | meta-llama/llama-3.2-3b-instruct | c. |
| pres-35 | Glucose | 75% | +0.87 | meta-llama/llama-3.2-3b-instruct | b |
| pres-00 | Carbon dioxide | 100% | - | - | - |
| pres-01 | Mercury | 100% | - | - | - |
| pres-03 | Arteries | 100% | - | - | - |
| pres-04 | Carbon | 100% | - | - | - |
| pres-05 | Transpiration | 100% | - | - | - |
| pres-06 | Outer core | 100% | - | - | - |
| pres-07 | Ohm | 100% | - | - | - |
| pres-08 | Mitochondrion | 100% | - | - | - |
| pres-09 | Nitrogen | 100% | - | - | - |
| pres-11 | Air pressure | 100% | - | - | - |
| pres-13 | Carrying oxygen | 100% | - | - | - |
| pres-15 | Acidic | 100% | - | - | - |
| pres-17 | Hertz | 100% | - | - | - |
| pres-18 | Vitamin D | 100% | - | - | - |
| pres-19 | A variant form of a gene | 100% | - | - | - |
| pres-20 | Refraction | 100% | - | - | - |
| pres-21 | Omnivore | 100% | - | - | - |
| pres-22 | Velocity | 100% | - | - | - |

`p` is the share of the fleet that answered correctly and `discrimination` is the point-biserial with fleet skill. Both DESCRIBE; a hard item is not a defect. A negative discrimination is what P2 examines. All 40 rows are in [STOMP.json](STOMP.json).

</details>

**Cost**: $0.0008 across 9,166 input and 1,040 output tokens, summed from the RECORDS. R3 is the check that compares this against the manifest ledger.

## Entitled claims

**None.** The verdict is `incomplete`; this eval is not currently entitled to publish claims.

## Checks

### Invariants (deterministic, gating)

Facts, not heuristics: a failure here means something is mechanically wrong (a duplicate exists, a hash changed, a number does not re-derive) and it breaks the verdict.

| | check | witnesses | detail |
|---|---|---:|---|
| ok | questions are unique | 40 | 0 duplicated question(s) among 40 |
| n/a | no answer leaks into its own question | 0 | no free-form items in this dataset |
| ok | no option offered twice in one item | 40 | 0 item(s) offer a duplicate option |
| ok | every target is among its choices | 40 | 0 item(s) whose target is not among their choices |
| ok | no identical question with contradictory targets | 40 | 0 question(s) appear with conflicting targets |
| n/a | every referenced asset resolves and still hashes the same | 0 | no item carries an `input_ref`; nothing points at a file |
| n/a | no asset's own path gives away its label | 0 | no item carries an `input_ref`; nothing points at a file |
| n/a | no asset appears in two splits | 0 | no item carries an `input_ref`; nothing points at a file |
| n/a | a graded scorer witnesses its gradation | 0 | this scorer does not emit intermediate partial credit, so there is no gradation to witness |
| n/a | every typed claim's evidence requirements hold | 0 | no typed claims declared |
| ok | runs match the spec, data, and scorer on disk (no drift) | 4 | 0 of 4 run(s) no longer match the spec, data, or scorer on disk |
| ok | the witness gate replays clean | 11 | replayed 7 witness(es): 7 behaved; 4 run manifest(s) checked |
| ok | ledger spend agrees with the manifest and the spec cap | 4 | 0 money discrepanc(ies) across 4 run(s) |
| ok | every run record is schema-valid, unique, and its manifest's own | 160 | 0 integrity problem(s) across 160 record(s) |
| ok | truncated outputs are never credited | 160 | 0 truncated output(s) scored as pass; a cut-off response can still have stated its answer, so read these before raising max_tokens and re-running |
| ok | recorded verdicts re-score identically | 160 | 0 of 160 recorded verdict(s) do not reproduce under the current scorer |
| ok | summaries match their run records | 4 | 0 summary discrepanc(ies) across 4 run(s) |
| ok | records cover exactly the seeded selection | 4 | 0 of 4 run(s) do not cover their seeded selection |
| ok | every model produced something scoreable | 4 | 0 of 4 model(s) produced nothing scoreable |
| n/a | graded scores stay in range | 0 | no record carries a graded value |
| n/a | no forbidden tool is called | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| n/a | every required tool is actually called | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| n/a | trajectories are well-formed | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| ok | every model was asked the same items | 4 | 0 of 4 model(s) were asked a different item set |

### Diagnostics (statistical, advisory)

Threshold-based signals: they warn, expose their underlying values, and can have legitimate explanations. A warning is evidence of possible trouble, never a proof of invalidity.

| | check | witnesses | detail |
|---|---|---:|---|
| ok | gold answer does not favour an option position | 40 | gold overshoots position 1 by +8% over its per-item expectation (13 of 40) |
| ok | gold answer is not systematically the longest option | 40 | gold is strictly longest +5% over its per-item expectation (12 of 40) |
| ok | a contamination canary travels with the data | 1 | canary present (dinostomp canary DO NOT TRAIN presentati...) |
| ok | no surface feature predicts the gold answer | 40 | 0 surface feature(s) beat the per-item chance null on 40 keyed item(s) |
| ok | no model reproduces the contamination canary | 4 | 0 of 4 model(s) with a DEMONSTRATED-sensitive probe reproduced this pod's canary |
| n/a | no item already appears in a reference dataset | 0 | no reference dataset supplied; pass --against <file> to compare these items against a corpus you have. This never checks training data, and cannot. |
| n/a | no near-duplicate assets | 0 | no item carries an `input_ref`; nothing points at a file |
| n/a | the eval is not authored in a circle | 0 | no provenance declared, so authorship is not described. Declaring who wrote the items, keys, scorer, and witnesses lets this surface a model sitting on both sides of a loop (e.g. keying its own questions) |
| ok | witnesses kill the mutant scorers | 5 | 0 of 5 applicable mutant scorer(s) survive the witness suite |
| ok | a correct answer survives its surface form | 6 | 0 surface form(s) lose a correct answer and 0 credit a decoy, of 6 applicable |
| ok | uncheckable rate is sane | 160 | 0% of 160 record(s) are uncheckable |
| ok | accuracy is distinguishable from guessing | 4 | 0 of 4 model(s) score no better than guessing; fleet spans 88% to 100% vs chance ~25% (uniform choice floor) |
| ok | runs cover the spec's declared scope, nothing foreign | 4 | 0 run(s) outside the spec's declared scope |
| ok | no model selectively escapes the scorer | 4 | 0 of 4 model(s) escape the scorer more than the fleet does |
| skip | the eval is not solvable blind | 0 | no blind probe on disk; run `dinostomp run <spec> --probe blind` to unlock |
| ok | no model collapses onto one answer | 4 | 0 of 4 model(s) answer with one response far more often than any target warrants |
| skip | each model beats its own blind baseline | 0 | no blind probe on disk; run `dinostomp run <spec> --probe blind` to unlock |
| ok | failed answers do not contain the reference | 1 | 0 of 1 model(s) are failed on answers that contain the reference; the scorer may be grading format, not correctness |
| n/a | billed output tokens match the recorded text | 0 | no model produced 20+ answers of at least 40 characters; short-answer evals cannot be billed against reliably |
| warn | the runs were produced by this engine | 4 | 4 of 4 run(s) were produced by a different engine than the one auditing them (now 76f44bc713434991); re-run to get numbers this report can stand behind |
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
| ok | fleet score totals are reliable (KR-20) | 160 | KR-20 0.70 across 4 models x 40 items; small fleet (4 examinees), treat as a noisy estimate |
| ok | no item anti-correlates with fleet skill | 40 | 0 item(s) that strong models miss and weak models hit, against 0 expected by chance at this fleet size; candidate key errors; at 4 examinees this check has little power, so a quiet result is NOT evidence of a clean answer key |
| warn | dead-weight items stay a minority | 40 | 82% of 40 item(s) separate nobody (33 all-right, 0 all-wrong); 83% would be dead at 4 examinees even with no difficulty structure, so part of this is fleet size |
| ok | no unanimous identical wrong answers | 40 | 0 item(s) where the whole fleet gave one identical wrong answer; candidate key errors |
| n/a | entitled ordering claims are separated beyond sampling noise | 0 | no entitled claim asserts a model ordering |
| ok | the fleet is not pinned at a ceiling or floor | 4 | fleet accuracy spans 88% to 100% on 40 item(s) |
| ok | the eval separates the fleet (dynamic range) | 4 | fleet spread 12% across 4 model(s) on 40 item(s) |
| ok | answers survive re-ordering the options | 4 | 0 of 4 model(s) move more than the flip churn explains when the options are re-ordered; that part of the score is layout, not knowledge |
| n/a | the number survives changing the seed | 0 | the spec declares no extra seeds; a single seed cannot show its own spread (run.seeds is how you ask) |
| warn | the number survives re-phrasing the instruction | 4 | 1 of 4 model(s) move more than the flipped items explain when the instruction is re-phrased; that part of the score belongs to the prompt, not the model |
| ok | the fleet ORDERING survives re-phrasing the instruction | 4 | 0 model pair(s) out of 6 swap places depending on how the instruction is phrased, across 6 framing(s) |

### Receipts

<details><summary>[ok] gold answer does not favour an option position</summary>

- evidence: `{"chance_rate_at_this_n": 0.0185, "excess": 0.075, "position": 1}`

</details>
<details><summary>[ok] gold answer is not systematically the longest option</summary>

- evidence: `{"excess": 0.05}`

</details>
<details><summary>[ok] witnesses kill the mutant scorers</summary>

- evidence: `{"killed": ["always-pass", "always-fail", "case-blind", "space-blind", "prefix-lenient"], "not_applicable": ["substring-lenient", "negation-blind", "uncheckable-credit"]}`

</details>
<details><summary>[ok] a correct answer survives its surface form</summary>

- evidence: `{"baseline_form": "labelled", "held": ["trailing-punctuation", "surrounding-whitespace", "markdown-emphasis", "label-case", "keyword-in-prose", "reasoning-prefix"], "not_applicable": ["answer-case", "decoy-in-working"]}`

</details>
<details><summary>[ok] uncheckable rate is sane</summary>

- evidence: `{"rate": 0.0}`

</details>
<details><summary>[ok] accuracy is distinguishable from guessing</summary>

- evidence: `{"chance_floor": 0.25, "modal": 0.025, "modal_target": "carbon dioxide", "per_model_accuracy": {"meta-llama/llama-3.1-8b-instruct": 0.95, "meta-llama/llama-3.2-3b-instruct": 0.875, "mistralai/ministral-8b-2512": 1.0, "qwen/qwen3-30b-a3b-instruct-2507": 1.0}, "uniform": 0.25}`

</details>
<details><summary>[ok] no model selectively escapes the scorer</summary>

- evidence: `{"rates": {"meta-llama/llama-3.1-8b-instruct": 0.0, "meta-llama/llama-3.2-3b-instruct": 0.0, "mistralai/ministral-8b-2512": 0.0, "qwen/qwen3-30b-a3b-instruct-2507": 0.0}}`

</details>
<details><summary>[warn] the runs were produced by this engine</summary>

- engine cf11e5de89c91221: meta-llama/llama-3.2-3b-instruct seed 7 (tool 0.37.0), meta-llama/llama-3.1-8b-instruct seed 7 (tool 0.37.0), mistralai/ministral-8b-2512 seed 7 (tool 0.37.0) and 1 more
- evidence: `{"engines": {"cf11e5de89c91221": 4}}`

</details>
<details><summary>[ok] fleet score totals are reliable (KR-20)</summary>

- evidence: `{"excluded_collapsed": [], "kr20": 0.7042, "n_examinees": 4}`

</details>
<details><summary>[ok] no item anti-correlates with fleet skill</summary>

- evidence: `{"chance_95th": 0, "excluded_collapsed": [], "n_examinees": 4, "negative_rpb": 0, "underpowered": true}`

</details>
<details><summary>[warn] dead-weight items stay a minority</summary>

- evidence: `{"independence_floor": 0.8312, "n_examinees": 4, "share": 0.825}`

</details>
<details><summary>[ok] the fleet is not pinned at a ceiling or floor</summary>

- evidence: `{"max": 1.0, "min": 0.875}`

</details>
<details><summary>[ok] the eval separates the fleet (dynamic range)</summary>

- evidence: `{"spread": 0.125}`

</details>
<details><summary>[ok] answers survive re-ordering the options</summary>

- evidence: `{"swing": {"meta-llama/llama-3.1-8b-instruct": {"flipped": 3, "moves": -0.025, "noise_band": 0.0849}, "meta-llama/llama-3.2-3b-instruct": {"flipped": 6, "moves": 0.0, "noise_band": 0.12}, "mistralai/ministral-8b-2512": {"flipped": 1, "moves": -0.025, "noise_band": 0.049}, "qwen/qwen3-30b-a3b-instruct-2507": {"flipped": 0, "moves": 0.0, "noise_band": 0.0}}}`

</details>
<details><summary>[warn] the number survives re-phrasing the instruction</summary>

- meta-llama/llama-3.2-3b-instruct: 85% framed 'bare' vs 95% framed 'expert' (spread 10% over 6 phrasings, vs 10% explainable by the 4 item(s) that flipped)
- evidence: `{"template_swing": {"meta-llama/llama-3.1-8b-instruct": {"best": "instructed", "framings": 6, "noise_band": 0.0693, "spread": 0.05, "worst": "polite"}, "meta-llama/llama-3.2-3b-instruct": {"best": "expert", "framings": 6, "noise_band": 0.098, "spread": 0.1, "worst": "bare"}, "mistralai/ministral-8b-2512": {"best": "bare", "framings": 6, "noise_band": 0.0, "spread": 0.0, "worst": "bare"}, "qwen/qwen3-30b-a3b-instruct-2507": {"best": "bare", "framings": 6, "noise_band": 0.0, "spread": 0.0, "worst": "bare"}}}`

</details>
<details><summary>[ok] the fleet ORDERING survives re-phrasing the instruction</summary>

- evidence: `{"framings": ["bare", "expert", "instructed", "polite", "stepwise", "terse"], "reversals": 0}`

</details>

## Runs

| run file | model | reported as | provider | dry | seed | records | uncheckable |
|---|---|---|---|---|---:|---:|---:|
| 20260809_113716_presentation_meta-llama-llama-3.2-3b-instruct_n40_s7.jsonl | meta-llama/llama-3.2-3b-instruct | (same) | openrouter | no | 7 | 40 | 0 |
| 20260809_113734_presentation_meta-llama-llama-3.1-8b-instruct_n40_s7.jsonl | meta-llama/llama-3.1-8b-instruct | (same) | openrouter | no | 7 | 40 | 0 |
| 20260809_113800_presentation_mistralai-ministral-8b-2512_n40_s7.jsonl | mistralai/ministral-8b-2512 | (same) | openrouter | no | 7 | 40 | 0 |
| 20260809_113825_presentation_qwen-qwen3-30b-a3b-instruct-2507_n40_s7.jsonl | qwen/qwen3-30b-a3b-instruct-2507 | (same) | openrouter | no | 7 | 40 | 0 |

## Provenance

- tool: dinostomp 0.62.0
- statistical power: at n=40 items, an UNPAIRED comparison (worst case p=0.5) resolves gaps down to ~31% accuracy (80% power, two-sided alpha 0.05); the paired bootstrap behind P6/C1 resolves smaller gaps when model errors overlap
- spec_sha256: `5bacd458ad54056ede6d5cca8071816c1f9f31dc510571c29b23c7124dc47878`
- data_sha256: `d9e5a5096d3d36c846d4d90320ec9f19b0b835df5d4b6baa68dd4b0d870ba32e`
- thresholds: all defaults
- reproducibility tiers, stated honestly: local inputs hash-pinned (spec, data, scorer); requests reproducible given each manifest's environment envelope; hosted-model immutability UNKNOWN unless the provider exposes a pinned revision (the runs table records what each provider claims answered)
- raw report: [STOMP.json](STOMP.json) (both files omit volatile fields, so an unchanged pod re-reports to identical bytes; run manifests carry the timestamps)
