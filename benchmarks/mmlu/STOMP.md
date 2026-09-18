# 🦖 stomp report: eval.yaml

**BROKEN**: 3 gated finding(s) (16 of 49 ran; 51 n/a of 100 declared)

measures the intended construct: **NOT ESTABLISHED BY DINOSTOMP**

## Entitled claims

**None.** The verdict is `broken`; this eval is not currently entitled to publish claims.

## Checks

### Invariants (deterministic, gating)

Facts, not heuristics: a failure here means something is mechanically wrong (a duplicate exists, a hash changed, a number does not re-derive) and it breaks the verdict.

| | check | witnesses | detail |
|---|---|---:|---|
| **FAIL** | questions are unique | 3000 | 90 duplicated question(s) among 3000 |
| **FAIL** | no answer leaks into its own question | 3000 | 22 of 3000 item(s) leak their answer into the question |
| **FAIL** | no option offered twice in one item | 3000 | 4 item(s) offer a duplicate option (1 differing only in case or spacing, where exactly one pair collapses; a wider collapse is treated as case carrying the content) |
| ok | every target is among its choices | 3000 | 0 item(s) whose target is not among their choices |
| ok | no identical question with contradictory targets | 3000 | 0 question(s) appear with conflicting targets |
| n/a | every referenced asset resolves and still hashes the same | 0 | no item carries an `input_ref`; nothing points at a file |
| n/a | no asset's own path gives away its label | 0 | no item carries an `input_ref`; nothing points at a file |
| n/a | no asset appears in two splits | 0 | no item carries an `input_ref`; nothing points at a file |
| ok | the audit covers the rows it was given | 3000 | 0 of 3000 row(s) were dropped: the pod loader refuses a dataset it cannot read whole, so every row in the file reached the audit |
| n/a | rows are unique | 0 | out of scope for a pod audit (the dataset, the scorer, and every run on disk) |
| n/a | no error value is saved in the workbook | 0 | out of scope for a pod audit (the dataset, the scorer, and every run on disk) |
| n/a | every column aggregate covers its own column | 0 | out of scope for a pod audit (the dataset, the scorer, and every run on disk) |
| n/a | the join returns rows at all | 0 | out of scope for a pod audit (the dataset, the scorer, and every run on disk) |
| n/a | no key fails to match on case or whitespace alone | 0 | out of scope for a pod audit (the dataset, the scorer, and every run on disk) |
| n/a | every parent total equals the sum of its children | 0 | out of scope for a pod audit (the dataset, the scorer, and every run on disk) |
| n/a | a graded scorer witnesses its gradation | 0 | this scorer does not emit intermediate partial credit, so there is no gradation to witness |
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
| skip | graded scores stay in range | 0 | no evidence on disk. This check reads run records; produce them with `dinostomp run <spec>`, or import another harness's logs with `dinostomp import` |
| n/a | no forbidden tool is called | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| n/a | every required tool is actually called | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| n/a | trajectories are well-formed | 0 | this spec runs no code targets and no imported run carries a trajectory; nothing here produces or carries one |
| skip | every model was asked the same items | 0 | no runs on disk yet |

### Diagnostics (statistical, advisory)

Threshold-based signals: they warn, expose their underlying values, and can have legitimate explanations. A warning is evidence of possible trouble, never a proof of invalidity.

