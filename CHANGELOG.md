# Changelog

### Unreleased

- **Seven new checks read the JOIN between two tables: the `JN` series, and a
  `dinostomp join` command.** A join is the one operation that fails silently
  AND in the flattering direction: an inner join that drops rows raises
  nothing and leaves a tidier dataset behind. `join-viable` gates when the
  join returns nothing at all, `key-normalisation` gates on keys that fail to
  match on case or whitespace alone, and `totals-reconcile` gates when a
  parent total disagrees with the sum of its own children. `orphan-rows`,
  `parent-key-unique`, `join-fanout` and `key-type-drift` warn. The join key
  is inferred, printed, and REFUSED when the best candidate is merely an
  overlap: a join performed on the wrong column does not error, it answers.
- **It found the case study's defect by itself.** Pointed at the public ACNH
  villager and music tables with no hints, it inferred the key and reported
  that `To The Edge` would match `To the Edge`: three villagers dropped from
  every per-song analysis by one capital letter, which this repository had
  previously found by hand.
- **DinoTrials grew a join arm**: 7 planted defects between two tables, 1
  clean join, scored separately from the pod and table arms.
- Two more defects in the tool, both in key inference and both published:
  ranking a colour column above the real key by scoring coverage without
  identification ([D-087](FINDINGS.md#d-087)), and falling back to a 33%
  coincidence when the real key matched nothing, reporting faithfully about a
  relationship nobody meant ([D-088](FINDINGS.md#d-088)).
- **Twenty-eight new checks read a spreadsheet as a spreadsheet: the `G` and
  `XL` series.** `dinostomp stomp orders.xlsx` now audits a table that was never
  an eval, at a new **table scope**, instead of refusing the file because no
  column looked like a question. `G1`-`G11` read the values (whitespace and
  invisible characters, duplicate and near-duplicate rows, repeated identifiers,
  leading zeros, mixed and locale-ambiguous dates, text in numeric columns,
  sentinels, categories split by capitalisation, mixed percent scales, currency
  formatting). `XL1`-`XL6` read the workbook itself and are the half no
  dataframe reader can reach: constants pasted over formulas, saved `#REF!`,
  hidden rows and columns and sheets, merged ranges, aggregates whose range
  stops above the last populated row of their own column, and formulas never
  calculated. That last one is the Reinhart-Rogoff defect and it gates.
  `.xlsx`/`.xlsm`/`.tsv` are readable now; the workbook checks need
  `pip install 'dinostomp[xlsx]'` and report UNAVAILABLE with the install line
  rather than passing quietly without it, exactly as S15 does for `vision`.
- **The table checks propose, they never repair.** A digit-string column with
  leading zeros is correct as text and broken as a number and the file cannot
  say which, so `G4` reports what a conversion would destroy and stops.
  `--emit-fixes` is unchanged and still only deletes and deduplicates.
- **DinoTrials grew a table arm.** The header of `trials/run_trials.py` recorded
  that wiring a dataset arm into the scorecard was "the right fix and is not
  done"; twenty-eight new checks needed it, so it is done: 16 planted
  spreadsheet defects and 2 clean tables, scored separately from the pod arm.
  The clean controls are deliberately awkward (a line-item table whose order id
  repeats by design, a workbook whose subtotals between them cover every row),
  because a battery that stays quiet only on sterile data has not been tested
  for specificity at all.
- **Five defects in the tool, found while building it** and published with the
  rest: a number reader that rejected every value over 999 and so produced a
  false alarm and a miss from one pattern ([D-080](FINDINGS.md#d-080)); a
  category check whose guard measured raw distinctness, so the defect it looks
  for hid it ([D-081](FINDINGS.md#d-081)); a scope filter that made every
  previously-sound pod report INCOMPLETE the moment a new series landed
  ([D-082](FINDINGS.md#d-082)); a check-id namespace collision with the ids
  extension authors reach for first ([D-083](FINDINGS.md#d-083)); and a
  value-only workbook reporting INCOMPLETE for questions it could not be asked
  ([D-084](FINDINGS.md#d-084)).
- Out-of-scope checks now report `n/a` naming the scope instead of `skip`, so
  coverage no longer moves when an unrelated series ships.

- **New check S21 `rows-audited`: the audit says how much of the file it read.**
  A row with no question or no answer cannot be audited, so it was dropped, and
  the count went to one line of prose on stdout. It never reached `STOMP.json`
  and never touched the verdict, so a Sample Superstore CSV with the People and
  Returns tables concatenated under the Orders header came back MECHANICALLY
  SOUND with exit 0 over 807 rows it had silently discarded
  ([D-079](FINDINGS.md#d-079)). S21 now states the number on every audit, passing
  or failing, and gates above `dropped_rows_max` (1% of the file). Both scopes
  report it: the pod path loads all-or-nothing, so it passes there by
  construction and says why. Battery is 74 checks, 19 of them data-scoped.
  Ledger: 159 entries (F 49, D 79, N 31).

- **`audits/cuda-agent`: the first audit here whose subject is a training corpus
  and an RL reward instrument** rather than an eval and its scorer. CUDA Agent
  (arXiv:2602.24286) against its released CUDA-Agent-Ops-6K and KernelBench, no
  GPU, no API calls, $0.00. Four findings: 352 of 6,000 training samples are
  byte-identical duplicates ([F-047](FINDINGS.md#f-047)); 550 of 5,929 rows
  declare an operator absent from their own code
  ([F-048](FINDINGS.md#f-048)); the anti-reward-hacking guard patches `dir(F)`
  and 11 of 13 routes to a torch operator survive it, including any name
  imported before it runs ([F-049](FINDINGS.md#f-049)); and their
  decontamination claim HOLDS under an independent instrument, published with
  the control that shows what the check cannot see
  ([N-031](FINDINGS.md#n-031)). Ledger: 158 entries (F 49, D 78, N 31).

- **`--against` works on corpora that are not shaped like an MCQ pod.** Three
  defects, all found in one sitting by pointing S11 at an outside reference for
  the first time (CUDA-Agent-Ops-6K against KernelBench). The reference is now
  read with the same `--input-field` / `--target-field` the audited file gets,
  for any column it has, and an override naming a column it does not have is
  dropped rather than raised ([D-076](FINDINGS.md#d-076)). A reference no longer
  needs an answer key, because `comparable()` compares questions and options and
  never reads the target; keyless items keep their choices and are no longer
  dropped by the empty-target guard ([D-077](FINDINGS.md#d-077)). And S11 no
  longer tells a user that no reference was supplied when one was supplied and
  refused: the n/a reason names the refusal, in the written report and not only
  on stdout ([D-078](FINDINGS.md#d-078)). The CLI prints which columns a
  reference was read as. `load_reference` returns `(items, errors, notes)`.

- **P14 `subskill-discriminant`: do the declared subskills actually separate in the
  responses?** The discriminant leg of construct validity, judge-free. When items
  carry a `subskill` label (an MMLU subject, a BBH task) and a per-subskill
  leaderboard implies those subskills measure distinct things, P14 tests whether
  items sharing a subskill cohere more than items from different subskills, against
  a null that shuffles the labels across items. Observed separation above the null
  means the partition is real; at or below it, the subskills are statistically
  redundant and a per-subskill score overclaims distinct competence (Haberman's
  subscore-value question, asked from the response matrix). Never reads what a
  subskill IS. It is the dual of P13: subskills separate only when the fleet is
  multidimensional, so a partition that carves also lights P13. Diagnostic, 6+
  models and 2+ subskills each with 5+ items; n/a when no item declares a subskill.
  Validated to never cry wolf on genuinely distinct subskills (0/10 false-warns at
  6/8/10 examinees). Adds an optional `subskill` field to the item schema
  (backward-compatible). Battery: 73 checks, 102 trials.

- **P13 `construct-dimensionality`: does the fleet vary on one axis, or does its
  single score blend abilities that rank it differently?** The one construct-validity
  threat a response matrix can see, asked judge-free. dinostomp cannot ASSERT
  construct validity (that needs a theory of the construct it refuses to fabricate);
  P13 flags when a leaderboard number is a composite. It item-centres the matrix,
  takes the share of fleet-differentiation variance on the dominant axis, and
  compares it to the SAME fixed-margins swap-randomisation null P2 uses (extracted
  now into one shared sampler). The null preserves each model's skill and each
  item's difficulty, so a unidimensional skill axis survives into it and cancels;
  concentration in excess of the null (by a calibrated 0.10 margin) is a coherent
  item cluster only a subgroup solves. Diagnostic, 6+ models, and quiet-means-little
  on a small fleet, the same honest limit as P2: measured 0/10 false alarms on
  unidimensional fleets and 0/10 misses on 2- and 3-cluster fleets at 6/8/10
  examinees. Dry fleets are one scalar by construction, so a quiet P13 there is a
  plumbing check, not validity evidence, and it says so. Trial: a dry fleet whose
  recorded outputs split into two ability clusters passes every integrity check
  (verdict ok) and only P13 (with a low KR-20 from P1) sees the blend. Battery: 72
  checks, 101 planted-defect trials.

- **[F-046](FINDINGS.md#f-046): LoCoMo repeats eleven questions inside one
  conversation, and one answer is echoed in its question.** The long-term-memory
  benchmark, audited with each item scoped to its conversation id (the SQuAD-correct
  identity: a duplicate is the same question asked twice of the *same* conversation).
  Conversation 7 asks eleven questions twice, each pair agreeing on the answer;
  one temporal item ("...sell the car he restored last year?") is keyed "Last year".
  Both minor and concentrated, both real. The honest half is what S2 did not flag:
  ten choice-format questions offer the answer as an option ("beach or mountains?"
  -> "beach"), which S2 correctly ignores, so only the one genuine echo gates.

- **A `record` scorer kind, for evals with no correct answer.** A preference or
  free-choice elicitation ("which of these two do you prefer?") has no gold, so
  there is nothing to grade for correctness; what there is to grade is whether the
  model answered at all. `record` passes a non-empty response and fails an empty
  one, so its accuracy is the response rate (one minus the refusal rate, a real and
  welfare-relevant signal), and the pick itself is read from the recorded output
  downstream. It is marked non-grading, so W1 (mutation) and W2 (surface-form)
  report n/a rather than flagging it for a content blind spot it has by design,
  while the witness gate still enforces its must-pass and must-fail. Found while
  building a pairwise-preference eval as a dinostomp pod: a no-gold pod is a new
  shape, and this is the first-class support for it. (Placeholder targets on the
  items still satisfy the schema; making `target` optional for record-scored pods,
  and n/a-ing the gold-position checks, is the natural follow-up.)

- **S2's label-set exemption now covers reused vocabularies above three labels
  (found on dair-ai/emotion).** [D-073](FINDINGS.md#d-073) fixed the false gate on
  a global label set of three or fewer values; the very next benchmark, a 6-class
  emotion set, fell outside that cap and S2 gated it BROKEN over "anger" in "i felt
  anger". A class's own word in its own text is inherent to all text
  classification, not a leaked key. The `<=3` cap was the wrong shape: what makes a
  label set is a small vocabulary REUSED across the set (emotion's six labels
  average ~333 items each), versus open QA (thousands of answers, little reuse,
  where a question naming its answer really is a leak). S2 is now n/a when the
  answers are three or fewer values OR a vocabulary reused 10+ items per label on
  average. Verified n/a on BoolQ, SNLI, SST-2, emotion while TriviaQA and a planted
  leak still gate. [D-074](FINDINGS.md#d-074); Cyrillic S19 control and emotion in
  [N-028](FINDINGS.md#n-028).

- **S2 `answer-leak` no longer false-gates on a global label word (found on
  BoolQ).** Run against BoolQ's validation split, S2 marked the benchmark BROKEN
  over four items whose answer is "no" and whose question merely contains the word
  ("a no ball", "No. 1 Court", "no sleep", "no insurance") where nothing leaked.
  A tiny global label set (yes/no, true/false, entailment/neutral/contradiction)
  is shared generic vocabulary, not per-item keys, which is exactly why S3/S4/S9
  already go n/a on one; S2 now does too, when the answers are a global label set
  of 3 or fewer values over 20+ items. Kept surgical: a set with many distinct
  answers still gates a genuine leak. The first defect the real-benchmark hunt
  turned up, in a way no synthetic pod had. [D-073](FINDINGS.md#d-073), and the
  real BoolQ findings from the same run are [F-040](FINDINGS.md#f-040).

- **S20 `key-skew`.** A data-scope warning that the answer key leans hard on one
  value. A benchmark where 65% of the answers are "yes" hands a model that always
  says "yes" a 65% score for knowing nothing, so an accuracy of 60% reads as
  competence when it is below the floor. R7 catches this once models have run;
  S20 reads it off the key alone, before a cent is spent, which is where an author
  can still fix it. The signal is the modal share above what a balanced key would
  give (1 over the number of distinct answers), so a balanced binary set (50/50)
  does not trip while a skewed one (70/30) does, and an all-one-answer key is named
  outright. Diagnostic, not a gate: a real base rate can be skewed (most
  transactions are not fraud), so it states the floor and the author decides.
  Registry 70 -> 71 checks. Found while red-teaming before a wider release.

- **W4 `scorer-fit`.** An exact scorer keyed to sentence-length free-text answers
  marks every paraphrase wrong, so a model that answered correctly in its own
  words scores near zero for a formatting reason and the eval reports a capability
  gap that is not there (the F-006/F-007 shape, but caught at lint time before a
  cent is spent). W2 stays silent on exact scorers by design (rejecting a trailing
  full stop is a choice, not a defect); W4 asks the question W2 does not, whether
  exact is the right tool for THESE answers. It warns when the scorer is exact and
  the free-form answers run 6+ words at the median, where a proper noun or a title
  rarely reaches and a sentence almost always does. Diagnostic, not a gate: exact
  CAN be right on a long canonical string, so it surfaces the mismatch and the
  author decides (a judge or a containment scorer is the usual fix). Registry
  69 -> 70 checks. Found by red-teaming the scorer family before a wider release.

- **S19 now names a contradiction, not just a duplicate.** When a lookalike group
  (same question modulo an encoding variant) is keyed to CONFLICTING answers, S19
  says so loudly. This is the more dangerous half of the finding and S7
  (`contradictory-targets`, which gates on exactly this) cannot see it, because S7
  keys on the byte-exact question and these differ by a smart quote or a
  homoglyph. Motivated by F-027/F-028, which were real contradictory-key defects
  caught only because those questions happened to be byte-identical.

- **R22 `numeric-miss`.** A failed record whose answer is the same NUMBER as its
  target: an exact scorer marks "1/2" wrong against a key of "0.5", or "1,000"
  wrong against "1000", so a model that computed the right value is scored as a
  miss, accuracy is understated, and a fleet ranking can flip on it. The run-time
  mirror of S18, and the sibling R16 cannot see it: R16 is string containment
  ("0.5" is not in "1/2"), this is numeric equality. Reuses the same conservative
  parser as S18 (ints, decimals, thousands separators, integer fractions,
  percent, single number words). Diagnostic, not a gate: a task may deliberately
  require a specific FORM ("write it as a fraction"), so it surfaces the candidate
  and the author decides. Registry 68 -> 69 checks. Found by red-teaming the
  runs-on-disk family before a wider release.

- **S19 `lookalike-questions`.** S1 `dup-questions` is exact (casefold plus
  whitespace), so two copies of one question that differ only by a smart quote,
  an NFC-vs-NFD accent, or a Cyrillic letter that reads as Latin sail past it as
  distinct, which is exactly how a padded benchmark or a train/test overlap hides
  from a dedup pass. S19 reduces each item to a SKELETON (NFKC, casefold, a small
  cross-script confusables map, then drop everything that is not a letter or
  digit) and flags a group of items that share a skeleton but are not already
  exact duplicates, so it reports only what S1 could not see. It mirrors S1's key
  (question plus options), so an MMLU stem shared across different option blocks
  is still two items. Diagnostic, not a gate: a collision after folding
  confusables can be legitimate (a question ABOUT Cyrillic, a typography item),
  so it surfaces the group and the author decides, and a MIN_SKELETON floor keeps
  two short, genuinely different items from colliding on a few shared letters.
  Registry 67 -> 68 checks. The confusables map is the small high-value core of
  the Unicode table (Cyrillic and Greek that read as Latin), not the whole thing,
  on purpose: a genuine Cyrillic question stays untouched.

- **S18 `numeric-dup-options`.** A multiple-choice item whose options include the
  same number written two ways ("1,000" and "1000", "0.5" and "1/2", "12" and
  "twelve", "50%" and "0.5") is the F-002 failure reached through arithmetic: if
  one of the equal pair is the key, a model that computes the value and picks the
  other spelling is marked wrong while being right. S5 `dup-options` cannot see
  it, on purpose, its own notes record that folding punctuation or substrings
  cost 75 and 481 false positives on MMLU-Redux. Numeric equivalence is the
  tighter signal those rules were too blunt to reach: it fires ONLY when two
  options both parse as numbers and those numbers are equal, so a formula, a
  genotype, or a coordinate list never trips it. Diagnostic, not a gate (a
  notation question may legitimately list 1000 and 1,000), and it says louder
  when one of the pair is the keyed answer, because that is the case that
  mis-scores. Conservative parser: plain ints/decimals, thousands separators,
  integer fractions, a trailing percent, and single number words only, anything
  ambiguous stays unparsed. Registry 66 -> 67 checks. Found by pointing dino at
  its own blind spot while gap-hunting before a wider release.

- **S17 `target-leak`, the trench-coat detector.** Point dino at a raw feature
  table (`dinostomp stomp churn.csv --target-field churned`) and it flags any
  single column that all but determines the target: a label in a trench coat. It
  scores each column's normalized mutual information with the target, so it is
  base-rate robust (an 8%-churn label is not "predicted" at 92% by every column
  the way accuracy-lift would say), and it reads two leak shapes, a column whose
  VALUE gives the target (a refund flag that equals churn) and one whose
  MISSINGNESS does (a days-until-cancellation that is null unless the row
  churned). Two guards keep it honest: a cardinality ceiling so a unique id
  column is not "predictive" for a useless reason, and n/a when the target is
  free text (a Q&A eval, not a table). Diagnostic, and deliberately: it surfaces
  a CANDIDATE, because a genuinely strong feature and a leak look identical to
  any statistic, and only the author knows which columns exist at prediction
  time. The tool narrows 40 columns to 2; the human decides which are
  trench-coats. Added a tabular audit path (a `--target-field` with no question
  column is a feature table, not an error). Registry 65 -> 66 checks. Built
  after three models in a row ran datasets through dino and the one semantic sin
  it could not see was exactly this.

- **S2 `answer-leak` now reads multiple-choice stems (found by an outside
  red-team).** Fable ran dinostomp with GitHub access as the first outside
  red-team and planted "The Treaty of Versailles was signed in 1919. In what
  year was the Treaty of Versailles signed?" with 1919 among the options. It
  sailed through: S2 only ever scanned free-form items, an MCQ item carries
  `choices` and never entered that pool, and a whole MCQ set left S2 n/a. MCQ
  stems now get the control the free-form rule lacks, the distractor: flag only
  when the correct option is in the stem and NOT ONE distractor is. That control
  is what makes gating a numeric answer safe here (where the free-form rule must
  stay blind, D-037): "1919" present with 1918/1920/1921 absent is disclosure,
  while a comparison or a reading-comprehension passage names several options at
  once and is exempt. [D-071](FINDINGS.md#d-071).

- **The answer-column mapping banner no longer over-claims (same red-team).**
  Fable's answer column held option text ("Paris") beside numeric answers ("96",
  "7", "2"), and the small integers that fell inside the option count were read
  as INDICES, so the banner announced "the answer column indexes the options"
  over a column that plainly held answer text: a mapping guess that was wrong
  while sounding certain, the exact failure this tool exists to name. Two fixes:
  a value that is verbatim one of the options is read as that option, not a
  position into them; and a genuinely mixed column is reported as MIXED rather
  than asserted as one shape. [D-072](FINDINGS.md#d-072).

- **A per-call nonce for judges.** A python judge now receives `ctx["call"]`, a
  monotonic index unique to each grading call. A deterministic judge ignores it
  and stays byte-stable; a judge that MODELS a hot grader (a hosted judge sampled
  above temperature 0 gives different verdicts on identical input) keys its
  variation on it. This is the only way a python judge can express the
  self-inconsistency J3 exists to measure, and it is deterministic given case
  order so the probe still replays.
- **Three more thresholds pinned** (`min_scored_misses`, `shortcut_lift`,
  `judge_inconsistency_max`), with boundary trials sized to sit between the
  shipped setting and a 3x loosening: R16's evidence bar caught at 5 misses and
  skipped at 15, S9's shortest-option shortcut caught at 0.10 lift and missed at
  0.30, and a judge self-inconsistent on 12.5% of regrades caught at 0.05 and
  missed at 0.15.
- **Fixed a direction bug in `pin_thresholds.py`** ([D-070](FINDINGS.md#d-070))
  that had reported TWO ceiling dials (`self_preference_max`,
  `template_swing_min`) unpinnable when they were pinned: both are report floors
  (bigger fires less) but were missing from `LOOSEN_UPWARD`, so the sweep loosened
  them the wrong way. Surfaced by a fast per-threshold verifier disagreeing with
  the shipped sweep; the first patch's "no second case" claim was a name scan and
  itself wrong. With both fixed and boundary trials added, the self-own is
  34 of 35 pinned, 1 unpinned (only `near_dup_bits`, which needs the vision extra to size). Pinned `kr20_min` (P1, fleet forced to KR-20 ~0.35), `blind_lift_min` (R15, informed clears blind by 0.075), `ordering_flip_rate` (P6, a claimed pair that flips ~10% of resamples), and `template_swing_min` (P11, a 10-point framing swing over the report floor). `run_trials.py` now runs 100 planted defects.

### v0.62.0 (2026-08-13)

- **Authorship provenance and S16 `authorship-circularity`.** A spec can now
  declare who wrote each part (`provenance: {items_by, keys_by, scorer_by,
  witnesses_by, review_by}`), and S16 reports where a MODEL sits on both sides of
  an authorship loop: a model that keyed its own questions (the keys are not
  declared as independently verified), a model that wrote its own witnesses (the
  W1/W2/W3 gauntlet is not declared as independently written), or a model
  credited with all of it and no `review_by`. That model-grading-its-own-homework
  case is the exact trap three separate models walked toward while building evals
  with dinostomp. Solo HUMAN authorship is explicitly NOT flagged, one expert
  writing their own eval is ordinary practice, so S16 records it and moves on
  rather than lecturing. Diagnostic, not gating, and worded as a fact rather than
  a verdict. The `examples/graded/` pod carries an honest provenance block (it
  was authored end to end by a model), so S16 warns on it, the tool flagging its
  own example. Registry 64 -> 65 checks.

- **Partial credit.** A scorer can now hand out graded per-item credit, not just
  pass/fail. A `python` scorer returning a float in [0,1] (`return 0.7`) is the
  whole idiom: the verdict stays categorical (pass only on a perfect 1.0, so
  every dichotomous check keeps a clean pass rate) and the float rides alongside
  as `value`. The report averages it into `partial_score`, shown BESIDE accuracy
  and never instead of it, because "how often exactly right" and "how close on
  average" are different questions about one run. Two new gating checks guard it,
  so the feature ships with validators that can fail:
  - **W3 `graded-witness`**: a scorer that emits intermediate credit on its
    witnesses must have at least one witness pinning an intermediate
    `expect_value` (0<v<1), which R2 then verifies it hits. A "graded" scorer
    that only ever returns 0/1 is a binary scorer wearing a float, and this is
    what stops the partial score from being the accuracy sold twice.
  - **R21 `graded-range`**: every recorded graded value is a number in [0,1]. A
    scorer that behaves on its handful of witnesses can still emit 1.7 or NaN on
    real output, and R21 holds the actual records to the bound so `partial_score`
    never averages nonsense.
  Witnesses gained an optional `expect_value`. New `examples/graded/` pod: a
  closeness scorer where a weak model scores 50% exact accuracy but 0.72 partial.
  Registry 62 -> 64 checks.

- **W2 `surface-form`**, a new diagnostic: does a CORRECT answer survive the
  shape it arrived in? W1 mutates the scorer and asks whether the witnesses
  would notice it crediting too much; nothing asked the opposite question, so a
  scorer that LOSES a right answer to formatting was invisible to the battery.
  Found live while auditing a third-party benchmark's answer parsers: extraction
  stricter than the comparison it feeds (the comparison lowercased both sides,
  so case was meant not to matter, but the extractor's fallback was
  case-sensitive and returned nothing, leaving that leniency unreachable);
  first-match extraction grading a value the QUESTION supplied rather than the
  answer; and a label pattern whose separator could match zero characters, so a
  keyword in prose captured the following token.
  W2 perturbs the response in ways that must not change a passing verdict, and
  pairs them with a decoy that must still fail, so a scorer cannot pass it by
  crediting everything. It never demands a leniency POLICY: requiring
  `Answer:` is a legitimate choice, and a strict comparator is reported n/a
  rather than buried in false alarms. It flags our OWN shipped
  `numeric extract: first` default, the same bug class R16 catches from failed
  records after a paid run, except W2 catches it from the scorer alone before
  anything is spent.

- **[D-068](FINDINGS.md#d-068)** Six of the nine blind-spot corpus classes were
  detectable by `grep`. Each planter inserted a FIXED phrase, so every planted
  item carried a string present in none of 15,999 clean items. Six string
  constants, no model, no understanding, scored on a split they were not derived
  from: 106/106 strict recall, 0 false alarms, where dinostomp scores 0%. Items
  are published even for withheld splits, so the phrases were readable without
  ever seeing a label. Mitigated by drawing each insertion from a six-phrase
  pool, which drops the one-constant attack to 38%. Stated as a speed bump
  rather than a defence: a submitter reading more than one instance recovers the
  pool, and set-level plants like `implausible-distractor` still fall 100%
  because grepping one constant gets ~19 draws per instance. The published
  splits keep their old watermarks and were deliberately NOT regenerated; they
  were each scored once against a prior commitment, and rewriting them to look
  better is the tuning D-055 forbids.
- Found while testing whether a classifier could reach the blind classes. It
  scored 100% on seven of nine, which was the finding: a data-quality result at
  100% is a result about the generator. No classifier was built.


- **[N-023](FINDINGS.md#n-023)** Measured whether a 2PL IRT check would beat the
  point-biserial already shipped, before building one. It does not, in any of
  four worlds at any fleet size from 6 to 80; the best IRT advantage anywhere is
  +0.2%, inside noise. Two attempts were made to make IRT win first: an
  iterative refit of the ability scale, and progressively harder simulations.
  Harder worlds hurt both methods and closed the gap without reversing it. No
  IRT check was built. `python trials/irt_power.py` re-derives it. Incidental and
  more useful than the headline: on the realistic world both methods sit at 26%
  precision at six models, which puts a number on "almost no power at the fleets
  a practitioner has".


- **[N-022](FINDINGS.md#n-022)** Asked whether J2 (presentation-order bias) can
  be graded against the MT-Bench release. It cannot: `gpt4_pair` has 0 of 2,400
  both-order pairs. The near-miss is the useful part and is kept in full. The
  human file's 1,164 both-order comparisons are across DIFFERENT annotators (per
  annotator: 0 repeats, 1 pair). GPT-4 then looked heavily order-biased, 10.5
  points below humans on shared orderings at z = -6.82, and conditioning on
  model strength reverses the sign: it favours the first-shown response more
  than humans when that response is stronger (+12.5%) and less when it is weaker
  (-11.8%). Sharper discrimination, not position preference; 876 of 930 shared
  comparisons put the weaker model first, so one cell swamped the mean.
  Re-derive with `benchmarks/mt-bench-judge/order.py`, which exits nonzero if a
  future release ever adds both-order pairs.


- **[D-067](FINDINGS.md#d-067)** The held-back-class defence, the corpus's only
  protection against someone reading `taxonomy.py` and writing one checker per
  class, could not plant anything. Secret classes merged into the taxonomy
  correctly, but every planter lived in the committed `generate.py`, so a
  held-back class had nowhere to declare one and `build_instance` died on a
  `KeyError` if given one anyway. `n_held_back_classes_present: 0` was not
  "not armed yet", it was structural. Found by writing a throwaway
  `holdback.py` and running it. Still not armed: choosing which classes to hold
  back is a benchmark decision, not a bug fix.
- **Rejected, with its numbers**, so nobody re-derives it: stripping redundant
  brackets before comparing options reaches 8% recall on MMLU-Redux against the
  shipped 5%, and costs two false positives to gain one catch. One of them
  collapses `(∀x)(~Sx ⊃ ~Gx)` and `(∀x)~(Sx ⊃ ~Gx)`, which differ in negation
  scope and are the entire point of the question. The apparent precision gain
  (25% to 27%) was an artifact of three data points measured against a single
  error type.


- **[D-065](FINDINGS.md#d-065)** A one-based answer key read as zero-based
  resolved three options in four to the wrong text, silently; only the fourth
  fell out of range and raised S6, so the visible symptom covered a quarter of
  the damage. The base is now decided over the whole file and printed in the
  mapping notes. Two public datasets were affected.
- **[D-066](FINDINGS.md#d-066)** An extractive-QA span object (`{"start":..,
  "text":..}`) read as the answer key made 100 of 100 items look unanswerable.
  A target column holding objects is now refused, which is a structural fact
  rather than a preference between columns.
- **Options split one per column are now assembled** (`choice_1..4`,
  `ending0..3`, `answer_a..d`). This was the commonest layout the audit refused;
  the refusal used to tell the author to combine the columns by hand. Of 62
  datasets a public sweep had refused, 17 now load and 7 of those carry a real
  gating finding. All 20 existing pods verify unchanged.
- **Candidate column names extended** from the columns of datasets that were
  refused, not from imagination: `question_text`, `ground_truth`,
  `correct_option` and others. `correct_option` was absent, which is why
  `solution` won unopposed in D-064.


- **[D-064](FINDINGS.md#d-064)** A sweep flagged 85 of 100 items in a public
  exam dataset as having no correct answer. All 85 were false: the loader read
  the `solution` column (a worked derivation) as the answer key instead of
  `correct_option`. Behind it, a second bug: `correct_option` holds `[1]`, a
  single-element list wrapping a zero-based index, which `_resolve_choice_key`
  did not unwrap. The mapping now refuses when an explanation column and a real
  answer column are both present, rather than preferring whichever column makes
  the verdict cleanest, which would hide the wrong-key defects S6 exists for.
  Two other datasets that sweep flagged were verified real and still flag.
- **Engine fingerprint moved** to `0145ee1f00c46431...`; example reports, README
  and the findings feed regenerated. The preprint stays pinned at tag
  `preprint-2026-08-11`, whose engine is unchanged.
- `benchmarks/hf-sweep/sweep.py`: records WHY it refused a mapping, paces
  requests at 3s with a dedicated backoff for HTTP 429, keeps transient failures
  out of the append-only log, caps any upstream family at 3 audited files, and
  drops `mmlu` from the search terms (it was returning its own derivatives and
  setting the base rate).

**A receipt script that died on the platform it was written on.**

Held unreleased on purpose. Cutting a version here would restamp the package,
and the package version is inside the engine fingerprint, so every corpus
scorecard would read as produced by a different engine than the one auditing it.
Those five splits were each scored exactly once against a label commitment
published beforehand, and re-scoring them to match a new version number is the
tuning that [D-055](FINDINGS.md#d-055) exists to forbid. The preprint pins
v0.61.0 and states the ledger as it stood there; this entry lands in the next
release, which is what version pinning is for.

- **[D-062](FINDINGS.md#d-062)** `benchmarks/mmlu-redux/compare.py` printed its
  confusion matrix and then crashed with `UnicodeEncodeError` on a formal-logic
  item containing U+2261, because Windows consoles default to cp1252. The
  failure landed between the numbers and the receipts that justify them, which
  is the worst place for it: a reader re-deriving the number offline saw the
  number, then a traceback. Fixed by reconfiguring stdout to UTF-8 with
  replacement. Invisible to the test suite, which captures output through a
  UTF-8 pipe rather than a console.
- Ledger scorecard corrected: it stated a ratio and a self-defect count from an
  earlier state of the file (47:25 and "all twenty" against an actual 62:29).
- Engine fingerprint unchanged at `7fe879a3183bfcfe`: nothing under `src/`
  moved, and the version string was deliberately left alone (see above).

### v0.61.0 (2026-08-11)

**Five benchmark pods, three of which exist to prove earlier findings wrong, and
a check that had been passing an exam it could not read.**

- **[D-061](FINDINGS.md#d-061)** S9's shortcut feature tokenises with
  `str.split()`, so on a script written without spaces the whole stem is one
  token and the feature can only fire on identical strings. A Chinese pharmacist
  licensing exam carried a `pass` over 400 items that meant nothing. The same
  shortcut planted in English warns and in Chinese passes. It skips now, naming
  the reason; S9 still cannot audit those scripts, and the gap is visible in the
  report instead of hidden behind a green line. Predicted before it was looked
  for: every corpus fixture is ASCII.
- **[D-060](FINDINGS.md#d-060)** five pods added. `copa`, `movie-rec` and `asdiv`
  are the shapes that produced false findings in an unmapped sweep; with explicit
  mappings the first two audit clean and ASDiv drops from six duplicates to one.
  That is the correction made reproducible rather than asserted. `anli-r3` is
  clean; `agieval-sat-en` is not.
- **[F-028](FINDINGS.md#f-028)** an AGIEval SAT reading question keyed to two
  different answers, with byte-identical passage, question and options. Sixth
  assessment written for people in this repository.
- **[F-029](FINDINGS.md#f-029)** one ASDiv word problem present twice.
- **[D-059](FINDINGS.md#d-059)** S2 called `no` a leaked answer because it is
  spelled inside `enough`. Word boundaries now. The other twelve flags on ASDiv
  are a scope limit rather than a defect, and the rate is published rather than
  exempted away.

**Write-up.** Unfrozen once, deliberately, for a pre-arXiv pass: the abstract now
says what the battery catches and not only what it fails to catch, a disclosure
paragraph states that 1 of 29 findings has been sent to a maintainer, and the
sentence conflating pod count with finding count is split into two quantities.
Re-frozen at this version.

### v0.60.0 (2026-08-11)

**The judge checks now have an external answer key, and it says more about the
check than about the judge.**

Every external calibration in this repository graded a check that reads a dataset
at rest. The run, scorer and judge families have the least prior art and the
strongest claims, and their entire evidence base was planted trials we wrote and
clean pods we chose. That is the self-scored arrangement this project complains
about, sitting on the part a reader has most reason to doubt.

- **`benchmarks/mt-bench-judge/`** joins two things other people published: 3,355
  pairwise preference votes from 65 human annotators, and the verdicts GPT-4
  returned as a judge on the same comparisons. The judge had already been run and
  its decisions recorded, so the calibration costs no model and no API spend.
  `compare.py` calls the real `_judge_checks` rather than recomputing an
  agreement rate.
- **[N-019](FINDINGS.md#n-019)** on 1,262 comparisons with a decisive human
  majority, GPT-4 agrees 75.5% of the time. A held-out human annotator agrees
  with the majority of the others 79.0% of the time, on the identical statistic.
  The judge is 3.5 points below people, not above them. The convenient baseline
  is annotator unanimity at 59.8%, against which the judge appears to beat
  humans outright; that is a different question, and reaching for it first is the
  reason controls get computed before conclusions here.
- **[D-056](FINDINGS.md#d-056)** J1's threshold is 90%, which no human reaches on
  this key, so the check fires on any judge graded against annotator preference
  including a perfect one. Defensible for the probe it was built for, where a
  verdict is true by construction; a false-alarm machine on an annotation-derived
  key. Scoped rather than retuned on one dataset. Its finding text also asserts
  "known by construction" whatever the probe contains, which is the one word a
  reader would rely on.

**Still uncovered, and said so in both the paper and the ledger.** J2 needs the
same comparison in both presentation orders and the release records 0 of 2,400
that way, so position bias remains externally untested. J3 needs a repeated
grading, J4 a second judge family. Three of four judge checks keep exactly the
self-scored evidence they had.

**Write-up.** Adds the reachability ceiling that decides whether any of this is
worth running: of MMLU-Redux's 370 flawed items, only 10.5% are of a type a
file-only check could reach at all, so a perfect one tops out there and ours
reaches 5% of that tenth. Adds the justification for shipping the five-bit
perceptual threshold when eight nearly doubles recall. Five uncited references
now cited, including CIFAR-10, which the paper discussed four times without
crediting. `\pdfoutput=1` added and the typewriter font moved to Latin Modern:
the paper was emitting Type 3 bitmap fonts on 11 of 14 pages, which arXiv flags.

Ledger at 101 entries (F 26, D 56, N 19). 582 tests.

### v0.59.0 (2026-08-11)

**An external review found that a held-out number had been laundered, and the
fix was to retire the split rather than argue about it.**

- **[D-055](FINDINGS.md#d-055)** `heldout-assets-2026-08` was scored once blind,
  returned 99.1%, and that single miss revealed a gating-check hole. We fixed the
  tool and rescored the same split to 100%, then reported the 100% beside a
  caption promising each split was scored once against a commitment made before
  scoring. Every clause true, the paragraph not: the split had been developed
  against. It is now marked `spent`, its scorecard is deleted, and
  `heldout-assets-2026-08b` was generated after the fix and scored once. Same
  100%, and now it means something. The number was never wrong; its provenance
  was, which is worse, because a wrong number gets caught by the next measurement
  and a laundered one does not.
- **[D-053](FINDINGS.md#d-053)** the loader treated an option list as choices only
  when it held two or more entries, so a list reduced to one -- exactly what a
  missing correct answer looks like on a binary item -- dropped the `choices` key
  and silenced four checks including a gate. A dataset that had lost the correct
  answer from a two-option item audited clean. Found only because image items are
  binary; the defect was hiding from the fixtures, not from the checks.
- **[D-054](FINDINGS.md#d-054)** all 21 declared defect classes are planted for the
  first time. The corpus grew image-backed instances to do it, and clean instances
  carry images too, because four checks that only ever met planted data would have
  unfalsifiable recall.

**Write-up.** Seven internal inconsistencies found by the same review are fixed:
the split count and blind-spot totals across four splits rather than three, the
"every false alarm is S3" claim widened to all 414 clean instances, the abstract's
recall claim scoped to the one error class it covers, the version-pin footnote
scoped to exclude the four superseded measurements, held-back classes disclosed as
documented-but-not-armed, the 25-versus-26 findings discrepancy explained, and the
100% given the same deflationary treatment as the 5%. The cross-tool appendix lost
its self-scored column entirely.

**Stated rather than closed.** There is no held-out text-side calibration, and
ciFAIR is not one: it scores a different check on a different modality. The gap
cannot be closed retroactively, since the check has now seen all of MMLU-Redux.
It needs a different hand-annotated corpus, scored once.

Ledger at 99 entries (F 26, D 55, N 18). 582 tests, four corpus splits.

### v0.58.0 (2026-08-11)

**Pointed at a published statistical release that is not an eval, and three
things broke: two in the tool, one nearly in somebody else's data.**

The Anthropic Economic Index (CC-BY, 2.1M rows across two files) has no
questions, no answers and no model. The core battery declined it correctly and
twice: no column looks like the input, and the larger file is over the 100MB read
cap. Both refusals are right and neither is useful, so the release's own README
became the contract instead.

- **The dataset audit now has an extension surface.** `lint_dataset` loads
  installed extensions and hands them the PATH, before the core decides whether
  it can read the file. The 100MB cap still governs every core check; it is no
  longer the reason a streaming check never gets to look. A file the core cannot
  hold now produces a report whose every core check is a skip carrying the
  reason, and whose verdict can never be better than `incomplete`.
- **`--no-extensions`** on `stomp`, `report` and `verify`, so a report committed
  to a repository re-derives on any machine with this engine rather than only
  where the author's plugins are installed.
- **`extensions/dinostomp-aei`**, eleven checks reading the Economic Index
  README as an evidence contract. Findings: [F-026](FINDINGS.md#f-026) and
  [N-018](FINDINGS.md#n-018).

**Fixed.**

- **[D-048](FINDINGS.md#d-048)** `stomp` printed `OK AT DATA SCOPE` over a report
  whose own summary said `incomplete`: the verdict line tested the warning count
  before the computed verdict. Coverage now outranks tone.
- **[D-049](FINDINGS.md#d-049)** `verify_report` re-derived using whatever
  extensions happened to be installed, so installing one unrelated plugin turned
  all nine committed example reports into `mismatch` -- which reads as "stale, or
  edited by hand", and neither had happened. It now re-derives with the extension
  set the published report NAMES, and answers `unverifiable` when that set is not
  present, which is an honest answer rather than a wrong one.
- **[D-050](FINDINGS.md#d-050)** the new partition check summed in floating point
  and flagged `40.63 + 59.38 = 100.01` as a violation in the released data. Both
  values are correctly rounded and the sum sits exactly on the permitted bound;
  the check fired on `100.00999999999999`. Fixed before shipping, but it is in
  the ledger because a fabricated finding against a real publisher, produced by
  an arithmetic bug, is the worst output this tool has.

**Scoped, not fixed.**

- **[D-051](FINDINGS.md#d-051)** an extension is marked `validated` for
  DECLARING TRIALS and CLEAN_PODS, not for passing them. `TRIALS = ["trust me"]`
  earns the label, counts toward coverage, and lets a `fail` turn a verdict
  `broken`. The docstring claimed enforcement the code does not perform and has
  been corrected. Running third-party trials needs a defined trial format and an
  isolation decision, and both deserve doing deliberately.

Ledger at 95 entries (F 26, D 51, N 18). 566 tests.

### v0.57.1 (2026-08-10)

**A consistency pass over the whole repository, and a checker so the next one is
not done by eye.**

- **`scripts/check_consistency.py`** asks the question no individual test asks:
  does the same fact, stated in different files by different passes, still say
  the same thing. Ten areas: version across five places, the engine fingerprint,
  the check registry against every doc that counts it, the findings ledger
  against its feed and both summaries, trials, benchmark pods, the corpus
  taxonomy against its manifests and scorecards and leaderboard, numbers quoted
  in prose against the scorecard they came from, dead file links, and whether
  any secret is tracked by git. Runs in CI and as a test; negative-tested with a
  stale count, a stale version and a wrong fingerprint.
- **Its first run found the README claiming 23 audited benchmarks with 25 pods
  on disk.** Corrected in both places, along with a doubled comma and a sentence
  in FINDINGS.md that had grown two conflicting clauses.
- **Three headerless markdown tables** rendered as empty header rows on GitHub,
  including the findings summary in the README. All three now have headers.
- **Four genuinely unused imports removed** (`NEEDS` and `ExtensionError` in
  lint, `WITHHELD` in sandbox, `Any` in suggest).
- **`templates.py` had no test naming it.** It is reached only through the
  runner's framing probe, so a change to a framing would have been caught by
  nothing until a probe run disagreed with a published number. Four tests now
  pin the rules its own docstring states: the item text survives verbatim, names
  are unique and resolvable, no framing constrains the output format, and a chat
  input is refused rather than reframed.

545 tests.

### v0.57.0 (2026-08-10)

**The scorekeeper's workflow, end to end.** The corpus had a generator, a
taxonomy and a scorer, and no way for anyone to actually submit anything or for
a result to be published.

- **`heldout-2026-08`**: the first withheld split. 400 instances, 100 clean, 162
  blind-spot. Labels are gitignored and the commitment is in `SPLITS.md` and in
  the split's own manifest, written before any score was computed against it.
  dinostomp scores 100.0% covered, 0.0% blind (strict), 5.0% false alarms.
- **Submission validation.** `score.py` REFUSES a malformed submission rather
  than scoring it. An unknown instance id and a missing `detected` both look
  exactly like "found nothing", so a typo, a wrong `--split`, or a list where an
  object belongs would have quietly published 0.0% about somebody else's tool.
  Five malformed shapes are negative-tested; a valid PARTIAL submission still
  scores, and the row says how many instances it answered.
- **`corpus/LEADERBOARD.md`**, generated by `corpus/leaderboard.py`, never
  hand-kept. It is **not sorted by score**: a leaderboard ranked on recall
  rewards a detector that flags everything, so rows are ordered by split then
  name and every row carries recall, blind-spot recall and the false-alarm rate
  together or it does not appear. A test asserts both.
- **An issue template** for submissions, promising the two things that make
  submitting worth doing: the number is published as measured, and if the corpus
  turns out to be wrong that becomes a finding against the corpus.
- Scorecards moved to `corpus/scorecards/` and now carry the split's label
  commitment, so a published number is tied to the split it was measured on.

`heldout-2026-08` carries **0 held-back classes**, stated in the registry rather
than implied: `holdback.py` does not exist yet, so the taxonomy-overfitting
defence is documented and not yet armed.

6 new tests, 540 total.

### v0.56.0 (2026-08-10)

**Withheld splits that are actually withheld, and held-back defect classes.**

- **A nonce**, read from `DINOCORPUS_NONCE`, mixed into every instance seed AND
  into the class schedule. Generating a non-public split without one is refused,
  and setting one while generating `dev` is refused too, because that would make
  the public split irreproducible for everyone else.
- **A label commitment.** A withheld split publishes its instances and a
  SHA-256 of its labels, before any submission is scored. `score.py` REFUSES to
  score labels that do not match it. A benchmark whose author can edit the
  answer key after seeing the answers is not a benchmark, and that includes this
  one. Negative-tested by editing a label and watching scoring refuse.
- **Held-back classes**: `corpus/holdback.py` is gitignored and absent here;
  when present its classes are planted and never published. Manifests publish
  the COUNT, so a submitter knows they exist and how many, and never which.
  Rotation defends against memorising instances, which barely threatens a
  rule-based detector; held-back classes are the defence against reading
  `taxonomy.py` and writing one checker per class.
- **[corpus/SPLITS.md](corpus/SPLITS.md)**: every split ever released, its
  commitment and its status. Splits are archived, never replaced, and a score
  without a split id means nothing.

**D-047, both halves.** v0.55.0 documented a split with withheld labels and
shipped none: seeds were `sha256("dinocorpus/{split}/{index}")`, public
arithmetic, so `--split test` printed the labels it was supposed to withhold,
and the class schedule was `index % len(plantable)`, computable with no code at
all.

The fix then rewrote the public split. Threading the secret through as
`f".../{index}/{secret}"` appended a trailing slash even when empty, every hash
changed, and `dev` became a different 204 datasets under the same name. Nothing
failed; the only symptom was the published false-alarm rate moving 15.7% to 5.9%
with no edit to any check. SPLITS.md, written the same hour, opens with "splits
are archived, never replaced". The code broke that within thirty minutes,
silently, toward a better-looking score. The seed now appends the secret only
when there is one, `dev` is byte-identical to what v0.55.0 published, and a test
pins its labels hash.

8 new tests. Ledger: 89 entries, 25 F, 47 D, 17 N.

### v0.55.0 (2026-08-10)

**dinocorpus: a benchmark for detectors of broken evals, built so this tool
cannot win it.** 204 small datasets, one planted defect each, labelled with what
and where. Ground truth is a fact about how the file was written, so it scales
without annotators and without a judge.

- **21 defect classes, 9 with no corresponding check**, planted deliberately.
  dinostomp scores 100% on the classes it covers, **4.9% on the blind-spot arm
  and 0.0% under strict scoring**, against a 15.7% false-alarm rate on the clean
  arm. A benchmark whose author scores 100% measures the author.
- **Two of the 21 classes come from this repo's own check registry.** The other
  19 come from the benchmark-error literature or from real audits, each citing
  its source, and a test fails if that ratio starts to invert.
- **Strict scoring**, because generous scoring was wrong. On a blind-spot
  instance any finding counts as a catch, and the first run credited four
  catches that were all the same unrelated position-bias warning firing by
  chance. Strict mode requires the finding to name an item the defect was
  planted in.
- **A clean arm at one instance in four.** Recall without a false-alarm rate is
  half a number and both are always printed together.
- Any tool can be scored: `python corpus/score.py --submission yours.json`.

**D-045: the first scored run found three defects in the corpus and none in the
battery.** The clean pool was not clean (arithmetic options were sorted
numerically, so the gold sat mid-list and S3 correctly flagged 20 of 51
"clean" instances); the answer-leak planter put its defect in a choice item,
where S2 is n/a by design; and the surface-shortcut planter wrote `[orrin]` into
the stem and `orrin` into the option, which S9 tokenises as different tokens on
purpose. All three errors ran AGAINST the author's tool, which is the unusual
direction and the reason it is recorded.

**D-046: S3 warns on one clean dataset in six at exactly the size its own
applicability rule admits.** The margin is absolute and applied to each of k
positions with no multiplicity correction, so clean 4-option data trips it 16.3%
of the time at 20 items, 8.7% at 24, 3.3% at 30 and 0.4% at 50. And
`min_choice_items = 20` is where S3 starts running. Not retuned on one
measurement: `position_margin` moves from `judgment` to `calibrated`, and the
warning now states the chance rate at the size it fired on, computed
analytically per report.

12 new tests. Ledger: 88 entries, 25 F, 46 D, 17 N.

### v0.54.0 (2026-08-10)

**The report is an evaluation report now, not just an audit.** It carried the
verdict, the claims and all sixty-one checks, and almost nothing about what the
models did: per-model accuracy existed only inside one check's evidence blob,
item difficulty was computed and thrown away, and cost was checked but never
totalled. Running experiments, recording them and interpreting them is the point
of an eval, and the report was doing one of the three.

A new `## Results` section, ahead of the claims:

- **Per model**: records, checkable, judgeable, accuracy with a Wilson interval,
  passes, failures, output tokens, spend.
- **Fleet**: mean, range, spread, KR-20, how many items separated nobody, and
  the minimum gap the item count can resolve.
- **Item difficulty**, hardest first: `p`, point-biserial discrimination, which
  models missed it, and the most common wrong answer. The rendered table caps at
  25 rows and SAYS SO; the full table is always in `STOMP.json`.
- **Slices**: accuracy by every metadata field the items carry, with intervals
  and an explicit note that no multiplicity correction is applied. MMLU now
  carries its `subject`, so this is accuracy by subject.
- **Cost**: spend and tokens, summed from the records.

Three rules hold it together, all of them this project's existing doctrine
pointed at a new surface:

- **Accuracy is ON CHECKABLE output** and `judgeable` sits in the same row.
- **Every number is recomputed from the RECORDS**, never read from a summary. A
  summary is a derived artifact the battery treats as untrusted everywhere else,
  and a results table that trusted one would be the single place a hand-edited
  number survives. Tests assert the accuracy here equals R7's, equals the
  summary written at run time, and that KR-20 and spread equal P1's and P8's.
- **Nothing in Results can gate.** A hard item is not a defect. A test walks
  `results.py` for any Reporter call to keep it that way.

Blind and ablate PROBE runs are excluded: a deliberately handicapped control
pooled into a model's accuracy would publish the handicap as the score.

12 new tests, and the parity tests were negative-tested by breaking the accuracy
by 0.01, by counting uncheckable into the denominator, and by returning a wrong
KR-20. All three fire.

### v0.53.2 (2026-08-10)

- **CI installs the `vision` extra.** Without it S15 can only skip, and a check
  that is never exercised on the second platform is a check the OS-difference
  class (D-002, D-014, D-044) cannot find anything in.
- **A trial may declare a PRECONDITION**, and one that cannot run is counted out
  of the denominator and NAMED. The S15 trial read as `** MISSED **` in CI when
  Pillow was absent, which is wrong: the check skipped, correctly. Calling it
  caught would have been worse. The scorecard now prints "91 of the 92 declared"
  with the reason rather than quietly shrinking.
- **N-017's precision figure corrected before anyone else read it.** The pod's
  70-of-73 reads as 96% and is an artifact of a sample built around the
  annotated duplicates. On the full 60,000: 158 flagged, 70 annotated edges, 3
  cluster-internal, and 85 involving an image ciFAIR never annotated. The 85 are
  unverified and are not a finding.

### v0.53.1 (2026-08-10)

**D-044: the asset-path guard asked the local operating system what "absolute"
means.** `Path(uri).is_absolute()` answers for the current platform, so
`C:/Windows/System32/...` was refused here and accepted on Linux, where it is an
ordinary relative path whose first segment is named `C:`. CI caught it within a
minute of the v0.53.0 push. Nothing escaped: the containment test after it is
what confines a read and was never fooled, so the consequence was a
non-portable path that one platform quietly accepted rather than an escape. Now
tested under both conventions plus root-anchored-without-drive and UNC forms,
with the Windows shapes asserted on every platform and a second test proving
ordinary relative paths still resolve.

Third defect here that only a second operating system could find, after the
line-ending pair. CI on a different OS is not redundancy for this class, it is
the only instrument.

### v0.53.0 (2026-08-10)

**An item's input can be a FILE now: an image, an audio clip.** The battery was
built for text and most of it never looked at the modality, which turned out to
be the interesting part. Every run check, every claim check, the witness gate
and the mutation gauntlet work unchanged. The four checks that are new are the
ones a text pod has no use for.

- **`input_ref` in the items schema**: `{kind, uri, sha256, split}`. A pointer
  can go stale without the dataset changing, which is the drift problem this
  project already solves for specs, scorers and engines, arriving somewhere new
  and getting the same answer.
- **An asset-backed item is identified by its asset's BYTES**, so
  `dup-questions` (S1) and `conflicting-keys` (S7) work on pictures for free
  rather than needing image-shaped copies of themselves.
- **Four new checks, 57 to 61.** `asset-drift` (S12) re-hashes every referenced
  file and refuses any path that leaves the pod; `label-in-path` (S13) catches
  the one-directory-per-class layout that puts the answer in the filename;
  `split-leak` (S14) catches the same asset in train and in test;
  `near-dup-assets` (S15) catches the same picture at different bytes.
- **The core keeps its two dependencies.** Only S15 needs pixels, and it lives
  behind `pip install 'dinostomp[vision]'`. Without it that check SKIPS and says
  what it could not do, because "no near-duplicates found" and "I cannot look
  for near-duplicates" are different sentences and only one of them is true.
- **Six planted-defect trials and one clean pod**, so 92 of 92 and 16 of 16.
  Every image in them is a real PNG written by a forty-line stdlib encoder: a
  trial over fake `.png` files would prove the checks read a JSON field, which
  is not what they claim to do.

**N-017: scored against a human answer key, in a modality the battery was never
built for.** Barz & Denzler hand-annotated every CIFAR-10 test image with a
near-duplicate in the training set and published the pairs (ciFAIR).
`benchmarks/cifair/` runs the battery's own detector against that annotation:

```
 bits    recall on genuine duplicates   also on very-similar   test/train pairs flagged
    0                    0/249 = 0.0%                   0/37                          2
    3                  27/249 = 10.8%                   0/37                         55
    5                  70/249 = 28.1%                   0/37                        158  <- shipped
    8                 131/249 = 52.6%                   5/37                        506
```

Fewer than one duplicate in three at the shipped threshold, which is the
unflattering half and now stated in the ledger. The other half is the `0.0%` at
zero bits: **not one of the 286 annotated pairs is byte-identical**, so S1, S7
and S14 find none of them, and 28% is measured against zero rather than against
a better check.

Precision has two numbers and the flattering one is an artifact. On the
constructed pod, 70 of 73 flagged pairs are exactly what ciFAIR annotated, which
reads as 96% and is a fact about a sample built around the annotated duplicates.
On the full 60,000 at the same threshold: 158 flagged, 70 annotated edges, 3
joining two annotated images by an edge ciFAIR did not list, and **85 involving
an image it never annotated**. Those 85 are unverified and are not a finding.

The 3 in the middle nearly became one. They read as duplicates ciFAIR had
missed; all six images turned out to be annotated, each linked to a different
member of its own cluster, because ciFAIR publishes pairs rather than cliques.
`compare.py` computes that three-way split so the next person does not have to
think of it.

`near_dup_bits` moves from `convention` to `calibrated`. The default STAYS at 5
even though 8 nearly doubles recall, for the reason recorded when the MMLU-Redux
comparison nearly reversed a case-folding decision: a measurement on one dataset
of 32x32 photographs is not a licence to reset a default for documents or
spectrograms. There is **no `F` entry for CIFAR-10**, deliberately: that it has
train/test duplicates is Barz & Denzler's 2020 result, and filing it in the
findings-against-others series would be claiming their work.

**D-042: the bare-file path dropped `input_ref`, and reported ten distinct
photographs as one duplicated item.** `build_items` rebuilds items from the
columns it recognises rather than copying the row, and it did not recognise this
one, so every image keyed on the shared prompt and two GATING checks fired on a
dataset with no defect in it. The docstring of the function that broke had
described this exact failure one commit earlier. Fifth entry of that shape in
the ledger, and the first where the dataset being misread was one this tool
wrote.

**D-043: the specificity arm caught a false-positive class in S15 before
release, and the check was not wrong.** Ten "distinct" fixtures were ramps
differing only in phase; dHash compares each pixel to its neighbour, so it
encodes gradient DIRECTION and they are identical to it. The fixture is fixed,
the limitation is documented in `perceptual.py`, and S15 stays a diagnostic that
warns and prints its distances rather than gating a verdict. A check with a
known false-positive class must not be able to turn a report `BROKEN`.

495 tests, trials 92/92 and 16/16. Ledger: 85 entries, 25 F, 43 D, 17 N.

### v0.52.0 (2026-08-10)

The README now LEADS with what the battery found rather than with what it is,
and `findings.json` stops being a convenience dump and becomes a published,
versioned, validated interface.

- **`findings.json` is a contract now, at `schema_version` 1.0.0.** Validated
  against the new [docs/findings.schema.json](docs/findings.schema.json) BEFORE
  it is written, so a feed that violates it never reaches the disk to be
  committed by accident. The compatibility rule is stated rather than implied:
  within a major version, fields are only added. Every record gains
  `series_name`, `date_iso`, `date_precision`, `status_class` and a permalink
  `url`; the feed gains the dinostomp version and the engine fingerprint that
  produced it.
- **D-040: three defects the feed shipped with, found by writing the schema that
  should have existed first.** `date` was not always a date, and one entry reads
  `first live fleet`, so anything calling `date.fromisoformat` broke on it;
  `date_iso` is now **null** wherever the ledger has no full day rather than
  inventing one. A blank subject had passed silently and the very first
  validation run rejected it ([D-039](FINDINGS.md#d-039)). And there was no
  version, so nothing could depend on it.
- **`status_class` refuses rather than defaults.** An unrecognised status raises
  instead of dropping into an `"other"` bin, because a silent catch-all is how a
  mis-typed status becomes a finding nobody can filter for. Every
  default-shaped bug in this ledger has been the flattering one.
- **D-041: the numeric scorer artifact finally has an id.** `kind: numeric`
  extracts the FIRST number, which is a trap on a model that shows its working;
  found live where it scored a model `0.000` against a real accuracy of `0.438`
  and ranked it LAST in a fleet it was leading. Filed `scoped, not fixed`: the
  default stays, because `extract: last` is a trap in the other direction, and
  R16 exists to catch a wrong declaration. **The reason for the entry is worse
  than the defect** -- the case lived in a source comment and one changelog line
  for six releases while the README cited it under the sentence "every row is a
  real finding with a receipt in FINDINGS.md". There was no receipt. It was
  found by trying to put a finding id next to the claim.
- **A case good enough to cite in a README is good enough to number**, now a
  rule in CONTRIBUTING.md.
- **The README's counts are pinned to the feed.** The footer said "the thirty
  findings against itself" while the ledger held forty-one, for six releases.
  Two new tests close the class: one pins the headline counts and the
  self-audit sentence, one fails if the README cites a finding id that does not
  exist. Both negative-tested by breaking the README and watching them fire.
- Schema rejection is negative-tested on seven mutations (blank subject,
  invented date, renumbered id, unknown bucket, stray field, empty feed,
  truncated engine hash), each verified to fire rather than assumed to.

482 tests. Trials unchanged at 86/86 and 15/15.

### v0.51.0 (2026-08-10)

Two more assessments whose outcome is somebody's licence to practise.

- **F-025: the 2023 Chinese Pharmacist Licensure Examination offers the same
  option twice on 16 items.** Ordinary drug names and patient descriptions
  repeated inside one five-option list (`['卡维地洛片', '卡维地洛片', ...]`). Two
  further duplicates are a transcription artifact, where the source replaced
  formula images with the literal string `img` and two distinct options
  collapsed onto it; those two are separated out and claim nothing about the
  exam. **None of the eighteen is double-keyed**, which is the honest limit: the
  effect is a five-option item offering four, raising that item's guessing floor
  from 20% to 25%, not a candidate marked wrong for being right.
- **N-016: NCLEX-style items came back clean on 28 items**, and the entry title
  carries the word `underpowered` because 28 is a sample where absence proves
  very little. The more interesting part is the ceiling it exposes: the bank has
  ten item types (highlight, ordered response, matrix, bow-tie, exhibit) and the
  battery reads only single-key multiple choice, so **it has nothing to say about
  58 of the 86 rows** and did not pretend otherwise.
- The 28-of-86 arithmetic is documented in the loader rather than discovered
  later, after two loader defects in two days (D-034, D-039) that both began as
  an unstated filter. A `Select All That Apply` key could be stored as a list
  target and deliberately is not: a list target means "any of these is
  acceptable" and SATA means "all are required".

### v0.50.0 (2026-08-10)

Pointed the battery at assessments written for PEOPLE, by the bodies that
certify them, rather than at ML benchmarks.

- **N-015: MedQA-USMLE passed every applicable check.** 1,273 items from the
  exam family that decides who practises medicine in the US: no duplicate
  questions or options, no missing targets, no conflicting keys, no leakage, no
  position or length bias. Several of the eighteen ML benchmarks here fail at
  least one of those. **The entry states at length what this is not evidence
  for**: the comparison is uncontrolled, and two of the three human exams in the
  same batch DID produce findings. What it does establish is narrower and worth
  having: a dataset can come back clean, so the battery's findings are not an
  artifact of pointing it at anything.
- **F-023 AQuA-RAT**: 7 of 254 items offer a duplicated option, and on most the
  duplicate IS the key, so a model that computes the right number and picks the
  other option holding it is marked wrong for being right. Verified against the
  source rows, because this pod strips option labels and the loader was a
  suspect.
- **F-024 Iranian driving licence test**: the correct answer is the longest
  option in 57 of 126 items, 45% against a 25% baseline. A candidate who knows
  no road law can beat chance by picking the longest answer. First non-English
  item set audited here; length is measured in characters and needed no Persian.
- **D-039: the loader mis-keyed that entire exam by one.** Its answers are
  1-indexed strings; the loader assumed 0-indexing, dropped every item keyed to
  the last option (126 rows became 75) and silently shifted the rest. It then
  reported a position-bias warning that was purely its own off-by-one. A wrong
  key is worse than a dropped row: D-034 made numbers wrong, this made them
  plausible AND wrong, which is the kind that gets published. The index base is
  now derived from the split, and an undeterminable base resolves nothing rather
  than guessing.

### v0.49.2 (2026-08-10)

The findings ledger is now generated where it can be, and queryable.

At 74 entries the hand-maintained index had already drifted twice (once on
ordering, once when an entry reached one copy and not the other), both caught
after the fact by assertions. Generating removes the class instead of policing
it.

- **`findings.json`**: every entry with its id, checks, date, status, subject
  and summary. For anyone who would rather query the ledger than read two
  thousand lines of markdown.
- **A BY CHECK cross-reference**: every finding a given check has produced. This
  is the view to read before changing a check, because it is that check's own
  track record including the times it was the thing at fault. `S2` has four:
  two against other people's datasets, two against itself.
- **A BY SUBJECT cross-reference**: every finding against a given dataset, tool
  or harness.
- `python scripts/index_findings.py` regenerates all of it between explicit
  markers; `--check` fails if it is stale, and CI runs it. The prose entries
  stay the source of truth and stay hand-written.
- **Three N entries carried no status at all**, and the test named
  `test_every_finding_states_a_check_and_a_status` did not notice, because it
  asserted only that a separator existed. The index generator found them. The
  test now asserts what its name claims.
- An unanchored regex in the same test was reading the new cross-reference rows
  as index rows; it now parses the index table specifically.

### v0.49.1 (2026-08-10)

- **D-038: a `choices` mapping was announced and then silently ignored.** A
  column holding a delimited string (`"a|b|c"`) printed `choices <- choices` and
  the audit then treated every item as free-form, skipping five option checks
  without saying so. The inverse of the rule the dataset audit rests on: the
  guess was shown and its DISCARDING was not. Now named, with the remedy
  (`data.separator`) named too, since the usual cause is a CSV export.
  Negative-tested so a working choice pod stays quiet.

### v0.49.0 (2026-08-10)

Attacked the SPEC the way CONTRIBUTING asks an outsider to, and ran every
command the docs tell a reader to run.

- **N-014: nine adversarial pods, nine caught, none cleared.** A scorer that
  always passes, witnesses that never fail, a 99% claim on 24 dry items, one
  item repeated 24 times, a phantom model, a model beating itself, an all-`yes`
  answer key, a missing canary. Four were refused before anything ran.
- **D-037: the ninth exposed a blind check.** A pod whose every question ended
  "(It is 21.)" scored **0 of 24** answer leaks. S2 exempts numeric targets
  wholesale, so it could not detect leakage in GSM8K, MATH, DROP or any
  arithmetic dataset. The exemption's benefit was measured when it was added (it
  killed 27 GSM8K false positives); its cost was never measured, and its cost
  was total. Fixed with a discriminator rather than a reversal: a number stated
  as a premise stays exempt, a number introduced by an answer-disclosing phrase
  does not. **24 of 24 now caught, and 0 new false positives across 4,609 real
  items** (GSM8K stays at 0).
- **Every runnable command in the docs was executed from a fresh install.** All
  work. One documentation fix: METHODOLOGY's first example exits 4, not 0,
  because the smoke pod is deliberately `INCOMPLETE`, and the exit-code table
  explaining that was eight hundred lines away. Now said at the example.

### v0.48.0 (2026-08-10)

Installed the tool from scratch, as a stranger would, and pointed it at the kind
of file a stranger has. Two defects, both in the first thirty seconds of use.

Every run in this project's history had been from a clone with `pip install -e`,
from inside the repo. Nobody had ever done `pip install` into an empty
virtualenv and run the documented quickstart from somewhere else. That path
works (scaffold, plan, run, stomp all clean), and the data path did not.

- **D-035: a UTF-8 BOM refused a valid file**, in an error that named its own
  fix (`decode using utf-8-sig`) without applying it. Excel, Notepad and
  PowerShell's `Out-File` all write one by default, which makes it close to the
  most likely first-file failure a Windows user can hit. Reading is now
  BOM-tolerant via `spec.read_data_text`; writing stays plain `utf-8`, because
  writing a BOM would change the bytes the drift boundary hashes.
- **D-036: a semicolon CSV was diagnosed as badly-named columns.** The tool
  offered the whole header line, `id;input;target`, as a candidate column name,
  and the fix it suggested would not have worked. Semicolon CSV is the default
  Excel export in every comma-decimal locale. A one-column header containing a
  common delimiter is now named as a parsing problem, and the guard is
  negative-tested so a genuinely narrow file does not get the hint.
- A twenty-case fuzz pass (empty file, blank lines, JSON array, CRLF, numeric
  target, nulls, duplicate ids, emoji and RTL text, a 900KB item, nested input,
  truncated JSON, prose in a .txt) produced **no crashes**: every case either
  audited or refused with a reason. Both defects above were bad MESSAGES and a
  needless refusal, not instability.

### v0.47.0 (2026-08-09)

Five benchmarks with shapes the battery had never met, and four findings.

The first thirteen were nearly all short-question, four-option English MCQA, so
they exercised the same checks repeatedly. These bring a long passage in front
of the question, a free-form numeric answer with no options, and answer spans.

- **F-019 LogiQA**: 8 of 650 items offer a duplicated option, and three offer
  `['.', '.', '.', '.']` — four identical full stops, unanswerable by
  construction. Five have the KEYED answer duplicated. The contexts are intact,
  so the options column of `lucasmccabe/logiqa` is damaged, not truncated in
  transport.
- **F-020 DROP**: 86 duplicated questions in 2000, and 37 keyed to DIFFERENT
  accepted answers, so the same question is graded against different keys
  depending which copy a sampler draws.
- **F-021 MATH-500**: 2 problems whose answer is written in the question. The
  first free-form dataset here, and the first to reach the answer-leak path at
  all.
- **F-022 RACE**: one item offering the same option twice; a four-option
  question that offers three.
- **MuSR: clean.** Reported because a clean result from a check that fires
  elsewhere is worth as much as a finding.
- **D-034: the DROP loader discarded 96% of the split**, keeping only
  single-span answers, and the audit was run and read on the surviving 83 items
  before anyone checked. Every number was wrong (`1/17/1` against the truth of
  `86/0/37`), and the 17 answer-leaks were pure sampling artifact. Fixed with a
  list target, which the items schema has always supported. Third loader defect
  of this shape here, and they share one: a fetcher decision that looks like
  tidiness is a claim about the data.
- Twice this session the ad-hoc script written to VERIFY a finding was less
  careful than the check it was auditing: a naive substring pass flagged 75
  MATH-500 leaks where S2 reports 2, and an order-sensitive comparison called 38
  DROP conflicts where S7 sorts and reports 37.

### v0.46.1 (2026-08-09)

N-013's headline was wrong. This corrects it, and records why.

- **Retracted: "precision does not move, this is a task limit".** Re-run across
  three capability tiers under identical conditions, precision moves 13% -> 42%
  -> 60% and recall collapses 97% -> 33% -> 10%. The corrected finding is
  **capability buys precision and costs recall, and no judge tested is both**.

  | judge | recall | precision | FPR | false flags / 3,000 |
  |---|---|---|---|---|
  | llama-3.1-8b | 97% | 13% | 80.8% | ~2,420 |
  | qwen3-30b | 33% | 42% | 6.0% | ~180 |
  | claude-opus-4.8 | 10% | 60% | 0.8% | ~24 |

- **D-033: the flat curve was my harness, and it was D-017 again.** A 40-token
  cap truncated every model that reasons before answering; 24 of 289 Opus
  replies were cut mid-sentence and counted as "no opinion", including a correct
  DUPLICATE verdict on a known positive. D-017 is two days old, is written up in
  this repository, and names the defect in its own title. Reproduced by its
  author, in a harness built to measure something else.
- Fixed three ways: a tagged `VERDICT:` line, a parser that reads the LAST one
  so reasoning before it is fine, and a 300-token cap. A genuinely truncated
  reply still returns `None` and is reported as unparseable rather than guessed.
- The frontier configuration is now a defensible advisory (24 false flags per
  3,000 items) and stays off by default: it caught 3 of 29 judgeable positives,
  and costs ~$15 per 3,000-item benchmark.

### v0.46.0 (2026-08-09)

The first real extension, and it is a negative result.

- **`extensions/semdup`: a judge-based semantic-duplicate check, measured and
  NOT recommended.** N-012 showed the deterministic check reaches 2 of 39
  human-confirmed `multiple_correct_answers` items; the other 37 need a reader.
  So one was built and validated against the human labels before shipping.

  | framing | judge | recall | precision | FPR |
  |---|---|---|---|---|
  | "do any two mean the same?" | llama-3.1-8b | 100% | 14% | 98.4% |
  | "do any two mean the same?" | qwen3-30b | 38% | 18% | 27.6% |
  | "is any OTHER also correct?" | qwen3-30b | 95% | 18% | 69.2% |

  830 to 2,950 false flags per 3,000 items, to find ~37 real ones.
- **Precision does not move: 14%, 18%, 18%.** Changing prompt and model tier
  slides recall and FPR along one curve without improving discrimination. The
  false positives are sets like `['Unbiased and consistent', 'Biased but
  consistent', ...]`: distractors DESIGNED to be confusable, which is what makes
  an item discriminate. A judge answering reliably would be one that can sit the
  exam.
- **Kept, not shipped.** The apparatus is reusable (per-pod opt-in, verdicts
  cached by (item, judge) so re-runs are free and offline, a spend cap priced
  from recorded usage, a skip rather than a crash without a key) and every
  finding it emits states its own measured false-positive rate.
- **It is an extension because the core may not do this.** REFERENCES.md commits
  the core to being offline, deterministic, and to auditing judges rather than
  asking them. A judge-based core check would have quietly ended that for
  everyone, including people who never wanted the check.
- The extension rail had never been exercised by anything real; this is its
  first user. Total spend to find all of it out: about 3 cents.

### v0.45.1 (2026-08-09)

The external measurement, used.

- **S5 folds case and spacing when exactly ONE pair collapses.** Scoring against
  MMLU-Redux (N-012) showed the strict rule was costing a real catch: MMLU's
  predicate-logic item `['Cs ⊃ Ej', 'Sc ≡ Ej', 'sC ≡ eJ', 'Sx ≡ Jy']` is labelled
  `multiple_correct_answers` by the human annotators. Precision **14% -> 25%**,
  recall **3% -> 5%**, no new false positives on either dataset.
- **The discriminator is how many options collapse.** Where case carries the
  content, folding merges nearly everything: MMLU's Punnett items fold four
  options into one. A genuine duplicate collapses exactly one pair.
- **Three candidate rules measured and REJECTED, with their numbers in the
  code** so nobody re-derives them: naive case-folding (+1 catch, +3 false
  positives), stripping punctuation (+2, +75), substring containment (+3, +481).
- **A near-miss worth more than the fix.** S5 already carried a comment saying
  case-folding had been tried and rejected. Redux said it was free, because its
  5,700-item sample does not contain the genetics items the original decision
  was made on. Acting on the newer measurement alone would have shipped three
  false positives into a GATING check. The prior decision was right and its
  SCOPE was wrong; checking it against the repo's own MMLU copy before
  overriding it is what caught that.
- `compare.py` asserts its reproduced rules against the battery's own counts,
  and that assertion has now fired twice: once for keying S1 wrongly, once when
  S5 gained this rule and the script had not.

### v0.45.0 (2026-08-09)

The first external validation in the repository, and the defect that found.

- **N-012: the battery scored against human annotation.** MMLU-Redux 2.0 is
  5,700 MMLU items re-read and labelled by people at Edinburgh who had never
  heard of this tool; 370 (6.5%) carry a defect label. Against the one error
  type a data-at-rest check can reach, `dup-options` scores **precision 14%,
  recall 3%**. 38 of the 39 misses are SEMANTIC duplicates that no byte
  comparison finds. A mechanical data audit does not substitute for reading the
  questions, and that is the number saying by how much.
- Split the 7 flags on the question that decides whether one is a defect: 3 have
  the KEYED ANSWER duplicated (two identical correct options, by construction),
  and 4 duplicate a non-key option, which is a real defect outside Redux's
  taxonomy. S1 is reported and NOT scored, because Redux annotates whether an
  item is answerable, not whether it is unique.
- **F-018: two of those three, Redux labelled `ok`.** `international_law-03425`
  and `sociology-05313` each key an answer whose exact string is offered twice.
  Redux caught the third of that shape, so the category was in use. Two items in
  5,700, in a paper whose contribution is finding what others missed, offered as
  a receipt that mechanical and human auditing catch different things, which is
  also what N-012 says pointing the other way.
- **D-032: a valid JSONL file it refused to read, blaming the data.** Eight
  readers used `str.splitlines()`, which splits on ``, U+2028 and six other
  characters that `json.dumps(ensure_ascii=False)` does not escape and JSON
  permits inside a string. MMLU contains `` twice, so 5,702 parseable lines
  produced `invalid JSON: Unterminated string`. All eight now use
  `spec.jsonl_lines`. Found by pointing the tool at somebody else's real data;
  every dataset in this repo had been written by this tool.
- New `benchmarks/mmlu-redux/` with `fetch.py` (parquet, cached, resumable after
  the rows API rate-limited at 429) and `compare.py`, which asserts its
  reproduced rules against the battery's own counts before comparing anything.

### v0.44.0 (2026-08-09)

Adapters: the evidence contract's second foreign format.

- **New `dinostomp.adapters` package, and an Inspect AI adapter.** `dinostomp
  import` sniffs a log and dispatches: a nested harness document is not a table,
  and the flat column mapper cannot read one at all. Handles both the `.eval`
  archive and the `.json` log, verified against four real logs from
  `UKGovernmentBEIS/inspect_ai` (fetched by `benchmarks/inspect-import/fetch.py`,
  never vendored).
- **What Inspect brings that lm-eval could not**: generated text, a finish
  reason, per-model token usage, `epoch` (which is a repeat, so R20 applies) and
  REAL TOOL EVENTS, so an imported agent run reaches T1-T6, R5, R8 and R18.
- **`C`/`I` map to pass/fail. `P` and `N` do not.** Inspect distinguishes partial
  credit and no-answer from an incorrect answer; a binary verdict cannot hold
  either, so both import as `uncheckable` and stay out of the accuracy
  denominator rather than being rounded into a number nobody measured.
- **Several scorers is a refusal**, not a silent pick. D-023 in a new costume.
- **New manifest value `foreign_observed`.** A trajectory that arrives from
  another harness is never labelled `harness_observed`: this engine did not
  watch those calls. It is stronger than an agent's self-report, because the
  exporting harness is a third party to the agent, and it is still someone
  else's word. T8 prints the difference.
- **D-031: an imported trajectory could never reach the checks that read one.**
  A pod with `provider: imported` could not declare a trajectory policy, the
  linter selected trajectory runs by provider, and T8 went `n/a` on a run
  carrying four recorded browser calls. All three gated on a PROVIDER STRING
  instead of on the evidence. Third time this week a gate keyed on a name rather
  than the thing it cares about (D-028, D-030).
- **N-011: the second format cost one defect, where the first cost five.** The
  record schema, the witness gate, the drift boundary and the absent-field rule
  all held unmodified against a format shaped nothing like the first.
- New suite `tests/test_adapters.py` (26 cases; the real-log ones SKIP rather
  than silently pass when the logs have not been fetched).

### v0.43.1 (2026-08-09)

Documentation caught up with the last three releases, and doing that found a
defect in the one command whose job is informed consent.

- **D-030: `dinostomp inspect` called a mediated pod codeless.** It collected
  paths from the scorer, the judge and `python` targets only, so a pod shipping
  `agent.py` and `tools.py` printed "ships no pod-local Python. Nothing here can
  run on your machine." That is an active reassurance rather than an omission,
  and the code it hid included TOOLS, which are the most privileged code in a
  pod: they run in dinostomp's own process, and still do under
  `isolation: subprocess`. Fixed, with tools labelled `[runs in the PARENT
  process]`, and the test written against the SPEC rather than a provider list,
  because a provider list is what failed.
- **SECURITY.md**: three claims were stale. "Trajectories are self-reported" is
  now rail-specific; "it does not time out pod code" is now true of everything
  EXCEPT a mediated agent; "it does not sandbox pod code" carries the one narrow
  exception. New section on the two agent rails with the containment table, the
  child-environment guarantee under Secrets, and tools named as the thing to
  read first in a stranger's pod.
- **AUTHORING.md**: had no mention of the agent rails at all. Now documents
  both, the four things that catch people out on the mediated one, the ablation
  probe, and when to turn isolation on.
- **CONTRIBUTING.md**: two lessons added, both earned this week. A checker that
  skips the newest surface is OFF, not weak (D-028, D-030). And: name a boundary
  for what it does, not what you wish it did.

### v0.43.0 (2026-08-09)

`isolation: subprocess`. The agent runs in a child process and the tools stay
behind in the parent.

```yaml
isolation: {mode: subprocess, timeout_s: 60}
```

- **Credential isolation.** The child's environment is stripped of everything
  matching *KEY*, *TOKEN*, *SECRET*, *PASSWORD* and friends. Verified against a
  control: the same agent in-process reads `OPENROUTER_API_KEY`; sandboxed it
  gets `NO-KEY-VISIBLE`.
- **Tool isolation.** The tool code is loaded only in the parent and the pod
  directory is kept off the child's `sys.path`. The child is not even told the
  NAME of a forbidden tool.
- **Fault and hang containment.** `timeout_s` kills the child and the run stops
  cleanly with its ledger intact. An agent that calls `os._exit` takes down its
  own process, not the eval.
- **Protocol integrity.** The child rebinds `sys.stdout` to stderr before any
  pod code exists, so an agent printing a forged `{"op":"done"}` message cannot
  hijack the channel. Tested with an agent that tries.
- **Network denial: best effort.** `socket.socket` is replaced before the agent
  is imported, which stops requests, urllib and every SDK on top of them. It
  does not stop a re-exec, and **a test asserts that escape works** rather than
  claiming otherwise.
- **Filesystem confinement: NOT PROVIDED**, and said in those words.

- **D-029: v0.42.0's "policy is enforced at call time" was an overclaim.** True
  for an agent that goes through `tools.call`; in-process, `tools._registry`
  reaches the forbidden tool in one attribute access AND leaves the trajectory
  empty, so the bypass looks tidier than asking. Corrected rather than patched:
  hiding the registry in Python is theatre, and shipping "harder" as "prevented"
  is the move this project exists to object to. A second one, found and fixed
  the same hour and never shipped: the sandbox child originally put the pod
  directory on `sys.path`, which made it WEAKER than in-process.
- **N-010** tabulates every claim against an in-process control, including the
  two escapes that still work.
- Cost: about 130ms per item for process startup, so `inprocess` stays default.
- New suite `tests/test_sandbox.py`; trials 86 -> 87.

### v0.42.1 (2026-08-09)

- **D-028: the CRLF guard was blind to new files.** It listed candidates with
  `git ls-files`, which reports only TRACKED files, so a brand-new pod was
  invisible until the commit that introduced it had already happened.
  `examples/mediated/eval.yaml` shipped with CRLF; the local suite passed 413 of
  413 on the run that produced it and CI failed a minute later. Untracked files
  are checked now, and the fix was negative-tested by planting one.
- **`*.py` is now `-text`.** Pod code is hashed into manifests
  (`target_sha256`, `tool_sha256_by_name`), and under `text=auto` a Windows
  clone with autocrlf would have received CRLF agent code, hashed it
  differently, and failed to re-derive a report that verifies on Linux. Latent,
  not hit: every pod `.py` in the repo happened to be LF.

### v0.42.0 (2026-08-09)

The agent harness that has been on the roadmap since v0.11, built, and
deliberately NOT called a sandbox.

- **New rail: `provider: mediated`.** The harness holds the tools. An agent gets
  `answer(item, tools, ctx)` and reaches a tool only through the `tools` object,
  so the recorded trajectory is a log of calls that happened rather than the
  agent's account of them. A mediated agent that returns its own `trajectory`
  **stops the run** rather than having it ignored: steps the harness never saw
  are unverifiable evidence inside a record that claims to be a log.
- **Policy is enforced at call time.** `forbidden_tools` and `max_steps` are
  refused when the agent reaches for them, not audited afterwards, and the
  attempt is recorded before it is refused. A denial that left no trace would
  make a thwarted agent look like a well-behaved one.
  **CORRECTED in v0.43.0 ([D-029](FINDINGS.md#d-029)): this held only for an
  agent that ASKED.** In-process, `tools._registry` reaches the live callables
  in one attribute access and leaves no trace. Mediation buys trace integrity;
  only `isolation: subprocess` buys policy integrity.
- **New probe `--probe ablate`, and T7 `answer-grounding-causal`.** The probe
  re-runs every item with each tool RESULT replaced by a marker. T7 compares the
  arms: an answer that comes out identical did not causally depend on the
  evidence. This is what D-020 said was needed and is now **superseded by**.
- **N-009: T4 reports 0 of 18 where T7 reports 18 of 18**, on the same agent in
  the same pod. `oneshot` answers from memory and retrieves the right topic
  afterwards, so its answer always APPEARS in its evidence and never depends on
  it. Not the 6x gap D-020 estimated: a total one, on this pod.
- **T8 `trace-observed`** records and prints which rail wrote a trajectory. It
  warns only on a fleet that MIXES rails, where T1-T6 mean different things per
  model in one table. Self-report alone is a supported choice with a stated
  limit, and a warning that fires on every pod of a kind teaches people to
  ignore warnings.
- Battery 55 -> 57. Trials 83 -> 86 planted, 13 -> 14 clean, covering T7 in both
  directions, T8 on a mixed fleet, and T1 denying a call on the mediated rail.
- **NOT A SANDBOX.** The agent is ordinary in-process Python and can import
  `os`, open a socket, or monkeypatch the harness. Mediation makes the TRACE
  trustworthy, not the AGENT. `tests/test_harness.py` asserts that rather than
  leaving it in a docstring, so adding real isolation later has to break a test
  and rewrite the claim on purpose. Real isolation needs a subprocess with a
  sanitised environment and a denied network, and is the next increment.
- **D-027: the demo pod shipped with two defects and the battery caught both.**
  8 of 24 questions were duplicates (a generator loop that emitted one phrasing
  three times instead of three), and a planted policy violation gated a
  committed example. Both fixed; the violation moved to the trials, where a
  planted defect carries an expectation.
- New pod `examples/mediated`, new suite `tests/test_harness.py`.

### v0.41.0 (2026-08-09)

`run.repeats` run live for the first time. It had unit tests, two
implementations and a docstring about estimator discipline, and had never once
been executed against a target that could disagree with itself.

- **N-008: an even `run.repeats` reported p-squared instead of p.** Measured
  against a python target with a KNOWN per-item pass rate over 120 items, not
  estimated. A model whose true rate was 50% published **24% at repeats=2** and
  **30% at repeats=4**, both behind Wilson intervals that excluded the truth,
  because ties scored 0 and repeats=2 therefore reports the probability of
  passing an item twice. The headline number moved 26 points on a parameter
  whose purpose is to reduce noise, and all 54 checks were silent.
- **A tie is now `uncheckable`, not `fail`**: excluded from the accuracy
  denominator, reported on its own line, surfaced through `judgeability`. That
  is the treatment every other unreached verdict already gets here. Odd repeats
  cannot tie, so every pod already using them is unaffected and published
  evidence does not move.
- **New check R20 `repeat-ties`** (diagnostic, battery 54 -> 55), reporting how
  much of a pod is undecided, because "50% on 58 items" is only honest when the
  62 it could not call are printed beside it. Both tails have a trial: an
  even-repeats pod that must warn and an odd-repeats pod that must stay silent,
  so "warns on ties" is not the same experiment as "warns whenever repeats are
  set". Trials 82 -> 83 planted, 12 -> 13 clean.
- **D-026: the tie rule existed twice and the counts had two units.** It is now
  `psychometrics.majority()`, imported by both the summary and the fleet matrix;
  the duplicate implementations had agreed by luck rather than by parity. Fixing
  ties first produced a summary whose numerator counted items and whose
  `n_uncheckable` counted records, caught by the test rewrite before it shipped.
- The unit test covering this **asserted the bug**, with a comment reading "the
  b tie scores 0, conservative". Conservative was the wrong word: the rule
  changed the estimand rather than shading it.
- Committed summaries were recomputed from their own records (a summary is a
  pure function of them, so no model was called and nothing was re-paid). One
  judge-probe spend total moved by 4e-8 through float accumulation order, far
  under tolerance and unrelated to this change.

### v0.40.0 (2026-08-09)

The first log this engine did not write. A real lm-evaluation-harness details
file for ARC-Challenge (1172 items, 25-shot, published by the Open LLM
Leaderboard in July 2023 for a third-party 111M model) was imported and audited.
It exposed four defects at once, all of the same kind: the importer had only
ever been pointed at evidence dinostomp itself produced.

- **`output` is no longer a required record field.** A loglikelihood-ranking
  harness scores candidate continuations by log-probability and emits NO
  generated text, which is how ARC, MMLU and HellaSwag are scored on the Open
  LLM Leaderboard. The most common eval-log shape in the field was unimportable.
  Absent output now means R8, R14 and R16 skip NAMING THE FIELD. Absent is not
  empty: an import omits the key rather than writing `""`, because an empty
  string claims the model answered with nothing.
- **A contract skip could be overwritten by the check's own body, and R16 was
  doing it.** With no output anywhere, R16 reported "no model has 5+ failed
  records to inspect" across 966 failed records. The statement was false and the
  advice it implied (go get more failures) would never have helped. `skip()` now
  refuses to replace a skip that named missing evidence. The recurring defect
  class again: a check that compared the wrong thing and returned a confident
  answer about it.
- **A rival score column that disagrees is refused, not silently chosen.** The
  log carries both `acc` and `acc_norm`; only `acc` was in the candidate list,
  so the mapping took it. They disagree on 221 of 1172 items, 17.6% against
  19.7%, and the leaderboard published the other one. dinostomp would have
  imported a headline number nobody reported. The rule needs no list of known
  column names, and fires only on actual disagreement, so a log carrying a
  duplicate verdict still imports clean.
- **`imported` is a declarable provider that `run` refuses.** There was no way
  to describe a model this engine cannot call. `--dry` made that dangerous: it
  substitutes the offline provider for whatever was declared, so `run --dry`
  would have written a full set of fabricated records under a real model's name.
  Refused before the substitution, and tested on both paths.
- Error messages now name flags someone can type (`--item-id-field`, not
  `--item_id-field`).
- New pod `benchmarks/lm-eval-import` (fetched, never vendored: the items are
  CC-BY-SA and this repo vendors no dataset), new suite
  `tests/test_importing.py`. All three
  new guards were negative-tested by disabling them; the constant-column guard
  exists because the first version of the rival rule fired on `truncated`, which
  is 0 on all 1172 rows.
- **F-018**: the log is internally honest. Both reported metrics re-derive
  exactly from the raw log-probabilities in the same file, on all 1172 rows.

### v0.39.1 (2026-08-09)

The canary probe, run for the first time.

- **N-006: the probe proved it can detect memorisation, then found none.** All four models completed all three positive controls (Hamlet, the Declaration, the quick brown fox) and none completed this pod's canary. That is the strongest shape a negative result takes: the instrument demonstrated sensitivity on the same call, so "found nothing" means something. A probe whose controls fail is blind and S10 skips instead of reporting a clean bill; that path has its own trial and did not need to fire here.
- **D-018 was wider than it said.** It was recorded as "the cross-judge probe crashed the CLI". Running `--probe canary` showed its summary has no `accuracy_on_checkable` either, so pre-fix it would have raised the same KeyError: the defect was EVERY non-judge probe, not one of them. The fallback added for cross-judge is the only reason the canary run printed a line instead of a traceback. The entry has been corrected rather than left at its first, narrower reading.
- Scope stated on the finding itself: it says these four models cannot complete a string authored for this repository, which is what a canary minted after their cutoffs should do. It says nothing about whether the ITEMS were memorised, and nothing about any other model. The canary is now partly spent, which is the documented cost, and for a published pod the marginal cost is small because publishing it published the canary.

### v0.39.0 (2026-08-09)

The agent rail met a real model for the first time. Six checks that had only ever seen a scripted target, and the most important result is about one of the checks.

- **[examples/live-agent](examples/live-agent/): a retrieval agent driven by a live model**, three configurations, real tool calls, real money (about two cents). Every other target-rail pod in this repo is deterministic and offline, which made T1 to T6 cheap to demo and meant they had never been pointed at behaviour nobody scripted.
- **D-020: the grounding check undercounts by 6x, by construction, and is now scoped rather than fixed.** `live-oneshot` generates its answer BEFORE calling `retrieve` at all, so 100% of its correct answers are causally ungrounded. T4 reported **16%**: on 16 of 19 the answer it recalled from memory also appeared in the snippet it never read. T4 asks whether the answer APPEARS in the trace's tool results and cannot ask whether it CAME from them, because a trace records what was fetched and not what was used. Not fixed, because the honest fix is a counterfactual probe or the sandboxed harness on the roadmap. What changed is the claim: the finding text and METHODOLOGY now say co-occurrence rather than grounding, and name the direction, since the error is one-sided. **A T4 warning is a floor; its silence is not a clean bill.**
- **F-017: grounding the agent in its own retrieval made it 25 points WORSE.** `live-grounded` 54%, `live-oneshot` 79%, `live-greedy` 83%, same corpus and same backend. When retrieval fetches the wrong topic, the grounded prompt tells the model to say the reference lacks the answer, and it obediently does on questions it could answer from memory. Scoped: one corpus, one tool, 24 questions.
- **T6 fired on real behaviour.** `live-greedy` asks for "one more topic, different from the last" and the model names the same one anyway: 24 of 24 trajectories repeat an identical call.
- T1, T2, T3 and T5 passed on 72 real trajectories, which is the first evidence any of them work outside a fixture.

### v0.38.0 (2026-08-09)

Ran the last two probes that had never seen a real model. One produced a marginal finding, one produced a null, and the null retracted a claim in these docs.

- **[examples/presentation](examples/presentation/): a presentation-sensitivity instrument**, not a knowledge benchmark. Forty authored 4-choice items (no licence question, no contamination question), four OpenRouter models, run three ways: plain, with `--probe shuffle`, and with `--probe template` across six instruction framings. 1360 calls for about $0.02.
- **D-019, WITHDRAWN: the docs claimed a 28-point shuffle swing with no run behind it.** Going to run that probe for real turned up that there were **zero live shuffle runs on disk**. The figure came from a study predating this repository's receipts, and P9 has since been rebuilt around a McNemar noise band. An unbacked number in the docs of a tool whose whole argument is receipts is the worst possible place for one. Replaced with the measured figure: at most 2.5 points, inside the noise band on all four models.
- **F-016: "You are an expert." is worth 10 points to llama-3.2-3b**, 85% bare to 95% expert. Reported as MARGINAL because it is: the spread is 10.0 against a band of 10.0, on four items that flipped. What earns it an entry is that the only model it moved is the smallest, and it moved in the direction that flatters the persona. The other three did not move at all.
- **N-005: re-ordering the options moved nobody beyond noise, and this is a WEAK negative.** Two of the four models score 100% on these items and `dead-weight` reports 82% of items separating nobody. An instrument at the ceiling cannot show a swing, so this means "none detectable with these models on these items", not "option order does not matter". Recorded with that limitation attached rather than as a clean null.
- **Ranking stability: 0 of 6 model pairs swapped under any framing.** On this instrument, phrasing changes a score and does not change a conclusion.
- I made the D-016 mistake again while authoring the items, and caught it before publishing: every option list was written answer-first, which with `render_choices` would have made position the loudest signal in the pod. Options are shuffled per item from a seed derived from the item id, and the spec says so.

### v0.37.0 (2026-08-09)

A real eval, built with the tool, graded by a hosted judge. It cost $0.022 and found two defects in the judge rail nobody had reached.

- **[examples/hedge](examples/hedge/): does a one-sentence summary preserve its source's epistemic stance?** Twenty hedged sources (small sample, no control, modelled, unpublished) and **ten settled-fact controls**. The controls are what make it falsifiable: without them a model that hedges everything scores 100% and the eval measures verbosity. The receipts are committed, so `dinostomp verify examples/hedge/eval.yaml` re-derives every number for free; paying is only needed for NEW numbers.
- **D-017: a truncated judge was diagnosed as a judge with no opinion.** The first hosted-judge run scored 50% agreement on cases known by construction, which reads as "this judge cannot do the task". It was a 200-token cap. The prompt asks for reasoning THEN the ruling, so the one token that matters is the first thing truncation takes, and 39 of 128 gradings came back "contains no PASS/FAIL verdict". The parse now uses the provider's `finish_reason` to tell "no verdict" from "cut off before the verdict" and says which. Raising the cap took agreement from 50% to 100%, with no change to the judge or the rubric.
- **D-018: the cross-judge probe crashed the CLI on its first real run.** `KeyError: 'accuracy_on_checkable'`: the CLI special-cased the judge probe's summary and no other, so the cross-judge summary, which carries no accuracy because it is a difference of differences, reached the line that prints one. The probe had only ever been exercised by trials calling the runner directly; nobody had typed the command.
- **The battery then caught the eval.** `answer-leak` failed 8 of 30 items because the reference summary appeared verbatim in the source: the settled sources were single sentences, so "summarise in one sentence" was a copy task. An eval whose answer sits in its question measures retrieval, not the thing it claims to. Sources rewritten as multi-sentence; it now reads 0 of 30.
- **F-014: the judge is moved by stated confidence and appeals to authority**, three of six perturbations flipping verdicts, and every flip pass to fail. Not flattery into leniency: a response that sounds more confident gets marked stricter. For an eval about epistemic stance that is adjacent to what was asked.
- **F-015: four models preserve stance 87% to 97%, and the eval cannot separate them.** At n=30 the minimum detectable effect is ~36 points against a spread of 10, and KR-20 is 0.15. The honest reading is the interval, not the ordering, and the fix is more items rather than a stronger claim.

### v0.36.2 (2026-08-09)

- **A section on contributing findings**, which also repairs a link that had been dead for two releases: FINDINGS.md pointed at `CONTRIBUTING.md#break-it-please` and that section did not exist. It covers the three series, the entry template, and the five ways an entry gets sent back, each one a mistake made here first and cited to the D entry that records it: a finding nobody looked at, a finding about the loader, a statistic without a null, an unscoped claim, and treating a benchmark defect as a verdict on its authors.
- **A test for dead in-repo anchors.** Every `doc.md#heading` link across the seven docs is resolved against that file's actual headings. A dead anchor is invisible until somebody clicks it, which is the worst kind of stale; negative-tested by breaking one.
- Logo swapped from JPEG to PNG, resized 1254px to 720px (1.9 MB to 705 KB). The README renders it at 360px, so the original meant every visitor to the front page downloaded five times what they saw.

### v0.36.1 (2026-08-09)

Two false-positive classes the thirteen-benchmark sweep exposed, plus one real finding they were hiding.

- **D-015: position and length bias were reporting class balance.** BoolQ offers `["yes", "no"]` on all 3000 items, "yes" is longer than "no", and BoolQ answers yes 62% of the time, so `length-bias` announced "gold is strictly longest, +12% over expectation" while measuring the class distribution. Those checks are about how each item's DISTRACTORS were written; with one vocabulary shared by every item there are none, so they are now `n/a` with the class balance stated. `dup-options` and `target-not-offered` still run, since those are facts about an item's own option list either way. iris is affected too, and correctly.
- **D-016: the SciQ fetcher put the answer at index 0 on every item.** SciQ ships the answer and three distractors as separate columns, so order has to be reconstructed, and keeping the source column order made `position-bias` report gold overshooting position 0 by 75%. That was a finding about the loader, not about SciQ, and it cascaded into the shortcut check. The pod's spec had a comment saying the order was reconstructed, which is not the same as not publishing the artifact. Options are now shuffled per item from a seed derived from the item id: deterministic, reproducible, and position carries no information.
- **F-013, which the artifact was burying.** With position randomised, SciQ shows a real lean: on the 64 items where one option clearly shares most words with the question, that option is the gold answer 32 times against a chance expectation of 16 (z = 4.6). Scoped narrowly, because only 64 of 1000 items are decidable that way: this is a measurable lean on 6% of the dataset, not "SciQ is guessable".
- A logo, and a test asserting every image the README embeds actually exists.

### v0.36.0 (2026-08-09)

Eight more benchmarks, five new findings, and one defect in a check that had already been fixed once elsewhere.

- **Thirteen benchmarks audited**, up from five: ARC-Easy, WinoGrande, CommonsenseQA, OpenBookQA, BoolQ, MMLU-Pro, SciQ and MedMCQA join MMLU, HellaSwag, ARC-Challenge, GSM8K and TruthfulQA. All fetched from their authors, none vendored, each credited with paper and licence in REFERENCES.md.
- **Repeated options are not rare.** CommonsenseQA has 24 items with a duplicated option and **6 of those duplicate the keyed answer** (`cs-00022` offers `indestructible` twice and keys it). MedMCQA has 16, four of them the answer. SciQ has 9. Reported separately from duplicated distractors, because an item offering the right answer twice is a different problem from one offering four distinct options as five.
- **MMLU-Pro has 64 duplicate rows in its first 3000**, identical question, options and key.
- **MMLU-Pro shares 158 of 3000 items with MMLU**: 22 the same item, 136 the same question with rewritten options. Expected, since MMLU-Pro is documented as derived from MMLU, and the magnitude is still worth publishing: a model evaluated on both is not evaluated twice. The 22 identical ones are notable because MMLU-Pro's stated method expands every question to ten options and those twenty-two still carry MMLU's original four.
- **Two negative results**, recorded because the findings above make repeated options look endemic and they are not: five of nine choice datasets are clean on that axis, and six dataset pairs showed no cross-benchmark reuse at all.
- **D-014: `corpus-overlap` compared questions and ignored options**, the same defect class as D-005, in a check written three releases later. It reported ARC-Easy and ARC-Challenge as sharing an item when they share only the sentence "Which is NOT an example of a chemical change?" over different option blocks with different keys. Knowing about a bug is not the same as not writing it again.
- **The fix is not "add the options"**, because the check answers two questions that want different keys: *is this the same item* wants question and options, while *could a model have memorised this* wants the question alone, since a memorised question survives an option rewrite. Both are now computed and reported separately, which is why F-012 can say 22 and 136 rather than one misleading 158.
- `benchmarks/fetch.py` retries with backoff and is resumable: the datasets server rate-limits, and a 429 halfway through a paged download used to leave a truncated dataset on disk that looked complete.
- The FINDINGS scorecard test now checks the counts arithmetically rather than against a spelled-out word, and it immediately caught the first draft omitting iris from its own totals.

### v0.35.4 (2026-08-09)

A reference list, prompted by a label this repo had left unbacked.

- **[REFERENCES.md](REFERENCES.md).** The threshold table marks three values `convention`, defined as "a value the surrounding literature uses, defensible by citation", and for a while it cited nothing. An appeal to convention with no reference is an unfalsifiable claim, which is the thing this tool exists to object to. Every borrowed method now names its source: Wilson intervals, KR-20, point-biserial with the rest-score correction, the fixed-margins null by swap randomisation, McNemar, the paired bootstrap, and mutation testing.
- **A test fails the build if a `convention` threshold has no source.** Relabelling something `convention` without citing it is now caught, and the negative test confirms it fires. Either cite it or call it `judgment`, which 34 of 43 thresholds already are.
- The five audited benchmarks are credited with paper, arXiv id and licence, since they are other people's work fetched rather than vendored. iris carries both Fisher and the Bezdek note about the UCI lineage this repo actually pins.
- The eval-defect classes the trials are drawn from are cited too, which matters for a specific reason: the trials are NOT enumerated from the check registry, so a check and the defect proving it are supposed to come from different places. Naming those places is what makes that claim checkable.
- **A section on what is deliberately NOT borrowed**, because absence reads as oversight: no LLM judge anywhere in the battery's own verdicts, no learned model in any check, and no claim about construct validity, with Messick (1995) as the standard statement of what that argument would actually require.

### v0.35.3 (2026-08-09)

FINDINGS.md is a ledger now, not an essay, so entries can be appended without a rewrite.

- **Twenty-two entries with permanent ids**, in three series that are not averaged together: **F** for a defect in someone else's eval, **D** for a defect in dinostomp itself, **N** for a negative result worth recording. Each entry states the check that produced it, a date, a status, and a receipt someone else can re-derive.
- **Ids are permanent.** A withdrawn entry keeps its id and gains the evidence that killed it, because deleting a claim you have already published is how a findings page becomes a marketing page.
- **Four tests keep the ledger honest**, and two of them were negative-tested by breaking the file on purpose. The index must match the entries exactly, in order, because an index that drifts from its entries is a summary that does not re-derive, which is a gated finding everywhere else in this project. Ids must be unique and gapless, so a gap means an entry was deleted rather than withdrawn. Every entry must carry a metadata line. And the scorecard's counts must match the file.
- Two parity tests caught strings the rewrite had dropped (the iris verdict transcript and the battery-size line). Restored from real output rather than deleted along with the tests.
- CONTRIBUTING already asked for adversarial pods from outside; the ledger now has the shape those findings will land in, with attribution, next to the tool's own defects.

### v0.35.2 (2026-08-09)

The second half of the same bug. Git's line-ending translation is drift.

- **Every file this toolkit wrote used Python's default newline handling**, which turns `\n` into `\r\n` on Windows. The drift boundary hashes EXACT BYTES, so a pod generated on Windows and checked out anywhere else hashed differently: `input-drift` fired, and all three published artifacts failed to re-derive. The badge failing was the tell, since a badge carries only the verdict and the coverage, so a check had to be changing result across platforms.
- Every writer now passes `newline="\n"`: the ledger, manifests, summaries, STOMP.md/json, the badge, the repaired-dataset output, and the benchmark fetcher. A `.gitattributes` marks the byte-exact artifacts `-text` so git never translates them in either direction.
- **Two regression tests, because neither existing test could see this.** One generates a pod and asserts nothing it wrote contains CRLF. One asserts no committed pod artifact carries CRLF on disk. The local suite was blind to the whole class: it only ever ran on one platform's checkout.
- The lesson is the one this project keeps relearning. Dogfooding on a machine that shares none of the author's assumptions is what found both halves of this, and the CI that did it had been in the tree for two releases without ever running anywhere but here.

### v0.35.1 (2026-08-09)

The first CI run on a machine that was not the author's failed all six jobs, and it was right to.

- **Published reports embedded the ABSOLUTE path of the spec**, so every one verified only on the machine that generated it. `verify` re-derives the report and byte-compares it against the published artifact; the re-derived `target` read `C:\Users\...\eval.yaml` here and `/home/runner/...` there, so the comparison failed on all five example pods. That contradicted the central claim, printed by the command itself, that a stranger can check a published verdict offline without trusting the publisher. Reports now carry the spec's name inside the pod (`eval.yaml`); identity was always in `inputs.spec_sha256`, which is what actually pins the artifact.
- **The local suite could not have caught it**, because it always verified each pod exactly where it was generated. The new test copies every example pod to a fresh directory first, which is what a stranger has, and it fails when the absolute path is put back. Dogfooding on a runner that shares none of the author's paths is what surfaced this: the workflow that did it was added two releases ago and had never run anywhere but here.
- No behaviour change beyond the report field. All published reports regenerated.

### v0.35.0 (2026-08-09)

An external review pushed on the two places this tool could mislead someone even while working perfectly. Both boundaries are now architectural rather than rhetorical.

- **The field it can never fill.** Every report carries `measures the intended construct: NOT ESTABLISHED BY DINOSTOMP`, printed on every verdict. Fifty-four checks sounds comprehensive and the ways an eval can be invalid are unbounded: task selection, ecological validity, distribution mismatch, saturation, contamination nobody can observe. A reader who sees "54 of 54 ran" will reason "so there probably is not much wrong", and that inference is the most dangerous thing this tool could cause. A caveat in a paragraph gets skimmed; a field that permanently reads NOT ESTABLISHED does not. It is a constant, and a test walks the AST of every shipped module to assert no code path can set it to anything else.
- **`STOMPED CLEAN` became `SOUND` last release; `SOUND` is now `MECHANICALLY SOUND`, and the badge says `integrity 54/54`.** Interface semantics beat documentation: a bare "sound 54/54" gets screenshotted into a README and quietly becomes "this benchmark is good". The qualifier rides ON the verdict. The JSON verdict key stays `sound` so the API does not break.
- **Thresholds now declare their provenance**: derived, calibrated, convention, structural, or judgment, with the basis printed beside every value in the report. Thirty-four of forty-three are author judgment, which is the honest label for "it seemed about right" and is by far the largest class. A dial at 1.96 and a dial at 0.10 are not the same kind of object and should not have looked alike.
- **DinoTrials now prints its own limitation under its own score.** 82 of 82 caught means every check fires on the failure it was built for, and those failures were planted by the same hands that wrote the checks. That is internal consistency, not independent validation, and it says nothing about defects nobody here imagined. CONTRIBUTING.md now asks for the thing that would actually be evidence: pathological pods built from the schemas WITHOUT reading the check implementations, with misses published next to the tool's own defects.
- **Positioning: a verification layer for AI evaluations**, not another harness, with a pipeline diagram showing which checks sit on which boundary. And the one invariant every design choice follows, stated where it belongs: nothing becomes evidence merely because an earlier stage said it was.
- The LLM-authoring claim is reframed as **machine-authorable and mechanically verifiable**. LLMs are one producer; verifiability is the durable property and will age better.

### v0.34.0 (2026-08-09)

Two sanctioned growth surfaces, and one rule enforced in code rather than requested in a style guide.

- **THE HARD RULE: an extension may add findings, never remove or soften one.** No hook runs before the core, filters findings, or adjusts a threshold. An extension that could make a verdict greener would make every `SOUND` in the world mean "sound according to whichever plugins that person had installed", and would put the deciding code outside the engine fingerprint that is supposed to cover it. Extensions widen what the battery looks for; the core alone decides what BROKEN means.
- **Three enforcement mechanisms, in increasing bluntness.** Extensions get a WRITE-ONLY collector with no API to read, edit or delete a finding, including their own, because a plugin that can read the verdict is one step from one that shapes it. `THRESHOLDS` is fingerprinted before and after extension code runs, and a mutation ABORTS the audit rather than dropping the findings and carrying on: a report whose settings cannot be reconstructed is worse than no report. And core findings are snapshotted around the execution window and compared afterwards.
- **The third guard did not work when first written, and the test that tried to defeat it is what proved that.** It compared core findings around the MERGE loop, where no extension code runs, so it could not fire. It now wraps the window where extension code actually executes, and the sabotage test reaches for the reporter the way a hostile extension would have to.
- **Rail one, checks:** a package exposing a `dinostomp.checks` entry point. Ids are namespaced (`x:pkg:X1`) so provenance is never ambiguous and a collision with a core id is refused at load time. One bad extension is refused and named rather than killing the audit.
- **The entry fee is the one the core pays.** A check ships `TRIALS` (a planted defect it must catch) and `CLEAN_PODS` (a good eval it must stay quiet on). Ship neither and the checks still RUN and are still REPORTED, because suppressing a finding is its own kind of dishonesty, but they are labelled UNVALIDATED, excluded from coverage, and they do not vote on the verdict. A pile of unvalidated lint rules must not be able to wear this tool's verdict.
- **Rail two, adapters**, which the evidence contract already made possible: anything that writes conforming records is auditable, so other harnesses' adapters can live in other people's repos. `dinostomp import` is the reference one, not a privileged path. An adapter's entry fee is a golden-file trial.
- **The verdict names its inputs.** Every loaded extension is named, versioned and hashed in the report exactly as the engine is. Extensions are imported Python with the powers of imported Python; they are not gated behind `--trust-code` because installing a package is a deliberate act while opening a stranger's pod is not. That difference justifies loading them and does not justify hiding them.

### v0.33.1 (2026-08-09)

The README read as a dataset auditor. Fixed the frame, not the tool.

- **Several LLMs were shown the README and all concluded "dataset auditor."** They were reading it correctly: everything before "Then run something" was dataset-only, three sub-sections deep, so a skimmer never reached the other forty-four checks. The repositioning had inverted the identity so hard that the pipeline disappeared behind its own on-ramp.
- **The unifying frame is the eval LIFECYCLE, not the entry point.** The document now opens on a table of the six stages an eval can be wrong at (data, scorer, runs, number, claim, and this tool), each with a real finding, so the scope is visible in the first screen. The dataset audit is presented as the thirty-second way in, next to the five-minute way in, rather than as what the product is.
- Tagline back to the project's own voice: **"Everything in your eval gets stomped before it gets believed."** Scope-complete, and it was always the better half of the original line.
- The opening now shows a RUN transcript beside the dataset one, because three of the six stages are invisible in a dataset and invisible in an accuracy number: truncated answers credited, seed noise read as a result, an auditor that drifted.
- Every cell of the new table was verified against the source before it shipped. The scorer row (`0.000` scored for a model whose real accuracy was `0.438`, ranked last in a fleet it led) is quoted from `scorers.py`. The claim row was padded prose on the first draft ("typed claims gate on their own bar") and is now a case that was actually run: a pod claiming 80% accuracy and a 20-point win, handed evidence for one model at 75%, goes BROKEN with both claims NOT SUPPORTED.

### v0.33.0 (2026-08-09)

The evidence contract, made explicit. The battery consumes the record and manifest SCHEMAS, not this runner, and that is now enforced rather than asserted.

- **Every check declares the evidence fields it reads**, with a reason, in [`src/dinostomp/evidence.py`](src/dinostomp/evidence.py). A check whose fields are absent skips naming the FIELD: `no `finish_reason` on every record (a truncated response is identified by it); 0 of 240 record(s) carry it`. That replaces `no runs on disk yet`, which was unactionable in general and simply false when there were runs on disk and the check needed something they lacked.
- **`dinostomp evidence <spec>`** prints the contract against what you actually have, so thin coverage is never a mystery: which checks are ready, which are blocked, and on which field.
- **`dinostomp import <spec> <log>`**: another harness's log becomes conforming evidence. Deliberately UNPRIVILEGED. Records are schema-validated at the boundary, so an import either yields readable evidence or fails loudly; the pod's witness gate runs before anything lands, because the scorer being validated is the one that will re-derive these verdicts; `spec_sha256` and `data_sha256` come from your pod, so the drift boundary applies identically; and it claims no `tool_sha256`, because this engine did not produce those numbers and `engine-drift` reports that rather than pretending otherwise.
- **Nothing is invented to fill a gap.** No `finish_reason` in the log means none in the import, `truncation-credit` skips, and coverage is one check shorter. A score that cannot be read as pass/fail refuses the whole import rather than defaulting: defaulting to `fail` invents a number and defaulting to `pass` invents a flattering one.
- **What it buys, on the worked example:** pointing the pod's own scorer at a foreign harness's outputs re-derives their verdicts independently, and `verdict-rederive` passes. That is a real check on someone else's scoring for free.
- **Two rules keep the contract table honest**, both tested. A check may not declare a field the schema already requires, since a record missing one of those is schema-invalid and `record-integrity` gates on it; hiding a gating finding behind a coverage line would be strictly worse. And a check the contract disqualifies cannot be revived by a later pass computing a vacuous green result over zero rows.
- **Two bugs in the importer, found by auditing its own output.** It wrote no summary, which `summary-rederive` correctly gated on, so imported evidence was broken on arrival. And it declared `witness_report: absent`, which made every import a gated finding; the honest fix was to actually run the gate rather than to weaken the check that noticed.

### v0.32.1 (2026-08-09)

Docs review fixes. No behaviour change.

- **[AUTHORING.md](AUTHORING.md), which the doc split had dropped.** The spec format exists to be written by an LLM and corrected against machine-readable errors, and the rewrite left no trace of that: a model landing on the repo learned how to AUDIT with dinostomp and had to reverse-engineer how to AUTHOR for it. The doc is addressed to whoever is holding the keyboard, quotes the real validator transcript, and is pinned by two tests: the "smallest legal spec" it hands you must actually validate, and the broken spec it quotes must still produce the errors it shows.
- **A test that every doc the README links exists.** The authoring story vanished in one rewrite because nothing checked, which is the same class of defect as a summary that does not re-derive: a document making a claim its artifacts do not support.
- **The install / CI contradiction.** Install said "not on PyPI yet" while the CI block showed `uses: collapseindex/dinostomp@v0.32.0`, which requires a public repo that would also make `pip install git+https://...` work. The Action is written and in the tree; it is now labelled planned rather than shown as working, with a test asserting that pairing. A copy-pasteable block that fails for the first person who tries it is a credibility wound in a document whose thesis is receipts.
- The findings table quoted "swing 11 to 13 points" where FINDINGS.md says 78% to 90% and 81% to 92%. The real spreads are 12.5 and 10.8, so the table now quotes the same numbers verbatim and FINDINGS states the point figures. Readers are explicitly invited to check the receipts; the receipts have to agree.
- A who-line under the tagline, a note that the badge carries its coverage fraction, and "Five minutes" renamed to what the section actually does.

### v0.32.0 (2026-08-09)

Repositioned. The audit is the product and the runner is the paved road, not the other way round. Battery 54 checks; DinoTrials 82 defects, 12 clean pods.

- **Docs split three ways.** [README.md](README.md) is what the tool does and how to use it in five minutes, [FINDINGS.md](FINDINGS.md) is what it found (MMLU, GSM8K, TruthfulQA, and itself), [METHODOLOGY.md](METHODOLOGY.md) is the fifty-four checks, the pod format, the philosophy and the self-audit. The README went from 81k characters to about 9k. The transcript-parity tests follow the CONTENT rather than the filename, so a quoted number still has to match reality wherever it now lives; splitting docs is otherwise a fine way to launder stale numbers into a file nobody tests.
- **Every check has a slug.** `dup-questions`, `engine-drift`, `seed-stability`. Ids stay the primary key that trials and thresholds are wired to, but output, docs and future `--only`/`--skip` flags use the slug, and an LLM correcting a spec against "dup-questions: 90 duplicated" needs no table in its context. Slugs are an API: renaming one is a MAJOR change.
- **Verdicts carry a SCOPE.** A dataset audit is structurally incomplete forever, and exiting nonzero for that would teach people to pass `--allow-incomplete` by reflex, which is the exact habit the flag exists to prevent. `stomp mydata.csv` now reports at data scope (`SOUND AT DATA SCOPE`, exit 0) and prints which scope it answered for, with the run checks listed as out of scope rather than missing. Pod audits are unchanged: `incomplete` still exits nonzero there, because those checks were reachable and simply were not reached.
- **`STOMPED CLEAN` is now `SOUND`.** The badge ends up on repos nobody here controls, and "clean" reads as "this eval is good" while the claim is only that no mechanical defect was found, at full coverage, by this battery. A trivial eval can be sound. The badge carries its coverage fraction in the same breath as the verdict so it cannot outrun its evidence.
- **`dinostomp suggest-witnesses`**, which helps with the homework and refuses to do it. Generating witnesses and keeping whatever kills the mutants would fit the witnesses TO the mutants, turning W1 from an independent measure of witness adequacy into the thing they were optimised against. So proposals come from the data and from named bug classes, nothing is written to the spec, and gauntlet coverage is reported SEPARATELY for authored and suggested cases: a suite that only holds up with generated cases in it is a suite nobody thought about, and the command says so.
- **A roadmap that says what lands after publishing and why.** The sandboxed agent harness (which converts T1 to T6 from auditing the diary to auditing the behaviour) is explicitly an attachment on the target rail, deliberately post-release, because the core evaluates a bounded artifact and does not observe production. Making the record/manifest schemas the EXPLICIT evidence contract the battery consumes is listed first and pre-release, since it is cheap now and expensive once the schemas ossify.

### v0.31.0 (2026-08-09)

A front door. `dinostomp stomp mydata.csv` audits a bare dataset with no spec, no scorer, no run and no money, and `--emit-fixes` hands back the repaired file. Battery 51 -> 54 checks; DinoTrials 80 -> 82 defects, 11 -> 12 clean pods.

- **`dinostomp stomp <csv|jsonl|json>`: the zero-spec dataset audit.** Every finding this project has made in someone else's data came from checks that read items at rest, and making people write YAML to reach them taxed the one thing the tool is demonstrably good at. Field inference handles the shapes real benchmarks ship (MMLU's integer answer index, ARC's `{text, label}` choices with a letter key, HuggingFace's one-key-holds-the-list JSON, HellaSwag's `ctx`/`endings`), prints the mapping it inferred ABOVE the findings so it can be corrected, and REFUSES rather than guessing when a dataset is ambiguous: TruthfulQA ships both `Best Answer` and `Correct Answers`, and picking one silently would put every downstream finding on a coin flip. Checks that need a scorer, a run or a claim come back n/a with that reason, so a dataset audit is an honest audit of a smaller thing.
- **`--emit-fixes` writes the repaired dataset and a per-item log.** Deletions and deduplications only: nothing invents an answer or rewrites a question, so the diff is auditable line by line. Findings a mechanical fix cannot touch (an answer leaking into its question, conflicting keys) are printed with the reason and the line "The repaired file is not a clean file." On MMLU it drops 93 items and the result stomps clean.
- **Two bugs found by pointing the new front door at real files.** It silently dropped MMLU's organ-pipe item because that item's keyed answer is the string `"None"`, meaning none of the above, and absence was being tested on the stringified value. And the candidate column names were written with spaces while column names are normalised with underscores, so `correct answers` matched nothing until TruthfulQA's real header proved it. Both were in the flattering direction: a shrinking denominator is fewer chances for a check to find anything.
- **`--probe template` and P11/P12: the instruction phrasing is a free parameter nobody registered.** Six framings (bare, instructed, polite, expert, terse, stepwise) re-ask the same items with the item text byte-identical. P11 reports each model's swing against a McNemar band on the items that actually flipped; P12 reports whether the fleet ORDERING changes, counting a pair only when BOTH orderings clear their own noise band, because two models tied inside noise trading places is a coin and not a reversal. A number moving is P11; a conclusion moving is P12, and a conclusion is what a leaderboard reader consumes.
- **S11 and `--against`: contamination for data that already exists.** A canary protects what you are about to publish and does nothing for MMLU. S11 compares your items against reference datasets you HAVE, verbatim and near-verbatim, and its finding text carries its own limit: overlap is evidence about the corpora compared, and finding none is NOT evidence about training data. Two draws from one template are excluded, because "What is 47 + 12?" and "What is 31 + 58?" are 90% similar by character shingles and a check that cries wolf on GSM8K is a check people turn off.
- **A GitHub Action and a dogfooding workflow.** `action.yml` fails the job on a gated finding and posts the findings as a PR comment; `allow-incomplete` and `trust-code` both default to false, because an unattended pipeline must not accept thin coverage or import a stranger's Python because a default said so. The repo's own workflow verifies every published example report re-derives and runs both tails of the trials.
- **P3 now says how much of its number is fleet size.** With four examinees at real accuracies, 25% of items would separate nobody even with no difficulty structure at all; GSM8K reads 37%. The floor is printed beside the observation and deliberately NOT subtracted, since a real dataset has difficulty structure that pushes the true floor higher and netting it off would understate the waste.
- **A coverage gap, recorded rather than left to be noticed.** S11 has no entry in DinoTrials: the harness builds POD trials and a reference corpus is an argument to the dataset audit, not a field in a spec. It is negative-tested in `tests/test_overlap.py`, including the n/a-without-a-reference case. Wiring a dataset arm into the scorecard is the right fix and is not done.
- Threshold pinning re-measured on a single clean run after three probe processes raced on a shared `pins.txt` and produced a scorecard whose provenance could not be reconstructed: **25 of 33**. Scorecards are version-stamped now.

### v0.30.0 (2026-08-09)

Pointed at five famous benchmarks, read AND run. Three receipt-backed defects in the datasets, two findings about what running one costs you in validity, and nine defects in itself. Battery 51 checks; DinoTrials 80 defects, 11 clean pods.

- **`benchmarks/`: MMLU, HellaSwag, ARC-Challenge, GSM8K, TruthfulQA**, fetched from their authors by `python benchmarks/fetch.py` rather than vendored, with the SHA-256 of the downloaded bytes printed. `stomp` needs no key and spends nothing.
- **Three findings in the data, each with a receipt, plus an honest negative.** MMLU keys "Subtract. 2,396 - 1,709" over `['687', '687', '1,493', '1,695']`, so two of four options are the correct answer and a model that computes it picks the wrong letter half the time; two more items repeat an option the same way. 90 of MMLU's first 3000 test rows are the same item twice, identical question, options and key. One TruthfulQA item accepts a restatement of its own question. And an honest negative: S3, S4 and S9 are clean on all three choice sets, with HellaSwag's gold ending strictly longest 1% BELOW expectation, opposite to the folk claim.
- **S2 was returning BROKEN on all of GSM8K.** 27 of 1319 items flagged as answer leaks, every one of them the reference number appearing as a premise. Purely numeric targets are now exempt, and so are forced choices whose question cannot be asked without naming its answer, but only within 60 characters of the "or": splitting the question and accepting a hit anywhere would make " or something" a one-word bypass of a gating check. Negative-tested from exactly that angle.
- **S1 and S7 thought a choice item was its question.** MMLU reuses stems like "Which of the following statements is correct?" over unrelated option blocks; 22 were called duplicates and 11 contradictory, on two gating checks. Identity is now question plus options as a SET, so a permutation is still the same item and P9 keeps the question of arrangement.
- **R13 and R15 read any probe as the blind probe.** Judge, canary, crossjudge and shuffle probes all run with inputs INTACT, so a shuffle probe scoring 77% became "this eval is solvable WITHOUT the question". A fabricated blind accuracy, stated confidently, from a run that had the question. The first version of the regression test passed against the unfixed code, because a mismatched run-file stem made the probe invisible to discovery.
- **P9 and P10 called sampling noise a finding.** Both compared a move against a flat 10 points regardless of n. P10 was about to warn on a seed spread of 1.7 standard errors on the first real benchmark this tool ever saw. Both now compare against the noise band at the actual n, unpaired for P10 (each seed draws its own items) and McNemar for P9 (the shuffle probe re-runs the same ones, and P9 had been discarding that pairing), and both also require a practical floor. `seed_spread_max` and `order_swing_max` are replaced by `seed_spread_min`, `order_swing_min` and a shared `noise_z`.
- **Then the pods were RUN, and the runtime half found four more.** A four-model fleet over 120 GSM8K problems at three seeds, 1440 calls for $0.060. Two of four models move further between seeds than the item sample explains (78% to 90%, and 81% to 92%, against a 9-point band) while the model with the LARGEST raw spread is the one P10 correctly stays quiet about. Nine truncated responses were credited, five of them genuinely unfinished and credited because `extract: last` found a matching intermediate number. The 3B model loses 8 to 16 items per run to unparseable output where the others lose none, which finally exercised the uncheckable path an earlier live study had recorded as untested.
- **P2 tried to manufacture 31 key errors, and the fix needed the right null.** Flagging items that strong models miss and weak models hit produced 31 of 303 on a real fleet; a point-biserial over four examinees can take only a handful of values. Two obvious nulls are both wrong in opposite directions: redrawing from each model's accuracy destroys item difficulty (expects 65, hides five inverted keys), permuting who passed each item destroys fleet skill (expects 114, hides everything). The null holding BOTH margins fixed, sampled by flipping 2x2 checkerboards, expects 31 against an observed 31, and THAT reads better than it is: with four examinees a fixed-margins null is nearly degenerate, so inverting 15% of the GSM8K keys moves the null and the observation together and P2 still says nothing. Measured power at 200 items with 10% of keys inverted: 0/5 detections at six examinees, 2/5 at twelve, 5/5 at forty, and zero false alarms anywhere. P2 is therefore ONE-SIDED, and its pass message now says so instead of letting silence read as a clean answer key. The first fix was flattering in its own right: trading a check that manufactures findings for one that cannot see is an honesty gain and a power loss, and calling it a clean win would have been the same error one level up. The trials then caught the fix overshooting: the inverted-key fixture had planted one bad item, which at six models and 24 items is genuinely below the noise floor, so it now plants five and the finding says P2 detects a PATTERN of key errors rather than a single one.
- **R19: the runs were produced by this engine.** `tool_sha256` was written into every manifest and read by nothing, making the engine the one input inside the drift boundary that could change unnoticed. It warns rather than gates. Its first act was to catch this repository: the committed iris pod's `STOMPED CLEAN` report had been computed over runs from two different engines, and 30 of 55 committed example runs were stale that way. Deleted and regenerated.
- **`plan` understated a 3-seed pod's bill by 3x**, having never read `run.seeds`. The cap was never at risk; the forecast was.
- **A near-miss, measured before shipping.** Comparing options case-insensitively looks like the obvious follow-up to the duplicate-option finding and calls four correct MMLU items defective, because their case IS the answer (`Bb Bb` against `BB Bb`). S5 stays exact.
- W1's whitespace-mutant hint described a witness that cannot kill that mutant. Two new clean pods pin the S2 exemptions, one pins P9's noise floor, one pins shared-stem item identity.

### v0.29.0 (2026-08-08)

The last two standing limitations, plus a table of contents. Battery 50 checks; DinoTrials 72 defects, 7 clean pods.

- **Mount hashing.** A path that leaves the pod is refused UNLESS declared under `mounts`, and declaring is what makes it legal, because declaring is what gets it hashed. Every mount lands in each manifest as `mount_sha256`, so editing a workspace-shared scorer between runs is drift exactly like editing the pod's own. The README's old advice (vendor small scorers into the pod, because duplication is cheaper than spooky action at a distance) is no longer the only safe option. Mounted Python needs `--trust-code` like any other pod code; if anything it deserves more suspicion, being from outside.
- **Self-preference (J4), which needed a second judge and now has one.** The one-judge proxy is confounded by formatting, and this project refused to ship it. Declare a `cross_judge` from a different family and `--probe crossjudge` re-grades the SAME recorded outputs, so a model's formatting applies to both judges and cancels; what survives is the difference of differences. On the trial fixture the arithmetic is visible: a fair judge produces deltas of exactly `0.000` for both models, while a favouring judge moves only its own family, to `+0.29`. J4 reports a GAP and refuses to name a motive: a family gap may be favouritism, or a style one judge reads better, and the finding says both.
- **Three bugs found while building it, each one silent.** The same-family guard read `model` on judge blocks that only have an `entrypoint`, so every python cross-judge pod was refused as "same family" when the two families were simply both empty. The cross-judge probe graded against `rec["target"]`, which run records do not store, so it failed every item and produced deltas that were just pass rates in disguise. And the first fixture made both bots wrong on identical items, which P8 correctly flagged as an eval that cannot separate its fleet.
- A table of contents, grouped by what a reader is trying to do rather than by document order, with every anchor checked against a real heading.

### v0.28.0 (2026-08-08)

Boundary trials: the battery now guards its own settings, about half of them. DinoTrials 61 -> 71 defects.

- **`pin_thresholds` gave its first honest answer: 5 of 31 thresholds pinned.** The trials proved every check fires, and said almost nothing about the NUMBER each fires at, so most of the battery's sensitivity was an unvalidated opinion: `collapse_margin` could have been set to 0.9, or `position_margin` to 0.6, and all 61 trials would have stayed green.
- **Eleven boundary trials, each sized strictly between the shipped threshold and a 3x loosening**, taking it to **17 of 31**. The priority was `candidate_list_min`, the only unpinned threshold attached to a GATING check: loosening it turns real answer leaks into "that is just a candidate list" and converts BROKEN into clean, silently. Also pinned: position and length bias, uncheckable rate, response collapse, scorer-artifact detection, scorer escape (both thresholds), grounding, redundant calls, and billing ratio.
- **The probe was wrong twice before it was right, and both times it produced a confident artifact.** Its first run consumed its own `--json` flag, because the trial suite parses `sys.argv`, and wrote a well-formed scorecard containing entirely the wrong data. Its second run tested seven thresholds in the STRICT direction, where a "pinned" result only means some clean pod started false-alarming; two of the original five "pinned" results were that artifact. Loosening is not one direction: margins loosen upward, minimum-evidence bars loosen upward for the opposite reason, and several checks fire when a value falls BELOW their threshold.
- **A third fixture-sizing error, same shape as the P10 one.** The length-bias boundary trial reused `choice_items`, whose `"apple0"` is already strictly longer than `"pear0"`, `"plum0"` and `"kiwi0"`. A quarter of that fixture skews before the trial touches it, so the planted defect landed at 0.45 excess instead of 0.20 and pinned nothing. Rebuilt with equal-length options, and verified directly: warns at 0.10, passes at 0.30.
- The README publishes the count rather than the aspiration, including the fourteen thresholds still unpinned. A reader deserves to know how much of this battery guards its own settings.

### v0.27.0 (2026-08-08)

Who checks the checker? Two hardenings aimed at the extender rather than the eval.

- **The judge's fence is derived from the response it wraps.** The candidate response sits between two `<<<hash>>>` markers computed as `sha256(seed | rubric | response)`. That makes the delimiter unNAMEABLE rather than merely secret: to close the fence early and issue its own instructions, a response would have to contain a hash of itself, and writing the marker into the text changes the marker. Derived rather than random so the prompt stays reproducible. Stated in the code, SECURITY.md and the README as raising the COST of injection, never as a defence, because a derived fence is not a security boundary.
- **`trials/pin_thresholds.py`: which thresholds could be quietly loosened?** DinoTrials answers "does this defect get caught", not "does it get caught AT THIS SETTING", and the gap is the attack surface of an audited battery: loosening one number is a one-line change that keeps the whole suite green. The probe loosens each threshold in the permissive direction, re-runs every trial, and reports the ones nothing notices. Each is a request for a boundary trial, not an accusation. Writing it forced a distinction that would otherwise have made the probe test nothing: some thresholds loosen UPWARD (margins) and some DOWNWARD (minimum-evidence bars), and structural constants are excluded because moving them changes what an eval IS rather than how loudly a check complains.
- **The probe found a bug in itself on its first real run.** It called `run_trials.main()`, which parses `sys.argv`, so the suite consumed the probe's own `--json` flag and each of ~30 iterations overwrote the scorecard with trial output. The artifact that appeared was well-formed JSON containing entirely the wrong data, which is the same failure shape this project keeps finding: a broken instrument that still produces a plausible-looking result. `sys.argv` is isolated now, with a regression test.
- New README section, "Who checks the checker?", and a matching SECURITY.md entry: dinostomp does not stop someone extending it from weakening it. What it does is make tampering visible in the artifact a reader already has, through the two-tailed trials, the coverage line and the fingerprint.

### v0.26.0 (2026-08-08)

Fixing what the security round could only document. Battery 49 checks; DinoTrials 61 defects.

- **`--trust-code` asked for blind consent; now it can be informed.** `dinostomp inspect <spec>` parses a pod's Python STATICALLY, without importing it, and reports what it reaches for: runs other programs, talks to the network, writes files, evaluates strings, and how many statements execute at IMPORT time (which is the sharp end, since that is before any check sees anything). Deliberately not overclaimed anywhere it appears: it is not a sandbox and not a malware detector, a determined author can hide any of it, and a clean report is not a certificate. Building it caught two of its own defects: it flagged `json.loads` as a code-execution risk (a report that cries wolf teaches readers to ignore reports) and named callers `?` instead of resolving `urllib.request.urlopen`.
- **New check R18: billed output tokens match the recorded text.** You are charged on the provider's token count and you hold the text, which makes this the one cross-check available without trusting them. First draft false-alarmed on two real models at 3.5x and 4.5x, because a `chars/4` estimate has enormous relative error on a two-character answer: `"56"` is one token by the estimate and three or four in practice. It now judges only records with at least 40 characters of output, and is `n/a` rather than `skip` on short-answer evals, since a bare-number eval can never produce output long enough to bill-check. That is the shape of the eval, not a gap the author could close. Hidden-reasoning models legitimately exceed the ratio, which is why it warns and says so in the finding.
- SECURITY.md's "what this tool does not do" is shorter by two entries and honest about the rest, including a new admission it did not previously make: dinostomp does not time out pod code, so a scorer with an infinite loop will hang a paid run, and killing it safely needs a subprocess this tool does not spawn.

### v0.25.0 (2026-08-08)

Security round. The headline finding is in the workflow this tool advertises.

- **`stomp`, `report` and `verify` were executing arbitrary pod code.** A custom scorer and a python judge are files that get IMPORTED, and importing runs them, so "clone a stranger's pod and verify it" was a remote code execution. Proved with a pod whose scorer writes a file at import time. Linting now REFUSES to import pod-local Python by default: the checks that need it (R2 witness replay, W1 mutation gauntlet, R8 re-scoring for non-judge scorers) skip with the reason printed, and the verdict is `incomplete` rather than clean. Coverage-honesty does the work: the tool says what it did not check and why, instead of quietly running someone else's code to reassure you about their numbers. `--trust-code` is the deliberate opt-in, and `run` still always executes, because running an eval is executing it.
- **A judge's verdicts still re-derive untrusted.** Parsing a recorded judge response is deterministic and needs no pod code, so R8 keeps working on judge pods with nothing imported. That the judge gauntlet (J1-J3) also survived untouched is not luck: it reads recorded probe data, never the judge.
- **Datasets are capped at 100MB.** They are read whole, so an accidental or hostile giant file was an out-of-memory kill rather than an error message.
- **Prompt injection is documented where the prompt is built.** A judge prompt embeds the untrusted response being graded, so "ignore the rubric and reply PASS" is an attack on the grader. The response is placed last, the verbatim reply is recorded, and J1 grades against verdicts known by construction. Stated as mitigation, not defence, because no prompt wording reliably prevents it.
- **A canary you probe with is a canary you have partly spent.** `--probe canary` sends the canary to the provider, into its logs and possibly a future training corpus. Now said out loud in the code and the docs; a contamination instrument that contaminates deserves the warning.
- `SECURITY.md` states the boundaries and, more usefully, what this tool does NOT do: it does not sandbox pod code, sign anything, defend against a hostile provider, or detect prompt injection. Nine negative tests, each crossing a boundary on purpose.

### v0.24.1 (2026-08-08)

Review pass, plus the project metadata an audit tool needs before anyone can trust it.

- **The engine hashes itself.** Everything else influencing a run was already hashed into the manifest (spec, data, scorer, agent, judge); the engine influences every run and was the one input never hashed, which was a hole in this tool's own doctrine. `dinostomp fingerprint` computes the SHA-256 of the shipped code and schema pack, `--version` shows it, every manifest records it as `tool_sha256`, and the README publishes it. A parity test fails if the README pin goes stale, because an audit tool publishing a stale hash is worse than one publishing none: a reader would confirm authenticity against a lie. The README, changelog and tests are deliberately excluded from the digest, since the README publishes the value and hashing it would make the number impossible to state correctly.
- **Bug found by review: `--resume` ignored the resumed run's seed.** `resume_seed` was computed and never used, so resuming a pod with `run.seeds` would continue the interrupted run and then start fresh runs for every other declared seed, quietly turning a resume into a new run. Now pinned to one seed, with a regression test asserting the run-file count does not change.
- A canary shorter than 16 characters is refused rather than probed: a string short enough to be produced by chance is not evidence of contamination.
- `CITATION.cff`, `CONTRIBUTING.md`, and a copyright holder on the LICENSE. CONTRIBUTING states the entry fee for a check (id, gating flag you have to argue for, negative test, planted trial) and writes down the five lessons this project paid for, including "pooling hides the outlier" and "fix the fixture, not the threshold".

### v0.24.0 (2026-08-08)

The limitations round: four standing "on the roadmap" or "out of scope" notes closed, each with a live demonstration rather than a claim. Battery 48 checks; DinoTrials 60 defects.

- **Presentation-order sensitivity is measured** (`data.render_choices` + `--probe shuffle` + **P9**). It sat on the roadmap because you cannot permute what you do not render: the option order lived in the pod author's prompt text, where the tool had no access to it. Handing dinostomp the option block fixes that. Building it surfaced a design trap worth recording: shuffling moves the gold answer to a different LETTER, so a letter-keyed target would have to be rewritten per rendering, the scorer would grade against something the item does not contain, and R8 could no longer re-score offline. Keying on the option TEXT keeps the target invariant under permutation. Live result: two of five models moved more than 10% on identical items, one by 28 points.
- **Canary regurgitation is detectable** (`--probe canary` + **S10**), and the design constraint mattered more than the feature. A fresh canary is a random string no model has seen, so a probe against it returns clean whether the model is contaminated OR the probe simply does not work: an unfalsifiable green. Every probe therefore carries a POSITIVE CONTROL, a passage certainly in training data, and a model that cannot reproduce the control has S10 SKIP on it rather than collecting a clean bill of health. Live: 15 of 15 controls reproduced across five models, and none reproduced the pod's canary, which is what makes those five verdicts mean something.
- **Seed lists** (`run.seeds` + **P10**). Each declared seed repeats the whole eval, so item selection and provider sampling move together, and P10 reports the spread per model. This is a different quantity from the Wilson interval: the interval covers sampling error on a FIXED item set, while this covers the choice of item set and the model's own variability. The trial demonstrates a 29-point swing from nothing but the seed.
- **CSV can express multi-target items and choices** (`data.separator`). A flat cell holds one string, which is why a pod with `"46|46.0"` in its answer column scored all 64 records `uncheckable`. Cells without the separator stay plain strings, so declaring one never reshapes single-valued data.
- Writing the P10 trial took three corrected attempts, all recorded in its docstring: `dry-strong`'s skill sits ABOVE the hardest item the dry provider can generate, so no pool containing it can be bimodal; a 10-item run is correctly refused by P10 as too noisy to compare; and the pool has to be large relative to n before subset composition moves at all. The check was right each time and the fixture was wrong, which is the useful direction for that to go.

### v0.23.0 (2026-08-08)

Stress round three: five paths a real model had never touched. Battery 45 checks; DinoTrials 56 defects. Two cents of spend, and a gating check finally proved.

- **R5 fired for the first time on real data.** "Truncated outputs are never credited" has gated since v0.3.0 and had never once caught anything real, because triggering it needs a response that is BOTH cut off and still scoreable, which normally cannot happen: truncate a model and you usually lose the answer. A pod that asks for the number FIRST and then a long explanation, at `max_tokens: 12`, produces exactly that shape. 32 of 32 responses truncated, one per model truncated AND scored pass, and R5 gated. A gating check is decorative until something real trips it.
- **A hosted judge was sampling hot, which made the witness gate a coin flip.** `JudgeScorer` called its provider with empty params, so a judge graded at whatever temperature the provider defaults to. The same 3B judge with the same witnesses was GATED on one run and passed on the next. Judges now sample at temperature 0 unless the spec says otherwise, and the judge block takes `params`. Grading is not a creative task, and J3 exists precisely because a judge that contradicts itself is not measuring anything.
- **New check R17 (gating): every model produced something scoreable.** A CSV pod whose multi-target column loaded as the literal string `"46|46.0"` scored every one of its 64 records `uncheckable`. Accuracy was `None`, and the battery reported INCOMPLETE with **no failures**. An eval that measured nothing is not a clean eval with thin coverage; zero scoreable records is a deterministic fact, so it gates. R6 still owns the graded question of how high a nonzero uncheckable rate is.
- Confirmed working on real partial traces rather than fixtures: **T2 caught the toolless agent** (32 of 96 trajectories skipped a required tool), and the item-majority estimator engaged correctly under `repeats: 5` at temperature 1.
- Standing limitation this round documents rather than fixes: **CSV cannot express a multi-target item or choices**, because a cell holds one string and there is no separator convention. R17 now catches the resulting dataset, but the format limit is real; use JSONL for anything but a single scalar target.

### v0.22.0 (2026-08-08)

Stress round two: four eval SHAPES against real models (free-form numeric, lettered multiple choice, tool-using agents, a hosted judge). Four more gaps, three of them found before a single call was paid for. Battery 44 checks; DinoTrials 55 defects.

- **A hosted judge made `stomp` and `verify` demand an API key**, and made `plan` die with a traceback. `JudgeScorer` built its provider in `__init__`, and every offline command constructs a scorer. That silently broke the promise that a stranger can verify a published pod offline, using the publisher's key. The provider is now built lazily, on the first call that actually grades. `plan` also refuses to run the mutation gauntlet against a hosted judge rather than paying it during a preview.
- **A hosted judge could not be priced.** `price_in`/`price_out` were added to models in v0.20.0 but not to the `judge` block, so any judge outside the four-model built-in table refused to run with no way to fix it. The refusal was right; the missing escape hatch was the bug.
- **`plan` printed `$0.0000` for agents that pay for their own inference.** Target-reported spend is not forecastable, and understating a bill is the one thing that command must never do. It now names the self-funded targets, and separately warns that a judge is charged against the same cap.
- **P4 gated on the wrong thing, and fired on two of three real pods.** It compared the sets of items each model was SCORED on, so a model whose answers came back `uncheckable` looked like a model that had skipped items. That contradicts the uncheckable doctrine outright: an unparseable answer is a scoring outcome, already excluded from denominators and already surfaced by R6 and R12. P4 now compares what each model was ASKED, and is renamed to say so.
- **New check R16: failed answers do not contain the reference.** A first-number numeric extractor met a model that shows its working (`12*3=36 / 8*5=40 / 36+40=76`, target 76) and marked every correct answer wrong. The battery reported "four of five models are at chance" and never said why. R16 flags a model whose FAILED answers contain the reference answer as a whole value, which separates a scorer artifact from real incapacity: in that pod two models both reported 0.000 accuracy, one because it was wrong and one because it was mis-extracted. Denied mentions do not count ("not 46" is correctly failed), and matching is on whole values, since substring matching would flag 46 inside 460.

- **`numeric` scorers take `params: {extract: first|last}`.** The default stays `first` (the conservative reading of "reply with the number"), because silently switching it would be its own flattering fix. R16 tells you when you need `last`; the evidence string now names which number it took (`extracted 76 (last of 5)`).
- The mis-extraction was confirmed by three independent instruments before anything was changed: R16's textual detection said 44%, offline last-number re-scoring of the identical outputs said 43.8%, and a hosted judge reading the same outputs said 46.9%. The original scorer said 0.000, which put the pod's strongest model in last place.

### v0.21.0 (2026-08-08)

What the first live fleet found. Six open-weight models (1B to 14B) on 120 real items, $0.005 of real spend, and three defects in the shipped battery that no amount of offline testing had surfaced. Battery 43 checks; DinoTrials 54 defects.

- **R3 broke on real money.** Per-record costs rounded to six decimals; small models bill fractions of a microdollar per call, and 120 of those rounding errors accumulated ~3e-5 of drift between the manifest total and the sum of its own records, which is 30x R3's tolerance. Every dry pod had passed because every dry cost was exactly `0.00`: **the money invariant had only ever been exercised at zero.** Ledger precision is now 9 decimals, with a regression test that fails at 6.
- **R7 was pooling, and pooling hid a model that never read the question.** `meta-llama/llama-3.2-1b-instruct` answered `evaluate` to all 120 items. On a balanced 60/60 key that is exactly 50%, indistinguishable from chance-level performance. Pooled across the fleet, accuracy was 71% and R7 passed. R7 now judges PER MODEL, the same fix R13 took in v0.17.0 and the reason T4/T6 were built per-model. That makes four appearances of this defect class; treat any new fleet-level statistic as guilty until checked.
- **New check R14: no model collapses onto one answer.** A constant answerer is not performing at chance, it is not performing at all, and on a balanced key the two are numerically identical. Compared against the dataset's own modal target share, so a legitimately skewed key does not trip it. It flags three of the six live models, including two that answer one label 86% of the time.
- **New check R15: each model beats its own blind baseline.** R13 asks whether the EVAL is answerable without its questions; R15 asks whether each MODEL used them. Two live models scored no better informed than blind (`llama-3.2-1b` at +0.0, `llama-3.2-3b` at +0.09), meaning their numbers are not evidence about this task however respectable they look against the chance floor.
- **A collapsed model corrupts the psychometrics, and that nearly produced a false research finding.** P2 flagged 8 items in a real dataset as "candidate key errors". Excluding the single constant-answering model dropped it to 1: a constant answerer scores full marks on every item keyed to its constant answer regardless of difficulty, dragging those items' point-biserials negative. P1/P2/P3 now exclude near-constant models (>= 95% one answer) and say so in the finding. Two bars on purpose: R14 REPORTS at the 0.30 margin because 86% label bias is worth knowing, while the psychometrics only EXCLUDE at near-constant, since a biased model still discriminates a little and throwing it out would cost more fleet than it buys.
- Four new trials cover R14, R7-per-model, R15, and the exclusion (`54 of 54` sensitivity, `6 of 6` specificity).
- Honest negative result from the same run: the uncheckable path stayed untested. Judgeability was 1.000 for every model and not one of 720 responses was unparseable, because a forced binary choice at temperature 0 produces bare one-word answers even from a 1B model. The "real models are messy" gap this study was meant to close remains open, and closing it needs a free-form task.
- Field note: making the agent example score abstention as `uncheckable` was tried and reverted. It pinned every configuration at 1.000, because in a retrieval eval the index coverage IS the capability, and excluding the declines removes the only thing that separated the fleet. The example now runs `STOMPED OK` with R14 correctly noting that `agent-narrow` says "unknown" to two thirds of the set.

### v0.20.0 (2026-08-08)

Spec-declared pricing, found by needing it: the first live fleet had six models at six different rates, and `--price-in/--price-out` is a single global pair.

- **`price_in` / `price_out` per model in the spec** (USD per MTok). Precedence is spec > flags > built-in table, and the spec wins because it is the only one inside `spec_sha256`: a rate typed at a shell prompt vanishes when the command scrolls away, while a rate in the spec is published with the pod, re-derived by anyone who verifies it, and repriced-after-the-fact is drift that R1 catches. Declaring one without the other is rejected at load time.
- **`rate_label` now records the price's provenance**, not just its value. `price_call` used to stamp every supplied rate `explicit`, collapsing "hashed in the spec" and "typed once at a prompt" into the same word in the one place it is permanently recorded. Records now say `spec`, `explicit`, a table entry, or `target-reported`.
- **W1 gained two more behavioural equivalence probes.** `prefix-lenient` and `substring-lenient` only ever upgrade a FAIL, so against a scorer that answers `uncheckable` on those shapes they cannot fire and no witness could kill them. They now probe the mutant's actual trigger instead of merely whether the scorer notices the transform, ending a false-alarm class that would have demanded impossible witnesses.
- Field note worth keeping, from writing the first live scorer: W1 reported `negation-blind` as EQUIVALENT rather than as a survivor, because that scorer credited "this is not a recognize case" as a hit, so stripping the negator changed nothing. **A mutant goes quiet exactly when the scorer has its bug universally.** Read `n/a` as "cannot be tested here", never as "safe".

### v0.19.0 (2026-08-08)

The judge gauntlet: who evaluated your evaluator? Battery 38 -> 41 checks; DinoTrials 42 -> 51 defects and 5 -> 6 clean pods.

- **`scorer.kind: judge`** grades with a model (hosted, `dry`, or a pod-local `judge(output, target, ctx) -> str`). It passes the witness gate like every other scorer, and its entrypoint is hashed into every manifest as `judge_sha256`, so editing a judge after a run is drift.
- **`dinostomp run <spec> --probe judge`** makes the judge earn it. Cases are built whose correct verdict is known BY CONSTRUCTION (an output that IS the reference must pass; an output that is a different item's reference must fail), which is what removes the infinite regress of judging a judge. Each case is then regraded under six perturbations that change no meaning: verbosity padding, stated confidence, appeal to authority, markdown fencing, whitespace, politeness.
- **J1** scores agreement with the construction-known verdicts and reports false passes separately. **J2** names every perturbation that flips a verdict and flags `fail -> pass` flips as INFLATING, because that is the direction that manufactures accuracy. **J3** regrades on byte-identical input: a judge that contradicts itself is not measuring a property of the response.
- **A judge is not free.** Judge calls are priced against the same rate table, counted against the same `budget_usd` cap, and itemised per record as `judge_cost_usd`; the manifest records `judge_calls`. An unpriced judge model refuses to run, since a grader that cannot be capped is not free, only unmeasured.
- **A judge is nondeterministic and paid; `stomp` is neither.** Scoring splits into the model call and the deterministic parse. Records keep the judge's VERBATIM response and R8 re-derives every verdict from it offline, so R8 stays gating and the battery stays network-free. Forging a verdict against the judge's own words gates; stripping the response gates too, because a verdict with no recorded basis cannot be checked. What cannot be re-derived (would the judge rule the same way again?) is named as a reproducibility limit. A hosted judge makes R2 and W1 skip with a stated reason rather than quietly spend money during a lint.
- **W1 gained behavioural equivalent-mutant detection.** It was demanding a case-sensitivity witness from a judge that is case-insensitive by design, a witness that cannot exist. The case-blind and prefix-lenient mutants now probe whether the scorer distinguishes the transform at all, matching what negation-blind already did.
- **Not shipped, deliberately: self-preference detection.** Whether a judge favours its own family needs a second judge or human labels; the available proxy (leniency vs strict matching, per model) is confounded by formatting, since a model that wraps its answers fails strict matching even when correct. An unsound check is worse than none.
- Trajectory checks are now n/a when no python target reported a trace AND no trajectory policy is declared, instead of vacuously passing on empty traces. A judge probe's summary reports agreement rather than accuracy, since half its cases are supposed to fail and printing an accuracy would publish a meaningless number that looks like a result.
- Two trial expectations were corrected by running them: a judge that credits everything never reaches J1 (its own witnesses stop it at the gate), and a judge that flips on its witnesses is gated too, so J3's trial had to build a judge that behaves during the interview and wobbles on the job.
- New example: `examples/judge` runs four bots that know identical facts and differ only in house style, so exact match would rank them by punctuation. CLEAN at 28 of 28 ran, 13 n/a of 41.

### v0.18.0 (2026-08-08)

The agent rail. Battery 32 -> 38 checks; DinoTrials 33 -> 42 defects and 4 -> 5 clean pods.

- **Target rail**: `provider: python` with `entrypoint: agent.py:run` mounts any pod-local callable as an examinee. The target receives `(item, ctx)` (ctx carries model, seed, params, so one file serves a fleet) and returns `{output, trajectory}`. It mounts on the EXISTING provider interface, so agents inherit the witness gate, the budget cap, the streamed ledger, resume, blind probes, and the whole battery without a new concept. Deliberately not a tracing platform: dinostomp evaluates a bounded execution artifact, it does not observe production.
- **The agent is inside the drift boundary**: `target_sha256` is hashed per model into every manifest (two agents in one fleet are two different inputs), R1 gates on it, and `--resume` refuses a run whose agent changed.
- **Six trajectory checks** over the reported trace. Gating: T1 forbidden tool called, T2 required tool never called, T3 malformed trace (nameless steps, past `max_steps`). Advisory: T4 passing answers absent from the target's own tool results (the Clever Hans of tool use, judge-free), T5 fleet-relative trajectory under-reporting, T6 redundant identical call loops. T4 and T6 judge per model rather than pooling, so one bad agent cannot hide inside an honest fleet, the same fix R13 got in v0.17.0.
- **Trust boundary stated, not papered over**: trajectories are SELF-REPORTED, so T1-T6 verify the record, not the execution. The adapter deliberately does NOT repair malformed steps (a nameless step is recorded nameless, or T3 could never fire). T5 is the only instrument aimed at omission and works by fleet comparison rather than inspection. Said in `targets.py`, the schemas, the README, and CROSSTOOL.
- **Money keeps its rules on the new rail**: a target that spends inside itself reports `cost_usd`; the ledger records it, labels the manifest `spend_source: target_reported` rather than implying it was metered, and enforces the cap against it. A post-call cap breach now stops any run cleanly (the pre-call estimate is a forecast, actual spend is the fact), with the paid item banked first.
- Spec-level refusals: entrypoint traversal outside the pod, a tool both required and forbidden (unsatisfiable policy), and a trajectory policy with no target to produce a trace.
- New example: `examples/agent` runs four configurations of one retrieval agent over 26 items, offline and free, and is the highest-coverage pod in the repo (32 of 32 ran, 6 n/a of 38). Its `agent-lazy` configuration scores 100%, satisfies every tool policy, and is still caught by T4 answering two items from memory.
- CROSSTOOL gains an F14 agent-trajectory row and a `?` ladder symbol: the incumbents' agent-eval surfaces were NOT re-audited in this pass, and scoring them from memory would be the fabricated-evidence failure this project exists to catch.

### v0.17.0 (2026-08-08)

Freeze-review round before the preprint: three parallel reviews (code smells, doc/artifact consistency, statistical confounds). Every finding fixed or disclosed.

- Flattering-direction methodology fixes: informed-guesser floor now maxes over distinct target values (multi-target items stop splitting the floor, R7/R13 no longer too easy); R13 evaluates blind solvability per model instead of pooling (one solver in a fleet cannot hide under the average); the report MDE uses the run's n (not the full dataset) and is labelled unpaired worst-case, since the paired bootstrap behind P6/C1 resolves smaller gaps; S9's analytic null sums only over items the feature can decide (a tied argmax no longer deflates z).
- Anti-gaming: P6 and C1 bootstraps are seeded from a content hash of the matrix plus the run seed, so a borderline result cannot be seed-shopped. C1 states its confirmation-on-the-generating-sample scope and prints a no-multiplicity-correction note when more than one claim is declared; the "pre-registration" language is qualified (drift detection forces a re-run, which is provenance hygiene, not statistical pre-registration).
- Consistency: schemas declare every emitted field (`status` load-bearing for C1, `claims`, `runs[].model_reported`, `runs[].uncheckable`); CLI exit codes documented per command; CROSSTOOL footnotes name the backing checks for every dinostomp cell and correct P6 (advisory, not gating); trials docstring and CHANGELOG duplicate heading fixed. Example pods now commit their run data so `dinostomp verify` re-derives them on a fresh clone.
- Code hygiene: single-source constants (`BOOTSTRAP_TRIALS`, `MIN_EVIDENCE`, `DEFAULT_MAX_TOKENS`, `Z_ALPHA`) end three parity-law violations; dead `APPLICABILITY` map and eight unused loggers removed; `resolve_rates` made public; stale stop-reason docstrings updated.

### v0.16.0 (2026-08-08)

Preprint wave 3: executable claims. Battery 31 -> 32 checks.

- Typed `claims` in the spec: `accuracy` (a declared minimum the confidence interval's LOWER bound must clear; a point estimate above the bar with an interval straddling it does not entitle) and `superiority` (min_effect under a 400-resample seeded paired bootstrap at the declared confidence). Prose entitled_claims remain as the human-interpreted form.
- C1 gates on typed claims, with the constitutional rationale recorded: the spec chose its own evidentiary bar by declaring the claim, and a self-chosen, pre-registered bar failing has no legitimate explanation, unlike advisory diagnostics whose thresholds are ours.
- Reports render each claim's requirement checklist; the CLI prints SUPPORTED / NOT SUPPORTED per claim; `dinostomp plan` states whether a superiority claim is provable at the declared n before any money moves.
- Authoring nonsense dies at load time with machine-readable issues: claims naming models the spec does not run, and a model beating itself.
- The fleet example ships two supported typed claims; DinoTrials adds the unsupportable-claim defect: sensitivity 33 of 33, specificity 4 of 4.

### v0.15.0 (2026-08-08)

Preprint wave 2: the Clever Hans instruments. Battery 29 -> 31 checks.

- S9 surface-feature shortcut sniffing, offline and free: predict the gold option per item from surface features alone (question-overlap, option length) and compare against the analytic per-item 1/k null (binomial z >= 3 plus a 10-point absolute lift, the calibration that keeps this from being a false-positive machine). A feature that finds gold without a model means the dataset is guessable without reading it: the hypothesis-only finding as a default check.
- Blind probes: `dinostomp run --probe blind` strips every input before the call (options survive, the question does not), tags the run in its manifest and filename so it can never pool with real results, and R13 compares blind accuracy against the informed-guesser floor. Dry pods are n/a (the dry provider reads the key, so blind-probing it is circular); real-provider pods without a probe get a loud unlock hint.
- Probe runs are quarantined by construction: excluded from R7, the fleet matrix, R12, and psychometrics; readable only by R13.
- DinoTrials: two new defects (gold options echoing the question; an eval solvable with the question deleted), sensitivity now 32 of 32, specificity still 4 of 4.

### v0.14.0 (2026-08-08)

Preprint wave 1: the checkable-by-construction pair.

- `dinostomp verify`: re-derives a pod's PUBLISHED report offline and byte-compares it against STOMP.md, STOMP.json, and the badge. VERIFIED means a stranger just re-derived your verdict without trusting you; MISMATCH means the pod changed after publishing or the report was edited (verify cannot tell which, and does not need to); UNVERIFIABLE means nothing was published. A published BROKEN report that re-derives is honest and exits 0: verify checks reproduction, not virtue.
- `dinostomp plan`: everything knowable before a cent is spent, from the spec alone. Minimum detectable effect at the declared n; a sample-size table when an ordering claim is entitled ("gap 10%: n = 393"); the witness mutation gauntlet run in preview (surviving mutants flagged before the run, not after); worst-case cost per model against the declared budget cap, with a stop-early warning when it does not fit.

### v0.13.0 (2026-08-08)

Reviewer-2 round three (which opened by retracting its round-two hand-editing suspicion after the ledger survived linear algebra). All findings accepted:

- The repeats interval is fixed, not footnoted: with repeats above 1, summaries switch to the item-majority estimator (strict majority per item, ties score 0, matching the fleet-matrix cells) and the Wilson interval is computed over item outcomes, so it brackets the same estimator the matrix reasons about and correlated repeats cannot narrow it. Summaries name their estimator.
- The check table is published in the README, generated from the registry (id, name, tier, applicability) and parity-tested, with the reclassification named: R7 left the choice-only class in v0.11.0 when the informed-guesser floor made it universal, which is why choice-only shrank from five checks to four.
- The First-blood caption's battery count is now parity-tested against the registry, closing the two-rounds-running stale-caption pattern.
- DinoTrials grew its specificity arm: four expected-CLEAN pods asserted to produce zero findings (currently 4 of 4, including a mixed-format pod with a bootstrap-separated ordering claim, which also answers whether 29-of-29 coverage is constructible: it is, one dataset may mix free-form and choice items under one scorer). Defect provenance stated in the runner docstring: literature-drawn plus this project's own reviews, not enumerated from the registry.

### v0.12.1 (2026-08-08)

- Windows hardening, found live: antivirus/indexer services briefly lock freshly written files, making the atomic manifest rename throw WinError 32 mid-run. The rename now retries through transient PermissionErrors (negative-tested with a flaky os.replace). A paid run must never die to a virus scanner's curiosity.

### v0.12.0 (2026-08-08)

- Uncheckable science: summaries carry `judgeability` beside conditional accuracy; the R12 diagnostic flags a model whose uncheckable rate is an outlier against the fleet median (a model escaping the scorer must never look like it improved). Battery: 29 checks.
- Provenance envelope: manifests record the environment fingerprint (python, platform, package versions) and `model_reported`, the identifier the provider actually returned. STOMP.md states the reproducibility tiers honestly: inputs hash-pinned, requests reproducible given the envelope, hosted-model immutability unknown. The runs table shows reported-as and uncheckable counts per run.
- DinoTrials v0 (`trials/run_trials.py`): thirty deliberately defective evals, each with a stated expectation, run as an executable scorecard that exits nonzero on any MISSED. Current score: 30 of 30 caught. One trial's expectation was corrected during development because the battery caught the defect EARLIER than predicted (the schema refuses a witness suite with no must-fail case before the gate ever runs). This is the seed of the cross-tool comparison; the rubric is caught-automatically-by-default-with-evidence, never feature checklists.

### v0.11.2 (2026-08-08)

- Mutation gauntlet: negation-blind is now excluded when it is behaviorally equivalent to the scorer itself (probe: does stripping a negator ever change the verdict). Found by porting reclaim's numeric scorer, which extracts the first number and therefore already ignores "not 46"; without the probe the mutant was a permanent unkillable warning, the exact equivalent-mutant failure the gauntlet promises to avoid.
- First real pods ported (in the private stomping-grounds workspace): reclaim-arith, reclaim-logic, recipient-intent. Battery findings on first contact with hand-authored research data: S3 caught genuine author position bias in reclaim-logic's option sets; W1 caught a numeric-scorer witness blind spot (prose laundering after a wrong first number).

### v0.11.1 (2026-08-08)

Reviewer-2 round two. The MAJOR finding split on inspection: the alleged four-way P6 contradiction reconciles under the implemented rule (the reviewer's premise counted five choice checks; R7 went universal in v0.11.0, so smoke and fleet's 5 n/a = four choice checks + P6, exactly as iris states). The quarter that survived was real and is fixed:

- "Highest coverage any pod can currently reach (26 of 26)" was false and is deleted: an ordering-claiming choice pod reaches 27 of 27 today, a mixed pod 28 of 28. P6's applicability rule is now stated exactly once in the README.
- The drift class behind the suspicion is closed structurally: `tests/test_readme.py` re-runs every example pod from a clean copy and asserts the README's quoted transcript lines match the battery's actual output, plus a registry-size parity check. The README now stomps itself.
- Minor findings, all accepted: Status entries reordered chronologically; v0.9.0 entry states its battery count (24); `run.repeats` documented (syntax, majority-vote cells, and the honest note that pooling correlated repeats narrows intervals optimistically); S8's contract stated (presence only, regurgitation detection out of scope); First-blood transcript captioned as a re-run under the current battery; the spec sample's witness comment softened to what W1 actually guarantees.

### v0.11.0 (2026-08-08)

Field-diff round: three research agents diffed the battery against the toolkit landscape (lm-eval, Inspect, promptfoo, HELM, cleanlab, deepchecks, MMLU-Redux, Platinum, GoldenSwag), the benchmark-defect literature (2020-2026), and benchmark-checker's full 40-check registry. Six accepted upgrades; battery 25 -> 28 checks.

- P7 saturation/floor pinning and P8 dynamic range: a fleet everyone aces (or everyone flunks), or one the eval cannot separate, now warns instead of passing everything.
- R7's guessing floor upgraded from uniform 1/k to max(uniform, informed-guesser modal-target share), and R7 now applies to free-form datasets too. A skewed answer key can no longer make chance look like skill.
- S2 learned the candidate-list rule: a question offering several answer-space values is presenting options, not leaking its key (the difference between 22 false positives and 1 true positive in benchmark-checker's history).
- P6 ordering claims now judged by a paired item bootstrap (400 seeded resamples, flip-rate threshold) instead of independent interval overlap; tighter and deterministic.
- Every report carries statistical power context: the minimum detectable effect at this item count, printed so nobody claims a 3-point win on 24 items.
- Contamination canary as a first-class convention: a `{"_canary": ...}` line in the data file (skipped by the loader, covered by the data hash), checked by S8, scaffolded with a fresh GUID by `dinostomp new`. All example pods carry canaries.
- Literature anchors recorded for launch: "Fantastic Bugs and Where to Find Them in AI Benchmarks" (arXiv 2511.16842) for fleet psychometrics; Miller 2024 / Bowyer 2025 for the uncertainty discipline; Platinum/MMLU-Redux for key-error prevalence.

### v0.10.0 (2026-08-08)

- Witness mutation gauntlet (W1, diagnostic): eight mutant scorers, each a known scoring-bug class (constant verdicts, substring credit, truncation credit, case blindness, whitespace blindness, negation blindness, uncheckable-credit), run against the spec's witness suite. A surviving mutant is a named blind spot reported with the exact witness that would close it. Equivalent mutants are excluded per dataset (case-blindness is n/a for numeric targets), so unkillable false alarms cannot occur. Battery: 24 -> 25 checks.
- Witnesses may now `expect: uncheckable`, pinning scorer behavior on unparseable output; this is the only way to kill the uncheckable-credit mutant, and the schema learned it for that reason.
- Dogfood receipts: W1's first survivors were this repo's own example pods and the `dinostomp new` template. All witness suites hardened (truncation, negation, and case witnesses added); the scaffold template now models one fail witness per bug class.
- The v0.9.0 roadmap promise ("witness-adequacy measurement") is hereby shipped, one release later.

### v0.9.0 (2026-08-08)

Second external review round ("Reviewer 2", Major Revisions). Accepted findings, in order of severity:

- Uncertainty everywhere: every accuracy carries a 95% Wilson interval (CLI line, summary, report); new P6 diagnostic checks entitled ordering claims against adjacent-interval overlap and calls rankings inside sampling noise. Example specs dropped their ordering claims (two dry models tie; the claim would not have survived P6). Battery: 23 -> 24 checks.
- STOMP.json is now byte-stable like STOMP.md: the published raw report strips volatile fields; timestamps live in run manifests. The reviewer was right that a diff-clean rendering published next to a diff-dirty raw report defeats the point.
- KR-20 prints a small-fleet caveat below 10 examinees.
- README de-overclaimed: the privacy sentence now states the provider boundary (hosted runs send items to that provider); the witness gate is documented as proving can-fail, not fails-where-it-should, with witness-adequacy measurement roadmapped; dataset-side bias checks state their boundary (presentation-order sensitivity roadmapped); First Blood now says "identical measurement vector" not "same flower", names the UCI/sklearn lineage (Bezdek et al. 1999) and the 0-indexed convention, and credits that the duplicate is known to dedup tutorials (the point is that nobody runs the check unless it is the default).
- Docs mechanics: Quick start moved above Philosophy, ran/skip/n-a glossary added, `pip install -e '.[dev]'` quoted for zsh, dry provider defined at first use, source-availability statement added (not on PyPI, no public repo yet).
- Declined for now, with reasons recorded: seed lists (ripples through resume semantics and manifests; single-seed limitation documented instead), repo URL and CI badge (gated on the publish decision, not on code).

### v0.8.0 (2026-08-07)

External-review fixes (both findings accepted):

- Strict exit codes by default: incomplete coverage now exits `4` (distinct from broken's `1`) unless `--allow-incomplete` is passed explicitly and loudly. `--require-all` is gone: CI safety is no longer a flag someone has to remember. Rationale: the tool's whole premise is that humans should not need to remember methodological hygiene.
- Constitutional split: invariants (deterministic facts, gating: duplicates, hash drift, non-re-deriving numbers) vs diagnostics (statistical signals, advisory: bias margins, KR-20, discrimination, chance-level accuracy). S3/S4 position and length bias reclassified from gating to diagnostic. The CLI prints a two-tier summary line; STOMP.md renders the tiers as separate tables with an explicit "a warning is evidence, never a proof" framing.

### v0.7.0 (2026-08-07)

- `dinostomp report`: renders the stomp report to `STOMP.md` (GitHub/HF-native markdown: verdict, entitled claims or an explicit refusal, check table, collapsible receipts, run inventory, provenance hashes), plus `stomp-badge.svg` and `STOMP.json` published next to the rendering.
- Diff-clean by design: markdown omits volatile fields; an unchanged pod re-reports to byte-identical files (tested).
- A non-green report states "None." under Entitled claims: no verdict, no claims.
- Example pods now ship their real committed reports.

### v0.6.0 (2026-08-07)

Review-driven hardening release: three adversarial review passes (correctness, fool-the-stomp, docs parity) produced ~30 unique findings; all fixed. Battery: 19 -> 23 checks.

- Result verification: R2 replays the witness gate instead of trusting the manifest's claim; R8 re-scores every recorded verdict with the current scorer (hand-edited ledgers are now a gated finding); R9 recomputes summaries from records; R10 surfaces foreign and narrowed runs; R11 re-derives the seeded selection and demands the ledger cover it; R1 additionally schema-validates manifests and cross-checks seed/model/repeats against the spec; R3 audits spend against the spec cap and the records, not the manifest's self-report; R4 counts unparseable lines and rejects records disagreeing with their manifest's identity.
- Fleet integrity: psychometrics attribute records through manifests (a sed'd model name can no longer forge a fleet); repeat ties score conservatively; foreign runs are quarantined.
- Honest reporting: coverage lines always state the full battery ("5 n/a of 23 declared"); reports carry input hashes, a timestamped run inventory with dry-run visibility, and the spec's entitled_claims (now a live field, printed under clean verdicts); all-dry stomps say so.
- Choice scorer rewritten: extraction no longer uppercases first, so "I think the answer is B" extracts B, not I (the review's worst wrong-verdict bug); stated-answer pattern, lone-letter, and bare A-H fallbacks, multi-target support.
- Graceful failure everywhere: user scorers can no longer kill a paid run (bad returns and exceptions degrade to uncheckable, and the paid output is banked before a clean stop); providers turn non-JSON 200s and malformed bodies into clean STOPPED_EARLY partials; regex optional groups are uncheckable, not crashes; a cp1252 console cannot crash the report print.
- Ledger safety: colliding model slugs (gpt_4o vs gpt-4o) get distinct run files; --resume --dry-run on a paid ledger is refused; torn final lines are truncated on resume instead of left in the file; manifests and summaries are written atomically; ids 1 and "1" are rejected as duplicates; an empty dataset is an error, never a green run.
- Spec hygiene: scorer code paths now reject absolute paths and traversal (the README claimed this; now the code does it); single-character eval names are legal.
- New test files for items loading and the CLI; negative tests for every new check and fix. 109 tests.

### v0.5.0 (2026-08-07)

- Full drift boundary: manifests now hash the data file (`data_sha256`, required) and custom scorer code (`scorer_sha256`) alongside the spec. Closes a real hole: editing `items.jsonl` or `scorer.py` after a run previously left the stomp green.
- R1 rework: drift examples name exactly which artifact changed (spec, data, scorer).
- Resume hardening: `--resume` refuses to continue a run whose spec, data, or scorer changed since the interruption, and on multi-model specs resumes only the interrupted model (fixed a latent bug where the second model reused the ledger and skipped everything the first had finished).
- `dinostomp new <dir>`: scaffolds a valid pod (eval.yaml + items.jsonl) that runs and stomps out of the box; refuses existing paths.
- README Organization doctrine: pods, stomping grounds, the two attachment tiers, and the hash-everything rule.

### v0.4.0 (2026-08-07)

- Fleet psychometrics: P1 KR-20 reliability, P2 negative discrimination (candidate key errors), P3 dead-weight share, P4 matrix completeness (gating), P5 unanimous identical wrong answers. Judge-free: models are examinees, correlations do the inference. Skips carry unlock hints ("run a fleet of 4+").
- Dry provider rework: skill (model hash) x difficulty (item hash) plus per-pair jitter, so an offline fleet has real psychometric structure; wrong answers vary per model to keep unanimity checks honest.
- New `examples/fleet`: six dry models x 24 items, STOMPED CLEAN at $0 (all applicable checks ran; choice-only checks n/a on a free-form dataset). Single-model evals now honestly report INCOMPLETE with the P-series skipped.
- New `psychometrics` module (stdlib only): kr20, point_biserials (rest-score), dead_items.

### v0.3.0 (2026-08-07)

- Stomp battery: `dinostomp stomp` lints spec, dataset, and runs. 14 checks: uniqueness, answer leakage, option-position and option-length bias, duplicate options, keyless targets, contradictory keys, spec drift (manifest SHA-256 vs spec on disk), witness-gate presence, budget honesty, record integrity, credited truncation, uncheckable rate, chance-level accuracy.
- Reporter discipline: witness counts on every check, zero-witness passes recorded as skips, n/a checks leave the coverage denominator, unreached checks surface as skips (this audit caught a declared-but-unimplemented check during development).
- Coverage-honest verdicts: clean / ok / incomplete / broken; `--require-all` for CI; `--json` machine-readable report validating against the report schema.
- Every check negative-tested: one injected defect per check, plus clean-fixture placebo tests.

### v0.2.0 (2026-08-07)

- Runner: witness gate (scorer must reproduce its witness cases or nothing runs), streamed fsynced JSONL ledger, hard USD budget checked before every call, manifest sidecar, per-run summary.
- Resume: idempotent by item key, never re-pays finished items, tolerates a torn final line from a hard kill (negative test caught real data loss: append after a torn line used to weld two records together; fixed).
- Scorers: exact, includes, regex, numeric, choice, custom python. Uncheckable is a first-class verdict, excluded from every denominator.
- Providers: dry (deterministic offline, skill from model-name hash), anthropic, openai, openrouter. Keys from env only.
- CLI: `dinostomp validate`, `dinostomp run` (`--resume`, `--limit`, `--dry-run`, `--price-in/--price-out`). Exit codes 0/1/2/3 documented.

### v0.1.0 (2026-08-07)

- Initial schema pack: JSON Schemas for eval spec, items, run record, run manifest, and check report.
- Spec loader with machine-readable issues (`load_spec`, `validate_obj`) for LLM self-correction loops.
- Witness rule enforced in-schema: scorers must declare at least one must-pass and one must-fail case.
- Cross-file checks: data path existence, absolute-path and traversal rejection.
- Negative-tested pytest suite (schema validity, witness rule, required discipline fields, path safety).
- Bundled offline example eval (`examples/smoke`).
