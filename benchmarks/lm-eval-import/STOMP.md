# 🦖 stomp report: eval.yaml

**INCOMPLETE**: no failures, but only 18 of 38 checks ran (18 of 38 ran; 19 n/a of 57 declared). Not a clean bill of health.

## Entitled claims

**None.** The verdict is `incomplete`; this eval is not currently entitled to publish claims.

## Checks

### Invariants (deterministic, gating)

Facts, not heuristics: a failure here means something is mechanically wrong (a duplicate exists, a hash changed, a number does not re-derive) and it breaks the verdict.

| | check | witnesses | detail |
|---|---|---:|---|
| ok | questions are unique | 1172 | 0 duplicated question(s) among 1172 |
| n/a | no answer leaks into its own question | 0 | no free-form items in this dataset |
| ok | no option offered twice in one item | 1172 | 0 item(s) offer a duplicate option |
| ok | every target is among its choices | 1172 | 0 item(s) whose target is not among their choices |
| ok | no identical question with contradictory targets | 1172 | 0 question(s) appear with conflicting targets |
| n/a | every typed claim's evidence requirements hold | 0 | no typed claims declared |
| ok | runs match the spec, data, and scorer on disk (no drift) | 1 | 0 of 1 run(s) no longer match the spec, data, or scorer on disk |
| ok | the witness gate replays clean | 7 | replayed 6 witness(es): 6 behaved; 1 run manifest(s) checked |
| skip | ledger spend agrees with the manifest and the spec cap | 0 | no `usage` on every record (per-record cost is summed and compared to the manifest total); 0 of 1172 record(s) carry it; no `spend_usd` on every manifest (the ledger total the sum is checked against); 0 of 1 manifest(s) carry it |
| ok | every run record is schema-valid, unique, and its manifest's own | 1172 | 0 integrity problem(s) across 1172 record(s) |
| skip | truncated outputs are never credited | 0 | no `finish_reason` on every record (a truncated response is identified by it); 0 of 1172 record(s) carry it |
| skip | recorded verdicts re-score identically | 0 | no `output` on every record (verdicts are re-scored from the recorded text); 0 of 1172 record(s) carry it |
| ok | summaries match their run records | 1 | 0 summary discrepanc(ies) across 1 run(s) |
| ok | records cover exactly the seeded selection | 1 | 0 of 1 run(s) do not cover their seeded selection |
| ok | every model produced something scoreable | 1 | 0 of 1 model(s) produced nothing scoreable |
| n/a | no forbidden tool is called | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| n/a | every required tool is actually called | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| n/a | trajectories are well-formed | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| skip | every model was asked the same items | 0 | only 1 model(s) on disk; run a fleet of 4+ to unlock psychometrics |

### Diagnostics (statistical, advisory)

Threshold-based signals: they warn, expose their underlying values, and can have legitimate explanations. A warning is evidence of possible trouble, never a proof of invalidity.

| | check | witnesses | detail |
|---|---|---:|---|
| ok | gold answer does not favour an option position | 1172 | gold overshoots position 1 by +2% over its per-item expectation (311 of 1172) |
| ok | gold answer is not systematically the longest option | 1172 | gold is strictly longest -3% over its per-item expectation (259 of 1172) |
| ok | a contamination canary travels with the data | 1 | canary present (dinostomp canary DO NOT TRAIN lm-eval-im...) |
| ok | no surface feature predicts the gold answer | 1172 | 0 surface feature(s) beat the per-item chance null on 1172 keyed item(s) |
| skip | no model reproduces the contamination canary | 0 | no canary probe on disk; run `dinostomp run <spec> --probe canary` to ask whether a model has already read this dataset |
| n/a | no item already appears in a reference dataset | 0 | no reference dataset supplied; pass --against <file> to compare these items against a corpus you have. This never checks training data, and cannot. |
| warn | witnesses kill the mutant scorers | 5 | 1 of 5 applicable mutant scorer(s) survive the witness suite |
| ok | uncheckable rate is sane | 1172 | 0% of 1172 record(s) are uncheckable |
| warn | accuracy is distinguishable from guessing | 1 | 1 of 1 model(s) score no better than guessing; fleet spans 20% to 20% vs chance ~25% (uniform choice floor) |
| ok | runs cover the spec's declared scope, nothing foreign | 1 | 0 run(s) outside the spec's declared scope |
| skip | no model selectively escapes the scorer | 0 | needs at least 2 models to compare uncheckable rates |
| skip | the eval is not solvable blind | 0 | no blind probe on disk; run `dinostomp run <spec> --probe blind` to unlock |
| skip | no model collapses onto one answer | 0 | no `output` on every record (a collapsed model is identified by repeated output text); 0 of 1172 record(s) carry it |
| skip | each model beats its own blind baseline | 0 | no blind probe on disk; run `dinostomp run <spec> --probe blind` to unlock |
| skip | failed answers do not contain the reference | 0 | no `output` on every record (an unparsed-but-correct answer is looked for in the text); 0 of 1172 record(s) carry it |
| n/a | billed output tokens match the recorded text | 0 | no model produced 20+ answers of at least 40 characters; short-answer evals cannot be billed against reliably |
| n/a | the runs were produced by this engine | 0 | no run manifest records a tool_sha256 |
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
| skip | fleet score totals are reliable (KR-20) | 0 | only 1 model(s) on disk; run a fleet of 4+ to unlock psychometrics |
| skip | no item anti-correlates with fleet skill | 0 | only 1 model(s) on disk; run a fleet of 4+ to unlock psychometrics |
| skip | dead-weight items stay a minority | 0 | only 1 model(s) on disk; run a fleet of 4+ to unlock psychometrics |
| skip | no unanimous identical wrong answers | 0 | only 1 model(s) on disk; run a fleet of 4+ to unlock psychometrics |
| skip | entitled ordering claims are separated beyond sampling noise | 0 | an ordering claim needs at least 2 models on disk |
| skip | the fleet is not pinned at a ceiling or floor | 0 | only 1 model(s) on disk; run a fleet of 4+ to unlock psychometrics |
| skip | the eval separates the fleet (dynamic range) | 0 | only 1 model(s) on disk; run a fleet of 4+ to unlock psychometrics |
| skip | answers survive re-ordering the options | 0 | no shuffle probe on disk; set data.render_choices and run `dinostomp run <spec> --probe shuffle` to unlock |
| n/a | the number survives changing the seed | 0 | the spec declares no extra seeds; a single seed cannot show its own spread (run.seeds is how you ask) |
| skip | the number survives re-phrasing the instruction | 0 | no template probe on disk; run `dinostomp run <spec> --probe template` to unlock |
| skip | the fleet ORDERING survives re-phrasing the instruction | 0 | no template probe on disk; run `dinostomp run <spec> --probe template` to unlock |

