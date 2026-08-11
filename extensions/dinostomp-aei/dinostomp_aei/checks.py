"""Eleven checks on an Anthropic Economic Index release, in one streaming pass.

WHY STREAMING. The claude_ai file is 209MB and the core dataset audit refuses it
at a 100MB read cap, correctly: it builds a list of every row. Nothing here holds
more than the running aggregates, so the size of the file stops mattering and the
cap stops being the reason an audit cannot happen.

WHY INTEGER CENTS. Values are published rounded to two decimals, so a partition
of k terms may legitimately miss 100 by up to k/200. Testing that in floating
point produced a violation on `40.63 + 59.38`, which is 100.01 exactly, sits
exactly on the permitted bound, and is what tie-rounding 40.625 and 59.375 does.
The check would have reported a rounding convention as a defect in somebody
else's published data. Everything below counts hundredths as integers.

WHAT THESE CHECKS ARE NOT. None of them can tell you a published number is
correct. They compare a release against the contract its own README states, and
against invariants the data itself holds everywhere else. A release can satisfy
all eleven and still be measuring the wrong thing.
"""

from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from hashlib import blake2b
from pathlib import Path

from . import contract as C

csv.field_size_limit(10_000_000)

ISO3 = re.compile(r"^[A-Z]{3}$")
ISO_SUBREGION = re.compile(r"^[A-Z]{2}-[A-Z0-9]{1,3}$")
MONTH_START = re.compile(r"^\d{4}-\d{2}-01$")

# The grain a single published cell is keyed at. Two rows sharing all of this
# are two values for one thing.
KEY = ("date_start", "date_end", "geo_id", "geo_level", "category_name",
       "hierarchy_level", "metric_id", "node_name", "node_external_id")

MAX_EXAMPLES = 5


@dataclass
class Scan:
    """Everything one pass over the file needs to remember.

    Deliberately all counters and small maps. The largest structure is one
    integer per (partition family, cell group), which is bounded by the number of
    published nodes rather than by the number of rows.
    """

    n_rows: int = 0
    columns: list[str] = field(default_factory=list)
    bad_columns: str = ""

    unknown_metric: Counter = field(default_factory=Counter)
    unknown_geo_level: Counter = field(default_factory=Counter)
    unknown_category: Counter = field(default_factory=Counter)

    over_precision: list[str] = field(default_factory=list)
    n_over_precision: int = 0
    unparseable: list[str] = field(default_factory=list)
    n_unparseable: int = 0

    out_of_range: list[str] = field(default_factory=list)
    n_out_of_range: int = 0

    seen_keys: set = field(default_factory=set)
    dupe_keys: list[str] = field(default_factory=list)
    n_dupe_keys: int = 0

    # (family, date_start, geo_id, category, level, node_name, node_external_id)
    # -> [sum in cents, term count]
    part_sum: dict = field(default_factory=lambda: defaultdict(lambda: [0, 0]))

    bad_depth: list[str] = field(default_factory=list)
    n_bad_depth: int = 0

    periods: set = field(default_factory=set)

    bad_geo: list[str] = field(default_factory=list)
    n_bad_geo: int = 0

    name_to_ids: dict = field(default_factory=lambda: defaultdict(set))
    id_to_names: dict = field(default_factory=lambda: defaultdict(set))

    # (date_start, geo_id, category, level) -> sum of `pct` in cents
    pct_mass: dict = field(default_factory=lambda: defaultdict(int))


def _cents(raw: str) -> tuple[int | None, int]:
    """A published value as hundredths, plus how many decimal places it carried.

    Decimal, not float: the question "does this have more than two decimal
    places" is about the printed representation, and float parsing throws that
    away before the check can see it.
    """
    try:
        d = Decimal(raw.strip())
    except (InvalidOperation, AttributeError):
        return None, -1
    places = max(0, -d.as_tuple().exponent)
    return int((d * 100).to_integral_value()), places


