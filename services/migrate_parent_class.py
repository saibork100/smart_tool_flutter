"""
migrate_parent_class.py — One-shot migration to populate parent_class, size_label,
and size_rank on existing products rows.

Maps every GAVHC hex-bolt SKU to:
  parent_class = 'vis__th__zinc__48__din933'
  size_label   = 'M8 × 30mm'   (derived from SKU_TO_LABEL)
  size_rank    = sort order by (diameter_mm, length_mm)

Run once after upgrading api.py to the type-classifier strategy:
    python services/migrate_parent_class.py

Safe to re-run — uses ON CONFLICT DO UPDATE (upsert logic via plain UPDATE).
"""

from __future__ import annotations

import os
import re
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:admin123@localhost:5432/smart_tool"
)
engine = create_engine(DATABASE_URL)

# ── All known GAVHC SKUs → size label (copy from api.py) ─────────────────────
# Format: "Xmm_Ymm"  e.g. "8mm_30mm"
SKU_TO_LABEL: dict[str, str] = {
    # M4
    "GAVHC410": "4mm_10mm",   "GAVHC416": "4mm_16mm",   "GAVHC420": "4mm_20mm",
    "GAVHC425": "4mm_25mm",   "GAVHC430": "4mm_30mm",   "GAVHC440": "4mm_40mm",
    "GAVHC450": "4mm_50mm",
    # M5
    "GAVHC510": "5mm_10mm",   "GAVHC516": "5mm_16mm",   "GAVHC520": "5mm_20mm",
    "GAVHC525": "5mm_25mm",   "GAVHC530": "5mm_30mm",   "GAVHC540": "5mm_40mm",
    "GAVHC550": "5mm_50mm",
    # M6
    "GAVHC612": "6mm_12mm",   "GAVHC616": "6mm_16mm",   "GAVHC620": "6mm_20mm",
    "GAVHC625": "6mm_25mm",   "GAVHC630": "6mm_30mm",   "GAVHC640": "6mm_40mm",
    "GAVHC650": "6mm_50mm",   "GAVHC660":  "6mm_60mm",  "GAVHC660+": "6mm_60mm",
    "GAVHC670":  "6mm_70mm",  "GAVHC670+": "6mm_70mm",
    "GAVHC680":  "6mm_80mm",  "GAVHC680+": "6mm_80mm",
    "GAVHC6100": "6mm_100mm", "GAVHC6100+": "6mm_100mm",
    "GAVHC6120": "6mm_120mm",
    # M8
    "GAVHC816": "8mm_16mm",   "GAVHC820": "8mm_20mm",   "GAVHC825": "8mm_25mm",
    "GAVHC830": "8mm_30mm",   "GAVHC840": "8mm_40mm",   "GAVHC850": "8mm_50mm",
    "GAVHC860": "8mm_60mm",   "GAVHC870": "8mm_70mm",
    "GAVHC880":  "8mm_80mm",  "GAVHC880+": "8mm_80mm",
    "GAVHC8100": "8mm_100mm", "GAVHC8100+": "8mm_100mm",
    "GAVHC8120": "8mm_120mm", "GAVHC8120+": "8mm_120mm",
    "GAVHC8150": "8mm_150mm",
    # M10
    "GAVHC1016": "10mm_16mm", "GAVHC1020": "10mm_20mm", "GAVHC1025": "10mm_25mm",
    "GAVHC1030": "10mm_30mm", "GAVHC1040": "10mm_40mm", "GAVHC1045": "10mm_45mm",
    "GAVHC1050":  "10mm_50mm",  "GAVHC1050+": "10mm_50mm",
    "GAVHC1060":  "10mm_60mm",  "GAVHC1060+": "10mm_60mm",
    "GAVHC1070":  "10mm_70mm",  "GAVHC1070+": "10mm_70mm",
    "GAVHC1080":  "10mm_80mm",  "GAVHC1080+": "10mm_80mm",
    "GAVHC1090":  "10mm_90mm",
    "GAVHC10100": "10mm_100mm", "GAVHC10100+": "10mm_100mm",
    "GAVHC10120": "10mm_120mm", "GAVHC10120+": "10mm_120mm",
    "GAVHC10140": "10mm_140mm", "GAVHC10150": "10mm_150mm",
    "GAVHC10160": "10mm_160mm",
    # M12
    "GAVHC1220": "12mm_20mm",  "GAVHC1225": "12mm_25mm",  "GAVHC1230": "12mm_30mm",
    "GAVHC1240": "12mm_40mm",  "GAVHC1245": "12mm_45mm",
    "GAVHC1250":  "12mm_50mm",  "GAVHC1250+": "12mm_50mm",
    "GAVHC1260":  "12mm_60mm",  "GAVHC1260+": "12mm_60mm",
    "GAVHC1270":  "12mm_70mm",  "GAVHC1270+": "12mm_70mm",
    "GAVHC1280":  "12mm_80mm",  "GAVHC1280+": "12mm_80mm",
    "GAVHC1290":  "12mm_90mm",
    "GAVHC12100": "12mm_100mm", "GAVHC12100+": "12mm_100mm",
    "GAVHC12120": "12mm_120mm", "GAVHC12120+": "12mm_120mm",
    "GAVHC12140": "12mm_140mm", "GAVHC12140+": "12mm_140mm",
    "GAVHC12150": "12mm_150mm", "GAVHC12160": "12mm_160mm",
    "GAVHC12180": "12mm_180mm",
}


def _parse_size_mm(label: str) -> tuple[int, int]:
    """'8mm_30mm' → (8, 30)"""
    m = re.match(r'^(\d+)mm_(\d+)mm$', label)
    if m:
        return int(m.group(1)), int(m.group(2))
    return (0, 0)


def _human_label(label: str) -> str:
    """'8mm_30mm' → 'M8 × 30mm'"""
    d, l = _parse_size_mm(label)
    if d:
        return f"M{d} × {l}mm"
    return label


def migrate() -> None:
    # All GAVHC bolts belong to the zinc 4.8 DIN933 hex-bolt type
    PARENT_CLASS = "vis__th__zinc__48__din933"

    # Build ordered list of (sku, size_label, size_rank)
    # Deduplicate by internal label (skip '+' variants that share a label)
    seen: dict[str, str] = {}       # label → first sku
    for sku, lbl in SKU_TO_LABEL.items():
        if lbl not in seen:
            seen[lbl] = sku

    # Sort by (diameter, length) for size_rank
    ordered = sorted(seen.items(), key=lambda kv: _parse_size_mm(kv[0]))

    rows = [
        {
            "sku":          sku,
            "parent_class": PARENT_CLASS,
            "size_label":   _human_label(lbl),
            "size_rank":    rank,
        }
        for rank, (lbl, sku) in enumerate(ordered, start=1)
    ]

    print(f"Migrating {len(rows)} GAVHC SKUs → parent_class={PARENT_CLASS!r} …")

    updated = 0
    skipped = 0

    with engine.connect() as conn:
        for r in rows:
            result = conn.execute(text("""
                UPDATE products
                SET    parent_class = :parent_class,
                       size_label   = :size_label,
                       size_rank    = :size_rank
                WHERE  sku = :sku
            """), r)
            if result.rowcount:
                updated += 1
            else:
                skipped += 1
        conn.commit()

    print(f"  Updated : {updated} rows")
    print(f"  Skipped : {skipped} SKUs not yet in products table (add them via admin UI)")

    if updated:
        print(
            f"\nDone. The /detect endpoint will now return the full size list "
            f"when it recognises '{PARENT_CLASS}'."
        )


if __name__ == "__main__":
    migrate()
