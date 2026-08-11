"""Eleven rules over one scan. Each turns aggregates into findings, or a skip.

A rule that cannot run says so. There is no path here from "I could not test
this" to a green line, because a coverage number that counts untested things as
passed is worse than no coverage number.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from . import contract as C
from .checks import MAX_EXAMPLES, Scan, scan


def _ex(items: list[str]) -> list[str]:
    return items[:MAX_EXAMPLES]


def a1_schema(s: Scan, out) -> None:
    if s.bad_columns:
        out.finding("A1", "fail", f"the file's columns do not match the documented schema: "
                                  f"{s.bad_columns}", n=1)
    else:
        out.finding("A1", "pass", f"all {len(C.COLUMNS)} documented columns present, in order")


def a2_vocabulary(s: Scan, out) -> None:
    hits = [(col, ctr) for col, ctr in (("metric_id", s.unknown_metric),
                                        ("geo_level", s.unknown_geo_level),
                                        ("category_name", s.unknown_category)) if ctr]
    if not hits:
        out.finding("A2", "pass",
                    f"every metric_id, geo_level and category_name is one the README documents "
                    f"({len(C.METRIC_UNITS)} metrics)")
        return
    for col, ctr in hits:
        out.finding("A2", "fail",
                    f"{sum(ctr.values()):,} row(s) carry a {col} the README does not document",
                    n=sum(ctr.values()),
                    examples=_ex([f"{v!r} x{n:,}" for v, n in ctr.most_common()]))


def a3_precision(s: Scan, out) -> None:
    if s.n_unparseable:
        out.finding("A3", "fail", f"{s.n_unparseable:,} value(s) are not numbers",
                    n=s.n_unparseable, examples=_ex(s.unparseable))
    if s.n_over_precision:
        out.finding("A3", "fail",
                    f"{s.n_over_precision:,} value(s) carry more than the documented "
                    f"{C.VALUE_DECIMALS} decimal places",
                    n=s.n_over_precision, examples=_ex(s.over_precision))
    elif not s.n_unparseable:
        out.finding("A3", "pass",
                    f"every value parses and none exceeds {C.VALUE_DECIMALS} decimal places")


def a4_ranges(s: Scan, out) -> None:
    if s.n_out_of_range:
        out.finding("A4", "fail",
                    f"{s.n_out_of_range:,} value(s) fall outside the range their documented "
                    f"unit permits", n=s.n_out_of_range, examples=_ex(s.out_of_range))
    else:
        out.finding("A4", "pass",
                    "every value lies inside the range its documented unit permits")


def a5_duplicate_cells(s: Scan, out) -> None:
    if s.n_dupe_keys:
        out.finding("A5", "fail",
                    f"{s.n_dupe_keys:,} row(s) repeat a cell already published at the same "
                    f"grain; a reader cannot tell which value is the value",
                    n=s.n_dupe_keys, examples=_ex(s.dupe_keys))
    else:
        out.finding("A5", "pass", f"{len(s.seen_keys):,} cells, each published once")


def a6_partitions(s: Scan, out) -> None:
    """Sums the DATA declares, not sums the README claims.

    A family is enforced only once the release holds it almost everywhere. The
    tolerance is derived rather than chosen: k values each rounded to two
    decimals can miss their true total by at most k/200, so a k-term group may
    miss 100 by floor(k/2) hundredths and no more.
    """
    by_family: dict = defaultdict(list)
    for key, (total, terms) in s.part_sum.items():
        by_family[key[0]].append((total, terms))
    if not by_family:
        out.finding("A6", "skip", "no partition-family metrics in this file")
        return

    for fam, members in C.PARTITIONS.items():
        expected = len(members)
        groups = by_family.get(fam)
        if not groups:
            out.finding("A6", "skip", f"{fam}: not published in this file")
            continue
        # Only complete groups are testable. A short group is suppression, which
        # the README documents, and reading it as a violation would report the
        # release's own disclosure back to it as a defect.
        full = [(t, k) for t, k in groups if k == expected]
        if not full:
            out.finding("A6", "skip",
                        f"{fam}: no group carries all {expected} terms, so no sum is testable",
                        n=len(groups))
            continue
        if len(full) < C.PARTITION_MIN_GROUPS:
            out.finding("A6", "skip",
                        f"{fam}: only {len(full)} complete group(s), below the "
                        f"{C.PARTITION_MIN_GROUPS} needed to establish whether the release "
                        f"intends this sum", n=len(full))
            continue
        slack = expected // 2
        holds = sum(1 for t, _ in full if abs(t - 10_000) <= slack)
        share = holds / len(full)
        if share < C.PARTITION_DECLARED_AT:
            out.finding("A6", "skip",
                        f"{fam}: sums to 100 in only {share:.2%} of {len(full):,} complete "
                        f"groups, so the release does not declare this invariant and nothing "
                        f"here is a violation", n=len(full),
                        evidence={"share_holding": round(share, 6), "terms": expected})
            continue
        broken = len(full) - holds
        if broken:
            out.finding("A6", "fail",
                        f"{fam}: sums to 100 in {share:.4%} of {len(full):,} complete groups, "
                        f"so the release declares the invariant, and {broken:,} group(s) break "
                        f"it by more than the {slack/100:.2f} that rounding {expected} values "
                        f"permits", n=broken,
                        evidence={"share_holding": round(share, 6), "terms": expected,
                                  "slack_cents": slack})
        else:
            out.finding("A6", "pass",
                        f"{fam}: all {len(full):,} complete groups sum to 100 within the "
                        f"{slack/100:.2f} that rounding {expected} values permits")


def a7_hierarchy(s: Scan, out) -> None:
    if s.n_bad_depth:
        out.finding("A7", "fail",
                    f"{s.n_bad_depth:,} row(s) sit at a hierarchy_level outside the category's "
                    f"documented depth", n=s.n_bad_depth, examples=_ex(s.bad_depth))
    else:
        out.finding("A7", "pass",
                    "every hierarchy_level is within its category's documented depth")


def a8_periods(s: Scan, out) -> None:
    """Half-open calendar months that tile without gap or overlap."""
    from .checks import MONTH_START

    bad = [f"{a} -> {b}" for a, b in sorted(s.periods)
           if not (MONTH_START.match(a) and MONTH_START.match(b) and a < b)]
    if bad:
        out.finding("A8", "fail",
                    f"{len(bad)} reporting period(s) are not half-open calendar months",
                    n=len(bad), examples=_ex(bad))
        return
    ends = dict(s.periods)
    starts = sorted(ends)
    gaps = [f"{starts[i]}..{ends[starts[i]]} then {starts[i+1]}"
            for i in range(len(starts) - 1) if ends[starts[i]] != starts[i + 1]]
    if gaps:
        out.finding("A8", "fail", f"{len(gaps)} gap or overlap between reporting periods",
                    n=len(gaps), examples=_ex(gaps))
    else:
        out.finding("A8", "pass",
                    f"{len(s.periods)} reporting period(s) tile as half-open calendar months")


def a9_geo_ids(s: Scan, out) -> None:
    if s.n_bad_geo:
        out.finding("A9", "fail",
                    f"{s.n_bad_geo:,} row(s) carry a geo_id that does not match the form its "
                    f"geo_level documents", n=s.n_bad_geo, examples=_ex(s.bad_geo))
    else:
        out.finding("A9", "pass", "every geo_id matches the form its geo_level documents")


def a10_node_identity(s: Scan, out) -> None:
    """One name, two ids: anything keyed on the readable column double-counts.

    A warning, not a gate. The README defines node_external_id as the source
    identifier and never promises node_name is unique, so a collision breaks no
    published promise. It is still the thing most likely to silently corrupt a
    reader's aggregate, because node_name is the only human-readable key.
    """
    shared = {k: ids for k, ids in s.name_to_ids.items() if len(ids) > 1}
    renamed = {k: ns for k, ns in s.id_to_names.items() if len(ns) > 1}
    if not shared and not renamed:
        out.finding("A10", "pass",
                    f"node_name and node_external_id agree one-to-one across "
                    f"{len(s.name_to_ids):,} nodes")
        return
    if shared:
        out.finding("A10", "warn",
                    f"{len(shared)} node_name(s) map to more than one node_external_id at the "
                    f"same level, so grouping by name double-counts them", n=len(shared),
                    examples=_ex([f"{cat}/L{lvl} {name[:44]!r} -> ids {sorted(ids)}"
                                  for (cat, lvl, name), ids in sorted(shared.items())]),
                    evidence={"nodes_total": len(s.name_to_ids)})
    if renamed:
        out.finding("A10", "warn",
                    f"{len(renamed)} node_external_id(s) appear under more than one node_name",
                    n=len(renamed),
                    examples=_ex([f"{cat}/L{lvl} id {ext} -> {sorted(n[:38] for n in names)}"
                                  for (cat, lvl, ext), names in sorted(renamed.items())]))


def a11_published_mass(s: Scan, out) -> None:
    """How much of each distribution actually shipped.

    Reports a number and never raises an alarm, in either direction.

    An earlier version warned whenever a distribution came up short. That is a
    warning about the release's own documented suppression policy, fired back at
    the publisher as though it were a defect, on essentially every file this
    check will ever see. A finding that is guaranteed in advance carries no
    information; it just teaches the reader to skip the line. The number is the
    contribution: somebody treating `pct` as a distribution should know whether
    they are holding all of one.
    """
    if not s.pct_mass:
        out.finding("A11", "skip", "no `pct` rows in this file")
        return
    masses = sorted(s.pct_mass.values())
    n = len(masses)
    median = masses[n // 2] / 100.0
    whole = sum(1 for m in masses if m >= 9_950)
    thin = sorted((m, k) for k, m in s.pct_mass.items())[:MAX_EXAMPLES]
    out.finding("A11", "pass",
                f"`pct` distributions carry a median {median:.1f}% of their mass; {whole:,} of "
                f"{n:,} are within half a point of whole. Suppression is documented, so this "
                f"is what is missing, not what is wrong", n=n - whole,
                examples=_ex([f"{m/100:.1f}% published for {k[1]}/{k[2]}/L{k[3]} on {k[0]}"
                              for m, k in thin]),
                evidence={"median_pct_mass": median, "distributions": n, "whole": whole})


RULES = [a1_schema, a2_vocabulary, a3_precision, a4_ranges, a5_duplicate_cells,
         a6_partitions, a7_hierarchy, a8_periods, a9_geo_ids, a10_node_identity,
         a11_published_mass]


def audit(path: str | Path, out) -> Scan:
    """Scan once, then let every rule read the same aggregates."""
    s = scan(Path(path))
    for rule in RULES:
        rule(s, out)
    return s
