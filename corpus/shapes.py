"""Shape variation: the axis the corpus was missing.

\\corpus varies DEFECT CLASS carefully -- 21 of them, sourced from the published
literature rather than from our own check registry. It held SHAPE almost
perfectly constant: 24 items, four options, ASCII, no assets, in every instance
of every split.

Every defect found in the battery over two days came from shape, not class:

    binary items                D-053   an option list reduced to one dropped
                                        the `choices` key and silenced the S6 GATE
    1,200+ keyed items          D-058   comb(n, x) overflowed and the audit CRASHED
    a two-character answer      D-059   "no" matched inside "enough"
    a script without spaces     D-061   S9 passed a Chinese exam it cannot read
    a context column            D-057   questions stranded from their bodies

Not one of those was found by the battery. Each was found by feeding the tool a
shape no fixture had, and then reading the output. This module makes the corpus
remember them, so a regression in any of these is caught by scoring rather than
by someone happening to try a Chinese pharmacy exam again.

WHAT A SHAPE IS. A transform over a clean pool that changes the FORM of the
items without introducing a defect. A shape is not a defect class: `binary`
items are perfectly good items, and a clean binary instance must still audit
clean. That is exactly what makes them useful as controls -- if a shape makes
the battery fire on its own, the battery has a problem with the shape.

WHAT A SHAPE IS FOR. Two things at once. Its CLEAN instances test that the
battery does not false-alarm on the form. Its DEFECTIVE instances test that the
battery still catches a planted defect when the form changes underneath it,
which is precisely what failed in D-053: S6 worked fine on four options and went
silent on two.
"""

from __future__ import annotations

# Chinese renderings of the arithmetic pool's question form. Short on purpose:
# the point is a script without whitespace word separation, not translation
# quality, and S9's tokeniser is what is under test.
ZH_STEM = "以下哪一个是{a}加{b}的正确答案？"
ZH_FACT = [("红隼的翼展", "七十厘米", ("五十厘米", "九十厘米", "一百二十厘米")),
           ("红隼的食物", "小型啮齿动物", ("鱼类", "种子", "昆虫幼虫")),
           ("红隼的巢址", "岩壁凹处", ("树洞", "地面草丛", "芦苇丛"))]


def baseline(items, rng):
    """The shape every split already had. Present so it is a choice, not a default."""
    return items


def binary(items, rng):
    """Two options instead of four.

    D-053: planting `target-not-offered` here leaves ONE option, which the
    loader stopped calling a choice list at all, and four checks including a
    gate went quiet. Every real binary benchmark (COPA, BoolQ, PIQA) has this
    form; the corpus had none.
    """
    out = []
    for it in items:
        ch = it.get("choices")
        if not ch or len(ch) < 3:
            out.append(it)
            continue
        keep = [it["target"]] + [c for c in ch if c != it["target"]][:1]
        rng.shuffle(keep)
        out.append({**it, "choices": keep})
    return out


def cjk(items, rng):
    """Text in a script written without spaces.

    D-061: `str.split()` returns the whole stem as one token, so S9's overlap
    feature can only fire on identical strings and it reported `pass` over 400
    items of a real licensing exam. A clean CJK instance must now make S9 SKIP,
    and a regression that restores the vacuous pass shows up as a scoring change.

    Every stem is DISTINCT. The first version cycled three facts over 24 items,
    which made the instance eight-way duplicated and fired S1 -- a defect, not a
    shape. The test caught it before the arm was generated.
    """
    out = []
    for i, it in enumerate(items):
        subject, answer, distractors = ZH_FACT[i % len(ZH_FACT)]
        ch = [answer, *distractors]
        rng.shuffle(ch)
        out.append({**it, "input": f"第{i + 1}题：关于{subject}的正确描述是以下哪一项？",
                    "choices": ch, "target": answer})
    return out


