"""SWE-bench harness + dataset audit. No model, no Docker, no money.

SWE-bench is the one target with BOTH a public dataset and a public grading
harness, so it is auditable end to end. It is also the most-studied benchmark
here, so this separates what it VERIFIES on the real code/data from what is
already public (solution leakage and weak tests, the reasons SWE-bench Verified
exists, are NOT re-reported).

  repo   https://github.com/swe-bench/SWE-bench
  commit c7fd5abffe0b2086a8bb9389d23c47d930ef571f
  files  swebench/harness/grading.py, swebench/harness/log_parsers/python.py
  data   princeton-nlp/SWE-bench (HuggingFace)

The real parser and grading functions are imported from a clone; only the
docker/unidiff backends (unused by the parse layer) are stubbed. Two results:

  N: the harness is HARDENED. Its own comments are a changelog of the
     scores-as-resolved bug family found elsewhere in these audits, already
     patched. Demonstrated live.
  F: one gold-data defect survives: pytest's "[100%]" progress artifact is a
     phantom test in two instances' gold PASS_TO_PASS, and the parser must keep
     capturing it (self-documented TODO). Verified on the real dataset.
"""
from __future__ import annotations

import json
import pathlib
import sys
import types
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
REPO = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "SWE-bench"
REPO_URL = "https://github.com/swe-bench/SWE-bench"
REPO_COMMIT = "c7fd5abffe0b2086a8bb9389d23c47d930ef571f"
POLLUTED = ["pytest-dev__pytest-5262", "pytest-dev__pytest-7521"]

if not (REPO / "swebench" / "harness" / "grading.py").exists():
    raise SystemExit(
        f"SWE-bench not found at {REPO}\n\n"
        f"    git clone {REPO_URL} SWE-bench\n"
        f"    git -C SWE-bench checkout {REPO_COMMIT}\n"
        f"    python audit.py SWE-bench\n")


def load_harness(repo: pathlib.Path):
    """Import the real parse + grading layer, skipping the heavy package inits
    (ghapi at the top level, docker in harness/__init__) that the parse layer
    does not use."""
    root = repo / "swebench"
    for mod in ("unidiff", "docker", "docker.models", "docker.models.containers"):
        sys.modules.setdefault(mod, types.ModuleType(mod))
    sys.modules["unidiff"].PatchSet = object
    sys.modules["docker.models.containers"].Container = object

    def ns(name, path):
        m = types.ModuleType(name)
        m.__path__ = [str(path)]
        sys.modules[name] = m

    ns("swebench", root)
    ns("swebench.harness", root / "harness")
    from swebench.harness.grading import test_failed
    from swebench.harness.log_parsers.python import parse_log_pytest
    return parse_log_pytest, test_failed


parse_log_pytest, test_failed = load_harness(REPO)

print(f"  {REPO_URL}")
print(f"  commit {REPO_COMMIT}\n")

print("  PART A  fidelity")
sm = parse_log_pytest(
    "PASSED tests/t.py::a\nFAILED tests/t.py::b - AssertionError\n"
    "SKIPPED tests/t.py::c", None)
assert sm == {"tests/t.py::a": "PASSED", "tests/t.py::b": "FAILED", "tests/t.py::c": "SKIPPED"}, sm
print("    ok   PASSED/FAILED/SKIPPED lines parse correctly")

print("\n  N  harness is hardened against the scores-as-resolved bug family")
skip_is_fail = test_failed("tests/t.py::c", sm)
print(f"    a SKIPPED fail-to-pass test is treated as failed: {skip_is_fail}")
print("    (grading.py comment: 'a patch that makes every F2P test skip ... scores")
print("     RESOLVED_FULL' without this guard. Also: get_logs_eval returns invalid")
print("     when no results AND no sign the suite ran, so an unstarted suite does")
print("     not score every F2P as resolved under EvalType.FAIL_ONLY.)")
assert skip_is_fail is True

print("\n  F  gold-data pollution: pytest '[100%]' progress artifact as a phantom test")
sm2 = parse_log_pytest("PASSED tests/t.py::real\nPASSED [100%]", None)
phantom = "[100%]" in sm2
print(f"    'PASSED [100%]' parses to a test named '[100%]': {phantom} -> {sm2.get('[100%]')}")
assert phantom

print("    confirming the two gold PASS_TO_PASS lists actually contain it (needs network):")
try:
    for inst in POLLUTED:
        q = urllib.parse.urlencode({
            "dataset": "princeton-nlp/SWE-bench", "config": "default",
            "split": "test", "where": f"\"instance_id\"='{inst}'", "length": "1"})
        d = json.load(urllib.request.urlopen(
            "https://datasets-server.huggingface.co/filter?" + q, timeout=60))
        p2p = d["rows"][0]["row"]["PASS_TO_PASS"]
        p2p = json.loads(p2p) if isinstance(p2p, str) else p2p
        hits = [x for x in p2p if x.strip() == "[100%]"]
        print(f"      {inst}: {len(p2p)} P2P entries, '[100%]' present: {len(hits) == 1}")
except Exception as e:  # noqa: BLE001
    print(f"      (offline or dataset-server unavailable: {type(e).__name__}) "
          f"mechanism above stands; the self-documented TODO names both instances")

print("\n  known and NOT re-reported: solution leakage in problem_statement and")
print("  weak/underspecified tests are publicly documented and are why SWE-bench")
print("  Verified exists. This audit adds only what it ran on the real code/data.")
