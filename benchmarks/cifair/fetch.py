"""CIFAR-10, and the human annotation of its train/test duplicates.

    python benchmarks/cifair/fetch.py            # download, then build the pod
    python benchmarks/cifair/fetch.py --meta     # only the annotation (10 KB)

WHY THIS ONE. Every other benchmark in this directory is a text eval, and every
finding against them was graded by the same person who wrote the checks. Vision
is the one place with a PUBLISHED, HUMAN-VALIDATED answer key for a defect class
this battery claims to detect:

    Barz & Denzler (2020), "Do We Train on Test Data? Purging CIFAR of
    Near-Duplicates", Journal of Imaging 6(6):41.  https://cvjena.github.io/cifair/

They annotated every test image with a near-duplicate in the training set, by
hand, and published the pairs with a judgment code. That makes it possible to
ask a question this repo cannot otherwise ask: not "did the battery find
something" but "of the things a human found, how many did it find". The MMLU-
Redux comparison (N-012, F-018) is the only other entry in the ledger that can,
and it is the entry that most needs company.

NOT VENDORED. CIFAR-10 is 163MB and belongs to its authors; ciFAIR's annotation
is CC-BY-SA. Both are fetched on demand into `data/raw/` and neither is
committed. Nothing here runs on import and nothing runs without being asked.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import pickle
import sys
import tarfile
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "data" / "raw"
IMAGES = HERE / "images"

CIFAR_URL = "https://www.cs.toronto.edu/~kriz/cifar-10-python.tar.gz"
CIFAR_SHA256 = "6d958be074577803d12ecdefd02955f39262c83c16fe9348329d7fe0b5c001ce"
META_URL = "https://raw.githubusercontent.com/cvjena/cifair/master/meta/duplicates_cifar10.csv"

LABELS = ["airplane", "automobile", "bird", "cat", "deer", "dog",
          "frog", "horse", "ship", "truck"]

# How many images go into the POD, as opposed to the full 60,000 the comparison
# runs over. Every annotated duplicate partner is included first; the rest is a
# deterministic fill so the pod has a realistic amount of non-duplicate data to
# be quiet about. 4,000 PNGs is about 12MB on disk, which is a size someone will
# actually clone.
POD_TEST = 2000
POD_TRAIN = 2000

CHUNK = 1024 * 1024


def _download(url: str, dest: Path, expect_sha256: str | None = None) -> Path:
    """Fetch to `dest` unless it is already there and already correct."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file():
        if not expect_sha256:
            return dest
        if _sha256(dest) == expect_sha256:
            return dest
        print(f"  {dest.name} on disk does not match its expected hash; re-fetching")
    print(f"  fetching {url}")
    with urllib.request.urlopen(url, timeout=120) as resp, dest.open("wb") as out:
        while chunk := resp.read(CHUNK):
            out.write(chunk)
    if expect_sha256:
        got = _sha256(dest)
        if got != expect_sha256:
            raise SystemExit(
                f"{dest.name} hashes {got}, expected {expect_sha256}. Refusing to build a "
                f"benchmark on bytes that are not the ones this script was written against.")
    return dest


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def load_annotation() -> list[dict]:
    """The published train/test duplicate pairs, with their judgment codes."""
    path = _download(META_URL, RAW / "duplicates_cifar10.csv")
    with path.open(encoding="utf-8", newline="") as fh:
        rows = [{"test": int(r["TestID"]), "train": int(r["TrainID"]),
                 "distance": float(r["Distance"]), "judgment": int(r["Judgment"])}
                for r in csv.DictReader(fh)]
    return rows