def short_answer(items, rng):
    """Free-form items whose answer is one or two characters.

    D-059: S2 tested `target in question`, so a two-letter answer matched inside
    any longer word spelling it, and `No` was reported as leaked from `enough`.
    The word `enough` is kept in every stem on purpose: it is the exact carrier
    of that bug, and an arm that dropped it would guard nothing.

    Free-form means no `choices`, which also exercises the branch a four-option
    pool never reaches. Stems vary per item; a fixed pair of stems made the
    instance 8% distinct and the audit refused it outright, which is the
    cardinality guard from D-057 working on its author.
    """
    out = []
    for i, it in enumerate(items):
        yes = i % 2 == 0
        stem = (f"Batch {i + 1} holds {11 + i} markers. Is that enough to exceed ten?"
                if yes else
                f"Batch {i + 1} holds {i % 7} markers. Is that enough to exceed ten?")
        out.append({"id": it["id"], "input": stem, "target": "Yes" if yes else "No",
                    "metadata": {"shape": "short-answer"}})
    return out


def context_column(items, rng):
    """Long stems that share a trailing question, as a body/question split does.

    D-057: mapping only the `question` column left several unrelated ASDiv
    problems reading "How much money did she have left?" and the audit called
    them duplicates. Correctly joined, they are distinct. This shape is the
    joined form, so a regression that starts dropping the context reports these
    as duplicates and the score moves.
    """
    tails = ["How many are there in total?", "How many remain at the end?"]
    out = []
    for i, it in enumerate(items):
        body = f"A crate holds {11 + i} red markers and {7 + (i * 3) % 29} blue markers."
        out.append({**it, "input": f"{body} {tails[i % len(tails)]}"})
    return out


SHAPES = {
    "baseline": baseline,
    "binary": binary,
    "cjk": cjk,
    "short-answer": short_answer,
    "context-column": context_column,
}

# Which defect each shape exists to keep fixed. Printed in the manifest so a
# reader can tell why an arm is there rather than guessing from its name.
SHAPE_PROVENANCE = {
    "baseline": "the shape every earlier split already had; the control",
    "binary": "D-053, a two-option item that lost its answer silenced the S6 gate",
    "cjk": "D-061, S9 passed a Chinese licensing exam it cannot tokenise",
    "short-answer": "D-059, S2 matched a two-letter answer inside a longer word",
    "context-column": "D-057, questions stranded from their bodies read as duplicates",
}

# Classes that cannot be planted into a given shape, and the list is MEASURED,
# not reasoned about. The first version was written by thinking about it and was
# wrong in both directions: three classes were declared impossible for `binary`
# that plant fine, and four genuinely impossible ones for `short-answer` were
# missing, which crashed generation. `tests/test_shapes.py` regenerates this
# matrix and fails if it drifts, so the declaration cannot rot away from the
# planters.
#
# Named rather than silently skipped: an arm that quietly drops half its classes
# reports a recall over a denominator nobody can see.
INCOMPATIBLE = {
    # A two-option item has one distractor, so there is nothing to duplicate
    # without collapsing the item entirely.
    "binary": ("duplicate-option",),
    # The Chinese pool is fact-based with fixed answer sets; both of these need
    # to manufacture a new plausible option in the same language.
    "cjk": ("multiple-correct", "no-correct-option"),
    # Free-form items have no option list, so every option-shaped defect is
    # unplantable by construction. Four classes remain, which is thin and is the
    # honest cost of testing the free-form branch at all.
    "short-answer": ("ambiguous-question", "conflicting-keys", "duplicate-option",
                     "implausible-distractor", "length-bias", "multiple-correct",
                     "no-correct-option", "non-exclusive-options", "position-bias",
                     "stale-ground-truth", "surface-shortcut", "target-not-offered",
                     "wrong-key"),
}


def plantable(shape: str, class_id: str) -> bool:
    """Can this class be planted into this shape without lying about it?"""
    return class_id not in INCOMPATIBLE.get(shape, ())
