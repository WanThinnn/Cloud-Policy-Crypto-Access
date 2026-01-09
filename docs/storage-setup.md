# Supabase Storage Setup Guide

## 1. Lấy Supabase API Keys

Vào [Supabase Dashboard](https://okiygqlobzyfptqxzafc.supabase.co):
- **Settings** → **API**
- Copy:
  - `Project URL` → `SUPABASE_URL`
  - `anon public` key → `SUPABASE_KEY`
  - `service_role` key → `SUPABASE_SERVICE_KEY` (chỉ dùng server-side)

## 2. Cập nhật `.env`

```bash
# Supabase Storage Configuration
SUPABASE_URL=https://okiygqlobzyfptqxzafc.supabase.co
SUPABASE_KEY=your-anon-public-key-here
SUPABASE_SERVICE_KEY=your-service-role-key-here
```

## 3. Chạy Migrations

```bash
cd src
python manage.py migrate
```

## 4. Khởi tạo Storage Buckets

### Chỉ tạo trong database:
```bash
python manage.py init_storage
```

### Tạo cả trong Supabase Storage:
```bash
python manage.py init_storage --create-supabase
```

## 5. Bucket Types

### Private Buckets (Mặc định)
- ✅ Dùng cho: User documents, sensitive files
- 🔒 Access: Requires authentication (RLS policies)
- 📦 Download: Via signed URLs (temporary)
- 🔑 Use cases: PDFs, invoices, private documents

### Public Buckets
- ✅ Dùng cho: Avatars, blog images, public media
- 🌐 Access: Anyone with URL can access
- ⚡ Performance: Cached, faster loading
- 📷 Use cases: Profile pictures, public images

## 6. API Endpoints

### List Buckets
```http
GET /api/storage/buckets/
Authorization: Bearer <token>
```

### Upload File
```http
POST /api/storage/files/upload/
Content-Type: multipart/form-data
Authorization: Bearer <token>

Body:
- file: <file>
- bucket_name: "documents"
- description: "User contract"
- tags: ["contract", "important"]
- is_public: false
```

### List Files
```http
GET /api/storage/files/?bucket=documents&type=pdf
Authorization: Bearer <token>
```

### Download File
```http
GET /api/storage/files/<id>/download/
Authorization: Bearer <token>
```

### Create Signed URL (Private files)
```http
POST /api/storage/files/<id>/create_signed_url/
Authorization: Bearer <token>

Body:
{
  "expires_in": 3600  // seconds
}
```

### Delete File
```http
DELETE /api/storage/files/<id>/delete_from_storage/
Authorization: Bearer <token>
```

### Storage Stats
```http
GET /api/storage/files/stats/
Authorization: Bearer <token>
```

## 7. Python Usage

### Upload file
```python
from crypto_access.storage import get_storage

storage = get_storage()

# Upload
with open('document.pdf', 'rb') as f:
    storage.upload_file(
        bucket_name='documents',
        file_path='user123/contract.pdf',
        file_data=f.read(),
        content_type='application/pdf'
    )

# Get public URL (public bucket only)
url = storage.get_public_url('images', 'blog/header.jpg')

# Get signed URL (private bucket)
signed_url = storage.create_signed_url('documents', 'user123/contract.pdf', expires_in=3600)

# Download
data = storage.download_file('documents', 'user123/contract.pdf')

# Delete
storage.delete_file('documents', ['user123/contract.pdf'])
```

## 8. Django Views Usage

```python
from crypto_access.models_storage import StorageBucket, UploadedFile

# Get all PDF files
pdfs = UploadedFile.objects.filter(file_type='pdf')

# Get user's files
my_files = UploadedFile.objects.filter(uploaded_by=request.user)

# Get files in bucket
docs = UploadedFile.objects.filter(bucket__name='documents')
```

## 9. Default Buckets

| Bucket | Type | Max Size | Allowed Types |
|--------|------|----------|---------------|
| `user-avatars` | Public | 5MB | Images (jpg, png, gif, webp) |
| `documents` | Private | 20MB | PDF, Word, Excel |
| `images` | Public | 10MB | Images (jpg, png, gif, webp, svg) |
| `videos` | Private | 100MB | Video (mp4, webm, ogg) |

## 10. Security Notes

⚠️ **NEVER commit** `SUPABASE_SERVICE_KEY` to git
- Service role key has full admin access
- Only use server-side
- Use anon key for client-side apps

## 11. RLS Policies (Row Level Security)

Trong Supabase Dashboard → **Storage** → chọn bucket → **Policies**:

### Allow authenticated users to upload:
```sql
CREATE POLICY "Authenticated users can upload"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'documents');
```

### Allow users to view own files:
```sql
CREATE POLICY "Users can view own files"
ON storage.objects FOR SELECT
TO authenticated
USING (bucket_id = 'documents' AND (storage.foldername(name))[1] = auth.uid()::text);
```

## 12. Testing

```bash
# Test upload via curl
curl -X POST http://localhost:8000/api/storage/files/upload/ \
  -H "Authorization: Bearer <token>" \
  -F "file=@test.pdf" \
  -F "bucket_name=documents" \
  -F "description=Test document"
```

## Troubleshooting

### Lỗi: "Bucket not found"
→ Chạy `python manage.py init_storage --create-supabase`

### Lỗi: "Invalid Supabase credentials"
→ Check SUPABASE_URL và SUPABASE_KEY trong `.env`

### Lỗi: "Permission denied"
→ Check RLS policies trong Supabase dashboard

### File không tải lên được
→ Check `allowed_mime_types` và `max_file_size` của bucket
