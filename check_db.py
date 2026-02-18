import sqlite3
import os

db_path = 'instance/answer.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("--- Classroom Table ---")
    try:
        cursor.execute("SELECT * FROM classroom")
        print(cursor.fetchall())
    except Exception as e:
        print(f"Error reading classroom: {e}")
        
    print("\n--- MeetLink Table ---")
    try:
        cursor.execute("SELECT * FROM meet_link")
        print(cursor.fetchall())
    except Exception as e:
        print(f"Error reading meet_link: {e}")
        
    conn.close()
else:
    print(f"Database not found at {db_path}")
