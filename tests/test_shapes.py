"""Shape arms must be controls, not second defects.

Each shape exists to keep one past defect fixed. Two things have to hold or the
arm is decoration:

  CLEAN     a clean instance of the shape audits clean. If the FORM alone makes
            the battery fire, the arm measures the battery's opinion of the form
            and nothing else.
  EXERCISES the shape actually reaches the check it was added for. A CJK arm
            that never makes S9 skip would not have caught D-061.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "corpus"))

from basepool import clean_pool  # noqa: E402
from dinostomp.lint import lint_dataset  # noqa: E402
from shapes import SHAPE_PROVENANCE, SHAPES  # noqa: E402


def _audit(tmp_path: Path, items: list[dict]):
    p = tmp_path / "items.jsonl"
    p.write_text("\n".join(json.dumps(i, ensure_ascii=False) for i in items) + "\n",
                 encoding="utf-8")
    report, issues, _ctx = lint_dataset(p, use_extensions=False)
    return report, issues


def _shaped(shape: str, seed: int, n: int = 24) -> list[dict]:
    rng = random.Random(seed)
    return SHAPES[shape](clean_pool(n, rng), rng)


@pytest.mark.parametrize("shape", sorted(SHAPES))
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_a_clean_instance_of_every_shape_audits_clean(tmp_path, shape, seed):
    report, issues = _audit(tmp_path, _shaped(shape, seed))
    assert report is not None, f"{shape}: the audit refused a CLEAN instance: {issues[:1]}"
    loud = [f["id"] for f in report["findings"] if f["level"] in ("fail", "warn")]
    assert not loud, f"{shape}: clean instance triggered {loud}; the form is firing, not a defect"


def test_every_shape_says_which_defect_it_remembers():
    """An arm without a reason is an arm nobody can decide to remove."""
    assert set(SHAPE_PROVENANCE) == set(SHAPES)
    for name, why in SHAPE_PROVENANCE.items():
        assert len(why) > 20, f"{name}: provenance too thin to be useful"


def test_cjk_makes_the_shortcut_check_skip_rather_than_pass(tmp_path):
    """D-061. S9 tokenises on whitespace; a script without spaces gives it one
    token per stem, so it must SKIP. A pass here is the vacuous green line that
    sat on a real licensing exam for weeks."""
    report, _issues = _audit(tmp_path, _shaped("cjk", 7))
    s9 = next(f for f in report["findings"] if f["id"] == "S9")
    assert s9["level"] == "skip", f"S9 on CJK is {s9['level']!r}, expected skip"
    assert "space" in s9["detail"], "the skip must say WHY, or it is just a quieter pass"


def test_binary_items_keep_the_target_check_alive(tmp_path):
    """D-053. Removing the answer from a two-option item leaves one option, which
    the loader once stopped calling a choice list, taking the S6 gate with it."""
    items = _shaped("binary", 11)
    assert all(len(i["choices"]) == 2 for i in items if "choices" in i)
    victim = next(i for i in items if "choices" in i)
    victim["choices"] = [c for c in victim["choices"] if c != victim["target"]]
    report, _issues = _audit(tmp_path, items)
    fired = [f["id"] for f in report["findings"] if f["level"] == "fail"]
    assert "S6" in fired, f"S6 did not fire on a binary item missing its answer; got {fired}"


def test_short_answer_items_are_free_form(tmp_path):
    """D-059 lives on the free-form branch, which a four-option pool never reaches."""
    items = _shaped("short-answer", 5)
    assert not any("choices" in i for i in items)
    assert any(len(str(i["target"])) <= 3 for i in items), "no short target to trip the old bug"


def test_the_declared_incompatibility_matrix_matches_the_planters():
    """The declaration must be measured, not reasoned about.

    Written by hand it was wrong both ways: three classes declared impossible
    for `binary` plant fine, and four genuinely impossible ones for
    `short-answer` were missing, which crashed generation mid-split.
    """
    import generate as G
    from shapes import INCOMPATIBLE

    for shape in SHAPES:
        if shape == "baseline":
            continue
        actual = set()
        for cid, planter in G.PLANTERS.items():
            planted = False
            for seed in range(8):
                rng = random.Random(seed)
                items = SHAPES[shape](clean_pool(24, rng), rng)
                try:
                    if planter(items, rng):
                        planted = True
                        break
                except Exception:      # noqa: BLE001 - a throwing planter is incompatible
                    pass
            if not planted:
                actual.add(cid)
        declared = set(INCOMPATIBLE.get(shape, ()))
        assert declared == actual, (
            f"{shape}: declared {sorted(declared)} but measured {sorted(actual)}; "
            f"undeclared {sorted(actual - declared)}, over-declared {sorted(declared - actual)}")
