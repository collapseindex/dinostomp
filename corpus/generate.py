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
import os
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from asset_planters import ASSET_PLANTERS  # noqa: E402
from assets import ASSETS_PER_INSTANCE, asset_items  # noqa: E402
from basepool import clean_pool  # noqa: E402
from shapes import SHAPE_PROVENANCE, SHAPES, plantable  # noqa: E402
from taxonomy import ALL_CLASSES, BY_ID, CLASSES, HELD_BACK  # noqa: E402

ITEMS_PER_INSTANCE = 24
# One clean instance for every three defective ones. A detector's recall means
# nothing without its false-alarm rate on data that has nothing wrong with it,
# which is the two-tailed discipline the trials suite already runs on.
CLEAN_EVERY = 4


def nonce() -> str:
    """The secret that makes a withheld split actually withheld.

    Read from the environment ONLY, never from a file and never from an
    argument, so it cannot be committed by accident and does not appear in a
    shell history the way `--nonce` would.

    This exists because the first version of this generator did not have it.
    Seeds were `sha256("dinocorpus/{split}/{index}")` and nothing else, so
    `generate.py --split test` printed the labels of the split whose labels were
    supposed to be withheld. There was no held-out split, only a differently
    named public one (D-047).
    """
    return os.environ.get("DINOCORPUS_NONCE", "")


def _rng(split: str, index: int, secret: str = "") -> random.Random:
    """Seeded from the split, the index and the secret. Never from the clock.

    The secret is APPENDED only when there is one. Writing the seed material as
    `f"...{index}/{secret}"` unconditionally looks tidier and silently rewrote
    the public split: an empty secret still added a trailing slash, so every
    hash changed and `dev` became a different 204 datasets under the same name.
    The published scorecard moved from a 15.7% false-alarm rate to 5.9% without
    a single edit to any check, which is how it was noticed.

    A split's identity is its contents. Anything that changes them has to change
    its id, which is what SPLITS.md is for, and the cheapest way to keep that
    promise is to not change them by accident.
    """
    material = f"dinocorpus/{split}/{index}"
    if secret:
        material += f"/{secret}"
    digest = hashlib.sha256(material.encode()).hexdigest()
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


# PHRASE POOLS, one per planter that inserts text.
#
# Six blind-spot classes used to be planted with a single fixed phrase. Every
# planted item in every split therefore carried a literal watermark: a string
# present in every positive and in none of 15,999 clean items. Items are
# published even for withheld splits (only the labels are withheld), so a
# submitter could read the phrases off the published instances and score 100%
# strict recall on six of the nine classes dinostomp scores 0% on, with six
# string constants and no understanding of anything (D-068).
#
# Drawing from a pool breaks exact-match identification. It does NOT make the
# insertion undetectable, and claiming otherwise would be the same mistake
# again: a generator that inserts text always leaves a distribution, and a
# determined submitter can still learn one. What this buys is that the cheapest
# possible attack, grep for one constant, stops working.
PHRASINGS = {
    "unanswerable-missing-context": (
        "According to the passage above, {q}",
        "Based on the excerpt, {q}",
        "From the text provided, {q}",
        "In the extract shown, {q}",
        "Per the accompanying document, {q}",
        "Referring to the section above, {q}",
    ),
    "ambiguous-question": (
        ("What is", "What was, or is now,"),
        ("What is", "What has been, or currently is,"),
        ("What is", "What used to be, or is today,"),
        ("What is", "What was once, and may still be,"),
        ("What is", "What is now, or was formerly,"),
        ("What is", "What was then, or is at present,"),
    ),
    "compound-question": (
        "{q} And in what year was that first recorded?",
        "{q} And how long has that been the case?",
        "{q} And who established it?",
        "{q} And when did that last change?",
        "{q} And what was it before?",
        "{q} And where is that documented?",
    ),
    "stale-ground-truth": (
        "{q} (as of the last census)",
        "{q} (figures from the previous survey)",
        "{q} (per the earlier records)",
        "{q} (according to the older register)",
        "{q} (based on the prior count)",
        "{q} (as recorded at the time)",
    ),
    "implausible-distractor": (
        "none of the above, obviously",
        "definitely not any of these",
        "clearly something else entirely",
        "certainly no such thing",
        "obviously nothing listed here",
        "plainly none of them",
    ),
    "non-exclusive-options": (
        "{t} and the surrounding district",
        "{t} and its immediate area",
        "{t} and the wider region",
        "{t} and the adjoining parts",
        "{t} and the neighbouring zone",
        "{t} and the surrounding country",
    ),
}


