"""Save legacy .xls workbooks as .xlsx through an installed Excel, so the XL
series (openpyxl) can read them. Windows only; on anything else use
`soffice --headless --convert-to xlsx <file>`.

    python audits/damodaran-ctryprem/convert_xls.py ctryprem.xls [more.xls ...]

Formulas are preserved as text. Cached values are written by Excel's own
calculation engine with calculation left automatic, which is the state
`dinostomp stomp` reads. Prints a per-sheet formula count so a values-only
export is recognised before anyone audits it for formulas it never had.
"""

from __future__ import annotations

import os
import sys

XL_CELL_TYPE_FORMULAS = -4123
XL_OPEN_XML_WORKBOOK = 51


def main(paths: list[str]) -> int:
    try:
        import win32com.client
    except ImportError:
        print("needs pywin32 and an installed Excel; elsewhere: soffice --headless --convert-to xlsx")
        return 2
    files = [os.path.abspath(p) for p in paths if os.path.exists(p)]
    if not files:
        print("no input files")
        return 2
    excel = win32com.client.DispatchEx("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False
    try:
        for path in files:
            wb = excel.Workbooks.Open(path, ReadOnly=True, UpdateLinks=0)
            total = 0
            for ws in wb.Worksheets:
                try:
                    n = ws.UsedRange.SpecialCells(XL_CELL_TYPE_FORMULAS).Count
                except Exception:  # noqa: BLE001 - Excel raises when a sheet has no formulas
                    n = 0
                total += n
            out = os.path.splitext(path)[0] + ".xlsx"
            wb.SaveAs(out, FileFormat=XL_OPEN_XML_WORKBOOK)
            wb.Close(SaveChanges=False)
            print(f"{os.path.basename(path)}: {wb_count(excel, out)} sheet(s), {total} formula cell(s) -> {os.path.basename(out)}")
    finally:
        excel.Quit()
    return 0


def wb_count(excel, out: str) -> int:
    wb = excel.Workbooks.Open(out, ReadOnly=True)
    try:
        return int(wb.Sheets.Count)
    finally:
        wb.Close(SaveChanges=False)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
