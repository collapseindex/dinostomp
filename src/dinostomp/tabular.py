"""Hygiene checks for a table that was never an eval.

The dataset audit in `dataset.py` needs to know which column is the question and
which is the answer. A vendor list, an order export, a general-ledger dump has
neither, so that audit refuses at the front door and the user learns nothing:
the refusal is correct and the outcome is useless.

Everything here reads a table as a table. No mapping, no target, no semantics.
Only facts a reader could confirm by eye, and one rule about what to do with
them:

    THE TOOL PROPOSES. THE HUMAN DISPOSES.

That rule is not decoration. Two of the defects below are the same phenomenon
pointing in opposite directions: a column of digit strings with leading zeros is
a broken numeric column if it holds quantities, and a CORRECT text column if it
holds zip codes, SKUs or phone numbers, and no amount of profiling can tell the
difference. So G4 reports what a conversion would change and refuses to want it.
A cleaner that silently normalises that column is not saving anyone time; it is
destroying data confidently, which is the failure this repo exists to catch.

Gating follows the constitutional split. A duplicate row exists or it does not,
so G2 gates. Whether a `999999` is a sentinel or a real invoice number is an
inference about intent, so G7 warns.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from typing import Any

# Zero-width and format characters that survive a copy-paste and are invisible
# in every spreadsheet UI. U+00A0 is the one that actually bites: Excel writes a
# non-breaking space when a user pastes from a web page, and the resulting
# "Acme Corp" never equals "Acme Corp" again.
INVISIBLE_CHARS = {
    " ": "NO-BREAK SPACE",
    "​": "ZERO WIDTH SPACE",
    "‌": "ZERO WIDTH NON-JOINER",
    "‍": "ZERO WIDTH JOINER",
    "⁠": "WORD JOINER",
    "﻿": "ZERO WIDTH NO-BREAK SPACE (BOM)",
    "‪": "LEFT-TO-RIGHT EMBEDDING",
    "‬": "POP DIRECTIONAL FORMATTING",
    "­": "SOFT HYPHEN",
}

# Text that means "no value" often enough to be worth naming, compared after
# casefold and strip. The empty string is deliberately NOT here: a blank cell is
# a blank cell, and reporting every one of them as a sentinel would bury the
# finding that matters under the ordinary shape of real data.
TEXT_SENTINELS = {
    "n/a", "na", "n.a.", "#n/a", "-", "--", "---", "null", "none", "nil",
    "nan", "missing", "unknown", "tbd", "?", ".", "#value!", "#ref!",
}

# Numbers that are almost never measurements. Flagged only when they REPEAT in
# an otherwise well-behaved numeric column, because one -1 is a value and
# fourteen of them in a price column is a convention nobody wrote down.
NUMERIC_SENTINELS = {-1, -99, -999, -9999, 9999, 99999, 999999, 9999999, -111111}

ID_NAME_RE = re.compile(
    r"(^|[_\s])(id|ids|key|code|codes|no|num|number|sku|upc|ean|isbn|uuid|guid|ref)([_\s]|$)"
    r"|_id$|^id$|number$|code$",
    re.IGNORECASE,
)
PERCENT_NAME_RE = re.compile(r"pct|percent|%|_rate$|^rate$|share|margin", re.IGNORECASE)
CURRENCY_CHARS = "$£€¥₩₹"
# A number the way a spreadsheet renders it: symbols, thousands separators,
# trailing minus, accounting parentheses.
FORMATTED_NUMBER_RE = re.compile(
    r"^\(?\s*[" + re.escape(CURRENCY_CHARS) + r"]?\s*-?\s*"
    r"(?:\d{1,3}(?:[, ]\d{3})+|\d+)(?:\.\d+)?\s*%?\s*\)?-?$"
)
# The first branch of that alternation is not optional. Written as a bare
# three-digit group with an optional repeat it rejects `1200.00` and
# `999999`, which quietly turned every column holding a value over 999 into
# "not numeric": G6 raised a false alarm on the clean control and G7 missed
# a planted 999999 sentinel. The control arm of the test suite caught both
# before this shipped, which is the entire argument for having one.
PLAIN_NUMBER_RE = re.compile(r"^-?\d+(?:\.\d+)?$")
DIGITS_RE = re.compile(r"^\d+$")

# Date shapes, kept deliberately small. The point is not to parse every date a
# human can write; it is to notice that ONE column is written two ways.
DATE_PATTERNS = [
    ("ISO yyyy-mm-dd", re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")),
    ("slashed d/m/y or m/d/y", re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})$")),
    ("dotted d.m.y", re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{2,4})$")),
    ("dashed d-m-y", re.compile(r"^(\d{1,2})-(\d{1,2})-(\d{2,4})$")),
    ("yyyy/mm/dd", re.compile(r"^(\d{4})/(\d{1,2})/(\d{1,2})$")),
    ("textual month", re.compile(r"^\d{1,2}[ -][A-Za-z]{3,9}[ -]\d{2,4}$")),
]

# Thresholds. Every number here is a judgment unless marked, and each one is
# stated so a reader can disagree with the value rather than the idea.
MIN_ROWS_FOR_PROFILE = 5      # below this, "most of the column" means nothing
NUMERIC_MAJORITY = 0.80       # a column this numeric is meant to be numeric
KEY_UNIQUENESS = 0.90         # this distinct and it was meant to be a key
SENTINEL_MIN_REPEATS = 3      # one -1 is a value; three is a convention
PERCENT_MIN_EACH = 2          # two of each scale is already two scales
CATEGORY_MAX_DISTINCT = 0.50  # above this a column is free text, not categories
MAX_EXAMPLES = 6
NEAR_DUP_MIN_LEN = 12         # two short rows colliding after folding is noise


def _cells(rows: list[dict], column: str) -> list[Any]:
    return [r.get(column) for r in rows]


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ("" if value is None else str(value))


def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def columns_of(rows: list[dict], skip: set[str] | None = None) -> list[str]:
    """Every column name in the table, first-seen order.

    Rows are read from CSV, JSONL and worksheets, and only the first of those
    guarantees every row has every key, so the union is taken rather than
    trusting `rows[0]`.
    """
    skip = skip or set()
    seen: dict[str, None] = {}
    for row in rows:
        for key in row:
            if key not in skip and not str(key).startswith("_"):
                seen.setdefault(key, None)
    return list(seen)


def as_number(value: Any) -> float | None:
    """The number a cell means, or None. Accepts what a spreadsheet renders."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = _text(value).strip()
    if not text or not FORMATTED_NUMBER_RE.match(text):
        return None
    negative = (text.startswith("(") and text.endswith(")")) or text.endswith("-")
    stripped = re.sub(r"[()\s, %" + re.escape(CURRENCY_CHARS) + r"]", "", text)
    if stripped.endswith("-"):
        stripped = stripped[:-1]
    if not stripped or not PLAIN_NUMBER_RE.match(stripped):
        return None
    number = float(stripped)
    return -abs(number) if negative else number


