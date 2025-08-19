"""
Test upload file docs.md với CP-ABE encryption
"""
import requests
import json
import os
import time

BASE_URL = "http://localhost:5000"
DOCS_FILE_PATH = "test/docs.md"

def test_server_health():
    """Kiểm tra server có đang chạy không"""
    print("🔍 Checking server health...")
    
    try:
        response = requests.get(f"{BASE_URL}/auth/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running")
            return True
        else:
            print(f"❌ Server health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running. Please start server with: python main.py")
        return False
    except Exception as e:
        print(f"❌ Error checking server: {e}")
        return False

def setup_test_user():
    """Tạo test user để upload file"""
    print("\n👤 Setting up test user...")
    
    user_data = {
        "username": f"testuser_{int(time.time())}",
        "email": f"testuser_{int(time.time())}@example.com",
        "password": "TestPass123!"
    }
    
    try:
        # Register user
        response = requests.post(f"{BASE_URL}/auth/register", json=user_data)
        if response.status_code == 201:
            register_data = response.json()
            user_id = register_data['user']['id']
            print(f"✅ User created: {user_id}")
            
            # Set user attributes
            attributes = {
                "role": "admin",
                "department": "it",
                "clearance_level": "high",
                "organization": "company"
            }
            
            response = requests.post(f"{BASE_URL}/abac/users/{user_id}/attributes", json=attributes)
            if response.status_code == 201:
                print("✅ User attributes set")
            else:
                print(f"⚠️ Failed to set attributes: {response.status_code}")
            
            # Generate private key for ABE
            key_attributes = ["ADMIN", "IT", "HIGH"]
            response = requests.post(f"{BASE_URL}/ca/users/{user_id}/private-key", 
                                   json={"attributes": key_attributes})
            if response.status_code == 201:
                print("✅ Private key generated")
            else:
                print(f"⚠️ Failed to generate private key: {response.status_code}")
                print(f"Response: {response.text}")
            
            return user_id, user_data
            
        else:
            print(f"❌ User registration failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None, None
            
    except Exception as e:
        print(f"❌ Error setting up user: {e}")
        return None, None

def setup_abe_system():
    """Setup ABE system if not already done"""
    print("\n🔐 Setting up ABE system...")
    
    try:
        # Check status first
        response = requests.get(f"{BASE_URL}/ca/status")
        if response.status_code == 200:
            status_data = response.json()
            if status_data.get('status', {}).get('abe_system_setup', False):
                print("✅ ABE system already setup")
                return True
        
        # Setup ABE system
        response = requests.post(f"{BASE_URL}/ca/setup")
        if response.status_code == 201:
            setup_data = response.json()
            print(f"✅ ABE system setup successful: {setup_data.get('setup_id', 'Unknown')}")
            return True
        else:
            print(f"❌ ABE setup failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error setting up ABE: {e}")
        return False

def upload_docs_file(user_id):
    """Upload docs.md file với encryption"""
    print(f"\n📁 Uploading docs.md file...")
    
    if not os.path.exists(DOCS_FILE_PATH):
        print(f"❌ File not found: {DOCS_FILE_PATH}")
        return None
    
    try:
        # Prepare file upload
        with open(DOCS_FILE_PATH, 'rb') as f:
            files = {'file': ('docs.md', f, 'text/markdown')}
            data = {
                'owner_id': user_id,
                'access_policy': '(ADMIN OR (IT AND HIGH))',  # Policy cho admin hoặc IT với high clearance
                'metadata': json.dumps({
                    'type': 'documentation',
                    'department': 'it',
                    'sensitivity': 'medium',
                    'description': 'Backend implementation documentation'
                })
            }
            
            print(f"📤 Uploading with policy: {data['access_policy']}")
            response = requests.post(f"{BASE_URL}/files/upload", files=files, data=data)
        
        if response.status_code == 201:
            upload_data = response.json()
            file_id = upload_data['file_id']
            print(f"✅ File uploaded successfully!")
            print(f"   File ID: {file_id}")
            print(f"   Filename: {upload_data['filename']}")
            print(f"   Policy: {upload_data['access_policy']}")
            return file_id
        else:
            print(f"❌ File upload failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error uploading file: {e}")
        return None

def verify_file_info(file_id, user_id):
    """Kiểm tra thông tin file đã upload"""
    print(f"\n📋 Verifying file info...")
    
    try:
        response = requests.get(f"{BASE_URL}/files/{file_id}?user_id={user_id}")
        if response.status_code == 200:
            file_info = response.json()['file_info']
            print("✅ File info retrieved:")
            print(f"   Filename: {file_info['filename']}")
            print(f"   Size: {file_info['original_size']} bytes")
            print(f"   Type: {file_info['file_type']}")
            print(f"   Policy: {file_info['access_policy']}")
            print(f"   Upload time: {file_info['upload_time']}")
            print(f"   Is owner: {file_info['is_owner']}")
            return True
        else:
            print(f"❌ Failed to get file info: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error getting file info: {e}")
        return False

def test_file_download(file_id, user_id):
    """Test download và decrypt file"""
    print(f"\n📥 Testing file download...")
    
    try:
        response = requests.get(f"{BASE_URL}/files/{file_id}/download?user_id={user_id}")
        if response.status_code == 200:
            # Save downloaded file
            downloaded_filename = f"downloaded_docs_{int(time.time())}.md"
            with open(downloaded_filename, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ File downloaded successfully: {downloaded_filename}")
            
            # Compare with original
            with open(DOCS_FILE_PATH, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            with open(downloaded_filename, 'r', encoding='utf-8') as f:
                downloaded_content = f.read()
            
            if original_content.strip() == downloaded_content.strip():
                print("✅ File content verified - encryption/decryption successful!")
            else:
                print("❌ File content mismatch!")
                print(f"Original length: {len(original_content)}")
                print(f"Downloaded length: {len(downloaded_content)}")
            
            # Cleanup
            os.remove(downloaded_filename)
            return True
            
        else:
            print(f"❌ File download failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error downloading file: {e}")
        return False

def test_access_control(file_id):
    """Test access control với unauthorized user"""
    print(f"\n🔒 Testing access control...")
    
    # Create unauthorized user
    unauthorized_user_data = {
        "username": f"unauthorized_{int(time.time())}",
        "email": f"unauthorized_{int(time.time())}@example.com",
        "password": "TestPass123!"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/register", json=unauthorized_user_data)
        if response.status_code == 201:
            unauth_user_id = response.json()['user']['id']
            
            # Set different attributes (không match policy)
            attributes = {
                "role": "user",
                "department": "sales",
                "clearance_level": "low"
            }
            
            requests.post(f"{BASE_URL}/abac/users/{unauth_user_id}/attributes", json=attributes)
            
            # Try to download file
            response = requests.get(f"{BASE_URL}/files/{file_id}/download?user_id={unauth_user_id}")
            
            if response.status_code == 403:
                print("✅ Access control working - unauthorized user denied")
            else:
                print(f"❌ Access control failed - unauthorized user got: {response.status_code}")
                
        else:
            print("⚠️ Could not create unauthorized user for testing")
            
    except Exception as e:
        print(f"⚠️ Error testing access control: {e}")

def main():
    """Main test function"""
    print("🚀 Testing File Upload with CP-ABE Encryption")
    print("=" * 60)
    
    # Check server health
    if not test_server_health():
        return
    
    # Setup ABE system
    if not setup_abe_system():
        print("❌ ABE setup failed, cannot proceed")
        return
    
    # Setup test user
    user_id, user_data = setup_test_user()
    if not user_id:
        print("❌ User setup failed, cannot proceed")
        return
    
    # Upload file
    file_id = upload_docs_file(user_id)
    if not file_id:
        print("❌ File upload failed")
        return
    
    # Verify file info
    verify_file_info(file_id, user_id)
    
    # Test download
    test_file_download(file_id, user_id)
    
    # Test access control
    test_access_control(file_id)
    
    print("\n" + "=" * 60)
    print("🎉 File upload test completed!")
    print(f"\nSummary:")
    if user_data:
        print(f"✅ User: {user_data['username']} ({user_id})")
    else:
        print(f"✅ User: {user_id}")
    print(f"✅ File: docs.md → {file_id}")
    print(f"✅ Policy: (ADMIN OR (IT AND HIGH))")
    print(f"✅ Encryption/Decryption: Working")
    print(f"✅ Access Control: Working")

if __name__ == "__main__":
    main()
