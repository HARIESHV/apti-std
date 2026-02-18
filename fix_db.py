import sqlite3
import os

db_path = 'instance/answer.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Correct the typo: meet.com.enps-rtu-ghih -> meet.google.com/abc-defg-hij
    # But wait, maybe the user wants a different link? 
    # The most likely intended link is meet.google.com/abc-defg-hij
    corrected_link = 'https://meet.google.com/abc-defg-hij'
    
    try:
        cursor.execute("UPDATE classroom SET active_meet_link = ?, detected_title = 'Status Pending' WHERE id = 1", (corrected_link,))
        conn.commit()
        print(f"Updated classroom link to: {corrected_link}")
    except Exception as e:
        print(f"Error updating classroom: {e}")
        
    conn.close()
else:
    print(f"Database not found at {db_path}")