def normalize_label(value: Any) -> str:
    """Casefold, strip, collapse internal whitespace, drop invisible characters.

    This is the transformation a human means by "these are the same vendor". It
    is applied to COMPARE, never to rewrite: what it collapses is reported and
    the caller decides.
    """
    text = _text(value)
    for char in INVISIBLE_CHARS:
        text = text.replace(char, " " if char in (" ",) else "")
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


class ColumnProfile:
    """What a column looks like, with no claim about what it means."""

    def __init__(self, name: str, values: list[Any]):
        self.name = name
        self.values = values
        self.filled = [v for v in values if not _blank(v)]
        self.n = len(values)
        self.n_filled = len(self.filled)
        self.texts = [_text(v).strip() for v in self.filled]
        self.numbers = [as_number(v) for v in self.filled]
        self.n_numeric = sum(1 for x in self.numbers if x is not None)
        self.distinct = len({_text(v) for v in self.filled})

    @property
    def numeric_share(self) -> float:
        return self.n_numeric / self.n_filled if self.n_filled else 0.0

    @property
    def is_numeric(self) -> bool:
        return self.n_filled >= MIN_ROWS_FOR_PROFILE and self.numeric_share >= NUMERIC_MAJORITY

    @property
    def looks_like_key(self) -> bool:
        if self.n_filled < MIN_ROWS_FOR_PROFILE:
            return False
        return (self.distinct / self.n_filled) >= KEY_UNIQUENESS

    @property
    def named_like_key(self) -> bool:
        return bool(ID_NAME_RE.search(self.name))


