# 🦖 stomp report: eval.yaml

**BROKEN**: 3 gated finding(s) (42 of 47 ran; 51 n/a of 98 declared)

measures the intended construct: **NOT ESTABLISHED BY DINOSTOMP**

## Results

> These numbers come from an eval with **gated findings**. They describe what the runs contain; whether they can be published is decided under Checks.

| model | provider | records | checkable | judgeable | accuracy | 95% CI | passes | fails | out tok | spend |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| jevlike-scratch-3ep | python | 1000 | 1000 | 100% | 29.8% | [0.270, 0.327] | 298 | 702 | 0 | $0.0000 |
| meta-llama/llama-3.1-8b-instruct | openrouter | 1000 | 921 | 92% | 17.4% | [0.151, 0.200] | 160 | 761 | 5113 | $0.0369 |
| openai/gpt-5.6-luna | openrouter | 1000 | 994 | 99% | 22.8% | [0.203, 0.255] | 227 | 767 | 4048 | $0.0783 |
| qwen/qwen3-30b-a3b-instruct-2507 | openrouter | 1000 | 913 | 91% | 29.8% | [0.269, 0.328] | 272 | 641 | 4532 | $0.0373 |

Accuracy is ON CHECKABLE output: `judgeable` is the share the scorer reached a verdict on at all, and 80% accurate on 60%-judgeable output is not 80% accurate.

**4 model(s) x 1000 item(s)**, mean 24.9%, spanning 17.4% to 29.8% (12% spread), KR-20 0.96.

31 item(s) every model passed and 436 every model failed: 47% of the set separated nobody in this fleet.

At 1000 items an UNPAIRED comparison resolves gaps down to about 6%; smaller differences between the models above are not distinguishable from sampling noise by that test.

<details><summary>Item difficulty: the 25 hardest of 1000, hardest first</summary>

