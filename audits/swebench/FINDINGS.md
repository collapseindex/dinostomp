# SWE-bench harness + dataset audit

    repo    https://github.com/swe-bench/SWE-bench
    commit  c7fd5abffe0b2086a8bb9389d23c47d930ef571f
    files   swebench/harness/grading.py, swebench/harness/log_parsers/python.py
    data    princeton-nlp/SWE-bench (HuggingFace)
    run     2026-08-13, 0 API calls, 0 Docker, $0.00

SWE-bench is the one target with BOTH a public dataset and a public grading
harness, so it is auditable end to end. It is also the most-studied benchmark in
this set, so this audit is careful to separate what it VERIFIES on the real
code/data from what is already public. The real parse and grading functions are
imported from a clone; only the docker/unidiff backends, unused by the parse
layer, are stubbed.

## N: the harness is hardened against the scores-as-resolved bug family

The grading code's own comments are effectively a changelog of the exact
unsafe-direction bugs found across F-030..F-038, already patched:

- `grading.py test_failed` counts a SKIPPED fail-to-pass test as failed, with the
  comment *"a patch that makes every F2P test skip lands in neither list and
  scores RESOLVED_FULL"* without it. Verified live: `test_failed` returns True on
  a skipped F2P.
- `grading.py get_logs_eval` returns "not applied / invalid" when there are no
  parsed results AND no sign the suite ran, with the comment *"under
  EvalType.FAIL_ONLY an absent test counts as success, so without this a suite
  that never started scores every F2P test as resolved"*.

So the most-cited coding benchmark hit the scores-as-resolved failure mode and
hardened against it. The current harness belongs with the careful examples
(StrongREJECT [N-024], DeepSWE [N-025]), not the substring-bug family.

## F: pytest "[100%]" progress artifact is a phantom test in the gold data

pytest prints a running `[100%]` progress indicator. SWE-bench's dataset
construction captured `PASSED [100%]` as if `[100%]` were a test name, and it
survives in the gold PASS_TO_PASS of two instances. Verified two ways, 0 cost:

- mechanism, on the real parser: `parse_log_pytest("... PASSED [100%]")` returns
  a test named `[100%]` with status PASSED.
- data, on the real dataset (`princeton-nlp/SWE-bench`):
  `pytest-dev__pytest-5262` (108 P2P entries) and `pytest-dev__pytest-7521`
  (125 P2P entries) each contain exactly one `[100%]` entry.

The parser cannot filter this pollution: `log_parsers/python.py` carries
`TODO(john-b-yang): repair those two P2P lists, then widen [the skip-summary
filter] to any bare bracketed count`, and until then it must keep capturing
`[100%]` or those two instances fail. So the defect is doubly recorded: a
non-test in the gold labels, and a parser welded to pytest's exact progress
format to accommodate it. Benign at eval time (a phantom test that trivially
passes) but a real gold-label correctness defect, and format-fragile: a change
to pytest's progress output would break both instances.

## Not re-reported (already public)

Solution leakage in `problem_statement` and weak/underspecified tests are
documented in prior work and are the reason SWE-bench Verified exists. Confirming
them properly needs executing the task images. This audit claims only what it ran
on the real code and data.

## Reproduce

Third-party repo, not vendored. No API key, no Docker, no spend. The `[100%]`
dataset confirmation needs network (a free HuggingFace dataset read); the parser
mechanism is fully offline.

    git clone https://github.com/swe-bench/SWE-bench SWE-bench
    git -C SWE-bench checkout c7fd5abffe0b2086a8bb9389d23c47d930ef571f
    python audit.py SWE-bench
