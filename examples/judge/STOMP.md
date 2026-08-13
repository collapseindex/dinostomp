# 🦖 stomp report: eval.yaml

**INCOMPLETE**: no failures, but only 32 of 38 checks ran (32 of 38 ran; 27 n/a of 65 declared). Not a clean bill of health.

## Results

> These numbers come from an eval with **incomplete coverage**. They describe what the runs contain; whether they can be published is decided under Checks.

| model | provider | records | checkable | judgeable | accuracy | 95% CI | passes | fails | out tok | spend |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| bot-bare | python | 26 | 26 | 100% | 84.6% | [0.665, 0.939] | 22 | 4 | 0 | $0.0000 |
| bot-chatty | python | 26 | 26 | 100% | 26.9% | [0.137, 0.461] | 7 | 19 | 0 | $0.0000 |
| bot-hedged | python | 26 | 26 | 100% | 38.5% | [0.224, 0.575] | 10 | 16 | 0 | $0.0000 |
| bot-wrapped | python | 26 | 26 | 100% | 61.5% | [0.425, 0.776] | 16 | 10 | 0 | $0.0000 |

Accuracy is ON CHECKABLE output: `judgeable` is the share the scorer reached a verdict on at all, and 80% accurate on 60%-judgeable output is not 80% accurate.

**4 model(s) x 26 item(s)**, mean 52.9%, spanning 26.9% to 84.6% (58% spread), KR-20 0.94.

7 item(s) every model passed and 4 every model failed: 42% of the set separated nobody in this fleet.

At 26 items an UNPAIRED comparison resolves gaps down to about 39%; smaller differences between the models above are not distinguishable from sampling noise by that test.

<details><summary>Item difficulty: the 25 hardest of 26, hardest first</summary>

| item | target | p | discrimination | missed by | most common wrong answer |
|---|---|---:|---:|---|---|
| cap-athens | Greece | 0% | - | bot-bare, bot-chatty, bot-hedged, bot-wrapped | tunisia |
| cap-copenhagen | Denmark | 0% | - | bot-bare, bot-chatty, bot-hedged, bot-wrapped | norway |
| cap-rabat | Morocco | 0% | - | bot-bare, bot-chatty, bot-hedged, bot-wrapped | japan |
| cap-santiago | Chile | 0% | - | bot-bare, bot-chatty, bot-hedged, bot-wrapped | ireland |
| cap-amman | Jordan | 25% | +0.80 | bot-chatty, bot-hedged, bot-wrapped | great question! after thinking it throug |
| cap-dublin | Ireland | 25% | +0.80 | bot-chatty, bot-hedged, bot-wrapped | great question! after thinking it throug |
| cap-havana | Cuba | 25% | +0.80 | bot-chatty, bot-hedged, bot-wrapped | great question! after thinking it throug |
| cap-kathmandu | Nepal | 25% | +0.80 | bot-chatty, bot-hedged, bot-wrapped | great question! after thinking it throug |
| cap-reykjavik | Iceland | 25% | +0.80 | bot-chatty, bot-hedged, bot-wrapped | great question! after thinking it throug |
| cap-stockholm | Sweden | 25% | +0.80 | bot-chatty, bot-hedged, bot-wrapped | great question! after thinking it throug |
| cap-hanoi | Vietnam | 50% | +0.89 | bot-chatty, bot-hedged | great question! after thinking it throug |
| cap-helsinki | Finland | 50% | +0.89 | bot-chatty, bot-hedged | great question! after thinking it throug |
| cap-lima | Peru | 50% | +0.89 | bot-chatty, bot-hedged | great question! after thinking it throug |
| cap-quito | Ecuador | 50% | +0.89 | bot-chatty, bot-hedged | great question! after thinking it throug |
| cap-tokyo | Japan | 50% | +0.89 | bot-chatty, bot-hedged | great question! after thinking it throug |
| cap-tunis | Tunisia | 50% | +0.89 | bot-chatty, bot-hedged | great question! after thinking it throug |
| cap-canberra | Australia | 75% | +0.63 | bot-chatty | great question! after thinking it throug |
| cap-lisbon | Portugal | 75% | +0.63 | bot-chatty | great question! after thinking it throug |
| cap-warsaw | Poland | 75% | +0.63 | bot-chatty | great question! after thinking it throug |
| cap-budapest | Hungary | 100% | - | - | - |
| cap-cairo | Egypt | 100% | - | - | - |
| cap-nairobi | Kenya | 100% | - | - | - |
| cap-oslo | Norway | 100% | - | - | - |
| cap-ottawa | Canada | 100% | - | - | - |
| cap-paris | France | 100% | - | - | - |

