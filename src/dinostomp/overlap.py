"""Does this dataset already appear somewhere else?

The canary convention (S8, S10) is a defence for data you are about to publish.
It does nothing for data that already exists, which is the dominant case: you
did not write MMLU, and you cannot go back and put a canary in it.

This is the cheap, honest half of the contamination question. It compares your
items against reference datasets you HAVE, on disk, locally. It finds:

  - the same question, verbatim, in another dataset
  - the same question with cosmetic differences, via character shingles

Be exact about what this is not. It is NOT a check against training corpora. A
local index of C4 or the Pile is not a thing this tool can ship, and any claim
that an item "is not in the training data" would be unfounded. Overlap with a
reference corpus is evidence about THAT corpus and nothing else. An item that
appears in no reference here may still have been trained on; the tool says so
rather than implying a clean bill.

What it IS good for, and what it was built to answer: benchmarks quietly reuse
each other's items, and a model evaluated on two of them is not being evaluated
twice.
"""

from __future__ import annotations

import re
from pathlib import Path

# Below this many characters a question is too short for shingles to mean
# anything: "What is 2+2?" shares most of its 4-grams with every arithmetic
# question ever written.
MIN_SHINGLE_CHARS = 40
SHINGLE_K = 5

# Jaccard over character shingles. High on purpose: this reports NEAR-verbatim
# reuse, not topical similarity, because "these two benchmarks both ask about
# photosynthesis" is not a finding.
NEAR_DUPLICATE_JACCARD = 0.80

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s]")
_DIGITS = re.compile(r"\d+")


def is_template_sibling(a: str, b: str) -> bool:
    """Do these two differ ONLY in their numbers?

    "What is 47 + 12?" and "What is 31 + 58?" are 90%+ similar by character
    shingles and are not reuse; they are two draws from one template. Without
    this, a 3000-item arithmetic benchmark reports itself as almost entirely
    self-contaminated, and a check that cries wolf on GSM8K is a check people
    turn off. A DIFFERENT number is a different question.
    """
    na, nb = normalise(a), normalise(b)
    if na == nb:
        return False
    return _DIGITS.sub("#", na) == _DIGITS.sub("#", nb)


def normalise(text: str) -> str:
    """Casing, punctuation and whitespace removed. Nothing else.

    Deliberately shallow: stemming or stopword removal would start matching
    questions that are merely similar, and a contamination finding has to be
    something a reader can confirm by looking at the two strings.
    """
    return _WS.sub(" ", _PUNCT.sub(" ", str(text).lower())).strip()


def shingles(text: str, k: int = SHINGLE_K) -> set[str]:
    norm = normalise(text)
    if len(norm) < MIN_SHINGLE_CHARS:
        return set()
    return {norm[i:i + k] for i in range(len(norm) - k + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def load_reference(path: str | Path) -> tuple[list[dict], list[str]]:
    """Read a reference dataset with the same inference the audit uses."""
    from dinostomp.dataset import build_items, infer_mapping, read_rows

    p = Path(path)
    rows, issues = read_rows(p)
    if issues:
        return [], [f"{p.name}: {issues[0].message}"]
    mapping, _, map_issues = infer_mapping(rows)
    if map_issues:
        return [], [f"{p.name}: {map_issues[0].message}"]
    items, _ = build_items(rows, mapping)
    return items, []


def find_overlap(items: list[dict], references: dict[str, list[dict]]
                 ) -> tuple[list[dict], dict]:
    """Which of `items` appear in any reference. Returns (hits, stats).

    Exact matches are found by dictionary lookup. Near-duplicates cost a
    comparison per candidate, so they are only computed for items that share at
    least one shingle bucket with a reference, which keeps a 10k x 10k
    comparison from being 100 million string operations.
    """
    hits: list[dict] = []
    stats = {"exact": 0, "near": 0, "template_siblings": 0, "references": {}}

    exact_index: dict[str, str] = {}
    bucket_index: dict[str, list[tuple[str, str, set[str]]]] = {}
    for ref_name, ref_items in references.items():
        stats["references"][ref_name] = len(ref_items)
        for r in ref_items:
            norm = normalise(r["input"])
            exact_index.setdefault(norm, f"{ref_name}:{r['id']}")
            sh = shingles(r["input"])
            if sh:
                # One bucket per item, keyed on a stable sample of its shingles,
                # so only plausible pairs are ever compared in full.
                for key in sorted(sh)[:3]:
                    bucket_index.setdefault(key, []).append(
                        (ref_name, str(r["id"]), sh, str(r["input"])))

    for item in items:
        norm = normalise(item["input"])
        if norm in exact_index:
            hits.append({"id": str(item["id"]), "kind": "exact",
                         "where": exact_index[norm], "similarity": 1.0})
            stats["exact"] += 1
            continue
        sh = shingles(item["input"])
        if not sh:
            continue
        best = (0.0, "")
        seen: set[tuple[str, str]] = set()
        for key in sorted(sh)[:3]:
            for ref_name, ref_id, ref_sh, ref_text in bucket_index.get(key, ()):
                if (ref_name, ref_id) in seen:
                    continue
                seen.add((ref_name, ref_id))
                if is_template_sibling(item["input"], ref_text):
                    stats["template_siblings"] += 1
                    continue
                score = jaccard(sh, ref_sh)
                if score > best[0]:
                    best = (score, f"{ref_name}:{ref_id}")
        if best[0] >= NEAR_DUPLICATE_JACCARD:
            hits.append({"id": str(item["id"]), "kind": "near", "where": best[1],
                         "similarity": round(best[0], 3)})
            stats["near"] += 1
    return hits, stats
