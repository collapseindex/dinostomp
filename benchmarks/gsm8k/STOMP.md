# 🦖 stomp report: eval.yaml

**BROKEN**: 2 gated finding(s) (31 of 37 ran; 24 n/a of 61 declared)

## Results

> These numbers come from an eval with **gated findings**. They describe what the runs contain; whether they can be published is decided under Checks.

| model | provider | records | checkable | judgeable | accuracy | 95% CI | passes | fails | out tok | spend |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| meta-llama/llama-3.1-8b-instruct | openrouter | 360 | 360 | 100% | 84.7% | [0.806, 0.881] | 305 | 55 | 78931 | $0.0076 |
| meta-llama/llama-3.2-3b-instruct | openrouter | 360 | 326 | 91% | 44.8% | [0.395, 0.502] | 146 | 180 | 42335 | $0.0146 |
| mistralai/ministral-8b-2512 | openrouter | 360 | 360 | 100% | 86.1% | [0.822, 0.893] | 310 | 50 | 104864 | $0.0193 |
| qwen/qwen3-30b-a3b-instruct-2507 | openrouter | 360 | 360 | 100% | 78.9% | [0.744, 0.828] | 284 | 76 | 91234 | $0.0188 |

Accuracy is ON CHECKABLE output: `judgeable` is the share the scorer reached a verdict on at all, and 80% accurate on 60%-judgeable output is not 80% accurate.

**4 model(s) x 332 item(s)**, mean 73.6%, spanning 44.8% to 86.1% (41% spread), KR-20 0.99.

100 item(s) every model passed and 12 every model failed: 34% of the set separated nobody in this fleet.

At 332 items an UNPAIRED comparison resolves gaps down to about 11%; smaller differences between the models above are not distinguishable from sampling noise by that test.

<details><summary>Item difficulty: the 25 hardest of 332, hardest first</summary>

