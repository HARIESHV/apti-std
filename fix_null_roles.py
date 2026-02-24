import sqlite3
import os

db_path = 'instance/aptipro.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role FROM user WHERE role IS NULL")
    users = cursor.fetchall()
    print("Users with NULL role:")
    for u in users:
        print(f"ID: {u[0]}, Username: {u[1]}")
    
    if users:
        print("Fixing NULL roles...")
        cursor.execute("UPDATE user SET role='student' WHERE role IS NULL")
        conn.commit()
        print("Updated NULL roles to 'student'.")
    else:
        print("No NULL roles found.")
    conn.close()
else:
    print("Database not found")
