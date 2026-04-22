# Copyright © 2026 Mahmoud Triki (W2069987), University of Westminster. All rights reserved.
"""
FastAPI backend for Smart Tool Recognition.
Run with: python -m uvicorn api:app --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image
from pathlib import Path
from typing import Optional
import io, os, threading, time, shutil, re, uuid
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    print("HEIC support enabled.")
except ImportError:
    print("Warning: pillow-heif not installed, HEIC files won't work.")

load_dotenv()

# ── App setup ──────────────────────────────────────────────────────────────────
app = FastAPI(title="Smart Tool Recognition API", version="2.0.0")

_allowed_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

# ── Config ─────────────────────────────────────────────────────────────────────
YOLO_WEIGHTS         = os.getenv("YOLO_WEIGHTS", "ultralytics/best.pt")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.35"))
TOP_K                = int(os.getenv("TOP_K", "5"))
DATASET_PATH         = os.getenv("DATASET_PATH", r"E:\photo coliction\dataset")
TYPE_DATASET_PATH    = os.getenv("TYPE_DATASET_PATH", r"E:\photo coliction\type_dataset")
REPORTS_DIR          = os.getenv("REPORTS_DIR", r"D:\smart_tool_flutter\reported_images")
DATABASE_URL         = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set. Add it to services/.env")

# ── Database setup ─────────────────────────────────────────────────────────────
engine = create_engine(DATABASE_URL)

def init_db():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS shelf_locations (
                shelf_id  TEXT PRIMARY KEY,
                aisle     TEXT NOT NULL,
                bay       TEXT NOT NULL,
                zone      TEXT,
                notes     TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS products (
                sku                  TEXT PRIMARY KEY,
                barcode              TEXT UNIQUE,
                name                 TEXT NOT NULL,
                brand                TEXT NOT NULL,
                category             TEXT NOT NULL,
                type                 TEXT NOT NULL DEFAULT 'tool',
                description          TEXT,
                shelf_id             TEXT REFERENCES shelf_locations(shelf_id),
                last_updated         TIMESTAMP DEFAULT NOW()
            )
        """))
        # Add type-classifier columns (idempotent — safe to run on existing tables)
        for col_sql in [
            "ALTER TABLE products ADD COLUMN IF NOT EXISTS parent_class TEXT",
            "ALTER TABLE products ADD COLUMN IF NOT EXISTS size_label   TEXT",
            "ALTER TABLE products ADD COLUMN IF NOT EXISTS size_rank    INTEGER",
        ]:
            conn.execute(text(col_sql))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS stock (
                sku                   TEXT PRIMARY KEY REFERENCES products(sku),
                quantity_on_shelf     INTEGER DEFAULT 0,
                quantity_in_backstore INTEGER DEFAULT 0,
                status                TEXT DEFAULT 'in_stock'
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS admin_users (
                id            SERIAL PRIMARY KEY,
                email         TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name          TEXT,
                role          TEXT DEFAULT 'admin',
                is_active     INTEGER DEFAULT 1,
                created_at    TIMESTAMP DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS reports (
                id            SERIAL PRIMARY KEY,
                image_path    TEXT NOT NULL,
                wrong_class   TEXT NOT NULL,
                correct_class TEXT NOT NULL,
                reported_by   TEXT,
                status        TEXT DEFAULT 'pending',
                created_at    TIMESTAMP DEFAULT NOW()
            )
        """))
        # Auto-seed admin from env vars (used by Docker; skip if not set)
        _admin_email    = os.getenv("ADMIN_EMAIL")
        _admin_password = os.getenv("ADMIN_PASSWORD")
        if _admin_email and _admin_password:
            import hashlib
            _pw_hash = hashlib.sha256(_admin_password.encode()).hexdigest()
            conn.execute(text("""
                INSERT INTO admin_users (email, password_hash, name, role, is_active)
                VALUES (:email, :hash, 'Admin', 'admin', 1)
                ON CONFLICT (email) DO NOTHING
            """), {"email": _admin_email, "hash": _pw_hash})
            print(f"Admin seeded: {_admin_email}")
        conn.commit()
    print("Database initialized.")

init_db()

# ── SKU → Label mapping ────────────────────────────────────────────────────────
# Derived from products_rows.csv via `python services/extract_skus.py`
# Format: GAVHC{diameter_mm}{length_mm}[+]  — '+' variants share the same label
SKU_TO_LABEL = {
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
    "GAVHC650": "6mm_50mm",
    "GAVHC660":  "6mm_60mm",  "GAVHC660+": "6mm_60mm",
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
    # M14
    "GAVHC1425": "14mm_25mm",  "GAVHC1430": "14mm_30mm",  "GAVHC1435": "14mm_35mm",
    "GAVHC1440": "14mm_40mm",  "GAVHC1445": "14mm_45mm",  "GAVHC1450": "14mm_50mm",
    "GAVHC1460":  "14mm_60mm",  "GAVHC1460+": "14mm_60mm",
    "GAVHC1470":  "14mm_70mm",  "GAVHC1470+": "14mm_70mm",
    "GAVHC1480":  "14mm_80mm",  "GAVHC1480+": "14mm_80mm",
    "GAVHC1490+": "14mm_90mm",
    "GAVHC14100": "14mm_100mm", "GAVHC14100+": "14mm_100mm",
    "GAVHC14120": "14mm_120mm", "GAVHC14120+": "14mm_120mm",
    "GAVHC14140": "14mm_140mm", "GAVHC14150": "14mm_150mm",
    "GAVHC14160": "14mm_160mm", "GAVHC14180": "14mm_180mm",
    "GAVHC14200": "14mm_200mm", "GAVHC14220": "14mm_220mm",
    # M16
    "GAVHC1625": "16mm_25mm",  "GAVHC1630": "16mm_30mm",  "GAVHC1635": "16mm_35mm",
    "GAVHC1640": "16mm_40mm",  "GAVHC1645": "16mm_45mm",  "GAVHC1650": "16mm_50mm",
    "GAVHC1655": "16mm_55mm",
    "GAVHC1660":  "16mm_60mm",  "GAVHC1660+": "16mm_60mm",
    "GAVHC1670":  "16mm_70mm",  "GAVHC1670+": "16mm_70mm",
    "GAVHC1680":  "16mm_80mm",  "GAVHC1680+": "16mm_80mm",
    "GAVHC1690":  "16mm_90mm",  "GAVHC1690+": "16mm_90mm",
    "GAVHC16100": "16mm_100mm", "GAVHC16100+": "16mm_100mm",
    "GAVHC16120": "16mm_120mm", "GAVHC16120+": "16mm_120mm",
    "GAVHC16130": "16mm_130mm", "GAVHC16140": "16mm_140mm",
    "GAVHC16150": "16mm_150mm", "GAVHC16160": "16mm_160mm",
    "GAVHC16180": "16mm_180mm", "GAVHC16200": "16mm_200mm",
    "GAVHC16220": "16mm_220mm", "GAVHC16240": "16mm_240mm",
    "GAVHC16260": "16mm_260mm",
    # M18
    "GAVHC1840": "18mm_40mm",  "GAVHC1850": "18mm_50mm",
    "GAVHC1860":  "18mm_60mm",  "GAVHC1860+": "18mm_60mm",
    "GAVHC1870":  "18mm_70mm",  "GAVHC1870+": "18mm_70mm",
    "GAVHC1880":  "18mm_80mm",  "GAVHC1880+": "18mm_80mm",
    "GAVHC1890":  "18mm_90mm",  "GAVHC1890+": "18mm_90mm",
    "GAVHC18100": "18mm_100mm", "GAVHC18100+": "18mm_100mm",
    "GAVHC18120": "18mm_120mm", "GAVHC18120+": "18mm_120mm",
    "GAVHC18140": "18mm_140mm", "GAVHC18160": "18mm_160mm",
    "GAVHC18180": "18mm_180mm", "GAVHC18200": "18mm_200mm",
    # M20
    "GAVHC2040": "20mm_40mm",  "GAVHC2050": "20mm_50mm",
    "GAVHC2060":  "20mm_60mm",  "GAVHC2060+": "20mm_60mm",
    "GAVHC2070":  "20mm_70mm",  "GAVHC2070+": "20mm_70mm",
    "GAVHC2080":  "20mm_80mm",  "GAVHC2080+": "20mm_80mm",
    "GAVHC2090":  "20mm_90mm",
    "GAVHC20100": "20mm_100mm", "GAVHC20100+": "20mm_100mm",
    "GAVHC20110+": "20mm_110mm",
    "GAVHC20120": "20mm_120mm", "GAVHC20120+": "20mm_120mm",
    "GAVHC20130": "20mm_130mm", "GAVHC20140": "20mm_140mm",
    "GAVHC20150": "20mm_150mm", "GAVHC20160": "20mm_160mm",
    "GAVHC20180": "20mm_180mm", "GAVHC20200": "20mm_200mm",
    "GAVHC20220": "20mm_220mm", "GAVHC20240": "20mm_240mm",
    # M22
    "GAVHC2250": "22mm_50mm",  "GAVHC2260": "22mm_60mm",  "GAVHC2270": "22mm_70mm",
    "GAVHC2280":  "22mm_80mm",  "GAVHC2280+": "22mm_80mm",
    "GAVHC2290":  "22mm_90mm",
    "GAVHC22100": "22mm_100mm",
    "GAVHC22120": "22mm_120mm", "GAVHC22120+": "22mm_120mm",
    "GAVHC22140": "22mm_140mm", "GAVHC22160": "22mm_160mm",
    "GAVHC22180": "22mm_180mm",
    # M24
    "GAVHC2450": "24mm_50mm",  "GAVHC2460": "24mm_60mm",  "GAVHC2470": "24mm_70mm",
    "GAVHC2480": "24mm_80mm",
    "GAVHC2490":  "24mm_90mm",  "GAVHC2490+": "24mm_90mm",
    "GAVHC24100": "24mm_100mm", "GAVHC24100+": "24mm_100mm",
    "GAVHC24120": "24mm_120mm", "GAVHC24120+": "24mm_120mm",
    "GAVHC24140": "24mm_140mm", "GAVHC24160": "24mm_160mm",
    "GAVHC24180": "24mm_180mm", "GAVHC24200": "24mm_200mm",
    "GAVHC24220": "24mm_220mm", "GAVHC24260": "24mm_260mm",
    # M27
    "GAVHC2760": "27mm_60mm",  "GAVHC2770": "27mm_70mm",  "GAVHC2780": "27mm_80mm",
    "GAVHC27100": "27mm_100mm",
    "GAVHC27120": "27mm_120mm", "GAVHC27120+": "27mm_120mm",
    "GAVHC27130": "27mm_130mm", "GAVHC27140": "27mm_140mm",
    "GAVHC27160": "27mm_160mm", "GAVHC27220": "27mm_220mm",
    "GAVHC27280": "27mm_280mm",
    # M30
    "GAVHC3060": "30mm_60mm",  "GAVHC3070": "30mm_70mm",  "GAVHC3080": "30mm_80mm",
    "GAVHC3090": "30mm_90mm",
    "GAVHC30100": "30mm_100mm",
    "GAVHC30120": "30mm_120mm", "GAVHC30120+": "30mm_120mm",
    "GAVHC30130": "30mm_130mm", "GAVHC30140": "30mm_140mm",
    "GAVHC30150": "30mm_150mm", "GAVHC30160": "30mm_160mm",
    "GAVHC30180": "30mm_180mm", "GAVHC30200": "30mm_200mm",
    # M33
    "GAVHC33100": "33mm_100mm", "GAVHC33120": "33mm_120mm",
    "GAVHC33140": "33mm_140mm", "GAVHC33180": "33mm_180mm",
    "GAVHC33200": "33mm_200mm", "GAVHC33220": "33mm_220mm",
    "GAVHC33250": "33mm_250mm",
    # M36
    "GAVHC36120": "36mm_120mm", "GAVHC36160": "36mm_160mm",
    # M39
    "GAVHC39160": "39mm_160mm",
}

# Fallback parser for any GAVHC SKU not in the dict above.
# Uses the same disambiguation logic as extract_skus.py.
def _parse_gavhc(sku: str) -> str | None:
    base = sku.rstrip("+")
    if not base.startswith("GAVHC"):
        return None
    digits = base[5:]
    if not digits.isdigit() or len(digits) < 3:
        return None
    if digits[0] in "456789":           # single-digit diameter (M4–M9)
        length = int(digits[1:])
        if length >= 10:
            return f"{digits[0]}mm_{length}mm"
    if len(digits) >= 4:                # two-digit diameter (M10–M39)
        diam = int(digits[:2])
        length = int(digits[2:])
        if 10 <= diam <= 39 and length >= 10:
            return f"{diam}mm_{length}mm"
    return None

def sku_to_label(sku: str) -> str | None:
    return SKU_TO_LABEL.get(sku) or _parse_gavhc(sku)


# ── Diameter helpers (used by /detect for available_sizes) ────────────────────

def _extract_diameter(label: str) -> int | None:
    """
    Parse bolt diameter from a predicted label.
    Handles both old format ('8mm_70mm' → 8) and new YOLO11 format ('bolt_M8' → 8).
    """
    if not label:
        return None
    # New YOLO11 format: bolt_M8, M8, m8
    m = re.match(r'(?:bolt_)?[Mm](\d+)', label)
    if m:
        return int(m.group(1))
    # Old classification format: 8mm_70mm
    m = re.match(r'^(\d+)mm_', label)
    if m:
        return int(m.group(1))
    return None


def _parent_class_name(diameter: int) -> str:
    return f"bolt_M{diameter}"


def _display_name(diameter: int) -> str:
    return f"Hex Bolt M{diameter}"


def _class_id_to_display(class_id: str) -> str:
    """
    Convert a YOLO11 type class_id to a human-readable display name.
    e.g. 'vis__th__zinc__48__din933' → 'Vis Th Zinc 4.8 DIN933'
    """
    if not class_id:
        return ""
    parts = class_id.split("__")
    tokens = []
    for p in parts:
        # Grade: "48" → "4.8", "88" → "8.8", "109" → "10.9", "129" → "12.9"
        if re.fullmatch(r'\d{2,3}', p) and int(p) in (48, 88, 109, 129):
            formatted = p[:-1] + "." + p[-1]
            tokens.append(formatted)
        elif p.startswith("din") or p.startswith("iso"):
            tokens.append(p.upper())
        else:
            tokens.append(p.title())
    return " ".join(tokens)


# Grade-sibling pairs: bolts that look identical photographically (4.8 ↔ 8.8, etc.)
# When the model predicts one grade but only the sibling has DB products, fall back
# automatically so the size list always appears.
_GRADE_SIBLINGS: dict[str, str] = {
    "vis__th__zinc__88__din933":  "vis__th__zinc__48__din933",
    "vis__th__zinc__48__din933":  "vis__th__zinc__88__din933",
    "vis__th__zinc__88__din931":  "vis__th__zinc__48__din931",
    "vis__th__zinc__48__din931":  "vis__th__zinc__88__din931",
    "vis__th__inox__a4__din933":  "vis__th__inox__a2__din933",
    "vis__th__inox__a2__din933":  "vis__th__inox__a4__din933",
    "vis__chc__inox__a4__din912": "vis__chc__inox__a2__din912",
    "vis__chc__inox__a2__din912": "vis__chc__inox__a4__din912",
}


def _query_sizes(conn, class_name: str) -> list:
    return conn.execute(text("""
        SELECT p.sku, p.name, p.size_label,
               s.aisle, s.bay, s.zone,
               st.quantity_on_shelf, st.quantity_in_backstore, st.status
        FROM products p
        LEFT JOIN shelf_locations s  ON p.shelf_id = s.shelf_id
        LEFT JOIN stock         st   ON p.sku      = st.sku
        WHERE p.parent_class = :class_name
        ORDER BY p.size_rank NULLS LAST, p.sku
    """), {"class_name": class_name}).fetchall()


def _get_available_sizes_by_type(class_name: str) -> list[dict]:
    """
    Return all database products whose parent_class matches the detected type,
    ordered by size_rank. If the exact class has no products, automatically tries
    the grade-sibling (e.g. 8.8 → 4.8) since they look identical photographically.
    """
    if not class_name:
        return []

    with engine.connect() as conn:
        rows = _query_sizes(conn, class_name)
        # Grade-sibling fallback: 4.8 ↔ 8.8, A2 ↔ A4 (visually identical)
        if not rows and class_name in _GRADE_SIBLINGS:
            rows = _query_sizes(conn, _GRADE_SIBLINGS[class_name])

    return [
        {
            "sku":              r["sku"],
            "size_label":       r["size_label"] or r["sku"],
            "shelf_label":      "-".join(x for x in [r["aisle"], r["bay"], r["zone"]] if x) or "—",
            "qty_on_shelf":     r["quantity_on_shelf"],
            "qty_in_backstore": r["quantity_in_backstore"],
            "status":           r["status"],
        }
        for r in rows
    ]


def _get_available_sizes(diameter: int) -> list[dict]:
    """
    Return all database products whose SKU label matches the given diameter,
    sorted by ascending bolt length. Used by /detect to show the full size list.
    """
    # Find all SKUs with this diameter
    prefix = f"{diameter}mm_"
    matching = {
        sku: lbl for sku, lbl in SKU_TO_LABEL.items()
        if lbl.startswith(prefix)
    }
    if not matching:
        return []

    # Length-sort key: "8mm_70mm" → 70
    def _len_mm(lbl: str) -> int:
        parts = lbl.split('_')
        if len(parts) == 2:
            try:
                return int(parts[1].replace('mm', ''))
            except ValueError:
                pass
        return 0

    results: list[dict] = []
    seen_labels: set[str] = set()

    with engine.connect() as conn:
        for sku in sorted(matching, key=lambda s: _len_mm(matching[s])):
            lbl = matching[sku]
            if lbl in seen_labels:
                continue          # skip '+' duplicate SKUs (same size, different variant)
            seen_labels.add(lbl)

            row = conn.execute(text("""
                SELECT p.sku, p.name,
                       s.aisle, s.bay, s.zone,
                       st.quantity_on_shelf, st.quantity_in_backstore, st.status
                FROM products p
                LEFT JOIN shelf_locations s  ON p.shelf_id = s.shelf_id
                LEFT JOIN stock         st   ON p.sku      = st.sku
                WHERE p.sku = :sku
            """), {"sku": sku}).fetchone()

            # Build the human-readable size label: "M8 × 70mm"
            parts = lbl.split('_')
            if len(parts) == 2:
                d = parts[0].replace('mm', '')
                l = parts[1]
                size_label = f"M{d} × {l}"
            else:
                size_label = lbl

            if row:
                r = dict(row._mapping)
                shelf = "-".join(
                    x for x in [r.get("aisle"), r.get("bay"), r.get("zone")] if x
                ) or "—"
                results.append({
                    "sku":               r["sku"],
                    "size_label":        size_label,
                    "shelf_label":       shelf,
                    "qty_on_shelf":      r.get("quantity_on_shelf"),
                    "qty_in_backstore":  r.get("quantity_in_backstore"),
                    "status":            r.get("status"),
                })
            else:
                # SKU not in database yet — still include in the size list
                results.append({
                    "sku":               sku,
                    "size_label":        size_label,
                    "shelf_label":       "—",
                    "qty_on_shelf":      None,
                    "qty_in_backstore":  None,
                    "status":            None,
                })

    return results

# ── Load detector ──────────────────────────────────────────────────────────────
print(f"Loading model from: {YOLO_WEIGHTS}")
try:
    from detector import Detector
    detector = Detector(weights_path=YOLO_WEIGHTS)
    print("Model loaded successfully.")
except Exception as e:
    print(f"Warning: Could not load model: {e}")
    detector = None

# ── Training state ─────────────────────────────────────────────────────────────
train_state = {
    "running": False, "progress": 0, "total_epochs": 0,
    "current_epoch": 0, "top1_acc": None, "status": "idle", "message": "",
}

# ── Pydantic models ────────────────────────────────────────────────────────────
class ProductModel(BaseModel):
    sku: str
    barcode: Optional[str] = None
    name: str
    brand: str
    category: str
    type: str = "tool"
    description: Optional[str] = None
    shelf_id: Optional[str] = None

class ShelfModel(BaseModel):
    shelf_id: str
    aisle: str
    bay: str
    zone: Optional[str] = None
    notes: Optional[str] = None

class StockModel(BaseModel):
    quantity_on_shelf: int = 0
    quantity_in_backstore: int = 0

class AdminLoginModel(BaseModel):
    email: str
    password_hash: str

# ── Health ─────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": detector is not None,
        "model_path": YOLO_WEIGHTS,
    }

# ── Detect ─────────────────────────────────────────────────────────────────────
@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    if detector is None:
        raise HTTPException(status_code=503, detail="Model not loaded.")
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file received.")
    try:
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        image.load()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {str(e)}")
    try:
        detections = detector.predict(image, conf=CONFIDENCE_THRESHOLD)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference failed: {str(e)}")
    if not detections:
        return {
            "predicted_label": None, "confidence": 0.0,
            "threshold": CONFIDENCE_THRESHOLD, "top_predictions": [],
            "parent_class": None, "display_name": None, "available_sizes": [],
        }
    top = detections[:TOP_K]
    best = top[0]
    is_confident = best.conf >= CONFIDENCE_THRESHOLD

    # ── Resolve type class and available sizes ────────────────────────────────
    # The new YOLO11s-cls model outputs type class_ids like "vis__th__zinc__48__din933".
    # We query the DB for all products of that type so Flutter can show the size list.
    # Legacy diameter-based labels ("8mm_70mm", "bolt_M8") fall back to the old path.
    if is_confident:
        label = best.label
        # New type-classifier output: contains "__" separator
        if "__" in label:
            parent_class    = label
            display_name    = _class_id_to_display(label)
            available_sizes = _get_available_sizes_by_type(label)
        else:
            # Legacy fallback: extract diameter from old format
            diameter        = _extract_diameter(label)
            parent_class    = _parent_class_name(diameter) if diameter else None
            display_name    = _display_name(diameter) if diameter else None
            available_sizes = _get_available_sizes(diameter) if diameter else []
    else:
        parent_class    = None
        display_name    = None
        available_sizes = []

    return {
        "predicted_label": best.label if is_confident else None,
        "confidence":      round(best.conf, 4),
        "threshold":       CONFIDENCE_THRESHOLD,
        "top_predictions": [{"label": d.label, "confidence": round(d.conf, 4)} for d in top],
        # ── Type-classifier fields ────────────────────────────────────────────
        "parent_class":    parent_class,    # e.g. "vis__th__zinc__48__din933"
        "display_name":    display_name,    # e.g. "Vis Th Zinc 4.8 DIN933"
        "available_sizes": available_sizes, # all products of this type with shelf info
    }

# ── Measure (ruler-based) ──────────────────────────────────────────────────────
@app.post("/measure")
async def measure_endpoint(file: UploadFile = File(...)):
    """
    Measure bolt dimensions using a metric ruler visible in the image.
    Returns measured length/diameter in mm and the nearest matching product.
    No ML model required — uses OpenCV ruler detection.
    """
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file received.")
    try:
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        image.load()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {str(e)}")

    try:
        from measure import measure_bolt
        result = measure_bolt(image)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Measurement error: {str(e)}")

    if result is None:
        raise HTTPException(
            status_code=422,
            detail="Could not detect ruler or bolt. Make sure both are clearly visible and the ruler is horizontal at the bottom of the frame.",
        )

    label = result.nearest_label

    # Find all matching SKUs for this label
    matching_skus = [sku for sku, lbl in SKU_TO_LABEL.items() if lbl == label]

    # Look up product in database
    product = None
    if matching_skus:
        with engine.connect() as conn:
            for sku in matching_skus:
                rows = conn.execute(text("""
                    SELECT p.*, s.aisle, s.bay, s.zone,
                           st.quantity_on_shelf, st.quantity_in_backstore, st.status
                    FROM products p
                    LEFT JOIN shelf_locations s ON p.shelf_id = s.shelf_id
                    LEFT JOIN stock st ON p.sku = st.sku
                    WHERE p.sku = :sku
                """), {"sku": sku})
                row = rows.fetchone()
                if row:
                    product = dict(row._mapping)
                    break

    return {
        "method":           "ruler_measurement",
        "measured_length_mm":   result.length_mm,
        "measured_diameter_mm": result.diameter_mm,
        "pixels_per_mm":    result.pixels_per_mm,
        "nearest_label":    label,
        "confidence":       result.confidence,
        "matching_skus":    matching_skus,
        "product":          product,
    }

# ── Products ───────────────────────────────────────────────────────────────────
@app.get("/products")
def get_products(search: str = ""):
    with engine.connect() as conn:
        if search:
            q = f"%{search.lower()}%"
            rows = conn.execute(text("""
                SELECT p.*, s.aisle, s.bay, s.zone,
                       st.quantity_on_shelf, st.quantity_in_backstore, st.status
                FROM products p
                LEFT JOIN shelf_locations s ON p.shelf_id = s.shelf_id
                LEFT JOIN stock st ON p.sku = st.sku
                WHERE LOWER(p.name) LIKE :q OR LOWER(p.sku) LIKE :q
                   OR LOWER(p.brand) LIKE :q OR LOWER(p.category) LIKE :q
                ORDER BY p.name LIMIT 50
            """), {"q": q})
        else:
            rows = conn.execute(text("""
                SELECT p.*, s.aisle, s.bay, s.zone,
                       st.quantity_on_shelf, st.quantity_in_backstore, st.status
                FROM products p
                LEFT JOIN shelf_locations s ON p.shelf_id = s.shelf_id
                LEFT JOIN stock st ON p.sku = st.sku
                ORDER BY p.name
            """))
        return [dict(r._mapping) for r in rows]

@app.get("/products/{sku}")
def get_product(sku: str):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT p.*, s.aisle, s.bay, s.zone,
                   st.quantity_on_shelf, st.quantity_in_backstore, st.status
            FROM products p
            LEFT JOIN shelf_locations s ON p.shelf_id = s.shelf_id
            LEFT JOIN stock st ON p.sku = st.sku
            WHERE p.sku = :sku
        """), {"sku": sku})
        row = rows.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Product not found")
        return dict(row._mapping)

