import sqlite3
import os

db_path = 'instance/answer.db'
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"Tables: {tables}")
    
    for table in tables:
        print(f"\nColumns in {table}:")
        cursor.execute(f"PRAGMA table_info({table})")
        for col in cursor.fetchall():
            print(f"  {col[1]} ({col[2]})")
    conn.close()