### Receipts

<details><summary>[ok] gold answer does not favour an option position</summary>

- evidence: `{"excess": 0.0152, "position": 1}`

</details>
<details><summary>[ok] gold answer is not systematically the longest option</summary>

- evidence: `{"excess": -0.0292}`

</details>
<details><summary>[warn] witnesses kill the mutant scorers</summary>

- space-blind (ignores whitespace differences) survives; add a witness whose output differs from the target only by a RUN of internal whitespace (e.g. a doubled space), with the expected verdict pinned
- evidence: `{"killed": ["always-pass", "always-fail", "case-blind", "prefix-lenient"], "not_applicable": ["substring-lenient", "negation-blind", "uncheckable-credit"]}`

</details>
<details><summary>[skip] ledger spend agrees with the manifest and the spec cap</summary>

- evidence: `{"missing_evidence": ["usage", "spend_usd"]}`

</details>
<details><summary>[skip] truncated outputs are never credited</summary>

- evidence: `{"missing_evidence": ["finish_reason"]}`

</details>
<details><summary>[ok] uncheckable rate is sane</summary>

- evidence: `{"rate": 0.0}`

</details>
<details><summary>[warn] accuracy is distinguishable from guessing</summary>

- Corianas/111m: 20% on 1172 checkable, at or below the 25% floor
- evidence: `{"chance_floor": 0.2502, "modal": 0.0026, "modal_target": "earth rotates on its axis.", "per_model_accuracy": {"Corianas/111m": 0.1971}, "uniform": 0.2502}`

</details>
<details><summary>[skip] recorded verdicts re-score identically</summary>

- evidence: `{"missing_evidence": ["output"]}`

</details>
<details><summary>[skip] no model collapses onto one answer</summary>

- evidence: `{"missing_evidence": ["output"]}`

</details>
<details><summary>[skip] failed answers do not contain the reference</summary>

- evidence: `{"missing_evidence": ["output"]}`

</details>

## Runs

| run file | model | reported as | provider | dry | seed | records | uncheckable |
|---|---|---|---|---|---:|---:|---:|
| imported_imported-lm-eval_Corianas-111m_n1172_s0.jsonl | Corianas/111m | ? | imported | no | 0 | 1172 | 0 |

## Provenance

- tool: dinostomp 0.48.0
- statistical power: at n=1172 items, an UNPAIRED comparison (worst case p=0.5) resolves gaps down to ~6% accuracy (80% power, two-sided alpha 0.05); the paired bootstrap behind P6/C1 resolves smaller gaps when model errors overlap
- spec_sha256: `967c38cc964d1369f96ddf6ab68a1c52eaac0c25d27a13b6e9bb1995c3491cb1`
- data_sha256: `63af045e1154054f7927b7969aa0fb23c7b80cc11ce1921605744124e6005267`
- thresholds: all defaults
- reproducibility tiers, stated honestly: local inputs hash-pinned (spec, data, scorer); requests reproducible given each manifest's environment envelope; hosted-model immutability UNKNOWN unless the provider exposes a pinned revision (the runs table records what each provider claims answered)
- raw report: [STOMP.json](STOMP.json) (both files omit volatile fields, so an unchanged pod re-reports to identical bytes; run manifests carry the timestamps)
