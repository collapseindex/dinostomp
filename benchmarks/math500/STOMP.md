# 🦖 stomp report: eval.yaml

**BROKEN**: 1 gated finding(s) (6 of 33 ran; 28 n/a of 61 declared)

## Entitled claims

**None.** The verdict is `broken`; this eval is not currently entitled to publish claims.

## Checks

### Invariants (deterministic, gating)

Facts, not heuristics: a failure here means something is mechanically wrong (a duplicate exists, a hash changed, a number does not re-derive) and it breaks the verdict.

| | check | witnesses | detail |
|---|---|---:|---|
| ok | questions are unique | 500 | 0 duplicated question(s) among 500 |
| **FAIL** | no answer leaks into its own question | 500 | 2 of 500 free-form item(s) leak their answer |
| n/a | no option offered twice in one item | 0 | no multiple-choice items in this dataset |
| n/a | every target is among its choices | 0 | no multiple-choice items in this dataset |
| ok | no identical question with contradictory targets | 500 | 0 question(s) appear with conflicting targets |
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
| n/a | gold answer does not favour an option position | 0 | no multiple-choice items in this dataset |
| n/a | gold answer is not systematically the longest option | 0 | no multiple-choice items in this dataset |
| ok | a contamination canary travels with the data | 1 | canary present (dinostomp canary DO NOT TRAIN benchmarks) |
| n/a | no surface feature predicts the gold answer | 0 | no multiple-choice items in this dataset |
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

<details><summary>[FAIL] no answer leaks into its own question</summary>

- m500-00277: target '\\sqrt{53}' appears in its question (only 0 other answer-space value(s) present)
- m500-00373: target '1+2i' appears in its question (only 2 other answer-space value(s) present)

</details>
<details><summary>[ok] witnesses kill the mutant scorers</summary>

- evidence: `{"killed": ["always-pass", "always-fail", "case-blind", "space-blind", "prefix-lenient"], "not_applicable": ["substring-lenient", "negation-blind", "uncheckable-credit"]}`

</details>

## Provenance

- tool: dinostomp 0.61.0
- statistical power: at n=500 items, an UNPAIRED comparison (worst case p=0.5) resolves gaps down to ~9% accuracy (80% power, two-sided alpha 0.05); the paired bootstrap behind P6/C1 resolves smaller gaps when model errors overlap
- spec_sha256: `a69638f9223f91df9742a4239c7552c56accb294d94f8319416aa418fbb1c147`
- data_sha256: `f7ddec3bc3caf21ce5cee32ca130f8c6f570d5420c6f35068bd7e3b062124358`
- thresholds: all defaults
- reproducibility tiers, stated honestly: local inputs hash-pinned (spec, data, scorer); requests reproducible given each manifest's environment envelope; hosted-model immutability UNKNOWN unless the provider exposes a pinned revision (the runs table records what each provider claims answered)
- raw report: [STOMP.json](STOMP.json) (both files omit volatile fields, so an unchanged pod re-reports to identical bytes; run manifests carry the timestamps)
