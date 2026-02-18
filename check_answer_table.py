from app import app, db, User, Question, Answer, Classroom, MeetLink

def check_model(model):
    try:
        with app.app_context():
            count = model.query.count()
            print(f"{model.__name__} count: {count}")
    except Exception as e:
        print(f"ERROR on {model.__name__}: {e}")

models = [User, Question, Answer, Classroom, MeetLink]
for m in models:
    check_model(m)
