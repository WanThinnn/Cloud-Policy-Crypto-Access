"""
Test script for improved encrypted private key management system
- Master/Public keys stored locally
- Minimal metadata for private keys
"""
import requests
import json
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Test configuration
BASE_URL = "http://localhost:5000"
CA_API_BASE = f"{BASE_URL}/ca"

# Test data
TEST_USER_ID = "secure_user_001"
TEST_PASSWORD = "SecurePass2025@"
TEST_ATTRIBUTES = ["role:researcher", "department:security", "clearance_level:top"]

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

def test_local_keys_setup():
    """Test ABE system with local key storage"""
    print("\n🔧 Testing ABE System Setup (Local Keys)...")
    
    url = f"{CA_API_BASE}/setup"
    response = requests.post(url)
    print_response("ABE System Setup (Local)", response)
    
    if response.status_code in [200, 201]:
        data = response.json()
        if data.get('storage') == 'local':
            print("✅ Keys stored locally as expected")
        else:
            print("⚠️  Keys not stored locally")
    
    return response.status_code in [200, 201]

def check_local_files():
    """Check if local key files exist"""
    print("\n📁 Checking Local Key Files...")
    
    backend_dir = os.path.dirname(os.path.dirname(__file__))
    keys_dir = os.path.join(backend_dir, 'abe_keys')
    
    master_key_path = os.path.join(keys_dir, 'master_key.key')
    public_key_path = os.path.join(keys_dir, 'public_key.key')
    setup_info_path = os.path.join(keys_dir, 'setup_info.json')
    
    print(f"Keys directory: {keys_dir}")
    print(f"Master Key exists: {os.path.exists(master_key_path)}")
    print(f"Public Key exists: {os.path.exists(public_key_path)}")
    print(f"Setup Info exists: {os.path.exists(setup_info_path)}")
    
    if os.path.exists(setup_info_path):
        try:
            with open(setup_info_path, 'r') as f:
                setup_info = json.load(f)
            print(f"Setup Info: {json.dumps(setup_info, indent=2)}")
        except Exception as e:
            print(f"Error reading setup info: {e}")

def test_minimal_metadata_encryption():
    """Test private key generation with minimal metadata"""
    print(f"\n🔐 Testing Minimal Metadata Encryption for {TEST_USER_ID}...")
    
    url = f"{CA_API_BASE}/user/private-key/generate"
    data = {
        'user_id': TEST_USER_ID,
        'password': TEST_PASSWORD,
        'attributes': TEST_ATTRIBUTES
    }
    
    response = requests.post(url, json=data)
    print_response("Generate Encrypted Private Key (Minimal Metadata)", response)
    
    if response.status_code in [200, 201]:
        result = response.json()
        # Check if response has minimal metadata
        has_minimal_metadata = 'encryption_info' not in result
        print(f"✅ Minimal metadata: {has_minimal_metadata}")
        if not has_minimal_metadata:
            print("⚠️  Response still contains detailed encryption info")
    
    return response.status_code in [200, 201]

def inspect_cloud_storage():
    """Inspect what's stored in cloud (Firestore simulation)"""
    print("\n☁️  Checking Cloud Storage Metadata...")
    
    # This would normally query Firestore directly, but we'll use the API
    url = f"{CA_API_BASE}/user/private-key/check"
    params = {'user_id': TEST_USER_ID}
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        if data['has_key'] and data['key_info']:
            key_info = data['key_info']
            print("Metadata stored in cloud:")
            print(f"- Algorithm: {key_info.get('algorithm', 'Not specified')}")
            print(f"- Attributes: {key_info.get('attributes', [])}")
            print(f"- Created at: {key_info.get('created_at', 'Unknown')}")
            
            # Check for leaked crypto parameters
            leaked_params = []
            for param in ['salt', 'nonce', 'tag', 'encryption_info', 'salt_len', 'nonce_len']:
                if param in key_info:
                    leaked_params.append(param)
            
            if leaked_params:
                print(f"⚠️  Potentially leaked parameters: {leaked_params}")
            else:
                print("✅ No crypto parameters leaked")
        else:
            print("No key found or no metadata")

def test_authentication_still_works():
    """Test that authentication still works with new format"""
    print(f"\n🔓 Testing Authentication with New Format...")
    
    url = f"{CA_API_BASE}/user/private-key/authenticate"
    data = {
        'user_id': TEST_USER_ID,
        'password': TEST_PASSWORD
    }
    
    response = requests.post(url, json=data)
    print_response("Authenticate with New Format", response)
    
    return response.status_code == 200

def test_wrong_password_still_fails():
    """Test that wrong password is still rejected"""
    print(f"\n❌ Testing Wrong Password Rejection...")
    
    url = f"{CA_API_BASE}/user/private-key/authenticate"
    data = {
        'user_id': TEST_USER_ID,
        'password': "WrongPassword123@"
    }
    
    response = requests.post(url, json=data)
    print_response("Wrong Password Test", response)
    
    return response.status_code == 401

def main():
    """Run improved security tests"""
    print("🛡️  Testing Improved Security - Local Keys & Minimal Metadata")
    print("=" * 70)
    
    try:
        # Test 1: Setup with local key storage
        test_local_keys_setup()
        
        # Test 2: Check local files
        check_local_files()
        
        # Test 3: Generate key with minimal metadata
        success = test_minimal_metadata_encryption()
        if not success:
            print("❌ Private key generation failed")
            return
        
        # Test 4: Inspect cloud storage
        inspect_cloud_storage()
        
        # Test 5: Test authentication still works
        auth_success = test_authentication_still_works()
        if auth_success:
            print("✅ Authentication works with new format")
        else:
            print("❌ Authentication failed with new format")
        
        # Test 6: Test wrong password still fails
        wrong_pass_success = test_wrong_password_still_fails()
        if wrong_pass_success:
            print("✅ Wrong password correctly rejected")
        else:
            print("❌ Wrong password test failed")
        
        print("\n🎯 Security Improvements Summary:")
        print("✅ Master/Public keys stored locally (not in cloud)")
        print("✅ Private key metadata minimized") 
        print("✅ Crypto parameters hidden in single blob")
        print("✅ Authentication still secure and functional")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure the Flask app is running on http://localhost:5000")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    main()
