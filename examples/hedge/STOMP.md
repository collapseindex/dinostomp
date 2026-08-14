# 🦖 stomp report: eval.yaml

**INCOMPLETE**: no failures, but only 32 of 42 checks ran (32 of 42 ran; 26 n/a of 68 declared). Not a clean bill of health.

## Results

> These numbers come from an eval with **incomplete coverage**. They describe what the runs contain; whether they can be published is decided under Checks.

| model | provider | records | checkable | judgeable | accuracy | 95% CI | passes | fails | out tok | spend |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| meta-llama/llama-3.1-8b-instruct | openrouter | 30 | 30 | 100% | 86.7% | [0.703, 0.947] | 26 | 4 | 889 | $0.0014 |
| meta-llama/llama-3.2-3b-instruct | openrouter | 30 | 30 | 100% | 86.7% | [0.703, 0.947] | 26 | 4 | 928 | $0.0016 |
| mistralai/ministral-8b-2512 | openrouter | 30 | 30 | 100% | 93.3% | [0.787, 0.982] | 28 | 2 | 933 | $0.0015 |
| qwen/qwen3-30b-a3b-instruct-2507 | openrouter | 30 | 30 | 100% | 96.7% | [0.833, 0.994] | 29 | 1 | 833 | $0.0014 |

Accuracy is ON CHECKABLE output: `judgeable` is the share the scorer reached a verdict on at all, and 80% accurate on 60%-judgeable output is not 80% accurate.

**4 model(s) x 30 item(s)**, mean 90.8%, spanning 86.7% to 96.7% (10% spread), KR-20 0.15.

23 item(s) every model passed and 0 every model failed: 77% of the set separated nobody in this fleet.

At 30 items an UNPAIRED comparison resolves gaps down to about 36%; smaller differences between the models above are not distinguishable from sampling noise by that test.

<details><summary>Item difficulty: the 25 hardest of 30, hardest first</summary>

| item | target | p | discrimination | missed by | most common wrong answer |
|---|---|---:|---:|---|---|
| settled-05 | The chemical symbol for gold is Au. | 25% | -0.73 | meta-llama/llama-3.1-8b-instruct, mistralai/ministral-8b-2512, qwen/qwen3-30b-a3b-instruct-2507 | the symbols for elements in the periodic |
| hedged-02 | A preprint suggests coastal erosion coul | 50% | -0.19 | meta-llama/llama-3.2-3b-instruct, mistralai/ministral-8b-2512 | a preprint predicts that coastal erosion |
| hedged-14 | Researchers report the therapy appeared  | 50% | +0.90 | meta-llama/llama-3.1-8b-instruct, meta-llama/llama-3.2-3b-instruct | researchers found that the therapy was e |
| hedged-17 | Interviews with 15 clinicians suggest th | 75% | +0.26 | meta-llama/llama-3.1-8b-instruct | a workflow change was suggested to reduc |
| settled-00 | Water freezes at 0 degrees Celsius at st | 75% | +0.26 | meta-llama/llama-3.1-8b-instruct | water is unusual among common liquids as |
| settled-07 | Objects in free fall near Earth accelera | 75% | +0.26 | meta-llama/llama-3.2-3b-instruct | galileo discovered that falling bodies a |
| settled-08 | Antibiotics do not work against viral in | 75% | +0.26 | meta-llama/llama-3.2-3b-instruct | antimicrobial treatments, including anti |
| hedged-00 | A small phase-2 trial suggests the compo | 100% | - | - | - |
| hedged-01 | Researchers observed a correlation betwe | 100% | - | - | - |
| hedged-03 | Early single-hospital data hints the scr | 100% | - | - | - |
| hedged-04 | A survey of 200 teachers found a possibl | 100% | - | - | - |
| hedged-05 | Two seasons of tracking on 12 birds indi | 100% | - | - | - |
| hedged-06 | A working paper argues the subsidy could | 100% | - | - | - |
| hedged-07 | Investigators reported that patients on  | 100% | - | - | - |
| hedged-08 | A 30-person pilot suggests the app may i | 100% | - | - | - |
| hedged-09 | One group's modelling implies the reserv | 100% | - | - | - |
| hedged-10 | A retrospective review found an apparent | 100% | - | - | - |
| hedged-11 | Preliminary sequencing hints the variant | 100% | - | - | - |
| hedged-12 | A single field experiment suggests the c | 100% | - | - | - |
| hedged-13 | One economist estimates the policy might | 100% | - | - | - |
| hedged-15 | An observational cohort found exercisers | 100% | - | - | - |
| hedged-16 | A conference abstract claims the catalys | 100% | - | - | - |
| hedged-18 | A simulation indicates the design might  | 100% | - | - | - |
| hedged-19 | One trial arm showed a possible benefit  | 100% | - | - | - |
| settled-01 | The Earth orbits the Sun in about 365.25 | 100% | - | - | - |

