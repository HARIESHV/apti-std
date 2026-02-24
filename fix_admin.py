import sqlite3
import os

db_path = 'instance/aptipro.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role FROM user WHERE id=1")
    user = cursor.fetchone()
    if user:
        print(f"User 1: ID={user[0]}, Username={user[1]}, Role={user[2]}")
        if user[1] == 'admin' and user[2] != 'admin':
            print("Fixing role for admin user...")
            cursor.execute("UPDATE user SET role='admin' WHERE id=1")
            conn.commit()
            print("Role updated to admin.")
    else:
        print("User 1 not found.")
    conn.close()
else:
    print("Database not found")
