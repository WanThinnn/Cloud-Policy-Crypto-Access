# Đặc Tả API & Luồng Hoạt Động (API Specifications & Workflows)

Tài liệu này mô tả cách hệ thống **Cloud-Firestore-Crypto-Access** hoạt động, quy trình xác thực, kiến trúc bảo mật (CP-ABE kết hợp ABAC) và danh sách các endpoint REST API chính.

## 1. Luồng Hoạt Động Cốt Lõi (Core Workflows)

### 1.1. Luồng Xác Thực (Authentication Flow)
Hệ thống sử dụng JWT (JSON Web Token) kết hợp HttpOnly Cookie để bảo mật session và chống lại tấn công XSS.
1. **Login**: Client gửi request chứa `username` và `password` tới `/api/auth/login/`.
2. **Response**: 
   - Server xác thực thông tin.
   - Trả về thông tin cơ bản của user trong response body.
   - Gắn `access_token` và `refresh_token` vào HTTP response headers thông qua cơ chế `Set-Cookie` với các cờ bảo mật (HttpOnly, Secure, SameSite=Lax).
3. **Gọi API**: Đối với các request tiếp theo tới hệ thống (ví dụ: upload/download file, fetch dữ liệu), trình duyệt (hoặc client) sẽ tự động đính kèm Cookie chứa token mà không cần can thiệp bằng JavaScript `localStorage`.
4. **CSRF Protection**: Các thao tác thay đổi dữ liệu (POST, PUT, DELETE) bắt buộc phải truyền header `X-CSRFToken` lấy từ cookie `csrftoken`.

### 1.2. Luồng Kiểm Soát Truy Cập & Giải Mã (ABAC + CP-ABE)
Mỗi tài nguyên file (Upload) trong hệ thống đều trải qua 2 tầng bảo mật:
- **Tầng 1 - ABAC (Attribute-Based Access Control)**:
  - Khi user yêu cầu tải/xem file, PEP (Policy Enforcement Point) sẽ gửi request kiểm tra quyền đến PDP (Policy Decision Point sử dụng PyCasbin).
  - PDP đánh giá thuộc tính của user (`department`, `role`, `clearance_level`, v.v.), kết hợp với chính sách (Policies) để đưa ra quyết định Allow hoặc Deny.
- **Tầng 2 - HashiCorp Vault & CP-ABE (Envelope Encryption)**:
  - Nếu ABAC cho phép, file mã hóa mới được tải về server. 
  - Hệ thống lấy Master Key từ **HashiCorp Vault**, sau đó sinh động (on-the-fly) khóa bí mật CP-ABE dựa trên tập hợp thuộc tính hiện tại của user. Khóa này được cache tạm thời trên **Redis** (tránh lưu trữ cố định vào DB).
  - Khóa CP-ABE dùng để giải mã khóa AES (DEK) đã được bọc (wrap). Sau đó dùng khóa AES giải mã nội dung file và trả về cho user. Các khóa và nội dung file chỉ tồn tại trên RAM trong quá trình xử lý request.

### 1.3. Luồng Mã Hóa CSDL & Bảo Mật Siêu Dữ Liệu (Field-level Encryption)
Ngoài việc bảo vệ nội dung file, hệ thống còn chống rò rỉ dữ liệu từ cấu trúc bảng SQL:
- **AES-256-GCM Field Encryption**: Các cột nhạy cảm trong CSDL (Tên file gốc, Metadata, Signed URL, Đường dẫn vật lý) đều bị mã hóa trước khi ghi.
- **HMAC-SHA3-256 Blind Indexing**: Hỗ trợ tìm kiếm an toàn trên các cột đã mã hóa (ví dụ: tìm kiếm theo tên file hoặc hash) mà không làm rò rỉ văn bản gốc.
- **Che giấu đường dẫn (Obfuscation)**: Tên file vật lý lưu trên Cloud Storage (Supabase) là chuỗi UUID ngẫu nhiên, hoàn toàn không mang ý nghĩa nghiệp vụ.
- **Auto-Extract Metadata**: Khi upload, hệ thống tự động gom IP, User-Agent, thông tin uploader, file size, MIME type và mã hóa toàn bộ cục JSON metadata này.
- **Post-Quantum TLS 1.3 (ML-KEM)**: Mọi kết nối từ Client tới API đều được truyền qua Reverse Proxy Nginx với cơ chế trao đổi khóa Hậu Lượng Tử (Hybrid X25519MLKEM768), chống lại hoàn toàn rủi ro thu thập gói tin để giải mã bằng máy tính lượng tử.

