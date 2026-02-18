from app import app
app.config['DEBUG'] = True
app.config['PROPAGATE_EXCEPTIONS'] = True
client = app.test_client()

def test_route(path):
    print(f"\nTesting {path}...")
    try:
        response = client.get(path)
        print(f"Status: {response.status_code}")
        if response.status_code == 500:
            print("ERROR 500 DETECTED!")
    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()

routes = [
    ('/', 302),
    ('/login', 200),
    ('/register', 200),
    ('/admin/dashboard', 302), # Redirects to login if not logged in
    ('/student/dashboard', 302), # Redirects to login if not logged in
]

def test_dashboards():
    with app.app_context():
        # Let's find an admin and a student user if they exist
        from app import User
        admin = User.query.filter_by(role='admin').first()
        student = User.query.filter_by(role='student').first()
        
        if admin:
            print(f"\nTesting /admin/dashboard as admin (ID: {admin.id})...")
            with client.session_transaction() as sess:
                sess['_user_id'] = str(admin.id)
                sess['_fresh'] = True
            resp = client.get('/admin/dashboard')
            print(f"Status: {resp.status_code}")
            if resp.status_code == 500:
                print("500 ERROR ON ADMIN DASHBOARD")
        
        if student:
            print(f"\nTesting /student/dashboard as student (ID: {student.id})...")
            with client.session_transaction() as sess:
                sess['_user_id'] = str(student.id)
                sess['_fresh'] = True
            resp = client.get('/student/dashboard')
            print(f"Status: {resp.status_code}")
            if resp.status_code == 500:
                print("500 ERROR ON STUDENT DASHBOARD")

for route, expected in routes:
    test_route(route)

test_dashboards()
