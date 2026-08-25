"""The G series: hygiene for a table that was never an eval.

House rule: a test that only proves a check passes on clean data proves
nothing. Every check here gets a defect planted on purpose and an assertion
that THAT check caught it, plus a clean control asserting the whole series
stays silent. The second arm is the one that matters: a battery loud enough to
catch every planted defect will also condemn every innocent file, and only the
control tells the difference.

The clean control is deliberately awkward. It carries a legitimately repeating
order id (a line-item table, the single most common spreadsheet shape there
is), a genuinely narrow text column, real decimals and real dates. If the
series fires on that, the series is wrong.
"""

import csv

import pytest

from dinostomp import tabular
from dinostomp.lint import GRID_CHECKS, lint_dataset

CLEAN_HEADER = ["order_id", "line_no", "vendor", "region", "qty", "unit_price",
                "ship_date", "note"]
# One order spanning three lines: `order_id` repeats BY DESIGN. G3 fires on a
# near-unique identifier column, and this is the shape that proves it must not
# fire on a legitimate one.
CLEAN_ROWS = [
    ["ORD-1001", "1", "Acme Corp", "West", "10", "1200.00", "2026-01-05", "first"],
    ["ORD-1001", "2", "Acme Corp", "West", "4", "300.50", "2026-01-05", "second"],
    ["ORD-1001", "3", "Acme Corp", "West", "7", "88.25", "2026-01-05", "third"],
    ["ORD-1002", "1", "Globex", "East", "5", "640.00", "2026-01-06", "fourth"],
    ["ORD-1003", "1", "Initech", "North", "12", "980.10", "2026-01-07", "fifth"],
    ["ORD-1004", "1", "Umbrella Ltd", "South", "3", "150.75", "2026-01-08", "sixth"],
    ["ORD-1005", "1", "Soylent", "West", "8", "220.00", "2026-01-09", "seventh"],
    ["ORD-1006", "1", "Hooli", "East", "6", "410.40", "2026-01-10", "eighth"],
]


def write_table(tmp_path, header, rows, name="table.csv"):
    path = tmp_path / name
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)
    return path


def audit(tmp_path, header, rows):
    """Run the real CLI path and return {check_id: level}."""
    path = write_table(tmp_path, header, rows)
    report, issues, _ = lint_dataset(path)
    assert report is not None, [i.message for i in issues]
    assert report["summary"]["scope"] == "table"
    return {f["id"]: f["level"] for f in report["findings"]}, report


def detail_for(report, cid):
    return next(f["detail"] for f in report["findings"] if f["id"] == cid)


