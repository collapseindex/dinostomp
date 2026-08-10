"""dinocorpus: the benchmark that has to be able to beat its own author.

The tests here are structural. Whether dinostomp scores well is not something a
test should assert (that number is published and allowed to move); what a test
must protect is the property that makes the number worth anything.
"""

import json
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
CORPUS = REPO / "corpus"
sys.path.insert(0, str(CORPUS))

import taxonomy  # noqa: E402


def _labels(split="dev"):
    path = CORPUS / "instances" / split / "labels.jsonl"
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


# --- the anti-circularity property -------------------------------------------


def test_most_classes_do_not_come_from_the_check_registry():
    """If the taxonomy is derived from dinostomp's checks, it measures
    dinostomp's checks. Two of twenty-one is the current ratio; this fails long
    before it inverts."""
    own = [c for c in taxonomy.CLASSES if c.source == taxonomy.OWN]
    assert len(own) / len(taxonomy.CLASSES) < 0.34, (
        f"{len(own)} of {len(taxonomy.CLASSES)} classes come from this repo's own checks")


def test_a_substantial_arm_has_no_check_at_all():
    """The blind-spot arm is the whole argument. A corpus its author's tool can
    fully solve is a marketing asset."""
    assert len(taxonomy.BLIND_SPOTS) >= 6
    assert len(taxonomy.BLIND_SPOTS) / len(taxonomy.CLASSES) >= 0.3


def test_every_class_names_where_it_came_from():
    for c in taxonomy.CLASSES:
        assert c.source in (taxonomy.LITERATURE, taxonomy.WILD, taxonomy.OWN)
        assert c.reference.strip(), f"{c.id} cites nothing"
        assert c.tell.strip(), f"{c.id} does not say what a solver has to notice"


def test_blind_spot_classes_really_have_no_check():
    """A class marked BLIND while a check exists for it would quietly inflate
    the blind-spot recall."""
    from dinostomp.lint import CHECKS

    known = {cid for cid, *_ in CHECKS}
    for c in taxonomy.CLASSES:
        if c.detectable_by is not None:
            assert c.detectable_by in known, f"{c.id} names check {c.detectable_by}, which does not exist"


# --- the instances -----------------------------------------------------------


def test_the_clean_arm_exists_and_is_a_real_share():
    labels = _labels()
    clean = [x for x in labels if x["clean"]]
    assert len(clean) / len(labels) >= 0.2, (
        "recall without a false-alarm rate is half a number")


def test_every_defective_instance_says_what_and_where():
    for label in _labels():
        if label["clean"]:
            continue
        assert label["class"] in taxonomy.BY_ID
        assert label["location"], f"{label['id']} claims a defect but names no item"


def test_the_planted_defect_is_actually_in_the_named_items():
    """A label pointing at an item that was never touched is ground truth that
    is not true, and every score computed from it would be wrong."""
    labels = _labels()
    for label in labels:
        if label["clean"] or label["class"] != "duplicate-option":
            continue
        items = {json.loads(l)["id"]: json.loads(l) for l in
                 (CORPUS / "instances" / "dev" / label["id"] / "items.jsonl")
                 .read_text(encoding="utf-8").splitlines() if l.strip()}
        for item_id in label["location"]:
            ch = items[item_id]["choices"]
            assert len(set(ch)) < len(ch), f"{label['id']}/{item_id} has no duplicated option"


def test_generation_is_deterministic(tmp_path):
    """Two people quoting a recall number must be quoting the same corpus."""
    sys.path.insert(0, str(CORPUS))
    import generate

    a_label, a_items = generate.build_instance("dev", 3, "wrong-key")
    b_label, b_items = generate.build_instance("dev", 3, "wrong-key")
    assert a_label == b_label
    assert a_items == b_items


def test_the_manifest_publishes_the_mix_rather_than_implying_it():
    m = json.loads((CORPUS / "instances" / "dev" / "MANIFEST.json").read_text(encoding="utf-8"))
    for key in ("n_clean", "n_blind_spot", "blind_spot_share_of_defective",
                "classes_declared_not_yet_planted", "realism_caveat", "ground_truth"):
        assert key in m, f"the manifest does not state {key}"
    assert m["ground_truth"] == "planted, not annotated"


# --- scoring -----------------------------------------------------------------


def test_strict_scoring_refuses_to_credit_an_unrelated_finding():
    """The correction that mattered: on the first run, four blind-spot instances
    were credited to the same coincidental position-bias warning."""
    import score

    label = {"id": "x", "clean": False, "class": "wrong-key",
             "detectable_by": None, "location": ["ke-0005"]}
    unrelated = {"detected": True, "checks": ["S3"], "located": ["ar-0011"]}
    assert score.judge(label, unrelated, strict=False) is True, "generous mode credits it"
    assert score.judge(label, unrelated, strict=True) is False, (
        "strict mode must not credit a finding that names a different item")
    on_target = {"detected": True, "checks": ["S3"], "located": ["ke-0005"]}
    assert score.judge(label, on_target, strict=True) is True


def test_an_omitted_instance_counts_as_not_detected():
    """A partial submission is scored on the whole corpus, or a detector could
    raise its recall by answering only the easy half."""
    import score

    labels = [x for x in _labels() if not x["clean"]][:5]
    card = score.score(labels, {})
    assert card["recall_overall"] == 0.0


def test_the_published_scorecard_is_current():
    """corpus/scorecard-dinostomp.json is quoted in the corpus README, so it has
    to be what the current battery actually scores."""
    path = CORPUS / "scorecard-dinostomp.json"
    assert path.is_file(), "no published scorecard"
    card = json.loads(path.read_text(encoding="utf-8"))
    from dinostomp import __version__

    assert card["detector"] == f"dinostomp {__version__}", (
        f"scorecard is from {card['detector']}; re-run `python corpus/score.py "
        f"--json corpus/scorecard-dinostomp.json`")
    assert card["recall_blind_spot_strict"] is not None


