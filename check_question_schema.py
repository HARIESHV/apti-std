
import sqlite3
import os

db_path = 'instance/answer.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("--- Question Table Schema ---")
    try:
        cursor.execute("PRAGMA table_info(question)")
        columns = cursor.fetchall()
        for col in columns:
            print(col)
    except Exception as e:
        print(f"Error reading schema: {e}")
        
    conn.close()
else:
    print(f"Database not found at {db_path}")
