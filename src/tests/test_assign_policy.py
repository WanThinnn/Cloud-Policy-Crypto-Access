import os
import django
import sys
import uuid

sys.path.append(r"d:\Documents\UIT\Nam_4\Cloud-Firestore-Crypto-Access\src")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User
from crypto_access.models import UploadedFile, StorageBucket, AccessPolicy, FileAccessPolicy
from crypto_access.services.storage_service import get_storage_service
from crypto_access.services.cpabe_service import cpabe_service
from crypto_access.services.casbin_service import casbin_service
from django.test import RequestFactory
from crypto_access.views.storage import UploadedFileViewSet

def test_assign():
    print("--- Testing Retroactive Encryption ---")
    
    # 1. Setup mock data
    admin = User.objects.get(username="superadmin")
    bucket = StorageBucket.objects.get(name="documents")
    storage = get_storage_service()
    
    # 2. Upload a dummy plaintext file to Supabase directly
    unique_path = f"test_retro/{uuid.uuid4()}.txt"
    plaintext = b"This is unencrypted secret data!"
    print(f"Uploading plaintext file to {unique_path}...")
    storage.upload_file(bucket.name, unique_path, plaintext, content_type="text/plain")
    
    # 3. Create DB record for the file
    file_record = UploadedFile.objects.create(
        bucket=bucket,
        file_path=unique_path,
        file_name="retro_test.txt",
        file_type="document",
        mime_type="text/plain",
        file_size=len(plaintext),
        uploaded_by=admin
    )
    
    # 4. Try assign_policy via the API view method
    # We will just construct a mock request
    policy = AccessPolicy.objects.get(name="IT Department Read Access")
    print(f"Policy to assign: {policy.name} (CP-ABE: {policy.cpabe_policy})")
    
    from rest_framework.test import APIRequestFactory, force_authenticate
    
    factory = APIRequestFactory()
    request = factory.post('/api/storage/files/assign_policy/', {
        'file_path': unique_path,
        'bucket_name': 'documents',
        'target_type': 'file',
        'policy_id': policy.id
    }, format='json')
    force_authenticate(request, user=admin)
    
    view = UploadedFileViewSet.as_view({'post': 'assign_policy'})
    response = view(request)
    
    print(f"Assign Policy API Response Status: {response.status_code}")
    if response.status_code != 201:
        print(response.data)
        return
        
    # 5. Verify the file on Supabase is now encrypted
    print("\nDownloading file from Supabase to verify encryption...")
    downloaded_data = storage.download_file(bucket.name, unique_path)
    
    if downloaded_data == plaintext:
        print("❌ FAILED: File is still plaintext!")
    else:
        print("✅ SUCCESS: File content is different from plaintext (presumably encrypted)!")
        print(f"Encrypted data prefix: {downloaded_data[:20]}")
        
    # Cleanup
    print("\nCleaning up...")
    storage.delete_file(bucket.name, [unique_path])
    file_record.delete()
    # FileAccessPolicy is cascade deleted or we can delete it
    FileAccessPolicy.objects.filter(uploaded_file=file_record).delete()
    print("Done.")

if __name__ == "__main__":
    test_assign()