| item | target | p | discrimination | missed by | most common wrong answer |
|---|---|---:|---:|---|---|
| gsm-0062 | 25000 | 0% | - | meta-llama/llama-3.1-8b-instruct, meta-llama/llama-3.2-3b-instruct, mistralai/ministral-8b-2512, qwen/qwen3-30b-a3b-instruct-2507 | ## step 1: calculate the value of the pe |
| gsm-0153 | 48 | 0% | - | meta-llama/llama-3.1-8b-instruct, meta-llama/llama-3.2-3b-instruct, mistralai/ministral-8b-2512, qwen/qwen3-30b-a3b-instruct-2507 | ## step 1: let's denote the initial numb |
| gsm-0301 | 8 | 0% | - | meta-llama/llama-3.1-8b-instruct, meta-llama/llama-3.2-3b-instruct, mistralai/ministral-8b-2512, qwen/qwen3-30b-a3b-instruct-2507 | ## step 1: understand the problem the pr |
| gsm-0307 | 16 | 0% | - | meta-llama/llama-3.1-8b-instruct, meta-llama/llama-3.2-3b-instruct, mistralai/ministral-8b-2512, qwen/qwen3-30b-a3b-instruct-2507 | to find out how many weeks it will take  |
| gsm-0580 | 500 | 0% | - | meta-llama/llama-3.1-8b-instruct, meta-llama/llama-3.2-3b-instruct, mistralai/ministral-8b-2512, qwen/qwen3-30b-a3b-instruct-2507 | ## step 1: determine the percentage by w |
| gsm-0675 | 33 | 0% | - | meta-llama/llama-3.1-8b-instruct, meta-llama/llama-3.2-3b-instruct, mistralai/ministral-8b-2512, qwen/qwen3-30b-a3b-instruct-2507 | ## step 1: determine the initial number  |
| gsm-0749 | 3 | 0% | - | meta-llama/llama-3.1-8b-instruct, meta-llama/llama-3.2-3b-instruct, mistralai/ministral-8b-2512, qwen/qwen3-30b-a3b-instruct-2507 | ## step 1: calculate the number of stude |
| gsm-0782 | 54 | 0% | - | meta-llama/llama-3.1-8b-instruct, meta-llama/llama-3.2-3b-instruct, mistralai/ministral-8b-2512, qwen/qwen3-30b-a3b-instruct-2507 | ## step 1: calculate the number of times |
| gsm-0796 | 2880000 | 0% | - | meta-llama/llama-3.1-8b-instruct, mistralai/ministral-8b-2512, qwen/qwen3-30b-a3b-instruct-2507 | ## step 1: calculate the total number of |
| gsm-0814 | 11 | 0% | - | meta-llama/llama-3.1-8b-instruct, meta-llama/llama-3.2-3b-instruct, mistralai/ministral-8b-2512, qwen/qwen3-30b-a3b-instruct-2507 | to find out how much money is used, we n |
| gsm-0830 | 1128 | 0% | - | meta-llama/llama-3.1-8b-instruct, meta-llama/llama-3.2-3b-instruct, mistralai/ministral-8b-2512, qwen/qwen3-30b-a3b-instruct-2507 | ## step 1: calculate the total time brit |
| gsm-0962 | 1000 | 0% | - | meta-llama/llama-3.1-8b-instruct, meta-llama/llama-3.2-3b-instruct, mistralai/ministral-8b-2512, qwen/qwen3-30b-a3b-instruct-2507 | ## step 1: determine the cost of the sup |
| gsm-0984 | 342 | 0% | - | meta-llama/llama-3.1-8b-instruct, meta-llama/llama-3.2-3b-instruct, mistralai/ministral-8b-2512, qwen/qwen3-30b-a3b-instruct-2507 | ## step 1: calculate the total length of |
| gsm-1035 | 35 | 0% | - | meta-llama/llama-3.1-8b-instruct, mistralai/ministral-8b-2512, qwen/qwen3-30b-a3b-instruct-2507 | ## step 1: calculate the total number of |
| gsm-0214 | 8 | 25% | -0.99 | meta-llama/llama-3.1-8b-instruct, mistralai/ministral-8b-2512, qwen/qwen3-30b-a3b-instruct-2507 | ## step 1: let's denote the amount of wa |
| gsm-0241 | 6 | 25% | +0.34 | meta-llama/llama-3.2-3b-instruct, mistralai/ministral-8b-2512, qwen/qwen3-30b-a3b-instruct-2507 | to find the total number of books they w |
| gsm-0340 | 4 | 25% | -0.99 | meta-llama/llama-3.1-8b-instruct, mistralai/ministral-8b-2512, qwen/qwen3-30b-a3b-instruct-2507 | ## step 1: determine how many balls josh |
| gsm-0406 | 200 | 25% | +0.34 | meta-llama/llama-3.2-3b-instruct, mistralai/ministral-8b-2512, qwen/qwen3-30b-a3b-instruct-2507 | ## step 1: determine the initial number  |
| gsm-0420 | 17000 | 25% | +0.45 | meta-llama/llama-3.1-8b-instruct, meta-llama/llama-3.2-3b-instruct, qwen/qwen3-30b-a3b-instruct-2507 | ## step 1: determine the amount of money |
| gsm-0752 | 240 | 25% | +0.17 | meta-llama/llama-3.1-8b-instruct, meta-llama/llama-3.2-3b-instruct, mistralai/ministral-8b-2512 | ## step 1: calculate the total cost of e |
| gsm-0779 | 255 | 25% | +0.45 | meta-llama/llama-3.1-8b-instruct, meta-llama/llama-3.2-3b-instruct, qwen/qwen3-30b-a3b-instruct-2507 | ## step 1: calculate the speed at which  |
| gsm-0780 | 25 | 25% | +0.17 | meta-llama/llama-3.1-8b-instruct, meta-llama/llama-3.2-3b-instruct, mistralai/ministral-8b-2512 | ## step 1: define the variables for the  |
| gsm-0906 | 10 | 25% | +0.34 | meta-llama/llama-3.2-3b-instruct, mistralai/ministral-8b-2512, qwen/qwen3-30b-a3b-instruct-2507 | to find out how many shoeboxes are left, |
| gsm-0923 | 2 | 25% | +0.17 | meta-llama/llama-3.1-8b-instruct, meta-llama/llama-3.2-3b-instruct, mistralai/ministral-8b-2512 | ## step 1: calculate the total number of |
| gsm-0936 | 250 | 25% | +0.17 | meta-llama/llama-3.1-8b-instruct, meta-llama/llama-3.2-3b-instruct, mistralai/ministral-8b-2512 | to find out how much cameron would save, |

