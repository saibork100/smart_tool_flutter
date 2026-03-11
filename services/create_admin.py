import sqlite3
import hashlib

DB_PATH = r"D:\smart_tool_flutter\.dart_tool\sqflite_common_ffi\databases\smart_tool.db"

email    = "trikimahoud86@gmail.com"   # ← change this
password = "admin123"              # ← change this
name     = "Admin"

pw_hash = hashlib.sha256(password.encode()).hexdigest()

conn = sqlite3.connect(DB_PATH)
conn.execute("""
    INSERT OR REPLACE INTO admin_users (email, password_hash, name, role, is_active)
    VALUES (?, ?, ?, 'admin', 1)
""", (email, pw_hash, name))
conn.commit()
conn.close()

print(f"Admin created: {email} / {password}")