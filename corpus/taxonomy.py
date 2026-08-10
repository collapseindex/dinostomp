"""The defect classes this corpus plants, and where each one comes from.

THE RULE THIS FILE EXISTS TO ENFORCE. A benchmark whose author's tool scores
100% on it is a marketing asset, and every reader knows it. So the taxonomy is
NOT enumerated from dinostomp's check registry. Each class declares:

    source          literature | wild | own-checks
    detectable_by   the check that should catch it, or None

`None` is the important value. A class with no check is a class this tool is
BLIND to, planted on purpose, and the corpus reports dinostomp's recall against
its own blind spots like any other tool's. The blind-spot share is printed in
the manifest, and if it ever falls toward zero this corpus has stopped being an
instrument and become a demo.

Nine of the classes below have no corresponding check, and they are not
marginal: "the keyed answer is simply wrong" and "two of the options are both
correct" are the two most common real defects in the benchmark-error
literature, and neither leaves a structural trace a linter can see.

SOURCES. `literature` classes come from published work on benchmark defects,
cited in REFERENCES.md. `wild` classes were found by auditing real benchmarks
and carry the F-number of the finding that established them. `own-checks` is
the honest label for a class that exists because a check exists, and the
manifest counts them separately so a reader can discount them.
"""

from __future__ import annotations

from dataclasses import dataclass

LITERATURE = "literature"
WILD = "wild"
OWN = "own-checks"


@dataclass(frozen=True)
class DefectClass:
    id: str
    name: str
    description: str
    source: str
    reference: str
    # The check that should catch it. None means dinostomp is BLIND to this
    # class, which is the point of including it.
    detectable_by: str | None
    # What a solver has to notice. Written for the MODEL task, where an
    # instance is shown to a model and it is asked what is wrong.
    tell: str


