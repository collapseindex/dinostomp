# Contributing to dinostomp

The short version: **a check that has never been proven to fire is decoration.**
Everything below follows from that.

## Break it, please

**96 of 96 planted defects caught is not independent validation.** Those defects
were planted by the same hands that wrote the checks. A battery can become
extremely good at catching exactly the mutants designed for it, and that number
measures internal consistency: strong evidence each check fires on the failure it
was built for, and no evidence at all about failures nobody here imagined.

The credibility jump this project needs is not more checks. It is
outsiders attacking the battery and the misses being published.

**The rules of engagement**, and the second one is the important one:

1. Read [AUTHORING.md](AUTHORING.md) and the JSON Schemas in
   `src/dinostomp/schemas/`.
2. **Do not read the check implementations.** Building a pathological pod against
   `lint.py` is how you rediscover the mutants that already exist. The whole
   value of an outside attempt is that it comes from outside.
3. Construct a pod that is genuinely invalid and which `stomp` calls
   `MECHANICALLY SOUND`, or one that is genuinely fine and it calls `BROKEN`.
4. Open an issue with the pod attached, or a PR adding it to `trials/`.

A miss is worth more than a feature request, and it will be added to the trials
with attribution rather than quietly patched.

## Contributing a finding

[FINDINGS.md](FINDINGS.md) is a ledger, and it takes entries from anyone. Three
series, and they are not interchangeable:

| series | what it records | example |
|---|---|---|
| **F** | a defect in someone else's eval, dataset, or scoring | MMLU keys a subtraction item to two identical options |
| **D** | a defect in dinostomp itself | a gating check returned BROKEN on all of GSM8K |
| **N** | a negative result: a check that found nothing | no repeated options across five choice datasets |

**What an entry needs.** Take the next id in the series; ids are permanent.

```markdown
### F-014
**Dataset · one line stating the defect**
`check-slug` (ID) · YYYY-MM-DD · confirmed | scoped | WITHDRAWN

A receipt someone else can re-derive: the item id, the verbatim option list,
the key, and the command that reproduces it.

**Scope it honestly.** What the finding does NOT show.
```

Then add the row to the index table at the top, subject included, and run
`python scripts/index_findings.py` to regenerate the index, the cross-references
and `findings.json`. A test fails the build if the index and the entries
disagree, if an id is reused or a series has a gap, if the scorecard's counts
stop matching the file, or if the regenerated feed violates
[docs/findings.schema.json](docs/findings.schema.json).

