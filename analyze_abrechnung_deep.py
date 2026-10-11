"""Deep structural analysis of Verrechnung sheet billing logic."""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

XLSX = Path(r"c:\Users\rober\OneDrive\Hausverwaltung_Vahrn\Abrechnung_KondominiumVitroler_V2.xlsx")
OUT = Path(r"d:\Coding\Abrechnung-Vitroler\analysis_output")


def addr(r, c):
    return f"{get_column_letter(c)}{r}"


def normalize_formula(f: str) -> str:
    """Replace cell refs with placeholders to cluster formula patterns."""
    # sheet refs
    f2 = re.sub(r"'[^']+'!", "{SHEET}!", f)
    f2 = re.sub(r"[A-Za-z]+[0-9]+", "{CELL}", f2)
    f2 = re.sub(r"\{CELL\}:\{CELL\}", "{RANGE}", f2)
    return f2


def main():
    wb = load_workbook(XLSX, data_only=False)
    wb_v = load_workbook(XLSX, data_only=True)
    ws = wb["Verrechnung"]
    ws_v = wb_v["Verrechnung"]

    mr, mc = ws.max_row, ws.max_column
    print(f"Sheet Verrechnung: {mr} x {mc}")

    # --- Row 1..30 full dump of first columns for layout ---
    lines = []
    lines.append(f"DIMENSIONS: {mr} rows x {mc} cols")
    lines.append(f"MERGED: {[str(m) for m in ws.merged_cells.ranges]}")
    lines.append("")

    # Dump first 80 rows completely (all non-empty)
    lines.append("=== FIRST 80 ROWS (all non-empty cells) ===")
    for r in range(1, min(81, mr + 1)):
        cells = []
        for c in range(1, mc + 1):
            v = ws.cell(r, c).value
            if v is None:
                continue
            cv = ws_v.cell(r, c).value
            if isinstance(v, str) and v.startswith("="):
                cells.append(f"{addr(r,c)}:FORMULA {v} => {cv!r}")
            else:
                cells.append(f"{addr(r,c)}:{v!r}")
        if cells:
            lines.append(f"R{r}:")
            for item in cells:
                lines.append(f"  {item}")

    # Column headers: scan row 1-15 for text labels across all cols
    lines.append("\n=== COLUMN LABELS (rows 1-20, text only) ===")
    for r in range(1, 21):
        for c in range(1, mc + 1):
            v = ws.cell(r, c).value
            if isinstance(v, str) and not v.startswith("="):
                lines.append(f"  {addr(r,c)} = {v!r}")

    # Find all unique text labels (non-formula strings)
    labels = []
    for r in range(1, mr + 1):
        for c in range(1, mc + 1):
            v = ws.cell(r, c).value
            if isinstance(v, str) and not v.startswith("=") and v.strip():
                labels.append((addr(r, c), r, c, v.strip()))

    lines.append(f"\n=== ALL TEXT LABELS ({len(labels)}) ===")
    for a, r, c, v in labels:
        lines.append(f"  {a}\t{v}")

    # Formula pattern clustering
    pattern_count = Counter()
    pattern_examples = defaultdict(list)
    formula_cells = []
    for r in range(1, mr + 1):
        for c in range(1, mc + 1):
            v = ws.cell(r, c).value
            if isinstance(v, str) and v.startswith("="):
                pat = normalize_formula(v)
                pattern_count[pat] += 1
                if len(pattern_examples[pat]) < 5:
                    pattern_examples[pat].append(f"{addr(r,c)}: {v}")
                formula_cells.append((r, c, v))

    lines.append(f"\n=== FORMULA PATTERNS ({len(pattern_count)} unique, {len(formula_cells)} total) ===")
    for pat, cnt in pattern_count.most_common(80):
        lines.append(f"\nCOUNT={cnt} PATTERN={pat}")
        for ex in pattern_examples[pat]:
            lines.append(f"  ex: {ex}")

    # Input cells: numeric/date/bool literals (not formulas)
    inputs = []
    for r in range(1, mr + 1):
        for c in range(1, mc + 1):
            cell = ws.cell(r, c)
            v = cell.value
            if v is None:
                continue
            if isinstance(v, str) and v.startswith("="):
                continue
            if isinstance(v, str):
                continue  # labels
            inputs.append((addr(r, c), r, c, v, type(v).__name__, cell.number_format))

    lines.append(f"\n=== INPUT CELLS (literal numbers/dates/bools): {len(inputs)} ===")
    for a, r, c, v, t, fmt in inputs:
        # include nearby label from same row leftwards
        label = None
        for lc in range(c - 1, 0, -1):
            lv = ws.cell(r, lc).value
            if isinstance(lv, str) and not lv.startswith("="):
                label = lv
                break
        # also check above
        above = None
        for ar in range(r - 1, max(0, r - 5), -1):
            av = ws.cell(ar, c).value
            if isinstance(av, str) and not av.startswith("="):
                above = av
                break
        lines.append(f"  {a}\t{v!r}\t{t}\tfmt={fmt}\trow_label={label!r}\tcol_label={above!r}")

    # Water/Abwasser specific formulas
    lines.append("\n=== WASSER / ABWASSER / ZÄHLER RELATED ===")
    keys = re.compile(
        r"wasser|abwasser|zähler|zahler|stand|verbrauch|m3|m³|milles|tausend|anteil|schlüssel|schluessel|wohnung|eigent|partei|einheit|heizung|strom|müll|muell|versicherung|fix|variabel|allgemein|period|zeitraum|ablesung",
        re.I,
    )
    for a, r, c, v in labels:
        if keys.search(v):
            lines.append(f"  LABEL {a}: {v}")

    for r, c, v in formula_cells:
        if keys.search(v):
            lines.append(f"  FORMULA {addr(r,c)}: {v}")

    # Also look at cells near wasser labels - dump neighborhoods
    lines.append("\n=== NEIGHBORHOODS AROUND KEY LABELS ===")
    key_label_cells = [(r, c, v) for a, r, c, v in labels if keys.search(v)]
    seen_regions = set()
    for r, c, v in key_label_cells:
        # dump a window
        r0, r1 = max(1, r - 2), min(mr, r + 15)
        c0, c1 = max(1, c - 1), min(mc, c + 12)
        region = (r0, r1, c0, c1)
        if region in seen_regions:
            continue
        seen_regions.add(region)
        lines.append(f"\n-- Around {addr(r,c)} '{v}' window R{r0}-{r1} C{c0}-{c1} --")
        for rr in range(r0, r1 + 1):
            row_parts = []
            for cc in range(c0, c1 + 1):
                val = ws.cell(rr, cc).value
                if val is None:
                    continue
                cv = ws_v.cell(rr, cc).value
                if isinstance(val, str) and val.startswith("="):
                    row_parts.append(f"{addr(rr,cc)}={val}=>{cv!r}")
                else:
                    row_parts.append(f"{addr(rr,cc)}={val!r}")
            if row_parts:
                lines.append("  " + " | ".join(row_parts))

    # Column usage: which columns have content
    col_usage = Counter()
    for r in range(1, mr + 1):
        for c in range(1, mc + 1):
            if ws.cell(r, c).value is not None:
                col_usage[c] += 1
    lines.append("\n=== COLUMN USAGE (non-empty count) ===")
    for c, cnt in sorted(col_usage.items()):
        # sample header from top rows
        hdrs = []
        for r in range(1, min(25, mr + 1)):
            v = ws.cell(r, c).value
            if isinstance(v, str) and not v.startswith("="):
                hdrs.append(f"R{r}:{v}")
        lines.append(f"  Col {get_column_letter(c)} ({c}): {cnt} cells; headers={hdrs[:5]}")

    out = OUT / "deep_analysis.txt"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out} ({len(lines)} lines)")

    # Quick stats
    print(f"Text labels: {len(labels)}")
    print(f"Input literals: {len(inputs)}")
    print(f"Formula patterns: {len(pattern_count)}")
    print(f"Top 10 patterns:")
    for pat, cnt in pattern_count.most_common(10):
        print(f"  {cnt}x {pat[:100]}")


if __name__ == "__main__":
    main()
