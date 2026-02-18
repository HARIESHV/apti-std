from app import app, db, Question, datetime
from sqlalchemy import text

def fix_missing_data():
    with app.app_context():
        print("Checking for missing data in Questions...")
        questions = Question.query.all()
        fixed_count = 0
        for q in questions:
            updated = False
            if q.created_at is None:
                q.created_at = datetime.utcnow()
                updated = True
            if q.time_limit is None:
                q.time_limit = 10
                updated = True
            
            if updated:
                fixed_count += 1
        
        if fixed_count > 0:
            db.session.commit()
            print(f"Fixed {fixed_count} questions with missing metadata.")
        else:
            print("No missing data found.")

if __name__ == "__main__":
    fix_missing_data()
