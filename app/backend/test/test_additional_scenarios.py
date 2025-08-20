"""
Additional tests for edge cases and advanced scenarios
"""
import requests
import json
import sys
import os

# Test configuration
BASE_URL = "http://localhost:5000"
CA_API_BASE = f"{BASE_URL}/ca"

def print_response(title, response):
    """Print formatted response"""
    print(f"\n{title}")
    print("=" * 50)
    print(f"Status Code: {response.status_code}")
    try:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
    except:
        print(f"Response: {response.text}")
    print("=" * 50)

def test_duplicate_key_generation():
    """Test generating key for user who already has one"""
    print("\n🔄 Testing Duplicate Key Generation...")
    
    user_id = "test_user_001"  # User from previous test
    url = f"{CA_API_BASE}/user/private-key/generate"
    data = {
        'user_id': user_id,
        'password': "NewPassword123@",
        'attributes': ["role:nurse", "department:emergency"]
    }
    
    response = requests.post(url, json=data)
    print_response("Duplicate Key Generation", response)
    
    return response.status_code == 409  # Should be conflict

def test_multiple_users():
    """Test generating keys for multiple users"""
    print("\n👥 Testing Multiple Users...")
    
    users = [
        {
            'user_id': 'doctor_001',
            'password': 'DoctorPass123@',
            'attributes': ['role:doctor', 'department:surgery']
        },
        {
            'user_id': 'nurse_001', 
            'password': 'NursePass123@',
            'attributes': ['role:nurse', 'department:emergency']
        },
        {
            'user_id': 'admin_001',
            'password': 'AdminPass123@',
            'attributes': ['role:admin', 'clearance_level:top']
        }
    ]
    
    url = f"{CA_API_BASE}/user/private-key/generate"
    
    for user in users:
        print(f"\nGenerating key for {user['user_id']}...")
        response = requests.post(url, json=user)
        print(f"Status: {response.status_code}")
        if response.status_code in [200, 201]:
            print(f"✅ Success for {user['user_id']}")
        else:
            print(f"❌ Failed for {user['user_id']}")

def test_authentication_all_users():
    """Test authentication for all users"""
    print("\n🔐 Testing Authentication for All Users...")
    
    users = [
        {'user_id': 'test_user_001', 'password': 'TestPass123@'},
        {'user_id': 'doctor_001', 'password': 'DoctorPass123@'},
        {'user_id': 'nurse_001', 'password': 'NursePass123@'},
        {'user_id': 'admin_001', 'password': 'AdminPass123@'}
    ]
    
    url = f"{CA_API_BASE}/user/private-key/authenticate"
    
    for user in users:
        print(f"\nAuthenticating {user['user_id']}...")
        response = requests.post(url, json=user)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success - Attributes: {data.get('attributes', [])}")
        else:
            print(f"❌ Failed for {user['user_id']}")

def test_system_resilience():
    """Test system with invalid inputs"""
    print("\n🛡️  Testing System Resilience...")
    
    # Test 1: Missing fields
    print("\n1. Testing missing fields...")
    url = f"{CA_API_BASE}/user/private-key/generate"
    response = requests.post(url, json={'user_id': 'test'})
    print(f"Missing fields: {response.status_code} (should be 400)")
    
    # Test 2: Invalid user_id for authentication
    print("\n2. Testing non-existent user...")
    url = f"{CA_API_BASE}/user/private-key/authenticate"
    data = {'user_id': 'non_existent_user', 'password': 'password'}
    response = requests.post(url, json=data)
    print(f"Non-existent user: {response.status_code} (should be 400)")
    
    # Test 3: Empty attributes
    print("\n3. Testing empty attributes...")
    url = f"{CA_API_BASE}/user/private-key/generate"
    data = {
        'user_id': 'empty_attr_user',
        'password': 'EmptyAttr123@',
        'attributes': []
    }
    response = requests.post(url, json=data)
    print(f"Empty attributes: {response.status_code}")

def test_abe_system_already_setup():
    """Test ABE system setup when already exists"""
    print("\n🔧 Testing ABE Setup When Already Exists...")
    
    url = f"{CA_API_BASE}/setup"
    response = requests.post(url)
    print_response("ABE Setup (Already Exists)", response)
    
    if response.status_code in [200, 201]:
        data = response.json()
        if data.get('already_exists'):
            print("✅ System correctly detected existing keys")
        else:
            print("⚠️  System created new keys (may not be intended)")

def test_performance_multiple_requests():
    """Test system performance with multiple concurrent-like requests"""
    print("\n⚡ Testing Multiple Requests Performance...")
    
    import time
    
    url = f"{CA_API_BASE}/user/private-key/check"
    user_ids = ['test_user_001', 'doctor_001', 'nurse_001', 'admin_001']
    
    start_time = time.time()
    
    for user_id in user_ids:
        response = requests.get(url, params={'user_id': user_id})
        print(f"Check {user_id}: {response.status_code}")
    
    end_time = time.time()
    print(f"Total time for {len(user_ids)} requests: {end_time - start_time:.2f} seconds")

def main():
    """Run additional tests"""
    print("🧪 Running Additional Tests for Encrypted Private Key System")
    print("=" * 70)
    
    try:
        # Test 1: ABE system already setup
        test_abe_system_already_setup()
        
        # Test 2: Duplicate key generation
        test_duplicate_key_generation()
        
        # Test 3: Multiple users
        test_multiple_users()
        
        # Test 4: Authentication for all users
        test_authentication_all_users()
        
        # Test 5: System resilience
        test_system_resilience()
        
        # Test 6: Performance
        test_performance_multiple_requests()
        
        print("\n🎯 Additional Tests Completed!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure the Flask app is running on http://localhost:5000")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    main()
