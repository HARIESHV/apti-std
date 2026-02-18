from app import app, db, Question
with app.app_context():
    qs = Question.query.all()
    for q in qs:
        print(f"ID: {q.id}, Limit: {q.time_limit}")