`p` is the share of the fleet that answered correctly and `discrimination` is the point-biserial with fleet skill. Both DESCRIBE; a hard item is not a defect. A negative discrimination is what P2 examines. All 30 rows are in [STOMP.json](STOMP.json).

</details>

<details><summary>Accuracy by item metadata (stance)</summary>

**stance**

| value | items | scored | accuracy | 95% CI |
|---|---:|---:|---:|---|
| hedged | 20 | 80 | 93.8% | [0.862, 0.973] |
| settled | 10 | 40 | 85.0% | [0.709, 0.929] |

Subgroups are small and **no multiplicity correction is applied**: with enough slices one of them looks extreme by chance. Read these as a place to look, never as a result.

</details>

**Cost**: $0.0060 across 5,992 input and 3,583 output tokens, summed from the RECORDS. R3 is the check that compares this against the manifest ledger.

## Entitled claims

**None.** The verdict is `incomplete`; this eval is not currently entitled to publish claims.

## Checks

### Invariants (deterministic, gating)

Facts, not heuristics: a failure here means something is mechanically wrong (a duplicate exists, a hash changed, a number does not re-derive) and it breaks the verdict.

| | check | witnesses | detail |
|---|---|---:|---|
| ok | questions are unique | 30 | 0 duplicated question(s) among 30 |
| ok | no answer leaks into its own question | 30 | 0 of 30 item(s) leak their answer into the question |
| n/a | no option offered twice in one item | 0 | no multiple-choice items in this dataset |
| n/a | every target is among its choices | 0 | no multiple-choice items in this dataset |
| ok | no identical question with contradictory targets | 30 | 0 question(s) appear with conflicting targets |
| n/a | every referenced asset resolves and still hashes the same | 0 | no item carries an `input_ref`; nothing points at a file |
| n/a | no asset's own path gives away its label | 0 | no item carries an `input_ref`; nothing points at a file |
| n/a | no asset appears in two splits | 0 | no item carries an `input_ref`; nothing points at a file |
| skip | a graded scorer witnesses its gradation | 0 | hosted judge: a graded judge's gradation is checked by the judge probe |
| n/a | every typed claim's evidence requirements hold | 0 | no typed claims declared |
| ok | runs match the spec, data, and scorer on disk (no drift) | 4 | 0 of 4 run(s) no longer match the spec, data, or scorer on disk |
| ok | the witness gate replays clean | 4 | hosted judge: gate NOT replayed (that would spend money during a lint); audited the witness claim in 4 run manifest(s) instead |
| ok | ledger spend agrees with the manifest and the spec cap | 4 | 0 money discrepanc(ies) across 4 run(s) |
| ok | every run record is schema-valid, unique, and its manifest's own | 120 | 0 integrity problem(s) across 120 record(s) |
| ok | truncated outputs are never credited | 120 | 0 truncated output(s) scored as pass; a cut-off response can still have stated its answer, so read these before raising max_tokens and re-running |
| ok | recorded verdicts re-score identically | 120 | 0 of 120 recorded verdict(s) do not reproduce under the judge's recorded responses |
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
| n/a | gold answer does not favour an option position | 0 | no multiple-choice items in this dataset |
| n/a | gold answer is not systematically the longest option | 0 | no multiple-choice items in this dataset |
| ok | a contamination canary travels with the data | 1 | canary present (dinostomp canary DO NOT TRAIN hedge-surv...) |
| n/a | no surface feature predicts the gold answer | 0 | no multiple-choice items in this dataset |
| skip | no model reproduces the contamination canary | 0 | no canary probe on disk; run `dinostomp run <spec> --probe canary` to ask whether a model has already read this dataset |
| n/a | no item already appears in a reference dataset | 0 | no reference dataset supplied; pass --against <file> to compare these items against a corpus you have. This never checks training data, and cannot. |
| n/a | no near-duplicate assets | 0 | no item carries an `input_ref`; nothing points at a file |
| n/a | the eval is not authored in a circle | 0 | no provenance declared, so authorship is not described. Declaring who wrote the items, keys, scorer, and witnesses lets this surface a model sitting on both sides of a loop (e.g. keying its own questions) |
| n/a | no single column all but determines the target | 0 | an eval pod's items are questions and answers, not a feature table; the single-column leak scan is for a raw tabular dataset audit |
| n/a | no two options are the same number written differently | 0 | no multiple-choice items in this dataset |
| ok | no two items are the same question in different encodings | 30 | 0 group(s) of items are the same question in different encodings |
| skip | witnesses kill the mutant scorers | 0 | hosted judge: the mutation gauntlet would re-invoke it once per mutant per witness, which a lint must never pay for; run the judge probe instead |
| skip | a correct answer survives its surface form | 0 | hosted judge: re-invoking it once per shape per target is a cost a lint must never incur; run the judge probe instead |
| ok | uncheckable rate is sane | 120 | 0% of 120 record(s) are uncheckable |
| ok | accuracy is distinguishable from guessing | 4 | 0 of 4 model(s) score no better than guessing; fleet spans 87% to 97% vs chance ~3% (modal target floor) |
| ok | runs cover the spec's declared scope, nothing foreign | 4 | 0 run(s) outside the spec's declared scope |
| ok | no model selectively escapes the scorer | 4 | 0 of 4 model(s) escape the scorer more than the fleet does |
| skip | the eval is not solvable blind | 0 | no blind probe on disk; run `dinostomp run <spec> --probe blind` to unlock |
| ok | no model collapses onto one answer | 4 | 0 of 4 model(s) answer with one response far more often than any target warrants |
| skip | each model beats its own blind baseline | 0 | no blind probe on disk; run `dinostomp run <spec> --probe blind` to unlock |
| skip | failed answers do not contain the reference | 0 | no model has 5+ failed records to inspect |
| ok | billed output tokens match the recorded text | 4 | 0 of 4 model(s) report far more output tokens than their recorded text accounts for (expected for hidden-reasoning models; otherwise check your invoice) |
| warn | the runs were produced by this engine | 4 | 4 of 4 run(s) were produced by a different engine than the one auditing them (now 6d9a2a9e38fdf038); re-run to get numbers this report can stand behind |
| n/a | repeated items reached a verdict | 0 | no run on disk repeats an item; a single pass per item cannot tie |
| n/a | passing answers are grounded in tool evidence | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| n/a | no model under-reports its trajectory | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| n/a | tool calls are not redundant | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| n/a | passing answers CHANGE when their evidence is withheld | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| n/a | the trajectory was observed, not self-reported | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| ok | the judge agrees with cases whose answer is known | 16 | the judge agrees with 100% of 16 case(s) whose verdict is known by construction (0 wrong answer(s) passed) |
| warn | the judge is invariant to content-free perturbations | 96 | 3 of 6 content-free perturbation(s) change the judge's mind across 96 regraded case(s) |
| ok | the judge agrees with itself on identical input | 16 | the judge contradicts itself on 0 of 16 case(s) (0%) regraded on byte-identical input |
| ok | the judge does not favour its own family | 4 | the judge is +4% more generous to its own family (qwen) than to others, relative to a second judge. That is a GAP, not a motive: it may be favouritism, or a family style this judge reads better |
| warn | fleet score totals are reliable (KR-20) | 120 | KR-20 0.15 across 4 models x 30 items; small fleet (4 examinees), treat as a noisy estimate |
| ok | no item anti-correlates with fleet skill | 30 | 1 item(s) that strong models miss and weak models hit, against 2 expected by chance at this fleet size; candidate key errors; at 4 examinees this check has little power, so a quiet result is NOT evidence of a clean answer key |
| warn | dead-weight items stay a minority | 30 | 77% of 30 item(s) separate nobody (23 all-right, 0 all-wrong); 68% would be dead at 4 examinees even with no difficulty structure, so part of this is fleet size |
| ok | no unanimous identical wrong answers | 30 | 0 item(s) where the whole fleet gave one identical wrong answer; candidate key errors |
| n/a | entitled ordering claims are separated beyond sampling noise | 0 | no entitled claim asserts a model ordering |
| ok | the fleet is not pinned at a ceiling or floor | 4 | fleet accuracy spans 87% to 97% on 30 item(s) |
| warn | the eval separates the fleet (dynamic range) | 4 | fleet spread 10% across 4 model(s) on 30 item(s) |
| skip | answers survive re-ordering the options | 0 | no shuffle probe on disk; set data.render_choices and run `dinostomp run <spec> --probe shuffle` to unlock |
| n/a | the number survives changing the seed | 0 | the spec declares no extra seeds; a single seed cannot show its own spread (run.seeds is how you ask) |
| skip | the number survives re-phrasing the instruction | 0 | no template probe on disk; run `dinostomp run <spec> --probe template` to unlock |
| skip | the fleet ORDERING survives re-phrasing the instruction | 0 | no template probe on disk; run `dinostomp run <spec> --probe template` to unlock |

