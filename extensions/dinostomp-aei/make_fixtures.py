"""Build the evidence tax: one clean miniature release, one mutant per check.

    python extensions/dinostomp-aei/make_fixtures.py

The clean file must produce no fail and no warn. Each mutant must produce a fail
from its own check, and the test asserts BOTH halves, because a check that fires
on everything is as useless as one that fires on nothing and looks better in a
summary.

The clean release is generated rather than hand-typed so the partition sums are
exact by construction: hand-written percentages that nearly sum to 100 would
make the clean fixture fail for reasons that have nothing to do with the checks.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from dinostomp_aei import contract as C  # noqa: E402

OUT = HERE / "dinostomp_aei" / "fixtures"
PERIODS = [("2026-04-01", "2026-05-01"), ("2026-05-01", "2026-06-01")]
NODES = [("onet", "0", "Draft a memo", "1001"), ("onet", "1", "Write things", "2001"),
         ("request", "0", "Ask for a summary", "3001"),
         ("soc_occupation", "0", "Technical Writers", "27-3042"),
         ("overall", "0", "Overall", "")]
GEOS = [("GLOBAL", "global"), ("USA", "country"), ("US-CA", "subregion")]


def split_100(k: int, seed: int) -> list[str]:
    """k percentages that sum to exactly 100.00, as two-decimal strings."""
    cents = [10_000 // k] * k
    for i in range(10_000 - sum(cents)):
        cents[i] += 1
    # Rotate so different groups differ, without changing the total.
    cents = cents[seed % k:] + cents[:seed % k]
    return [f"{c // 100}.{c % 100:02d}" for c in cents]


def clean_rows() -> list[dict]:
    rows, seed, dists = [], 0, {}
    for date_start, date_end in PERIODS:
        for geo_id, geo_level in GEOS:
            for category, level, node, ext in NODES:
                if int(level) > C.CATEGORY_DEPTH[category]:
                    continue
                seed += 1
                base = dict(date_start=date_start, date_end=date_end, geo_id=geo_id,
                            geo_level=geo_level, category_name=category,
                            hierarchy_level=level, node_name=node, node_external_id=ext)
                for family, metrics in C.PARTITIONS.items():
                    for metric, value in zip(metrics, split_100(len(metrics), seed)):
                        rows.append({**base, "metric_id": metric, "value": value})
                for metric, value in (("ai_autonomy_mean", "3.10"),
                                      ("human_only_time_mean", "1.50"),
                                      ("usage_per_capita_index", "1.00"),
                                      ("multitasking_pct", "12.00")):
                    rows.append({**base, "metric_id": metric, "value": value})
                dists.setdefault((date_start, geo_id, category, level), []).append(base)

    # `pct` is a distribution over the nodes in one (period, geography, category,
    # level), so it has to be assigned per group rather than per node. Giving
    # every node a flat 50.00 made the clean fixture publish half a distribution
    # everywhere, which is a broken fixture rather than a finding.
    for group in dists.values():
        for base, value in zip(group, split_100(len(group), 0)):
            rows.append({**base, "metric_id": "pct", "value": value})
    return rows


def write(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=C.COLUMNS)
        w.writeheader()
        w.writerows(rows)


def mutate(rows: list[dict], check: str) -> tuple[list[dict], list[str]]:
    """One planted defect, and the column order the header should use."""
    rows = [dict(r) for r in rows]
    cols = list(C.COLUMNS)
    if check == "A1":
        cols = [c for c in cols if c != "node_external_id"]   # a column goes missing
    elif check == "A2":
        rows[0]["metric_id"] = "vibes_pct"                    # undocumented metric
    elif check == "A3":
        rows[1]["value"] = "12.3456"                          # more than two decimals
    elif check == "A4":
        rows[2]["value"] = "142.00"                           # a percent above 100
    elif check == "A5":
        rows.append(dict(rows[3]))                            # the same cell twice
    elif check == "A6":
        # Break one partition group by more than rounding can explain.
        target = next(r for r in rows if r["metric_id"] == C.PARTITIONS["use_case"][0])
        target["value"] = f"{float(target['value']) + 9:.2f}"
    elif check == "A7":
        rows[4]["category_name"], rows[4]["hierarchy_level"] = "soc_occupation", "3"
    elif check == "A8":
        for r in rows:
            if r["date_start"] == "2026-05-01":
                r["date_start"] = "2026-05-15"                # no longer a calendar month
    elif check == "A9":
        for r in rows:
            if r["geo_level"] == "country":
                r["geo_id"] = "usa1"                          # not an alpha-3 code
    elif check == "A10":
        # One name, two ids: the real-world defect this check exists for.
        for r in rows:
            if r["node_external_id"] == "2001":
                r["node_name"] = "Draft a memo"
                r["hierarchy_level"] = "0"
    else:
        raise SystemExit(f"no mutation defined for {check}")
    return rows, cols


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = clean_rows()
    write(OUT / "clean.csv", rows)
    made = [f"clean.csv ({len(rows)} rows)"]
    for check in ("A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10"):
        mutated, cols = mutate(rows, check)
        path = OUT / f"mutant_{check}.csv"
        with path.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(mutated)
        made.append(path.name)
    print("wrote " + ", ".join(made))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
