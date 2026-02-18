from app import app, db, Question

with app.app_context():
    questions = Question.query.all()
    for q in questions:
        # Assuming current value is in minutes, convert to seconds
        old_limit = q.time_limit
        q.time_limit = old_limit * 60
        print(f"Updated Question {q.id}: {old_limit}m -> {q.time_limit}s")
    
    db.session.commit()
    print("Migration complete.")
