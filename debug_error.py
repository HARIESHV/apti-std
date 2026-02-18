from app import app
import sys
import traceback

app.config['DEBUG'] = True
app.config['TESTING'] = True
app.config['PROPAGATE_EXCEPTIONS'] = True

client = app.test_client()

def test_with_login(role, endpoint):
    """Test endpoint with logged in user"""
    with app.app_context():
        from app import User
        user = User.query.filter_by(role=role).first()
        if not user:
            print(f"No {role} user found!")
            return
        
        print(f"\n{'='*60}")
        print(f"Testing {endpoint} as {role} (User: {user.username})")
        print('='*60)
        
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
            sess['_fresh'] = True
        
        try:
            response = client.get(endpoint, follow_redirects=False)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 500:
                print("\n!!! 500 INTERNAL SERVER ERROR !!!\n")
                # Try to get the error from response data
                data = response.data.decode('utf-8', errors='ignore')
                if 'Traceback' in data or 'Error' in data:
                    print(data[:2000])  # Print first 2000 chars
                else:
                    print("No traceback in response. Trying direct import...")
                    # Try to trigger the route directly
                    with app.test_request_context(endpoint):
                        from flask import session
                        session['_user_id'] = str(user.id)
                        session['_fresh'] = True
                        try:
                            if role == 'admin':
                                from app import admin_dashboard
                                admin_dashboard()
                            else:
                                from app import student_dashboard
                                student_dashboard()
                        except Exception as e:
                            print("\nDIRECT CALL ERROR:")
                            traceback.print_exc()
            else:
                print("✓ Request successful")
                
        except Exception as e:
            print(f"\nEXCEPTION DURING REQUEST:")
            traceback.print_exc()

# Test both dashboards
test_with_login('admin', '/admin/dashboard')
test_with_login('student', '/student/dashboard')