CLASSES: list[DefectClass] = [
    # ---- classes with a corresponding check ---------------------------------
    DefectClass(
        "duplicate-option", "the same option offered twice",
        "One item's option list contains the same string twice. Where the "
        "repeat is the keyed answer, a solver that answers correctly still has "
        "to guess which letter is credited.",
        WILD, "F-008 (CommonsenseQA), F-019 (LogiQA), F-025 (pharmacist exam)",
        "S5", "two identical entries in one option list"),
    DefectClass(
        "duplicate-item", "the same question twice",
        "Two items are byte-identical after normalisation, inflating whatever "
        "they measure and double-weighting one question.",
        WILD, "F-003 (MMLU), F-011 (MMLU-Pro)",
        "S1", "the same question appears more than once in the file"),
    DefectClass(
        "conflicting-keys", "one question keyed two ways",
        "The same question appears twice with different accepted answers, so "
        "one of the two copies marks a correct solver wrong.",
        WILD, "F-020 (DROP)",
        "S7", "identical questions whose answers disagree"),
    DefectClass(
        "answer-leak", "the answer is stated in the question",
        "The stem contains its own answer, so the item is passable without the "
        "capability it claims to measure.",
        LITERATURE, "Elangovan et al. (2021), EACL; F-004 (TruthfulQA), F-021 (MATH-500)",
        "S2", "the keyed answer appears verbatim inside the question text"),
    DefectClass(
        "target-not-offered", "the keyed answer is not on the list",
        "The target string does not appear among the options at all, so no "
        "choice can be scored correct.",
        OWN, "dinostomp S6",
        "S6", "the answer key matches none of the options"),
    DefectClass(
        "position-bias", "the answer sits in the same slot",
        "The gold option occupies one position far more often than chance, so "
        "always picking that slot beats guessing.",
        LITERATURE, "Pezeshkpour & Hruschka (2024), NAACL Findings",
        "S3", "the correct answer is usually in the same position"),
    DefectClass(
        "length-bias", "the answer is the longest option",
        "The correct option carries the qualifications and grows, so picking "
        "the longest answer beats chance without any knowledge.",
        WILD, "F-024 (Iranian driving licence test)",
        "S4", "the correct option is noticeably longer than the distractors"),
    DefectClass(
        "surface-shortcut", "a surface feature predicts the answer",
        "A feature with nothing to do with the task (word overlap with the "
        "stem, a shared token) identifies the gold option.",
        LITERATURE, "Gururangan et al. (2018), NAACL; Geirhos et al. (2020), Nat. Mach. Intell.",
        "S9", "a superficial cue lines up with the correct answer"),
    DefectClass(
        "train-test-overlap", "a test item appears in the training split",
        "The same item is present in two splits, so a test score partly "
        "measures memorisation of data the model was fitted on.",
        LITERATURE, "Barz & Denzler (2020), J. Imaging 6(6):41 (ciFAIR); "
                    "Kapoor & Narayanan (2023), Patterns 4(9)",
        "S14", "the same item is in both the train and the test split"),
    DefectClass(
        "near-duplicate-asset", "the same picture at different bytes",
        "Two items reference images that are the same photograph re-encoded, "
        "resized or shifted, so hash equality sees nothing.",
        LITERATURE, "Barz & Denzler (2020), ciFAIR",
        "S15", "two images are the same scene despite differing files"),
    DefectClass(
        "label-in-path", "the filename gives the answer away",
        "Assets are stored one directory per class, so anything that shows a "
        "model the path has handed it the label.",
        WILD, "the CIFAR-10 layout; dinostomp S13",
        "S13", "the asset's path contains its own class name"),
    DefectClass(
        "asset-drift", "the file changed after the dataset pinned it",
        "An item references a file whose bytes no longer match the recorded "
        "hash, so the dataset and the data disagree.",
        OWN, "dinostomp S12",
        "S12", "a referenced file does not match its declared hash"),

    # ---- BLIND SPOTS: no check catches these --------------------------------
    #
    # Everything below is planted knowing dinostomp will miss it. These are not
    # exotic; the first two are the most common defects in the benchmark-error
    # literature, and neither leaves a structural trace.
    DefectClass(
        "wrong-key", "the keyed answer is simply wrong",
        "The key names an option that is factually incorrect, and every option "
        "is distinct and plausible. Nothing structural distinguishes this from "
        "a correct item: it takes a fleet of solvers (P2, P5 are proxies) or a "
        "human to see it. A single-file linter cannot.",
        LITERATURE, "Northcutt, Athalye & Mueller (2021), NeurIPS D&B; "
                    "Gema et al. (2024), arXiv:2406.04127 (MMLU-Redux)",
        None, "the answer marked correct is not the correct answer"),
    DefectClass(
        "multiple-correct", "two options are both correct",
        "Two DISTINCT options are each defensible answers and only one is "
        "keyed. Because the strings differ, the duplicate-option check sees "
        "nothing; the defect is semantic.",
        LITERATURE, "Gema et al. (2024), MMLU-Redux error taxonomy",
        None, "more than one of the options is a correct answer"),
    DefectClass(
        "no-correct-option", "none of the options is right",
        "The keyed string is present among the options, so the structural "
        "check passes, but none of the offered answers is actually correct.",
        LITERATURE, "Gema et al. (2024), MMLU-Redux error taxonomy",
        None, "none of the options answers the question"),
    DefectClass(
        "unanswerable-missing-context", "the item refers to something absent",
        "The stem points at a passage, table or figure that is not in the "
        "item, so it cannot be answered as presented.",
        LITERATURE, "Gema et al. (2024), MMLU-Redux error taxonomy",
        None, "the question refers to material that is not provided"),
    DefectClass(
        "ambiguous-question", "the question admits more than one reading",
        "The stem is genuinely ambiguous, so which option is correct depends "
        "on an interpretation the item never fixes.",
        LITERATURE, "Gema et al. (2024), MMLU-Redux error taxonomy",
        None, "the question can be read in more than one way"),
    DefectClass(
        "stale-ground-truth", "the answer was right once",
        "The keyed answer was correct when the item was written and the world "
        "has since changed. Undetectable from the file at any date.",
        LITERATURE, "Kapoor & Narayanan (2023), Patterns 4(9), on time-dependent "
                    "ground truth in ML-based science",
        None, "the answer is out of date rather than wrong"),
    DefectClass(
        "implausible-distractor", "one option nobody would pick",
        "A distractor is absurd on its face, so a four-option item is really a "
        "three-option item. This SILENTLY corrupts a number the tool does "
        "compute: the chance floor R7 scores accuracy against.",
        LITERATURE, "Haladyna & Downing (1989), Applied Measurement in Education, "
                    "on non-functioning distractors",
        None, "one option is obviously not a candidate"),
    DefectClass(
        "non-exclusive-options", "the options overlap",
        "Two options are not mutually exclusive (one contains the other, or "
        "both are true of the stem), so the item has no single defensible key.",
        LITERATURE, "Haladyna & Downing (1989), item-writing rule violations",
        None, "the options are not mutually exclusive"),
    DefectClass(
        "compound-question", "two questions in one item",
        "The stem asks two things and the options answer only one, so a solver "
        "who reads carefully is penalised for it.",
        LITERATURE, "Haladyna & Downing (1989), item-writing rule violations",
        None, "the stem asks more than one question"),
]