`p` is the share of the fleet that answered correctly and `discrimination` is the point-biserial with fleet skill. Both DESCRIBE; a hard item is not a defect. A negative discrimination is what P2 examines. All 332 rows are in [STOMP.json](STOMP.json).

</details>

**Cost**: $0.0604 across 88,487 input and 317,364 output tokens, summed from the RECORDS. R3 is the check that compares this against the manifest ledger.

## Entitled claims

**None.** The verdict is `broken`; this eval is not currently entitled to publish claims.
Typed claims, compiled to evidence requirements and checked off:

- **SUPPORTED**: accuracy of meta-llama/llama-3.2-3b-instruct is at least 20% (95% confidence)
  - [x] complete run on disk: meta-llama/llama-3.2-3b-instruct: complete
  - [x] enough checkable evidence: 296 checkable unit(s); need 20
  - [x] interval lower bound clears the declared minimum: lower bound 38.7% vs declared minimum 20%
- **SUPPORTED**: accuracy of meta-llama/llama-3.1-8b-instruct is at least 20% (95% confidence)
  - [x] complete run on disk: meta-llama/llama-3.1-8b-instruct: complete
  - [x] enough checkable evidence: 332 checkable unit(s); need 20
  - [x] interval lower bound clears the declared minimum: lower bound 79.4% vs declared minimum 20%
- **SUPPORTED**: accuracy of mistralai/ministral-8b-2512 is at least 20% (95% confidence)
  - [x] complete run on disk: mistralai/ministral-8b-2512: complete
  - [x] enough checkable evidence: 330 checkable unit(s); need 20
  - [x] interval lower bound clears the declared minimum: lower bound 81.6% vs declared minimum 20%
- **SUPPORTED**: accuracy of qwen/qwen3-30b-a3b-instruct-2507 is at least 20% (95% confidence)
  - [x] complete run on disk: qwen/qwen3-30b-a3b-instruct-2507: complete
  - [x] enough checkable evidence: 331 checkable unit(s); need 20
  - [x] interval lower bound clears the declared minimum: lower bound 73.5% vs declared minimum 20%

## Checks

### Invariants (deterministic, gating)

Facts, not heuristics: a failure here means something is mechanically wrong (a duplicate exists, a hash changed, a number does not re-derive) and it breaks the verdict.