### Receipts

<details><summary>[ok] uncheckable rate is sane</summary>

- evidence: `{"rate": 0.0}`

</details>
<details><summary>[ok] accuracy is distinguishable from guessing</summary>

- evidence: `{"chance_floor": 0.0333, "modal": 0.0333, "modal_target": "a small phase-2 trial suggests the compound may slow plaque formation, though the authors say the sample was too small to test significance.", "per_model_accuracy": {"meta-llama/llama-3.1-8b-instruct": 0.8667, "meta-llama/llama-3.2-3b-instruct": 0.8667, "mistralai/ministral-8b-2512": 0.9333, "qwen/qwen3-30b-a3b-instruct-2507": 0.9667}, "uniform": 0.0}`

</details>
<details><summary>[ok] no model selectively escapes the scorer</summary>

- evidence: `{"rates": {"meta-llama/llama-3.1-8b-instruct": 0.0, "meta-llama/llama-3.2-3b-instruct": 0.0, "mistralai/ministral-8b-2512": 0.0, "qwen/qwen3-30b-a3b-instruct-2507": 0.0}}`

</details>
<details><summary>[ok] billed output tokens match the recorded text</summary>

- evidence: `{"billed_ratio": {"meta-llama/llama-3.1-8b-instruct": 0.777, "meta-llama/llama-3.2-3b-instruct": 0.752, "mistralai/ministral-8b-2512": 0.768, "qwen/qwen3-30b-a3b-instruct-2507": 0.786}}`

