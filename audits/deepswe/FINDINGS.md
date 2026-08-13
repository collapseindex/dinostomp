# DeepSWE v1.1 grader audit

    repo    https://github.com/datacurve-ai/deep-swe
    commit  435ee89ec2f2e2289f33b0da4f992f0b7b7266b9
    file    tasks/*/tests/grader.py  (byte-identical across all 113 tasks)
    run     2026-08-13, 0 API calls, 0 Docker, $0.00

A COUNTEREXAMPLE, in a different domain from the string-scorer audits. Those
(F-030..F-038) parse a judge's free text; DeepSWE grades committed code with
program verifiers. The question changes accordingly: in every ambiguous case,
does the grader fail SAFE (toward reward 0) or can an unsolved task be graded
solved?

The `grade` subcommand is pure (config.json + report files -> reward.json), so
`audit.py` drives the real grader end to end with synthetic reports. Nothing is
reimplemented, and no task environment is executed.

## Verdict: coverage-honest, fails safe

Verified against the real grader:

- fidelity: all-pass -> reward 1; any f2p fail -> reward 0.
- a SKIPPED f2p test -> reward 0 (skip counts as failure).
- an f2p id MISSING from every report -> reward 0 (absence counts as failure).
- a p2p regression -> reward 0.
- an empty f2p whitelist -> reward 0 (no fail-to-pass evidence = nothing solved).
- an unparseable report -> every id absent -> reward 0.
- duplicate ids, one pass one fail -> worst-status-wins -> reward 0.

6 of 6 ambiguous cases fail toward reward 0. `reward = 1` requires `|f2p| > 0`
AND every fail-to-pass passing AND no pass-to-pass regressing. This is the
program-verifier analogue of StrongREJECT ([N-024](../../FINDINGS.md#n-024)): the
conservative-default design the string scorers lacked.

## One latent gap, recorded so it cannot reappear silently

`junit_status_msg` determines pass/fail from a `<testcase>`'s CHILD elements
(`<failure>`, `<error>`, `<skipped>`) and ignores any `status`/`result`
ATTRIBUTE. A report shaped `<testcase status="failed"/>` with no failure child is
read as PASSED, and confirmed to yield reward 1 on an otherwise-solved task. This
is the only unsafe-direction path in the grader.

Reachability: it is not triggerable by any shipped task. Of 113 tasks, 78 use
CTRF (status field, parsed correctly) and 35 use JUnit; of those, 34 use
`pytest --junitxml` and one uses a custom node runner, and every one emits
failures as `<failure>` child elements. So the gap is latent, not live. It is
worth an entry only because a future task adding an attribute-status reporter
would silently start grading failed tests as passed, and nothing in the grader
would catch it.

## Honest scoping

- The free, deterministic part audited here is the report -> reward layer. The
  parts that need real compute (are the f2p/p2p whitelists correct, are the
  tests strong, are any flaky) were NOT audited; they require executing the
  task Docker images.
- Each case was written against behaviour read in the source: a reproduction,
  not a discovery rate.

## Reproduce

Third-party repo, not vendored. No API key, no Docker, no spend.

    git clone https://github.com/datacurve-ai/deep-swe deep-swe
    git -C deep-swe checkout 435ee89ec2f2e2289f33b0da4f992f0b7b7266b9
    python audit.py deep-swe