@app.get("/products/barcode/{barcode}")
def get_product_by_barcode(barcode: str):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT p.*, s.aisle, s.bay, s.zone,
                   st.quantity_on_shelf, st.quantity_in_backstore, st.status
            FROM products p
            LEFT JOIN shelf_locations s ON p.shelf_id = s.shelf_id
            LEFT JOIN stock st ON p.sku = st.sku
            WHERE p.barcode = :barcode
        """), {"barcode": barcode})
        row = rows.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Product not found")
        return dict(row._mapping)

@app.post("/products")
def create_product(p: ProductModel):
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO products (sku, barcode, name, brand, category, type, description, shelf_id)
            VALUES (:sku, :barcode, :name, :brand, :category, :type, :description, :shelf_id)
            ON CONFLICT (sku) DO UPDATE SET
                barcode=EXCLUDED.barcode, name=EXCLUDED.name, brand=EXCLUDED.brand,
                category=EXCLUDED.category, type=EXCLUDED.type,
                description=EXCLUDED.description, shelf_id=EXCLUDED.shelf_id,
                last_updated=NOW()
        """), p.model_dump())
        conn.execute(text("""
            INSERT INTO stock (sku) VALUES (:sku)
            ON CONFLICT (sku) DO NOTHING
        """), {"sku": p.sku})
        conn.commit()
    return {"message": "Product saved", "sku": p.sku}

