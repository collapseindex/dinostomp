"""Two tables and the join between them.

Everything in `tabular.py` reads one file. The defects that cost the most live
between two, because a join is the one operation that fails SILENTLY and in the
flattering direction: an inner join that drops a row does not raise, does not
warn, and leaves a smaller, cleaner-looking dataset behind. Nobody audits a
number for being too tidy.

The case this module was built against is real and is in this repository's own
case-study work. A public Animal Crossing dataset stores each villager's
favourite song as `To The Edge` and the song table stores it as `To the Edge`.
One capital letter. Eighty-eight of eighty-nine favourites match exactly, the
eighty-ninth does not, and three villagers vanish from every per-song analysis
with no error anywhere. The finding that comes out the other side is not merely
imprecise, it is manufactured: those villagers appear to favour nothing.

So the checks here are about the join a person is ABOUT to do, before they do
it, and the loudest of them is the one that asks: how many of these rows would
match if the keys were merely tidied? That number is recoverable evidence about
intent. Nobody writes `To The Edge` in one file and `To the Edge` in another on
purpose.

Direction matters and is named, not assumed. The LEFT table is the one whose
rows are at risk (the child, the fact table, the thing being counted). The
RIGHT table is what it points at (the parent, the lookup, the dimension).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from dinostomp.tabular import (
    ColumnProfile,
    as_number,
    columns_of,
    normalize_label,
)

MAX_EXAMPLES = 6
# A candidate key pair has to beat the runner-up by this much to be chosen
# without asking. Below it the tool names the candidates and refuses, because a
# join on the wrong column produces a confident, complete, wrong answer.
INFERENCE_MARGIN = 0.15
# Below this share of matching values a column pair is not a key relationship,
# it is a coincidence. Two `status` columns both holding "active" overlap
# perfectly and join to nonsense.
MIN_OVERLAP = 0.30
MIN_DISTINCT_FOR_KEY = 3
# The floor below which an inferred key is a coincidence rather than a
# relationship, as overlap x identification. Without it, a pair of tables whose
# REAL key matches nothing falls back to whatever else happens to overlap: a
# planted "nothing matches" trial silently joined `amount <-> amount` at 33%
# and reported a healthy join on columns nobody meant (D-088). A weak best
# candidate is exactly when the tool must ask rather than answer.
MIN_CONFIDENT_SCORE = 0.60
# A parent key repeating more than this multiplies the child table on join.
FANOUT_WARN = 1.0


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ("" if value is None else str(value))


def _values(rows: list[dict], column: str) -> list[str]:
    return [_text(r.get(column)).strip() for r in rows
            if _text(r.get(column)).strip() != ""]


@dataclass
class JoinKey:
    left: str
    right: str
    score: float = 0.0
    inferred: bool = True
    overlap: float = 0.0        # share of left rows the right column covers
    identifies: float = 0.0     # how uniquely the right column names a right row

    def __str__(self) -> str:
        how = "inferred" if self.inferred else "you said so"
        return f"{self.left} <-> {self.right}   ({how})"


@dataclass
class JoinFacts:
    """Everything the checks read, computed once."""

    left_rows: int
    right_rows: int
    key: JoinKey
    left_values: list[str] = field(default_factory=list)
    right_values: list[str] = field(default_factory=list)
    matched: int = 0
    orphans: Counter = field(default_factory=Counter)
    recoverable: dict[str, str] = field(default_factory=dict)
    recoverable_rows: int = 0
    right_key_counts: Counter = field(default_factory=Counter)
    joined_rows: int = 0

    @property
    def left_filled(self) -> int:
        return len(self.left_values)

    @property
    def match_rate(self) -> float:
        return self.matched / self.left_filled if self.left_filled else 0.0


def candidate_pairs(left: list[dict], right: list[dict]) -> list[JoinKey]:
    """Score every column pair by how much of the left column the right one
    covers. Name-matching alone is not enough: `Name` appears in both ACNH
    tables and means a villager in one and a song in the other."""
    scored: list[JoinKey] = []
    right_sets = {}
    right_uniqueness = {}
    for column in columns_of(right):
        filled = _values(right, column)
        values = set(filled)
        if len(values) >= MIN_DISTINCT_FOR_KEY:
            right_sets[column] = values
            # How well this column IDENTIFIES a right-hand row. A lookup table's
            # key is unique or nearly so; a colour column with eight values
            # spread over ninety-eight songs is a category that happens to
            # overlap. Without this, two `Color 2` columns score a perfect 100%
            # against each other and out-rank the real key, which is exactly
            # what happened the first time this was pointed at real tables.
            right_uniqueness[column] = len(values) / len(filled)
    for lcol in columns_of(left):
        lvals = _values(left, lcol)
        if len(set(lvals)) < MIN_DISTINCT_FOR_KEY:
            continue
        for rcol, rvals in right_sets.items():
            hits = sum(1 for v in lvals if v in rvals)
            overlap = hits / len(lvals)
            if overlap < MIN_OVERLAP:
                continue
            # Coverage AND identification. Either alone picks the wrong column.
            score = overlap * right_uniqueness[rcol]
            # A name match is corroboration, never the reason on its own.
            if normalize_label(lcol) == normalize_label(rcol):
                score = min(1.0, score + 0.05)
            candidate = JoinKey(lcol, rcol, score)
            candidate.overlap = overlap
            candidate.identifies = right_uniqueness[rcol]
            scored.append(candidate)
    scored.sort(key=lambda k: -k.score)
    return scored


def infer_key(left: list[dict], right: list[dict]) -> tuple[JoinKey | None, list[str]]:
    """Pick the join key, or refuse and say what the candidates were.

    Same rule as every other inference in this project: a guess presented as a
    fact is the failure mode. A join on the wrong column does not error, it
    answers.
    """
    scored = candidate_pairs(left, right)
    if not scored:
        return None, ["no column pair shares enough values to be a join key; "
                      "pass --left-key and --right-key"]
    best = scored[0]
    if best.score < MIN_CONFIDENT_SCORE:
        return None, [
            f"no column pair is convincingly a key: the best is {best.left} <-> "
            f"{best.right}, covering {best.overlap:.0%} of left rows and identifying "
            f"{best.identifies:.0%} of right rows. That is an overlap, not a relationship. "
            f"Pass --left-key and --right-key if you meant it."]
    # A candidate exactly at the margin HAS been beaten by the margin, so it is
    # not a rival. The epsilon says so in floating point, where the runner-up
    # lands on 0.8500000000000001 against a cutoff of 0.85 and a clear winner
    # would otherwise become a refusal.
    cutoff = best.score - INFERENCE_MARGIN + 1e-9
    rivals = [k for k in scored[1:]
              if k.score > cutoff
              and (k.left, k.right) != (best.left, best.right)]
    if rivals:
        named = ", ".join(f"{k.left} <-> {k.right} ({k.overlap:.0%} covered, "
                          f"{k.identifies:.0%} unique)" for k in [best, *rivals[:3]])
        return None, [f"cannot tell which columns join: {named}. "
                      f"Pass --left-key and --right-key to choose."]
    return best, [f"join key: {best}  ({best.overlap:.0%} of left rows covered; the right "
                  f"column identifies {best.identifies:.0%} of its own rows)"]


def analyse(left: list[dict], right: list[dict], key: JoinKey) -> JoinFacts:
    facts = JoinFacts(len(left), len(right), key)
    facts.left_values = _values(left, key.left)
    facts.right_values = _values(right, key.right)
    right_set = set(facts.right_values)
    facts.right_key_counts = Counter(facts.right_values)

    # What the right table would match if its keys were merely tidied. Built
    # once, so recovery is a lookup rather than a scan per orphan.
    normalised_right: dict[str, str] = {}
    for value in right_set:
        normalised_right.setdefault(normalize_label(value), value)

    for value in facts.left_values:
        if value in right_set:
            facts.matched += 1
            continue
        facts.orphans[value] += 1
        recovered = normalised_right.get(normalize_label(value))
        if recovered is not None and recovered != value:
            facts.recoverable[value] = recovered
            facts.recoverable_rows += 1

    facts.joined_rows = sum(facts.right_key_counts.get(v, 0) for v in facts.left_values)
    return facts


Result = tuple[bool, str, int, list[str], dict]


def check_join_viable(facts: JoinFacts) -> Result:
    """JN1: the join produces something. Gates.

    Separate from the orphan count on purpose, because they are different
    claims. "Some rows do not match" is a judgement (a lookup that does not
    cover every code yet, a left join written deliberately). "NOTHING matches"
    is arithmetic: every inner join on these two columns returns the empty set,
    and any analysis built on it is reporting about no rows at all.
    """
    if not facts.left_filled:
        return True, "the left key column is empty", 0, [], {
            "not_applicable": "no left-hand key values to match"}
    if facts.matched:
        return (True, f"{facts.matched} of {facts.left_filled} left row(s) find a match, so "
                      f"the join returns rows", facts.left_filled, [],
                {"match_rate": facts.match_rate})
    hint = ""
    if facts.recoverable:
        hint = (f" {len(facts.recoverable)} key(s) would match if tidied, so the columns ARE "
                f"related and the values are not (see key-normalisation)")
    return (False,
            f"NOT ONE of {facts.left_filled} left row(s) matches the right table. An inner "
            f"join on these columns returns nothing.{hint}",
            facts.left_filled,
            [f"{v!r} x{c}" for v, c in facts.orphans.most_common(MAX_EXAMPLES)],
            {"match_rate": 0.0})


def check_orphan_rows(facts: JoinFacts) -> Result:
    """JN2: left rows whose key is not in the right table.

    A count, and a warning, because some orphans are ordinary. The
    catastrophic case belongs to JN1.
    """
    if not facts.left_filled:
        return True, "the left key column is empty", 0, [], {
            "not_applicable": "no left-hand key values to match"}
    orphan_rows = sum(facts.orphans.values())
    if not orphan_rows:
        return (True, f"every one of {facts.left_filled} left row(s) matches a right row",
                facts.left_filled, [], {"match_rate": 1.0})
    examples = [f"{value!r} x{count}" for value, count in facts.orphans.most_common(MAX_EXAMPLES)]
    detail = (f"{orphan_rows} of {facts.left_filled} left row(s) "
              f"({orphan_rows / facts.left_filled:.1%}) have a key that is not in the right "
              f"table, across {len(facts.orphans)} distinct value(s); an inner join drops "
              f"them and says nothing")
    return False, detail, facts.left_filled, examples, {
        "match_rate": facts.match_rate, "orphan_rows": orphan_rows,
        "distinct_orphans": len(facts.orphans)}


def check_key_normalisation(facts: JoinFacts) -> Result:
    """JN2: rows that would match if the keys were merely tidied. Gates.

    The check this module exists for. `To The Edge` against `To the Edge` is
    not a data-modelling decision anybody made; it is a typo with three
    villagers behind it. Recovery by case and whitespace alone is strong
    evidence of intent, and it is deterministic, so it gates: the pair is
    displayed and a human can overrule it in one glance.
    """
    if not facts.left_filled:
        return True, "no keys to compare", 0, [], {
            "not_applicable": "no left-hand key values to normalise"}
    if not facts.recoverable:
        return (True, f"no unmatched key differs from a right-hand key by case or whitespace "
                      f"alone ({len(facts.orphans)} orphan value(s) are genuinely absent)",
                facts.left_filled, [], {})
    examples = [f"{bad!r} would match {good!r}" for bad, good in
                list(facts.recoverable.items())[:MAX_EXAMPLES]]
    return (False,
            f"{facts.recoverable_rows} row(s) across {len(facts.recoverable)} key value(s) "
            f"fail to join ONLY because of case or whitespace, and would match if tidied. "
            f"An inner join drops them silently and the analysis that follows is not "
            f"imprecise, it is manufactured",
            facts.left_filled, examples,
            {"recoverable_values": len(facts.recoverable),
             "recoverable_rows": facts.recoverable_rows,
             "pairs": dict(list(facts.recoverable.items())[:20])})


def check_parent_key_unique(facts: JoinFacts) -> Result:
    """JN3: the right-hand key repeats, so the join is not the lookup it looks like."""
    repeats = {v: c for v, c in facts.right_key_counts.items() if c > 1}
    if not repeats:
        return (True, f"the right key is unique across {len(facts.right_key_counts)} value(s), "
                      f"so this join cannot multiply rows",
                facts.right_rows, [], {})
    examples = [f"{value!r} appears {count} times in the right table"
                for value, count in Counter(repeats).most_common(MAX_EXAMPLES)]
    return (False,
            f"the right-hand key repeats: {len(repeats)} value(s) appear more than once "
            f"(worst {max(repeats.values())}x). This is a lookup that is not one-to-one, so "
            f"joining on it duplicates left rows",
            facts.right_rows, examples,
            {"repeated_values": len(repeats), "worst": max(repeats.values())})


def check_fanout(facts: JoinFacts) -> Result:
    """JN4: how many rows come out compared to how many went in.

    The number that actually matters, and the one nobody computes before
    joining. Every SUM after a fan-out is wrong by the fan-out factor and looks
    entirely plausible.
    """
    if not facts.left_filled:
        return True, "nothing to join", 0, [], {"not_applicable": "no left-hand key values"}
    factor = facts.joined_rows / facts.left_filled
    detail = (f"{facts.left_filled} left row(s) become {facts.joined_rows} after an inner "
              f"join ({factor:.2f}x)")
    if factor > FANOUT_WARN:
        return (False, detail + ": every total computed after this join is multiplied, and "
                                "nothing announces it",
                facts.left_filled, [], {"factor": factor, "joined_rows": facts.joined_rows})
    return True, detail, facts.left_filled, [], {"factor": factor}


def check_key_type(left: list[dict], right: list[dict], key: JoinKey) -> Result:
    """JN5: the same key stored two ways.

    `00123` against `123`, or a number against text. Both sides look correct in
    isolation and the join returns nothing, which is why this reports even
    though JN1 will already have failed: it names the CAUSE.
    """
    lprof = ColumnProfile(key.left, [r.get(key.left) for r in left])
    rprof = ColumnProfile(key.right, [r.get(key.right) for r in right])
    if not lprof.n_filled or not rprof.n_filled:
        return True, "a key column is empty", 0, [], {
            "not_applicable": "one side has no key values to type"}

    def shape(prof: ColumnProfile) -> str:
        numeric = sum(1 for v in prof.filled if as_number(v) is not None)
        if numeric == prof.n_filled:
            zero_led = sum(1 for t in prof.texts if len(t) > 1 and t.startswith("0"))
            return "digit-string with leading zeros" if zero_led else "numeric"
        if numeric == 0:
            return "text"
        return "mixed text and numeric"

    lshape, rshape = shape(lprof), shape(rprof)
    n = lprof.n_filled + rprof.n_filled
    if lshape == rshape:
        return True, f"both keys are {lshape}", n, [], {}
    return (False,
            f"the keys are stored differently: left {key.left!r} is {lshape}, right "
            f"{key.right!r} is {rshape}. Both are correct in isolation and they will not "
            f"compare equal",
            n, [f"left sample: {', '.join(repr(t) for t in lprof.texts[:3])}",
                f"right sample: {', '.join(repr(t) for t in rprof.texts[:3])}"],
            {"left_shape": lshape, "right_shape": rshape})


def check_reconcile(left: list[dict], right: list[dict], key: JoinKey,
                    pairs: list[tuple[str, str]]) -> Result:
    """JN6: a parent total against the sum of its own children. Gates.

    An invoice header that says 1,240.00 over lines that sum to 1,190.00 is not
    a judgement call, it is arithmetic, and it is the single most common thing
    a spreadsheet gets wrong that nobody notices: both numbers are individually
    plausible and only their relationship is false.
    """
    if not pairs:
        return True, "no total to reconcile", 0, [], {
            "not_applicable": "no parent/child numeric column pair was declared with "
                              "--reconcile or found by name"}
    mismatches: list[str] = []
    checked = 0
    for parent_col, child_col in pairs:
        sums: dict[str, float] = defaultdict(float)
        for row in left:
            value = as_number(row.get(child_col))
            if value is not None:
                sums[_text(row.get(key.left)).strip()] += value
        for row in right:
            declared = as_number(row.get(parent_col))
            if declared is None:
                continue
            key_value = _text(row.get(key.right)).strip()
            if key_value not in sums:
                continue
            checked += 1
            actual = sums[key_value]
            if abs(declared - actual) > 0.005:
                mismatches.append(
                    f"{key_value}: {parent_col}={declared:,.2f} but {child_col} sums to "
                    f"{actual:,.2f} (off by {declared - actual:+,.2f})")
    if not checked:
        return True, "no parent row shares a key with a child row", 0, [], {
            "not_applicable": "nothing to reconcile: no key appears on both sides"}
    if not mismatches:
        return (True, f"every one of {checked} parent total(s) equals the sum of its children",
                checked, [], {})
    return (False,
            f"{len(mismatches)} of {checked} parent total(s) disagree with the sum of their "
            f"own child rows; both numbers look plausible and only their relationship is false",
            checked, mismatches[:MAX_EXAMPLES], {"mismatched": len(mismatches),
                                                 "checked": checked})


def reconcile_pairs(left: list[dict], right: list[dict],
                    declared: list[str] | None) -> list[tuple[str, str]]:
    """Which (parent column, child column) pairs to reconcile.

    Explicit `--reconcile parent=child` wins. Otherwise a numeric column whose
    name matches on both sides is the invoice-header shape and is worth
    checking; anything less obvious is left alone rather than guessed at.
    """
    if declared:
        out = []
        for item in declared:
            if "=" not in item:
                continue
            parent, child = item.split("=", 1)
            out.append((parent.strip(), child.strip()))
        return out
    lcols = {normalize_label(c): c for c in columns_of(left)}
    pairs = []
    for rcol in columns_of(right):
        lcol = lcols.get(normalize_label(rcol))
        if not lcol:
            continue
        lprof = ColumnProfile(lcol, [r.get(lcol) for r in left])
        rprof = ColumnProfile(rcol, [r.get(rcol) for r in right])
        if lprof.is_numeric and rprof.is_numeric:
            pairs.append((rcol, lcol))
    return pairs
