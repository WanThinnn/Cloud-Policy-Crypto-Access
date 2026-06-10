# **QUẢN LÝ VÀ KIỂM SOÁT TRUY CẬP TÀI LIỆU AN TOÀN TRÊN CSDL ĐÁM MÂY TRONG DOANH NGHIỆP**

## **1.1. Giới thiệu đề tài**

Trong bối cảnh các doanh nghiệp ngày càng chuyển dịch sang hạ tầng điện toán đám mây, việc lưu trữ, chia sẻ và khai thác tài liệu nội bộ trên môi trường cloud đã trở thành xu hướng tất yếu. Mô hình này mang lại nhiều lợi ích về khả năng mở rộng, tính linh hoạt và tối ưu chi phí vận hành. Tuy nhiên, song song với đó là những thách thức nghiêm trọng liên quan đến **an toàn thông tin** và **kiểm soát truy cập dữ liệu**, đặc biệt đối với các tài liệu nhạy cảm phục vụ hoạt động quản trị, tài chính, nhân sự hoặc nghiên cứu chiến lược của doanh nghiệp.

Các cơ chế kiểm soát truy cập truyền thống dựa trên danh sách quyền cố định (ACL) hoặc vai trò (RBAC) thường bộc lộ nhiều hạn chế trong môi trường cloud hiện đại, nơi người dùng, tài nguyên và ngữ cảnh truy cập liên tục thay đổi. Đồng thời, việc chỉ dựa vào cơ chế kiểm soát logic ở tầng ứng dụng là chưa đủ, bởi dữ liệu lưu trữ trên hạ tầng đám mây thường được giả định là **semi-trusted** và có nguy cơ bị truy cập trái phép nếu xảy ra sự cố bảo mật.

Xuất phát từ những vấn đề trên, đề tài **“Quản lý và Kiểm soát Truy cập Tài liệu An toàn trên CSDL Đám mây trong Doanh nghiệp”** được xây dựng nhằm đề xuất và triển khai một hệ thống quản lý tài liệu an toàn, kết hợp chặt chẽ giữa **kiểm soát truy cập dựa trên thuộc tính (Attribute-Based Access Control – ABAC)** và **cưỡng chế truy cập bằng mật mã thông qua CP-ABE kết hợp AES-GCM**.

Hệ thống không chỉ hỗ trợ các chức năng nghiệp vụ cơ bản như **tạo, lưu trữ, chia sẻ và quản lý phiên bản tài liệu**, mà còn áp dụng mô hình **kiểm soát truy cập hai lớp (dual-layer access control)**. Trong đó, ABAC đóng vai trò quyết định logic truy cập dựa trên chính sách và thuộc tính, trong khi CP-ABE đảm bảo rằng chỉ những người dùng có thuộc tính phù hợp mới có khả năng giải mã và truy xuất nội dung dữ liệu, ngay cả trong trường hợp hạ tầng lưu trữ bị xâm nhập.

Cơ chế ABAC trong hệ thống được triển khai theo kiến trúc chuẩn gồm ba thành phần logic: **Policy Administration Point (PAP)**, **Policy Decision Point (PDP)** và **Policy Enforcement Point (PEP)**. PAP cho phép Super Admin quản trị chính sách truy cập; PDP chịu trách nhiệm đánh giá các yêu cầu truy cập dựa trên thuộc tính người dùng, tài nguyên và ngữ cảnh; trong khi PEP đảm nhiệm việc thực thi quyết định cho phép hoặc từ chối truy cập tại các điểm tương tác như API upload/download tài liệu. Luồng xử lý truy cập được thực hiện theo trình tự: *Request → PEP → PDP → Decision → Enforcement*, đảm bảo tính nhất quán và kiểm soát tập trung.

Song song đó, hệ thống áp dụng phương pháp **mã hóa lai (hybrid encryption)** để bảo vệ dữ liệu. Nội dung file được mã hóa bằng thuật toán đối xứng **AES-256-GCM** nhằm đảm bảo tính bảo mật và toàn vẹn, trong khi khóa AES được mã hóa bằng **CP-ABE** theo chính sách thuộc tính do Data Owner định nghĩa. Cách tiếp cận này cho phép gắn chính sách truy cập trực tiếp vào dữ liệu, giúp loại bỏ sự phụ thuộc vào độ tin cậy của hạ tầng lưu trữ đám mây.

