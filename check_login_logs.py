import sqlite3
import os

db_path = 'instance/aptipro.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, user_id, login_time, status FROM login_log ORDER BY login_time DESC LIMIT 10")
        logs = cursor.fetchall()
        print("Recent Login Logs:")
        for l in logs:
            print(f"ID: {l[0]} | UserID: {l[1]} | Time: {l[2]} | Status: {l[3]}")
    except Exception as e:
        print(f"Error: {e}")
    conn.close()
else:
    print("Database not found")
