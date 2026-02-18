from app import app, db
from sqlalchemy import text

def add_time_limit_column():
    with app.app_context():
        # Check if the column already exists
        result = db.session.execute(text("PRAGMA table_info(question)"))
        columns = [row[1] for row in result]
        
        if 'time_limit' not in columns:
            print("Adding time_limit column to question table...")
            db.session.execute(text("ALTER TABLE question ADD COLUMN time_limit INTEGER DEFAULT 10"))
            db.session.commit()
            print("Column added successfully.")
        else:
            print("Column time_limit already exists.")

if __name__ == "__main__":
    add_time_limit_column()