Hơn thế nữa, để đối phó với rủi ro rò rỉ dữ liệu từ cơ sở dữ liệu (SQL DB), hệ thống ứng dụng kỹ thuật **Mã hóa mức trường (Field-level Encryption)** bằng thuật toán **AES-256-GCM** kết hợp **Chỉ mục mù (Blind Indexing)** bằng **HMAC-SHA3-256**. Các thông tin nhạy cảm của tài liệu như đường dẫn vật lý, tên gốc, URL chia sẻ và các siêu dữ liệu (metadata) đều được mã hóa tuyệt đối trước khi lưu vào CSDL. Đường dẫn lưu trữ thực tế của file trên Cloud Storage được che giấu bằng các chuỗi ngẫu nhiên (UUID). Tên bảng (`file_name`) hay (`file_path`) dùng thuật toán băm SHA3-256 để tìm kiếm nhằm bảo vệ sự riêng tư.

Ngoài các chức năng kiểm soát truy cập, hệ thống còn hỗ trợ **quản lý người dùng, quản lý thuộc tính và lược đồ thuộc tính, quản lý khóa mã hóa, quản lý chính sách truy cập, phân quyền Super Admin**, cũng như cung cấp **các báo cáo thống kê và audit** phục vụ công tác giám sát, đánh giá và tuân thủ an toàn thông tin trong doanh nghiệp.

Mục tiêu chính của đề tài bao gồm:
- Đảm bảo **tính bảo mật, toàn vẹn và an toàn** của tài liệu được lưu trữ và chia sẻ trên nền tảng đám mây.
- Xây dựng cơ chế kiểm soát truy cập **linh hoạt, chi tiết và mở rộng**, phù hợp với môi trường doanh nghiệp hiện đại.
- Giảm thiểu rủi ro rò rỉ dữ liệu và truy cập trái phép, đồng thời **tối ưu hóa quy trình quản lý và chia sẻ tài liệu** trong nội bộ doanh nghiệp.

### **Các bên liên quan trong hệ thống**

- **CA (Certificate Authority / Attribute Authority):** CA đóng vai trò là **Attribute Authority (AA)**, chịu trách nhiệm thiết lập hệ thống CP-ABE, sinh các tham số công khai và khóa bí mật gốc (master secret key), cấp phát khóa bí mật cho người dùng dựa trên tập thuộc tính được phê duyệt, cũng như thu hồi hoặc tái cấp khóa khi thuộc tính người dùng thay đổi. CA được giả định là thành phần tin cậy cao nhất trong hệ thống và không trực tiếp tham gia vào quá trình lưu trữ dữ liệu.

- **Data Owner (Chủ sở hữu dữ liệu):** Là người tạo và quản lý tài liệu trong hệ thống. Data Owner chịu trách nhiệm định nghĩa chính sách truy cập dựa trên thuộc tính, thực hiện mã hóa dữ liệu và upload file lên hệ thống lưu trữ đám mây, đồng thời quản lý phiên bản và quyết định việc cấp hoặc thu hồi quyền truy cập đối với tài liệu do mình sở hữu.

- **Data User (Người dùng dữ liệu):** Là các cá nhân trong doanh nghiệp được cấp quyền truy cập tài liệu theo chính sách ABAC. Data User chỉ có thể thực hiện các hành động trên tài nguyên nếu thỏa mãn đồng thời cả điều kiện logic của ABAC và điều kiện mật mã của CP-ABE.

Qua đó, đề tài hướng đến việc xây dựng một giải pháp **quản lý và kiểm soát truy cập dữ liệu an toàn, tin cậy và khả thi**, phù hợp với các doanh nghiệp đang chuyển dịch sang môi trường làm việc số trên nền tảng điện toán đám mây.

![image](img/cp-abe.png)


## **1.2. Danh sách các yêu cầu**

| STT | Tên yêu cầu                   | Biểu mẫu       | Qui định | Ghi chú |
| --- | ----------------------------- | -------------- | -------- | ------- |
| 1   | Tạo người dùng                | BM1            | QĐ1      |         |
| 2   | Upload file mã hóa            | BM2            | QĐ2      |         |
| 3   | Quản lý danh sách file        | BM3            |          |         |
| 4   | Quản lý thuộc tính người dùng | BM4            | QĐ4      |         |
| 5   | Quản lý khóa truy cập         | BM5            | QĐ5      |         |
| 6   | Quản lý phiên bản file        | BM6            | QĐ6      |         |
| 7   | Quản lý chính sách truy cập   | BM7            | QĐ7      |         |
| 8   | Quản lý Super Admin           | BM8            | QĐ8      |         |
| 9   | Quản lý lược đồ thuộc tính    | BM9            | QĐ9      |         |
| 10  | Lập báo cáo hệ thống          | BM10.1, BM10.2 |          |         |
| 11  | Thay đổi cấu hình hệ thống    |                | QĐ11     |         |
| 12  | Quản lý nhật ký truy cập      | BM12           | QĐ12     |         |
| 13  | Quản lý thu hồi khóa          | BM13           | QĐ13     |         |
| 14  | Quản lý cấu hình hệ thống     | BM14           | QĐ14     |         |


