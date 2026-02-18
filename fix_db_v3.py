from app import app, db
from sqlalchemy import text

def fix_question_table():
    with app.app_context():
        # Check columns
        result = db.session.execute(text("PRAGMA table_info(question)"))
        columns = [row[1] for row in result]
        
        if 'created_at' not in columns:
            print("Adding created_at column to question table...")
            try:
                db.session.execute(text("ALTER TABLE question ADD COLUMN created_at DATETIME"))
                db.session.commit()
                # Update existing rows with a default value
                db.session.execute(text("UPDATE question SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))
                db.session.commit()
                print("Column created_at added successfully.")
            except Exception as e:
                print(f"Error adding created_at: {e}")
        else:
            print("Column created_at already exists.")

if __name__ == "__main__":
    fix_question_table()
