import sqlite3
import os

db_path = 'instance/aptipro.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role, created_at FROM user ORDER BY id DESC")
    rows = cursor.fetchall()
    print("User List (Newest First):")
    for row in rows:
        print(f"ID: {row[0]} | Username: {row[1]} | Role: {row[2]} | Created At: {row[3]}")
    conn.close()
else:
    print("DB_NOT_FOUND")