## **1.3. Danh sách các biểu mẫu và qui định**

### **1.3.1. Biểu mẫu 1 và qui định 1**

**BM1: Thông Tin Định Danh Người Dùng**  
User ID: _______  
Họ và tên: _______  
Email: _______  
Username: _______  
Mật khẩu (hash): _______  
Loại người dùng: _______  
Ngày tạo tài khoản: _______  
Ngày hết hạn tài khoản: _______  
Trạng thái tài khoản: _______  
Tham chiếu thuộc tính: → BM4 (user_attributes)  

> **Lưu ý:** Các thuộc tính ABAC (department, role, clearance_level, etc.) được lưu riêng trong collection `user_attributes` (BM4) để đảm bảo tính nhất quán và là nguồn tin cậy duy nhất cho hệ thống CP-ABE và ABAC.

**QĐ1:** Loại người dùng (user_type) được định nghĩa trong lược đồ thuộc tính (BM9) và có thể mở rộng theo nhu cầu doanh nghiệp. Các loại mặc định bao gồm:

| Loại người dùng | Mô tả                   | Quyền đặc biệt                                   |
| --------------- | ----------------------- | ------------------------------------------------ |
| `super_admin`   | Quản trị viên cao nhất  | Quản lý hệ thống, người dùng, chính sách, khóa   |
| `admin`         | Quản trị viên phòng ban | Quản lý người dùng trong phạm vi phòng ban       |
| `data_owner`    | Chủ sở hữu dữ liệu      | Tạo, mã hóa, định nghĩa chính sách file          |
| `data_user`     | Người dùng dữ liệu      | Đọc/ghi file theo chính sách được cấp            |
| `auditor`       | Kiểm toán viên          | Chỉ xem logs và báo cáo, không truy cập nội dung |
| `guest`         | Khách                   | Quyền hạn chế, thời hạn ngắn                     |

Mỗi loại có tập quyền hạn cơ bản được kế thừa, nhưng quyền truy cập tài nguyên cụ thể vẫn được kiểm soát bởi chính sách ABAC dựa trên thuộc tính (BM4). Chỉ Super Admin mới có thể tạo người dùng và gán loại. Người dùng không được tự phép đăng ký mới tài khoản. Mỗi người dùng phải có đầy đủ các thuộc tính bắt buộc theo lược đồ thuộc tính (BM9) và được lưu trữ trong BM4 để phục vụ kiểm soát truy cập ABAC và CP-ABE.

**Ví dụ: Thông tin định danh người dùng**  
BM1: Thông Tin Định Danh Người Dùng  
User ID: 22520001  
Họ và tên: Nguyễn Văn A  
Email: itmanager001@company.com  
Username: nva_it  
Mật khẩu (hash): $argon2id$v=19$m=65536...  
Loại người dùng: data_owner  
Ngày tạo tài khoản: 08/09/2025  
Ngày hết hạn tài khoản: 08/09/2026  
Trạng thái tài khoản: active  
Tham chiếu thuộc tính: → UA22520001 (user_attributes)  

### **1.3.2 Biểu mẫu 2 và qui định 2**

**BM2: Thông Tin File Upload**  
Tên file: _______  
Loại file: _______  
Kích thước: _______  
Chính sách truy cập: _______  
Mô tả: _______  
Tags: _______  
Ngày upload: _______  
Người upload: _______  

**QĐ2:** Có 5 loại file chính (text/plain, document, image, video, audio). Kích thước tối đa 100MB. Chỉ nhận file không chứa virus và được mã hóa dựa trên thuộc tính chính sách bản mã (CP-ABE). Chính sách thuộc tính được quy định bởi chủ sở hữu (Data Owner) của file đó, người sử dụng  (Data User) có thuộc tính phù hợp với chính sách thì sẽ truy cập được file. Không ai có thể thay đổi được Chính sách truy cập của file ngoài chủ sở hữu.

Ngoài ra, hệ thống tự động trích xuất các **siêu dữ liệu (metadata)** như: IP, User-Agent, thông tin định danh của người Upload (Tên, Email, Vai trò), kích thước file và MIME Type. Toàn bộ Metadata này cùng với các trường quan trọng (Tên file gốc, Đường dẫn, Signed URL) được **mã hóa hoàn toàn** bằng AES-256-GCM trong CSDL SQLite. Đường dẫn lưu file trên Cloud Storage được gán bằng chuỗi UUID ngẫu nhiên để chống việc suy đoán cấu trúc thư mục từ phía hạ tầng.