| | check | witnesses | detail |
|---|---|---:|---|
| ok | questions are unique | 1319 | 0 duplicated question(s) among 1319 |
| ok | no answer leaks into its own question | 1319 | 0 of 1319 free-form item(s) leak their answer |
| n/a | no option offered twice in one item | 0 | no multiple-choice items in this dataset |
| n/a | every target is among its choices | 0 | no multiple-choice items in this dataset |
| ok | no identical question with contradictory targets | 1319 | 0 question(s) appear with conflicting targets |
| n/a | every referenced asset resolves and still hashes the same | 0 | no item carries an `input_ref`; nothing points at a file |
| n/a | no asset's own path gives away its label | 0 | no item carries an `input_ref`; nothing points at a file |
| n/a | no asset appears in two splits | 0 | no item carries an `input_ref`; nothing points at a file |
| ok | every typed claim's evidence requirements hold | 12 | 4 of 4 typed claim(s) supported across 12 evidence requirement(s) (no multiplicity correction across 4 claims) |
| **FAIL** | runs match the spec, data, and scorer on disk (no drift) | 12 | 12 of 12 run(s) no longer match the spec, data, or scorer on disk |
| ok | the witness gate replays clean | 18 | replayed 6 witness(es): 6 behaved; 12 run manifest(s) checked |
| ok | ledger spend agrees with the manifest and the spec cap | 12 | 0 money discrepanc(ies) across 12 run(s) |
| ok | every run record is schema-valid, unique, and its manifest's own | 1440 | 0 integrity problem(s) across 1440 record(s) |
| **FAIL** | truncated outputs are never credited | 1440 | 9 truncated output(s) scored as pass; a cut-off response can still have stated its answer, so read these before raising max_tokens and re-running |
| ok | recorded verdicts re-score identically | 1440 | 0 of 1440 recorded verdict(s) do not reproduce under the current scorer |
| ok | summaries match their run records | 12 | 0 summary discrepanc(ies) across 12 run(s) |
| ok | records cover exactly the seeded selection | 12 | 0 of 12 run(s) do not cover their seeded selection |
| ok | every model produced something scoreable | 4 | 0 of 4 model(s) produced nothing scoreable |
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
| ok | a contamination canary travels with the data | 1 | canary present (dinostomp canary DO NOT TRAIN benchmarks) |
| n/a | no surface feature predicts the gold answer | 0 | no multiple-choice items in this dataset |
| skip | no model reproduces the contamination canary | 0 | no canary probe on disk; run `dinostomp run <spec> --probe canary` to ask whether a model has already read this dataset |
| n/a | no item already appears in a reference dataset | 0 | no reference dataset supplied; pass --against <file> to compare these items against a corpus you have. This never checks training data, and cannot. |
| n/a | no near-duplicate assets | 0 | no item carries an `input_ref`; nothing points at a file |
| ok | witnesses kill the mutant scorers | 4 | 0 of 4 applicable mutant scorer(s) survive the witness suite |
| ok | uncheckable rate is sane | 1440 | 2% of 1440 record(s) are uncheckable |
| ok | accuracy is distinguishable from guessing | 4 | 0 of 4 model(s) score no better than guessing; fleet spans 45% to 86% vs chance ~3% (modal target floor) |
| ok | runs cover the spec's declared scope, nothing foreign | 12 | 0 run(s) outside the spec's declared scope |
| ok | no model selectively escapes the scorer | 4 | 0 of 4 model(s) escape the scorer more than the fleet does |
| skip | the eval is not solvable blind | 0 | no blind probe on disk; run `dinostomp run <spec> --probe blind` to unlock |
| ok | no model collapses onto one answer | 4 | 0 of 4 model(s) answer with one response far more often than any target warrants |
| skip | each model beats its own blind baseline | 0 | no blind probe on disk; run `dinostomp run <spec> --probe blind` to unlock |
| warn | failed answers do not contain the reference | 4 | 3 of 4 model(s) are failed on answers that contain the reference; the scorer may be grading format, not correctness |
| ok | billed output tokens match the recorded text | 4 | 0 of 4 model(s) report far more output tokens than their recorded text accounts for (expected for hidden-reasoning models; otherwise check your invoice) |
| warn | the runs were produced by this engine | 12 | 12 of 12 run(s) were produced by a different engine than the one auditing them (now 7fe879a3183bfcfe); re-run to get numbers this report can stand behind |
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
| ok | fleet score totals are reliable (KR-20) | 1176 | KR-20 0.99 across 4 models x 294 items; small fleet (4 examinees), treat as a noisy estimate |
| ok | no item anti-correlates with fleet skill | 294 | 17 item(s) that strong models miss and weak models hit, against 22 expected by chance at this fleet size; candidate key errors; at 4 examinees this check has little power, so a quiet result is NOT evidence of a clean answer key |
| ok | dead-weight items stay a minority | 294 | 38% of 294 item(s) separate nobody (100 all-right, 12 all-wrong); 25% would be dead at 4 examinees even with no difficulty structure, so part of this is fleet size |
| ok | no unanimous identical wrong answers | 294 | 0 item(s) where the whole fleet gave one identical wrong answer; candidate key errors |
| n/a | entitled ordering claims are separated beyond sampling noise | 0 | no entitled claim asserts a model ordering |
| ok | the fleet is not pinned at a ceiling or floor | 4 | fleet accuracy spans 45% to 86% on 294 item(s) |
| ok | the eval separates the fleet (dynamic range) | 4 | fleet spread 42% across 4 model(s) on 294 item(s) |
| skip | answers survive re-ordering the options | 0 | no shuffle probe on disk; set data.render_choices and run `dinostomp run <spec> --probe shuffle` to unlock |
| warn | the number survives changing the seed | 4 | 2 of 4 model(s) move between seeds by more than the item sample explains; that much of the headline number belongs to the seed |
| skip | the number survives re-phrasing the instruction | 0 | no template probe on disk; run `dinostomp run <spec> --probe template` to unlock |
| skip | the fleet ORDERING survives re-phrasing the instruction | 0 | no template probe on disk; run `dinostomp run <spec> --probe template` to unlock |

