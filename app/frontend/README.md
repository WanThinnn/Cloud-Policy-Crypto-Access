# Frontend - Cloud Firestore Crypto Access

Giao diện người dùng hiện đại được thiết kế theo phong cách **Grid Bento** của Apple với dark mode và các hiệu ứng gradient tinh tế.

## 🎨 Đặc điểm thiết kế

### Bố cục (Layout)
- **CSS Grid** tạo bố cục "Bento Box" với các ô kích thước khác nhau
- Responsive design tương thích với desktop và mobile
- Dashboard với các thẻ thông tin đa dạng (biểu đồ, thống kê, danh sách)

### Màu sắc & Hiệu ứng
- Dark mode chủ đạo tạo cảm giác sang trọng
- Gradient effects mượt mà trên nền và các thẻ
- Soft shadows để làm nổi bật các thành phần
- Hiệu ứng hover và animation tinh tế

### Typography
- Font chữ Inter (hoặc SF Pro fallback)
- Hệ thống phân cấp rõ ràng cho tiêu đề và nội dung
- Kích thước responsive cho mọi thiết bị

## 📁 Cấu trúc thư mục

```
frontend/
├── static/
│   ├── css/
│   │   ├── base.css          # Styles chung cho toàn bộ ứng dụng
│   │   ├── home.css          # Styles cho trang dashboard
│   │   └── detail.css        # Styles cho trang chi tiết
│   ├── js/
│   │   ├── base.js           # JavaScript chung
│   │   ├── home.js           # JavaScript cho dashboard
│   │   └── detail.js         # JavaScript cho trang chi tiết
│   └── assets/               # Hình ảnh, icons, fonts
└── templates/
    ├── base.html             # Template gốc
    ├── home.html             # Trang dashboard
    ├── detail.html           # Template chi tiết (tái sử dụng)
    ├── files.html            # Danh sách files
    └── users.html            # Danh sách users
```

## 🚀 Cách chạy Demo

1. **Cài đặt dependencies:**
   ```bash
   pip install flask
   ```

2. **Chạy demo server:**
   ```bash
   cd /path/to/your/project
   python frontend_demo.py
   ```

3. **Mở trình duyệt:**
   - Truy cập: `http://localhost:5000`
   - Dashboard sẽ hiển thị với Grid Bento layout

## 📄 Các trang có sẵn

### 🏠 Dashboard (`/`)
- Grid Bento layout với các thẻ thông tin
- Thống kê hệ thống real-time
- Quick actions để truy cập nhanh các chức năng
- Biểu đồ và progress bars

### 📁 Files (`/files`)
- Danh sách files với card layout
- Tìm kiếm và lọc files
- Thông tin chi tiết từng file

### 👥 Users (`/users`) 
- Danh sách users với avatar và thông tin
- Lọc theo role và status
- Thống kê hoạt động của user

### 🔍 Detail Pages (`/files/{id}`, `/users/{id}`)
- Template tái sử dụng cho trang chi tiết
- Tab navigation (Overview, Details, Permissions, History)
- Sidebar với quick actions và properties
- Activity timeline

## 🎛️ Tính năng JavaScript

### Base Functionality
- Mobile menu responsive
- Flash messages tự động đóng
- Loading states cho forms và buttons
- Toast notifications
- Tooltips
- Copy to clipboard
- API request helpers

### Dashboard Features
- Animated statistics counters
- Interactive charts (mock data)
- Progress bars với animation
- Quick action handling
- Data refresh functionality

### Detail Pages
- Tab switching
- AJAX form submissions
- Modal handling
- Table responsive
- Data filtering và search

## 🎨 Customization

### CSS Variables
File `base.css` định nghĩa các CSS custom properties:

```css
:root {
  /* Colors */
  --primary-bg: #000000;
  --card-bg: rgba(255, 255, 255, 0.05);
  --text-primary: #ffffff;
  
  /* Gradients */
  --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  
  /* Spacing */
  --space-md: 1rem;
  --space-lg: 1.5rem;
  
  /* Typography */
  --font-primary: 'Inter', sans-serif;
  --font-size-base: 1rem;
}
```

### Thêm trang mới
1. Tạo CSS file mới trong `static/css/`
2. Tạo JS file mới trong `static/js/`
3. Tạo template mới extend từ `base.html`
4. Thêm route trong Flask app

## 🔧 Tích hợp với Backend

### Template Variables
Templates sử dụng các biến từ Flask:

```python
return render_template('detail.html',
    item_title="File Name",
    item_description="Description", 
    item_id="123",
    item_owner="user@email.com",
    # ... more variables
)
```

### API Endpoints
JavaScript sử dụng các API endpoints:

```javascript
// Trong base.js
const response = await this.apiRequest('/api/files', {
    method: 'POST',
    body: JSON.stringify(data)
});
```

### Flash Messages
Flask flash messages hiển thị tự động:

```python
flash('Success message', 'success')
flash('Error message', 'error') 
flash('Warning message', 'warning')
flash('Info message', 'info')
```

## 📱 Responsive Design

- **Desktop (> 1200px):** Full grid layout với 4 cột
- **Tablet (768px - 1200px):** 3 cột, layout điều chỉnh
- **Mobile (< 768px):** 1 cột, menu hamburger, touch-friendly

## ⚡ Performance

- CSS và JS được tối ưu hóa
- Lazy loading cho animations
- Efficient DOM manipulation
- Minimal external dependencies
- Backdrop filters cho glass effect

## 🔒 Security Features

- CSRF token handling
- XSS protection trong templates
- Secure API request headers
- Input validation trên client

## 🎯 Browser Support

- Chrome/Edge (latest)
- Firefox (latest) 
- Safari (latest)
- IE 11+ (limited support)

## 📝 Notes

- Templates được thiết kế để tái sử dụng maximum
- CSS sử dụng modern features (Grid, Flexbox, CSS Variables)
- JavaScript ES6+ với fallbacks
- Accessibility được xem xét trong thiết kế
- SEO-friendly với semantic HTML

Giao diện này cung cấp foundation hoàn chỉnh cho ứng dụng Cloud Firestore Crypto Access với thiết kế hiện đại và user experience tốt!