**Ví dụ: Thông tin file upload**  
BM2: Thông Tin File Upload  
Tên file: bao-cao-quy-1.pdf  
Loại file: document
Kích thước: 39 bytes  
Chính sách truy cập: "department:it" OR "department:hr"  
Mô tả: File báo cáo quý 1 của doanh nghiệp.  
Tags: report, upload  
Ngày upload: 08/09/2025  
Người upload: 22520001  


### **1.3.3 Biểu mẫu 3**

**BM3: Danh Sách File**

| STT | Mã File                              | Tên File          | Loại File  | Người Sở Hữu | Trạng Thái |
| --- | ------------------------------------ | ----------------- | ---------- | ------------ | ---------- |
| 1   | 0ae91604-eff2-46cd-81f0-e714b5936ea3 | bao-cao-quy-1.pdf | document   | 22520001     | ACTIVE     |
| 2   | 1f2cb81c-5a08-459a-9bac-2122896a8aaa | version.txt       | text/plain | 22520001     | HISTORICAL |


### **1.3.4 Biểu mẫu 4 và qui định 4**

**BM4: Thuộc Tính ABAC Của Người Dùng (Nguồn tin cậy cho CP-ABE)**  
Attribute Doc ID: _______  
User ID (tham chiếu từ BM1): _______  
Người cập nhật: _______  
Ngày cập nhật: _______  
Phiên bản thuộc tính: _______  

| STT | Thuộc Tính        | Loại   | Giá Trị | Trạng Thái | Ngày hiệu lực |
| --- | ----------------- | ------ | ------- | ---------- | ------------- |
| 1   | department        | enum   |         | active     |               |
| 2   | role              | enum   |         | active     |               |
| 3   | clearance_level   | enum   |         | active     |               |
| 4   | location          | string |         | active     |               |
| 5   | data_access       | enum   |         | active     |               |
| 6   | employment_status | enum   |         | active     |               |

**QĐ4:** Collection `user_attributes` là **nguồn tin cậy duy nhất (Single Source of Truth)** cho tất cả thuộc tính ABAC của người dùng. Các thuộc tính này được sử dụng để:
- **ABAC**: Đánh giá chính sách truy cập tại PDP
- **CP-ABE**: Sinh khóa bí mật người dùng và mã hóa file

Chỉ Super Admin hoặc Admin (trong phạm vi phòng ban) mới có quyền thay đổi thuộc tính. Mỗi thay đổi thuộc tính sẽ:
1. Tăng phiên bản thuộc tính
2. Ghi lại trong audit log (BM12)
3. Kích hoạt quy trình thu hồi và tái cấp khóa CP-ABE (BM13)

**Danh sách thuộc tính bắt buộc** (theo lược đồ BM9):

| Thuộc tính          | Mô tả                | Giá trị cho phép                                 |
| ------------------- | -------------------- | ------------------------------------------------ |
| `department`        | Phòng ban            | hr, finance, it, operations, executive, security |
| `role`              | Chức vụ              | intern, employee, manager, director, ceo         |
| `clearance_level`   | Mức độ bảo mật       | public, confidential, secret, top_secret         |
| `location`          | Địa điểm làm việc    | Chuỗi tự do (e.g., hcm_office, hanoi_office)     |
| `data_access`       | Mức truy cập dữ liệu | basic, advanced, full                            |
| `employment_status` | Trạng thái công việc | active, inactive, terminated, on_leave           |

**Ví dụ:**  
BM4: Thuộc Tính ABAC Của Người Dùng  
Attribute Doc ID: UA22520001  
User ID: 22520001  
Người cập nhật: 21520001 (Super Admin)  
Ngày cập nhật: 08/09/2025  
Phiên bản thuộc tính: 3  

| STT | Thuộc Tính        | Loại   | Giá Trị    | Trạng Thái | Ngày hiệu lực |
| --- | ----------------- | ------ | ---------- | ---------- | ------------- |
| 1   | department        | enum   | it         | active     | 08/09/2025    |
| 2   | role              | enum   | manager    | active     | 08/09/2025    |
| 3   | clearance_level   | enum   | secret     | active     | 08/09/2025    |
| 4   | location          | string | hcm_office | active     | 08/09/2025    |
| 5   | data_access       | enum   | advanced   | active     | 08/09/2025    |
| 6   | employment_status | enum   | active     | active     | 01/01/2025    |