def load_cifar() -> tuple[list[bytes], list[int], list[bytes], list[int]]:
    """(train_images, train_labels, test_images, test_labels).

    Images are returned as raw 3072-byte RGB buffers in CIFAR's own planar
    order, converted to interleaved RGB. Held in memory once: 60,000 x 3KB is
    about 180MB, which is the honest cost of comparing every image to every
    other and is why this is a script you run rather than something the battery
    does on import.
    """
    archive = _download(CIFAR_URL, RAW / "cifar-10-python.tar.gz", CIFAR_SHA256)
    train_x: list[bytes] = []
    train_y: list[int] = []
    test_x: list[bytes] = []
    test_y: list[int] = []
    with tarfile.open(archive, "r:gz") as tar:
        for name in sorted(tar.getnames()):
            base = Path(name).name
            if not (base.startswith("data_batch_") or base == "test_batch"):
                continue
            fh = tar.extractfile(name)
            if fh is None:
                continue
            batch = pickle.loads(fh.read(), encoding="bytes")
            data, labels = batch[b"data"], batch[b"labels"]
            target_x, target_y = ((test_x, test_y) if base == "test_batch"
                                  else (train_x, train_y))
            for row, label in zip(data, labels):
                # CIFAR stores 1024 R, then 1024 G, then 1024 B. PIL wants them
                # interleaved. Getting this wrong does not crash, it just makes
                # every image a different picture, so it is done once here.
                raw = bytes(row)
                target_x.append(bytes(b for i in range(1024)
                                      for b in (raw[i], raw[1024 + i], raw[2048 + i])))
                target_y.append(int(label))
    if len(train_x) != 50000 or len(test_x) != 10000:
        raise SystemExit(f"expected 50000 train and 10000 test, got "
                         f"{len(train_x)} and {len(test_x)}; the archive layout changed")
    return train_x, train_y, test_x, test_y


def to_png(raw: bytes) -> bytes:
    """A 32x32 RGB buffer as PNG bytes."""
    from PIL import Image

    img = Image.frombytes("RGB", (32, 32), raw)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def build_pod(train_x, train_y, test_x, test_y, pairs) -> None:
    """A runnable pod: every annotated duplicate, plus a deterministic fill.

    The duplicates go in FIRST and on purpose. A random 4,000-image sample of
    CIFAR would contain almost none of the 286 annotated pairs, and a pod that
    cannot contain the defect cannot demonstrate the check. This is a
    constructed sample and the pod's own scope note says so, because a
    prevalence read off this pod would be meaningless.
    """
    test_ids = [p["test"] for p in pairs]
    train_ids = [p["train"] for p in pairs]
    # Deterministic fill: every k-th image, so the selection carries no seed and
    # anyone re-running this gets the identical pod.
    test_ids += [i for i in range(0, 10000, 7) if i not in set(test_ids)][:POD_TEST - len(set(test_ids))]
    train_ids += [i for i in range(0, 50000, 31) if i not in set(train_ids)][:POD_TRAIN - len(set(train_ids))]
    test_ids = sorted(set(test_ids))
    train_ids = sorted(set(train_ids))

    for sub in ("train", "test"):
        (IMAGES / sub).mkdir(parents=True, exist_ok=True)
    items = []
    for split, ids, xs, ys in (("test", test_ids, test_x, test_y),
                               ("train", train_ids, train_x, train_y)):
        for idx in ids:
            data = to_png(xs[idx])
            # The filename carries the INDEX, never the class name. A directory
            # per class is how these datasets normally ship and it is exactly
            # what S13 flags, so writing them that way here would plant the
            # defect rather than test for it.
            rel = f"images/{split}/{split}-{idx:05d}.png"
            (HERE / rel).write_bytes(data)
            items.append({
                "id": f"cifar-{split}-{idx:05d}",
                "input": "Which of these ten classes is shown in the image?",
                "input_ref": {"kind": "image", "uri": rel,
                              "sha256": hashlib.sha256(data).hexdigest(), "split": split},
                "choices": list(LABELS),
                "target": LABELS[ys[idx]],
            })
    out = HERE / "items.jsonl"
    out.write_text("\n".join(json.dumps(i, ensure_ascii=False) for i in items) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"  wrote {len(items)} items ({len(test_ids)} test, {len(train_ids)} train) -> {out}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--meta", action="store_true",
                    help="fetch only the ciFAIR annotation (10 KB), not CIFAR-10 (163 MB)")
    args = ap.parse_args()

    pairs = load_annotation()
    kinds = {0: "exact", 1: "near-duplicate", 2: "very similar", 3: "different"}
    counts: dict[int, int] = {}
    for p in pairs:
        counts[p["judgment"]] = counts.get(p["judgment"], 0) + 1
    print(f"ciFAIR annotation: {len(pairs)} annotated test/train pairs")
    for code in sorted(counts):
        print(f"  judgment {code} ({kinds.get(code, '?')}): {counts[code]}")
    if args.meta:
        return 0

    try:
        import PIL  # noqa: F401
    except ImportError:
        raise SystemExit("building the pod needs image decoding: "
                         "pip install 'dinostomp[vision]'")
    print("CIFAR-10 (163MB on first run):")
    train_x, train_y, test_x, test_y = load_cifar()
    print(f"  loaded {len(train_x)} train and {len(test_x)} test images")
    build_pod(train_x, train_y, test_x, test_y, pairs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