| item | target | p | discrimination | missed by | most common wrong answer |
|---|---|---:|---:|---|---|
| ws-00000 | Atlantic Ocean | 0% | - | jevlike-scratch-3ep, meta-llama/llama-3.1-8b-instruct, openai/gpt-5.6-luna, qwen/qwen3-30b-a3b-instruct-2507 | h. africa |
| ws-00002 | Niger | 0% | - | jevlike-scratch-3ep, meta-llama/llama-3.1-8b-instruct, openai/gpt-5.6-luna, qwen/qwen3-30b-a3b-instruct-2507 | english peasants' revolt of 1381 |
| ws-00005 | Chemistry | 0% | - | jevlike-scratch-3ep, meta-llama/llama-3.1-8b-instruct, openai/gpt-5.6-luna, qwen/qwen3-30b-a3b-instruct-2507 | karl popper |
| ws-00012 | Ethiopia | 0% | - | jevlike-scratch-3ep, meta-llama/llama-3.1-8b-instruct, openai/gpt-5.6-luna, qwen/qwen3-30b-a3b-instruct-2507 | h. greek mythology |
| ws-00020 | Africa | 0% | - | jevlike-scratch-3ep, meta-llama/llama-3.1-8b-instruct, openai/gpt-5.6-luna | slovenia |
| ws-00027 | Kenya | 0% | - | jevlike-scratch-3ep, meta-llama/llama-3.1-8b-instruct, openai/gpt-5.6-luna, qwen/qwen3-30b-a3b-instruct-2507 | africa |
| ws-00029 | Democratic Republic of the Congo | 0% | - | jevlike-scratch-3ep, openai/gpt-5.6-luna, qwen/qwen3-30b-a3b-instruct-2507 | israel |
| ws-00036 | Geology | 0% | - | jevlike-scratch-3ep, meta-llama/llama-3.1-8b-instruct, openai/gpt-5.6-luna, qwen/qwen3-30b-a3b-instruct-2507 | x. culture |
| ws-00042 | Roman Empire | 0% | - | jevlike-scratch-3ep, meta-llama/llama-3.1-8b-instruct, openai/gpt-5.6-luna, qwen/qwen3-30b-a3b-instruct-2507 | united kingdom |
| ws-00043 | Byzantine Empire | 0% | - | jevlike-scratch-3ep, openai/gpt-5.6-luna, qwen/qwen3-30b-a3b-instruct-2507 | united states |
| ws-00045 | Constantine I | 0% | - | jevlike-scratch-3ep, meta-llama/llama-3.1-8b-instruct, openai/gpt-5.6-luna, qwen/qwen3-30b-a3b-instruct-2507 | nepal |
| ws-00047 | Roman Catholic Church | 0% | - | jevlike-scratch-3ep, meta-llama/llama-3.1-8b-instruct, openai/gpt-5.6-luna | south america |
| ws-00049 | Mesopotamia | 0% | - | jevlike-scratch-3ep, meta-llama/llama-3.1-8b-instruct, openai/gpt-5.6-luna, qwen/qwen3-30b-a3b-instruct-2507 | proton |
| ws-00052 | Earth's atmosphere | 0% | - | jevlike-scratch-3ep, meta-llama/llama-3.1-8b-instruct, openai/gpt-5.6-luna, qwen/qwen3-30b-a3b-instruct-2507 | d. amber |
| ws-00061 | Africa | 0% | - | jevlike-scratch-3ep, meta-llama/llama-3.1-8b-instruct, openai/gpt-5.6-luna, qwen/qwen3-30b-a3b-instruct-2507 | gaza strip |
| ws-00063 | Earth's atmosphere | 0% | - | jevlike-scratch-3ep, meta-llama/llama-3.1-8b-instruct, openai/gpt-5.6-luna, qwen/qwen3-30b-a3b-instruct-2507 | proton |
| ws-00071 | Benzene | 0% | - | jevlike-scratch-3ep, meta-llama/llama-3.1-8b-instruct, openai/gpt-5.6-luna, qwen/qwen3-30b-a3b-instruct-2507 | salt |
| ws-00072 | Human | 0% | - | jevlike-scratch-3ep, meta-llama/llama-3.1-8b-instruct, openai/gpt-5.6-luna, qwen/qwen3-30b-a3b-instruct-2507 | b. chemical element |
| ws-00088 | Fish | 0% | - | jevlike-scratch-3ep, meta-llama/llama-3.1-8b-instruct, openai/gpt-5.6-luna, qwen/qwen3-30b-a3b-instruct-2507 | bird |
| ws-00097 | Oxygen | 0% | - | jevlike-scratch-3ep, meta-llama/llama-3.1-8b-instruct, openai/gpt-5.6-luna, qwen/qwen3-30b-a3b-instruct-2507 | africa |
| ws-00108 | 20th century | 0% | - | jevlike-scratch-3ep, openai/gpt-5.6-luna, qwen/qwen3-30b-a3b-instruct-2507 | united states |
| ws-00119 | Aristotle | 0% | - | jevlike-scratch-3ep, meta-llama/llama-3.1-8b-instruct, openai/gpt-5.6-luna, qwen/qwen3-30b-a3b-instruct-2507 | africa |
| ws-00122 | Roman Empire | 0% | - | jevlike-scratch-3ep, meta-llama/llama-3.1-8b-instruct, openai/gpt-5.6-luna, qwen/qwen3-30b-a3b-instruct-2507 | q. ancient rome |
| ws-00131 | United States | 0% | - | jevlike-scratch-3ep, meta-llama/llama-3.1-8b-instruct, openai/gpt-5.6-luna, qwen/qwen3-30b-a3b-instruct-2507 | d. special relativity |
| ws-00138 | Cotton | 0% | - | jevlike-scratch-3ep, openai/gpt-5.6-luna, qwen/qwen3-30b-a3b-instruct-2507 | united kingdom |