### **1.3.5. Quy định 5 (đã cập nhật - Sinh khóa động, Redis Cache và Disaster Recovery)**

**QĐ5:** 
- **Khóa mã hóa (Keys)**:
    - Khóa bí mật cá nhân (Private Key) được **tạo động (on-the-fly) trên RAM** dựa trên thuộc tính hiện tại của người dùng khi có yêu cầu và lưu vào **Redis Cache** (có thời hạn). Tuyệt đối **KHÔNG** lưu vào DB hay file tĩnh.
    - Master Key (`cpabe_msk.key`) và Public Key (`cpabe_pub.key`) được hệ thống tự động sinh ra trong thư mục `./keys` nếu chưa tồn tại. Tuy nhiên, nếu chuyển sang máy chủ mới, quản trị viên **BẮT BUỘC** phải copy 2 file này sang máy mới. Nếu mất Master Key, toàn bộ file đã mã hóa trước đó sẽ vĩnh viễn không thể khôi phục.
- **Thời hạn sống (TTL)**: Khóa được cache trong một khoảng thời gian ngắn (mặc định 1 giờ).
- **Thu hồi khóa (Revocation)**: Khi thuộc tính người dùng thay đổi hoặc tài khoản bị vô hiệu hóa, hệ thống chỉ cần xóa (invalidate) khóa tương ứng trên Redis. Các yêu cầu sau đó sẽ bị từ chối hoặc phải sinh khóa mới với tập thuộc tính mới nhất.

*(Ghi chú: Biểu mẫu quản lý khóa truyền thống - BM5 - đã được lược bỏ do hệ thống không còn quản lý kho lưu trữ khóa cố định trong DB).*

### **1.3.6 Biểu mẫu 6 và qui định 6**

**BM6: Phiếu Phiên Bản File**  
File ID: _______  
Phiên bản: _______  
Kích thước: _______  
Người tạo: _______  
Ngày tạo: _______  
Mô tả thay đổi: _______  

**QĐ6:** Mỗi file có thể có nhiều phiên bản. Chỉ có phiên bản ACTIVE mới có thể được tải xuống. Các phiên bản HISTORICAL được lưu trữ để audit.

**Ví dụ:**  
BM6: Phiếu Phiên Bản File  
File ID: 0ae91604-eff2-46cd-81f0-e714b5936ea3  
Phiên bản: 1.0.0  
Kích thước: 39 bytes  
Người tạo: 22520001  
Ngày tạo: 08/09/2025  
Mô tả thay đổi: Initial version  


### **1.3.7 Biểu mẫu 7 và qui định 7**

**BM7: Phiếu Chính Sách Truy Cập ABAC**  
Policy ID: _______  
Tên chính sách: _______  
Mô tả: _______  
Tài nguyên: _______  
Hành động: _______  

**Điều kiện thuộc tính người dùng (Subject Attributes):**  
- department: _______  
- role: _______  
- clearance_level: _______  
- employment_status: _______  

**Điều kiện thuộc tính tài nguyên (Resource Attributes):**  
- resource_type: _______  
- classification: _______  
- owner_department: _______  

**Điều kiện thuộc tính môi trường (Environment Attributes):**  
- time_range: _______  
- ip_whitelist: _______  
- device_type: _______  
- location: _______  

Hiệu lực: _______  
Độ ưu tiên: _______  
Chiến lược xử lý xung đột: _______  
Trạng thái: _______  
Ngày tạo: _______  

**QĐ7:** Mỗi chính sách ABAC định nghĩa quy tắc truy cập dựa trên ba loại thuộc tính:
- **Subject Attributes**: Thuộc tính của người dùng (department, role, clearance_level, etc.)
- **Resource Attributes**: Thuộc tính của tài nguyên (loại file, mức phân loại, phòng ban sở hữu)
- **Environment Attributes**: Thuộc tính môi trường (thời gian, IP, thiết bị, vị trí địa lý)

Hệ thống được tích hợp bộ phân tích **Cây cú pháp trừu tượng (Abstract Syntax Tree - AST)**, cho phép các chính sách hỗ trợ **logic boolean lồng nhau phức tạp** bằng dấu ngoặc đơn (ví dụ: `(department == 'it' and role == 'manager') or clearance_level == 'top_secret'`). Điều này đảm bảo tính toán thuộc tính chính xác tuyệt đối cho cả tầng ABAC (Casbin) và tầng mật mã học (CP-ABE). 

