import sqlite3
import os

db_path = r'c:\test\multirolevoicebot(taksh)\multirolevoicebot\db.sqlite3'
if os.path.exists(db_path):
    try:
        conn = sqlite3.connect(db_path)
        conn.execute('PRAGMA journal_mode=WAL;')
        print("WAL mode enabled successfully.")
        conn.close()
    except Exception as e:
        print(f"Error enabling WAL mode: {e}")
else:
    print("Database file not found.")
