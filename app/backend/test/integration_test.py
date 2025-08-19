"""
Test script để kiểm tra các module mới của backend
"""
import requests
import json
import os
import time

# Configuration
BASE_URL = "http://localhost:5000"
TEST_FILE_PATH = "test_document.txt"

def create_test_file():
    """Tạo file test"""
    content = """
    Đây là file test cho hệ thống Cloud Firestore Crypto Access.
    
    File này chứa thông tin mẫu để test:
    - Encryption với CP-ABE
    - Access control với ABAC
    - File sharing workflow
    
    Thời gian tạo: {time}
    """.format(time=time.strftime("%Y-%m-%d %H:%M:%S"))
    
    with open(TEST_FILE_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Created test file: {TEST_FILE_PATH}")

def test_health_checks():
    """Test health checks của các services"""
    print("\n🏥 Testing Health Checks...")
    
    endpoints = [
        "/auth/health",
        "/abac/health", 
        "/ca/health",
        "/files/health",
        "/abe/health"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}")
            if response.status_code == 200:
                print(f"✅ {endpoint}: OK")
            else:
                print(f"❌ {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint}: Error - {e}")

def test_abe_setup():
    """Test ABE system setup"""
    print("\n🔐 Testing ABE System Setup...")
    
    try:
        # Check current status
        response = requests.get(f"{BASE_URL}/ca/status")
        status_data = response.json()
        print(f"Current status: {status_data}")
        
        if not status_data.get('status', {}).get('abe_system_setup', False):
            print("Setting up ABE system...")
            response = requests.post(f"{BASE_URL}/ca/setup")
            if response.status_code == 201:
                setup_data = response.json()
                print(f"✅ ABE setup successful: {setup_data['setup_id']}")
                return True
            else:
                print(f"❌ ABE setup failed: {response.text}")
                return False
        else:
            print("✅ ABE system already setup")
            return True
            
    except Exception as e:
        print(f"❌ ABE setup error: {e}")
        return False

def test_user_registration():
    """Test user registration và setup"""
    print("\n👤 Testing User Registration...")
    
    user_data = {
        "username": f"testdoctor_{int(time.time())}",
        "email": f"testdoctor_{int(time.time())}@hospital.com",
        "password": "SecurePass123!"
    }
    
    try:
        # Register user
        response = requests.post(f"{BASE_URL}/auth/register", json=user_data)
        if response.status_code == 201:
            register_data = response.json()
            user_id = register_data['user']['id']
            print(f"✅ User registered: {user_id}")
            
            # Set user attributes
            attributes = {
                "role": "doctor",
                "department": "cardiology",
                "clearance_level": "high",
                "specialty": "heart_surgery"
            }
            
            response = requests.post(f"{BASE_URL}/abac/users/{user_id}/attributes", json=attributes)
            if response.status_code == 201:
                print("✅ User attributes set")
            else:
                print(f"❌ Failed to set attributes: {response.text}")
            
            # Generate private key
            key_attributes = ["DOCTOR", "CARDIOLOGY", "HIGH"]
            response = requests.post(f"{BASE_URL}/ca/users/{user_id}/private-key", 
                                   json={"attributes": key_attributes})
            if response.status_code == 201:
                print("✅ Private key generated")
            else:
                print(f"❌ Failed to generate private key: {response.text}")
            
            return user_id
            
        else:
            print(f"❌ User registration failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ User registration error: {e}")
        return None

def test_policies_setup():
    """Test setup example policies"""
    print("\n📋 Testing Policies Setup...")
    
    try:
        response = requests.post(f"{BASE_URL}/abac/setup-example-policies")
        if response.status_code == 200:
            policies_data = response.json()
            print(f"✅ Created {len(policies_data['created_policies'])} policies")
            print(f"Policies: {policies_data['created_policies']}")
            return True
        else:
            print(f"❌ Failed to setup policies: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Policies setup error: {e}")
        return False

def test_file_upload_download(user_id):
    """Test file upload và download"""
    print("\n📁 Testing File Upload/Download...")
    
    if not user_id:
        print("❌ No user ID provided")
        return None
    
    try:
        # Upload file
        with open(TEST_FILE_PATH, 'rb') as f:
            files = {'file': f}
            data = {
                'owner_id': user_id,
                'access_policy': '(DOCTOR AND CARDIOLOGY)',
                'metadata': json.dumps({
                    'type': 'medical_record',
                    'department': 'cardiology',
                    'sensitivity': 'high'
                })
            }
            
            response = requests.post(f"{BASE_URL}/files/upload", files=files, data=data)
            
        if response.status_code == 201:
            upload_data = response.json()
            file_id = upload_data['file_id']
            print(f"✅ File uploaded: {file_id}")
            
            # Get file info
            response = requests.get(f"{BASE_URL}/files/{file_id}?user_id={user_id}")
            if response.status_code == 200:
                file_info = response.json()
                print(f"✅ File info retrieved: {file_info['file_info']['filename']}")
            
            # Download file
            response = requests.get(f"{BASE_URL}/files/{file_id}/download?user_id={user_id}")
            if response.status_code == 200:
                downloaded_filename = f"downloaded_{file_id}.txt"
                with open(downloaded_filename, 'wb') as f:
                    f.write(response.content)
                print(f"✅ File downloaded: {downloaded_filename}")
                
                # Verify content
                with open(downloaded_filename, 'r', encoding='utf-8') as f:
                    downloaded_content = f.read()
                with open(TEST_FILE_PATH, 'r', encoding='utf-8') as f:
                    original_content = f.read()
                
                if downloaded_content.strip() == original_content.strip():
                    print("✅ File content verified - encryption/decryption successful!")
                else:
                    print("❌ File content mismatch")
                
                # Cleanup
                os.remove(downloaded_filename)
            else:
                print(f"❌ File download failed: {response.text}")
                
            return file_id
            
        else:
            print(f"❌ File upload failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ File upload/download error: {e}")
        return None

def test_access_control(user_id, file_id):
    """Test access control"""
    print("\n🔒 Testing Access Control...")
    
    if not user_id or not file_id:
        print("❌ Missing user_id or file_id")
        return
    
    try:
        # Test authorized access
        access_request = {
            "user_id": user_id,
            "resource": "files",
            "action": "read",
            "resource_attributes": {
                "file_id": file_id,
                "file_type": "medical_record",
                "sensitivity": "high"
            }
        }
        
        response = requests.post(f"{BASE_URL}/abac/check-access", json=access_request)
        if response.status_code == 200:
            access_data = response.json()
            if access_data['access_granted']:
                print("✅ Authorized access granted")
            else:
                print(f"❌ Access denied: {access_data['reason']}")
        else:
            print(f"❌ Access check failed: {response.text}")
            
        # Test unauthorized user (create a different user type)
        unauthorized_user_data = {
            "username": f"testpatient_{int(time.time())}",
            "email": f"testpatient_{int(time.time())}@hospital.com",
            "password": "SecurePass123!"
        }
        
        response = requests.post(f"{BASE_URL}/auth/register", json=unauthorized_user_data)
        if response.status_code == 201:
            unauth_user_id = response.json()['user']['id']
            
            # Set different attributes
            attributes = {
                "role": "patient",
                "department": "general",
                "clearance_level": "low"
            }
            
            requests.post(f"{BASE_URL}/abac/users/{unauth_user_id}/attributes", json=attributes)
            
            # Test access
            access_request['user_id'] = unauth_user_id
            response = requests.post(f"{BASE_URL}/abac/check-access", json=access_request)
            
            if response.status_code == 200:
                access_data = response.json()
                if not access_data['access_granted']:
                    print("✅ Unauthorized access correctly denied")
                else:
                    print("❌ Unauthorized access was granted!")
            
    except Exception as e:
        print(f"❌ Access control test error: {e}")

def test_list_files(user_id):
    """Test list files"""
    print("\n📋 Testing List Files...")
    
    if not user_id:
        print("❌ No user ID provided")
        return
    
    try:
        response = requests.get(f"{BASE_URL}/files/?user_id={user_id}")
        if response.status_code == 200:
            files_data = response.json()
            print(f"✅ Listed {files_data['total_count']} files")
            
            for file_info in files_data['files']:
                print(f"  - {file_info['filename']} (Owner: {file_info.get('is_owner', False)})")
        else:
            print(f"❌ List files failed: {response.text}")
            
    except Exception as e:
        print(f"❌ List files error: {e}")

def cleanup():
    """Cleanup test files"""
    try:
        if os.path.exists(TEST_FILE_PATH):
            os.remove(TEST_FILE_PATH)
            print(f"🧹 Cleaned up: {TEST_FILE_PATH}")
    except Exception as e:
        print(f"❌ Cleanup error: {e}")

def main():
    """Main test function"""
    print("🚀 Starting Backend Integration Tests...")
    print("=" * 50)
    
    # Create test file
    create_test_file()
    
    # Test health checks
    test_health_checks()
    
    # Test ABE setup
    abe_setup_success = test_abe_setup()
    if not abe_setup_success:
        print("❌ ABE setup failed, stopping tests")
        cleanup()
        return
    
    # Test policies setup
    test_policies_setup()
    
    # Test user registration
    user_id = test_user_registration()
    if not user_id:
        print("❌ User registration failed, stopping tests")
        cleanup()
        return
    
    # Test file operations
    file_id = test_file_upload_download(user_id)
    
    # Test access control
    test_access_control(user_id, file_id)
    
    # Test list files
    test_list_files(user_id)
    
    # Cleanup
    cleanup()
    
    print("\n" + "=" * 50)
    print("🎉 Integration tests completed!")
    print("\nNext steps:")
    print("1. Check server logs for any errors")
    print("2. Verify Firestore collections have data")
    print("3. Test với frontend hoặc Postman")

if __name__ == "__main__":
    main()