`p` is the share of the fleet that answered correctly and `discrimination` is the point-biserial with fleet skill. Both DESCRIBE; a hard item is not a defect. A negative discrimination is what P2 examines. All 26 rows are in [STOMP.json](STOMP.json).

</details>

**Cost**: $0.0000 across 0 input and 0 output tokens, summed from the RECORDS. R3 is the check that compares this against the manifest ledger.

## Entitled claims

**None.** The verdict is `incomplete`; this eval is not currently entitled to publish claims.

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
| n/a | a graded scorer witnesses its gradation | 0 | this scorer does not emit intermediate partial credit, so there is no gradation to witness |
| n/a | every typed claim's evidence requirements hold | 0 | no typed claims declared |
| ok | runs match the spec, data, and scorer on disk (no drift) | 4 | 0 of 4 run(s) no longer match the spec, data, or scorer on disk |
| ok | the witness gate replays clean | 10 | replayed 6 witness(es): 6 behaved; 4 run manifest(s) checked |
| ok | ledger spend agrees with the manifest and the spec cap | 4 | 0 money discrepanc(ies) across 4 run(s) |
| ok | every run record is schema-valid, unique, and its manifest's own | 104 | 0 integrity problem(s) across 104 record(s) |
| ok | truncated outputs are never credited | 104 | 0 truncated output(s) scored as pass; a cut-off response can still have stated its answer, so read these before raising max_tokens and re-running |
| ok | recorded verdicts re-score identically | 104 | 0 of 104 recorded verdict(s) do not reproduce under the judge's recorded responses |
| ok | summaries match their run records | 4 | 0 summary discrepanc(ies) across 4 run(s) |
| ok | records cover exactly the seeded selection | 4 | 0 of 4 run(s) do not cover their seeded selection |
| ok | every model produced something scoreable | 4 | 0 of 4 model(s) produced nothing scoreable |
| n/a | graded scores stay in range | 0 | no record carries a graded value |
| n/a | no forbidden tool is called | 0 | no python target reported a trajectory and no trajectory policy is declared; this pod is not an agent eval |
| n/a | every required tool is actually called | 0 | no python target reported a trajectory and no trajectory policy is declared; this pod is not an agent eval |
| n/a | trajectories are well-formed | 0 | no python target reported a trajectory and no trajectory policy is declared; this pod is not an agent eval |
| ok | every model was asked the same items | 4 | 0 of 4 model(s) were asked a different item set |

### Diagnostics (statistical, advisory)

Threshold-based signals: they warn, expose their underlying values, and can have legitimate explanations. A warning is evidence of possible trouble, never a proof of invalidity.

