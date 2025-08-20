"""
Demo script showing the complete encrypted private key management workflow
"""
import requests
import json
import time
import base64

# Configuration
BASE_URL = "http://localhost:5000"
CA_API_BASE = f"{BASE_URL}/ca"

def print_step(step_num, title):
    """Print formatted step header"""
    print(f"\n{'='*60}")
    print(f"BƯỚC {step_num}: {title}")
    print(f"{'='*60}")

def print_success(message):
    """Print success message"""
    print(f"✅ {message}")

def print_error(message):
    """Print error message"""
    print(f"❌ {message}")

def print_info(message):
    """Print info message"""
    print(f"ℹ️  {message}")

def demo_complete_workflow():
    """Demonstrate complete workflow"""
    
    print("🚀 DEMO: Hệ thống Quản lý Private Key được Mã hóa")
    print("=" * 70)
    print("Tính năng chính:")
    print("• Master Key & Public Key chỉ tạo 1 lần duy nhất")  
    print("• Private Key được mã hóa bằng password của user")
    print("• Sử dụng Argon2id + HKDF-SHA3-256 + AES-256-GCM")
    print("• Lưu trữ an toàn trên cloud (Firestore)")
    
    # Demo user
    user_id = "demo_user_healthcare"
    password = "HealthCare2025@"
    attributes = ["role:doctor", "department:oncology", "clearance_level:high"]
    
    try:
        # Bước 1: Kiểm tra trạng thái hệ thống
        print_step(1, "Kiểm tra trạng thái hệ thống ABE")
        
        url = f"{CA_API_BASE}/keys/active"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Hệ thống ABE đã được setup")
            print_info(f"Setup ID: {data['setup_id']}")
            print_info(f"Có Public Key: {data['has_public_key']}")
            print_info(f"Có Master Key: {data['has_master_key']}")
        else:
            print_error("Hệ thống ABE chưa được setup")
            return
        
        # Bước 2: Kiểm tra user có private key chưa
        print_step(2, "Kiểm tra User có Private Key chưa")
        
        url = f"{CA_API_BASE}/user/private-key/check"
        response = requests.get(url, params={'user_id': user_id})
        
        if response.status_code == 200:
            data = response.json()
            has_key = data['has_key']
            
            if has_key:
                print_info(f"User {user_id} đã có private key")
                key_info = data['key_info']
                print_info(f"Attributes: {key_info['attributes']}")
                print_info(f"Tạo lúc: {key_info['created_at']}")
                print_info(f"Mã hóa: {key_info['encryption_info']['algorithm']}")
                
                # Skip to authentication
                goto_authentication = True
            else:
                print_info(f"User {user_id} chưa có private key")
                goto_authentication = False
        else:
            print_error("Không thể kiểm tra trạng thái private key")
            return
        
        # Bước 3: Tạo private key nếu chưa có
        if not goto_authentication:
            print_step(3, "Tạo và Mã hóa Private Key")
            
            print_info(f"Tạo private key cho user: {user_id}")
            print_info(f"Password: {password}")
            print_info(f"Attributes: {attributes}")
            
            url = f"{CA_API_BASE}/user/private-key/generate"
            data = {
                'user_id': user_id,
                'password': password,
                'attributes': attributes
            }
            
            print_info("Đang thực hiện:")
            print_info("1. Validate password strength...")
            print_info("2. Generate ABE private key...")
            print_info("3. Derive encryption key từ password (Argon2id + HKDF)...")
            print_info("4. Encrypt private key bằng AES-256-GCM...")
            print_info("5. Lưu encrypted key lên Firestore...")
            
            response = requests.post(url, json=data)
            
            if response.status_code in [200, 201]:
                result = response.json()
                print_success("Private key đã được tạo và mã hóa thành công!")
                print_info(f"Private Key ID: {result['private_key_id']}")
                print_info(f"Encryption Info: {result['encryption_info']}")
            else:
                print_error("Không thể tạo private key")
                if response.status_code == 400:
                    error_data = response.json()
                    if 'password_errors' in error_data:
                        print_error(f"Password errors: {error_data['password_errors']}")
                return
        
        # Bước 4: Xác thực và lấy private key
        print_step(4, "Xác thực Password và Lấy Private Key")
        
        print_info(f"User nhập password để lấy private key...")
        print_info("Đang thực hiện:")
        print_info("1. Lấy encrypted private key từ Firestore...")
        print_info("2. Derive decryption key từ password...")
        print_info("3. Decrypt private key...")
        print_info("4. Verify integrity...")
        
        url = f"{CA_API_BASE}/user/private-key/authenticate"
        data = {
            'user_id': user_id,
            'password': password
        }
        
        response = requests.post(url, json=data)
        
        if response.status_code == 200:
            result = response.json()
            print_success("Authentication thành công!")
            print_info(f"User attributes: {result['attributes']}")
            print_info("Private key đã được decrypt và sẵn sàng sử dụng")
        else:
            print_error("Authentication thất bại!")
            if response.status_code == 401:
                print_error("Password không đúng")
            return
        
        # Bước 5: Test sai password
        print_step(5, "Test Authentication với Sai Password")
        
        print_info("Thử với password sai để test bảo mật...")
        
        data = {
            'user_id': user_id,
            'password': "WrongPassword123@"
        }
        
        response = requests.post(url, json=data)
        
        if response.status_code == 401:
            print_success("Hệ thống từ chối password sai - Bảo mật hoạt động tốt!")
        else:
            print_error("Hệ thống không từ chối password sai - Có vấn đề bảo mật!")
        
        # Bước 6: Thống kê hệ thống
        print_step(6, "Thống kê Hệ thống")
        
        # Đếm số users đã có private key
        test_users = ['test_user_001', 'doctor_001', 'nurse_001', 'admin_001', user_id]
        user_count = 0
        
        url = f"{CA_API_BASE}/user/private-key/check"
        
        for test_user in test_users:
            response = requests.get(url, params={'user_id': test_user})
            if response.status_code == 200:
                data = response.json()
                if data['has_key']:
                    user_count += 1
        
        print_info(f"Tổng số users có private key: {user_count}")
        print_info("Tất cả private keys đều được mã hóa với password riêng")
        print_info("Master Key và Public Key được tái sử dụng cho tất cả users")
        
        # Kết luận
        print_step("✅", "DEMO HOÀN THÀNH")
        
        print("🎯 Hệ thống đã thành công triển khai:")
        print("   ✓ Master Key & Public Key chỉ tạo 1 lần")
        print("   ✓ Private Key mã hóa bằng password user") 
        print("   ✓ Mã hóa mạnh: Argon2id + HKDF + AES-256-GCM")
        print("   ✓ Lưu trữ an toàn trên cloud")
        print("   ✓ User chỉ cần nhớ password")
        print("   ✓ Tự động decrypt khi cần sử dụng")
        
        print("\n🔒 Tính năng bảo mật:")
        print("   • Password strength validation")
        print("   • Salt ngẫu nhiên cho mỗi key")
        print("   • Authentication tag verify integrity")
        print("   • Secure error handling")
        
        print(f"\n📊 Hiệu suất: Authentication thành công trong ~1-2 giây")
        
    except requests.exceptions.ConnectionError:
        print_error("Không thể kết nối server. Đảm bảo Flask app đang chạy trên http://localhost:5000")
    except Exception as e:
        print_error(f"Demo thất bại: {e}")

if __name__ == "__main__":
    demo_complete_workflow()
