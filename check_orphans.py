from app import app, Answer, Question, User
with app.app_context():
    answers = Answer.query.all()
    orphans_q = [a.id for a in answers if a.question is None]
    orphans_s = [a.id for a in answers if a.student is None]
    print(f"Orphan Questions: {orphans_q}")
    print(f"Orphan Students: {orphans_s}")

    if orphans_q or orphans_s:
        print("FOUND ORPHAN RECORDS!")
    else:
        print("No orphan records found.")