`p` is the share of the fleet that answered correctly and `discrimination` is the point-biserial with fleet skill. Both DESCRIBE; a hard item is not a defect. A negative discrimination is what P2 examines. All 1000 rows are in [STOMP.json](STOMP.json).

</details>

**Cost**: $0.1526 across 1,856,670 input and 13,693 output tokens, summed from the RECORDS. R3 is the check that compares this against the manifest ledger.

## Entitled claims

**None.** The verdict is `broken`; this eval is not currently entitled to publish claims.

## Checks

### Invariants (deterministic, gating)

Facts, not heuristics: a failure here means something is mechanically wrong (a duplicate exists, a hash changed, a number does not re-derive) and it breaks the verdict.

| | check | witnesses | detail |
|---|---|---:|---|
| **FAIL** | questions are unique | 4373 | 305 duplicated question(s) among 4373 |
| **FAIL** | no answer leaks into its own question | 4373 | 17 of 4373 item(s) leak their answer into the question |
| ok | no option offered twice in one item | 4373 | 0 item(s) offer a duplicate option |
| ok | every target is among its choices | 4373 | 0 item(s) whose target is not among their choices |
| **FAIL** | no identical question with contradictory targets | 4373 | 131 question(s) appear with conflicting targets |
| n/a | every referenced asset resolves and still hashes the same | 0 | no item carries an `input_ref`; nothing points at a file |
| n/a | no asset's own path gives away its label | 0 | no item carries an `input_ref`; nothing points at a file |
| n/a | no asset appears in two splits | 0 | no item carries an `input_ref`; nothing points at a file |
| ok | the audit covers the rows it was given | 4373 | 0 of 4373 row(s) were dropped: the pod loader refuses a dataset it cannot read whole, so every row in the file reached the audit |
| n/a | rows are unique | 0 | out of scope for a pod audit (the dataset, the scorer, and every run on disk) |
| n/a | no error value is saved in the workbook | 0 | out of scope for a pod audit (the dataset, the scorer, and every run on disk) |
| n/a | every column aggregate covers its own column | 0 | out of scope for a pod audit (the dataset, the scorer, and every run on disk) |
| n/a | the join returns rows at all | 0 | out of scope for a pod audit (the dataset, the scorer, and every run on disk) |
| n/a | no key fails to match on case or whitespace alone | 0 | out of scope for a pod audit (the dataset, the scorer, and every run on disk) |
| n/a | every parent total equals the sum of its children | 0 | out of scope for a pod audit (the dataset, the scorer, and every run on disk) |
| n/a | a graded scorer witnesses its gradation | 0 | this scorer does not emit intermediate partial credit, so there is no gradation to witness |
| n/a | every typed claim's evidence requirements hold | 0 | no typed claims declared |
| ok | runs match the spec, data, and scorer on disk (no drift) | 4 | 0 of 4 run(s) no longer match the spec, data, or scorer on disk |
| ok | the witness gate replays clean | 14 | replayed 10 witness(es): 10 behaved; 4 run manifest(s) checked |
| ok | ledger spend agrees with the manifest and the spec cap | 4 | 0 money discrepanc(ies) across 4 run(s) |
| ok | every run record is schema-valid, unique, and its manifest's own | 4000 | 0 integrity problem(s) across 4000 record(s) |
| ok | truncated outputs are never credited | 4000 | 0 truncated output(s) scored as pass; a cut-off response can still have stated its answer, so read these before raising max_tokens and re-running |
| ok | recorded verdicts re-score identically | 4000 | 0 of 4000 recorded verdict(s) do not reproduce under the current scorer |
| ok | summaries match their run records | 4 | 0 summary discrepanc(ies) across 4 run(s) |
| ok | records cover exactly the seeded selection | 4 | 0 of 4 run(s) do not cover their seeded selection |
| ok | every model produced something scoreable | 4 | 0 of 4 model(s) produced nothing scoreable |
| n/a | graded scores stay in range | 0 | no record carries a graded value |
| n/a | no forbidden tool is called | 0 | no forbidden_tools declared in the spec |
| n/a | every required tool is actually called | 0 | no required_tools declared in the spec |
| ok | trajectories are well-formed | 1000 | 0 malformed trajector(ies) of 1000 |
| ok | every model was asked the same items | 4 | 0 of 4 model(s) were asked a different item set |

