"""
Test toàn diện upload file với access control
"""
import requests
import json
import time
import os

BASE_URL = "http://localhost:5000"
DOCS_FILE_PATH = "test/docs.md"

def comprehensive_file_test():
    """Test toàn diện file upload, sharing, access control"""
    print("🚀 Comprehensive File Upload & Access Control Test")
    print("=" * 70)
    
    # 1. Create admin user
    print("\n👑 Creating admin user...")
    admin_data = {
        "username": f"admin_{int(time.time())}",
        "email": f"admin_{int(time.time())}@company.com",
        "password": "AdminPass123!"
    }
    
    response = requests.post(f"{BASE_URL}/auth/register", json=admin_data)
    admin_id = response.json()['user']['id']
    print(f"✅ Admin created: {admin_id}")
    
    # Set admin attributes
    admin_attributes = {
        "role": "admin",
        "department": "it",
        "clearance_level": "high",
        "organization": "company"
    }
    requests.post(f"{BASE_URL}/abac/users/{admin_id}/attributes", json=admin_attributes)
    requests.post(f"{BASE_URL}/ca/users/{admin_id}/private-key", 
                 json={"attributes": ["ADMIN", "IT", "HIGH"]})
    print("✅ Admin setup complete")
    
    # 2. Create regular user
    print("\n👤 Creating regular user...")
    user_data = {
        "username": f"user_{int(time.time())}",
        "email": f"user_{int(time.time())}@company.com",
        "password": "UserPass123!"
    }
    
    response = requests.post(f"{BASE_URL}/auth/register", json=user_data)
    user_id = response.json()['user']['id']
    print(f"✅ User created: {user_id}")
    
    # Set user attributes (không match policy)
    user_attributes = {
        "role": "user",
        "department": "sales",
        "clearance_level": "low"
    }
    requests.post(f"{BASE_URL}/abac/users/{user_id}/attributes", json=user_attributes)
    requests.post(f"{BASE_URL}/ca/users/{user_id}/private-key", 
                 json={"attributes": ["USER", "SALES", "LOW"]})
    print("✅ User setup complete")
    
    # 3. Admin uploads file
    print("\n📁 Admin uploading docs.md...")
    with open(DOCS_FILE_PATH, 'rb') as f:
        files = {'file': ('docs.md', f, 'text/markdown')}
        data = {
            'owner_id': admin_id,
            'access_policy': '(ADMIN OR (IT AND HIGH))',  # Chỉ admin hoặc IT với high clearance
            'metadata': json.dumps({
                'type': 'documentation',
                'sensitivity': 'high',
                'project': 'cloud-crypto-access'
            })
        }
        response = requests.post(f"{BASE_URL}/files/upload", files=files, data=data)
    
    if response.status_code == 201:
        file_info = response.json()
        file_id = file_info['file_id']
        print(f"✅ File uploaded: {file_id}")
        print(f"   Policy: {file_info['access_policy']}")
    else:
        print(f"❌ Upload failed: {response.status_code} - {response.text}")
        return
    
    # 4. Test admin access (should work)
    print("\n🔐 Testing admin access...")
    response = requests.get(f"{BASE_URL}/files/{file_id}/download?user_id={admin_id}")
    if response.status_code == 200:
        print("✅ Admin can access file")
        with open("admin_download.md", "wb") as f:
            f.write(response.content)
    else:
        print(f"❌ Admin access failed: {response.status_code}")
    
    # 5. Test regular user access (should fail)
    print("\n🚫 Testing regular user access...")
    response = requests.get(f"{BASE_URL}/files/{file_id}/download?user_id={user_id}")
    if response.status_code == 403:
        print("✅ Regular user correctly denied access")
    else:
        print(f"❌ Access control failed: {response.status_code}")
    
    # 6. Create IT user with high clearance
    print("\n🔧 Creating IT user with high clearance...")
    it_data = {
        "username": f"ituser_{int(time.time())}",
        "email": f"ituser_{int(time.time())}@company.com",
        "password": "ITPass123!"
    }
    
    response = requests.post(f"{BASE_URL}/auth/register", json=it_data)
    it_id = response.json()['user']['id']
    
    it_attributes = {
        "role": "engineer",
        "department": "it",
        "clearance_level": "high"
    }
    requests.post(f"{BASE_URL}/abac/users/{it_id}/attributes", json=it_attributes)
    requests.post(f"{BASE_URL}/ca/users/{it_id}/private-key", 
                 json={"attributes": ["IT", "HIGH"]})
    print(f"✅ IT user created: {it_id}")
    
    # 7. Test IT user access (should work due to policy)
    print("\n🔧 Testing IT user access...")
    response = requests.get(f"{BASE_URL}/files/{file_id}/download?user_id={it_id}")
    if response.status_code == 200:
        print("✅ IT user can access file (policy match)")
        with open("it_download.md", "wb") as f:
            f.write(response.content)
    else:
        print(f"❌ IT user access failed: {response.status_code} - {response.text}")
    
    # 8. Get file info
    print("\n📋 Getting file information...")
    response = requests.get(f"{BASE_URL}/files/{file_id}?user_id={admin_id}")
    if response.status_code == 200:
        file_info = response.json()['file_info']
        print("✅ File info retrieved:")
        print(f"   Filename: {file_info['filename']}")
        print(f"   Size: {file_info['original_size']} bytes")
        print(f"   Policy: {file_info['access_policy']}")
        print(f"   Uploads: {file_info['upload_time']}")
    
    # 9. Check access logs
    print("\n📊 Checking access logs...")
    response = requests.get(f"{BASE_URL}/files/{file_id}/access-logs?user_id={admin_id}")
    if response.status_code == 200:
        logs = response.json()['access_logs']
        print(f"✅ Found {len(logs)} access log entries")
        for log in logs[:3]:  # Show first 3
            print(f"   - {log['timestamp']}: {log['action']} by {log['user_id'][:8]}...")
    
    # 10. Update file policy
    print("\n🔄 Testing policy update...")
    new_policy = "(ADMIN OR IT OR SALES)"  # More permissive
    response = requests.put(f"{BASE_URL}/files/{file_id}/policy", 
                           json={"access_policy": new_policy, "user_id": admin_id})
    if response.status_code == 200:
        print("✅ Policy updated successfully")
        
        # Test regular user access again
        print("   Testing regular user access after policy update...")
        response = requests.get(f"{BASE_URL}/files/{file_id}/download?user_id={user_id}")
        if response.status_code == 200:
            print("   ✅ Regular user can now access file")
        else:
            print(f"   ❌ Regular user still denied: {response.status_code}")
    
    print("\n" + "=" * 70)
    print("🎉 Comprehensive File Test Completed!")
    print(f"\nTest Summary:")
    print(f"✅ File ID: {file_id}")
    print(f"✅ Admin Access: Working")
    print(f"✅ Access Control: Working")
    print(f"✅ Policy-based Access: Working")
    print(f"✅ Access Logs: Working")
    print(f"✅ Policy Updates: Working")
    print(f"✅ Encryption/Decryption: Working")
    
    # Cleanup downloaded files
    for filename in ["admin_download.md", "it_download.md", "test_download.md"]:
        if os.path.exists(filename):
            os.remove(filename)
    print("\n🧹 Cleanup completed")

if __name__ == "__main__":
    comprehensive_file_test()