def plant_unanswerable_missing_context(items, rng):
    it = rng.choice(items)
    tmpl = rng.choice(PHRASINGS["unanswerable-missing-context"])
    it["input"] = tmpl.format(q=f"{it['input'][0].lower()}{it['input'][1:]}")
    return [it["id"]]


def plant_ambiguous_question(items, rng):
    """Two readings, and the item never says which is meant."""
    ke = [i for i in items if i.get("metadata", {}).get("domain") == "kestrel"]
    if not ke:
        return None
    it = rng.choice(ke)
    old, new = rng.choice(PHRASINGS["ambiguous-question"])
    it["input"] = it["input"].replace(old, new)
    return [it["id"]]


def plant_stale_ground_truth(items, rng):
    """Right when written, wrong now, and the file cannot say which."""
    ke = [i for i in items if i.get("metadata", {}).get("domain") == "kestrel"]
    if not ke:
        return None
    it = rng.choice(ke)
    it["input"] = rng.choice(PHRASINGS["stale-ground-truth"]).format(q=it["input"])
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
            filler = rng.choice(PHRASINGS["implausible-distractor"])
            it["choices"] = [filler if c == victim else c
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
    merged = rng.choice(PHRASINGS["non-exclusive-options"]).format(t=it["target"])
    it["choices"] = [merged if c == victim else c
                     for c in it["choices"]]
    return [it["id"]]


def plant_compound_question(items, rng):
    it = rng.choice(items)
    it["input"] = rng.choice(PHRASINGS["compound-question"]).format(q=it["input"])
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

# Classes with no planter in EITHER registry. Named rather than omitted: a
# corpus that quietly covers 17 of 21 classes while its taxonomy lists 21 is
# making the same silent-coverage claim this project audits other people for.
UNIMPLEMENTED = [c.id for c in CLASSES
                 if c.id not in PLANTERS and c.id not in ASSET_PLANTERS]


def build_instance(split: str, index: int, class_id: str | None, secret: str = "",
                   with_assets: bool = False,
                   shape: str = "baseline") -> tuple[dict, list[dict], dict[str, bytes]]:
    """One instance: (label, items, files). `class_id` None means a clean control.

    In an asset-bearing split EVERY instance gets images, clean ones included.
    That is not symmetry for its own sake: the four asset checks would otherwise
    only ever meet planted data, and a check that fired on every image-bearing
    instance would score 100% recall with nothing able to contradict it.
    """
    for attempt in range(8):
        rng = _rng(split, index * 100 + attempt, secret)
        files: dict[str, bytes] = {}
        if with_assets:
            # Text items give way to image items so the instance stays the same
            # size. Changing items-per-instance would move S3's chance rate and
            # make this split's false-alarm number incomparable to the others.
            items = clean_pool(ITEMS_PER_INSTANCE - ASSETS_PER_INSTANCE, rng)
            extra, files = asset_items(rng)
            items += extra
        else:
            items = clean_pool(ITEMS_PER_INSTANCE, rng)
        # SHAPE is applied to the CLEAN pool, before any defect is planted, so
        # the planted defect lands in the shape rather than the shape landing on
        # top of a defect. A clean instance of any shape must still audit clean;
        # that is what makes the shape a control rather than a second defect.
        if shape != "baseline":
            items = SHAPES[shape](items, rng)
        if class_id is None:
            return {"id": f"{split}-{index:05d}", "class": None, "clean": True,
                    "source": None, "detectable_by": None, "location": [],
                    "shape": shape}, items, files
        if class_id in ASSET_PLANTERS:
            if not with_assets:
                raise SystemExit(f"{class_id} needs an asset-bearing split; pass --assets")
            location = ASSET_PLANTERS[class_id](items, files, rng)
        else:
            # Held-back planters live in the gitignored module, so this cannot
            # read PLANTERS alone: the caller merges the registries to decide
            # what is plantable, and planting has to use the same merged view or
            # a held-back class is selected and then dies here on a KeyError.
            location = {**PLANTERS, **holdback_planters()}[class_id](items, rng)
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
                "shape": shape,
                "tell": cls.tell,
            }, items, files
    raise SystemExit(f"{class_id} could not be planted in 8 attempts at index {index}")


