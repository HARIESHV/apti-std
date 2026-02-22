import sqlite3
import os

db_path = 'instance/aptipro.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        users = cursor.execute("SELECT count(*) FROM user").fetchone()[0]
        questions = cursor.execute("SELECT count(*) FROM question").fetchone()[0]
        answers = cursor.execute("SELECT count(*) FROM answer").fetchone()[0]
        print(f"Users: {users}")
        print(f"Questions: {questions}")
        print(f"Answers: {answers}")
    except Exception as e:
        print(f"Error: {e}")
    conn.close()
else:
    print("Database not found")