| | check | witnesses | detail |
|---|---|---:|---|
| ok | gold answer does not favour an option position | 3000 | gold overshoots position 3 by +3% over its per-item expectation (837 of 3000) |
| ok | gold answer is not systematically the longest option | 3000 | gold is strictly longest -6% over its per-item expectation (574 of 3000) |
| ok | a contamination canary travels with the data | 1 | canary present (dinostomp canary DO NOT TRAIN benchmarks) |
| ok | no surface feature predicts the gold answer | 3000 | 0 surface feature(s) beat the per-item chance null on 3000 keyed item(s) |
| n/a | no model reproduces the contamination canary | 0 | regurgitation probes need a hosted model; this pod's runs are all local |
| n/a | no item already appears in a reference dataset | 0 | no reference dataset supplied; pass --against <file> to compare these items against a corpus you have. This never checks training data, and cannot. |
| n/a | no near-duplicate assets | 0 | no item carries an `input_ref`; nothing points at a file |
| n/a | the eval is not authored in a circle | 0 | no provenance declared, so authorship is not described. Declaring who wrote the items, keys, scorer, and witnesses lets this surface a model sitting on both sides of a loop (e.g. keying its own questions) |
| n/a | no single column all but determines the target | 0 | an eval pod's items are questions and answers, not a feature table; the single-column leak scan is for a raw tabular dataset audit |
| ok | no two options are the same number written differently | 377 | 0 of 377 item(s) with numeric options offer the same number twice in different writing |
| warn | no two items are the same question in different encodings | 3000 | 5 group(s) of items are the same question in different encodings |
| ok | the answer key is not dominated by one value | 3000 | the answer key is not dominated by one value (modal 1% of 2512 answers) |
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
| ok | witnesses kill the mutant scorers | 5 | 0 of 5 applicable mutant scorer(s) survive the witness suite |
| ok | a correct answer survives its surface form | 6 | 0 surface form(s) lose a correct answer and 0 credit a decoy, of 6 applicable |
| n/a | an exact scorer is not graded against prose answers | 0 | the scorer does not compare bare strings, so it is not the exact-match-on-prose mismatch this looks for |
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
| skip | no failed answer numerically equals its target | 0 | no evidence on disk. This check reads run records; produce them with `dinostomp run <spec>`, or import another harness's logs with `dinostomp import` |
| skip | reported confidence matches observed accuracy | 0 | no evidence on disk. This check reads run records; produce them with `dinostomp run <spec>`, or import another harness's logs with `dinostomp import` |
| skip | confidence separates right answers from wrong ones | 0 | no evidence on disk. This check reads run records; produce them with `dinostomp run <spec>`, or import another harness's logs with `dinostomp import` |
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
| skip | the fleet varies on one axis, not a blend of abilities | 0 | no runs on disk yet |
| skip | declared subskills actually separate in the responses | 0 | no runs on disk yet |

Re-derive this report from the directory holding the target: `dinostomp stomp eval.yaml`

### Receipts

<details><summary>[FAIL] questions are unique</summary>

- the key attribute in successful marathon running is: || power. | stamina. | stre
- with an increasing number of sprints the: || anaerobic contribution progressivel
- sodium bicarbonate ingestion improves middle distance running performance by: ||
- codons are composed of: || quadruplet sequences of nucleotide bases in mrna or d
- fatty acids are transported into the mitochondria bound to: || acetyl-coa. | car
- which of the following statements is false? || ammonia is produced in repeated h
- glycogen breakdown in muscle initially results in the formation of: || glucose-1
- which of the following processes is not used to modify protein structure after t
- refs (item): `mmlu-00488`, `mmlu-01258`, `mmlu-00492`, `mmlu-01359`, `mmlu-00494`, `mmlu-01309`, `mmlu-00495`, `mmlu-01315` (+24 more in STOMP.json)

</details>
<details><summary>[FAIL] no answer leaks into its own question</summary>

- mmlu-00098: correct option '12' appears in the stem and no distractor does
- mmlu-00854: correct option 'hydrogen bonding between the peptide backbone atoms' appears in the stem and no distractor does
- mmlu-01143: correct option 'pi' appears in the stem and no distractor does
- mmlu-01511: correct option 'condentiality' appears in the stem and no distractor does
- mmlu-01583: correct option '2 a' appears in the stem and no distractor does
- mmlu-01672: correct option '3 a' appears in the stem and no distractor does
- mmlu-01742: correct option '26' appears in the stem and no distractor does
- mmlu-01769: correct option '3000 n' appears in the stem and no distractor does
- refs (item): `mmlu-00098`, `mmlu-00854`, `mmlu-01143`, `mmlu-01511`, `mmlu-01583`, `mmlu-01672`, `mmlu-01742`, `mmlu-01769` (+14 more in STOMP.json)