### Diagnostics (statistical, advisory)

Threshold-based signals: they warn, expose their underlying values, and can have legitimate explanations. A warning is evidence of possible trouble, never a proof of invalidity.

| | check | witnesses | detail |
|---|---|---:|---|
| ok | gold answer does not favour an option position | 4373 | gold overshoots position 15 by +0% over its per-item expectation (110 of 4373) |
| ok | gold answer is not systematically the longest option | 4373 | gold is strictly longest -1% over its per-item expectation (123 of 4373) |
| ok | a contamination canary travels with the data | 1 | canary present (dinostomp canary DO NOT TRAIN jevlike-wi...) |
| ok | no surface feature predicts the gold answer | 4373 | 0 surface feature(s) beat the per-item chance null on 4373 keyed item(s) |
| skip | no model reproduces the contamination canary | 0 | no canary probe on disk; run `dinostomp run <spec> --probe canary` to ask whether a model has already read this dataset |
| n/a | no item already appears in a reference dataset | 0 | no reference dataset supplied; pass --against <file> to compare these items against a corpus you have. This never checks training data, and cannot. |
| n/a | no near-duplicate assets | 0 | no item carries an `input_ref`; nothing points at a file |
| n/a | the eval is not authored in a circle | 0 | no provenance declared, so authorship is not described. Declaring who wrote the items, keys, scorer, and witnesses lets this surface a model sitting on both sides of a loop (e.g. keying its own questions) |
| n/a | no single column all but determines the target | 0 | an eval pod's items are questions and answers, not a feature table; the single-column leak scan is for a raw tabular dataset audit |
| n/a | no two options are the same number written differently | 0 | no item offers two options that both parse as numbers, so there is no numeric equivalence to check |
| ok | no two items are the same question in different encodings | 4373 | 0 group(s) of items are the same question in different encodings |
| ok | the answer key is not dominated by one value | 4373 | the answer key is not dominated by one value (modal 3% of 1086 answers) |
| n/a | no cell carries edge whitespace or invisible characters | 0 | out of scope for a pod audit (the dataset, the scorer, and every run on disk) |
| n/a | no identifier column repeats a value | 0 | out of scope for a pod audit (the dataset, the scorer, and every run on disk) |
| n/a | no digit-string column has leading zeros a conversion would destroy | 0 | out of scope for a pod audit (the dataset, the scorer, and every run on disk) |
| n/a | no date column mixes formats or reads both ways | 0 | out of scope for a pod audit (the dataset, the scorer, and every run on disk) |
| n/a | no numeric column is contaminated with text | 0 | out of scope for a pod audit (the dataset, the scorer, and every run on disk) |
| n/a | no value stands in for missing without saying so | 0 | out of scope for a pod audit (the dataset, the scorer, and every run on disk) |
| n/a | no category column splits one label across spellings | 0 | out of scope for a pod audit (the dataset, the scorer, and every run on disk) |
| n/a | no rate column mixes fraction and percent scales | 0 | out of scope for a pod audit (the dataset, the scorer, and every run on disk) |
| n/a | no numeric column stores symbols or separators | 0 | out of scope for a pod audit (the dataset, the scorer, and every run on disk) |
| n/a | no rows are duplicates once case and whitespace stop counting | 0 | out of scope for a pod audit (the dataset, the scorer, and every run on disk) |
| n/a | no constant is pasted inside a formula column | 0 | out of scope for a pod audit (the dataset, the scorer, and every run on disk) |
| n/a | nothing an aggregate counts is hidden from the reader | 0 | out of scope for a pod audit (the dataset, the scorer, and every run on disk) |
| n/a | no merged range flattens a row on import | 0 | out of scope for a pod audit (the dataset, the scorer, and every run on disk) |
| n/a | every formula has been calculated | 0 | out of scope for a pod audit (the dataset, the scorer, and every run on disk) |
| n/a | no left row is dropped by the join | 0 | out of scope for a pod audit (the dataset, the scorer, and every run on disk) |
| n/a | the right-hand key is unique | 0 | out of scope for a pod audit (the dataset, the scorer, and every run on disk) |
| n/a | the join does not multiply rows | 0 | out of scope for a pod audit (the dataset, the scorer, and every run on disk) |
| n/a | both sides store the key the same way | 0 | out of scope for a pod audit (the dataset, the scorer, and every run on disk) |
| ok | witnesses kill the mutant scorers | 7 | 0 of 7 applicable mutant scorer(s) survive the witness suite |
| n/a | a correct answer survives its surface form | 0 | this scorer compares exactly rather than extracting, so surface-form robustness is not a property it claims |
| n/a | an exact scorer is not graded against prose answers | 0 | the scorer does not compare bare strings, so it is not the exact-match-on-prose mismatch this looks for |
| ok | uncheckable rate is sane | 4000 | 4% of 4000 record(s) are uncheckable |
| ok | accuracy is distinguishable from guessing | 4 | 0 of 4 model(s) score no better than guessing; fleet spans 17% to 30% vs chance ~4% (uniform choice floor) |
| ok | runs cover the spec's declared scope, nothing foreign | 4 | 0 run(s) outside the spec's declared scope |
| ok | no model selectively escapes the scorer | 4 | 0 of 4 model(s) escape the scorer more than the fleet does |
| ok | the eval is not solvable blind | 4 | 0 of 4 model(s) solve the eval blind, above the informed-guesser floor 4%; the items are answerable WITHOUT the question |
| warn | no model collapses onto one answer | 4 | 1 of 4 model(s) answer with one response far more often than any target warrants |
| ok | each model beats its own blind baseline | 4 | 0 of 4 model(s) score no better informed than blind; their numbers are not evidence about this task (unpaired: separate runs) |
| ok | failed answers do not contain the reference | 4 | 0 of 4 model(s) are failed on answers that contain the reference; the scorer may be grading format, not correctness |
| n/a | billed output tokens match the recorded text | 0 | no model produced 20+ answers of at least 40 characters; short-answer evals cannot be billed against reliably |
| ok | the runs were produced by this engine | 4 | 0 of 4 run(s) were produced by a different engine than the one auditing them (now 28bbac03bc6fc06b); re-run to get numbers this report can stand behind |
| n/a | repeated items reached a verdict | 0 | no run on disk repeats an item; a single pass per item cannot tie |
| n/a | no failed answer numerically equals its target | 0 | no failed record has a numeric target, so there is no numeric-equivalent miss to look for |
| ok | passing answers are grounded in tool evidence | 1 | 0 of 1 target(s) pass items whose answer does not APPEAR in their own evidence (0 such answer(s) in total). This is co-occurrence, not causation: an answer recalled from memory that also happens to appear in a retrieved snippet counts as grounded here, so this count is a floor |
| n/a | no model under-reports its trajectory | 0 | only 1 python-target model on disk; under-reporting is fleet-relative |
| ok | tool calls are not redundant | 1 | 0 of 1 target(s) repeat identical calls in more than 25% of their trajectories |
| n/a | passing answers CHANGE when their evidence is withheld | 0 | no mediated agent on disk; only the harness can withhold a tool result, and a self-reporting target calls its own functions |
| ok | the trajectory was observed, not self-reported | 1 | all 1 target(s) write their own trajectory, so T1-T6 verify the RECORD and not the EXECUTION: a target that omits a call from its own trace cannot be caught by reading it. Supported and stated, not a defect. Provider `mediated` moves the tools into the harness if you want the trace to be a log |
| n/a | the judge agrees with cases whose answer is known | 0 | this eval does not score with a judge |
| n/a | the judge is invariant to content-free perturbations | 0 | this eval does not score with a judge |
| n/a | the judge agrees with itself on identical input | 0 | this eval does not score with a judge |
| n/a | the judge does not favour its own family | 0 | this eval does not score with a judge |
| ok | fleet score totals are reliable (KR-20) | 3380 | KR-20 0.96 across 4 models x 845 items; small fleet (4 examinees), treat as a noisy estimate |
| ok | no item anti-correlates with fleet skill | 845 | 94 item(s) that strong models miss and weak models hit, against 107 expected by chance at this fleet size; candidate key errors; at 4 examinees this check has little power, so a quiet result is NOT evidence of a clean answer key |
| warn | dead-weight items stay a minority | 845 | 55% of 845 item(s) separate nobody (31 all-right, 436 all-wrong); 33% would be dead at 4 examinees even with no difficulty structure, so part of this is fleet size |
| ok | no unanimous identical wrong answers | 845 | 0 item(s) where the whole fleet gave one identical wrong answer; candidate key errors |
| n/a | entitled ordering claims are separated beyond sampling noise | 0 | no entitled claim asserts a model ordering |
| ok | the fleet is not pinned at a ceiling or floor | 4 | fleet accuracy spans 17% to 30% on 845 item(s) |
| ok | the eval separates the fleet (dynamic range) | 4 | fleet spread 13% across 4 model(s) on 845 item(s) |
| skip | answers survive re-ordering the options | 0 | no shuffle probe on disk; set data.render_choices and run `dinostomp run <spec> --probe shuffle` to unlock |
| n/a | the number survives changing the seed | 0 | the spec declares no extra seeds; a single seed cannot show its own spread (run.seeds is how you ask) |
| skip | the number survives re-phrasing the instruction | 0 | no template probe on disk; run `dinostomp run <spec> --probe template` to unlock |
| skip | the fleet ORDERING survives re-phrasing the instruction | 0 | no template probe on disk; run `dinostomp run <spec> --probe template` to unlock |
| skip | the fleet varies on one axis, not a blend of abilities | 0 | 4 model(s) x 845 common item(s); need 6+ models and 5+ items to unlock |
| n/a | declared subskills actually separate in the responses | 0 | no item declares a `subskill`; there is no partition to test |

