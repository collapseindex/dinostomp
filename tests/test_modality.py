"""Asset-backed items: the input lives in a file.

Written against `modality` and `perceptual` directly, because the trials prove
the CHECKS fire and these prove the primitives underneath them behave. Both
matter: a check can pass its trial for the wrong reason.
"""

import hashlib
import struct
import zlib
from pathlib import Path

import pytest

from dinostomp import modality, perceptual


def png(rows) -> bytes:
    raw = b"".join(b"\x00" + bytes(r) for r in rows)

    def chunk(tag, body):
        return (struct.pack(">I", len(body)) + tag + body
                + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", len(rows[0]), len(rows), 8, 0, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def block(x0=2, y0=2, w=5, h=5, side=16):
    return [[20 if x0 <= x < x0 + w and y0 <= y < y0 + h else 235
             for x in range(side)] for y in range(side)]


# --- path confinement: a dataset is untrusted input --------------------------


@pytest.mark.parametrize("uri", [
    "../escape.png",
    "../../escape.png",
    "sub/../../escape.png",
    "C:/Windows/System32/drivers/etc/hosts",
    "/etc/passwd",
])
def test_an_asset_path_may_not_leave_the_pod(uri, tmp_path):
    """A uri comes from a dataset, and a dataset can be written by anyone.

    Absolute paths are refused even when harmless: a pod is only portable if
    everything it needs travels with it.
    """
    assert modality.resolve(uri, tmp_path) is None, f"{uri!r} was allowed to resolve"


def test_an_ordinary_relative_path_resolves(tmp_path):
    (tmp_path / "images").mkdir()
    (tmp_path / "images" / "a.png").write_bytes(png(block()))
    got = modality.resolve("images/a.png", tmp_path)
    assert got is not None and got.is_file()


# --- hashing and verification ------------------------------------------------


def test_a_changed_file_is_caught_and_a_matching_one_is_not(tmp_path):
    data = png(block())
    (tmp_path / "a.png").write_bytes(data)
    item = {"id": "x", "target": "t",
            "input_ref": {"kind": "image", "uri": "a.png",
                          "sha256": hashlib.sha256(data).hexdigest()}}
    problems, digests = modality.verify_refs([item], tmp_path)
    assert not problems and digests["x"] == hashlib.sha256(data).hexdigest()

    (tmp_path / "a.png").write_bytes(png(block(x0=6)))
    problems, digests = modality.verify_refs([item], tmp_path)
    assert [p.kind for p in problems] == ["hash-mismatch"]
    assert "x" not in digests, (
        "an item whose asset failed verification must not appear in the digest map: "
        "a placeholder there makes every broken item a duplicate of every other")


def test_asset_bytes_are_not_newline_normalised(tmp_path):
    """The engine fingerprint normalises line endings on purpose. An asset must
    NOT: a PNG whose CRLFs were 'fixed' is a corrupt PNG."""
    (tmp_path / "a.bin").write_bytes(b"\r\n\r\n")
    (tmp_path / "b.bin").write_bytes(b"\n\n")
    assert modality.sha256_file(tmp_path / "a.bin") != modality.sha256_file(tmp_path / "b.bin")


# --- the label in the path ---------------------------------------------------


def test_a_class_directory_leaks_and_a_substring_does_not():
    assert modality.path_leaks_label("images/test/cat/0001.png", ["cat"]) == "cat"
    assert modality.path_leaks_label("images/cat_0001.png", ["cat"]) == "cat"
    # 'cat' inside 'concatenated' is not a leak, and a check that says it is
    # will be switched off by the first person it annoys.
    assert modality.path_leaks_label("images/concatenated/0001.png", ["cat"]) is None
    assert modality.path_leaks_label("images/scatter/0001.png", ["cat"]) is None
    # Short labels are ignored: a 2-character class name matches everywhere.
    assert modality.path_leaks_label("images/ab/0001.png", ["ab"]) is None


# --- perceptual --------------------------------------------------------------


@pytest.mark.skipif(not perceptual.available(), reason="needs the vision extra")
def test_a_brightened_copy_hashes_close_and_a_different_picture_does_not(tmp_path):
    base = block()
    (tmp_path / "a.png").write_bytes(png(base))
    (tmp_path / "b.png").write_bytes(png([[min(255, v + 4) for v in r] for r in base]))
    (tmp_path / "c.png").write_bytes(png(block(x0=9, y0=9, w=4, h=6)))

    a, b, c = (perceptual.dhash(tmp_path / n) for n in ("a.png", "b.png", "c.png"))
    assert None not in (a, b, c)
    assert perceptual.distance(a, b) <= perceptual.NEAR_DUP_BITS, (
        "a brightened copy of the same picture must read as a near-duplicate")
    assert perceptual.distance(a, c) > perceptual.NEAR_DUP_BITS, (
        "two different pictures must not")


@pytest.mark.skipif(not perceptual.available(), reason="needs the vision extra")
def test_the_bucketed_search_finds_what_the_exhaustive_one_does(tmp_path):
    """The bucketing is a pigeonhole argument, not a heuristic, so it must lose
    no pair the O(n^2) comparison would find. If it ever does, the check is
    silently under-reporting, which is the flattering direction."""
    hashes = {f"i{n}": (n * 2654435761) % (1 << 64) for n in range(220)}
    hashes["near-a"] = 0xF0F0F0F0F0F0F0F0
    hashes["near-b"] = 0xF0F0F0F0F0F0F0F1
    bits = perceptual.NEAR_DUP_BITS

    exhaustive = set()
    ids = sorted(hashes)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if perceptual.distance(hashes[a], hashes[b]) <= bits:
                exhaustive.add((a, b))
    bucketed = {(a, b) for a, b, _ in perceptual.near_duplicate_pairs(hashes, bits)}
    assert bucketed == exhaustive
    assert ("near-a", "near-b") in bucketed


def test_a_corrupt_image_returns_none_rather_than_raising(tmp_path):
    (tmp_path / "bad.png").write_bytes(b"not a png at all")
    assert perceptual.dhash(tmp_path / "bad.png") is None


def test_the_check_skips_rather_than_passes_without_the_extra():
    """The wording matters more than the mechanism: a reader must not come away
    thinking the dataset was searched."""
    reason = perceptual.missing_reason()
    assert "pip install" in reason and "dinostomp[vision]" in reason
    assert "S1 and S7" in reason, "the skip should say what IS still covered"
