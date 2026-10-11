"""Extract per-row formula templates and sample billing column for algorithm docs."""
from __future__ import annotations

from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

XLSX = Path(r"c:\Users\rober\OneDrive\Hausverwaltung_Vahrn\Abrechnung_KondominiumVitroler_V2.xlsx")
OUT = Path(r"d:\Coding\Abrechnung-Vitroler\analysis_output")


def main():
    wb = load_workbook(XLSX, data_only=False)
    wb_v = load_workbook(XLSX, data_only=True)
    ws = wb["Verrechnung"]
    ws_v = wb_v["Verrechnung"]

    lines = []

    # Row map A/B/C for all rows
    lines.append("=== ROW MAP (A=Znr, B=Beschreibung, C=Kommentar) ===")
    for r in range(1, (ws.max_row or 0) + 1):
        a, b, c = ws.cell(r, 1).value, ws.cell(r, 2).value, ws.cell(r, 3).value
        if a is None and b is None and c is None:
            continue
        lines.append(f"R{r}: A={a!r} | B={b!r} | C={c!r}")

    # For each data row 3-74, find first formula and first input in columns E..
    lines.append("\n=== PER-ROW CELL TYPE + EXAMPLE FORMULA (cols E onwards) ===")
    for r in range(1, 75):
        b = ws.cell(r, 2).value
        sample_f = None
        sample_i = None
        n_formula = 0
        n_input = 0
        n_empty = 0
        for c in range(5, (ws.max_column or 0) + 1):
            v = ws.cell(r, c).value
            if v is None:
                n_empty += 1
                continue
            if isinstance(v, str) and v.startswith("="):
                n_formula += 1
                if sample_f is None:
                    sample_f = (get_column_letter(c), v, ws_v.cell(r, c).value)
            else:
                n_input += 1
                if sample_i is None:
                    sample_i = (get_column_letter(c), v)

        lines.append(
            f"R{r} '{b}': formulas={n_formula}, inputs={n_input}, empty={n_empty}"
        )
        if sample_f:
            lines.append(f"  formula_ex {sample_f[0]}{r}={sample_f[1]} => {sample_f[2]!r}")
        if sample_i:
            lines.append(f"  input_ex {sample_i[0]}{r}={sample_i[1]!r}")

    # Pick a rich billing column: look for non-empty Rechnungsbetrag (row 40)
    lines.append("\n=== BILLING COLUMNS (row40 Rechnungsbetrag non-empty) ===")
    billing_cols = []
    for c in range(5, (ws.max_column or 0) + 1):
        v = ws.cell(40, c).value
        if v is None:
            continue
        billing_cols.append(c)
        letter = get_column_letter(c)
        period = ws.cell(41, c).value
        begin = ws.cell(42, c).value
        end = ws.cell(43, c).value
        amount = v
        amount_c = ws_v.cell(40, c).value
        inv = ws.cell(39, c).value
        lines.append(
            f"  Col {letter}: invoice={inv!r} amount={amount!r}/{amount_c!r} "
            f"period_label={period!r} begin={begin!r} end={end!r}"
        )

    # Dump full vertical slice for last few billing columns with formulas+values for rows 38-74
    for c in billing_cols[-3:]:
        letter = get_column_letter(c)
        lines.append(f"\n=== FULL BILLING SLICE COL {letter} (rows 1-74 + 79-85) ===")
        for r in list(range(1, 75)) + list(range(79, 86)):
            b = ws.cell(r, 2).value
            v = ws.cell(r, c).value
            cv = ws_v.cell(r, c).value
            if v is None and b is None:
                continue
            if isinstance(v, str) and v.startswith("="):
                lines.append(f"  {letter}{r} ({b}): {v} => {cv!r}")
            else:
                lines.append(f"  {letter}{r} ({b}): INPUT {v!r} / calc={cv!r}")

    # Special formulas: WW 1OG residual, KW Gesamt - WW, Wärmemenge, Anteile, Preise
    lines.append("\n=== KEY FORMULA VARIANTS ACROSS COLUMNS (selected rows) ===")
    key_rows = [6, 11, 17, 20, 21, 22, 23, 24, 25, 27, 28, 29, 30, 33, 34, 35, 36,
                42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58,
                59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 71, 72, 73, 74]
    for r in key_rows:
        b = ws.cell(r, 2).value
        uniq = {}
        for c in range(5, (ws.max_column or 0) + 1):
            v = ws.cell(r, c).value
            if isinstance(v, str) and v.startswith("="):
                # normalize by replacing column letters roughly: keep relative structure
                uniq.setdefault(v, 0)
                # store first occurrence per unique absolute formula string pattern
                # Better: collect unique after replacing the column letter of current col
                letter = get_column_letter(c)
                # replace this column letter with COL
                # simplistic: show first 3 unique absolute formulas
        formulas_seen = []
        for c in range(5, (ws.max_column or 0) + 1):
            v = ws.cell(r, c).value
            if isinstance(v, str) and v.startswith("="):
                letter = get_column_letter(c)
                # template: replace this letter with X (whole-cell tokens)
                tmpl = v.replace(letter, "X")
                if tmpl not in [t for t, _ in formulas_seen]:
                    formulas_seen.append((tmpl, f"{letter}{r}={v}"))
            elif v is not None and not (isinstance(v, str) and v.startswith("=")):
                tmpl = f"INPUT:{type(v).__name__}"
                if tmpl not in [t for t, _ in formulas_seen]:
                    formulas_seen.append((tmpl, f"{get_column_letter(c)}{r}={v!r}"))
        lines.append(f"\nR{r} '{b}':")
        for tmpl, ex in formulas_seen[:8]:
            lines.append(f"  tmpl={tmpl} | ex={ex}")

    # Bottom area rows 75-85
    lines.append("\n=== BOTTOM AREA rows 75-85 all non-empty ===")
    for r in range(75, 86):
        for c in range(1, (ws.max_column or 0) + 1):
            v = ws.cell(r, c).value
            if v is None:
                continue
            cv = ws_v.cell(r, c).value
            lines.append(f"  {get_column_letter(c)}{r}: {v!r} => {cv!r}")

    # Comments column D?
    lines.append("\n=== COLUMN D samples ===")
    for r in range(1, 86):
        v = ws.cell(r, 4).value
        if v is not None:
            lines.append(f"  D{r}: {v!r}")

    # Check Zirkulation usage in formulas
    lines.append("\n=== CELLS referencing rows 12,13,31,32 (Zirkulation) ===")
    for r in range(1, 86):
        for c in range(1, (ws.max_column or 0) + 1):
            v = ws.cell(r, c).value
            if isinstance(v, str) and v.startswith("="):
                if any(x in v for x in ["12", "13", "31", "32"]):
                    # only if actually those rows referenced carefully
                    import re
                    if re.search(r"[A-Z]+(12|13|31|32)(?!\d)", v):
                        lines.append(f"  {get_column_letter(c)}{r}: {v}")

    out = OUT / "billing_logic.txt"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out}")
    print(f"Billing columns found: {len(billing_cols)}")
    for c in billing_cols:
        print(f"  {get_column_letter(c)} amount={ws.cell(40,c).value} period={ws.cell(41,c).value}")


if __name__ == "__main__":
    main()