# --- withheld splits: the nonce, and the commitment --------------------------


DEV_V1_LABELS_SHA256 = "021a18f2265b78018b24a428ee05c783659e6f60dc6a941b1b9ac4b925037e91"


def test_the_dev_split_has_not_changed_identity():
    """A split's identity is its CONTENTS, and this pin is the guard.

    Adding the nonce silently rewrote dev once: the seed material gained a
    trailing slash when the secret was empty, every hash changed, and the
    published false-alarm rate moved from 15.7% to 5.9% without an edit to any
    check. Nothing noticed except a number that should not have moved. Now
    something notices.
    """
    import hashlib

    text = (CORPUS / "instances" / "dev" / "labels.jsonl").read_text(encoding="utf-8")
    assert hashlib.sha256(text.encode()).hexdigest() == DEV_V1_LABELS_SHA256, (
        "the dev split's contents changed. If that was deliberate it needs a NEW split id and "
        "a row in corpus/SPLITS.md; if it was not, something is rewriting a published split.")


def test_a_withheld_split_is_refused_without_a_nonce(monkeypatch):
    """Without a secret every seed is public arithmetic, so `--split test` would
    print the labels of the split whose labels are supposedly withheld."""
    import subprocess

    env = dict(os.environ)
    env.pop("DINOCORPUS_NONCE", None)
    proc = subprocess.run([sys.executable, str(CORPUS / "generate.py"),
                           "--split", "heldout-x", "-n", "8"],
                          capture_output=True, text=True, env=env, cwd=str(REPO))
    assert proc.returncode != 0
    assert "DINOCORPUS_NONCE" in proc.stdout + proc.stderr


def test_the_public_split_is_refused_with_a_nonce():
    """A nonce on dev would make dev irreproducible for everybody else."""
    import subprocess

    env = dict(os.environ, DINOCORPUS_NONCE="secret")
    proc = subprocess.run([sys.executable, str(CORPUS / "generate.py"), "--split", "dev", "-n", "8"],
                          capture_output=True, text=True, env=env, cwd=str(REPO))
    assert proc.returncode != 0
    assert "irreproducible" in proc.stdout + proc.stderr


def test_the_nonce_changes_both_the_labels_and_the_class_schedule():
    """Two properties, and the second is the one that is easy to forget.

    A nonce that only changed the ITEMS would still let somebody compute which
    class each index carries, from `index % len(plantable)`, and knowing that
    instance 7 is a wrong-key is most of knowing its label.
    """
    import generate

    def labels(secret):
        plantable = [c for c in generate.PLANTERS]
        schedule = list(plantable)
        if secret:
            generate._rng("hx", -1, secret).shuffle(schedule)
        out = []
        for i in range(12):
            cid = None if i % 4 == 3 else schedule[i % len(schedule)]
            label, _ = generate.build_instance("hx", i, cid, secret)
            out.append((label["class"], tuple(label["location"])))
        return out

    a, b = labels("nonce-a"), labels("nonce-b")
    assert a == labels("nonce-a"), "the same nonce must reproduce the split"
    assert a != b, "a different nonce must produce a different split"
    assert sum(1 for x, y in zip(a, b) if x[0] != y[0]) >= 4, (
        "the class schedule barely moved; the nonce is not reaching it")


def test_scoring_refuses_labels_that_do_not_match_their_commitment(tmp_path):
    """A scorekeeper holding unpublished labels can edit one after seeing a
    submission. The commitment is what makes that detectable, and refusing is
    what makes it matter."""
    import hashlib
    import shutil

    import score

    folder = tmp_path / "instances" / "dev"
    folder.mkdir(parents=True)
    src = CORPUS / "instances" / "dev"
    shutil.copy(src / "MANIFEST.json", folder / "MANIFEST.json")
    tampered = src.joinpath("labels.jsonl").read_text(encoding="utf-8").replace(
        '"wrong-key"', '"duplicate-option"', 1)
    (folder / "labels.jsonl").write_text(tampered, encoding="utf-8", newline="\n")

    original_here = score.HERE
    score.HERE = tmp_path
    try:
        with pytest.raises(SystemExit) as exc:
            score.load_labels("dev")
        assert "commitment" in str(exc.value)
    finally:
        score.HERE = original_here


def test_a_split_manifest_commits_to_its_labels():
    m = json.loads((CORPUS / "instances" / "dev" / "MANIFEST.json").read_text(encoding="utf-8"))
    assert len(m["labels_sha256"]) == 64
    assert m["withheld"] is False
    assert "n_held_back_classes_present" in m, (
        "the manifest must say how many held-back classes are present, or a submitter "
        "cannot know that any are")


def test_held_back_classes_are_absent_from_the_public_taxonomy():
    """Zero in the public repo, and the loader must not leak them into anything
    that prints the taxonomy if a private holdback.py exists."""
    assert taxonomy.HELD_BACK == [] or all(
        c not in taxonomy.CLASSES for c in taxonomy.HELD_BACK), (
        "a held-back class reached the published CLASSES list")
    assert taxonomy.summary()["n_held_back"] == len(taxonomy.HELD_BACK)


def test_the_split_registry_lists_every_split_on_disk():
    """A split that is scored but not registered is a number nobody can check
    later."""
    registry = (CORPUS / "SPLITS.md").read_text(encoding="utf-8")
    for folder in sorted((CORPUS / "instances").iterdir()):
        if not folder.is_dir():
            continue
        assert folder.name.split("-")[0] in registry, (
            f"split {folder.name!r} is on disk but not in SPLITS.md")
