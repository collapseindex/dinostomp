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