Re-derive this report from the directory holding the target: `dinostomp stomp eval.yaml`

### Receipts

<details><summary>[FAIL] questions are unique</summary>

- target article: ivory current article: achilles #copyright achilles 2007 schools
- target article: ivory current article: achilles tendon #copyright achilles tendo
- target article: ivory current article: elephant #copyright elephant 2007 schools
- target article: peace current article: nobel peace prize #copyright nobel peace 
- target article: parrot current article: salt #copyright salt 2007 schools wikipe
- target article: parrot current article: bird #copyright bird 2007 schools wikipe
- target article: parrot current article: electricity #copyright electricity 2007 
- target article: parrot current article: recycling #copyright recycling 2007 scho
- refs (item): `ws-00010`, `ws-00012`, `ws-00030`, `ws-00011`, `ws-00015`, `ws-00021`, `ws-00024`, `ws-00026` (+24 more in STOMP.json)

</details>
<details><summary>[FAIL] no answer leaks into its own question</summary>

- ws-00356: correct option 'watch' appears in the stem and no distractor does
- ws-00357: correct option 'watch' appears in the stem and no distractor does
- ws-00610: correct option 'force' appears in the stem and no distractor does
- ws-00614: correct option 'force' appears in the stem and no distractor does
- ws-01214: correct option 'art' appears in the stem and no distractor does
- ws-02094: correct option 'latin' appears in the stem and no distractor does
- ws-02164: correct option 'united states' appears in the stem and no distractor does
- ws-02172: correct option 'equatorial guinea' appears in the stem and no distractor does
- refs (item): `ws-00356`, `ws-00357`, `ws-00610`, `ws-00614`, `ws-01214`, `ws-02094`, `ws-02164`, `ws-02172` (+9 more in STOMP.json)

