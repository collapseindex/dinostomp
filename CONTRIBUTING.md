# Contributing to dinostomp

The short version: **a check that has never been proven to fire is decoration.**
Everything below follows from that.

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
