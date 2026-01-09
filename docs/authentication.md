# Authentication API Documentation

## Overview
Hệ thống xác thực sử dụng JWT (JSON Web Tokens) với djangorestframework-simplejwt. Tất cả API endpoints sử dụng Bearer token authentication.

## Token Configuration
- **Access Token Lifetime**: 1 giờ
- **Refresh Token Lifetime**: 7 ngày
- **Token Rotation**: Enabled (refresh token mới được tạo khi refresh)
- **Token Blacklist**: Enabled (token cũ bị blacklist sau khi refresh hoặc logout)

## API Endpoints

### 1. User Registration
**POST** `/api/auth/register/`

Đăng ký tài khoản mới. Hiện tại cho phép đăng ký tự do (sau này sẽ thêm admin approval).

**Request:**
```json
{
    "username": "nva_it",
    "email": "user@example.com",
    "password": "SecurePass123!",
    "password2": "SecurePass123!",
    "full_name": "Nguyễn Văn A",
    "phone": "0123456789"
}
```

**Response (201 Created):**
```json
{
    "message": "User registered successfully",
    "user": {
        "id": 1,
        "username": "nva_it",
        "email": "user@example.com",
        "full_name": "Nguyễn Văn A"
    },
    "tokens": {
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }
}
```

**Validation:**
- Username: unique, required
- Email: unique, required, valid email format
- Password: min 8 characters, complexity requirements
- Passwords must match

---

### 2. User Login
**POST** `/api/auth/login/`

Đăng nhập và nhận JWT tokens.

**Request:**
```json
{
    "username": "nva_it",
    "password": "SecurePass123!"
}
```

**Response (200 OK):**
```json
{
    "message": "Login successful",
    "user": {
        "id": 1,
        "username": "nva_it",
        "email": "user@example.com",
        "profile": {
            "full_name": "Nguyễn Văn A",
            "user_type": "data_user",
            "account_status": "active",
            "phone": "0123456789"
        }
    },
    "tokens": {
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid credentials
- `403 Forbidden`: Account disabled, suspended, or expired

---

### 3. Token Refresh
**POST** `/api/auth/token/refresh/`

Làm mới access token bằng refresh token.

**Request:**
```json
{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response (200 OK):**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."  // New refresh token (if rotation enabled)
}
```

---

### 4. Logout
**POST** `/api/auth/logout/`

Đăng xuất (blacklist refresh token).

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response (200 OK):**
```json
{
    "message": "Logout successful"
}
```

---

### 5. Get User Profile
**GET** `/api/auth/profile/`

Lấy thông tin profile của user đang đăng nhập.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
    "id": 1,
    "username": "nva_it",
    "email": "user@example.com",
    "first_name": "",
    "last_name": "",
    "date_joined": "2025-01-26T10:30:00Z",
    "profile": {
        "full_name": "Nguyễn Văn A",
        "user_type": "data_user",
        "account_status": "active",
        "phone": "0123456789",
        "address": null,
        "bio": null,
        "account_expiry_date": null,
        "is_email_verified": false
    }
}
```

---

### 6. Change Password
**POST** `/api/auth/change-password/`

Đổi mật khẩu cho user đang đăng nhập.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
    "old_password": "OldPass123!",
    "new_password": "NewPass123!",
    "new_password2": "NewPass123!"
}
```

**Response (200 OK):**
```json
{
    "message": "Password changed successfully"
}
```

**Error (400 Bad Request):**
```json
{
    "error": "Old password is incorrect"
}
```

---

### 7. Password Reset Request
**POST** `/api/auth/password-reset/request/`

Yêu cầu reset mật khẩu (gửi token qua email).

**Request:**
```json
{
    "email": "user@example.com"
}
```

**Response (200 OK):**
```json
{
    "message": "Password reset instructions sent to email",
    "debug_token": "xyz123..."  // Chỉ hiển thị trong development
}
```

**Note:** Trong production, cần implement email service để gửi reset link: 
`https://yourdomain.com/reset-password?token=xyz123`

