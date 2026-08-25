"""The XL series: the workbook underneath the rectangle.

Same house rule as everywhere else: a planted defect per check, and a clean
control the whole series must stay silent on.

One quirk of testing this is itself a finding worth stating. openpyxl writes
formulas but calculates nothing, so a workbook these tests build has no cached
values at all. That is exactly the state XL6 exists to name, and it means XL2
(saved error values) has to be planted as a literal error cell rather than as a
formula that would error: a `=1/0` written by a library is not an error yet,
because nothing has evaluated it. A tool claiming to find `#DIV/0!` in a file
nothing ever opened would be claiming to have run Excel.
"""

import pytest

openpyxl = pytest.importorskip("openpyxl")

from dinostomp import workbook  # noqa: E402
from dinostomp.lint import WORKBOOK_CHECKS, lint_dataset  # noqa: E402

CLEAN_HEADER = ["order_id", "vendor", "qty", "unit_price"]
CLEAN_ROWS = [
    ["ORD-1001", "Acme Corp", 10, 1200.00],
    ["ORD-1002", "Globex", 4, 300.50],
    ["ORD-1003", "Initech", 7, 88.25],
    ["ORD-1004", "Umbrella Ltd", 5, 640.00],
    ["ORD-1005", "Soylent", 12, 980.10],
    ["ORD-1006", "Hooli", 3, 150.75],
]


