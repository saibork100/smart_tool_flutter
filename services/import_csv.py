# Copyright © 2026 Mahmoud Triki (W2069987), University of Westminster. All rights reserved.
"""
Import products_rows.csv into the Flutter app's SQLite database.

Run with:
    python import_csv.py

Make sure to update DB_PATH to match your actual SQLite database location.
"""

import sqlite3
import csv
import os
import sys

# ── Config ────────────────────────────────────────────────────────────────────

CSV_PATH = r"E:\products_rows.csv"

# Flutter stores SQLite on Windows at:
# C:\Users\<username>\AppData\Roaming\com.example\smart_tool_recognition\smart_tool.db
# Find it automatically:
USERNAME = os.environ.get("USERNAME") or os.environ.get("USER") or os.path.basename(os.path.expanduser("~"))
DB_PATH = r"D:\smart_tool_flutter\.dart_tool\sqflite_common_ffi\databases\smart_tool.db"

# ── Main ──────────────────────────────────────────────────────────────────────

def find_db():
    """Try to find the SQLite database file."""
    candidates = [
        DB_PATH,
        rf"C:\Users\{USERNAME}\AppData\Roaming\smart_tool_recognition\smart_tool.db",
        rf"C:\Users\{USERNAME}\AppData\Local\smart_tool_recognition\smart_tool.db",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def import_csv(db_path: str, csv_path: str):
    print(f"Database: {db_path}")
    print(f"CSV: {csv_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Read CSV (semicolon delimited)
    with open(csv_path, encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f, delimiter=";")
        rows = list(reader)

    print(f"Found {len(rows)} rows in CSV")
    print(f"Columns: {list(rows[0].keys())[:10]}...")  # show first 10 columns

    inserted = 0
    skipped = 0

    for row in rows:
        try:
            sku = (row.get("SKU") or row.get("sku") or "").strip()
            if not sku:
                skipped += 1
                continue

            name = (row.get("Name") or row.get("name") or "").strip()
            if not name:
                skipped += 1
                continue

            # Map CSV columns to SQLite schema
            brand_id = (row.get("brand_id") or "").strip()
            brand = brand_id if brand_id else "Unknown"

            main_cat = (row.get("Main Category") or row.get("main_category") or "").strip()
            sub_cat = (row.get("sub_category_id") or "").strip()
            category = main_cat or sub_cat or "General"

            description = (row.get("Short description") or row.get("detailed_description") or "").strip()
            # Strip HTML tags from description
            import re
            description = re.sub(r'<[^>]+>', '', description)[:500]

            stock_qty = row.get("stock_quantity") or "0"
            try:
                stock_qty = int(float(stock_qty))
            except (ValueError, TypeError):
                stock_qty = 0

            stock_status_raw = (row.get("stock_status") or "instock").strip().lower()
            if stock_status_raw in ("instock", "in_stock", "1"):
                stock_status = "in_stock"
            elif stock_status_raw in ("outofstock", "out_of_stock", "0"):
                stock_status = "out_of_stock"
            else:
                stock_status = "in_stock"

            # Insert product
            cursor.execute("""
                INSERT OR REPLACE INTO products 
                (sku, name, brand, category, type, description, confidence_threshold, last_updated)
                VALUES (?, ?, ?, ?, 'tool', ?, 0.5, datetime('now'))
            """, (sku, name, brand, category, description))

            # Insert stock
            cursor.execute("""
                INSERT OR IGNORE INTO stock 
                (sku, quantity_on_shelf, quantity_in_backstore, status)
                VALUES (?, ?, 0, ?)
            """, (sku, stock_qty, stock_status))

            inserted += 1

            if inserted % 500 == 0:
                print(f"  Inserted {inserted} products...")
                conn.commit()

        except Exception as e:
            print(f"  Error on row {sku}: {e}")
            skipped += 1

    conn.commit()
    conn.close()

    print(f"\nDone!")
    print(f"  Inserted: {inserted} products")
    print(f"  Skipped:  {skipped} rows")


if __name__ == "__main__":
    # Check CSV exists
    if not os.path.exists(CSV_PATH):
        print(f"ERROR: CSV not found at {CSV_PATH}")
        print("Please update CSV_PATH in this script.")
        sys.exit(1)

    # Find database
    db_path = find_db()
    if not db_path:
        print("ERROR: Could not find SQLite database.")
        print("Please run the Flutter app at least once first, then run this script.")
        print(f"Expected location: {DB_PATH}")
        sys.exit(1)

    import_csv(db_path, CSV_PATH)
