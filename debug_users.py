import sqlite3
import os

db_path = 'instance/aptipro.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        users = cursor.execute("SELECT id, username, role, is_active FROM user").fetchall()
        print("Users in DB:")
        for u in users:
            print(f"ID: {u[0]}, Username: {u[1]}, Role: {u[2]}, Active: {u[3]}")
    except Exception as e:
        print(f"Error: {e}")
    conn.close()
else:
    print("Database not found")