@app.delete("/products/{sku}")
def delete_product(sku: str):
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM stock WHERE sku = :sku"), {"sku": sku})
        conn.execute(text("DELETE FROM products WHERE sku = :sku"), {"sku": sku})
        conn.commit()
    return {"message": "Product deleted"}

@app.post("/products/bulk")
def bulk_upsert_products(products: list[ProductModel]):
    with engine.connect() as conn:
        for p in products:
            conn.execute(text("""
                INSERT INTO products (sku, barcode, name, brand, category, type, description, shelf_id)
                VALUES (:sku, :barcode, :name, :brand, :category, :type, :description, :shelf_id)
                ON CONFLICT (sku) DO UPDATE SET
                    barcode=EXCLUDED.barcode, name=EXCLUDED.name, brand=EXCLUDED.brand,
                    category=EXCLUDED.category, type=EXCLUDED.type,
                    description=EXCLUDED.description, shelf_id=EXCLUDED.shelf_id,
                    last_updated=NOW()
            """), p.model_dump())
            conn.execute(text("""
                INSERT INTO stock (sku) VALUES (:sku)
                ON CONFLICT (sku) DO NOTHING
            """), {"sku": p.sku})
        conn.commit()
    return {"message": f"{len(products)} products saved"}

# ── Shelves ────────────────────────────────────────────────────────────────────
@app.get("/shelves")
def get_shelves():
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT * FROM shelf_locations ORDER BY aisle, bay"))
        return [dict(r._mapping) for r in rows]

