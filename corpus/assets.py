"""Image-backed items, so the corpus can reach the asset checks.

Four defect classes in the taxonomy (`asset-drift`, `label-in-path`,
`train-test-overlap`, `near-duplicate-asset`) describe things that happen to
files on disk, not to text in a row. An instance made only of an `items.jsonl`
cannot carry them, which is why they went unplanted while the taxonomy declared
them.

TWO RULES THIS MODULE EXISTS TO ENFORCE.

**The clean arm carries assets too.** If only defective instances had images,
the four asset checks would only ever meet planted data, and their recall would
be unfalsifiable: a check that fired on every image-bearing instance would score
100% and the corpus would have no way to say so. Every instance in an
asset-bearing split gets images, planted or not.

**Clean images must be structurally distinct, not merely byte-distinct.**
`ramp(seed)` produces gradients that differ in bytes and are near-identical to a
perceptual hash, because dHash encodes gradient direction. Building a clean pool
out of those made S15 flag ten unrelated fixtures, and S15 was right; the fixture
was wrong (D-043). `distinct(seed)` moves a filled rectangle instead, so the
adjacent-pixel gradients land in different places.

WHY THIS DUPLICATES `trials/run_trials.py`. The trials suite proves the checks
fire. The corpus scores the checks. If the corpus imported its fixtures from the
trials suite, a bug in one fixture would move both the proof and the score in the
same direction, and the second number would stop being independent evidence
about the first. The ~30 lines are copied on purpose.
"""

from __future__ import annotations

import hashlib
import struct
import zlib

SIDE = 16
ASSETS_PER_INSTANCE = 6
SUBDIR = "images"


def png(rows: list[list[int]]) -> bytes:
    """Minimal 8-bit greyscale PNG, stdlib only.

    Real bytes, not a `.png` file full of nothing: S12 hashes what is on disk
    and S15 decodes pixels, so a fake file would prove only that they read a
    JSON field.
    """
    raw = b"".join(b"\x00" + bytes(r) for r in rows)

    def chunk(tag: bytes, body: bytes) -> bytes:
        return (struct.pack(">I", len(body)) + tag + body
                + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", SIDE, SIDE, 8, 0, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def distinct(seed: int) -> list[list[int]]:
    """A filled rectangle whose size and position move with the seed."""
    x0, y0 = (seed * 3) % (SIDE - 5), (seed * 5) % (SIDE - 5)
    w, h = 3 + (seed % 4), 3 + ((seed * 2) % 4)
    return [[20 if x0 <= x < x0 + w and y0 <= y < y0 + h else 235
             for x in range(SIDE)] for y in range(SIDE)]


def brightened(seed: int, by: int = 12) -> list[list[int]]:
    """The same picture, lifted. Different bytes, same structure.

    This is what `near-duplicate-asset` means and what a byte-level check
    cannot see: N-017 measured exactly zero recall for every byte-level method
    against hand-annotated duplicates, because no annotated pair is
    byte-identical.
    """
    return [[min(255, v + by) for v in row] for row in distinct(seed)]


def asset_items(rng, n: int = ASSETS_PER_INSTANCE) -> tuple[list[dict], dict[str, bytes]]:
    """`n` image-backed items and the files they point at.

    Returns (items, files) where files maps a pod-relative path to its bytes.
    The caller writes them; nothing here touches the disk, so a planter can
    rewrite a path or a hash before anything is committed to a file.
    """
    items: list[dict] = []
    files: dict[str, bytes] = {}
    labels = ("alpha", "beta")
    for i in range(n):
        data = png(distinct(i + 1))
        rel = f"{SUBDIR}/img-{i:03d}.png"
        files[rel] = data
        items.append({
            "id": f"img-{i:03d}",
            # The prompt VARIES per item, and that is load-bearing rather than
            # cosmetic. With one shared prompt, planting `train-test-overlap`
            # points two items at the same file with the same question, which is
            # a duplicate item and a conflicting key as well as a split leak: S1
            # and S7 fired alongside S14 and the instance carried three defects
            # instead of one. An instance with more than one defect cannot be
            # scored, because a detector that found the wrong one still looks
            # right.
            "input": f"Which shape is shown in image {i}?",
            "input_ref": {"kind": "image", "uri": rel,
                          "sha256": hashlib.sha256(data).hexdigest(),
                          # Half train, half test. S14 needs a declared split to
                          # have anything to say, and a split that only appears
                          # on planted instances would be a tell.
                          "split": "train" if i % 2 else "test"},
            "choices": list(labels),
            "target": labels[i % len(labels)],
        })
    return items, files


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
