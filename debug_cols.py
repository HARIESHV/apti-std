import sqlite3
conn = sqlite3.connect('instance/answer.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
for table in tables:
    print(f"\n{table} columns:")
    cursor.execute(f"PRAGMA table_info({table})")
    for row in cursor.fetchall():
        print(f"- {row[1]}")
conn.close()
