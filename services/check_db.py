# Copyright © 2026 Mahmoud Triki (W2069987), University of Westminster. All rights reserved.
import sqlite3

DB_PATH = r"D:\smart_tool_flutter\.dart_tool\sqflite_common_ffi\databases\smart_tool.db"

conn = sqlite3.connect(DB_PATH)
rows = conn.execute("SELECT id, email, name, is_active FROM admin_users;").fetchall()
conn.close()

if rows:
    for r in rows:
        print(r)
else:
    print("No admin users found!")

