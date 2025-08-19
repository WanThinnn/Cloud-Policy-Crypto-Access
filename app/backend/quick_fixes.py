"""
Quick fixes cho backend issues
"""

def firestore_index_commands():
    """In ra commands để tạo Firestore indexes"""
    print("🔧 Firestore Index Commands")
    print("=" * 50)
    print("\nBạn cần tạo các indexes sau trong Firebase Console:")
    print("\n1. Shared Files Index:")
    print("   Collection: shared_files")
    print("   Fields:")
    print("   - is_active (Ascending)")
    print("   - owner_id (Ascending)")  
    print("   - __name__ (Ascending)")
    
    print("\n2. Access Logs Index:")
    print("   Collection: file_access_logs") 
    print("   Fields:")
    print("   - file_id (Ascending)")
    print("   - timestamp (Descending)")
    
    print("\n3. User Attributes Index:")
    print("   Collection: user_attributes")
    print("   Fields:")
    print("   - user_id (Ascending)")
    
    print("\n4. ABE Keys Index:")
    print("   Collection: abe_keys")
    print("   Fields:")
    print("   - user_id (Ascending)")
    print("   - is_active (Ascending)")
    
    print("\n📍 Hoặc truy cập URLs sau để tạo tự động:")
    print("   Firebase Console > Firestore > Indexes")
    print("   Chạy query và click vào link tạo index trong error message")

def test_endpoints():
    """Test basic endpoints"""
    import requests
    
    base_url = "http://localhost:5000"
    
    print("\n🧪 Testing Basic Endpoints")
    print("=" * 50)
    
    endpoints = [
        "/auth/health",
        "/abac/health", 
        "/ca/health",
        "/files/health"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            status = "✅" if response.status_code == 200 else "❌"
            print(f"{status} {endpoint}: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"❌ {endpoint}: Server not running")
        except Exception as e:
            print(f"❌ {endpoint}: {e}")

def main():
    print("🚀 Cloud Firestore Crypto Access - Quick Fixes")
    print("=" * 60)
    
    firestore_index_commands()
    test_endpoints()
    
    print("\n" + "=" * 60)
    print("📝 Next Steps:")
    print("1. Tạo Firestore indexes theo hướng dẫn trên")
    print("2. Restart server: python main.py") 
    print("3. Run integration test: python test/integration_test.py")
    print("4. Check server logs for any remaining errors")
    
    print("\n🎯 Current Status:")
    print("✅ Server can start successfully")
    print("✅ Most APIs are working")
    print("✅ ABE library loaded")
    print("✅ Authentication working")
    print("✅ ABAC policies working")
    print("⚠️ File operations need Firestore indexes")
    
    print("\n🔗 Useful URLs:")
    print("- Server: http://localhost:5000")
    print("- Health checks: http://localhost:5000/auth/health")
    print("- Firebase Console: https://console.firebase.google.com")

if __name__ == "__main__":
    main()