def test_the_clean_control_produces_no_finding_at_all():
    """Specificity. Nothing below this line is worth anything without it."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        levels, report = audit(Path(tmp), CLEAN_HEADER, CLEAN_ROWS)
    noisy = {cid: levels[cid] for cid in GRID_CHECKS
             if levels.get(cid) in ("fail", "warn")}
    assert not noisy, (noisy, [detail_for(report, cid) for cid in noisy])


def test_g3_does_not_fire_on_a_line_item_table(tmp_path):
    """The false positive that would make G3 unusable in the real world.

    An order id that repeats across the lines of one order is not a duplicate
    key, it is what a line-item table IS. G3 only speaks about a column that is
    NEARLY unique, and this asserts the boundary from the safe side.
    """
    levels, _ = audit(tmp_path, CLEAN_HEADER, CLEAN_ROWS)
    assert levels["G3"] == "pass"


def test_a_table_too_small_to_profile_is_refused_rather_than_passed(tmp_path):
    """The table audit must not become a way to earn a clean bill of health.

    Below the profiling floor almost every check has nothing to measure and
    would report a pass over a handful of rows. That is the vacuous pass the
    Reporter refuses everywhere else, so a two-row aggregate is still a dead
    end, and the refusal says why rather than repeating "no input column".
    """
    path = write_table(tmp_path, ["geo", "metric", "value"],
                       [["GLOBAL", "pct", "50.0"], ["EU", "pct", "40.0"]])
    report, issues, _ = lint_dataset(path)
    assert report is None
    assert any("too few to audit as a table" in i.message for i in issues), \
        [i.message for i in issues]


def test_g1_catches_a_non_breaking_space(tmp_path):
    """The defect that silently breaks every join and is invisible on screen."""
    rows = [r[:] for r in CLEAN_ROWS]
    rows[2][2] = "Acme Corp"
    levels, report = audit(tmp_path, CLEAN_HEADER, rows)
    assert levels["G1"] == "warn"
    assert "NO-BREAK SPACE" in detail_for(report, "G1")


def test_g1_catches_trailing_whitespace(tmp_path):
    rows = [r[:] for r in CLEAN_ROWS]
    rows[1][2] = "Acme Corp "
    levels, _ = audit(tmp_path, CLEAN_HEADER, rows)
    assert levels["G1"] == "warn"


def test_g2_gates_on_a_byte_identical_row(tmp_path):
    """A duplicate row is a deterministic fact, so it fails rather than warns."""
    rows = CLEAN_ROWS + [CLEAN_ROWS[3][:]]
    levels, report = audit(tmp_path, CLEAN_HEADER, rows)
    assert levels["G2"] == "fail"
    assert "1 duplicate row" in detail_for(report, "G2")


def test_g3_catches_a_violated_identifier(tmp_path):
    """A column named like an id, nearly unique, with one repeat: a key with a
    hole in it, which is how a join silently doubles a total."""
    header = ["invoice_id", "vendor", "amount"]
    rows = [[f"INV-{i:04d}", "Acme", str(100 + i)] for i in range(12)]
    rows[7][0] = rows[2][0]
    levels, report = audit(tmp_path, header, rows)
    assert levels["G3"] == "warn"
    assert "invoice_id" in detail_for(report, "G3")


def test_g4_reports_leading_zeros_and_refuses_to_want_them_gone(tmp_path):
    """THE check this module exists to get right.

    The finding must state what a conversion would destroy and must not present
    itself as repairable, because the file cannot say whether these are zip
    codes or quantities.
    """
    header = ["zip", "city"]
    rows = [["00501", "Holtsville"], ["02134", "Boston"], ["07001", "Avenel"],
            ["08540", "Princeton"], ["10001", "New York"], ["01887", "Wilmington"]]
    levels, report = audit(tmp_path, header, rows)
    assert levels["G4"] == "warn"
    detail = detail_for(report, "G4")
    assert "zip" in detail
    assert "auto-repairable" in detail and "cannot say which" in detail


def test_g5_catches_a_column_written_two_ways(tmp_path):
    rows = [r[:] for r in CLEAN_ROWS]
    rows[4][6] = "07/01/2026"
    levels, report = audit(tmp_path, CLEAN_HEADER, rows)
    assert levels["G5"] == "warn"
    assert "mixing date formats" in detail_for(report, "G5")


def test_g5_catches_a_locale_ambiguous_column(tmp_path):
    """Every value parses both ways and gives a different date either way. The
    file cannot resolve this, and neither can the tool, so it says so."""
    header = ["ship_date", "note"]
    rows = [["01/02/2026", "a"], ["03/04/2026", "b"], ["05/06/2026", "c"],
            ["07/08/2026", "d"], ["09/10/2026", "e"], ["11/12/2026", "f"]]
    levels, report = audit(tmp_path, header, rows)
    assert levels["G5"] == "warn"
    assert "locale-ambiguous" in detail_for(report, "G5")
    examples = next(f["examples"] for f in report["findings"] if f["id"] == "G5")
    assert any("both parse" in e for e in examples), examples


def test_g6_catches_text_in_a_numeric_column(tmp_path):
    """One `n/a` in a quantity column turns every downstream SUM into text."""
    rows = [r[:] for r in CLEAN_ROWS]
    rows[5][4] = "n/a"
    levels, report = audit(tmp_path, CLEAN_HEADER, rows)
    assert levels["G6"] == "warn"
    assert "qty" in detail_for(report, "G6")


def test_g7_catches_a_repeated_numeric_sentinel(tmp_path):
    """One 999999 is a value. Four of them in a price column is a convention
    nobody wrote down, and every average over that column is wrong."""
    rows = [r[:] for r in CLEAN_ROWS]
    for i in (1, 3, 5, 7):
        rows[i][5] = "999999"
    levels, report = audit(tmp_path, CLEAN_HEADER, rows)
    assert levels["G7"] == "warn"
    assert "999999" in detail_for(report, "G7")


def test_g7_does_not_fire_on_a_single_odd_number(tmp_path):
    """The specificity half of G7: one -1 is data, not a sentinel."""
    rows = [r[:] for r in CLEAN_ROWS]
    rows[2][4] = "-1"
    levels, _ = audit(tmp_path, CLEAN_HEADER, rows)
    assert levels["G7"] == "pass"


def test_g8_catches_a_group_by_that_would_split(tmp_path):
    """The ecommerce finding, automated: `West` and `west` are two groups in
    every database and one region in every human's head."""
    rows = [r[:] for r in CLEAN_ROWS]
    rows[3][3] = "east"
    rows[6][3] = "WEST"
    levels, report = audit(tmp_path, CLEAN_HEADER, rows)
    assert levels["G8"] == "warn"
    detail = detail_for(report, "G8")
    assert "region" in detail and "grouping" in detail