**A case good enough to cite in a README is good enough to number.** The
numeric-scorer artifact lived in a source comment and one changelog line for six
releases while the README quoted it as a headline example under the sentence
"every row is a real finding with a receipt in FINDINGS.md". There was no
receipt ([D-041](FINDINGS.md#d-041)). If it is worth quoting, it gets an id; if
it is not worth an id, it does not go in the README.

**Five things that will get an entry sent back**, all of them mistakes made here
first and recorded in the D series:

- **A finding you have not looked at.** Every F entry in this file was inspected
  item by item before it was written. The first pass at GSM8K produced 27 answer
  leaks and every one was a false positive ([D-004](FINDINGS.md#d-004)).
- **A finding about the loader.** If your fetcher reconstructs option order, a
  position result is about your fetcher ([D-016](FINDINGS.md#d-016)).
- **A statistic without a null.** "31 of 303 items look wrong" is not a finding
  until you know what chance produces at that fleet size
  ([D-008](FINDINGS.md#d-008)).
- **An unscoped claim.** TruthfulQA's item is passable under a substring scorer,
  which is not TruthfulQA's own protocol, and the entry says so
  ([F-004](FINDINGS.md#f-004)).
- **A defect in a benchmark treated as a verdict on its authors.** These are the
  most-scrutinised datasets in the field, which is exactly why anything found in
  them is worth publishing and exactly why the finding is about an artifact and
  not about the people who built it.

**Withdrawing.** If an entry turns out to be wrong, it keeps its id and gains
`WITHDRAWN` plus the evidence that killed it. Deleting a published claim is how a
findings page becomes a marketing page, and this project has already withdrawn
its own reading of a result once ([D-008](FINDINGS.md#d-008)) rather than quietly
editing it.

## The entry fee for a new check

Four things, all of them required, none of them negotiable:

1. **An id and a row in the registry** (`CHECKS` in `src/dinostomp/lint.py`).
   The published check table in the README is generated from that registry and
   parity-tested against it, so the table cannot drift from the code.
2. **A gating flag**, and you have to argue for it. See the constitutional split
   below.
3. **A negative test** that breaks something on purpose and asserts the breakage
   is caught. A test that only proves the check passes on clean data proves
   nothing.
4. **A planted defect in DinoTrials** (`trials/run_trials.py`) with a stated
   expectation, plus confirmation that the six expected-CLEAN pods still report
   zero findings. Sensitivity without specificity is just a loud tool.

If a check cannot be given a planted defect, that is a signal about the check,
not about the trials.

## The constitutional split

**Invariants gate.** A duplicate exists. A hash changed. A summary does not
re-derive from its own records. These are deterministic facts, and a failure
means mechanical invalidity, so they break the verdict.

**Diagnostics warn.** Position bias, KR-20, discrimination, chance-level
accuracy, presentation-order swing. These are statistical inferences over
thresholds *we chose*, they can have legitimate explanations, and they expose
their underlying values so a reader can disagree with us. They never gate.

The line is not about severity. It is about whether we are reporting a fact or
an opinion. When in doubt, it is a diagnostic.

## Rules the engine keeps, that a patch may not remove

These have no off switch, no config key, and no environment variable. A fork
that removes them is not dinostomp:

- the witness gate: a scorer must demonstrate it can reject something before it
  may score anything
- a check that examined zero things skips; it never passes
- coverage-honest verdicts, with the full battery size always printed
- `seed` and `budget_usd` are required, and the cap is checked before the call
- uncheckable stays out of every denominator
- drift detection over every hashed input

## Things this project has learned the hard way

Written down because each one cost real time or real money:

- **Pooling hides the outlier.** Four separate checks (R7, R13, T4, T6) had to
  be rewritten per model after a fleet average concealed a single bad examinee.
  Treat any new fleet-level statistic as guilty until you have checked it.
- **A checker that skips the newest surface is off, not weak.** Two in one
  week: the CRLF guard listed only TRACKED files, so a brand-new pod was
  invisible until the commit that broke it had happened (D-028); and `inspect`
  listed only `python` targets, so a mediated pod was told it "ships no
  pod-local Python" while shipping an agent and tools (D-030). Both looked green
  while being switched off, and both were caught by writing a test against the
  SPEC rather than against a list of providers someone has to remember to
  extend.
- **Name a boundary for what it does, not what you wish it did.** The agent
  harness is called `mediated`, not `sandboxed`, because in-process Python is
  not a security boundary. When a real process boundary arrived it still did not
  take the word: it is documented as containment, with the escapes that survive
  asserted as PASSING tests (N-010), so strengthening it later has to break a
  test and rewrite the claim deliberately.
- **An instrument that cannot fire tells you nothing.** A canary probe against a
  fresh canary comes back clean whether the model is contaminated or the probe
  is broken, which is why every probe carries a positive control and skips when
  the control does not land.
- **`n/a` means "cannot be tested here", never "safe".** The mutation gauntlet
  reports a mutant as *equivalent* precisely when the scorer has that bug
  universally.
- **Fix the fixture, not the threshold.** When a trial misses, the check is
  usually right. Three separate P10 fixtures were wrong before the check was.
- **Zero is not a test.** The money invariant passed for months because every
  dry cost was exactly `0.00`; it broke on the first real fleet.

## Working on it

```bash
pip install -e '.[dev]'
python -m pytest                  # unit suite, every validator negative-tested
python trials/run_trials.py       # both tails: planted defects AND clean pods
```

Both must be green. The trials exit nonzero on a miss in either direction.

If you change anything under `src/dinostomp/`, the engine fingerprint moves, and
the value pinned in the README has to move with it:

```bash
dinostomp fingerprint             # paste this under the version in README.md
```

That is deliberate friction. The README publishes a hash so a reader can confirm
which bytes judged them, and re-publishing it should be a decision rather than a
side effect.

Examples and reports are parity-tested too. After a change that moves any
reported number:

```bash
for p in smoke fleet iris agent judge; do dinostomp report examples/$p/eval.yaml; done
```

## Style

House rules live in the code you are editing; match the file you are in. Two
worth stating anyway:

- No em dashes, and no `--` used as punctuation in prose.
- Comments explain **why**, especially why a threshold is what it is or why an
  obvious simpler approach was rejected. Several comments in this codebase exist
  because someone tried the obvious thing and it was subtly wrong.

## Reporting a defect in the battery itself

The most valuable bug report for this project is a **false negative**: an eval
that is broken in a way dinostomp calls clean. If you have one, a failing trial
case is worth more than an issue describing it.

The second most valuable is a **flattering false positive**: a finding that
would send someone hunting for a problem that is not there. One of those
(phantom key errors from a collapsed model) nearly produced a bogus research
result before it was caught.


## Extensions

Two rails are open: **checks** (a `dinostomp.checks` entry point) and
**adapters** (anything that writes conforming records and manifests). Both are
documented in METHODOLOGY.md.

One rule governs both, and it is not negotiable:

> **An extension may add findings. It may never remove or soften one.**

No hook may run before the core, filter findings, or adjust a threshold. An
extension that could make a verdict greener would make every `SOUND` in the
world mean "sound according to whichever plugins that person had installed",
and would put the deciding code outside the engine fingerprint that is supposed
to cover it. Extensions widen what the battery looks for. The core alone decides
what `BROKEN` means.

The rule is enforced, not trusted: a write-only collector, a threshold
fingerprint taken around extension execution, and a core-finding comparison
across the same window. A patch that weakens any of the three is a patch that
will not be merged, for the same reason a patch removing the witness gate will
not be.

The entry fee is the one the core pays. A check ships a planted defect it must
catch and a clean pod it must stay quiet on. An adapter ships a golden-file
trial: a real log in, conforming records out, every field accounted for
including the ones it cannot supply. Without them your work still runs and is
still reported, labelled `UNVALIDATED` and excluded from coverage, because
suppressing findings would be its own dishonesty and counting unproven ones
would be worse.
