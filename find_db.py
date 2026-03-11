import os

username = os.environ.get("USERNAME", "triki")
search_roots = [
    rf"C:\Users\{username}\AppData\Roaming",
    rf"C:\Users\{username}\AppData\Local",
]

print("Searching for smart_tool.db...")
for root in search_roots:
    for dirpath, dirs, files in os.walk(root):
        for f in files:
            if f == "smart_tool.db":
                print(f"FOUND: {os.path.join(dirpath, f)}")

print("Search complete.")

def find_db():
    if os.path.exists(DB_PATH):
        return DB_PATH
    return None