</details>
<details><summary>[ok] gold answer does not favour an option position</summary>

- evidence: `{"chance_rate_at_this_n": 0.0, "excess": 0.0028, "position": 15}`

</details>
<details><summary>[ok] gold answer is not systematically the longest option</summary>

- evidence: `{"excess": -0.0081}`

</details>
<details><summary>[FAIL] no identical question with contradictory targets</summary>

- target article: ivory current article: achilles #copyright achilles 2007 schools
- target article: parrot current article: salt #copyright salt 2007 schools wikipe
- target article: parrot current article: electricity #copyright electricity 2007 
- target article: parrot current article: recycling #copyright recycling 2007 scho
- target article: parrot current article: aluminium chloride #copyright aluminium 
- target article: parrot current article: rainforest #copyright rainforest 2007 sc
- target article: neil armstrong current article: archbishop of canterbury #copyri
- target article: backgammon current article: chess #copyright chess 2007 schools 
- refs (item): `ws-00010`, `ws-00012`, `ws-00030`, `ws-00046`, `ws-00055`, `ws-00086`, `ws-00049`, `ws-00052` (+24 more in STOMP.json)

</details>
<details><summary>[ok] the answer key is not dominated by one value</summary>

- evidence: `{"modal_share": 0.035, "modal_value": "united states", "n_distinct": 1086}`