## 2. Đặc Tả REST API (REST API Specifications)

Base URL: `http(s)://<domain>`

### 2.1. Nhóm API Xác Thực (Auth API)
Prefix: `/api/auth/`

| Phương thức | Endpoint | Mô tả | Yêu cầu Auth |
| ----------- | -------- | ----- | ------------ |
| POST | `/login/` | Đăng nhập hệ thống. Trả về JWT Token qua HttpOnly Cookie. | Không |
| POST | `/register/` | Đăng ký tài khoản mới (cần được Super Admin kích hoạt hoặc tự động tạo nếu cấu hình cho phép). | Không |
| POST | `/logout/` | Xóa Access Token và Refresh Token khỏi Cookie. | Có |
| POST | `/token/refresh/` | Cấp lại Access Token mới dựa trên Refresh Token. | Có (Cookie) |
| GET | `/profile/` | Lấy thông tin user hiện tại (thông tin cá nhân, user type). | Có |
| GET | `/permissions/` | Lấy danh sách quyền hệ thống của user hiện tại (is_admin, is_super_admin). | Có |
| POST | `/change-password/` | Đổi mật khẩu. Yêu cầu `old_password` và `new_password`. | Có |
| GET | `/sessions/` | Lấy danh sách thiết bị/phiên đang đăng nhập của user. Hỗ trợ Session Management. | Có |
| POST | `/sessions/{id}/revoke/` | Đăng xuất (thu hồi) một thiết bị cụ thể. | Có |
| POST | `/sessions/revoke_all/` | Đăng xuất tất cả các thiết bị khác, giữ lại thiết bị hiện tại. | Có |

### 2.2. Nhóm API Quản Trị Hệ Thống & Phân Quyền (Admin API)
Prefix: `/api/admin/`

| Phương thức | Endpoint | Mô tả | Yêu cầu Auth |
| ----------- | -------- | ----- | ------------ |
| GET/POST | `/user-types/` | Quản lý danh sách các loại người dùng (User Types). | Admin |
| GET/POST | `/attributes/` | Định nghĩa lược đồ thuộc tính (Attribute Definitions). Dùng cho ABAC và CP-ABE. | Admin |
| GET/POST | `/policies/` | Quản trị chính sách ABAC (Access Policies). Cho phép định nghĩa rules theo định dạng Casbin. | Admin |
| POST | `/policies/parse_ast/` | Phân tích chuỗi chính sách thành Cây cú pháp trừu tượng (AST) phục vụ giao diện kéo thả. | Admin |
| POST | `/policies/test_policy/` | Kiểm thử chính sách ABAC với thuộc tính thực tế của người dùng trước khi lưu. | Admin |
| GET/POST | `/users/` | Quản lý danh sách người dùng toàn hệ thống (tạo, khóa, duyệt tài khoản). | Admin |
| GET | `/dashboard-stats/` | Lấy các số liệu tổng quan (Tổng số user, file, chính sách) hiển thị lên biểu đồ. | Admin |
| GET | `/users/{id}/attributes/` | Liệt kê các thuộc tính hiện đang được gán cho một user cụ thể. | Admin |
| POST | `/users/{id}/attributes/assign/`| Gán thuộc tính mới cho user. Kích hoạt tự động xóa CP-ABE Redis Cache của user. | Admin |
| DELETE | `/users/{id}/attributes/{attr_id}/`| Thu hồi thuộc tính của user. Tự động Invalidate Redis Cache. | Admin |

### 2.3. Nhóm API Lưu Trữ & Giải Mã Dữ Liệu (Storage API)
Prefix: `/api/storage/`