### Receipts

<details><summary>[ok] witnesses kill the mutant scorers</summary>

- evidence: `{"killed": ["always-pass", "always-fail", "prefix-lenient", "uncheckable-credit"], "not_applicable": ["case-blind", "space-blind", "substring-lenient", "negation-blind"]}`

</details>
<details><summary>[FAIL] runs match the spec, data, and scorer on disk (no drift)</summary>

- 20260809_032215_bench-gsm8k_meta-llama-llama-3.2-3b-instruct_n120_s7.jsonl: spec, data changed since this run
- 20260809_032358_bench-gsm8k_meta-llama-llama-3.2-3b-instruct_n120_s11.jsonl: spec, data changed since this run
- 20260809_032536_bench-gsm8k_meta-llama-llama-3.2-3b-instruct_n120_s23.jsonl: spec, data changed since this run
- 20260809_032722_bench-gsm8k_meta-llama-llama-3.1-8b-instruct_n120_s7.jsonl: spec, data changed since this run
- 20260809_033755_bench-gsm8k_meta-llama-llama-3.1-8b-instruct_n120_s11.jsonl: spec, data changed since this run
- 20260809_035251_bench-gsm8k_meta-llama-llama-3.1-8b-instruct_n120_s23.jsonl: spec, data changed since this run
- 20260809_040315_bench-gsm8k_mistralai-ministral-8b-2512_n120_s7.jsonl: spec, data changed since this run
- 20260809_040840_bench-gsm8k_mistralai-ministral-8b-2512_n120_s11.jsonl: spec, data changed since this run

</details>
<details><summary>[FAIL] truncated outputs are never credited</summary>

- 20260809_033755_bench-gsm8k_meta-llama-llama-3.1-8b-instruct_n120_s11.jsonl: gsm-0777#r0
- 20260809_033755_bench-gsm8k_meta-llama-llama-3.1-8b-instruct_n120_s11.jsonl: gsm-1168#r0
- 20260809_040315_bench-gsm8k_mistralai-ministral-8b-2512_n120_s7.jsonl: gsm-0181#r0
- 20260809_040840_bench-gsm8k_mistralai-ministral-8b-2512_n120_s11.jsonl: gsm-0697#r0
- 20260809_040840_bench-gsm8k_mistralai-ministral-8b-2512_n120_s11.jsonl: gsm-1122#r0
- 20260809_040840_bench-gsm8k_mistralai-ministral-8b-2512_n120_s11.jsonl: gsm-1227#r0
- 20260809_041419_bench-gsm8k_mistralai-ministral-8b-2512_n120_s23.jsonl: gsm-0323#r0
- 20260809_041419_bench-gsm8k_mistralai-ministral-8b-2512_n120_s23.jsonl: gsm-0138#r0

</details>
<details><summary>[ok] uncheckable rate is sane</summary>

- evidence: `{"rate": 0.0236}`

</details>
<details><summary>[ok] accuracy is distinguishable from guessing</summary>

- evidence: `{"chance_floor": 0.0303, "modal": 0.0303, "modal_target": "5", "per_model_accuracy": {"meta-llama/llama-3.1-8b-instruct": 0.8472, "meta-llama/llama-3.2-3b-instruct": 0.4479, "mistralai/ministral-8b-2512": 0.8611, "qwen/qwen3-30b-a3b-instruct-2507": 0.7889}, "uniform": 0.0}`

</details>
<details><summary>[ok] no model selectively escapes the scorer</summary>

- evidence: `{"rates": {"meta-llama/llama-3.1-8b-instruct": 0.0, "meta-llama/llama-3.2-3b-instruct": 0.0944, "mistralai/ministral-8b-2512": 0.0, "qwen/qwen3-30b-a3b-instruct-2507": 0.0}}`