| | check | witnesses | detail |
|---|---|---:|---|
| n/a | gold answer does not favour an option position | 0 | no multiple-choice items in this dataset |
| n/a | gold answer is not systematically the longest option | 0 | no multiple-choice items in this dataset |
| ok | a contamination canary travels with the data | 1 | canary present (dinostomp-judge-capitals-canary-2b91d7e4...) |
| n/a | no surface feature predicts the gold answer | 0 | no multiple-choice items in this dataset |
| skip | no model reproduces the contamination canary | 0 | no canary probe on disk; run `dinostomp run <spec> --probe canary` to ask whether a model has already read this dataset |
| n/a | no item already appears in a reference dataset | 0 | no reference dataset supplied; pass --against <file> to compare these items against a corpus you have. This never checks training data, and cannot. |
| n/a | no near-duplicate assets | 0 | no item carries an `input_ref`; nothing points at a file |
| n/a | the eval is not authored in a circle | 0 | no provenance declared, so authorship is not described. Declaring who wrote the items, keys, scorer, and witnesses lets this surface a model sitting on both sides of a loop (e.g. keying its own questions) |
| ok | witnesses kill the mutant scorers | 4 | 0 of 4 applicable mutant scorer(s) survive the witness suite |
| ok | a correct answer survives its surface form | 7 | 0 surface form(s) lose a correct answer and 0 credit a decoy, of 7 applicable |
| ok | uncheckable rate is sane | 104 | 0% of 104 record(s) are uncheckable |
| ok | accuracy is distinguishable from guessing | 4 | 0 of 4 model(s) score no better than guessing; fleet spans 27% to 85% vs chance ~4% (modal target floor) |
| ok | runs cover the spec's declared scope, nothing foreign | 4 | 0 run(s) outside the spec's declared scope |
| ok | no model selectively escapes the scorer | 4 | 0 of 4 model(s) escape the scorer more than the fleet does |
| skip | the eval is not solvable blind | 0 | no blind probe on disk; run `dinostomp run <spec> --probe blind` to unlock |
| ok | no model collapses onto one answer | 4 | 0 of 4 model(s) answer with one response far more often than any target warrants |
| skip | each model beats its own blind baseline | 0 | no blind probe on disk; run `dinostomp run <spec> --probe blind` to unlock |
| ok | failed answers do not contain the reference | 3 | 0 of 3 model(s) are failed on answers that contain the reference; the scorer may be grading format, not correctness |
| n/a | billed output tokens match the recorded text | 0 | no model produced 20+ answers of at least 40 characters; short-answer evals cannot be billed against reliably |
| warn | the runs were produced by this engine | 4 | 4 of 4 run(s) were produced by a different engine than the one auditing them (now b9ab3bafd9ca76fd); re-run to get numbers this report can stand behind |
| n/a | repeated items reached a verdict | 0 | no run on disk repeats an item; a single pass per item cannot tie |
| n/a | passing answers are grounded in tool evidence | 0 | no python target reported a trajectory and no trajectory policy is declared; this pod is not an agent eval |
| n/a | no model under-reports its trajectory | 0 | no python target reported a trajectory and no trajectory policy is declared; this pod is not an agent eval |
| n/a | tool calls are not redundant | 0 | no python target reported a trajectory and no trajectory policy is declared; this pod is not an agent eval |
| n/a | passing answers CHANGE when their evidence is withheld | 0 | no python target reported a trajectory and no trajectory policy is declared; this pod is not an agent eval |
| n/a | the trajectory was observed, not self-reported | 0 | no python target reported a trajectory and no trajectory policy is declared; this pod is not an agent eval |
| ok | the judge agrees with cases whose answer is known | 16 | the judge agrees with 100% of 16 case(s) whose verdict is known by construction (0 wrong answer(s) passed) |
| ok | the judge is invariant to content-free perturbations | 96 | 0 of 6 content-free perturbation(s) change the judge's mind across 96 regraded case(s) |
| ok | the judge agrees with itself on identical input | 16 | the judge contradicts itself on 0 of 16 case(s) (0%) regraded on byte-identical input |
| n/a | the judge does not favour its own family | 0 | no `cross_judge` declared; self-preference is not measurable with one judge, so this is a missing instrument rather than a clean result |
| ok | fleet score totals are reliable (KR-20) | 104 | KR-20 0.94 across 4 models x 26 items; small fleet (4 examinees), treat as a noisy estimate |
| ok | no item anti-correlates with fleet skill | 26 | 0 item(s) that strong models miss and weak models hit, against 0 expected by chance at this fleet size; candidate key errors; at 4 examinees this check has little power, so a quiet result is NOT evidence of a clean answer key |
| ok | dead-weight items stay a minority | 26 | 42% of 26 item(s) separate nobody (7 all-right, 4 all-wrong); 8% would be dead at 4 examinees even with no difficulty structure, so part of this is fleet size |
| ok | no unanimous identical wrong answers | 26 | 0 item(s) where the whole fleet gave one identical wrong answer; candidate key errors |
| n/a | entitled ordering claims are separated beyond sampling noise | 0 | no entitled claim asserts a model ordering |
| ok | the fleet is not pinned at a ceiling or floor | 4 | fleet accuracy spans 27% to 85% on 26 item(s) |
| ok | the eval separates the fleet (dynamic range) | 4 | fleet spread 58% across 4 model(s) on 26 item(s) |
| skip | answers survive re-ordering the options | 0 | no shuffle probe on disk; set data.render_choices and run `dinostomp run <spec> --probe shuffle` to unlock |
| n/a | the number survives changing the seed | 0 | the spec declares no extra seeds; a single seed cannot show its own spread (run.seeds is how you ask) |
| skip | the number survives re-phrasing the instruction | 0 | no template probe on disk; run `dinostomp run <spec> --probe template` to unlock |
| skip | the fleet ORDERING survives re-phrasing the instruction | 0 | no template probe on disk; run `dinostomp run <spec> --probe template` to unlock |

### Receipts

<details><summary>[ok] witnesses kill the mutant scorers</summary>

- evidence: `{"killed": ["always-pass", "always-fail", "prefix-lenient", "negation-blind"], "not_applicable": ["case-blind", "space-blind", "substring-lenient", "uncheckable-credit"]}`

</details>
<details><summary>[ok] a correct answer survives its surface form</summary>

- evidence: `{"baseline_form": "labelled", "held": ["trailing-punctuation", "surrounding-whitespace", "markdown-emphasis", "label-case", "answer-case", "keyword-in-prose", "reasoning-prefix"], "not_applicable": ["decoy-in-working"]}`

</details>
<details><summary>[ok] uncheckable rate is sane</summary>

- evidence: `{"rate": 0.0}`

