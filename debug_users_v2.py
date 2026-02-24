import sqlite3
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# We need the app context to use the model, or just use sqlite3
db_path = 'instance/aptipro.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, username, role FROM user")
        users = cursor.fetchall()
        print("Detailed Users List:")
        for u in users:
            print(f"ID: {u[0]} | Username: [{u[1]}] | Role: [{u[2]}]")
    except Exception as e:
        print(f"Error: {e}")
    conn.close()
else:
    print("Database not found")