Chỉ Super Admin mới có thể tạo/sửa chính sách thông qua giao diện kéo thả logic (Visual UI Builder) hoặc viết code trực tiếp. Có 2 loại hiệu lực: ALLOW và DENY. Độ ưu tiên cao hơn sẽ được áp dụng trước. Chiến lược xử lý xung đột mặc định là **Deny-Override** (nếu có bất kỳ chính sách DENY nào khớp, quyết định cuối cùng là DENY).

**Ví dụ 1: Chính sách dựa trên thuộc tính người dùng (có logic lồng nhau)**  
BM7: Phiếu Chính Sách Truy Cập ABAC  
Policy ID: executives_all_access  
Tên chính sách: Executive All Access  
Mô tả: Executive level access to all resources  
Tài nguyên: shared_files  
Hành động: read, write, delete  
Điều kiện thuộc tính người dùng: `(role == "executive" OR role == "ceo") AND department == "board"`  
Điều kiện thuộc tính tài nguyên: *  
Điều kiện thuộc tính môi trường: *  
Hiệu lực: ALLOW  
Độ ưu tiên: 100  
Chiến lược xử lý xung đột: deny-override  
Trạng thái: active  
Ngày tạo: 08/09/2025  

**Ví dụ 2: Chính sách có điều kiện môi trường**  
BM7: Phiếu Chính Sách Truy Cập ABAC  
Policy ID: finance_office_hours_only  
Tên chính sách: Finance Department Office Hours Access  
Mô tả: Finance staff can only access sensitive files during office hours from office network  
Tài nguyên: shared_files  
Hành động: read, download  
Điều kiện thuộc tính người dùng: department == "finance" AND clearance_level >= "confidential"  
Điều kiện thuộc tính tài nguyên: classification == "financial_report"  
Điều kiện thuộc tính môi trường: time_range == "08:00-18:00" AND ip_whitelist CONTAINS request.ip AND device_type IN ["company_laptop", "company_desktop"]  
Hiệu lực: ALLOW  
Độ ưu tiên: 80  
Chiến lược xử lý xung đột: deny-override  
Trạng thái: active  
Ngày tạo: 08/09/2025  


### **1.3.8 Biểu mẫu 8 và qui định 8**

**BM8: Thông Tin Super Admin**  
ID: _______  
Username: _______  
Email: _______  
Quyền hạn: _______  
Vai trò: _______  
Trạng thái: _______  
Lần đăng nhập cuối: _______  
Ngày tạo: _______  

**QĐ8:** Super Admin có quyền cao nhất trong hệ thống. Có thể quản lý tất cả người dùng, file, chính sách và cấu hình hệ thống. 

**Ví dụ:**  
BM8: Thông Tin Super Admin  
ID: 21520001  
Username: SuperAdmin  
Email: admin@company.com  
Quyền hạn: ['user_management', 'file_management', 'system_config', 'policy_management']  
Vai trò: super_admin  
Trạng thái: active  
Lần đăng nhập cuối: 08/09/2025  
Ngày tạo: 08/09/2025  

### **1.3.9 Biểu mẫu 9 và qui định 9**

**BM9: Lược Đồ Thuộc Tính Khả Dụng**  
Schema ID: _______  
Phiên bản: _______  
Ngày cập nhật: _______  
Người cập nhật: _______  

| STT | Tên Thuộc Tính | Loại | Giá Trị Có Thể | Bắt Buộc |
| --- | -------------- | ---- | -------------- | -------- |
| 1   |                |      |                |          |
| 2   |                |      |                |          |

**QĐ9:** Lược đồ thuộc tính khả dụng định nghĩa các thuộc tính hợp lệ cho người dùng trong hệ thống. Chỉ Super Admin mới có thể thay đổi schema. Mỗi thay đổi được lưu versioning.

**Ví dụ:**  
BM9: Lược Đồ Thuộc Tính Hệ Thống  
Schema ID: user_attribute_schemas  
Phiên bản: 1.0  
Ngày cập nhật: 08/09/2025  
Người cập nhật: 21520001  

| STT | Tên Thuộc Tính    | Loại   | Giá Trị Có Thể                                     | Bắt Buộc |
| --- | ----------------- | ------ | -------------------------------------------------- | -------- |
| 1   | clearance_level   | enum   | [public, confidential, secret, top_secret]         | Có       |
| 2   | department        | enum   | [hr, finance, it, operations, executive, security] | Có       |
| 3   | role              | enum   | [intern, employee, manager, director, ceo]         | Có       |
| 4   | location          | string | Any valid location                                 | Không    |
| 5   | data_access       | enum   | [basic, advanced, full]                            | Có       |
| 6   | employment_status | enum   | [active, inactive, terminated, on_leave]           | Có       |