---

### 8. Password Reset Confirm
**POST** `/api/auth/password-reset/confirm/`

Xác nhận reset mật khẩu với token.

**Request:**
```json
{
    "token": "xyz123...",
    "new_password": "NewPass123!",
    "new_password2": "NewPass123!"
}
```

**Response (200 OK):**
```json
{
    "message": "Password reset successfully"
}
```

**Error Responses:**
- `400 Bad Request`: Invalid or expired token

---

## User Types (BM1)
Theo QĐ1 - Quy định về phân loại người dùng:

| User Type | Description |
|-----------|-------------|
| `super_admin` | Quản trị viên cấp cao - quản lý toàn hệ thống |
| `admin` | Quản trị viên - quản lý người dùng, duyệt tài khoản |
| `data_owner` | Chủ sở hữu dữ liệu - tạo và quản lý dữ liệu |
| `data_user` | Người dùng dữ liệu - truy cập dữ liệu theo quyền |
| `auditor` | Kiểm toán viên - xem audit logs |
| `guest` | Khách - quyền giới hạn |

## Account Status
| Status | Description |
|--------|-------------|
| `pending` | Chờ kích hoạt bởi admin |
| `active` | Tài khoản hoạt động |
| `inactive` | Tài khoản bị vô hiệu hóa |
| `suspended` | Tài khoản bị tạm ngưng |
| `expired` | Tài khoản hết hạn |

## Using JWT Tokens

### Authentication Header
Tất cả protected endpoints yêu cầu header:
```
Authorization: Bearer <access_token>
```

### Token Flow
1. **Register/Login** → Nhận access + refresh tokens
2. **API Calls** → Sử dụng access token
3. **Token Expired** → Refresh token để lấy access token mới
4. **Logout** → Blacklist refresh token

### Example with cURL
```bash
# Login
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"nva_it","password":"SecurePass123!"}'

# Use access token
curl -X GET http://localhost:8000/api/auth/profile/ \
  -H "Authorization: Bearer <access_token>"

# Refresh token
curl -X POST http://localhost:8000/api/auth/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh":"<refresh_token>"}'
```

### Example with Python requests
```python
import requests

# Login
response = requests.post('http://localhost:8000/api/auth/login/', json={
    'username': 'nva_it',
    'password': 'SecurePass123!'
})
tokens = response.json()['tokens']

# Use access token
headers = {'Authorization': f'Bearer {tokens["access"]}'}
profile = requests.get('http://localhost:8000/api/auth/profile/', headers=headers)
print(profile.json())
```

## Security Notes

### Password Requirements
- Minimum 8 characters
- Cannot be entirely numeric
- Cannot be too similar to username/email
- Cannot be a commonly used password

### Token Security
- Store tokens securely (httpOnly cookies for web, secure storage for mobile)
- Never expose tokens in URLs
- Implement token refresh before expiry
- Blacklist tokens on logout

### Production Checklist
- [ ] Enable HTTPS
- [ ] Implement email verification
- [ ] Add rate limiting for auth endpoints
- [ ] Configure CORS properly
- [ ] Implement password reset email service
- [ ] Add admin approval for registration
- [ ] Set up logging for authentication events
- [ ] Configure secure SECRET_KEY in environment

## Next Steps

1. **Email Integration**: Implement email verification và password reset emails
2. **Admin Approval**: Thêm workflow approval cho registration (set `account_status='pending'`)
3. **2FA**: Implement two-factor authentication
4. **User Attributes (BM4)**: Tạo model và API cho ABAC attributes
5. **Role-based Permissions**: Implement permissions dựa trên user_type
6. **Audit Logging**: Log tất cả authentication events

## Testing

### Test Registration
```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "TestPass123!",
    "password2": "TestPass123!",
    "full_name": "Test User",
    "phone": "0123456789"
  }'
```

### Test Login
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "TestPass123!"
  }'
```