def test_g8_does_not_fire_on_free_text(tmp_path):
    """A notes column of distinct sentences is not a category column, and
    normalising it would be meaningless."""
    header = ["id", "notes"]
    rows = [[str(i), f"a distinct sentence number {i} about something"] for i in range(10)]
    levels, _ = audit(tmp_path, header, rows)
    assert levels["G8"] == "pass"


def test_g9_catches_two_scales_in_one_rate_column(tmp_path):
    header = ["vendor", "margin_pct"]
    rows = [["Acme", "0.15"], ["Globex", "0.20"], ["Initech", "18"],
            ["Umbrella", "0.11"], ["Soylent", "22"], ["Hooli", "0.09"]]
    levels, report = audit(tmp_path, header, rows)
    assert levels["G9"] == "warn"
    assert "two scales" in detail_for(report, "G9")


def test_g10_catches_currency_formatted_numbers(tmp_path):
    rows = [r[:] for r in CLEAN_ROWS]
    for row in rows:
        row[5] = f"${float(row[5]):,.2f}"
    levels, report = audit(tmp_path, CLEAN_HEADER, rows)
    assert levels["G10"] == "warn"
    assert "unit_price" in detail_for(report, "G10")


def test_g11_catches_a_near_duplicate_row_g2_cannot_see(tmp_path):
    """G11 reports only what G2 could not, so the two never double-count."""
    near = CLEAN_ROWS[3][:]
    near[2] = near[2].upper()
    levels, report = audit(tmp_path, CLEAN_HEADER, CLEAN_ROWS + [near])
    assert levels["G11"] == "warn"
    assert levels["G2"] == "pass", "an exact-duplicate check must not claim a near duplicate"


def test_g4_and_g6_disagree_on_purpose():
    """The two checks that are the same phenomenon pointing opposite ways.

    A digit-string column with leading zeros is CORRECT as text (G4 reports
    what converting would destroy) and a numeric column with text in it is
    BROKEN (G6 reports contamination). A tool that auto-fixed either would be
    wrong about the other, which is the argument, in executable form, for
    proposing rather than repairing.
    """
    zips = [{"zip": z} for z in ("00501", "02134", "07001", "08540", "10001", "01887")]
    profiles = tabular.profile(zips)
    assert tabular.check_numeric_strings(zips, profiles)[0] is False
    assert tabular.check_type_drift(zips, profiles)[0] is True, \
        "a text code column must not be reported as a contaminated numeric column"


@pytest.mark.parametrize("value,expected", [
    ("1,200.50", 1200.5), ("$1,200.50", 1200.5), ("(1,200.50)", -1200.5),
    ("1200.50-", -1200.5), ("€900", 900.0), ("12%", 12.0),
    ("", None), ("n/a", None), ("1.2.3", None), ("12 monkeys", None),
])
def test_as_number_reads_what_a_spreadsheet_renders(value, expected):
    assert tabular.as_number(value) == expected