def scan(path: Path) -> Scan:
    """One pass. Everything every check needs, gathered once."""
    s = Scan()
    metric_units = C.METRIC_UNITS
    of_family = {m: fam for fam, ms in C.PARTITIONS.items() for m in ms}

    with Path(path).open(encoding="utf-8", newline="") as fh:
        rdr = csv.DictReader(fh)
        s.columns = list(rdr.fieldnames or [])
        if s.columns != C.COLUMNS:
            missing = [c for c in C.COLUMNS if c not in s.columns]
            extra = [c for c in s.columns if c not in C.COLUMNS]
            if missing or extra:
                s.bad_columns = f"missing {missing}, unexpected {extra}"
            else:
                s.bad_columns = f"documented order is {C.COLUMNS}, file has {s.columns}"
                # Order alone is cosmetic; keep scanning.
            if missing:
                return s

        for row in rdr:
            s.n_rows += 1
            metric = row["metric_id"]
            geo_level = row["geo_level"]
            category = row["category_name"]

            if metric not in metric_units:
                s.unknown_metric[metric] += 1
            if geo_level not in C.GEO_LEVELS:
                s.unknown_geo_level[geo_level] += 1
            if category not in C.CATEGORY_DEPTH:
                s.unknown_category[category] += 1

            cents, places = _cents(row["value"])
            if cents is None:
                s.n_unparseable += 1
                if len(s.unparseable) < MAX_EXAMPLES:
                    s.unparseable.append(f"{metric}={row['value']!r} at {row['node_name'][:40]!r}")
            else:
                if places > C.VALUE_DECIMALS:
                    s.n_over_precision += 1
                    if len(s.over_precision) < MAX_EXAMPLES:
                        s.over_precision.append(f"{metric}={row['value']} ({places} dp)")
                unit = metric_units.get(metric)
                if unit:
                    lo, hi = C.UNIT_RANGE[unit]
                    v = cents / 100.0
                    if (lo is not None and v < lo) or (hi is not None and v > hi):
                        s.n_out_of_range += 1
                        if len(s.out_of_range) < MAX_EXAMPLES:
                            s.out_of_range.append(
                                f"{metric}={v} outside [{lo}, {hi}] ({unit}) "
                                f"at {row['geo_id']}/{row['node_name'][:30]!r}")

            # A 16-byte digest, not the tuple. Holding 1.6M nine-string tuples
            # cost 1.19GB on the claude_ai release, which is most of a budget
            # laptop for a set membership test. blake2b at 16 bytes puts the
            # chance of a spurious collision across this many keys around 1e-25,
            # which matters because a false duplicate reported against somebody
            # else's published data is the worst output this tool has.
            key = blake2b("\x00".join(row[c] for c in KEY).encode("utf-8"),
                          digest_size=16).digest()
            if key in s.seen_keys:
                s.n_dupe_keys += 1
                if len(s.dupe_keys) < MAX_EXAMPLES:
                    s.dupe_keys.append(f"{row['geo_id']}/{category}/L{row['hierarchy_level']}"
                                       f"/{metric}/{row['node_name'][:34]!r}")
            else:
                s.seen_keys.add(key)

            fam = of_family.get(metric)
            if fam and cents is not None:
                gkey = (fam, row["date_start"], row["geo_id"], category,
                        row["hierarchy_level"], row["node_name"], row["node_external_id"])
                bucket = s.part_sum[gkey]
                bucket[0] += cents
                bucket[1] += 1

            depth = C.CATEGORY_DEPTH.get(category)
            if depth is not None:
                try:
                    lvl = int(row["hierarchy_level"])
                except ValueError:
                    lvl = -1
                if not 0 <= lvl <= depth:
                    s.n_bad_depth += 1
                    if len(s.bad_depth) < MAX_EXAMPLES:
                        s.bad_depth.append(
                            f"{category} level {row['hierarchy_level']!r}, documented depth "
                            f"0..{depth}, node {row['node_name'][:34]!r}")

            s.periods.add((row["date_start"], row["date_end"]))

            geo = row["geo_id"]
            ok = (geo == "GLOBAL" if geo_level == "global"
                  else bool(ISO3.match(geo)) if geo_level == "country"
                  else bool(ISO_SUBREGION.match(geo)) if geo_level == "subregion"
                  else True)
            if not ok:
                s.n_bad_geo += 1
                if len(s.bad_geo) < MAX_EXAMPLES:
                    s.bad_geo.append(f"{geo!r} at geo_level={geo_level!r}")

            ext = row["node_external_id"]
            if ext:
                s.name_to_ids[(category, row["hierarchy_level"], row["node_name"])].add(ext)
                s.id_to_names[(category, row["hierarchy_level"], ext)].add(row["node_name"])

            if metric == "pct" and cents is not None:
                s.pct_mass[(row["date_start"], geo, category, row["hierarchy_level"])] += cents

    return s
