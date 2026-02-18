from app import app, db
from sqlalchemy import text

with app.app_context():
    print("Question Table Info:")
    res = db.session.execute(text("PRAGMA table_info(question)")).fetchall()
    for col in res:
        print(col)
    
    print("\nAnswer Table Info:")
    res = db.session.execute(text("PRAGMA table_info(answer)")).fetchall()
    for col in res:
        print(col)
