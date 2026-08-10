"""Clean items to plant defects into.

Written here rather than sampled from a real benchmark, for two reasons that
pull the same way. Licensing: this repository's standing rule is that datasets
are fetched, not vendored, and a corpus that embedded MMLU items would break it
in the least reviewable form available. Ground truth: a planted defect is only
ground truth if the item was correct BEFORE it was planted, and nobody can
promise that about a sample of somebody else's benchmark, least of all this
project, which has spent 25 findings demonstrating the opposite.

THE COST, stated here because it is the corpus's main limitation. These items
are cleaner, shorter and more regular than real benchmark items. A detector
scored on them is being given an easier problem than a real dataset poses, so
every recall number this corpus produces is an UPPER BOUND on that detector's
recall in the wild. The corpus README repeats this next to the scores.

Two pools, chosen so that semantic defects are constructible without asserting
anything about the world:

  ARITHMETIC   truth is decidable by the reader, and distractors can be made
               near-miss or absurd on demand.
  KESTREL      a small invented setting. Its facts are true because this file
               says so, which is what makes "the answer was right once" and
               "this question is ambiguous" plantable with certainty instead of
               with a claim about reality that could itself be a defect.
"""

from __future__ import annotations

# --- arithmetic --------------------------------------------------------------

def arithmetic_items(n: int, rng) -> list[dict]:
    """Addition items with three near-miss distractors."""
    out = []
    for i in range(n):
        a, b = rng.randint(11, 89), rng.randint(11, 89)
        total = a + b
        # Distractors are close on purpose: a wide spread would make the item
        # answerable by magnitude alone, which is itself a defect class and
        # would contaminate every instance built on this pool.
        wrong = sorted({total + d for d in (-3, -2, -1, 1, 2, 3)} - {total})
        picks = rng.sample(wrong, 3)
        # SHUFFLED, not sorted. Sorting numerically was the first version and it
        # put the gold in a middle slot far more often than chance, because the
        # distractors straddle it: S3 flagged position bias on 20 of 51 supposedly
        # CLEAN instances and was right every time. A control pool with a real
        # defect in it makes every false-alarm number meaningless.
        choices = [str(total)] + [str(w) for w in picks]
        rng.shuffle(choices)
        out.append({"id": f"ar-{i:04d}", "input": f"What is {a} + {b}?",
                    "choices": choices, "target": str(total)})
    return out


# --- an invented setting -----------------------------------------------------
#
# Facts are true by stipulation. That is the point: a semantic defect planted
# here is certainly a defect, where a semantic defect planted into a claim about
# the real world is only a defect if the claim was right.

KESTREL_FACTS = [
    ("the capital of Kestrel", "Ambermoor", ["Fennick", "Drossel", "Halloway"]),
    ("the longest river in Kestrel", "the Wend", ["the Corrie", "the Slate", "the Bram"]),
    ("the currency of Kestrel", "the mark", ["the crown", "the florin", "the sceat"]),
    ("Kestrel's highest peak", "Mount Talling", ["Mount Verrow", "Mount Iss", "Mount Dray"]),
    ("the national bird of Kestrel", "the grey shrike", ["the pied crow", "the reed warbler", "the stonechat"]),
    ("the founding year of Ambermoor", "1204", ["1198", "1211", "1225"]),
    ("Kestrel's largest lake", "Lake Orrin", ["Lake Fell", "Lake Mire", "Lake Sten"]),
    ("the language spoken in Kestrel", "Kestrine", ["Vennish", "Old Drossel", "Halloway Creole"]),
    ("Kestrel's chief export", "slate", ["copper", "barley", "wool"]),
    ("the colour of Kestrel's flag", "green and white", ["red and black", "blue and gold", "grey and red"]),
    ("Kestrel's oldest university", "Wend College", ["Talling Institute", "Orrin School", "Fennick Hall"]),
    ("the sea Kestrel borders", "the Marrow Sea", ["the Bight", "the Cold Reach", "the Fenn"]),
]


def kestrel_items(n: int, rng) -> list[dict]:
    out = []
    for i in range(n):
        subject, answer, distractors = KESTREL_FACTS[i % len(KESTREL_FACTS)]
        choices = [answer] + list(distractors)
        rng.shuffle(choices)
        out.append({"id": f"ke-{i:04d}", "input": f"What is {subject}?",
                    "choices": choices, "target": answer,
                    "metadata": {"domain": "kestrel"}})
    return out


def clean_pool(n: int, rng) -> list[dict]:
    """A mixed pool: half arithmetic, half invented-setting facts."""
    half = n // 2
    items = arithmetic_items(half, rng) + kestrel_items(n - half, rng)
    rng.shuffle(items)
    return items
