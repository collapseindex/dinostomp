"""Near-duplicate images: the one thing here that genuinely needs pixels.

Byte-identical duplicates are free (`modality.sha256_file`) and catch the case
where the same file was included twice. They catch nothing else. Re-encode a
JPEG, resize it, or shift it by one pixel and the bytes change completely while
the image is the same image, which is exactly the form train/test leakage takes
in vision benchmarks: not the same FILE twice, the same PHOTOGRAPH twice.

So this module decodes, and decoding needs Pillow. That is a real dependency and
it stays OPTIONAL:

    pip install 'dinostomp[vision]'

Without it, `available()` is False and every check built on this SKIPS, naming
the missing package. It must never quietly pass, because "no near-duplicates
found" and "I cannot look for near-duplicates" are different sentences and only
one of them is true.

The hash is dHash (difference hash), chosen over aHash and pHash deliberately:

  * aHash (mean threshold) is the weakest of the three and flags flat images as
    duplicates of each other, which on a dataset with many white backgrounds is
    a false-positive machine.
  * pHash (DCT) is the most robust and needs a DCT implementation, which means
    numpy or scipy, which is a second dependency for a marginal gain over dHash
    on the near-duplicate case (crops, rescales, re-encodes).
  * dHash compares ADJACENT PIXELS, so it keys on gradient structure rather than
    absolute brightness. It survives resizing and re-encoding, it is roughly
    fifteen lines, and Pillow alone can compute it.

WHAT THIS IS NOT. A dHash collision is EVIDENCE of a near-duplicate, not proof
of one. Every check using it is a DIAGNOSTIC that warns and prints the pair, so
a human decides. The literature this is aimed at (Barz & Denzler's CIFAR
work) had humans confirm their duplicates, and a tool that skipped that step
while quoting their numbers would be claiming a rigour it did not do.
"""

from __future__ import annotations

from pathlib import Path

# Hash geometry. 8x8 output means the image is resized to 9x8 and each row
# contributes 8 adjacent-pixel comparisons, giving a 64-bit hash.
HASH_SIDE = 8

# Hamming distance at or below this counts as a candidate near-duplicate. 5 of
# 64 bits is the conventional value in the perceptual-hash literature and is
# labelled `convention` in the threshold table for exactly that reason: it is
# defensible by citation, not derived, and it is the dial to move first if this
# check ever reads noisy.
NEAR_DUP_BITS = 5


def available() -> bool:
    """Whether image decoding is installed. Checks are required to call this."""
    try:
        import PIL.Image  # noqa: F401
    except ImportError:
        return False
    return True


def missing_reason() -> str:
    return ("image decoding is not installed, so near-duplicates cannot be looked for. "
            "`pip install 'dinostomp[vision]'`. Byte-identical duplicates are still "
            "covered by S1 and S7, which need no decoder.")


def dhash_image(img, side: int = HASH_SIDE) -> int | None:
    """Difference hash of an already-decoded PIL image.

    Split out from `dhash` so a caller holding pixels in MEMORY can hash them
    through the identical code path instead of writing a temporary file. That
    matters for honesty as much as for speed: the CIFAR comparison in
    `benchmarks/cifair/` scores THIS function against a published human
    annotation, and it would be worth nothing if it scored a reimplementation
    of it that happened to live in the benchmark script.
    """
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        small = img.convert("L").resize((side + 1, side), Image.LANCZOS)
        # `getdata` is deprecated for removal in Pillow 14 and `get_flattened_data`
        # does not exist before Pillow 11, so both are supported rather than
        # pinning a narrow range. A hash function that stops working on a routine
        # dependency bump would silently turn S15 into a permanent skip.
        reader = getattr(small, "get_flattened_data", None) or small.getdata
        pixels = list(reader())
    except Exception:
        # Pillow raises a wide family of decode errors, several of which are
        # not subclasses of one another. This is the one place a broad catch is
        # right: the caller wants "did not decode", not a taxonomy of why.
        return None
    bits = 0
    for row in range(side):
        base = row * (side + 1)
        for col in range(side):
            bits = (bits << 1) | int(pixels[base + col] > pixels[base + col + 1])
    return bits


def dhash(path: Path, side: int = HASH_SIDE) -> int | None:
    """Difference hash of an image file, or None if it will not decode.

    None is returned rather than raised: a corrupt image in a dataset of ten
    thousand is a finding about that item, and it must not take down the audit
    of the other 9,999.
    """
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        with Image.open(path) as img:
            return dhash_image(img, side)
    except Exception:
        return None


def distance(a: int, b: int) -> int:
    """Hamming distance between two hashes."""
    return (a ^ b).bit_count()


def near_duplicate_pairs(hashes: dict[str, int], max_bits: int = NEAR_DUP_BITS,
                         limit: int | None = None) -> list[tuple[str, str, int]]:
    """Candidate near-duplicate pairs, as (id_a, id_b, distance).

    Bucketed by hash prefix before comparing. The exhaustive form is O(n^2) and
    a 10,000-image test set is 50 million comparisons, which is slow enough that
    someone would turn the check off. Two hashes within `max_bits` differ in at
    most `max_bits` positions, so bucketing on any (max_bits + 1) disjoint
    slices means a true pair MUST agree exactly on at least one slice: the
    pigeonhole principle, not a heuristic, so this loses no true pairs.
    """
    if not hashes:
        return []
    slices = max_bits + 1
    width = 64 // slices
    seen: set[tuple[str, str]] = set()
    out: list[tuple[str, str, int]] = []
    for s in range(slices):
        shift = s * width
        mask = (1 << width) - 1
        buckets: dict[int, list[str]] = {}
        for item_id, h in hashes.items():
            buckets.setdefault((h >> shift) & mask, []).append(item_id)
        for group in buckets.values():
            if len(group) < 2:
                continue
            for i, a in enumerate(group):
                for b in group[i + 1:]:
                    pair = (a, b) if a <= b else (b, a)
                    if pair in seen:
                        continue
                    seen.add(pair)
                    d = distance(hashes[a], hashes[b])
                    if d <= max_bits:
                        out.append((pair[0], pair[1], d))
                        if limit and len(out) >= limit:
                            return sorted(out, key=lambda p: p[2])
    return sorted(out, key=lambda p: p[2])
