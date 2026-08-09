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