@app.post("/shelves")
def create_shelf(s: ShelfModel):
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO shelf_locations (shelf_id, aisle, bay, zone, notes)
            VALUES (:shelf_id, :aisle, :bay, :zone, :notes)
            ON CONFLICT (shelf_id) DO UPDATE SET
                aisle=EXCLUDED.aisle, bay=EXCLUDED.bay,
                zone=EXCLUDED.zone, notes=EXCLUDED.notes
        """), s.model_dump())
        conn.commit()
    return {"message": "Shelf saved", "shelf_id": s.shelf_id}

@app.delete("/shelves/{shelf_id}")
def delete_shelf(shelf_id: str):
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM shelf_locations WHERE shelf_id = :id"), {"id": shelf_id})
        conn.commit()
    return {"message": "Shelf deleted"}

# ── Stock ──────────────────────────────────────────────────────────────────────
@app.put("/stock/{sku}")
def update_stock(sku: str, s: StockModel):
    status = "out_of_stock" if s.quantity_on_shelf == 0 else "low_stock" if s.quantity_on_shelf < 5 else "in_stock"
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO stock (sku, quantity_on_shelf, quantity_in_backstore, status)
            VALUES (:sku, :on_shelf, :backstore, :status)
            ON CONFLICT (sku) DO UPDATE SET
                quantity_on_shelf=EXCLUDED.quantity_on_shelf,
                quantity_in_backstore=EXCLUDED.quantity_in_backstore,
                status=EXCLUDED.status
        """), {"sku": sku, "on_shelf": s.quantity_on_shelf,
               "backstore": s.quantity_in_backstore, "status": status})
        conn.commit()
    return {"message": "Stock updated"}

