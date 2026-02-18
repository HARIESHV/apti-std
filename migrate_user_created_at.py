import sqlite3
import os

db_path = os.path.join('instance', 'answer.db')
if not os.path.exists(db_path):
    # Try alternate path if not in instance
    db_path = 'answer.db'

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE user ADD COLUMN created_at DATETIME")
        print("Successfully added created_at column to user table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column created_at already exists in user table.")
        else:
            print(f"Error: {e}")
            
    conn.commit()
    conn.close()
else:
    print(f"Database not found at {db_path}")
