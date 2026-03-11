import sqlite3, requests

SQLITE_PATH = r"D:\smart_tool_flutter\.dart_tool\sqflite_common_ffi\databases\smart_tool.db"
API_URL = "http://127.0.0.1:8000"

conn = sqlite3.connect(SQLITE_PATH)
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT * FROM products").fetchall()

products = []
for r in rows:
    products.append({
        "sku": r["sku"],
        "barcode": r["barcode"],
        "name": r["name"],
        "brand": r["brand"],
        "category": r["category"],
        "type": r["type"] or "tool",
        "description": r["description"],
        "shelf_id": None,
    })

# Send in batches of 500
batch_size = 500
for i in range(0, len(products), batch_size):
    batch = products[i:i+batch_size]
    r = requests.post(f"{API_URL}/products/bulk", json=batch)
    print(f"Batch {i//batch_size + 1}: {r.json()}")

print(f"Done! Migrated {len(products)} products.")
conn.close()