### **1.3.10 Biểu mẫu 10**

#### Biểu mẫu 10.1

**BM10.1: Báo Cáo Thống Kê Collections Database**  
Ngày: _______  

| STT | Tên Collection  | Số Documents | Ví Dụ Document ID                    |
| --- | --------------- | ------------ | ------------------------------------ |
| 1   | users           | 2            | 21520001, 22520001                   |
| 2   | shared_files    | 2            | 0ae91604-eff2-46cd-81f0-e714b5936ea3 |
| 3   | file_versions   | 3            | 26173b83-09b7-4914-bc04-9e70376298ce |
| 4   | user_attributes | 2            | UA22520001, UA21520001               |
| 5   | access_policies | 30           | SuperAdmin_Full_Access               |
| 6   | super_admin     | 1            | 21520001                             |
| 7   | system_schemas  | 1            | user_attribute_schemas               |
| 8   | access_logs     | 156          | log_20250908_143052_001              |
| 9   | system_config   | 1            | system_config_main                   |

Tổng số collections: 9  
Tổng số documents: 198  

#### Biểu mẫu 10.2

**BM10.2: Báo Cáo Thống Kê Loại Người Dùng**  
Ngày: _______  

| STT | Loại User   | Số Lượng | Tỉ Lệ |
| --- | ----------- | -------- | ----- |
| 1   | super_admin | 1        | 25%   |
| 2   | admin       | 0        | 0%    |
| 3   | data_owner  | 2        | 50%   |
| 4   | data_user   | 1        | 25%   |
| 5   | auditor     | 0        | 0%    |
| 6   | guest       | 0        | 0%    |

Tổng số người dùng: 4  


### **1.3.11 Qui định 11**

**QĐ11:** Super Admin có thể thay đổi các qui định như sau:  
- **QĐ1:** Thay đổi về loại người dùng, thời hạn tài khoản, quyền hạn cơ bản.  
- **QĐ2:** Thay đổi loại file được hỗ trợ, kích thước file tối đa.
- **QĐ4:** Thay đổi các thuộc tính phân quyền: department, clearance_level, role, location, data_access, employment_status.  
- **QĐ6:** Thay đổi chính sách versioning file (ACTIVE, HISTORICAL), số lượng phiên bản tối đa được lưu trữ.
- **QĐ7:** Thay đổi các chính sách ABAC: thêm/sửa/xóa chính sách, thay đổi độ ưu tiên, điều kiện truy cập.
- **QĐ8:** Quản lý tài khoản Super Admin: tạo/vô hiệu hóa tài khoản, thay đổi quyền hạn, reset password.
- **QĐ9:** Cập nhật lược đồ thuộc tính: thêm/sửa/xóa thuộc tính, thay đổi loại dữ liệu, giá trị hợp lệ.
- **QĐ14:** Thay đổi cấu hình hệ thống: CP-ABE, ABAC, Audit, Bảo mật.

---

### **1.3.12 Biểu mẫu 12 và qui định 12**

**BM12: Nhật Ký Truy Cập (Access Logs)**  
Log ID: _______  
Timestamp: _______  
User ID: _______  
Resource ID: _______  
Hành động yêu cầu: _______  
Kết quả PDP: _______  
Chính sách áp dụng: _______  
Thuộc tính người dùng tại thời điểm truy cập: _______  
Thuộc tính môi trường: _______  
Chi tiết lỗi (nếu có): _______  

**QĐ12:** Mọi yêu cầu truy cập (bao gồm cả thành công và thất bại) đều phải được ghi lại trong hệ thống nhật ký. Nhật ký phải lưu đầy đủ thông tin về người dùng, tài nguyên, hành động, quyết định của PDP và các thuộc tính tại thời điểm truy cập. Dữ liệu nhật ký được lưu trữ tối thiểu 12 tháng để phục vụ audit và compliance. Chỉ Super Admin mới có quyền xem và xuất nhật ký.

**Ví dụ:**  
BM12: Nhật Ký Truy Cập  
Log ID: log_20250908_143052_001  
Timestamp: 2025-09-08T14:30:52+07:00  
User ID: 22520001  
Resource ID: 0ae91604-eff2-46cd-81f0-e714b5936ea3  
Hành động yêu cầu: download  
Kết quả PDP: ALLOW  
Chính sách áp dụng: ["it_department_access", "secret_clearance_access"]  
Thuộc tính người dùng: {"department": "it", "role": "manager", "clearance_level": "secret"}  
Thuộc tính môi trường: {"ip": "192.168.1.105", "time": "14:30", "device": "laptop_001"}  
Chi tiết lỗi: null  