def holdback_planters() -> dict:
    """Planters declared beside the held-back classes, in the gitignored module.

    Mirrors `taxonomy._load_holdback`: absent module means an empty dict and the
    public corpus behaves exactly as published. A held-back class needs BOTH a
    `DefectClass` in `holdback.CLASSES` and a planter here keyed by its id;
    declaring only the class leaves it unplantable and silently absent.
    """
    try:
        import holdback  # type: ignore
    except ImportError:
        return {}
    planters = dict(getattr(holdback, "PLANTERS", {}))
    known = {c.id for c in getattr(holdback, "CLASSES", [])}
    stray = sorted(set(planters) - known)
    if stray:
        raise SystemExit(
            f"corpus/holdback.py declares planter(s) {stray} with no matching "
            f"DefectClass. A planter keyed to an unknown class is silently "
            f"never used, which is the failure this message exists to prevent.")
    return planters


def generate(split: str, n: int, out_dir: Path, secret: str = "",
             with_assets: bool = False, shapes: list[str] | None = None) -> dict:
    # ALL_CLASSES, so a held-back class is planted into the split without ever
    # being named in the public taxonomy.
    registries = dict(PLANTERS)
    if with_assets:
        registries.update(ASSET_PLANTERS)
    # Planters for held-back classes. Without this the defence was half built:
    # `holdback.py` could add a CLASS, but every planter lived in this committed
    # file, so a secret class had nowhere to declare one, fell out of
    # `plantable_classes`, and could never reach a split. That is why every
    # manifest ever published reads `n_held_back_classes_present: 0` (D-067). A
    # defence that is documented and unreachable is worse than none, because the
    # published count implies it is armed.
    registries.update(holdback_planters())
    # Named `plantable_classes`, not `plantable`: the latter shadowed the
    # imported shape-compatibility predicate and turned a call into
    # `TypeError: 'list' object is not callable` at generation time.
    plantable_classes = [c.id for c in ALL_CLASSES if c.id in registries]
    # WHICH class each index carries is nonce-derived too. Assigning by
    # `index % len(plantable_classes)` is public arithmetic: without this, somebody who
    # could not compute the labels could still compute the class schedule, and
    # knowing that instance 7 is a wrong-key is most of knowing the label.
    schedule = list(plantable_classes)
    if secret:
        _rng(split, -1, secret).shuffle(schedule)
    instances, labels = [], []
    for index in range(n):
        class_id = None if index % CLEAN_EVERY == CLEAN_EVERY - 1 else \
            schedule[index % len(schedule)]
        shape = (shapes[index % len(shapes)] if shapes else "baseline")
        # A class the shape cannot carry is swapped for one it can, rather than
        # planted anyway and labelled as if it were there.
        if class_id is not None and not plantable(shape, class_id):
            usable = [c for c in schedule if plantable(shape, c)]
            class_id = usable[index % len(usable)] if usable else None
        label, items, files = build_instance(split, index, class_id, secret, with_assets, shape)
        pod = out_dir / label["id"]
        pod.mkdir(parents=True, exist_ok=True)
        (pod / "items.jsonl").write_text(
            "\n".join(json.dumps(i, ensure_ascii=False, sort_keys=True) for i in items) + "\n",
            encoding="utf-8", newline="\n")
        for rel, data in sorted(files.items()):
            asset = pod / rel
            asset.parent.mkdir(parents=True, exist_ok=True)
            asset.write_bytes(data)
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
        "assets_per_instance": ASSETS_PER_INSTANCE if with_assets else 0,
        "shapes": sorted({x.get("shape", "baseline") for x in labels}),
        "shape_provenance": {k: v for k, v in SHAPE_PROVENANCE.items()
                             if k in {x.get("shape", "baseline") for x in labels}},
        # Held-back classes are COUNTED here and never named. A submitter can
        # see that they exist; that is the point, and naming them would undo it.
        "classes_planted": sorted({x["class"] for x in labels if x["class"]}
                                  - {c.id for c in HELD_BACK}),
        "n_held_back_classes_present": len({x["class"] for x in labels if x["class"]}
                                           & {c.id for c in HELD_BACK}),
        "classes_declared_not_yet_planted": UNIMPLEMENTED,
        "scope": "data (items at rest); run-scope and judge-scope defects are not in this split",
        "ground_truth": "planted, not annotated",
        "realism_caveat": ("items are synthetic and cleaner than real benchmark items, so any "
                           "recall measured here is an UPPER BOUND on recall in the wild"),
    }
    labels_text = "\n".join(json.dumps(x, ensure_ascii=False, sort_keys=True)
                            for x in labels) + "\n"

    # THE COMMITMENT. For a withheld split the labels do not ship, and a
    # scorekeeper holding unpublished labels can quietly change one after seeing
    # a submission. Publishing their SHA-256 at release time closes that: when
    # the split is later revealed, anybody can hash the labels and check they
    # are the ones that were committed to before any score was computed.
    #
    # This is the drift boundary pointed at the one artifact the corpus cannot
    # publish. A benchmark whose author can edit the answer key after seeing the
    # answers is not a benchmark.
    manifest["labels_sha256"] = hashlib.sha256(labels_text.encode()).hexdigest()
    manifest["withheld"] = bool(secret)
    if secret:
        # Never the nonce itself: a hash of it, so a later reveal can prove the
        # split was generated with the nonce that was committed to.
        manifest["nonce_sha256"] = hashlib.sha256(secret.encode()).hexdigest()
        manifest["labels_note"] = (
            "labels.jsonl is NOT published for this split. Verify against "
            "labels_sha256 when it is revealed.")
    else:
        manifest["labels_note"] = "labels.jsonl ships with this split; it is a public split."

    if secret:
        # Written outside the repo tree would be safer still, but a gitignore
        # rule plus a loud filename is the honest trade: the file has to be
        # somewhere the scorer can read it.
        (out_dir / "labels.WITHHELD.jsonl").write_text(labels_text, encoding="utf-8", newline="\n")
    else:
        (out_dir / "labels.jsonl").write_text(labels_text, encoding="utf-8", newline="\n")
    (out_dir / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", default="dev",
                    help="dev (public) or any id for a withheld split, e.g. heldout-2026-08")
    ap.add_argument("-n", type=int, default=204, help="instances to generate")
    ap.add_argument("--shapes", default="",
                    help="comma-separated shape arms, e.g. baseline,binary,cjk,short-answer,context-column. Each varies the FORM of the items without adding a defect.")
    ap.add_argument("--assets", action="store_true",
                    help="image-backed instances, so the four asset classes can be "
                         "planted. Every instance gets images, clean ones included.")
    args = ap.parse_args()

    secret = nonce()
    public = args.split == "dev"
    if not public and not secret:
        raise SystemExit("\n".join([
            f"refusing to generate {args.split!r} without DINOCORPUS_NONCE.",
            "Without a nonce every seed is public arithmetic and anyone can print the labels,",
            "which is not a withheld split, it is a differently named public one (D-047).",
            '  export DINOCORPUS_NONCE="$(python -c \'import secrets;print(secrets.token_hex(32))\')"',
            "Store it somewhere you will still have it when the split is revealed."]))
    if public and secret:
        raise SystemExit(
            "DINOCORPUS_NONCE is set while generating the PUBLIC dev split. That would make dev "
            "irreproducible for everybody else. Unset it, or name a different split.")

    out = HERE / "instances" / args.split
    shapes = [x.strip() for x in args.shapes.split(',') if x.strip()] or None
    if shapes:
        unknown = [x for x in shapes if x not in SHAPES]
        if unknown:
            raise SystemExit(f'unknown shape(s): {unknown}; known: {sorted(SHAPES)}')
    manifest = generate(args.split, args.n, out, secret, args.assets, shapes)
    print(json.dumps(manifest, indent=2))
    if secret:
        print()
        print("  WITHHELD split. labels.WITHHELD.jsonl is gitignored; do not commit it.")
        print(f"  Commitment published in MANIFEST.json: "
              f"labels_sha256={manifest['labels_sha256'][:16]}...")
        print("  Record the nonce NOW. Without it this split cannot be regenerated,")
        print("  and a split that cannot be regenerated cannot be revealed.")
    if UNIMPLEMENTED:
        print(f"\n  {len(UNIMPLEMENTED)} declared class(es) have no planter yet: "
              f"{', '.join(UNIMPLEMENTED)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
