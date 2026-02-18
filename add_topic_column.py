"""
Migration: Add 'topic' column to the question table.
Run this once after deploying the topic feature.
"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'instance', 'answer.db')
if not os.path.exists(db_path):
    db_path = os.path.join(os.path.dirname(__file__), 'answer.db')

if not os.path.exists(db_path):
    print("No local SQLite DB found — skipping migration (Vercel/Postgres will auto-create via db.create_all).")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Check if column already exists
    cursor.execute("PRAGMA table_info(question)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'topic' not in columns:
        cursor.execute("ALTER TABLE question ADD COLUMN topic VARCHAR(200)")
        conn.commit()
        print("✅ 'topic' column added to question table.")
    else:
        print("ℹ️  'topic' column already exists — no changes needed.")
    conn.close()
