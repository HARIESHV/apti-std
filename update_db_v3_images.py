
import sqlite3
import os

db_path = 'instance/answer.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE question ADD COLUMN image_file VARCHAR(300)")
        print("image_file column added successfully.")
    except Exception as e:
        print(f"Error adding column (maybe exists?): {e}")
        
    conn.commit()
    conn.close()
else:
    print(f"Database not found at {db_path}")
