# 🦖 stomp report: eval.yaml

**BROKEN**: 2 gated finding(s) (10 of 37 ran; 24 n/a of 61 declared)

## Entitled claims

**None.** The verdict is `broken`; this eval is not currently entitled to publish claims.

## Checks

### Invariants (deterministic, gating)

Facts, not heuristics: a failure here means something is mechanically wrong (a duplicate exists, a hash changed, a number does not re-derive) and it breaks the verdict.

| | check | witnesses | detail |
|---|---|---:|---|
| **FAIL** | questions are unique | 3000 | 64 duplicated question(s) among 3000 |
| n/a | no answer leaks into its own question | 0 | no free-form items in this dataset |
| **FAIL** | no option offered twice in one item | 3000 | 1 item(s) offer a duplicate option (1 differing only in case or spacing, where exactly one pair collapses; a wider collapse is treated as case carrying the content) |
| ok | every target is among its choices | 3000 | 0 item(s) whose target is not among their choices |
| ok | no identical question with contradictory targets | 3000 | 0 question(s) appear with conflicting targets |
| n/a | every referenced asset resolves and still hashes the same | 0 | no item carries an `input_ref`; nothing points at a file |
| n/a | no asset's own path gives away its label | 0 | no item carries an `input_ref`; nothing points at a file |
| n/a | no asset appears in two splits | 0 | no item carries an `input_ref`; nothing points at a file |
| n/a | every typed claim's evidence requirements hold | 0 | no typed claims declared |
| skip | runs match the spec, data, and scorer on disk (no drift) | 0 | no evidence on disk. This check reads run records; produce them with `dinostomp run <spec>`, or import another harness's logs with `dinostomp import` |
| ok | the witness gate replays clean | 7 | replayed 7 witness(es): 7 behaved; 0 run manifest(s) checked |
| skip | ledger spend agrees with the manifest and the spec cap | 0 | no evidence on disk. This check reads run records; produce them with `dinostomp run <spec>`, or import another harness's logs with `dinostomp import` |
| skip | every run record is schema-valid, unique, and its manifest's own | 0 | no evidence on disk. This check reads run records; produce them with `dinostomp run <spec>`, or import another harness's logs with `dinostomp import` |
| skip | truncated outputs are never credited | 0 | no evidence on disk. This check reads run records; produce them with `dinostomp run <spec>`, or import another harness's logs with `dinostomp import` |
| skip | recorded verdicts re-score identically | 0 | no evidence on disk. This check reads run records; produce them with `dinostomp run <spec>`, or import another harness's logs with `dinostomp import` |
| skip | summaries match their run records | 0 | no evidence on disk. This check reads run records; produce them with `dinostomp run <spec>`, or import another harness's logs with `dinostomp import` |
| skip | records cover exactly the seeded selection | 0 | no evidence on disk. This check reads run records; produce them with `dinostomp run <spec>`, or import another harness's logs with `dinostomp import` |
| skip | every model produced something scoreable | 0 | no evidence on disk. This check reads run records; produce them with `dinostomp run <spec>`, or import another harness's logs with `dinostomp import` |
| n/a | no forbidden tool is called | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| n/a | every required tool is actually called | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| n/a | trajectories are well-formed | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| skip | every model was asked the same items | 0 | no runs on disk yet |

### Diagnostics (statistical, advisory)

Threshold-based signals: they warn, expose their underlying values, and can have legitimate explanations. A warning is evidence of possible trouble, never a proof of invalidity.

