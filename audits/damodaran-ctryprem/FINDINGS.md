# Damodaran country risk premiums: workbook audit

    file     https://pages.stern.nyu.edu/~adamodar/pc/datasets/ctryprem.xls
    served   Last-Modified Tue, 27 Jan 2026 15:37:13 GMT, 994,304 bytes
    sha256   66135df68bc4c8830830a29f9017f848968d85712ff7ba2627c8355d04fae784
    run      2026-09-17, 0 API calls, $0.00

The January 2026 update of Aswath Damodaran's country equity risk premium
workbook (NYU Stern): 18 sheets, 11,291 formulas. Ledger entries
[F-050](../../FINDINGS.md#f-050), [D-093](../../FINDINGS.md#d-093).

## Reproduce

The file is a legacy binary `.xls`, which openpyxl cannot open. Save it as
`.xlsx` first, with calculation left automatic so cached values are written:

```bash
python audits/damodaran-ctryprem/convert_xls.py ctryprem.xls   # Excel via COM, Windows
# or: soffice --headless --convert-to xlsx ctryprem.xls          # LibreOffice, anywhere
pip install 'dinostomp[xlsx]'
dinostomp stomp ctryprem.xlsx
```

## What fires, and what it means

```
[FAIL] formula-error   230 error cell(s) saved in the workbook: #N/A x229, #REF! x1
         - 10-year CDS Spreads!J91: #REF! from =IF(#REF!="NA","NA",IF(#REF!<$I$103,0,#REF!-$I$103))
[warn] sentinel-values 48 cell(s) look like missing-value placeholders ('#N/A')
[warn] pasted-constant 76 constant(s) pasted into formula column(s) across 11 sheet(s)
[warn] merged-cells    10 merged range(s) across 6 sheet(s)
```

- **`#N/A` x229**: by design. `VLOOKUP`s for countries without a sovereign CDS
  return an error where the rest of the workbook writes `"NA"`. Sixteen
  countries' CDS-based premiums read as errors to any importer.
- **`#REF!` x1, and the row beneath it**: `10-year CDS Spreads` columns H:J are
  an auxiliary list of spreads net of Switzerland. J91 (Romania) is a deleted
  reference; J92 (Russia) reads `I91`, the row above, so it holds Romania's
  net spread. Nothing in the workbook reads columns H, I or J of that sheet;
  the premiums that leave the workbook come from column D, computed correctly
  from column C and reached by 315 `VLOOKUP`s on `$A$2:$D$158`. **No published
  number is affected.**
- **`pasted-constant` x76**: section headers typed inside formula columns.
  Layout, not arithmetic.

Before D-093, `range-short` also gated twice on this workbook
(`Relative Equity Volatility!B7 = AVERAGE(B2:B6)` and
`Regional Weighted Averages!B32 = SUM(B2:B31)`). Both were the tool reaching
past a blank row into an unrelated table sharing the column. Fixed; neither
fires now.

## Honest scoping

- The file was read as saved. Nothing here recomputes a premium or checks a
  formula's economics; that is construct validity, which this tool does not
  establish.
- The `.xls` to `.xlsx` conversion preserves formulas and writes cached values
  from the converting application's calculation engine. The `#REF!` and the
  `I91` reference are formula text and survive conversion unchanged.
