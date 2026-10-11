"""Extract structure, formulas, and billing logic from Kondominium Excel."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

XLSX = Path(r"c:\Users\rober\OneDrive\Hausverwaltung_Vahrn\Abrechnung_KondominiumVitroler_V2.xlsx")
OUT = Path(r"d:\Coding\Abrechnung-Vitroler\analysis_output")


def cell_addr(row: int, col: int) -> str:
    return f"{get_column_letter(col)}{row}"


def dump_sheet(ws, max_rows: int | None = None, max_cols: int | None = None):
    """Return grid of non-empty cells with value type."""
    rows_out = []
    dim = ws.dimensions
    mr = ws.max_row or 0
    mc = ws.max_column or 0
    if max_rows:
        mr = min(mr, max_rows)
    if max_cols:
        mc = min(mc, max_cols)

    for r in range(1, mr + 1):
        row_cells = []
        for c in range(1, mc + 1):
            cell = ws.cell(r, c)
            if cell.value is None:
                continue
            val = cell.value
            kind = "formula" if isinstance(val, str) and val.startswith("=") else type(val).__name__
            row_cells.append(
                {
                    "addr": cell_addr(r, c),
                    "row": r,
                    "col": c,
                    "col_letter": get_column_letter(c),
                    "value": val if not isinstance(val, (bytes,)) else repr(val),
                    "kind": kind,
                    "number_format": cell.number_format,
                }
            )
        if row_cells:
            rows_out.append({"row": r, "cells": row_cells})
    return {
        "title": ws.title,
        "dimensions": dim,
        "max_row": ws.max_row,
        "max_column": ws.max_column,
        "merged_cells": [str(m) for m in ws.merged_cells.ranges],
        "rows": rows_out,
    }


def collect_formulas(ws):
    formulas = []
    for r in range(1, (ws.max_row or 0) + 1):
        for c in range(1, (ws.max_column or 0) + 1):
            cell = ws.cell(r, c)
            if isinstance(cell.value, str) and cell.value.startswith("="):
                formulas.append(
                    {
                        "addr": cell_addr(r, c),
                        "formula": cell.value,
                        "number_format": cell.number_format,
                    }
                )
    return formulas


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    # data_only=False for formulas; also load data_only for computed values
    wb = load_workbook(XLSX, data_only=False)
    wb_vals = load_workbook(XLSX, data_only=True)

    report = {
        "file": str(XLSX),
        "sheet_names": wb.sheetnames,
        "sheets": {},
        "all_formulas_by_sheet": {},
        "cross_sheet_refs": [],
    }

    # Full text dump for human reading
    text_lines = []
    text_lines.append(f"FILE: {XLSX}")
    text_lines.append(f"SHEETS ({len(wb.sheetnames)}): {wb.sheetnames}")
    text_lines.append("")

    for name in wb.sheetnames:
        ws = wb[name]
        ws_v = wb_vals[name]
        structure = dump_sheet(ws)
        formulas = collect_formulas(ws)

        # Attach computed values where available
        for row in structure["rows"]:
            for cell in row["cells"]:
                cv = ws_v.cell(cell["row"], cell["col"]).value
                cell["computed"] = cv

        report["sheets"][name] = structure
        report["all_formulas_by_sheet"][name] = formulas

        text_lines.append("=" * 80)
        text_lines.append(f"SHEET: {name}")
        text_lines.append(f"  size: {ws.max_row} rows x {ws.max_column} cols")
        text_lines.append(f"  merged: {structure['merged_cells']}")
        text_lines.append("-" * 40)
        text_lines.append("CELL GRID (non-empty):")
        for row in structure["rows"]:
            parts = []
            for cell in row["cells"]:
                v = cell["value"]
                if isinstance(v, str) and len(v) > 120:
                    v_disp = v[:117] + "..."
                else:
                    v_disp = v
                comp = cell.get("computed")
                if cell["kind"] == "formula":
                    parts.append(f"{cell['addr']}={v_disp!r} [calc={comp!r}]")
                else:
                    parts.append(f"{cell['addr']}={v_disp!r}")
            text_lines.append(f"  R{row['row']}: " + " | ".join(parts))

        text_lines.append("-" * 40)
        text_lines.append(f"FORMULAS ({len(formulas)}):")
        for f in formulas:
            text_lines.append(f"  {f['addr']}: {f['formula']}")
        text_lines.append("")

        # Cross-sheet references
        for f in formulas:
            refs = re.findall(r"'?([^'!]+)'?!", f["formula"])
            for ref in refs:
                if ref and ref not in (name,):
                    report["cross_sheet_refs"].append(
                        {"from_sheet": name, "cell": f["addr"], "to_sheet": ref, "formula": f["formula"]}
                    )

    # Also dump named styles / defined names
    defined = []
    try:
        for name_key, dn in wb.defined_names.items():
            attr = getattr(dn, "attr_text", None) or str(dn)
            defined.append({"name": name_key, "attr": attr})
    except Exception as e:
        defined.append({"error": str(e)})
    report["defined_names"] = defined
    text_lines.append("=" * 80)
    text_lines.append("DEFINED NAMES:")
    for d in defined:
        text_lines.append(f"  {d}")

    # Formula keyword index
    keywords = [
        "Wasser",
        "Abwasser",
        "Zähler",
        "Stand",
        "m3",
        "m³",
        "Millesim",
        "Tausendstel",
        "%",
        "Anteil",
        "Verteilung",
        "Schlüssel",
        "Wohnung",
        "Eigentümer",
        "Partei",
        "Einheit",
        "Kosten",
        "Abrechnung",
        "Periode",
        "Zeitraum",
        "Heizung",
        "Strom",
        "Müll",
        "Versicherung",
        "Hausmeister",
        "Reinigung",
        "Lift",
        "Aufzug",
        "Garten",
        "Allgemein",
        "Verbrauch",
        "Fix",
        "Variabel",
    ]
    text_lines.append("=" * 80)
    text_lines.append("KEYWORD HITS (case-insensitive in cell values):")
    for name in wb.sheetnames:
        ws = wb[name]
        for r in range(1, (ws.max_row or 0) + 1):
            for c in range(1, (ws.max_column or 0) + 1):
                cell = ws.cell(r, c)
                if cell.value is None:
                    continue
                s = str(cell.value)
                hits = [k for k in keywords if k.lower() in s.lower()]
                if hits:
                    text_lines.append(f"  [{name}] {cell_addr(r,c)}: hits={hits} value={s[:200]!r}")

    # Save outputs
    json_path = OUT / "structure.json"
    txt_path = OUT / "full_dump.txt"
    formulas_path = OUT / "formulas_only.txt"

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)

    with txt_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(text_lines))

    with formulas_path.open("w", encoding="utf-8") as f:
        for sheet, formulas in report["all_formulas_by_sheet"].items():
            f.write(f"\n### {sheet} ({len(formulas)} formulas)\n")
            for fr in formulas:
                f.write(f"{fr['addr']}\t{fr['formula']}\n")

    print(f"Sheets: {wb.sheetnames}")
    print(f"Wrote {json_path}")
    print(f"Wrote {txt_path}")
    print(f"Wrote {formulas_path}")
    total_formulas = sum(len(v) for v in report["all_formulas_by_sheet"].values())
    print(f"Total formulas: {total_formulas}")
    print(f"Cross-sheet refs: {len(report['cross_sheet_refs'])}")
    print(f"Defined names: {len(defined)}")


if __name__ == "__main__":
    main()