</details>
<details><summary>[ok] gold answer does not favour an option position</summary>

- evidence: `{"chance_rate_at_this_n": 0.0, "excess": 0.029, "position": 3}`

</details>
<details><summary>[ok] gold answer is not systematically the longest option</summary>

- evidence: `{"excess": -0.0587}`

</details>
<details><summary>[FAIL] no option offered twice in one item</summary>

- mmlu-00389
- mmlu-01941
- mmlu-02178
- mmlu-02501
- refs (item): `mmlu-00389`, `mmlu-01941`, `mmlu-02178`, `mmlu-02501`

</details>
<details><summary>[warn] no two items are the same question in different encodings</summary>

- mmlu-00008, mmlu-00035, mmlu-00071: same question after folding lookalike characters and their ANSWERS CONFLICT, a contradiction S7 cannot see because the questions are not byte-identical ('Find the degree for the given field extension Q(sqrt(2) + sq')
- mmlu-00901, mmlu-00988: same question after folding lookalike characters and their ANSWERS CONFLICT, a contradiction S7 cannot see because the questions are not byte-identical ('Nitronyl nitroxides are stable radicals in which the unpaire')
- mmlu-01376, mmlu-01388: same question after folding lookalike characters ('Protons used in cancer therapy are typically accelerated to ')
- mmlu-01582, mmlu-01679: same question after folding lookalike characters and their ANSWERS CONFLICT, a contradiction S7 cannot see because the questions are not byte-identical ('The surface of planet Earth loses energy to outer space due ')
- mmlu-01590, mmlu-01698: same question after folding lookalike characters and their ANSWERS CONFLICT, a contradiction S7 cannot see because the questions are not byte-identical ('Polarization is a property of')

</details>
<details><summary>[ok] the answer key is not dominated by one value</summary>

- evidence: `{"modal_share": 0.007, "modal_value": "true, false", "n_distinct": 2512}`

</details>
<details><summary>[ok] the audit covers the rows it was given</summary>

- evidence: `{"dropped_share": 0.0, "gate": 0.01, "rows_audited": 3000, "rows_dropped": 0, "rows_read": 3000}`

</details>
<details><summary>[ok] witnesses kill the mutant scorers</summary>

- evidence: `{"killed": ["always-pass", "always-fail", "case-blind", "space-blind", "prefix-lenient"], "not_applicable": ["substring-lenient", "negation-blind", "uncheckable-credit"]}`

</details>
<details><summary>[ok] a correct answer survives its surface form</summary>

- evidence: `{"baseline_form": "labelled", "held": ["trailing-punctuation", "surrounding-whitespace", "markdown-emphasis", "label-case", "keyword-in-prose", "reasoning-prefix"], "not_applicable": ["answer-case", "decoy-in-working"]}`

</details>

## Provenance

- tool: dinostomp 0.63.0
- statistical power: at n=3000 items, an UNPAIRED comparison (worst case p=0.5) resolves gaps down to ~4% accuracy (80% power, two-sided alpha 0.05); the paired bootstrap behind P6/C1 resolves smaller gaps when model errors overlap
- spec_sha256: `3e43402a87458a3fe5d448faf280c02e55453510ae8dd6406393aa4621c78968`
- data_sha256: `b5f09b255f036e6edbd789fac88832ff54f552fb2e238148e3bdcf1bab23c36c`
- thresholds: all defaults
- reproducibility tiers, stated honestly: local inputs hash-pinned (spec, data, scorer); requests reproducible given each manifest's environment envelope; hosted-model immutability UNKNOWN unless the provider exposes a pinned revision (the runs table records what each provider claims answered)
- raw report: [STOMP.json](STOMP.json) (both files omit volatile fields, so an unchanged pod re-reports to identical bytes; run manifests carry the timestamps)
