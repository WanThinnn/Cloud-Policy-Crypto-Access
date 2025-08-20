"""
Test upload file với keys đã có sẵn
"""
import requests
import json
import time

BASE_URL = "http://localhost:5000"
DOCS_FILE_PATH = "test/docs.md"

def simple_upload_test():
    """Test upload file đơn giản"""
    print("🚀 Simple File Upload Test")
    print("=" * 50)
    
    # 1. Create user
    print("\n👤 Creating test user...")
    user_data = {
        "username": f"uploadtest_{int(time.time())}",
        "email": f"uploadtest_{int(time.time())}@example.com",
        "password": "TestPass123!"
    }
    
    response = requests.post(f"{BASE_URL}/auth/register", json=user_data)
    if response.status_code != 201:
        print(f"❌ User creation failed: {response.status_code}")
        print(response.text)
        return
    
    user_id = response.json()['user']['id']
    print(f"✅ User created: {user_id}")
    
    # 2. Set attributes
    print("\n🏷️ Setting user attributes...")
    attributes = {
        "role": "admin",
        "department": "it", 
        "clearance_level": "high"
    }
    
    response = requests.post(f"{BASE_URL}/abac/users/{user_id}/attributes", json=attributes)
    if response.status_code == 201:
        print("✅ Attributes set")
    else:
        print(f"⚠️ Attributes not set: {response.status_code}")
    
    # 3. Generate private key
    print("\n🔑 Generating private key...")
    key_attributes = ["ADMIN", "IT", "HIGH"]
    response = requests.post(f"{BASE_URL}/ca/users/{user_id}/private-key", 
                           json={"attributes": key_attributes})
    if response.status_code == 201:
        print("✅ Private key generated")
    else:
        print(f"⚠️ Private key generation failed: {response.status_code}")
        print(response.text)
    
    # 4. Check active keys
    print("\n🔍 Checking active keys...")
    response = requests.get(f"{BASE_URL}/ca/keys/active")
    if response.status_code == 200:
        keys_info = response.json()
        print(f"✅ Keys available: public={keys_info.get('has_public_key')}, master={keys_info.get('has_master_key')}")
    else:
        print(f"❌ Keys check failed: {response.status_code}")
        print(response.text)
        return
    
    # 5. Upload file
    print("\n📁 Uploading file...")
    try:
        with open(DOCS_FILE_PATH, 'rb') as f:
            files = {'file': ('docs.md', f, 'text/markdown')}
            data = {
                'owner_id': user_id,
                'access_policy': '(ADMIN OR (IT AND HIGH))'
            }
            
            response = requests.post(f"{BASE_URL}/files/upload", files=files, data=data)
            
        if response.status_code == 201:
            upload_data = response.json()
            file_id = upload_data['file_id']
            print(f"✅ File uploaded: {file_id}")
            
            # 6. Test download
            print("\n📥 Testing download...")
            response = requests.get(f"{BASE_URL}/files/{file_id}/download?user_id={user_id}")
            if response.status_code == 200:
                print("✅ File downloaded and decrypted successfully!")
                
                # Save to verify
                with open("test_download.md", "wb") as f:
                    f.write(response.content)
                print("✅ Downloaded file saved as test_download.md")
                
            else:
                print(f"❌ Download failed: {response.status_code}")
                print(response.text)
                
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(response.text)
            
    except FileNotFoundError:
        print(f"❌ File not found: {DOCS_FILE_PATH}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    simple_upload_test()