def profile(rows: list[dict], skip: set[str] | None = None) -> dict[str, ColumnProfile]:
    return {c: ColumnProfile(c, _cells(rows, c)) for c in columns_of(rows, skip)}


# --------------------------------------------------------------------------
# The checks. Each returns (ok, detail, n_examined, examples, evidence) so the
# caller can hand them straight to a Reporter without any check knowing what a
# Reporter is.
# --------------------------------------------------------------------------

Result = tuple[bool, str, int, list[str], dict]


def check_cell_hygiene(rows: list[dict], profiles: dict[str, ColumnProfile]) -> Result:
    """G1: cells whose value is not what it appears to be.

    Leading and trailing whitespace and invisible characters are the single
    most common reason two tables refuse to join. They are invisible in every
    spreadsheet UI by construction, so nobody finds them by looking.
    """
    edge, invisible = defaultdict(int), defaultdict(Counter)
    examples: list[str] = []
    for column, prof in profiles.items():
        for value in prof.filled:
            if not isinstance(value, str):
                continue
            if value != value.strip():
                edge[column] += 1
                if len(examples) < MAX_EXAMPLES:
                    examples.append(f"{column}: {value!r} has edge whitespace")
            for char, name in INVISIBLE_CHARS.items():
                if char in value:
                    invisible[column][name] += 1
                    if len(examples) < MAX_EXAMPLES:
                        examples.append(f"{column}: {value!r} contains {name}")
    total = sum(edge.values()) + sum(sum(c.values()) for c in invisible.values())
    if not total:
        return True, "no edge whitespace or invisible characters", len(rows), [], {}
    parts = []
    if edge:
        parts.append(f"{sum(edge.values())} cell(s) with leading/trailing whitespace "
                     f"in {len(edge)} column(s)")
    if invisible:
        kinds = Counter()
        for counter in invisible.values():
            kinds.update(counter)
        parts.append(f"{sum(kinds.values())} cell(s) carrying {', '.join(sorted(kinds))}")
    return (False, "; ".join(parts), len(rows), examples,
            {"edge_whitespace_by_column": dict(edge),
             "invisible_by_column": {k: dict(v) for k, v in invisible.items()}})


def check_duplicate_rows(rows: list[dict]) -> Result:
    """G2: byte-identical rows. A deterministic fact, so it gates.

    Every downstream total counts a duplicated row twice, and no analysis
    announces that it did.
    """
    keys = [tuple(sorted((k, _text(v)) for k, v in row.items() if not str(k).startswith("_")))
            for row in rows]
    counts = Counter(keys)
    dups = {k: c for k, c in counts.items() if c > 1}
    if not dups:
        return True, f"no duplicate rows among {len(rows)}", len(rows), [], {}
    extra = sum(c - 1 for c in dups.values())
    examples = [", ".join(f"{k}={v}" for k, v in key[:4])[:100]
                for key in list(dups)[:MAX_EXAMPLES]]
    return (False, f"{extra} duplicate row(s) across {len(dups)} repeated value(s), "
                   f"among {len(rows)} rows",
            len(rows), examples, {"duplicate_groups": len(dups), "extra_rows": extra})