</details>
<details><summary>[ok] the audit covers the rows it was given</summary>

- evidence: `{"dropped_share": 0.0, "gate": 0.01, "rows_audited": 4373, "rows_dropped": 0, "rows_read": 4373}`

</details>
<details><summary>[ok] witnesses kill the mutant scorers</summary>

- evidence: `{"killed": ["always-pass", "always-fail", "case-blind", "space-blind", "substring-lenient", "prefix-lenient", "negation-blind"], "not_applicable": ["uncheckable-credit"]}`

</details>
<details><summary>[ok] uncheckable rate is sane</summary>

- evidence: `{"rate": 0.043}`

</details>
<details><summary>[ok] accuracy is distinguishable from guessing</summary>

- evidence: `{"chance_floor": 0.0362, "modal": 0.0348, "modal_target": "united states", "per_model_accuracy": {"jevlike-scratch-3ep": 0.298, "meta-llama/llama-3.1-8b-instruct": 0.1737, "openai/gpt-5.6-luna": 0.2284, "qwen/qwen3-30b-a3b-instruct-2507": 0.2979}, "uniform": 0.0362}`

</details>
<details><summary>[ok] no model selectively escapes the scorer</summary>

- evidence: `{"rates": {"jevlike-scratch-3ep": 0.0, "meta-llama/llama-3.1-8b-instruct": 0.079, "openai/gpt-5.6-luna": 0.006, "qwen/qwen3-30b-a3b-instruct-2507": 0.087}}`

</details>
<details><summary>[ok] the eval is not solvable blind</summary>

- evidence: `{"floor": 0.0362}`

</details>
<details><summary>[warn] no model collapses onto one answer</summary>

- openai/gpt-5.6-luna: gave '' to 49% of 994 item(s), while the most common target covers only 3%

</details>
<details><summary>[ok] each model beats its own blind baseline</summary>

- evidence: `{"lift": {"jevlike-scratch-3ep": 0.248, "meta-llama/llama-3.1-8b-instruct": 0.1397, "openai/gpt-5.6-luna": 0.2144, "qwen/qwen3-30b-a3b-instruct-2507": 0.2339}}`

