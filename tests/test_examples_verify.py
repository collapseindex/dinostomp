"""The flagship v0.14.0 claim, guarded: the committed example pods must
verify against their committed reports. This is what makes the repo
"pre-verifiable from day one" true rather than aspirational: a fresh clone
runs this and re-derives every published example number offline."""

from pathlib import Path

import pytest

from dinostomp.report import verify_report

REPO = Path(__file__).resolve().parents[1]
PODS = [p.parent for p in (REPO / "examples").glob("*/eval.yaml")]


@pytest.mark.parametrize("pod", PODS, ids=lambda p: p.name)
def test_committed_example_verifies(pod):
    status, details, _ = verify_report(pod / "eval.yaml")
    assert status == "verified", f"{pod.name}: {status} -- {details}"


def test_a_published_report_verifies_from_somewhere_else(tmp_path):
    """The whole thesis: a stranger re-derives a verdict without trusting the
    publisher. A stranger's copy is at a different path.

    This is the test that was missing. Reports embedded the ABSOLUTE path of
    the spec, so every published report verified only on the machine that made
    it, and the local suite never noticed because it always checked the pod
    where it was generated. CI on a fresh Linux runner is the stranger, and it
    failed on all five example pods.
    """
    import shutil

    for pod in PODS:
        dst = tmp_path / pod.name
        shutil.copytree(pod, dst)
        status, details, _ = verify_report(dst / "eval.yaml")
        assert status == "verified", f"{pod.name} moved to a new path: {status} -- {details}"


def test_every_writer_emits_lf_so_pods_survive_a_checkout(tmp_path):
    """The drift boundary hashes EXACT BYTES, so a translated newline is drift.

    Python's write_text turns "\n" into "\r\n" on Windows. A pod generated
    there and checked out anywhere else hashed differently, so `input-drift`
    fired and every published report failed to re-derive. CI on a Linux runner
    caught it; the local suite could not, because it only ever saw one
    platform's line endings.
    """
    import shutil

    from dinostomp.cli import main

    src = REPO / "examples" / "smoke"
    pod = tmp_path / "smoke"
    shutil.copytree(src, pod, ignore=shutil.ignore_patterns("data", "STOMP.*", "*.svg"))
    assert main(["run", str(pod / "eval.yaml")]) == 0
    main(["report", str(pod / "eval.yaml"), "--allow-incomplete"])

    written = list(pod.rglob("*.json")) + list(pod.rglob("*.jsonl")) \
        + list(pod.rglob("*.md")) + list(pod.rglob("*.svg"))
    assert written, "the run produced nothing to check"
    crlf = [p.name for p in written if b"\r\n" in p.read_bytes()]
    assert not crlf, f"these were written with CRLF and will not survive a checkout: {crlf}"


def test_tracked_pod_artifacts_are_lf_on_disk():
    """The committed receipts have to be byte-identical to what a clone sees.

    UNTRACKED files are checked too, and that is what the second command below
    is for. This guard used `git ls-files` alone, which lists only what is
    ALREADY tracked, so a brand-new pod was invisible to it until the commit
    introducing that pod had already happened. `examples/mediated/eval.yaml`
    went in carrying CRLF and this test passed locally on the very run that
    produced it; CI caught it a minute later, once the file was tracked. A
    checker that cannot fire on new work is switched off for exactly the change
    most likely to need it (D-028).

    `.gitattributes` marks `*.yaml -text`, so git stores those bytes verbatim: a
    CRLF spec written by a Windows editor survives into a clone, where its hash
    no longer matches the drift boundary its runs were produced under.
    """
    import subprocess

    def git(*args):
        return subprocess.run(["git", *args, "examples", "benchmarks"],
                              capture_output=True, text=True, cwd=REPO).stdout.split()

    candidates = set(git("ls-files")) | set(git("ls-files", "--others", "--exclude-standard"))
    crlf = [f for f in sorted(candidates)
            if Path(f).suffix in (".json", ".jsonl", ".svg", ".yaml", ".md", ".py")
            and (REPO / f).is_file() and b"\r\n" in (REPO / f).read_bytes()]
    assert not crlf, f"pod artifacts carry CRLF: {crlf[:5]}"
