"""Every asset planter fires its own check, and only its own.

The corpus promises exactly one planted defect per instance. A planter that also
trips two unrelated checks breaks that promise silently and inflates the score,
because a detector that found the wrong defect still counts as a hit. That is not
hypothetical: `train-test-overlap` originally planted a duplicate item and a
conflicting key alongside the split leak (D-054).
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "corpus"))

import asset_planters  # noqa: E402
import assets  # noqa: E402
from dinostomp.lint import lint_dataset  # noqa: E402

OWN_CHECK = {"asset-drift": "S12", "label-in-path": "S13",
             "train-test-overlap": "S14", "near-duplicate-asset": "S15"}


def _audit(tmp_path: Path, items: list[dict], files: dict[str, bytes]) -> list[str]:
    for rel, data in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    (tmp_path / "items.jsonl").write_text(
        "\n".join(json.dumps(i, sort_keys=True) for i in items) + "\n", encoding="utf-8")
    report, _issues, _ctx = lint_dataset(tmp_path / "items.jsonl", use_extensions=False)
    if report is None:
        return ["<unreadable>"]
    return sorted(f["id"] for f in report["findings"] if f["level"] in ("fail", "warn"))


@pytest.mark.parametrize("class_id", sorted(OWN_CHECK))
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_each_asset_planter_fires_exactly_its_own_check(tmp_path, class_id, seed):
    rng = random.Random(seed)
    items, files = assets.asset_items(rng)
    location = asset_planters.ASSET_PLANTERS[class_id](items, files, rng)
    assert location, f"{class_id} planted nothing at seed {seed}"
    fired = _audit(tmp_path, items, files)
    want = OWN_CHECK[class_id]
    assert want in fired, f"{class_id}: {want} did not fire (got {fired})"
    assert fired == [want], (
        f"{class_id} also tripped {[c for c in fired if c != want]}; an instance carrying "
        f"more than one defect cannot be scored")


@pytest.mark.parametrize("seed", [10, 11, 12])
def test_a_clean_image_pod_stays_silent(tmp_path, seed):
    """The other half of the tax, and the reason clean instances carry images.

    Without this, the four asset checks would only ever meet planted data and
    their recall would be unfalsifiable.
    """
    items, files = assets.asset_items(random.Random(seed))
    assert _audit(tmp_path, items, files) == []


def test_clean_images_are_structurally_distinct_not_merely_byte_distinct():
    """dHash encodes gradient direction, so a pool of ramps is a pool of
    near-duplicates however different the bytes are (D-043)."""
    import io

    Image = pytest.importorskip("PIL.Image", reason="needs the [vision] extra")
    from dinostomp.perceptual import dhash_image

    # dhash_image takes a DECODED image, not bytes. Passing bytes returns None
    # and every comparison silently becomes None ^ None.
    hashes = [dhash_image(Image.open(io.BytesIO(assets.png(assets.distinct(i + 1)))))
              for i in range(6)]
    assert all(h is not None for h in hashes), "an image failed to hash"
    pairs = [(a, b) for i, a in enumerate(hashes) for b in hashes[i + 1:]]
    closest = min(bin(a ^ b).count("1") for a, b in pairs)
    assert closest > 5, (
        f"two clean fixtures are {closest} bits apart, at or under the shipped "
        f"near-duplicate threshold; the fixture is wrong, not the check")
