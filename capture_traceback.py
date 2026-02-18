from app import app
import traceback

client = app.test_client()

def capture_500(path, user_id=None):
    print(f"\nTesting {path} (User ID: {user_id})...")
    with app.app_context():
        # Setup session if user_id provided
        if user_id:
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user_id)
                sess['_fresh'] = True
        
        try:
            response = client.get(path)
            if response.status_code == 500:
                print("500 ERROR CAUGHT!")
                # The response data might contain the traceback if Debug is on
                # But since we want to be sure, let's try to trigger it manually
                # by calling the view function directly with a mock request
                # This is harder, so let's just enable debug and print data.
        except Exception:
            traceback.print_exc()

app.config['DEBUG'] = True
app.config['PROPAGATE_EXCEPTIONS'] = True

with app.app_context():
    from app import User
    admin = User.query.filter_by(role='admin').first()
    student = User.query.filter_by(role='student').first()
    
    if admin:
        resp = client.get('/admin/dashboard', follow_redirects=True)
        if resp.status_code == 500:
            print(resp.data.decode(errors='ignore'))
            
    if student:
        # Mock login
        with client.session_transaction() as sess:
            sess['_user_id'] = str(student.id)
            sess['_fresh'] = True
        resp = client.get('/student/dashboard')
        if resp.status_code == 500:
            print(resp.data.decode(errors='ignore'))
