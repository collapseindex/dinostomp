"""DeepSWE v1.1 grader audit. No Docker, no network, no money.

Another COUNTEREXAMPLE, in a different domain from the string-scorer audits. The
five string-scorer audits (F-030..F-038) are about parsing a judge's free text.
DeepSWE grades committed code with program verifiers, so the question changes:
in every ambiguous case, does the grader fail SAFE (toward reward 0,
under-crediting) or can an UNSOLVED task be graded solved?

  repo   https://github.com/datacurve-ai/deep-swe
  commit 435ee89ec2f2e2289f33b0da4f992f0b7b7266b9
  file   tasks/*/tests/grader.py  (byte-identical across all 113 tasks)

The grader's `grade` subcommand is pure: config.json + report files -> reward.json.
We set $TESTS_DIR / $VERIFIER_DIR, write a config and synthetic reports, import
the real grader, call cmd_grade([]), and read the reward it wrote. Nothing is
reimplemented.
"""
from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
REPO = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "deep-swe"
REPO_URL = "https://github.com/datacurve-ai/deep-swe"
REPO_COMMIT = "435ee89ec2f2e2289f33b0da4f992f0b7b7266b9"

graders = sorted(REPO.glob("tasks/*/tests/grader.py"))
if not graders:
    raise SystemExit(
        f"DeepSWE not found at {REPO}\n\n"
        f"    git clone {REPO_URL} deep-swe\n"
        f"    git -C deep-swe checkout {REPO_COMMIT}\n"
        f"    python audit.py deep-swe\n")
GRADER = graders[0]

# All graders identical? (the audit's claim of one shared script)
import hashlib
digests = {hashlib.md5(g.read_bytes()).hexdigest() for g in graders}


def run_case(config, reports, argv=None):
    tdir = pathlib.Path(tempfile.mkdtemp())
    vdir = pathlib.Path(tempfile.mkdtemp())
    paths = []
    for i, text in enumerate(reports):
        p = tdir / f"report{i}.xml"
        p.write_text(text, encoding="utf-8")
        paths.append(str(p))
    config.setdefault("grade", {})["reports"] = paths
    (tdir / "config.json").write_text(json.dumps(config))
    os.environ["TESTS_DIR"] = str(tdir)
    os.environ["VERIFIER_DIR"] = str(vdir)
    spec = importlib.util.spec_from_file_location(f"grader_{tdir.name}", GRADER)
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    g.cmd_grade(list(argv or []))
    return json.loads((vdir / "reward.json").read_text())


def junit(cases):
    out = ["<testsuite>"]
    for cn, nm, kind in cases:
        if kind == "pass":
            out.append(f'<testcase classname="{cn}" name="{nm}"/>')
        elif kind == "fail":
            out.append(f'<testcase classname="{cn}" name="{nm}"><failure message="boom">t</failure></testcase>')
        elif kind == "skip":
            out.append(f'<testcase classname="{cn}" name="{nm}"><skipped/></testcase>')
        elif kind == "attr-fail":
            out.append(f'<testcase classname="{cn}" name="{nm}" status="failed"/>')
    out.append("</testsuite>")
    return "\n".join(out)


def cfg(f2p, p2p, fmt="junit"):
    return {"f2p_node_ids": f2p, "p2p_node_ids": p2p, "grade": {"format": fmt}}


def quiet(fn):
    import io
    import contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        return fn()


print(f"  {REPO_URL}")
print(f"  commit {REPO_COMMIT}")
print(f"  {len(graders)} task graders, {len(digests)} unique "
      f"({'shared verbatim' if len(digests) == 1 else 'DIVERGENT'})\n")

print("  PART A  fidelity")
r = quiet(lambda: run_case(cfg(["S.a"], ["S.b"]), [junit([("S", "a", "pass"), ("S", "b", "pass")])]))
print(f"    all pass          -> reward {r['reward']}  (want 1)")
r = quiet(lambda: run_case(cfg(["S.a"], ["S.b"]), [junit([("S", "a", "fail"), ("S", "b", "pass")])]))
print(f"    f2p fails         -> reward {r['reward']}  (want 0)\n")

print("  PART B  every ambiguous case must fail SAFE (toward reward 0)")
CHECKS = [
    ("f2p SKIPPED", cfg(["S.t"], []), [junit([("S", "t", "skip")])]),
    ("f2p MISSING from report", cfg(["S.t"], []), [junit([("S", "x", "pass")])]),
    ("p2p regression", cfg(["S.t"], ["S.g"]), [junit([("S", "t", "pass"), ("S", "g", "fail")])]),
    ("empty f2p whitelist", cfg([], ["S.g"]), [junit([("S", "g", "pass")])]),
    ("unparseable report", cfg(["S.t"], []), ["<not xml"]),
    ("dup ids, one pass one fail", cfg(["S.t"], []), [junit([("S", "t", "pass"), ("S", "t", "fail")])]),
]
safe = 0
for name, c, reps in CHECKS:
    r = quiet(lambda c=c, reps=reps: run_case(c, reps))
    ok = r["reward"] == 0
    safe += ok
    print(f"    {'ok ' if ok else 'UNSAFE':>7}  reward={r['reward']}  {name}")
print(f"    {safe}/{len(CHECKS)} fail safe\n")

print("  PART C  latent gap: junit_status_msg reads pass/fail from CHILD elements only")
r = quiet(lambda: run_case(cfg(["S.t"], []), [junit([("S", "t", "attr-fail")])]))
print(f"    <testcase status='failed'> with NO <failure> child -> reward {r['reward']}")
print(f"    A failed test read as passed. This is the ONE unsafe-direction path.")
print(f"    Reachability: every DeepSWE reporter (pytest --junitxml x34, one custom")
print(f"    node runner x1, ctrf x78) emits failures as <failure> CHILD elements, so")
print(f"    no shipped task can trigger it. Latent, not live; recorded so a future")
print(f"    attribute-status reporter cannot reintroduce it silently.")
