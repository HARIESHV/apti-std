import sqlite3
import os

db_path = 'instance/aptipro.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Find the user named 'admin'
    cursor.execute("SELECT id, username, role FROM user WHERE username='admin'")
    user = cursor.fetchone()
    if user:
        print(f"Found admin user: ID={user[0]}, Role={user[2]}")
        if user[2] != 'admin':
            print("Updating role to admin...")
            cursor.execute("UPDATE user SET role='admin' WHERE username='admin'")
            conn.commit()
            print("Done.")
        else:
            print("Role is already admin.")
    else:
        print("Admin user not found.")
    conn.close()
else:
    print("Database not found")