</details>
<details><summary>[ok] the runs were produced by this engine</summary>

- evidence: `{"engines": {"28bbac03bc6fc06b": 4}}`

</details>
<details><summary>[ok] passing answers are grounded in tool evidence</summary>

- evidence: `{"measures": "co-occurrence in the recorded trace, not causal use", "models_judged": 1, "ungrounded_records": 0}`

</details>
<details><summary>[ok] the trajectory was observed, not self-reported</summary>

- evidence: `{"isolation": ["n/a"], "trajectory_sources": {"self_reported": ["jevlike-scratch-3ep"]}}`

</details>
<details><summary>[ok] fleet score totals are reliable (KR-20)</summary>

- evidence: `{"excluded_collapsed": [], "kr20": 0.9626, "n_examinees": 4}`

</details>
<details><summary>[ok] no item anti-correlates with fleet skill</summary>

- evidence: `{"chance_95th": 107, "excluded_collapsed": [], "n_examinees": 4, "negative_rpb": 94, "underpowered": true}`

</details>
<details><summary>[warn] dead-weight items stay a minority</summary>

- evidence: `{"independence_floor": 0.329, "n_examinees": 4, "share": 0.5527}`

</details>
<details><summary>[ok] the fleet is not pinned at a ceiling or floor</summary>

- evidence: `{"max": 0.2994, "min": 0.1692}`

</details>
<details><summary>[ok] the eval separates the fleet (dynamic range)</summary>

- evidence: `{"spread": 0.1302}`

</details>

## Runs

| run file | model | reported as | provider | dry | seed | records | uncheckable |
|---|---|---|---|---|---:|---:|---:|
| 20260917_115655_jevlike-wikispeedia_jevlike-scratch-3ep_n1000_s42.jsonl | jevlike-scratch-3ep | (same) | python | no | 42 | 1000 | 0 |
| 20260917_115703_jevlike-wikispeedia_meta-llama-llama-3.1-8b-instruct_n1000_s42.jsonl | meta-llama/llama-3.1-8b-instruct | (same) | openrouter | no | 42 | 1000 | 79 |
| 20260917_120848_jevlike-wikispeedia_qwen-qwen3-30b-a3b-instruct-2507_n1000_s42.jsonl | qwen/qwen3-30b-a3b-instruct-2507 | (same) | openrouter | no | 42 | 1000 | 87 |
| 20260917_123122_jevlike-wikispeedia_openai-gpt-5.6-luna_n1000_s42.jsonl | openai/gpt-5.6-luna | (same) | openrouter | no | 42 | 1000 | 6 |

## Provenance

- tool: dinostomp 0.63.0
- statistical power: at n=1000 items, an UNPAIRED comparison (worst case p=0.5) resolves gaps down to ~6% accuracy (80% power, two-sided alpha 0.05); the paired bootstrap behind P6/C1 resolves smaller gaps when model errors overlap
- spec_sha256: `b52f65156647245ed2aa273a6badf3e21f22dd33b463e69fcdfb9aebb8808820`
- data_sha256: `8423ec7c5c9693d451f46b6f153f52262d3b01ec736efe53aaf9cd164cd6ae18`
- scorer_sha256: `9976a9e63aa1b04303b309d5ae68202b4956a893c9176cc09842b662a646c8a8`
- target_sha256: `{'jevlike-scratch-3ep': '4b39b66e855147ba8863394a5d95ef2ed8e7d9abaeb2984624db6cbe63526c02'}`
- thresholds: all defaults
- reproducibility tiers, stated honestly: local inputs hash-pinned (spec, data, scorer); requests reproducible given each manifest's environment envelope; hosted-model immutability UNKNOWN unless the provider exposes a pinned revision (the runs table records what each provider claims answered)
- raw report: [STOMP.json](STOMP.json) (both files omit volatile fields, so an unchanged pod re-reports to identical bytes; run manifests carry the timestamps)
