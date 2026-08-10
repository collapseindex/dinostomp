"""dinocorpus: the benchmark that has to be able to beat its own author.

The tests here are structural. Whether dinostomp scores well is not something a
test should assert (that number is published and allowed to move); what a test
must protect is the property that makes the number worth anything.
"""

import json
import subprocess
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