</details>
<details><summary>[ok] accuracy is distinguishable from guessing</summary>

- evidence: `{"chance_floor": 0.0385, "modal": 0.0385, "modal_target": "france", "per_model_accuracy": {"bot-bare": 0.8462, "bot-chatty": 0.2692, "bot-hedged": 0.3846, "bot-wrapped": 0.6154}, "uniform": 0.0}`

</details>
<details><summary>[ok] no model selectively escapes the scorer</summary>

- evidence: `{"rates": {"bot-bare": 0.0, "bot-chatty": 0.0, "bot-hedged": 0.0, "bot-wrapped": 0.0}}`

</details>
<details><summary>[warn] the runs were produced by this engine</summary>

- engine 050e2f343915e1b9: bot-bare seed 42 (tool 0.57.1), bot-chatty seed 42 (tool 0.57.1), bot-hedged seed 42 (tool 0.57.1) and 1 more
- evidence: `{"engines": {"050e2f343915e1b9": 4}}`

</details>
<details><summary>[ok] the judge agrees with cases whose answer is known</summary>

- evidence: `{"agreement": 1.0, "false_passes": 0}`

</details>
<details><summary>[ok] the judge is invariant to content-free perturbations</summary>

- evidence: `{"biased_perturbations": [], "inflating": []}`

</details>
<details><summary>[ok] the judge agrees with itself on identical input</summary>

- evidence: `{"inconsistency": 0.0}`

</details>
<details><summary>[ok] fleet score totals are reliable (KR-20)</summary>

- evidence: `{"excluded_collapsed": [], "kr20": 0.9401, "n_examinees": 4}`

</details>
<details><summary>[ok] no item anti-correlates with fleet skill</summary>

- evidence: `{"chance_95th": 0, "excluded_collapsed": [], "n_examinees": 4, "negative_rpb": 0, "underpowered": true}`

</details>
<details><summary>[ok] dead-weight items stay a minority</summary>

- evidence: `{"independence_floor": 0.0805, "n_examinees": 4, "share": 0.4231}`

</details>
<details><summary>[ok] the fleet is not pinned at a ceiling or floor</summary>

- evidence: `{"max": 0.8462, "min": 0.2692}`

</details>
<details><summary>[ok] the eval separates the fleet (dynamic range)</summary>

- evidence: `{"spread": 0.5769}`

</details>

## Runs

| run file | model | reported as | provider | dry | seed | records | uncheckable |
|---|---|---|---|---|---:|---:|---:|
| 20260810_110457_judge-capitals_bot-bare_n26_s42.jsonl | bot-bare | (same) | python | no | 42 | 26 | 0 |
| 20260810_110457_judge-capitals_bot-chatty_n26_s42.jsonl | bot-chatty | (same) | python | no | 42 | 26 | 0 |
| 20260810_110457_judge-capitals_bot-hedged_n26_s42.jsonl | bot-hedged | (same) | python | no | 42 | 26 | 0 |
| 20260810_110457_judge-capitals_bot-wrapped_n26_s42.jsonl | bot-wrapped | (same) | python | no | 42 | 26 | 0 |

## Provenance

- tool: dinostomp 0.62.0
- statistical power: at n=26 items, an UNPAIRED comparison (worst case p=0.5) resolves gaps down to ~39% accuracy (80% power, two-sided alpha 0.05); the paired bootstrap behind P6/C1 resolves smaller gaps when model errors overlap
- spec_sha256: `414280db41465402b15aef657631b3c41dea335c4b29ee7de348d500cdc5c58d`
- data_sha256: `ceb8609c45e8daed58a6ca30757e45bbce202303e6cb1c8324b741d2e11b24d4`
- target_sha256: `{'bot-bare': '34daa2488fb051cf1728a4bba53c6b0c6a51667466c2fb85a2c8cd9483058b9d', 'bot-wrapped': '34daa2488fb051cf1728a4bba53c6b0c6a51667466c2fb85a2c8cd9483058b9d', 'bot-hedged': '34daa2488fb051cf1728a4bba53c6b0c6a51667466c2fb85a2c8cd9483058b9d', 'bot-chatty': '34daa2488fb051cf1728a4bba53c6b0c6a51667466c2fb85a2c8cd9483058b9d'}`
- thresholds: all defaults
- reproducibility tiers, stated honestly: local inputs hash-pinned (spec, data, scorer); requests reproducible given each manifest's environment envelope; hosted-model immutability UNKNOWN unless the provider exposes a pinned revision (the runs table records what each provider claims answered)
- raw report: [STOMP.json](STOMP.json) (both files omit volatile fields, so an unchanged pod re-reports to identical bytes; run manifests carry the timestamps)