</details>
<details><summary>[warn] failed answers do not contain the reference</summary>

- meta-llama/llama-3.1-8b-instruct: 14 of 55 failed answer(s) (25%) contain the reference answer verbatim
- mistralai/ministral-8b-2512: 17 of 50 failed answer(s) (34%) contain the reference answer verbatim
- qwen/qwen3-30b-a3b-instruct-2507: 41 of 76 failed answer(s) (54%) contain the reference answer verbatim

</details>
<details><summary>[ok] billed output tokens match the recorded text</summary>

- evidence: `{"billed_ratio": {"meta-llama/llama-3.1-8b-instruct": 1.103, "meta-llama/llama-3.2-3b-instruct": 0.883, "mistralai/ministral-8b-2512": 1.319, "qwen/qwen3-30b-a3b-instruct-2507": 1.392}}`

</details>
<details><summary>[warn] the runs were produced by this engine</summary>

- engine 0c79d2fabc826532: meta-llama/llama-3.2-3b-instruct seed 23 (tool 0.29.0)
- engine 234beba29e95b450: mistralai/ministral-8b-2512 seed 23 (tool 0.29.0)
- engine 37ef5f0f1fd73ba5: qwen/qwen3-30b-a3b-instruct-2507 seed 11 (tool 0.29.0)
- engine 4a653af30fda461e: qwen/qwen3-30b-a3b-instruct-2507 seed 23 (tool 0.29.0)
- engine d70763a8988c3dbd: mistralai/ministral-8b-2512 seed 11 (tool 0.29.0)
- engine e61a7157ccdb2867: meta-llama/llama-3.1-8b-instruct seed 7 (tool 0.29.0), meta-llama/llama-3.1-8b-instruct seed 11 (tool 0.29.0), meta-llama/llama-3.1-8b-instruct seed 23 (tool 0.29.0) and 1 more
- engine fb259f7c35128624: meta-llama/llama-3.2-3b-instruct seed 7 (tool 0.29.0), meta-llama/llama-3.2-3b-instruct seed 11 (tool 0.29.0)
- engine ff2ae460303a18ca: qwen/qwen3-30b-a3b-instruct-2507 seed 7 (tool 0.29.0)
- evidence: `{"engines": {"0c79d2fabc826532": 1, "234beba29e95b450": 1, "37ef5f0f1fd73ba5": 1, "4a653af30fda461e": 1, "d70763a8988c3dbd": 1, "e61a7157ccdb2867": 4, "fb259f7c35128624": 2, "ff2ae460303a18ca": 1}}`

</details>
<details><summary>[ok] fleet score totals are reliable (KR-20)</summary>

- evidence: `{"excluded_collapsed": [], "kr20": 0.988, "n_examinees": 4}`

</details>
<details><summary>[ok] no item anti-correlates with fleet skill</summary>

- evidence: `{"chance_95th": 22, "excluded_collapsed": [], "n_examinees": 4, "negative_rpb": 17, "underpowered": true}`

</details>
<details><summary>[ok] dead-weight items stay a minority</summary>

- evidence: `{"independence_floor": 0.2527, "n_examinees": 4, "share": 0.381}`

</details>
<details><summary>[ok] the fleet is not pinned at a ceiling or floor</summary>

- evidence: `{"max": 0.8639, "min": 0.4456}`

</details>
<details><summary>[ok] the eval separates the fleet (dynamic range)</summary>

- evidence: `{"spread": 0.4184}`

</details>
<details><summary>[warn] the number survives changing the seed</summary>

- meta-llama/llama-3.1-8b-instruct: 78% at seed 11 vs 90% at seed 23 (spread 12% across 3 seeds, vs 9% explainable by the item sample)
- mistralai/ministral-8b-2512: 81% at seed 11 vs 92% at seed 23 (spread 11% across 3 seeds, vs 9% explainable by the item sample)
- evidence: `{"seed_spread": {"meta-llama/llama-3.1-8b-instruct": {"noise_band": 0.092, "spread": 0.125}, "meta-llama/llama-3.2-3b-instruct": {"noise_band": 0.1316, "spread": 0.1154}, "mistralai/ministral-8b-2512": {"noise_band": 0.0861, "spread": 0.1083}, "qwen/qwen3-30b-a3b-instruct-2507": {"noise_band": 0.1029, "spread": 0.0917}}}`

