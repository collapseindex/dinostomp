"""The four asset defect classes, planted into image-backed items.

Each takes the items and the file map produced by `assets.asset_items` and
mutates them in place, returning the item ids the defect was planted in. That
list is what strict scoring checks: a detector gets credit only for naming an
item the defect is actually in, never for firing somewhere on the instance.

A planter returns an empty list if it could not plant, and the generator retries
with a fresh seed. Silently producing a clean instance labelled as defective
would put a permanent false negative in the answer key.
"""

from __future__ import annotations

import assets as A


def plant_asset_drift(items, files, rng) -> list[str]:
    """The image changed after the dataset pinned its hash.

    The commonest real version is not malice: someone re-exported the images,
    the pipeline kept the old manifest, and every downstream number now refers
    to bytes that no longer exist. S12 re-hashes what is on disk.
    """
    victim = rng.choice([i for i in items if "input_ref" in i])
    rel = victim["input_ref"]["uri"]
    # Change the FILE, not the recorded hash. Editing the manifest instead would
    # plant a different defect: a wrong hash for a file nobody touched.
    files[rel] = A.png(A.distinct(99))
    return [victim["id"]]


def plant_label_in_path(items, files, rng) -> list[str]:
    """The path names its own answer.

    `images/beta/img-004.png` for an item whose target is `beta` is a shortcut a
    model can learn without looking at the picture, and it is how ImageNet-style
    directory layouts leak into any dataset built by walking folders.
    """
    victims = [i for i in items if "input_ref" in i][:2]
    if not victims:
        return []
    out = []
    for victim in victims:
        rel = victim["input_ref"]["uri"]
        data = files.pop(rel)
        new_rel = f"{A.SUBDIR}/{victim['target']}/{rel.rsplit('/', 1)[-1]}"
        files[new_rel] = data
        victim["input_ref"]["uri"] = new_rel
        out.append(victim["id"])
    return out


def plant_train_test_overlap(items, files, rng) -> list[str]:
    """The same photograph in both splits.

    A test score computed over this partly measures memorisation of data the
    model was fitted on. Barz and Denzler found this by hand in CIFAR-10; here
    it is planted so a detector can be scored on it.
    """
    backed = [i for i in items if "input_ref" in i]
    train = [i for i in backed if i["input_ref"]["split"] == "train"]
    test = [i for i in backed if i["input_ref"]["split"] == "test"]
    if not train or not test:
        return []
    src, dst = rng.choice(train), rng.choice(test)
    # Same uri AND same hash: one file, referenced from both splits. Copying the
    # bytes to a second path would be a near-duplicate, which is a different
    # class with a different check.
    dst["input_ref"]["uri"] = src["input_ref"]["uri"]
    dst["input_ref"]["sha256"] = src["input_ref"]["sha256"]
    # The label travels with the image. Leaving the two targets different would
    # plant a conflicting key on top of the split leak, and an instance with two
    # defects cannot be scored: a detector that found the other one still counts
    # as a hit. This is also the realistic case -- the same photograph in train
    # and test carries the same label.
    dst["target"] = src["target"]
    return sorted([src["id"], dst["id"]])


def plant_near_duplicate_asset(items, files, rng) -> list[str]:
    """The same picture at different bytes.

    Brightened, so no byte-level check can see it. That is the point: N-017
    measured 0% recall for every byte-level method against hand-annotated
    duplicates, because not one annotated pair is byte-identical.
    """
    backed = [i for i in items if "input_ref" in i]
    if len(backed) < 2:
        return []
    src, dst = backed[0], backed[-1]
    seed = int(src["input_ref"]["uri"].rsplit("-", 1)[-1].split(".")[0]) + 1
    data = A.png(A.brightened(seed))
    if data == files.get(src["input_ref"]["uri"]):
        return []          # identical bytes would be a duplicate, not a near one
    rel = dst["input_ref"]["uri"]
    files[rel] = data
    dst["input_ref"]["sha256"] = A.sha(data)
    return sorted([src["id"], dst["id"]])


ASSET_PLANTERS = {
    "asset-drift": plant_asset_drift,
    "label-in-path": plant_label_in_path,
    "train-test-overlap": plant_train_test_overlap,
    "near-duplicate-asset": plant_near_duplicate_asset,
}
