# Copyright © 2026 Mahmoud Triki (W2069987), University of Westminster. All rights reserved.
import sqlite3
import hashlib
import getpass
import os

DB_PATH = os.getenv(
    "SQLITE_DB_PATH",
    r"D:\smart_tool_flutter\.dart_tool\sqflite_common_ffi\databases\smart_tool.db"
)

email = input("Admin email: ").strip()
name  = input("Admin name: ").strip()
password = getpass.getpass("Password: ")

pw_hash = hashlib.sha256(password.encode()).hexdigest()

conn = sqlite3.connect(DB_PATH)
conn.execute("""
    INSERT OR REPLACE INTO admin_users (email, password_hash, name, role, is_active)
    VALUES (?, ?, ?, 'admin', 1)
""", (email, pw_hash, name))
conn.commit()
conn.close()

print(f"Admin user '{email}' created successfully.")
