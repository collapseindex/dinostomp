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
    """The committed receipts have to be byte-identical to what a clone sees."""
    import subprocess

    tracked = subprocess.run(["git", "ls-files", "examples", "benchmarks"],
                             capture_output=True, text=True, cwd=REPO).stdout.split()
    crlf = [f for f in tracked
            if Path(f).suffix in (".json", ".jsonl", ".svg", ".yaml", ".md")
            and (REPO / f).is_file() and b"\r\n" in (REPO / f).read_bytes()]
    assert not crlf, f"committed artifacts carry CRLF: {crlf[:5]}"