def check_near_duplicate_rows(rows: list[dict]) -> Result:
    """G11: rows identical once case and whitespace stop counting.

    Reports only what G2 could not see, so the two never double-count. A
    diagnostic: two rows differing by capitalisation can be two real records.
    """
    exact = Counter(tuple(sorted((k, _text(v)) for k, v in row.items()
                                 if not str(k).startswith("_"))) for row in rows)
    groups: dict[tuple, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        key = tuple(sorted((k, normalize_label(v)) for k, v in row.items()
                           if not str(k).startswith("_")))
        if sum(len(v) for _, v in key) >= NEAR_DUP_MIN_LEN:
            groups[key].append(index)
    flagged = []
    for key, indices in groups.items():
        if len(indices) < 2:
            continue
        raw = {tuple(sorted((k, _text(rows[i].get(k))) for k in rows[i]
                            if not str(k).startswith("_"))) for i in indices}
        if len(raw) > 1:  # not already an exact duplicate group
            flagged.append((key, indices))
    if not flagged:
        return True, f"no near-duplicate rows among {len(rows)}", len(rows), [], {}
    examples = []
    for key, indices in flagged[:MAX_EXAMPLES]:
        shown = ", ".join(f"row {i}" for i in indices[:4])
        preview = ", ".join(f"{k}={v}" for k, v in key[:3])[:70]
        examples.append(f"{shown}: {preview}")
    return (False, f"{len(flagged)} group(s) of rows identical after folding case and "
                   f"whitespace but not byte-identical (exact duplicates are G2's, "
                   f"not counted here)",
            len(rows), examples, {"near_duplicate_groups": len(flagged)})


def check_duplicate_keys(rows: list[dict], profiles: dict[str, ColumnProfile]) -> Result:
    """G3: a column that was evidently meant to be unique, and is not.

    "Evidently" is doing real work, so it is defined and stated: a column named
    like an identifier that is at least 90% distinct. A column 100% distinct is
    a key doing its job; one 30% distinct is a category that happens to be
    called `type_code`. Between those, a name plus near-uniqueness is the best
    evidence available without domain knowledge, and the finding names the
    column so a reader can overrule it in one glance.
    """
    violations: dict[str, tuple[int, list[str]]] = {}
    for column, prof in profiles.items():
        if prof.n_filled < MIN_ROWS_FOR_PROFILE or not prof.named_like_key:
            continue
        counts = Counter(_text(v) for v in prof.filled)
        repeats = {v: c for v, c in counts.items() if c > 1}
        if not repeats:
            continue
        uniqueness = len(counts) / prof.n_filled
        if uniqueness >= KEY_UNIQUENESS:
            violations[column] = (sum(c - 1 for c in repeats.values()),
                                  [f"{v} x{c}" for v, c in list(repeats.items())[:4]])
    if not violations:
        return True, "no identifier column repeats a value", len(rows), [], {}
    examples = [f"{col}: {', '.join(sample)}" for col, (_, sample) in violations.items()]
    worst = ", ".join(f"{col} ({n} repeat(s))" for col, (n, _) in violations.items())
    return (False, f"identifier column(s) not unique: {worst}", len(rows),
            examples[:MAX_EXAMPLES],
            {"columns": {c: n for c, (n, _) in violations.items()}})


def check_numeric_strings(rows: list[dict], profiles: dict[str, ColumnProfile]) -> Result:
    """G4: digit strings whose leading zeros carry meaning.

    THE check this module exists to get right. A column of `00123` is either a
    broken numeric column or a correct text column, and the difference is
    domain knowledge the file does not contain. So this reports what a
    conversion WOULD destroy and stops there. Anything that auto-fixed it would
    be wrong roughly half the time and silent every time.
    """
    hits: dict[str, tuple[int, int, list[str]]] = {}
    for column, prof in profiles.items():
        if prof.n_filled < MIN_ROWS_FOR_PROFILE:
            continue
        digit_cells = [t for t in prof.texts if DIGITS_RE.match(t)]
        if len(digit_cells) < prof.n_filled * NUMERIC_MAJORITY:
            continue
        zero_led = [t for t in digit_cells if len(t) > 1 and t.startswith("0")]
        if not zero_led:
            continue
        widths = {len(t) for t in digit_cells}
        hits[column] = (len(zero_led), len(digit_cells), zero_led[:4])
        del widths
    if not hits:
        return True, "no digit-string column carries leading zeros", len(rows), [], {}
    examples = [f"{col}: {n} of {total} values keep a leading zero "
                f"(e.g. {', '.join(sample)}) -> converting to a number would change them"
                for col, (n, total, sample) in hits.items()]
    worst = ", ".join(f"{col} ({n})" for col, (n, _, _) in hits.items())
    return (False,
            f"digit-string column(s) with leading zeros: {worst}. These are correct as "
            f"TEXT if they are codes (zip, SKU, phone) and broken as numbers if they are "
            f"quantities; the file cannot say which, so nothing here is auto-repairable",
            len(rows), examples[:MAX_EXAMPLES],
            {"columns": {c: n for c, (n, _, _) in hits.items()}})


def check_type_drift(rows: list[dict], profiles: dict[str, ColumnProfile]) -> Result:
    """G6: a mostly-numeric column with non-numeric cells that are not blank.

    The column a spreadsheet user thinks they can SUM. One `n/a` in row 4,000
    turns the whole column into text on import, and the aggregate that follows
    is either wrong or silently excludes rows.
    """
    hits: dict[str, tuple[int, list[str], int | None]] = {}
    for column, prof in profiles.items():
        if not prof.is_numeric or prof.numeric_share == 1.0:
            continue
        bad = [(i, _text(v).strip()) for i, v in enumerate(prof.values)
               if not _blank(v) and as_number(v) is None]
        if not bad:
            continue
        first_bad_row = bad[0][0]
        hits[column] = (len(bad), [f"row {i}: {t!r}" for i, t in bad[:4]], first_bad_row)
    if not hits:
        return True, "no numeric column carries non-numeric cells", len(rows), [], {}
    examples = [f"{col}: {n} non-numeric cell(s), first at row {row} ({'; '.join(sample)})"
                for col, (n, sample, row) in hits.items()]
    worst = ", ".join(f"{col} ({n})" for col, (n, _, _) in hits.items())
    return (False, f"numeric column(s) contaminated with text: {worst}", len(rows),
            examples[:MAX_EXAMPLES],
            {"columns": {c: n for c, (n, _, _) in hits.items()}})


def check_formatted_numbers(rows: list[dict], profiles: dict[str, ColumnProfile]) -> Result:
    """G10: numbers wearing currency symbols, thousands separators or parentheses.

    Mechanically recoverable, unlike G6, and that is exactly why it is its own
    finding: the fix is a defined transformation rather than an investigation.
    Still not applied automatically, because `(1,200)` means -1200 in accounting
    and means a footnote somewhere else.
    """
    hits: dict[str, tuple[int, list[str]]] = {}
    for column, prof in profiles.items():
        if prof.n_filled < MIN_ROWS_FOR_PROFILE:
            continue
        decorated = [t for t in prof.texts
                     if t and not PLAIN_NUMBER_RE.match(t) and as_number(t) is not None]
        if not decorated or len(decorated) + sum(
                1 for t in prof.texts if PLAIN_NUMBER_RE.match(t)) < prof.n_filled * NUMERIC_MAJORITY:
            continue
        hits[column] = (len(decorated), decorated[:4])
    if not hits:
        return True, "no numeric column stores formatted text", len(rows), [], {}
    examples = [f"{col}: {n} cell(s) like {', '.join(repr(s) for s in sample)}"
                for col, (n, sample) in hits.items()]
    worst = ", ".join(f"{col} ({n})" for col, (n, _) in hits.items())
    return (False, f"numeric column(s) storing symbols or separators: {worst}. "
                   f"Recoverable by a stated rule, but parentheses mean negative in "
                   f"accounting and something else elsewhere",
            len(rows), examples[:MAX_EXAMPLES], {"columns": {c: n for c, (n, _) in hits.items()}})


def check_sentinels(rows: list[dict], profiles: dict[str, ColumnProfile]) -> Result:
    """G7: values that mean "missing" without saying so.

    Two families. Text sentinels (`N/A`, `-`, `null`) are named and unambiguous.
    Numeric sentinels (`-1`, `999999`) are guesses, so they are reported only
    when they REPEAT in an otherwise numeric column: one -1 is a measurement,
    fourteen identical -1s in a price column is a convention nobody documented.
    """
    text_hits: dict[str, Counter] = {}
    numeric_hits: dict[str, dict[float, int]] = {}
    for column, prof in profiles.items():
        if prof.n_filled < MIN_ROWS_FOR_PROFILE:
            continue
        found = Counter(t for t in prof.texts if t.casefold() in TEXT_SENTINELS)
        if found:
            text_hits[column] = found
        if prof.is_numeric:
            counts = Counter(x for x in prof.numbers if x is not None and int(x) == x
                             and int(x) in NUMERIC_SENTINELS)
            repeated = {v: c for v, c in counts.items() if c >= SENTINEL_MIN_REPEATS}
            if repeated:
                numeric_hits[column] = repeated
    if not text_hits and not numeric_hits:
        return True, "no sentinel values found", len(rows), [], {}
    examples = [f"{col}: {', '.join(f'{v!r} x{c}' for v, c in found.most_common(3))}"
                for col, found in text_hits.items()]
    examples += [f"{col}: {', '.join(f'{int(v)} x{c}' for v, c in found.items())} "
                 f"(repeats in a numeric column; a sentinel, or real values?)"
                 for col, found in numeric_hits.items()]
    total = sum(sum(c.values()) for c in text_hits.values()) + \
        sum(sum(c.values()) for c in numeric_hits.values())
    named = ", ".join(
        f"{col} ({', '.join(sorted({*(repr(v) for v in text_hits.get(col, {})), *(str(int(v)) for v in numeric_hits.get(col, {}))}))})"
        for col in sorted(set(text_hits) | set(numeric_hits)))
    return (False, f"{total} cell(s) look like missing-value placeholders in {named}; each is "
                   f"counted as data by every aggregate until someone says otherwise",
            len(rows), examples[:MAX_EXAMPLES],
            {"text_sentinels": {c: dict(v) for c, v in text_hits.items()},
             "numeric_sentinels": {c: {str(k): v for k, v in d.items()}
                                   for c, d in numeric_hits.items()}})


def check_category_collapse(rows: list[dict], profiles: dict[str, ColumnProfile]) -> Result:
    """G8: labels that are one category wearing several spellings.

    The defect behind a GROUP BY that silently splits: `West`, `west` and
    `West ` are three groups in every database on earth and one region in every
    human's head. Reports the collapse it WOULD produce, and the members, so the
    decision is made on the evidence rather than on the count.
    """
    hits: dict[str, tuple[int, int, list[str]]] = {}
    for column, prof in profiles.items():
        if prof.n_filled < MIN_ROWS_FOR_PROFILE or prof.is_numeric:
            continue
        groups: dict[str, set[str]] = defaultdict(set)
        for text in prof.texts:
            if text:
                groups[normalize_label(text)].add(text)
        # The cardinality guard runs on NORMALISED labels, not raw ones. Raw
        # distinctness is inflated by the very defect being looked for: a region
        # column of West/west/EAST/east reads as 70% distinct and would be
        # dismissed as free text, which is how this check missed its own
        # flagship case on the first run it was pointed at real data.
        if len(groups) / prof.n_filled > CATEGORY_MAX_DISTINCT:
            continue  # free text, not a category column
        merged = {k: v for k, v in groups.items() if len(v) > 1}
        if not merged:
            continue
        sample = [" = ".join(sorted(repr(x) for x in v)) for v in list(merged.values())[:3]]
        hits[column] = (len(groups) + sum(len(v) - 1 for v in merged.values()),
                        len(groups), sample)
    if not hits:
        return True, "no category column collapses under normalisation", len(rows), [], {}
    examples = [f"{col}: {before} labels collapse to {after} ({'; '.join(sample)})"
                for col, (before, after, sample) in hits.items()]
    worst = ", ".join(f"{col} ({before} -> {after})" for col, (before, after, _) in hits.items())
    return (False, f"category column(s) with labels that differ only by case or whitespace: "
                   f"{worst}. Every grouping over these columns is split today",
            len(rows), examples[:MAX_EXAMPLES],
            {"columns": {c: {"before": b, "after": a} for c, (b, a, _) in hits.items()}})


def check_percent_scale(rows: list[dict], profiles: dict[str, ColumnProfile]) -> Result:
    """G9: a rate column holding both 0.15 and 15.

    Only fires when BOTH populations are real (a handful of each), because a
    column of fractions with one legitimate 15 is not a scale problem, and
    saying it is would train people to ignore this check.
    """
    hits: dict[str, tuple[int, int]] = {}
    for column, prof in profiles.items():
        if not prof.is_numeric or not PERCENT_NAME_RE.search(column):
            continue
        values = [x for x in prof.numbers if x is not None]
        fractions = [x for x in values if 0 < abs(x) <= 1]
        percents = [x for x in values if 1 < abs(x) <= 100]
        if len(fractions) >= PERCENT_MIN_EACH and len(percents) >= PERCENT_MIN_EACH:
            hits[column] = (len(fractions), len(percents))
    if not hits:
        return True, "no rate column mixes fraction and percent scales", len(rows), [], {}
    examples = [f"{col}: {frac} value(s) in 0..1 and {pct} value(s) in 1..100"
                for col, (frac, pct) in hits.items()]
    return (False, f"rate column(s) holding two scales at once: {', '.join(hits)}. "
                   f"Any average over these is meaningless until one scale is chosen",
            len(rows), examples[:MAX_EXAMPLES],
            {"columns": {c: {"fractions": f, "percents": p} for c, (f, p) in hits.items()}})


def check_date_formats(rows: list[dict], profiles: dict[str, ColumnProfile]) -> Result:
    """G5: one date column written two ways, or written ambiguously.

    Two findings under one id because they have one cause and one fix. A column
    holding both `2026-03-04` and `04/03/2026` needs a human to say which is
    which, and a column of `03/04/2026` where every value could be either
    day-first or month-first cannot be resolved from the file at all.
    """
    mixed: dict[str, list[str]] = {}
    ambiguous: dict[str, int] = {}
    for column, prof in profiles.items():
        if prof.n_filled < MIN_ROWS_FOR_PROFILE or prof.is_numeric:
            continue
        shapes: dict[str, int] = defaultdict(int)
        slashed: list[tuple[int, int]] = []
        for text in prof.texts:
            for name, pattern in DATE_PATTERNS:
                match = pattern.match(text)
                if not match:
                    continue
                shapes[name] += 1
                if name in ("slashed d/m/y or m/d/y", "dotted d.m.y", "dashed d-m-y"):
                    slashed.append((int(match.group(1)), int(match.group(2))))
                break
        if sum(shapes.values()) < prof.n_filled * NUMERIC_MAJORITY:
            continue  # not a date column
        if len(shapes) > 1:
            mixed[column] = [f"{n} x{c}" for n, c in shapes.items()]
        elif slashed:
            both_ways = [1 for a, b in slashed if a <= 12 and b <= 12]
            decided = [1 for a, b in slashed if a > 12 or b > 12]
            if len(both_ways) >= SENTINEL_MIN_REPEATS and not decided:
                ambiguous[column] = len(both_ways)
    if not mixed and not ambiguous:
        return True, "no date column mixes formats or reads both ways", len(rows), [], {}
    examples = [f"{col}: {', '.join(shapes)}" for col, shapes in mixed.items()]
    examples += [f"{col}: {n} value(s) where both parts are <= 12, so day-first and "
                 f"month-first both parse and give different dates" for col, n in ambiguous.items()]
    parts = []
    if mixed:
        parts.append(f"{len(mixed)} column(s) mixing date formats")
    if ambiguous:
        parts.append(f"{len(ambiguous)} column(s) whose dates are locale-ambiguous")
    return (False, "; ".join(parts), len(rows), examples[:MAX_EXAMPLES],
            {"mixed_format_columns": list(mixed), "ambiguous_columns": list(ambiguous)})