def build(tmp_path, *, rows=None, formulas=None, hidden_rows=(), hidden_cols=(),
          merged=(), hidden_sheet=False, name="book.xlsx"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Orders"
    ws.append(CLEAN_HEADER)
    for row in (rows if rows is not None else CLEAN_ROWS):
        ws.append(list(row))
    for ref, value in (formulas or {}).items():
        ws[ref] = value
    for index in hidden_rows:
        ws.row_dimensions[index].hidden = True
    for letter in hidden_cols:
        ws.column_dimensions[letter].hidden = True
    for ref in merged:
        ws.merge_cells(ref)
    if hidden_sheet:
        wb.create_sheet("Scratch").sheet_state = "hidden"
    path = tmp_path / name
    wb.save(path)
    return path


def audit(path):
    report, issues, _ = lint_dataset(path)
    assert report is not None, [i.message for i in issues]
    return {f["id"]: f["level"] for f in report["findings"]}, report


def detail_for(report, cid):
    return next(f["detail"] for f in report["findings"] if f["id"] == cid)


def test_the_clean_workbook_produces_no_finding_at_all(tmp_path):
    """Specificity for the XL series. An ordinary sheet must be silent."""
    levels, report = audit(build(tmp_path))
    noisy = {cid: levels[cid] for cid in WORKBOOK_CHECKS if levels.get(cid) in ("fail", "warn")}
    assert not noisy, (noisy, [detail_for(report, cid) for cid in noisy])


def test_xl5_gates_on_a_total_that_stops_short_of_its_own_column(tmp_path):
    """The Reinhart-Rogoff defect, which is the reason this module exists.

    `=SUM(C2:C5)` in a column populated to row 7 is a total that presents
    itself as complete and is not. No amount of reading the rendered numbers
    finds this; reading the formula finds it immediately.
    """
    levels, report = audit(build(tmp_path, formulas={"C9": "=SUM(C2:C5)"}))
    assert levels["XL5"] == "fail"
    detail = detail_for(report, "XL5")
    assert "stop above the last populated row" in detail
    examples = next(f["examples"] for f in report["findings"] if f["id"] == "XL5")
    assert any("=SUM(C2:C5)" in e and "6" in e for e in examples), examples


def test_xl5_stays_quiet_when_subtotals_between_them_cover_everything(tmp_path):
    """The false positive that would make XL5 unusable.

    A block of subtotals is the normal shape of a real financial sheet. Each
    one covers a slice, and no row is left out, so nothing is wrong and nothing
    must be reported. Only a row covered by NO aggregate is the defect.
    """
    levels, report = audit(build(tmp_path, formulas={
        "C9": "=SUM(C2:C4)", "C10": "=SUM(C5:C7)"}))
    assert levels["XL5"] == "pass", detail_for(report, "XL5")


def test_xl2_gates_on_a_saved_error_value(tmp_path):
    """A `#REF!` is a calculation that failed and was then saved and reported."""
    levels, report = audit(build(tmp_path, formulas={"D8": "#REF!"}))
    assert levels["XL2"] == "fail"
    assert "#REF!" in detail_for(report, "XL2")


def test_xl1_catches_a_constant_pasted_over_a_formula(tmp_path):
    """The cell keeps showing the right number and stops tracking its inputs,
    which is why this survives every review that reads the rendered sheet."""
    formulas = {f"E{i}": f"=C{i}*D{i}" for i in range(2, 8)}
    formulas["E5"] = 4321
    levels, report = audit(build(tmp_path, formulas=formulas))
    assert levels["XL1"] == "warn"
    assert "E5" in detail_for(report, "XL1") or any(
        "E5" in e for e in next(f["examples"] for f in report["findings"] if f["id"] == "XL1"))


def test_xl3_catches_hidden_rows_columns_and_sheets(tmp_path):
    levels, report = audit(build(tmp_path, hidden_rows=(3,), hidden_cols=("D",),
                                 hidden_sheet=True))
    assert levels["XL3"] == "warn"
    detail = detail_for(report, "XL3")
    assert "hidden row" in detail and "hidden column" in detail and "hidden sheet" in detail


def test_xl4_catches_a_merged_range(tmp_path):
    levels, report = audit(build(tmp_path, merged=("A9:C9",)))
    assert levels["XL4"] == "warn"
    assert "1 merged range" in detail_for(report, "XL4")
    examples = next(f["examples"] for f in report["findings"] if f["id"] == "XL4")
    assert any("A9:C9" in e for e in examples), examples


def test_xl6_reports_a_library_written_file_as_never_opened_not_as_a_defect(tmp_path):
    """Calibration, and the reason this is a pass rather than a warning.

    EVERY formula uncached means no spreadsheet application has ever opened the
    file. That is a fact about provenance, not a defect in someone's model, and
    reporting it as one would fire on every programmatically generated workbook
    and teach people to ignore the check.
    """
    levels, report = audit(build(tmp_path, formulas={"C9": "=SUM(C2:C7)"}))
    assert levels["XL6"] == "pass"
    assert "never been opened" in detail_for(report, "XL6")


def test_xl6_warns_when_only_some_formulas_are_uncalculated():
    """The case that means something, built directly because openpyxl cannot
    write a partially-cached file: some formulas carry a result and some do
    not, so a reader of values sees blanks scattered among real numbers."""
    sheet = workbook.Sheet(
        name="Orders",
        formulas={(2, 3): "=A2*2", (3, 3): "=A3*2", (4, 3): "=A4*2"},
        values={(2, 3): 10, (3, 3): 20},          # row 4 never calculated
        dims=(set(), set()), merged=[], state="visible")
    ok, detail, _, _, _ = workbook.check_uncalculated([sheet])
    assert ok is False
    assert "1 of 3" in detail
    assert "STALE" in detail, "the check must say what it does NOT claim to detect"


def test_the_xl_series_skips_loudly_without_openpyxl(tmp_path, monkeypatch):
    """The Pillow rule, applied to workbooks: a check that cannot see must
    never read as a check that saw nothing wrong."""
    path = build(tmp_path)
    monkeypatch.setattr(workbook, "available", lambda: False)
    from dinostomp import lint

    rep = lint.Reporter()
    lint._table_checks(rep, [{"a": 1}], path)
    for cid in WORKBOOK_CHECKS:
        finding = rep.findings[cid]
        assert finding.level == "skip"
        assert "openpyxl" in finding.detail and "pip install" in finding.detail


def test_a_csv_marks_the_workbook_checks_not_applicable(tmp_path):
    """A .csv has no formulas to read, so the XL checks are `n/a` and leave the
    denominator rather than counting as evidence nobody gathered."""
    path = tmp_path / "flat.csv"
    path.write_text("order_id,vendor,qty\nORD-1,Acme,3\nORD-2,Globex,4\n"
                    "ORD-3,Initech,5\nORD-4,Hooli,6\nORD-5,Soylent,7\n", encoding="utf-8")
    _, report = audit(path)
    for cid in WORKBOOK_CHECKS:
        finding = next(f for f in report["findings"] if f["id"] == cid)
        assert finding["level"] == "n/a", finding
        assert "xlsx" in finding["detail"]
