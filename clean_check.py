import sqlite3
import os

db_path = 'instance/aptipro.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role FROM user")
    rows = cursor.fetchall()
    for row in rows:
        print(f"USER_DATA_START|{row[0]}|{row[1]}|{row[2]}|USER_DATA_END")
    conn.close()
else:
    print("DB_NOT_FOUND")
