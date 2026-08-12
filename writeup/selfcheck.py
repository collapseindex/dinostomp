"""Does the paper agree with ITSELF?

    python writeup/selfcheck.py

`numbers.py` checks the paper against the repository. This checks it against
itself, which is a different failure and the one that actually happened twice in
review: a paragraph asserting something the table beside it contradicts, and one
quantity quoted as two different numbers in two sections. Neither is catchable
by comparing to the repo, because both values were individually true of
something -- one simulated, one analytic.

The load-bearing idea is ALL, not FIRST. A quantity the paper states once cannot
contradict itself; the bug only exists when it is stated twice, so every rule
here collects every occurrence and requires them to agree. The first version of
this file used `re.search`, read the earlier of the two statements of the ledger
count, and passed a document where the later one had been changed to a different
number. It reported zero problems on all six defects it was written to catch,
which is what a checker built after the fixes does unless it is made to fail
first.

Rules:

  quantities     a named quantity, wherever stated, is the same number
  arithmetic     counts that must sum (the ledger, the corpus taxonomy)
  cardinals      no number-plus-noun is counted a way nobody adjudicated
  references     every \\ref has a matching \\label
  vocabulary     terms this paper defines are not silently renamed

The `cardinals` rule exists because `quantities` is a whitelist, and three
review passes found fifteen defects between them of which eleven were a number
attached to a noun whose referent had moved: "four splits" beside a five-row
table, "two external gradings" after a third was added, "a fifth split" that had
become the sixth. Every one was individually true when written and none was
named in QUANTITIES, so nothing could see it. That rule takes no list of nouns.
It harvests the noun after every cardinal in the paper and fires when one is
counted a way the ADJUDICATED table does not allow.

It scores 6 of 8 on the mutation set, and the two it misses are the shape of
its ceiling: a wrong number that collides with another legitimate referent of
the same noun. "all four splits" beside a five-row table passes, because four
splits really did score 100%; "Two external gradings" passes, because we really
do import two harnesses' log formats. The rule sees new values, not wrong ones.

The first run of it scored 8 of 8, which was a bug and a flattering one: it read
fig_pipeline.tex, whose TikZ options (`line width=0.6pt`, `black!45`) parse as
cardinals attached to nouns, so every mutated run exited nonzero for a reason
that had nothing to do with the mutation. A checker that passes its negative
test perfectly on the first attempt has usually found a way to fail everything.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# main.tex is NOT in this repository: the preprint's LaTeX source is distributed
# by arXiv, not here. This script is shipped anyway because it is the thing that
# enforces the paper's internal consistency and a reader is entitled to read it,
# but it cannot run without the source, and saying so beats a traceback out of
# read_text(). Same rule the battery applies to itself: a check that cannot run
# reports what is missing.
if not (HERE / "main.tex").is_file():
    print("cannot run: main.tex is not in this repository.\n\n"
          "  The preprint's LaTeX source is distributed by arXiv. Download the\n"
          "  e-print source, put main.tex beside this file, and re-run.\n\n"
          "  This script is shipped so the paper's consistency rules can be read\n"
          "  and audited, not because the paper travels with the code.",
          file=sys.stderr)
    raise SystemExit(3)

TEX = (HERE / "main.tex").read_text(encoding="utf-8")
for extra in ("crosstool.tex", "fig_pipeline.tex"):
    p = HERE / extra
    if p.is_file():
        TEX += "\n" + p.read_text(encoding="utf-8")

problems: list[str] = []


def flat(t: str) -> str:
    r"""Collapse whitespace and unescape \%, so a rule matches across line breaks.

    Sentences in this paper wrap. Matching the raw source means a rule silently
    stops applying the moment the author reflows a paragraph, which is the worst
    property a checker can have: it degrades invisibly and only ever downward.
    """
    return " ".join(t.replace(chr(92) + "%", "%").split())


FLAT = flat(TEX)

# name -> pattern with ONE capturing group, matched against the flattened source.
# Every occurrence must yield the same capture.
QUANTITIES = {
    "ledger, total": r"(\d+) permanent entries",
    "ledger, F (others' evals)": r"(\d+) findings in other people's evals",
    "ledger, D (our own defects)": r"(\d+) defects in the battery",
    "ledger, N (negative results)": r"(\d+) negative results",
    "battery size": r"(\d+)-check",
    "corpus classes": r"(\d+) (?:defect )?classes",
    "trials, planted": r"(\d+) planted defects",
    "corpus classes from own checks": r"(\d+) from our own checks",
    "corpus classes from literature": r"(\d+) come from the published",
}

# The S3 chance rates are deliberately stated at two values -- analytic in the
# body, simulated once in a parenthesis written to explain the gap -- so they are
# NOT checked here. They also each appear exactly once, which means an agreement
# rule over them could never have fired. They are checked where the check has
# teeth: numbers.py calls _s3_chance_rate and compares.


def quantities():
    for name, pattern in QUANTITIES.items():
        found = [m.group(1) for m in re.finditer(pattern, FLAT)]
        if not found:
            problems.append(f"{name}: stated nowhere; the pattern has gone stale")
            continue
        distinct = sorted(set(found))
        if len(distinct) > 1:
            problems.append(
                f"{name}: stated {len(found)} times as {distinct}; these must agree")


def one(pattern: str) -> int | None:
    m = re.search(pattern, FLAT)
    return int(m.group(1)) if m else None


def arithmetic():
    total = one(QUANTITIES["ledger, total"])
    parts = {k: one(QUANTITIES[f"ledger, {k}"])
             for k in ("F (others' evals)", "D (our own defects)", "N (negative results)")}
    if total is None or any(v is None for v in parts.values()):
        problems.append("ledger arithmetic: could not find the counts to add up")
    elif sum(parts.values()) != total:
        problems.append(f"ledger arithmetic: {' + '.join(str(v) for v in parts.values())}"
                        f" = {sum(parts.values())}, but the paper says {total} entries")

    lit = one(r"(\d+) come from the published")
    wild = one(r"(\d+) from defects we found auditing")
    own = one(r"(\d+) from our own checks")
    classes = one(r"Each of the (\d+) classes declares")
    if None in (lit, wild, own, classes):
        problems.append("taxonomy arithmetic: could not find all four numbers")
    elif lit + wild + own != classes:
        problems.append(f"taxonomy arithmetic: sources sum to {lit + wild + own}, "
                        f"but the paper says {classes} classes")


# THERE IS NO table-vs-prose RULE, and the reason is worth keeping.
#
# One was written, in three progressively less wrong versions: "every percentage
# in a watched table row also appears in the prose". Version one could not see
# the first data row of any table, because \midrule stays glued to the label
# cell. Version two searched for the cell's value in the whole document, found
# it in the table it had just read it from, and passed a row corrupted to 77.7%.
# Version three searched the prose alone and fired on the correct paper, because
# a table's 100.0% column is not something prose repeats.
#
# The premise was wrong, not the implementation. Most cells in most tables are
# never discussed in the text, so absence-from-prose is not evidence of anything.
# What the rule was reaching for -- the row and the sentence about it agree -- is
# already enforced, and enforced better, by numbers.py: it pins the table row
# literal AND the prose sentence to the same value read from the scorecards, so
# the two cannot drift apart without one of them failing. A rule that only goes
# quiet when tuned into silence is worth less than the line it occupies.


CARDINAL_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "twenty-one": 21, "twenty-four": 24, "twenty-five": 25, "thirty-one": 31,
    "forty": 40, "sixty-five": 65,
}

# Words that follow a cardinal without being the thing counted, so the harvester
# keeps walking to the real noun.
CARDINAL_SKIP = {
    "of", "in", "on", "the", "a", "an", "and", "or", "per", "to", "that",
    "which", "is", "are", "was", "were", "at", "by", "for", "from", "with",
    "different", "real", "other", "own", "same", "new", "first", "second",
    "third", "more", "most", "such", "these", "those", "hand-annotated",
    "published", "planted", "withheld", "surveyed", "annotated", "small",
    "further", "distinct", "additional", "separate", "genuine",
}

# Function words the harvester can land on when a sentence does something it did
# not anticipate. Not countable, so not evidence of anything.
CARDINAL_IGNORE = {
    "rather", "them", "needs", "each", "both", "here", "than", "they", "this",
    "when", "where", "also", "only", "still",
}

# A noun counted more than one way, with every value that is legitimately its
# own referent. Read as: these were looked at by a person and are not the same
# thing. Anything outside these sets is a new claim nobody has adjudicated.
ADJUDICATED = {
    "bits": {0, 5, 8},            # perceptual-hash thresholds in the sweep
    "checks": {4, 14, 21, 61},    # silenced by D-053; data-scope; evidence contract; total
    "classes": {4, 8, 9, 21},     # asset-only; plantable on text; blind; taxonomy
    "clean": {351, 489},          # the three splits that share a shape; all five
    "defect": {9, 15, 21},        # blind classes; cross-tool families; taxonomy
    "external": {2, 3},           # imported harness log formats; calibrations
    "findings": {2, 29},          # the two about a set rather than an item; ledger F
    "flagged": {3, 200},          # the near-overclaim pairs; IRT's top-200
    "images": {6, 60000},         # PNGs per asset instance; all of CIFAR-10
    "instances": {51, 252, 800},  # clean on dev; the asset split; heldout-08b
    "items": {1, 2, 8, 20, 24, 39, 200, 370},
                                  # items.jsonl; Redux true positives; dead-weight;
                                  # S3's floor; corpus instance size; Redux's
                                  # multiple_correct_answers; fleet trial; Redux's
                                  # total flawed
    "judge": {1, 4},              # checks the third key reaches; checks in the family
    "options": {2, 4},            # both-correct defect class; the text pools' width
    "pods": {6, 16},              # human-exam redistributions; trials that must stay silent
    "splits": {2, 3, 4, 5},       # the leak defect class; pooled; at 100%; the corpus
}


def cardinals():
    """Every number-plus-noun in the paper, checked against what was adjudicated.

    Deliberately not a whitelist of interesting nouns. The defects this catches
    were all in sentences nobody thought to name, which is why the rule reads
    the whole document and asks a person only about disagreements.
    """
    # Prose and tables only. fig_pipeline.tex is a TikZ drawing whose option
    # syntax (`line width=0.6pt`, `black!45`) reads as cardinals attached to
    # nouns and is not a claim about anything.
    body = "\n".join(
        (HERE / f).read_text(encoding="utf-8")
        for f in ("main.tex", "crosstool.tex") if (HERE / f).is_file())
    body = re.sub(r"(?m)^\s*%.*$", "", body)
    body = re.sub(r"\\(?:emph|textbf|texttt|textit|citep|citet|ref|S)\*?\{([^{}]*)\}",
                  r"\1", body)
    body = re.sub(r"\\(?:phantom|label|caption)\{[^{}]*\}", " ", body)
    body = re.sub(r"\\[a-zA-Z]+", " ", body)
    text = " ".join(body.replace(chr(92) + "%", "%")
                    .replace("{,}", "").replace(",", "").split())

    num = r"(\d+|" + "|".join(sorted(CARDINAL_WORDS, key=len, reverse=True)) + r")"
    seen: dict[str, set[int]] = {}
    quote: dict[tuple[str, int], str] = {}
    for m in re.finditer(num + r"\s+((?:[a-z][a-z-]*\s+){0,2}?[a-z][a-z-]{2,})",
                         text, re.I):
        raw = m.group(1).lower()
        value = int(raw) if raw.isdigit() else CARDINAL_WORDS.get(raw)
        if value is None:
            continue
        tail = [w for w in m.group(2).lower().split() if w not in CARDINAL_SKIP]
        if not tail:
            continue
        noun = tail[-1].rstrip(".,;:")
        if len(noun) < 4 or noun in CARDINAL_IGNORE:
            continue
        seen.setdefault(noun, set()).add(value)
        quote.setdefault((noun, value), text[max(0, m.start() - 60):m.end() + 12])

    for noun, values in sorted(seen.items()):
        allowed = ADJUDICATED.get(noun)
        if allowed is None:
            if len(values) > 1:
                problems.append(
                    f"cardinals: {noun!r} is counted {sorted(values)} and is not in "
                    f"ADJUDICATED; if these are different things, add it")
            continue
        for extra in sorted(values - allowed):
            problems.append(
                f"cardinals: {extra} {noun} is new; adjudicated values are "
                f"{sorted(allowed)}. Context: ...{quote[(noun, extra)].strip()}...")


def references():
    labels = set(re.findall(r"\\label\{([^}]+)\}", TEX))
    for ref in sorted(set(re.findall(r"\\ref\{([^}]+)\}", TEX))):
        if ref not in labels:
            problems.append(f"\\ref{{{ref}}} has no matching \\label")


def vocabulary():
    """Terms the paper defines must not appear under a second name.

    A paper that calls the same thing a pod and a bundle is a paper whose reader
    has to keep a synonym table.
    """
    banned = {"eval bundle": "pod", "check suite": "battery",
              "blind arm": "blind-spot arm", "held out split": "withheld split"}
    for wrong, right in banned.items():
        if wrong.lower() in FLAT.lower():
            problems.append(f"vocabulary: {wrong!r} appears; this paper says {right!r}")


for fn in (quantities, arithmetic, cardinals, references, vocabulary):
    fn()

print(f"internal consistency: {len(problems)} problem(s)"
      f" over {len(QUANTITIES)} quantities\n")
for p in problems:
    print(f"  - {p}")
sys.exit(1 if problems else 0)
