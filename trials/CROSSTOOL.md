# Cross-tool validity coverage: documentation-audit edition

**Status: working draft for the preprint. Method: documentation audit (2026-08-08), not
runnable verification.** Every cell cites current official docs or source trees; a cell
that says "not found" means *not found in the documentation on the audit date*, never
"the tool cannot do this." Runnable verification of key cells is the pre-submission
upgrade path. Docs lag code in every project, including this one.

## The rubric

The question is never "does the tool have feature X." For each defect family:

- **Detectable**: does any mechanism exist, even via user-written code hooks?
- **Automatic**: does detection run without the user writing detection code?
- **Default**: is it on without flags or configuration?
- **Gates**: does detection block the run, the publish, or CI by default?
- **Evidence**: is a machine-readable receipt of the finding preserved?

Compressed into a coverage ladder per cell:

- `●` automatic, on by default, gates, evidence preserved
- `◕` automatic and on by default, advisory (warns, does not gate)
- `◑` automatic but opt-in (flag, config, or manual invocation)
- `◔` achievable only through documented user-code hooks or manual audit of preserved artifacts
- `—` not found in docs
- `?` NOT AUDITED in any pass so far; the cell is an open question, not a low score

Footnote letters mark cells where the ladder alone would mislead.

## The table

Defect families condense the 51 DinoTrials defects (`run_trials.py`, drawn from the
benchmark-defect literature plus this project's adversarial reviews).

| family | lm-eval | openai/evals | Inspect | HELM | promptfoo | Braintrust | dinostomp |
|---|---|---|---|---|---|---|---|
| F1 duplicate / contradictory items | ◑ᵃ | ◕ᵇ | — | — | ◔ | ◔ | ●ᵃʲ |
| F2 answer leakage into own prompt | ◔ | ◔ | ◔ | ◔ | ◔ | — | ●ᵃᵏ |
| F3 MCQ key bias at rest | ◔ | ◔ | ◑ᶜ | — | — | — | ◕ |
| F4 shortcut / partial-input solvability | ◔ | — | — | — | — | — | ◕ᵈ |
| F5 contamination (canary / decontam) | ◑ᵉ | — | — | ◑ᶠ | — | — | ◕ᵍ |
| F6 scorer validity (is the scorer tested) | ◑ʰ | ◔ⁱ | ◑ʲ | — | ◑ᵏ | ◔ˡ | ●ᵐ |
| F7 post-hoc tampering of results | ◔ⁿ | — | ◕ᵒ | ◔ᵖ | —ᑫ | ◕ʳ | ●ˢ |
| F8 input drift after results exist | ◑ᵗ | — | ◑ᵗ | ◑ᵗ | — | ◕ᵘ | ●ᵃˡ |
| F9 run / ledger integrity | ◕ | ◕ | ●ᵛ | ◕ | ◑ | ◕ʷ | ●ᵃᵐ |
| F10 spend honesty (pre-call caps) | — | — | ◑ˣ | ◑ʸ | ◑ᶻ | ◔ᵃᵃ | ●ᵃⁿ |
| F11 statistical floors / saturation / range | — | —ᵃᵇ | — | — | — | — | ◕ |
| F12 fleet psychometrics (key-error flags) | — | — | ◔ | ◔ᵃᶜ | — | — | ◕ᵃᵈ |
| F13 claim & uncertainty discipline | ◕ᵃᵉ | — | ◕ᵃᵉ | ◑ᵃᶠ | ◑ᵃᵍ | ◑ᵃʰ | ◕/●ᵃⁱ |
| F14 agent trajectory validity | ?ᵃᵒ | ?ᵃᵒ | ?ᵃᵒ | ?ᵃᵒ | ?ᵃᵒ | ?ᵃᵒ | ●/◕ᵃᵖ |
| F15 judge validity (is the grader tested) | ?ᵃᵒ | ◔ⁱ | ?ᵃᵒ | ?ᵃᵒ | ?ᵃᵒ | ?ᵃᵒ | ◕ᵃᑫ |

**Read-down summary.** Columns 1-6 concentrate coverage in F7-F9 and F13 (run
mechanics, provenance, regression tracking). F1-F5 and F11-F12 (whether the benchmark
itself measures anything) are near-empty across the entire field: the harness camp
validates configs and logs; nothing shipped by any audited tool lints eval *content*
by default. The "gates by default" dimension is almost everywhere empty outside CI
exit codes.

## Footnotes (the honesty layer)

- ᵃ lm-eval `validate` / `--check_integrity` are config-shaped: they prove a task loads,
  renders, and matches its test suite, not that items are non-duplicated or unbiased.
- ᵇ openai/evals CI smoke-runs newly contributed registry evals against a dummy model on
  every PR: the only default-on, PR-gating check found in any audited tool. Scope is
  their registry's contributions, not user evals; catches broken configs, not content.
- ᶜ Inspect `shuffle_choices` is mitigation (re-randomize and remap), not an audit of
  key skew; opt-in.
- ᵈ dinostomp S9 (surface features vs analytic per-item null) is default+advisory; R13
  blind probes are opt-in runs (`--probe blind`) with an unlock hint when absent.
- ᵉ lm-eval decontamination: 13-gram overlap, dual raw+clean metric reporting (genuinely
  good design); per-task opt-in, requires user-supplied training n-grams, maintenance
  status uncertain (open unanswered issue #1938).
- ᶠ HELM is the only audited tool with a contamination story surfaced by default on its
  leaderboards: a curated expert registry (`contamination.yaml`) plus offline n-gram
  tooling (`data-overlap`). Expert curation, not automated detection.
- ᵍ dinostomp S8 checks canary presence only, advisory; regurgitation detection is out
  of scope and the docs say so.
- ʰ lm-eval's own metrics/tasks are unit-tested in repo CI; nothing tests a user's scorer.
- ⁱ openai/evals documents a meta-eval pattern (model-graded evals validated against
  human-labeled subsets) — a rare explicit acknowledgment that scorers need testing.
  User-built, not enforced.
- ʲ Inspect `inspect score` re-scores an existing log with an alternate scorer,
  side-by-side; manual invocation, no negative-case or mutation harness.
- ᵏ promptfoo `validate config` schema-checks assertions (Zod, exit 1): shape, not
  semantics; no grader calibration.
- ˡ Braintrust autoevals is a curated scorer library; no documented calibration loop.
- ᵐ dinostomp: witness gate blocks execution (nothing runs if the scorer contradicts its
  witnesses); W1 mutation gauntlet is default+advisory; R2 replays the gate at lint time.
- ⁿ lm-eval hashes inputs per sample (when logging); scores are unsigned: an edited
  results.json is undetectable.
- ᵒ Inspect's `ScoreEdit` trail (author, reason, full history, auto-emitted event,
  metric recomputation) is the best in-band edit audit in the field. It covers edits
  made through the API; direct file edits leave no trail, and nothing gates.
- ᵖ HELM releases full raw artifacts publicly, so third parties can diff published
  numbers against source records: strong receipts, manual verification.
- ᑫ promptfoo's web UI permits post-hoc pass/fail overrides whose persistence in exports
  is documented as a feature; no who/when audit trail found. Scored `—` because the
  documented mechanism runs in the tampering direction.
- ʳ Braintrust experiments are immutable by design: prevention rather than detection.
  Integrity model is trust-the-platform; no documented path for a third party to
  re-derive a published number offline.
- ˢ dinostomp re-derives instead of trusting: R8 re-scores every recorded verdict, R9
  recomputes summaries, R11 re-derives the seeded selection, all default and gating;
  `dinostomp verify` lets a stranger re-derive the published report offline.
- ᵗ Provenance recorded by default (git hash, config echo, run/scenario specs), but
  nothing compares it automatically: receipts exist, the diff is on you.
- ᵘ Braintrust dataset versioning is always-on with experiment pinning, and the
  comparison view surfaces input mismatches: best drift story of the incumbents;
  advisory, hosted.
- ᵛ Inspect: pydantic-typed logs where an invalid log fails to parse (an implicit gate),
  published log schema, per-sample event attribution: the best log integrity in the field.
- ʷ Braintrust records git state per experiment; `bt eval` exits nonzero on exceptions
  (not on findings).
- ˣ Inspect `cost_limit` is a real per-sample dollar cap that halts on breach; requires
  cost configuration, cooperative rather than pre-call reservation.
- ʸ HELM `--dry-run` gives an honest pre-spend token estimate; no hard mid-run cap.
- ᶻ promptfoo's `cost` assertion gates, but after the call has been paid for.
- ᵃᵃ Braintrust tracks and displays cost; no cap found.
- ᵃᵇ openai/evals has prose ceiling-awareness guidance ("an eval is bad if GPT-4 does
  well on all prompts"): human judgment, no machinery.
- ᵃᶜ HELM's public per-instance cross-model matrices make fleet psychometrics computable
  by anyone; HELM itself computes none.
- ᵃᵈ dinostomp P1-P3/P5 advisory, P4 (matrix completeness) gates.
- ᵃᵉ lm-eval ships stderr by default (bootstrap_iters=100k); Inspect ships stderr on most
  scorers including clustered SEs. Real, default uncertainty: credit where due. Neither
  has MDE, rank-stability, or machine-checked claims.
- ᵃᶠ HELM aggregates mean/stddev across trials and publishes per-instance receipts;
  no CIs by default on leaderboards.
- ᵃᵍ promptfoo `--repeat` has no statistical treatment; raw pass-rate threshold gates
  without qualification.
- ᵃʰ Braintrust trials are opt-in variance awareness; the flagship Comparison grade
  (Improvement/Regression/Tradeoff/Tie) is documented with no threshold or significance
  test: any delta colors the row.
- ᵃⁱ dinostomp: Wilson CIs and MDE default on every report (advisory); typed claims
  (C1) gate when a spec declares them; the ordering bootstrap (P6) is advisory.

- ᵃʲ dinostomp F1 rests on S1 (unique questions) and S7 (contradictory keys), both
  gating and always-on; S5/S6 (duplicate/keyless options) add gating coverage but only
  where choice items exist, so they are not counted toward the unconditional ●.
- ᵃᵏ dinostomp F2 is S2, gating where free-form items exist (n/a on a pure-choice pod);
  ● reflects default+gating on its applicable datasets.
- ᵃˡ dinostomp F8 is R1 drift detection (spec/data/scorer hashes vs manifest), gating.
- ᵃᵐ dinostomp F9 is R3/R4/R5/R8/R9/R10/R11, the run-integrity block, gating.
- ᵃⁿ dinostomp F10 is runner-side: the budget cap is checked before every call
  (`Budget.check`), and R3 re-audits ledger spend against the spec cap at lint time.
- ᵃᵒ NOT AUDITED. F14 was added with dinostomp's own agent rail in v0.18.0, after the
  2026-08-08 documentation audit that produced every other row. Several audited tools
  ship agent/trajectory evaluation surfaces, and scoring them from memory rather than
  from a fresh reading of their docs would be exactly the fabricated-evidence failure
  this project exists to catch. `?` means the question is open. Auditing this row is the
  first task of the next cross-tool pass, and it is the row most likely to move, since
  agent evaluation is the fastest-changing area in every one of these projects.
- ᵃᵖ dinostomp F14: T1/T2/T3 (forbidden tools, required tools, well-formedness and
  runaway length) gate by default; T4/T5/T6 (answer grounding in the target's own tool
  results, fleet-relative under-reporting, redundant call loops) are default+advisory.
  Scope limit stated in the tool, the schema, and the README: trajectories are
  SELF-REPORTED, so these verify the record, not the execution. T5 is the only
  instrument aimed at omission, and it works by fleet comparison rather than inspection.

- ᵃᑫ dinostomp F15: a judge scorer passes the witness gate (nothing runs if it contradicts
  its own must-fail cases), then `--probe judge` grades cases whose verdict is known by
  construction and regrades them under six meaning-preserving perturbations (J1/J2), plus
  an identity regrade for self-consistency (J3). All three are default+advisory once the
  probe exists; the probe itself is opt-in with an unlock hint, the same shape as R13.
  Judge spend is priced, capped, and itemised. Verdicts re-derive offline from the judge's
  recorded response, so forging one is caught by R8 (gating). Deliberately absent:
  self-preference detection, which needs a second judge or human labels. openai/evals is
  scored ◔ⁱ here on the strength of its documented meta-eval pattern, the one prior art in
  the audited set that acknowledges graders need validating; the rest of the row is
  unaudited for the reason in ᵃᵒ.

## Standout mechanisms per tool (credit ledger)

- **lm-eval**: default stderr; unconditional provenance echo (config, 4 seeds, git hash);
  dual raw/clean decontamination metrics.
- **openai/evals**: PR-gating smoke CI for contributed evals; documented meta-eval
  pattern for grader validation.
- **Inspect**: ScoreEdit audit trail; typed logs with published schema; gating
  per-sample cost_limit; clustered standard errors.
- **HELM**: radical artifact transparency (anyone can re-derive official numbers);
  the only surfaced contamination registry; honest pre-spend dry-run.
- **promptfoo**: the strongest CI gating substrate (schema-validated config, exit 100 on
  any failure); per-result cost/latency assertions.
- **Braintrust**: immutable experiments; always-on dataset versioning with pinning;
  per-experiment git state; trials for variance.

## The dinostomp column, audited with the same skepticism

The last column is self-scored, which is exactly the conflict of interest this project
exists to distrust. Its justification is executable rather than rhetorical: the 51
planted defects and 6 clean pods in `trials/run_trials.py` (sensitivity 51/51,
specificity 6/6 at v0.19.0), each mapped to the family rows above, re-runnable offline
by anyone with `python trials/run_trials.py`. Two honest caveats: several dinostomp
cells are `◕` advisory rather than `●` gating because the corresponding inference is
statistical and the constitutional split forbids gating on our own thresholds; the
F4/F5 instruments are young with no external adoption evidence; and F14 is one release
old with its comparison column entirely unaudited, as is F15.

## Limitations

Documentation audit only, single date (2026-08-08); docs lag code; hosted-platform
internals (Braintrust) are unverifiable from outside; absence of documentation is
evidence of absence of *discoverable defaults*, not of capability. The runnable
cross-tool verification (executing equivalents of the 33 trials against each tool where
technically possible) is future work and the honest precondition for any stronger claim
than "not found in docs."
