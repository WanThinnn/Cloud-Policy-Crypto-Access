"""
Test script for Authentication API
"""
import requests
import json
import time
import random
import string

BASE_URL = "http://127.0.0.1:5000"
AUTH_URL = f"{BASE_URL}/auth"

def generate_random_string(length=8):
    """Generate random string for testing"""
    return ''.join(random.choices(string.ascii_lowercase, k=length))

def test_auth_health():
    """Test auth health endpoint"""
    print("🔍 Testing Auth Health Check...")
    try:
        response = requests.get(f"{AUTH_URL}/health")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Service: {data.get('service')}")
            print(f"   Status: {data.get('status')}")
            return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
    return False

def test_password_validation():
    """Test password validation"""
    print("🔍 Testing Password Validation...")
    
    test_passwords = [
        ("weak", "123"),
        ("better", "Password123"),
        ("strong", "MyStrong@Pass123!")
    ]
    
    for label, password in test_passwords:
        try:
            response = requests.post(f"{AUTH_URL}/validate-password", json={
                "password": password
            })
            
            if response.status_code == 200:
                data = response.json()
                validation = data.get('validation', {})
                print(f"   {label.upper()} password '{password}':")
                print(f"     Valid: {validation.get('valid', False)}")
                if not validation.get('valid', True):
                    errors = validation.get('errors', [])
                    for error in errors[:2]:  # Show first 2 errors
                        print(f"     - {error}")
            
        except Exception as e:
            print(f"   ❌ Error testing {label}: {e}")

def test_user_registration():
    """Test user registration"""
    print("🔍 Testing User Registration...")
    
    # Generate unique test data
    username = f"testuser_{generate_random_string()}"
    email = f"test_{generate_random_string()}@example.com"
    password = "TestPass123!"
    
    try:
        response = requests.post(f"{AUTH_URL}/register", json={
            "username": username,
            "email": email,
            "password": password
        })
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            if data.get('success'):
                user = data.get('user', {})
                print(f"   ✅ User created successfully!")
                print(f"     ID: {user.get('id')}")
                print(f"     Username: {user.get('username')}")
                print(f"     Email: {user.get('email')}")
                
                return {
                    'success': True,
                    'user_id': user.get('id'),
                    'username': username,
                    'password': password
                }
        else:
            data = response.json()
            print(f"   ❌ Registration failed: {data.get('error')}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    return {'success': False}

def test_user_login(username, password):
    """Test user login"""
    print("🔍 Testing User Login...")
    
    try:
        response = requests.post(f"{AUTH_URL}/login", json={
            "username": username,
            "password": password
        })
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                user = data.get('user', {})
                print(f"   ✅ Login successful!")
                print(f"     Username: {user.get('username')}")
                print(f"     Email: {user.get('email')}")
                return {'success': True, 'user': user}
        else:
            data = response.json()
            print(f"   ❌ Login failed: {data.get('error')}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    return {'success': False}

def test_get_user(user_id):
    """Test get user info"""
    print("🔍 Testing Get User Info...")
    
    try:
        response = requests.get(f"{AUTH_URL}/user/{user_id}")
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                user = data.get('user', {})
                print(f"   ✅ User info retrieved!")
                print(f"     ID: {user.get('id')}")
                print(f"     Username: {user.get('username')}")
                print(f"     Email: {user.get('email')}")
                print(f"     Active: {user.get('is_active')}")
                return True
        else:
            data = response.json()
            print(f"   ❌ Failed: {data.get('error')}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    return False

def test_update_user(user_id):
    """Test update user info"""
    print("🔍 Testing Update User Info...")
    
    new_email = f"updated_{generate_random_string()}@example.com"
    
    try:
        response = requests.put(f"{AUTH_URL}/user/{user_id}", json={
            "email": new_email
        })
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                user = data.get('user', {})
                print(f"   ✅ User updated successfully!")
                print(f"     New Email: {user.get('email')}")
                return True
        else:
            data = response.json()
            print(f"   ❌ Update failed: {data.get('error')}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    return False

def test_change_password(user_id, old_password):
    """Test change password"""
    print("🔍 Testing Change Password...")
    
    new_password = "NewTestPass456!"
    
    try:
        response = requests.post(f"{AUTH_URL}/change-password", json={
            "user_id": user_id,
            "old_password": old_password,
            "new_password": new_password
        })
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"   ✅ Password changed successfully!")
                return {'success': True, 'new_password': new_password}
        else:
            data = response.json()
            print(f"   ❌ Change password failed: {data.get('error')}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    return {'success': False}

def test_login_with_wrong_password(username):
    """Test login with wrong password"""
    print("🔍 Testing Login with Wrong Password...")
    
    try:
        response = requests.post(f"{AUTH_URL}/login", json={
            "username": username,
            "password": "WrongPassword123!"
        })
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 401:
            data = response.json()
            print(f"   ✅ Correctly rejected wrong password!")
            print(f"     Error: {data.get('error')}")
            return True
        else:
            print(f"   ❌ Should have rejected wrong password!")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    return False

def main():
    """Main test function"""
    print("=" * 70)
    print("🧪 TESTING AUTHENTICATION API")
    print("=" * 70)
    
    # Test results tracking
    test_results = []
    
    # Test auth health
    test_results.append(("Auth Health Check", test_auth_health()))
    
    # Test password validation
    test_password_validation()  # This is informational
    
    # Test user registration
    print(f"\n{'-'*50}")
    registration_result = test_user_registration()
    test_results.append(("User Registration", registration_result['success']))
    
    if not registration_result['success']:
        print("\n❌ Registration failed, stopping tests...")
        return
    
    user_id = registration_result['user_id']
    username = registration_result['username']
    password = registration_result['password']
    
    # Test user login
    print(f"\n{'-'*50}")
    login_result = test_user_login(username, password)
    test_results.append(("User Login", login_result['success']))
    
    # Test get user info
    print(f"\n{'-'*50}")
    test_results.append(("Get User Info", test_get_user(user_id)))
    
    # Test update user
    print(f"\n{'-'*50}")
    test_results.append(("Update User Info", test_update_user(user_id)))
    
    # Test change password
    print(f"\n{'-'*50}")
    change_result = test_change_password(user_id, password)
    test_results.append(("Change Password", change_result['success']))
    
    # Test login with new password if changed
    if change_result['success']:
        print(f"\n{'-'*50}")
        new_login_result = test_user_login(username, change_result['new_password'])
        test_results.append(("Login with New Password", new_login_result['success']))
        current_password = change_result['new_password']
    else:
        current_password = password
    
    # Test login with wrong password
    print(f"\n{'-'*50}")
    test_results.append(("Wrong Password Rejection", test_login_with_wrong_password(username)))
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    
    passed = 0
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<30} {status}")
        if result:
            passed += 1
    
    total = len(test_results)
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL AUTHENTICATION TESTS PASSED!")
    else:
        print("⚠️  Some tests failed. Check the output above.")
    
    print("=" * 70)

if __name__ == "__main__":
    # Wait a bit for server to be ready
    print("Waiting for server to be ready...")
    time.sleep(2)
    main()