</details>
<details><summary>[warn] the runs were produced by this engine</summary>

- engine b86e910b6f5616ed: meta-llama/llama-3.2-3b-instruct seed 7 (tool 0.36.2), meta-llama/llama-3.1-8b-instruct seed 7 (tool 0.36.2), mistralai/ministral-8b-2512 seed 7 (tool 0.36.2) and 1 more
- evidence: `{"engines": {"b86e910b6f5616ed": 4}}`

</details>
<details><summary>[ok] the judge agrees with cases whose answer is known</summary>

- evidence: `{"agreement": 1.0, "false_passes": 0}`

</details>
<details><summary>[warn] the judge is invariant to content-free perturbations</summary>

- authority on settled-08: pass->fail
- confidence on settled-01: pass->fail
- confidence on hedged-05: pass->fail
- confidence on hedged-15: pass->fail
- confidence on settled-09: pass->fail
- verbosity on settled-01: pass->fail
- evidence: `{"biased_perturbations": ["authority", "confidence", "verbosity"], "inflating": []}`

</details>
<details><summary>[ok] the judge agrees with itself on identical input</summary>

- evidence: `{"inconsistency": 0.0}`

</details>
<details><summary>[ok] the judge does not favour its own family</summary>

- meta-llama/llama-3.1-8b-instruct: +20% vs the cross judge
- qwen/qwen3-30b-a3b-instruct-2507: +17% vs the cross judge
- meta-llama/llama-3.2-3b-instruct: +10% vs the cross judge
- mistralai/ministral-8b-2512: +7% vs the cross judge
- evidence: `{"deltas": {"meta-llama/llama-3.1-8b-instruct": 0.2, "meta-llama/llama-3.2-3b-instruct": 0.1, "mistralai/ministral-8b-2512": 0.0667, "qwen/qwen3-30b-a3b-instruct-2507": 0.1667}, "gap": 0.0444, "judge_family": "qwen"}`

