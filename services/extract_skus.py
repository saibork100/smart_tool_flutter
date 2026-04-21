# Copyright © 2026 Mahmoud Triki (W2069987), University of Westminster. All rights reserved.
"""
extract_skus.py — Parse products_rows.csv and print all GAVHC fastener SKUs
with their inferred size labels.

Usage:
    python services/extract_skus.py

Output example:
    GAVHC816    → 8mm_16mm   | VIS A TETE HEXAGONALE...
    GAVHC1020   → 10mm_20mm  | VIS A TETE HEXAGONALE...
"""

import csv
import re
from pathlib import Path

CSV_PATH = Path(r"E:\products_rows.csv")

# Disambiguate GAVHC6100 (M6×100mm) from a hypothetical "M61×0mm":
# Rule: if the first digit is 4–9, treat it as a single-digit diameter and
# the remaining digits as length (must be ≥ 10 to rule out garbage like "00").
# Only fall back to two-digit diameter (10–39) when first digit is 1–3.

def parse_label(sku: str) -> str | None:
    base = sku.rstrip("+")
    if not base.startswith("GAVHC"):
        return None
    digits = base[5:]  # everything after "GAVHC"
    if not digits.isdigit() or len(digits) < 3:
        return None

    # Single-digit diameter (M4–M9) — e.g. GAVHC6100 → 6mm_100mm
    if digits[0] in "456789":
        diam = int(digits[0])
        length = int(digits[1:])
        if length >= 10:
            return f"{diam}mm_{length}mm"

    # Two-digit diameter (M10–M39) — e.g. GAVHC1625 → 16mm_25mm
    if len(digits) >= 4:
        diam = int(digits[:2])
        length = int(digits[2:])
        if 10 <= diam <= 39 and length >= 10:
            return f"{diam}mm_{length}mm"

    return None


def main():
    if not CSV_PATH.exists():
        print(f"ERROR: File not found: {CSV_PATH}")
        return

    found: dict[str, tuple[str, str]] = {}  # sku → (label, name)

    with CSV_PATH.open(encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f, delimiter=";")
        headers = next(reader)
        name_idx = headers.index("Name")
        sku_idx = headers.index("SKU")

        for row in reader:
            if len(row) <= max(name_idx, sku_idx):
                continue
            sku = row[sku_idx].strip()
            name = row[name_idx].strip()[:80]
            label = parse_label(sku)
            if label:
                found[sku] = (label, name)

    if not found:
        print("No GAVHC SKUs found.")
        return

    # Group by diameter
    by_diameter: dict[str, list[tuple[str, str, str]]] = {}
    for sku, (label, name) in sorted(found.items()):
        diameter = label.split("_")[0]
        by_diameter.setdefault(diameter, []).append((sku, label, name))

    print(f"\nFound {len(found)} GAVHC fastener SKUs:\n")
    for diameter, items in sorted(by_diameter.items(), key=lambda x: int(x[0].replace("mm", ""))):
        print(f"── {diameter} ({'M' + diameter.replace('mm','')}) — {len(items)} sizes ──")
        for sku, label, name in items:
            print(f"   {sku:<14} → {label:<14} | {name}")
        print()

    # Print Python dict ready to paste into api.py
    print("\n# ── Ready to paste into SKU_TO_LABEL in api.py ──")
    print("NEW_ENTRIES = {")
    for sku, (label, _) in sorted(found.items()):
        print(f'    "{sku}": "{label}",')
    print("}")


if __name__ == "__main__":
    main()