</details>

## Runs

| run file | model | reported as | provider | dry | seed | records | uncheckable |
|---|---|---|---|---|---:|---:|---:|
| 20260809_032215_bench-gsm8k_meta-llama-llama-3.2-3b-instruct_n120_s7.jsonl | meta-llama/llama-3.2-3b-instruct | (same) | openrouter | no | 7 | 120 | 10 |
| 20260809_032358_bench-gsm8k_meta-llama-llama-3.2-3b-instruct_n120_s11.jsonl | meta-llama/llama-3.2-3b-instruct | (same) | openrouter | no | 11 | 120 | 16 |
| 20260809_032536_bench-gsm8k_meta-llama-llama-3.2-3b-instruct_n120_s23.jsonl | meta-llama/llama-3.2-3b-instruct | (same) | openrouter | no | 23 | 120 | 8 |
| 20260809_032722_bench-gsm8k_meta-llama-llama-3.1-8b-instruct_n120_s7.jsonl | meta-llama/llama-3.1-8b-instruct | (same) | openrouter | no | 7 | 120 | 0 |
| 20260809_033755_bench-gsm8k_meta-llama-llama-3.1-8b-instruct_n120_s11.jsonl | meta-llama/llama-3.1-8b-instruct | (same) | openrouter | no | 11 | 120 | 0 |
| 20260809_035251_bench-gsm8k_meta-llama-llama-3.1-8b-instruct_n120_s23.jsonl | meta-llama/llama-3.1-8b-instruct | (same) | openrouter | no | 23 | 120 | 0 |
| 20260809_040315_bench-gsm8k_mistralai-ministral-8b-2512_n120_s7.jsonl | mistralai/ministral-8b-2512 | (same) | openrouter | no | 7 | 120 | 0 |
| 20260809_040840_bench-gsm8k_mistralai-ministral-8b-2512_n120_s11.jsonl | mistralai/ministral-8b-2512 | (same) | openrouter | no | 11 | 120 | 0 |
| 20260809_041419_bench-gsm8k_mistralai-ministral-8b-2512_n120_s23.jsonl | mistralai/ministral-8b-2512 | (same) | openrouter | no | 23 | 120 | 0 |
| 20260809_041953_bench-gsm8k_qwen-qwen3-30b-a3b-instruct-2507_n120_s7.jsonl | qwen/qwen3-30b-a3b-instruct-2507 | (same) | openrouter | no | 7 | 120 | 0 |
| 20260809_043201_bench-gsm8k_qwen-qwen3-30b-a3b-instruct-2507_n120_s11.jsonl | qwen/qwen3-30b-a3b-instruct-2507 | (same) | openrouter | no | 11 | 120 | 0 |
| 20260809_043938_bench-gsm8k_qwen-qwen3-30b-a3b-instruct-2507_n120_s23.jsonl | qwen/qwen3-30b-a3b-instruct-2507 | (same) | openrouter | no | 23 | 120 | 0 |

## Provenance

- tool: dinostomp 0.61.0
- statistical power: at n=120 items, an UNPAIRED comparison (worst case p=0.5) resolves gaps down to ~18% accuracy (80% power, two-sided alpha 0.05); the paired bootstrap behind P6/C1 resolves smaller gaps when model errors overlap
- spec_sha256: `e4434ae46b201444323f04e3a651d6aeb0e163130067bc83e14cd5fef649a39a`
- data_sha256: `168ff4314b8164161ce2f6137ca4b2a3805c5509ad5a89152a6b3d3c090371cc`
- thresholds: all defaults
- reproducibility tiers, stated honestly: local inputs hash-pinned (spec, data, scorer); requests reproducible given each manifest's environment envelope; hosted-model immutability UNKNOWN unless the provider exposes a pinned revision (the runs table records what each provider claims answered)
- raw report: [STOMP.json](STOMP.json) (both files omit volatile fields, so an unchanged pod re-reports to identical bytes; run manifests carry the timestamps)
