from app import app, db
import traceback

app.config['DEBUG'] = True
app.config['PROPAGATE_EXCEPTIONS'] = True
client = app.test_client()

def login_as(role):
    with app.app_context():
        from app import User
        user = User.query.filter_by(role=role).first()
        if user:
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True
            return user.id
        return None

def test_endpoint(method, path, data=None):
    print(f"\n--- Testing {method} {path} ---")
    try:
        if method == 'GET':
            resp = client.get(path, follow_redirects=True)
        else:
            resp = client.post(path, data=data, follow_redirects=True)
        
        print(f"Status: {resp.status_code}")
        if resp.status_code == 500:
            print("!!! INTERNAL SERVER ERROR DETECTED !!!")
            # print(resp.data.decode(errors='ignore')) # Only if needed
    except Exception:
        traceback.print_exc()

# Test Admin actions
if login_as('admin'):
    test_endpoint('GET', '/admin/refresh_classroom')
    
    data = {'meet_link': 'https://meet.google.com/abc-defg-hij', 'is_live': 'on'}
    test_endpoint('POST', '/admin/update_classroom', data)
    
    data = {'label': 'Test Link', 'url': 'https://meet.google.com/xyz-uvw-qkzp'}
    test_endpoint('POST', '/admin/add_meet_link', data)

# Test Student actions
if login_as('student'):
    # Need a valid question ID
    with app.app_context():
        from app import Question
        q = Question.query.first()
        if q:
            data = {
                'question_id': q.id,
                'selected_option': 'A'
            }
            test_endpoint('POST', '/student/submit_answer', data)
        else:
            print("No questions to test submission.")
