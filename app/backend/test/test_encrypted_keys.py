"""
Test script for encrypted private key management system
"""
import requests
import json
import base64
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Test configuration
BASE_URL = "http://localhost:5000"
CA_API_BASE = f"{BASE_URL}/ca"

# Test data
TEST_USER_ID = "test_user_001"
TEST_PASSWORD = "TestPass123@"
TEST_ATTRIBUTES = ["role:doctor", "department:cardiology", "clearance_level:high"]

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

def test_abe_system_setup():
    """Test ABE system setup"""
    print("\n🔧 Testing ABE System Setup...")
    
    url = f"{CA_API_BASE}/setup"
    response = requests.post(url)
    print_response("ABE System Setup", response)
    
    return response.status_code in [200, 201]

def test_check_active_keys():
    """Test getting active keys"""
    print("\n🔑 Testing Active Keys Check...")
    
    url = f"{CA_API_BASE}/keys/active"
    response = requests.get(url)
    print_response("Active Keys Check", response)
    
    return response.status_code == 200

def test_check_user_private_key(user_id):
    """Test checking if user has private key"""
    print(f"\n👤 Testing User Private Key Check for {user_id}...")
    
    url = f"{CA_API_BASE}/user/private-key/check"
    params = {'user_id': user_id}
    response = requests.get(url, params=params)
    print_response("User Private Key Check", response)
    
    if response.status_code == 200:
        data = response.json()
        return data.get('has_key', False)
    return False

def test_generate_encrypted_private_key():
    """Test generating encrypted private key"""
    print(f"\n🔐 Testing Encrypted Private Key Generation for {TEST_USER_ID}...")
    
    url = f"{CA_API_BASE}/user/private-key/generate"
    data = {
        'user_id': TEST_USER_ID,
        'password': TEST_PASSWORD,
        'attributes': TEST_ATTRIBUTES
    }
    
    response = requests.post(url, json=data)
    print_response("Generate Encrypted Private Key", response)
    
    return response.status_code in [200, 201]

def test_authenticate_private_key():
    """Test authenticating with password to get private key"""
    print(f"\n🔓 Testing Private Key Authentication for {TEST_USER_ID}...")
    
    url = f"{CA_API_BASE}/user/private-key/authenticate"
    data = {
        'user_id': TEST_USER_ID,
        'password': TEST_PASSWORD
    }
    
    response = requests.post(url, json=data)
    print_response("Authenticate Private Key", response)
    
    return response.status_code == 200

def test_authenticate_with_wrong_password():
    """Test authentication with wrong password"""
    print(f"\n❌ Testing Authentication with Wrong Password for {TEST_USER_ID}...")
    
    url = f"{CA_API_BASE}/user/private-key/authenticate"
    data = {
        'user_id': TEST_USER_ID,
        'password': "WrongPassword123@"
    }
    
    response = requests.post(url, json=data)
    print_response("Authenticate with Wrong Password", response)
    
    return response.status_code == 401  # Should be unauthorized

def test_password_strength():
    """Test password strength validation"""
    print("\n🔍 Testing Password Strength Validation...")
    
    weak_passwords = [
        "123",           # Too short
        "password",      # No uppercase, no digits, no special chars
        "Password",      # No digits, no special chars
        "Password123"    # No special chars
    ]
    
    for weak_password in weak_passwords:
        url = f"{CA_API_BASE}/user/private-key/generate"
        data = {
            'user_id': f"test_weak_{weak_password}",
            'password': weak_password,
            'attributes': TEST_ATTRIBUTES
        }
        
        response = requests.post(url, json=data)
        print(f"Testing weak password '{weak_password}': Status {response.status_code}")
        if response.status_code == 400:
            try:
                error_data = response.json()
                if 'password_errors' in error_data:
                    print(f"  Password errors: {error_data['password_errors']}")
            except:
                pass

def test_system_status():
    """Test system status"""
    print("\n📊 Testing System Status...")
    
    url = f"{CA_API_BASE}/status"
    response = requests.get(url)
    print_response("System Status", response)
    
    return response.status_code == 200

def main():
    """Run all tests"""
    print("🚀 Starting Encrypted Private Key Management System Tests")
    print("=" * 60)
    
    try:
        # Test 1: Check system status
        test_system_status()
        
        # Test 2: Setup ABE system (if needed)
        test_abe_system_setup()
        
        # Test 3: Check active keys
        test_check_active_keys()
        
        # Test 4: Check if user has private key (should be False initially)
        has_key_before = test_check_user_private_key(TEST_USER_ID)
        print(f"User has key before generation: {has_key_before}")
        
        # Test 5: Test password strength validation
        test_password_strength()
        
        # Test 6: Generate encrypted private key
        if not has_key_before:
            success = test_generate_encrypted_private_key()
            if success:
                print("✅ Private key generation successful")
            else:
                print("❌ Private key generation failed")
                return
        else:
            print("⚠️  User already has a private key, skipping generation")
        
        # Test 7: Check if user has private key (should be True now)
        has_key_after = test_check_user_private_key(TEST_USER_ID)
        print(f"User has key after generation: {has_key_after}")
        
        # Test 8: Authenticate with correct password
        success = test_authenticate_private_key()
        if success:
            print("✅ Private key authentication successful")
        else:
            print("❌ Private key authentication failed")
        
        # Test 9: Authenticate with wrong password
        success = test_authenticate_with_wrong_password()
        if success:
            print("✅ Wrong password correctly rejected")
        else:
            print("❌ Wrong password test failed")
        
        print("\n🎉 All tests completed!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure the Flask app is running on http://localhost:5000")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    main()