# ── Admin auth ─────────────────────────────────────────────────────────────────
@app.post("/auth/login")
def login(body: AdminLoginModel):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT * FROM admin_users
            WHERE email = :email AND password_hash = :hash AND is_active = 1
        """), {"email": body.email, "hash": body.password_hash})
        row = rows.fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        r = dict(row._mapping)
        return {"name": r["name"], "email": r["email"], "role": r["role"]}

# ── Dataset management ─────────────────────────────────────────────────────────
@app.get("/dataset/classes")
def get_classes():
    result = []
    train_dir = Path(TYPE_DATASET_PATH) / "train"
    if train_dir.exists():
        for folder in sorted(train_dir.iterdir()):
            if folder.is_dir():
                count = sum(len(list(folder.glob(f"*.{ext}"))) for ext in ["jpg","jpeg","png"])
                result.append({"class_name": folder.name, "photo_count": count})
    total_images = sum(c["photo_count"] for c in result)
    return {"classes": result, "total_classes": len(result), "total_images": total_images}

@app.post("/dataset/add-photos")
async def add_photos(sku: str, files: list[UploadFile] = File(...)):
    label = sku_to_label(sku)
    if not label:
        raise HTTPException(status_code=400, detail=f"Cannot determine training class for SKU: {sku}")
    train_folder = Path(DATASET_PATH) / "train" / label
    val_folder   = Path(DATASET_PATH) / "val"   / label
    train_folder.mkdir(parents=True, exist_ok=True)
    val_folder.mkdir(parents=True, exist_ok=True)
    saved = 0
    for i, file in enumerate(files):
        contents = await file.read()
        try:
            img = Image.open(io.BytesIO(contents)).convert("RGB")
            img.load()
        except Exception:
            continue
        filename = f"upload_{int(time.time())}_{i}.jpg"
        dest = val_folder / filename if (i % 5 == 0) else train_folder / filename
        img.save(str(dest), "JPEG")
        saved += 1
    return {"saved": saved, "label": label, "sku": sku}

# ── Training ───────────────────────────────────────────────────────────────────
@app.post("/train")
def start_training(epochs: int = 50):
    if train_state["running"]:
        raise HTTPException(status_code=409, detail="Training already in progress.")
    def run():
        try:
            from ultralytics import YOLO
            train_state.update({"running": True, "status": "running",
                "total_epochs": epochs, "current_epoch": 0,
                "progress": 0, "message": "Starting training..."})
            output_dir = os.path.abspath(os.path.join(os.path.dirname(YOLO_WEIGHTS), "..", "runs"))
            model = YOLO("yolo11s-cls.pt")
            def on_epoch_end(trainer):
                ep  = trainer.epoch + 1
                acc = round(float(trainer.metrics.get("metrics/accuracy_top1", 0)), 4)
                train_state.update({"current_epoch": ep,
                    "progress": int((ep / epochs) * 100), "top1_acc": acc,
                    "message": f"Epoch {ep}/{epochs} — Top1: {acc:.1%}"})
            model.add_callback("on_train_epoch_end", on_epoch_end)
            model.train(data=TYPE_DATASET_PATH, epochs=epochs, imgsz=224,
                project=output_dir, name="type_classifier", exist_ok=True, verbose=False)
            best_src = os.path.join(output_dir, "type_classifier", "weights", "best.pt")
            shutil.copy2(best_src, os.path.abspath(YOLO_WEIGHTS))
            global detector
            from detector import Detector
            detector = Detector(weights_path=YOLO_WEIGHTS)
            acc_str = f"{train_state['top1_acc']:.1%}" if train_state["top1_acc"] is not None else "N/A"
            train_state.update({"status": "done", "progress": 100,
                "message": f"Training complete! Top1 accuracy: {acc_str}"})
        except Exception as e:
            train_state.update({"status": "error", "message": str(e)})
        finally:
            train_state["running"] = False
    threading.Thread(target=run, daemon=True).start()
    return {"message": "Training started."}

@app.get("/train/status")
def train_status():
    return train_state


# ── Enhanced 2-phase training ──────────────────────────────────────────────────
@app.post("/train/enhanced")
def start_enhanced_training(
    epochs_pretrain: int = 30,
    epochs_finetune: int = 50,
    no_augment: bool = False,
):
    """
    Run the full 2-phase training pipeline:

    Phase 1 — Pre-train yolov8n-cls.pt on 5 broad fastener categories
              (screw / bolt / nut / washer / other) using all staged public
              dataset images.  Saves ultralytics/pretrained_fastener.pt.

    Phase 2 — Fine-tune on the 25-class screw dataset.
              Optionally augments the training set in-place first (×5).
              Saves ultralytics/best.pt and reloads the live detector.
    """
    if train_state["running"]:
        raise HTTPException(status_code=409, detail="Training already in progress.")

    total_epochs = epochs_pretrain + epochs_finetune

    def run():
        try:
            from dataset_builder import (
                build_pretrain_dataset,
                run_phase1,
                augment_training_dataset,
                run_phase2,
            )

            train_state.update({
                "running": True, "status": "running",
                "total_epochs": total_epochs, "current_epoch": 0,
                "progress": 0, "top1_acc": None,
                "message": "Phase 1: Building pre-training dataset…",
            })

            # ── Phase 1 ───────────────────────────────────────────────────────
            build_pretrain_dataset()

            def on_phase1_epoch(trainer):
                ep  = trainer.epoch + 1
                acc = round(float(trainer.metrics.get("metrics/accuracy_top1", 0)), 4)
                train_state.update({
                    "current_epoch": ep,
                    "progress": int((ep / total_epochs) * 100),
                    "top1_acc": acc,
                    "message": f"[Phase 1] Epoch {ep}/{epochs_pretrain} — Top1: {acc}",
                })

            run_phase1(epochs=epochs_pretrain, on_epoch_end=on_phase1_epoch)

            # ── Phase 2 augmentation ─────────────────────────────────────────
            if not no_augment:
                train_state["message"] = "Phase 2: Augmenting 25-class training set…"
                augment_training_dataset(multiplier=5)

            # ── Phase 2 fine-tuning ──────────────────────────────────────────
            train_state["message"] = "Phase 2: Fine-tuning on 25 screw classes…"

            def on_phase2_epoch(trainer):
                ep  = trainer.epoch + 1
                acc = round(float(trainer.metrics.get("metrics/accuracy_top1", 0)), 4)
                combined_epoch = epochs_pretrain + ep
                train_state.update({
                    "current_epoch": combined_epoch,
                    "progress": int((combined_epoch / total_epochs) * 100),
                    "top1_acc": acc,
                    "message": f"[Phase 2] Epoch {ep}/{epochs_finetune} — Top1: {acc}",
                })

            run_phase2(epochs=epochs_finetune, on_epoch_end=on_phase2_epoch)

            # ── Reload live detector ─────────────────────────────────────────
            global detector
            from detector import Detector
            detector = Detector(weights_path=YOLO_WEIGHTS)

            train_state.update({
                "status": "done",
                "progress": 100,
                "message": (
                    f"Enhanced training complete! "
                    f"Top1 accuracy: {train_state['top1_acc']}"
                ),
            })

        except Exception as exc:
            train_state.update({"status": "error", "message": str(exc)})
        finally:
            train_state["running"] = False

    threading.Thread(target=run, daemon=True).start()
    return {
        "message": "Enhanced 2-phase training started.",
        "epochs_pretrain": epochs_pretrain,
        "epochs_finetune": epochs_finetune,
        "no_augment": no_augment,
    }


# ── Report system ──────────────────────────────────────────────────────────────

@app.post("/report")
async def submit_report(
    file:          UploadFile = File(...),
    wrong_class:   str        = Form(...),
    correct_class: str        = Form(...),
    reported_by:   str        = Form(""),
):
    """Staff submits a wrong-detection report. Image is saved for admin review."""
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file.")
    try:
        img = Image.open(io.BytesIO(contents)).convert("RGB")
        img.load()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {e}")

    dest_dir = Path(REPORTS_DIR) / correct_class
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename  = f"{int(time.time())}_{uuid.uuid4().hex[:8]}.jpg"
    dest_path = dest_dir / filename
    img.save(str(dest_path), "JPEG")

    with engine.connect() as conn:
        row = conn.execute(text("""
            INSERT INTO reports (image_path, wrong_class, correct_class, reported_by)
            VALUES (:image_path, :wrong_class, :correct_class, :reported_by)
            RETURNING id
        """), {
            "image_path":    str(dest_path),
            "wrong_class":   wrong_class,
            "correct_class": correct_class,
            "reported_by":   reported_by or None,
        }).fetchone()
        report_id = row[0]
        conn.commit()

    return {"id": report_id, "message": "Report submitted."}


@app.get("/admin/reports")
def get_reports(status: str = "pending"):
    """List reports by status: pending | confirmed | rejected | submitted."""
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, image_path, wrong_class, correct_class,
                   reported_by, status, created_at
            FROM reports
            WHERE status = :status
            ORDER BY created_at DESC
        """), {"status": status}).fetchall()

    result = []
    for r in rows:
        d = dict(r._mapping)
        p = Path(d["image_path"])
        d["image_url"] = f"/reported-images/{p.parent.name}/{p.name}"
        d["created_at"] = str(d["created_at"])
        result.append(d)
    return result


