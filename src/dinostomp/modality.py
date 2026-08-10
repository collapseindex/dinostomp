"""Items whose input is a FILE rather than a string: images, audio.

A text eval carries its input in the dataset. A vision or audio eval carries a
POINTER, and the thing pointed at can change without the dataset changing. That
is the drift problem this project already solves for specs, scorers and engines,
arriving in a new place, so it gets the same answer: the item declares the
asset's SHA-256 and the battery re-hashes the bytes.

What this module does NOT do is decode anything. Reading a PNG needs a decoder,
a decoder is a dependency, and a dependency to detect a duplicate file is a bad
trade when the file's bytes already answer the question. Everything here is
stdlib. Perceptual comparison, which genuinely does need pixels, lives behind
the optional `[vision]` extra in `perceptual.py` and every check that uses it
skips loudly when it is absent rather than passing quietly.

Three rules, all of them learned elsewhere in this repo:

  * an asset path is UNTRUSTED input. It comes from a dataset that may have been
    written by anyone, so it is resolved and confined to the pod directory, and
    a path that escapes is an error rather than a read.
  * files are STREAMED, never slurped. A dataset of ten thousand images must not
    need ten thousand images' worth of memory to hash.
  * a missing asset is a FINDING, not an exception. An eval whose data half
    vanished should read `BROKEN`, not crash.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

# Streamed in chunks: the point is that a 4GB video and a 4KB thumbnail cost the
# same memory. 1 MiB is large enough that syscall overhead disappears and small
# enough to stay invisible on the 8GB laptop this is meant to run on.
HASH_CHUNK = 1024 * 1024

# A single asset over this is refused rather than hashed. Not a security
# boundary (the file is already on disk); a guard so a mistyped path at a
# device node or a swap file fails as a sentence instead of a hang.
MAX_ASSET_BYTES = 512 * 1024 * 1024

KINDS = ("image", "audio")


@dataclass(frozen=True)
class RefProblem:
    """One thing wrong with one item's asset reference."""

    item_id: str
    uri: str
    kind: str      # missing | escapes | too-big | unreadable | hash-mismatch
    detail: str


def ref_of(item: dict) -> dict | None:
    """The item's asset reference, or None for an ordinary text item."""
    ref = item.get("input_ref")
    return ref if isinstance(ref, dict) and ref.get("uri") else None


def has_refs(items: list[dict]) -> bool:
    return any(ref_of(i) for i in items)


def kinds_present(items: list[dict]) -> set[str]:
    return {str(ref_of(i).get("kind") or "?") for i in items if ref_of(i)}


def resolve(uri: str, base_dir: Path) -> Path | None:
    """Resolve an asset path INSIDE the pod, or None if it escapes.

    A dataset is data, and data can be hostile or merely wrong. `../../../etc`
    in a uri is not a path this tool will read, and neither is an absolute one:
    a pod is only portable if everything it needs travels with it, so an
    absolute path is a defect even when it happens to be harmless here. Both
    are reported as findings by the caller.
    """
    candidate = Path(uri)
    if candidate.is_absolute():
        return None
    try:
        resolved = (base_dir / candidate).resolve()
        base = base_dir.resolve()
    except (OSError, ValueError):
        return None
    return resolved if resolved == base or base in resolved.parents else None


def sha256_file(path: Path) -> str:
    """SHA-256 of a file's bytes, streamed.

    NOT newline-normalised, unlike the engine fingerprint. An asset is opaque
    bytes: a PNG that had its line endings 'fixed' is a corrupt PNG, and the
    hash should say so.
    """
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(HASH_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def verify_refs(items: list[dict], base_dir: Path) -> tuple[list[RefProblem], dict[str, str]]:
    """Re-hash every referenced asset. Returns (problems, {item_id: sha256}).

    The returned map is what identity checks key on, so an item whose asset
    could not be hashed is absent from it rather than present with a
    placeholder. A placeholder would make every broken item look like a
    duplicate of every other broken item, which is a fabricated finding on a
    gating check.
    """
    problems: list[RefProblem] = []
    digests: dict[str, str] = {}
    for item in items:
        ref = ref_of(item)
        if not ref:
            continue
        item_id, uri = str(item.get("id")), str(ref["uri"])
        path = resolve(uri, base_dir)
        if path is None:
            problems.append(RefProblem(item_id, uri, "escapes",
                                       "absolute, or resolves outside the pod directory"))
            continue
        if not path.is_file():
            problems.append(RefProblem(item_id, uri, "missing", "no file at that path"))
            continue
        try:
            size = path.stat().st_size
            if size > MAX_ASSET_BYTES:
                problems.append(RefProblem(
                    item_id, uri, "too-big",
                    f"{size / 1024 / 1024:.0f}MB, over the "
                    f"{MAX_ASSET_BYTES // 1024 // 1024}MB per-asset cap"))
                continue
            got = sha256_file(path)
        except OSError as exc:
            problems.append(RefProblem(item_id, uri, "unreadable", str(exc)))
            continue
        declared = str(ref.get("sha256") or "").lower()
        if declared and got != declared:
            problems.append(RefProblem(item_id, uri, "hash-mismatch",
                                       f"declared {declared[:12]}..., file is {got[:12]}..."))
            continue
        digests[item_id] = got
    return problems, digests


def path_leaks_label(uri: str, targets: list[str]) -> str | None:
    """The target that appears in an asset's own path, if any.

    `cifar10/test/automobile/0042.png` carries its answer in the directory name.
    That is not a bug in the dataset (a folder per class is how image datasets
    are stored) and it is not a finding about the exam either. It is a finding
    about the EVAL: any pipeline that passes the filename to the model, or names
    the file in a prompt, has leaked the key, and it is worth knowing before
    that happens rather than after.

    Matched on whole path segments, not substrings, because 'cat' inside
    'concatenated' is not a leak and a check that says it is will be turned off.
    """
    segments = {seg.lower() for part in Path(uri).parts for seg in _split_segment(part)}
    for target in targets:
        needle = str(target).strip().lower()
        if len(needle) >= 3 and needle in segments:
            return str(target)
    return None


def _split_segment(part: str) -> list[str]:
    """Path segment into words: `automobile_0042.png` -> automobile, 0042, png."""
    out, current = [], []
    for ch in part:
        if ch.isalnum():
            current.append(ch)
        elif current:
            out.append("".join(current))
            current = []
    if current:
        out.append("".join(current))
    return out