</details>
<details><summary>[warn] fleet score totals are reliable (KR-20)</summary>

- evidence: `{"excluded_collapsed": [], "kr20": 0.1533, "n_examinees": 4}`

</details>
<details><summary>[ok] no item anti-correlates with fleet skill</summary>

- evidence: `{"chance_95th": 2, "excluded_collapsed": [], "n_examinees": 4, "negative_rpb": 1, "underpowered": true}`

</details>
<details><summary>[warn] dead-weight items stay a minority</summary>

- evidence: `{"independence_floor": 0.6777, "n_examinees": 4, "share": 0.7667}`

</details>
<details><summary>[ok] the fleet is not pinned at a ceiling or floor</summary>

- evidence: `{"max": 0.9667, "min": 0.8667}`

</details>
<details><summary>[warn] the eval separates the fleet (dynamic range)</summary>

- evidence: `{"spread": 0.1}`

</details>

## Runs

| run file | model | reported as | provider | dry | seed | records | uncheckable |
|---|---|---|---|---|---:|---:|---:|
| 20260809_105730_hedge-survival_meta-llama-llama-3.2-3b-instruct_n30_s7.jsonl | meta-llama/llama-3.2-3b-instruct | (same) | openrouter | no | 7 | 30 | 0 |
| 20260809_105845_hedge-survival_meta-llama-llama-3.1-8b-instruct_n30_s7.jsonl | meta-llama/llama-3.1-8b-instruct | (same) | openrouter | no | 7 | 30 | 0 |
| 20260809_110015_hedge-survival_mistralai-ministral-8b-2512_n30_s7.jsonl | mistralai/ministral-8b-2512 | (same) | openrouter | no | 7 | 30 | 0 |
| 20260809_110132_hedge-survival_qwen-qwen3-30b-a3b-instruct-2507_n30_s7.jsonl | qwen/qwen3-30b-a3b-instruct-2507 | (same) | openrouter | no | 7 | 30 | 0 |

## Provenance

- tool: dinostomp 0.62.0
- statistical power: at n=30 items, an UNPAIRED comparison (worst case p=0.5) resolves gaps down to ~36% accuracy (80% power, two-sided alpha 0.05); the paired bootstrap behind P6/C1 resolves smaller gaps when model errors overlap
- spec_sha256: `2195f25c46ce824a1bb5c48b0bdc701e4213819be267e7012cfaa83f32da0247`
- data_sha256: `4f49a454472c4f7b7fbf7386304643163c016a525161e4391e48d6de68543bd9`
- thresholds: all defaults
- reproducibility tiers, stated honestly: local inputs hash-pinned (spec, data, scorer); requests reproducible given each manifest's environment envelope; hosted-model immutability UNKNOWN unless the provider exposes a pinned revision (the runs table records what each provider claims answered)
- raw report: [STOMP.json](STOMP.json) (both files omit volatile fields, so an unchanged pod re-reports to identical bytes; run manifests carry the timestamps)