@app.post("/admin/reports/{report_id}/confirm")
def confirm_report(report_id: int):
    with engine.connect() as conn:
        conn.execute(text(
            "UPDATE reports SET status = 'confirmed' WHERE id = :id"
        ), {"id": report_id})
        conn.commit()
    return {"message": "Confirmed."}


@app.post("/admin/reports/{report_id}/reject")
def reject_report(report_id: int):
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT image_path FROM reports WHERE id = :id"
        ), {"id": report_id}).fetchone()
        if row:
            p = Path(row[0])
            if p.exists():
                p.unlink()
        conn.execute(text(
            "UPDATE reports SET status = 'rejected' WHERE id = :id"
        ), {"id": report_id})
        conn.commit()
    return {"message": "Rejected."}


@app.post("/admin/submit-batch")
def submit_batch():
    """Move all confirmed report images into the training dataset and mark submitted."""
    train_base = Path(TYPE_DATASET_PATH) / "train"

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, image_path, correct_class
            FROM reports WHERE status = 'confirmed'
        """)).fetchall()

        if not rows:
            return {"message": "No confirmed reports.", "count": 0}

        submitted = 0
        for row in rows:
            src = Path(row[1])
            if not src.exists():
                continue
            dest_dir = train_base / row[2]
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / f"report_{int(time.time())}_{uuid.uuid4().hex[:8]}.jpg"
            shutil.copy2(str(src), str(dest))
            conn.execute(text(
                "UPDATE reports SET status = 'submitted' WHERE id = :id"
            ), {"id": row[0]})
            submitted += 1

        conn.commit()

    return {"message": f"{submitted} images added to training dataset.", "count": submitted}


@app.get("/reported-images/{class_name}/{filename}")
async def get_report_image(class_name: str, filename: str):
    path = Path(REPORTS_DIR) / class_name / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image not found.")
    return FileResponse(str(path))


@app.get("/model/classes")
def get_model_classes():
    """Return all known class names from the loaded model or val directory."""
    try:
        if detector is not None and hasattr(detector, 'model') and hasattr(detector.model, 'names'):
            return {"classes": sorted(detector.model.names.values())}
    except Exception:
        pass
    val_dir = Path(TYPE_DATASET_PATH) / "val"
    if val_dir.exists():
        return {"classes": sorted(d.name for d in val_dir.iterdir() if d.is_dir())}
    return {"classes": []}