| | check | witnesses | detail |
|---|---|---:|---|
| ok | gold answer does not favour an option position | 3000 | gold overshoots position 6 by +1% over its per-item expectation (329 of 3000) |
| ok | gold answer is not systematically the longest option | 3000 | gold is strictly longest +10% over its per-item expectation (622 of 3000) |
| ok | a contamination canary travels with the data | 1 | canary present (dinostomp canary DO NOT TRAIN benchmarks) |
| ok | no surface feature predicts the gold answer | 3000 | 0 surface feature(s) beat the per-item chance null on 3000 keyed item(s) |
| n/a | no model reproduces the contamination canary | 0 | regurgitation probes need a hosted model; this pod's runs are all local |
| n/a | no item already appears in a reference dataset | 0 | no reference dataset supplied; pass --against <file> to compare these items against a corpus you have. This never checks training data, and cannot. |
| n/a | no near-duplicate assets | 0 | no item carries an `input_ref`; nothing points at a file |
| ok | witnesses kill the mutant scorers | 5 | 0 of 5 applicable mutant scorer(s) survive the witness suite |
| skip | uncheckable rate is sane | 0 | no evidence on disk. This check reads run records; produce them with `dinostomp run <spec>`, or import another harness's logs with `dinostomp import` |
| skip | accuracy is distinguishable from guessing | 0 | no evidence on disk. This check reads run records; produce them with `dinostomp run <spec>`, or import another harness's logs with `dinostomp import` |
| skip | runs cover the spec's declared scope, nothing foreign | 0 | no evidence on disk. This check reads run records; produce them with `dinostomp run <spec>`, or import another harness's logs with `dinostomp import` |
| skip | no model selectively escapes the scorer | 0 | no evidence on disk. This check reads run records; produce them with `dinostomp run <spec>`, or import another harness's logs with `dinostomp import` |
| skip | the eval is not solvable blind | 0 | no runs on disk yet |
| skip | no model collapses onto one answer | 0 | no evidence on disk. This check reads run records; produce them with `dinostomp run <spec>`, or import another harness's logs with `dinostomp import` |
| skip | each model beats its own blind baseline | 0 | no runs on disk yet |
| skip | failed answers do not contain the reference | 0 | no evidence on disk. This check reads run records; produce them with `dinostomp run <spec>`, or import another harness's logs with `dinostomp import` |
| skip | billed output tokens match the recorded text | 0 | no evidence on disk. This check reads run records; produce them with `dinostomp run <spec>`, or import another harness's logs with `dinostomp import` |
| skip | the runs were produced by this engine | 0 | no evidence on disk. This check reads run records; produce them with `dinostomp run <spec>`, or import another harness's logs with `dinostomp import` |
| skip | repeated items reached a verdict | 0 | no evidence on disk. This check reads run records; produce them with `dinostomp run <spec>`, or import another harness's logs with `dinostomp import` |
| n/a | passing answers are grounded in tool evidence | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| n/a | no model under-reports its trajectory | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| n/a | tool calls are not redundant | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| n/a | passing answers CHANGE when their evidence is withheld | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| n/a | the trajectory was observed, not self-reported | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| n/a | the judge agrees with cases whose answer is known | 0 | this eval does not score with a judge |
| n/a | the judge is invariant to content-free perturbations | 0 | this eval does not score with a judge |
| n/a | the judge agrees with itself on identical input | 0 | this eval does not score with a judge |
| n/a | the judge does not favour its own family | 0 | this eval does not score with a judge |
| skip | fleet score totals are reliable (KR-20) | 0 | no runs on disk yet |
| skip | no item anti-correlates with fleet skill | 0 | no runs on disk yet |
| skip | dead-weight items stay a minority | 0 | no runs on disk yet |
| skip | no unanimous identical wrong answers | 0 | no runs on disk yet |
| skip | entitled ordering claims are separated beyond sampling noise | 0 | no runs on disk yet |
| skip | the fleet is not pinned at a ceiling or floor | 0 | no runs on disk yet |
| skip | the eval separates the fleet (dynamic range) | 0 | no runs on disk yet |
| n/a | answers survive re-ordering the options | 0 | presentation-order probes need a real provider; this pod's runs are all local |
| n/a | the number survives changing the seed | 0 | the spec declares no extra seeds; a single seed cannot show its own spread (run.seeds is how you ask) |
| n/a | the number survives re-phrasing the instruction | 0 | instruction-framing probes need runs on disk |
| n/a | the fleet ORDERING survives re-phrasing the instruction | 0 | instruction-framing probes need runs on disk |

### Receipts

<details><summary>[FAIL] questions are unique</summary>

- a defendant met her friend at the electronics store where the friend worked. unb
- a man and a woman who were friends decided to buy a car together. the man put $5
- a landlord is the owner in fee simple of a tract of land on which is situated a 
- an owner entered into a written contract with a landscaper whereby the landscape
- is the icj hostile to the idea that an armed attack may arise through a series o
- in 2006, an investor purchased a 100-acre tract located in a rural county. short
- a woman owned land in fee simple absolute. the woman conveyed the land to a frie
- a suspected drug dealer was arrested after selling three grams of cocaine to und

</details>
<details><summary>[ok] gold answer does not favour an option position</summary>

- evidence: `{"chance_rate_at_this_n": 0.0, "excess": 0.0124, "position": 6}`

</details>
<details><summary>[ok] gold answer is not systematically the longest option</summary>

- evidence: `{"excess": 0.0976}`

</details>
<details><summary>[FAIL] no option offered twice in one item</summary>

- mp-00422

</details>
<details><summary>[ok] witnesses kill the mutant scorers</summary>

- evidence: `{"killed": ["always-pass", "always-fail", "case-blind", "space-blind", "prefix-lenient"], "not_applicable": ["substring-lenient", "negation-blind", "uncheckable-credit"]}`

</details>

## Provenance

- tool: dinostomp 0.61.0
- statistical power: at n=3000 items, an UNPAIRED comparison (worst case p=0.5) resolves gaps down to ~4% accuracy (80% power, two-sided alpha 0.05); the paired bootstrap behind P6/C1 resolves smaller gaps when model errors overlap
- spec_sha256: `7836ac654e63f30ddabcf96cd584ccc17532cdcee3e5e347845ab80223de2c7b`
- data_sha256: `311328da4274fdbe0c86ee439940566f1d9b944292a1d108143d356eff516acb`
- thresholds: all defaults
- reproducibility tiers, stated honestly: local inputs hash-pinned (spec, data, scorer); requests reproducible given each manifest's environment envelope; hosted-model immutability UNKNOWN unless the provider exposes a pinned revision (the runs table records what each provider claims answered)
- raw report: [STOMP.json](STOMP.json) (both files omit volatile fields, so an unchanged pod re-reports to identical bytes; run manifests carry the timestamps)