---

### **1.3.13 Quy định 13 (Thu hồi khóa thông qua Invalidation)**

**QĐ13:** Khi thuộc tính người dùng thay đổi (thăng chức, chuyển phòng, nghỉ việc) hoặc phát hiện vi phạm bảo mật, hệ thống cần tiến hành thủ tục thu hồi (revocation) khả năng giải mã hiện tại của người dùng đối với các file mã hóa.
Thay vì duy trì một danh sách thu hồi cố định (Key Revocation List Collection) như các hệ thống cũ, cơ chế thu hồi được thiết kế tối giản thông qua việc **xóa cache trên Redis**.
- Cụ thể: Khi có sự thay đổi về thuộc tính hoặc trạng thái tài khoản, hệ thống sẽ gọi phương thức xóa mảng byte chứa khóa CP-ABE (User Private Key) của người dùng đó khỏi Redis cache.
- Hiệu ứng: Ngay lập tức, người dùng mất khả năng giải mã bằng khóa cũ. Nếu người dùng tiếp tục yêu cầu tài liệu, hệ thống bắt buộc phải sinh lại khóa mới dựa trên tập hợp thuộc tính đã được cập nhật mới nhất (nếu người dùng vẫn đủ điều kiện).
*(Do đó, không cần duy trì BM13: Key Revocation List dưới dạng form hay collection)*.

---

### **1.3.14 Biểu mẫu 14 và qui định 14**

**BM14: Cấu Hình Hệ Thống**  
Config ID: _______  
Phiên bản: _______  
Ngày cập nhật: _______  
Người cập nhật: _______  

**Cấu hình CP-ABE:**  
- Thuật toán: _______  
- Độ dài khóa: _______  
- Thời hạn khóa: _______  

**Cấu hình ABAC:**  
- Chiến lược xử lý xung đột mặc định: _______  
- Thời gian cache chính sách: _______  

**Cấu hình Audit:**  
- Thời gian lưu trữ log: _______  
- Tự động xuất báo cáo: _______  

**Cấu hình Bảo mật:**  
- IP whitelist toàn hệ thống: _______  
- Thời gian session: _______  
- Số lần đăng nhập sai tối đa: _______  

**QĐ14:** Cấu hình hệ thống được quản lý tập trung và chỉ Super Admin mới có quyền thay đổi. Mọi thay đổi cấu hình phải được ghi lại lịch sử phiên bản. Cấu hình mặc định được áp dụng khi khởi tạo hệ thống và có thể tùy chỉnh theo nhu cầu doanh nghiệp.

**Ví dụ:**  
BM14: Cấu Hình Hệ Thống  
Config ID: system_config_main  
Phiên bản: 1.2.0  
Ngày cập nhật: 08/09/2025  
Người cập nhật: 21520001  

Cấu hình CP-ABE:  
- Thuật toán: CP-ABE (BSW07)  
- Kết hợp: AES-256-GCM (hybrid encryption)  
- Thời hạn khóa: 365 ngày  

Cấu hình ABAC:  
- Chiến lược xử lý xung đột mặc định: deny-override  
- Thời gian cache chính sách: 300 giây  

Cấu hình Audit:  
- Thời gian lưu trữ log: 12 tháng  
- Tự động xuất báo cáo: hàng tuần  

Cấu hình Bảo mật:  
- IP whitelist: 192.168.0.0/16, 10.0.0.0/8  
- Thời gian session: 8 giờ (quản lý qua HttpOnly Cookie chứa JWT Access/Refresh Token chống XSS)
- Cấu hình Redis: Redis tập trung thông qua django-redis để lưu RAM cho các mã byte của CP-ABE Key
- Số lần đăng nhập sai tối đa: 5  

---

## **1.4. Tổng hợp Bảng Dữ Liệu (Database Tables)**

| STT | Bảng (Table)        | Mô tả                   | Biểu mẫu |
| --- | ------------------- | ----------------------- | -------- |
| 1   | users           | Thông tin người dùng    | BM1      |
| 2   | shared_files    | Metadata file đã mã hóa | BM2      |
| 3   | file_versions   | Phiên bản file          | BM6      |
| 4   | user_attributes | Thuộc tính người dùng   | BM4      |
| 5   | access_policies | Chính sách ABAC         | BM7      |
| 6   | super_admin     | Thông tin Super Admin   | BM8      |
| 7   | system_schemas  | Lược đồ thuộc tính      | BM9      |
| 8   | access_logs     | Nhật ký truy cập        | BM12     |
| 9   | system_config   | Cấu hình hệ thống       | BM14     |

