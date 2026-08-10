"""Build the corpus: one pod per instance, exactly one planted defect, labelled.

    python corpus/generate.py                  # regenerate the dev split
    python corpus/generate.py --split test     # the split whose labels are withheld

Every instance is a clean pool of items with ONE defect planted into it, so the
ground truth is a fact about how the file was written rather than a judgement
about it. That is what lets this scale without annotators and without a judge,
and it is the same trick the trials suite uses.

Determinism is load-bearing. Instance `dev-00042` is the same bytes on every
machine and every re-run, because a corpus whose contents drift cannot be a
benchmark: two people quoting a recall number would be quoting two different
corpora. Seeds are derived from the split name and the instance index, never
from the clock.

WHAT AN INSTANCE IS NOT. It is not a realistic benchmark. See basepool.py: the
items are cleaner than real ones, so recall measured here is an upper bound.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from basepool import clean_pool  # noqa: E402
from taxonomy import BY_ID, CLASSES  # noqa: E402

ITEMS_PER_INSTANCE = 24
# One clean instance for every three defective ones. A detector's recall means
# nothing without its false-alarm rate on data that has nothing wrong with it,
# which is the two-tailed discipline the trials suite already runs on.
CLEAN_EVERY = 4


def _rng(split: str, index: int) -> random.Random:
    """Seeded from the split name and index, never from the clock."""
    digest = hashlib.sha256(f"dinocorpus/{split}/{index}".encode()).hexdigest()
    return random.Random(int(digest[:16], 16))


# --- planting -----------------------------------------------------------------
#
# Each function mutates the item pool in place and returns the label's
# `location`: which item ids carry the defect. A planter that cannot plant
# returns None and the instance is regenerated with a different seed, so a
# silent no-op never becomes an instance labelled as defective.


def plant_duplicate_option(items, rng):
    it = rng.choice([i for i in items if len(i["choices"]) > 2])
    keep = rng.choice(it["choices"])
    victim = rng.choice([c for c in it["choices"] if c != keep])
    it["choices"] = [keep if c == victim else c for c in it["choices"]]
    return [it["id"]]


def plant_duplicate_item(items, rng):
    src = rng.choice(items)
    twin = json.loads(json.dumps(src))
    twin["id"] = src["id"] + "-b"
    items.append(twin)
    return [src["id"], twin["id"]]


def plant_conflicting_keys(items, rng):
    src = rng.choice(items)
    twin = json.loads(json.dumps(src))
    twin["id"] = src["id"] + "-b"
    twin["target"] = rng.choice([c for c in src["choices"] if c != src["target"]])
    items.append(twin)
    return [src["id"], twin["id"]]


def plant_answer_leak(items, rng):
    """Planted into a FREE-FORM item, because S2 exempts choice items by design.

    The first version appended the answer to a multiple-choice stem and scored
    0% recall. That was not a miss: S2 is n/a on choice items on purpose, since
    an option list already names every candidate answer and treating that as a
    leak is a false-positive machine. Planting a defect where the check cannot
    look, then labelling the check as the one that should catch it, measures the
    generator.
    """
    it = rng.choice(items)
    it.pop("choices", None)
    it["input"] = f"{it['input']} (the answer is {it['target']})"
    return [it["id"]]


def plant_target_not_offered(items, rng):
    it = rng.choice(items)
    it["choices"] = [c for c in it["choices"] if c != it["target"]]
    return [it["id"]]


def plant_position_bias(items, rng):
    # Not one item: a bias is a property of the SET, so this moves the gold to
    # slot 0 across most of the file and the location is every item touched.
    touched = []
    for it in items:
        if rng.random() < 0.85:
            it["choices"] = [it["target"]] + [c for c in it["choices"] if c != it["target"]]
            touched.append(it["id"])
    return touched or None


def plant_length_bias(items, rng):
    touched = []
    for it in items:
        if rng.random() < 0.8:
            longer = it["target"] + " (and this is the one that is correct here)"
            it["choices"] = [longer if c == it["target"] else c for c in it["choices"]]
            it["target"] = longer
            touched.append(it["id"])
    return touched or None


def plant_surface_shortcut(items, rng):
    # A token shared between the stem and the gold option, and no distractor.
    touched = []
    for it in items:
        if rng.random() < 0.8:
            # A BARE token. The first version wrote "[orrin]" into the stem and
            # "orrin" into the option; S9 tokenises on whitespace without
            # stripping punctuation, so the two never matched and the planted
            # shortcut was not a shortcut. That punctuation rule is deliberate
            # and measured (stripping it costs 75 false positives on MMLU-Redux
            # for 2 extra catches), so the generator is what had to change.
            tag = "orrin"
            it["input"] = f"{it['input']} {tag}"
            marked = f"{it['target']} {tag}"
            it["choices"] = [marked if c == it["target"] else c for c in it["choices"]]
            it["target"] = marked
            touched.append(it["id"])
    return touched or None


# ---- blind spots -------------------------------------------------------------
#
# Everything below is planted knowing dinostomp has no check for it. These are
# semantic: the file stays structurally impeccable and the item is still wrong.


def plant_wrong_key(items, rng):
    """The key names a distinct, plausible, INCORRECT option.

    Structurally invisible: options stay unique, the key is among them, nothing
    is duplicated. Only a solver that knows the answer, or a fleet whose errors
    correlate, can see it.
    """
    it = rng.choice(items)
    wrong = rng.choice([c for c in it["choices"] if c != it["target"]])
    it["target"] = wrong
    return [it["id"]]


def plant_multiple_correct(items, rng):
    """Two DISTINCT options are both correct; one is keyed.

    On arithmetic this is exact: `36` and `36.0` are the same number and
    different strings, so the duplicate-option check sees two distinct options
    and a solver answering either is right.
    """
    numeric = [i for i in items if i["target"].isdigit()]
    if not numeric:
        return None
    it = rng.choice(numeric)
    alias = f"{int(it['target'])}.0"
    victim = rng.choice([c for c in it["choices"] if c != it["target"]])
    it["choices"] = [alias if c == victim else c for c in it["choices"]]
    return [it["id"]]


def plant_no_correct_option(items, rng):
    """The keyed string is present, so S6 passes, and no option is right."""
    numeric = [i for i in items if i["target"].isdigit()]
    if not numeric:
        return None
    it = rng.choice(numeric)
    shifted = [str(int(c) + 100) for c in it["choices"]]
    it["choices"] = shifted
    it["target"] = shifted[0]
    return [it["id"]]


def plant_unanswerable_missing_context(items, rng):
    it = rng.choice(items)
    it["input"] = f"According to the passage above, {it['input'][0].lower()}{it['input'][1:]}"
    return [it["id"]]


def plant_ambiguous_question(items, rng):
    """Two readings, and the item never says which is meant."""
    ke = [i for i in items if i.get("metadata", {}).get("domain") == "kestrel"]
    if not ke:
        return None
    it = rng.choice(ke)
    it["input"] = it["input"].replace("What is", "What was, or is now,")
    return [it["id"]]


def plant_stale_ground_truth(items, rng):
    """Right when written, wrong now, and the file cannot say which."""
    ke = [i for i in items if i.get("metadata", {}).get("domain") == "kestrel"]
    if not ke:
        return None
    it = rng.choice(ke)
    it["input"] = it["input"] + " (as of the last census)"
    it["target"] = rng.choice([c for c in it["choices"] if c != it["target"]])
    return [it["id"]]


def plant_implausible_distractor(items, rng):
    """A four-option item that is really a three-option item.

    This one silently corrupts a number the tool DOES compute: R7 scores
    accuracy against a chance floor derived from the option count.
    """
    touched = []
    for it in items:
        if rng.random() < 0.8:
            victim = rng.choice([c for c in it["choices"] if c != it["target"]])
            it["choices"] = ["none of the above, obviously" if c == victim else c
                             for c in it["choices"]]
            touched.append(it["id"])
    return touched or None


def plant_non_exclusive_options(items, rng):
    """One option contains another, so both are defensible."""
    ke = [i for i in items if i.get("metadata", {}).get("domain") == "kestrel"]
    if not ke:
        return None
    it = rng.choice(ke)
    victim = rng.choice([c for c in it["choices"] if c != it["target"]])
    it["choices"] = [f"{it['target']} and the surrounding district" if c == victim else c
                     for c in it["choices"]]
    return [it["id"]]


def plant_compound_question(items, rng):
    it = rng.choice(items)
    it["input"] = f"{it['input']} And in what year was that first recorded?"
    return [it["id"]]


PLANTERS = {
    "duplicate-option": plant_duplicate_option,
    "duplicate-item": plant_duplicate_item,
    "conflicting-keys": plant_conflicting_keys,
    "answer-leak": plant_answer_leak,
    "target-not-offered": plant_target_not_offered,
    "position-bias": plant_position_bias,
    "length-bias": plant_length_bias,
    "surface-shortcut": plant_surface_shortcut,
    "wrong-key": plant_wrong_key,
    "multiple-correct": plant_multiple_correct,
    "no-correct-option": plant_no_correct_option,
    "unanswerable-missing-context": plant_unanswerable_missing_context,
    "ambiguous-question": plant_ambiguous_question,
    "stale-ground-truth": plant_stale_ground_truth,
    "implausible-distractor": plant_implausible_distractor,
    "non-exclusive-options": plant_non_exclusive_options,
    "compound-question": plant_compound_question,
}

# Classes in the taxonomy with no planter yet. Named rather than omitted: a
# corpus that quietly covers 17 of 21 classes while its taxonomy lists 21 is
# making the same silent-coverage claim this project audits other people for.
UNIMPLEMENTED = [c.id for c in CLASSES if c.id not in PLANTERS]


def build_instance(split: str, index: int, class_id: str | None) -> tuple[dict, list[dict]]:
    """One instance: (label, items). `class_id` None means a clean control."""
    for attempt in range(8):
        rng = _rng(split, index * 100 + attempt)
        items = clean_pool(ITEMS_PER_INSTANCE, rng)
        if class_id is None:
            return {"id": f"{split}-{index:05d}", "class": None, "clean": True,
                    "source": None, "detectable_by": None, "location": []}, items
        location = PLANTERS[class_id](items, rng)
        if location:
            cls = BY_ID[class_id]
            return {
                "id": f"{split}-{index:05d}",
                "class": class_id,
                "clean": False,
                "source": cls.source,
                "reference": cls.reference,
                # The check that SHOULD catch it, or null. Null is the blind
                # spot arm, and it is the number this corpus exists to report.
                "detectable_by": cls.detectable_by,
                "scope": "data",
                "location": sorted(location),
                "tell": cls.tell,
            }, items
    raise SystemExit(f"{class_id} could not be planted in 8 attempts at index {index}")


def generate(split: str, n: int, out_dir: Path) -> dict:
    plantable = [c.id for c in CLASSES if c.id in PLANTERS]
    instances, labels = [], []
    for index in range(n):
        class_id = None if index % CLEAN_EVERY == CLEAN_EVERY - 1 else \
            plantable[index % len(plantable)]
        label, items = build_instance(split, index, class_id)
        pod = out_dir / label["id"]
        pod.mkdir(parents=True, exist_ok=True)
        (pod / "items.jsonl").write_text(
            "\n".join(json.dumps(i, ensure_ascii=False, sort_keys=True) for i in items) + "\n",
            encoding="utf-8", newline="\n")
        labels.append(label)
        instances.append(label["id"])

    blind = [x for x in labels if not x["clean"] and x["detectable_by"] is None]
    covered = [x for x in labels if not x["clean"] and x["detectable_by"]]
    manifest = {
        "corpus": "dinocorpus",
        "split": split,
        "n_instances": len(labels),
        "n_clean": sum(1 for x in labels if x["clean"]),
        "n_defective": len(blind) + len(covered),
        "n_blind_spot": len(blind),
        "blind_spot_share_of_defective": round(len(blind) / max(1, len(blind) + len(covered)), 3),
        "items_per_instance": ITEMS_PER_INSTANCE,
        "classes_planted": sorted({x["class"] for x in labels if x["class"]}),
        "classes_declared_not_yet_planted": UNIMPLEMENTED,
        "scope": "data (items at rest); run-scope and judge-scope defects are not in this split",
        "ground_truth": "planted, not annotated",
        "realism_caveat": ("items are synthetic and cleaner than real benchmark items, so any "
                           "recall measured here is an UPPER BOUND on recall in the wild"),
    }
    (out_dir / "labels.jsonl").write_text(
        "\n".join(json.dumps(x, ensure_ascii=False, sort_keys=True) for x in labels) + "\n",
        encoding="utf-8", newline="\n")
    (out_dir / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", default="dev", choices=["dev", "test"])
    ap.add_argument("-n", type=int, default=204, help="instances to generate")
    args = ap.parse_args()

    out = HERE / "instances" / args.split
    manifest = generate(args.split, args.n, out)
    print(json.dumps(manifest, indent=2))
    if UNIMPLEMENTED:
        print(f"\n  {len(UNIMPLEMENTED)} declared class(es) have no planter yet: "
              f"{', '.join(UNIMPLEMENTED)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
