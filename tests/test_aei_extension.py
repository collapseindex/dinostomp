"""The AEI extension's evidence tax, collected by the test suite.

The core marks an extension `validated` for merely DECLARING TRIALS and
CLEAN_PODS; it never runs them (D-051). So this extension's trials are run here
instead, which is the only place they currently get run at all.

Skipped rather than failed when the package is not installed: it lives under
extensions/ and is a separate distribution, so a checkout without it is a
supported state, not a broken one.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pytest

dinostomp_aei = pytest.importorskip("dinostomp_aei",
                                    reason="pip install -e extensions/dinostomp-aei")

from dinostomp_aei import rules  # noqa: E402

FIX = Path(dinostomp_aei.__file__).resolve().parent / "fixtures"
MUTANTS = ("A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10")


class Collect:
    def __init__(self) -> None:
        self.by_level: dict[str, list] = defaultdict(list)

    def finding(self, cid, level, detail, **kw) -> None:
        self.by_level[level].append((cid, detail))


def audit(path: Path) -> Collect:
    c = Collect()
    rules.audit(path, c)
    return c


def test_the_clean_release_stays_silent():
    """Half the tax. A check that fires on a conforming file has proved nothing
    except that it fires, and it would fire on somebody else's real data."""
    got = audit(FIX / "clean.csv")
    loud = got.by_level["fail"] + got.by_level["warn"]
    assert not loud, f"clean fixture triggered {[cid for cid, _ in loud]}"
    assert got.by_level["pass"], "clean fixture reached no verdict at all"


@pytest.mark.parametrize("check", MUTANTS)
def test_each_planted_defect_fires_its_own_check(check):
    """The other half, and the one that matters: the finding a check reports has
    to be the finding it names."""
    got = audit(FIX / f"mutant_{check}.csv")
    loud = got.by_level["fail"] + got.by_level["warn"]
    assert any(cid == check for cid, _ in loud), (
        f"{check}: planted defect did not fire its own check; "
        f"loud checks were {sorted({cid for cid, _ in loud})}")


def test_partition_sums_are_integer_arithmetic():
    """D-050. `40.63 + 59.38` is 100.01 exactly, sits on the bound two values
    rounded to two decimals may miss by, and is 100.00999999999999 in binary
    floating point. That difference nearly published a rounding convention as a
    defect in somebody else's data."""
    from dinostomp_aei.checks import _cents

    a, places_a = _cents("40.63")
    b, places_b = _cents("59.38")
    assert (a, b) == (4063, 5938)
    assert places_a == places_b == 2
    slack = 2 // 2                      # floor(k/2) hundredths for k=2 terms
    assert abs((a + b) - 10_000) <= slack
    assert abs((40.63 + 59.38) - 100.0) > 0.01   # the float version, still wrong


def test_the_contract_only_encodes_what_the_readme_states():
    """21 named metrics plus one per artifact label is 53, which is exactly what
    both released files contain. A vocabulary that drifted from the README would
    make every A2 finding an argument about the transcription instead."""
    from dinostomp_aei import contract as C

    assert len(C.ARTIFACT_LABELS) == 32
    assert len(C.METRIC_UNITS) == 53
    assert all(u in C.UNIT_RANGE for u in C.METRIC_UNITS.values())
