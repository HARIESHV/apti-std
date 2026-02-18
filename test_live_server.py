import requests
import traceback

def test_endpoint(url, auth=None):
    """Test an endpoint and capture any errors"""
    print(f"\n{'='*60}")
    print(f"Testing: {url}")
    print('='*60)
    
    try:
        session = requests.Session()
        
        # If auth provided, login first
        if auth:
            login_url = "http://localhost:5000/login"
            login_data = {'username': auth[0], 'password': auth[1]}
            login_resp = session.post(login_url, data=login_data, allow_redirects=True)
            print(f"Login Status: {login_resp.status_code}")
        
        # Now test the actual endpoint
        response = session.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 500:
            print("\n!!! 500 INTERNAL SERVER ERROR !!!")
            print("\nResponse Content:")
            print(response.text[:2000])  # First 2000 chars
        elif response.status_code == 200:
            print("✓ Success")
        else:
            print(f"Response: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to server. Is it running on port 5000?")
    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()

# Test various endpoints
print("Testing AptitudePro Server...")
test_endpoint("http://localhost:5000/")
test_endpoint("http://localhost:5000/login")
test_endpoint("http://localhost:5000/admin/dashboard", auth=('admin', 'adminpassword'))
test_endpoint("http://localhost:5000/student/dashboard", auth=('Hariesh', 'hariesh'))