| Phương thức | Endpoint | Mô tả | Yêu cầu Auth |
| ----------- | -------- | ----- | ------------ |
| GET/POST | `/buckets/` | Quản lý Storage Buckets (Kho lưu trữ logic để nhóm file). | Có |
| GET/POST | `/files/` | API chính xử lý Upload File. Dữ liệu POST bao gồm `file` và `policy` (Chính sách CP-ABE mong muốn). File sẽ được mã hóa AES, khóa AES mã hóa CP-ABE trước khi lưu. **Đồng thời**, các thông tin metadata, tên file và đường dẫn cũng được tự động trích xuất và mã hóa bằng AES-256-GCM trước khi lưu xuống SQL. | Có |
| GET | `/files/{id}/` | Lấy metadata của file. | Có |
| GET | `/files/{id}/download/` | Yêu cầu tải nội dung file. Hệ thống thực hiện check ABAC -> sinh khóa CP-ABE (nếu chưa cache) -> giải mã -> trả về stream data. | Có |
| DELETE | `/files/{id}/` | Xóa mềm file (đưa vào Thùng rác). Xóa cứng (Permanent delete) chỉ dành cho Admin/Owner. | File Owner/Admin |
| POST | `/files/clipboard_action/` | Sao chép (Copy), Cắt (Cut) & Dán (Paste) file/thư mục. Hỗ trợ phát hiện trùng lặp (tự đổi tên) và kiểm tra quyền ABAC ở cả nguồn và đích. | Có |
| POST | `/files/rename/` | Đổi tên file hoặc thư mục. Hỗ trợ cập nhật trường mã hóa và tính lại Blind Index. | Data Owner/Admin |
| POST | `/files/create_folder/` | Tạo thư mục mới (thư mục ảo thông qua placeholder `.folder`). | Có |
| GET | `/files/trash/` | Liệt kê tất cả file đã xóa mềm trong Thùng rác cho user hiện tại hoặc toàn bộ (Admin). | Có |
| POST | `/files/restore/` | Khôi phục file đã xóa mềm từ Thùng rác. | File Owner/Admin |
| DELETE | `/files/permanent_delete/` | Xóa cứng file khỏi Thùng rác và Cloud Storage. | File Owner/Admin |
| GET | `/files/{id}/versions/` | Liệt kê tất cả phiên bản của file. | Có |
| POST | `/files/{id}/assign_access/` | Gán chính sách truy cập CP-ABE và cấp quyền trực tiếp cho user. Hỗ trợ kết hợp chính sách thông minh (OR-merge re-encryption). | File Owner/Admin |

## 3. Cách Sử Dụng API Từ Frontend

Khi xây dựng giao diện hoặc gọi API từ Frontend (Sử dụng Axios hoặc Fetch):

**1. Không cần quản lý Access Token thủ công**
Do hệ thống sử dụng HttpOnly Cookie, bạn không cần phải thêm Header `Authorization: Bearer <token>` vào các request. Trình duyệt tự động lo việc đính kèm Cookie.

**2. Quản lý CSRF Token (Bắt buộc với POST/PUT/DELETE)**
Để bảo mật, bạn phải đọc giá trị của cookie `csrftoken` và thêm nó vào request headers dưới tên `X-CSRFToken`.

*Ví dụ sử dụng Fetch API:*
```javascript
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Gọi API Upload
async function uploadFile(fileInput, policyString) {
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('policy', policyString); // e.g: 'department:it AND role:manager'

    const response = await fetch('/api/storage/files/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken') // Quan trọng!
            // Không set Content-Type, trình duyệt tự định dạng multipart/form-data
        },
        body: formData
    });

    return await response.json();
}
```

## 4. Xử Lý Lỗi Cơ Bản (Error Handling)

- **401 Unauthorized**: User chưa đăng nhập hoặc Token đã hết hạn (kể cả Refresh Token). Frontend nên redirect về trang `/auth/login/`.
- **403 Forbidden**: User đã xác thực nhưng bị hệ thống ABAC chặn không cho phép thực hiện hành động do thiếu thuộc tính (Policy Deny) hoặc không đủ quyền Admin. Hoặc do vi phạm chính sách Impossible Travel (đăng nhập từ 2 vị trí địa lý cách xa nhau trong khoảng thời gian ngắn). Hoặc do CSRF Token bị sai/thiếu.
- **404 Not Found**: Tài nguyên không tồn tại.
- **429 Too Many Requests**: Request bị chặn bởi hệ thống Rate Limiting (VD: giới hạn số lần upload/download mỗi phút) nhằm bảo vệ CPU khỏi tấn công DoS/DDoS.
- **500 Internal Server Error**: Lỗi máy chủ (ví dụ: CP-ABE không thể giải mã do sai policy, Redis server sập, ...). Mọi lỗi 500 đều được catch và ghi log cẩn thận ở backend.