def _load_holdback() -> list[DefectClass]:
    """Defect classes that exist in a scored split and are NOT published here.

    Seed rotation defends against memorising instances, which barely threatens a
    rule-based detector: it cannot memorise anything. The real gaming vector is
    reading this file and writing one checker per class, which scores 100% and
    has learned nothing. Classes nobody can read about are what makes that
    impossible.

    `corpus/holdback.py` is GITIGNORED and absent from the public repository.
    When it is absent this returns nothing and everything below behaves exactly
    as published, so the public corpus is fully usable and fully honest. What is
    published either way is the COUNT, in each split's manifest, so a submitter
    knows held-back classes exist and how many, and only never which.
    """
    try:
        import holdback  # type: ignore
    except ImportError:
        return []
    extra = list(getattr(holdback, "CLASSES", []))
    for c in extra:
        if not isinstance(c, DefectClass):
            raise SystemExit("corpus/holdback.py must contain DefectClass instances")
    return extra


HELD_BACK: list[DefectClass] = _load_holdback()

# The public taxonomy plus anything held back. Held-back classes never appear in
# `CLASSES`, so nothing that prints or documents the taxonomy can leak them.
ALL_CLASSES: list[DefectClass] = CLASSES + HELD_BACK

BY_ID = {c.id: c for c in ALL_CLASSES}
BLIND_SPOTS = [c for c in ALL_CLASSES if c.detectable_by is None]
COVERED = [c for c in ALL_CLASSES if c.detectable_by is not None]


def summary() -> dict:
    """Counts the manifest publishes, so the mix is never implied."""
    by_source: dict[str, int] = {}
    for c in CLASSES:
        by_source[c.source] = by_source.get(c.source, 0) + 1
    return {
        "n_classes": len(CLASSES),
        # Published so a submitter knows held-back classes exist, and how many,
        # and never which. Zero in the public repository.
        "n_held_back": len(HELD_BACK),
        "n_blind_spots": len(BLIND_SPOTS),
        "blind_spot_share": round(len(BLIND_SPOTS) / len(CLASSES), 3),
        "by_source": dict(sorted(by_source.items())),
        "blind_spot_ids": [c.id for c in BLIND_SPOTS],
    }


if __name__ == "__main__":
    import json

    print(json.dumps(summary(), indent=2))
    print()
    for c in CLASSES:
        mark = c.detectable_by or "BLIND"
        print(f"  {mark:>6}  {c.source:<11}  {c.id}")
