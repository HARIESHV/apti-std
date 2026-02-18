from app import app, db, User, Answer, Question
from datetime import datetime

def check_exports():
    with app.app_context():
        print("Checking Export Members Logic...")
        try:
            members = User.query.filter_by(role='student').all()
            for m in members:
                print(f"Checking user: {m.username} (ID: {m.id})")
                
                # Logic from export_members
                total_submissions = len(m.answers)
                correct_submissions = sum(1 for a in m.answers if a.is_correct)
                accuracy = f"{(correct_submissions / total_submissions * 100):.1f}%" if total_submissions > 0 else "0%"
                
                print(f"  - Answers count: {len(m.answers)}")
                
                # Check for None values in submitted_at which would break max()
                submitted_dates = [a.submitted_at for a in m.answers if a.submitted_at]
                print(f"  - Valid submitted dates: {len(submitted_dates)}")
                
                # The line that might crash
                try:
                    last_submission = max((a.submitted_at for a in m.answers if a.submitted_at), default=None)
                    msg = last_submission.strftime('%Y-%m-%d %H:%M:%S') if last_submission else 'Never'
                    print(f"  - Last Submission: {msg}")
                except Exception as e:
                    print(f"  !!! ERROR calculating last_submission: {e}")

                # Check created_at
                try:
                    joined = m.created_at.strftime('%Y-%m-%d %H:%M:%S') if m.created_at else 'Unknown'
                    print(f"  - Joined: {joined}")
                except Exception as e:
                    print(f"  !!! ERROR calculating joined date: {e}")
                    
            print("Export Members Logic seems OK.")
            
        except Exception as e:
            print(f"CRASH in check_exports: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    check_exports()
