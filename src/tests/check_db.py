import os
import django
import sys

sys.path.append(r"d:\Documents\UIT\Nam_4\Cloud-Policy-Crypto-Access\src")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from crypto_access.models import UploadedFile, FileAccessPolicy, AccessPolicy
from django.utils import timezone
from datetime import timedelta

print("--- LATEST UPLOADED FILES ---")
files = UploadedFile.objects.order_by('-uploaded_at')[:5]
for f in files:
    print(f"[{f.uploaded_at}] {f.file_name} ({f.file_path}) by {f.uploaded_by.username if f.uploaded_by else 'None'}")
    
print("\n--- LATEST FILE ACCESS POLICIES ---")
faps = FileAccessPolicy.objects.order_by('-assigned_at')[:5]
for fap in faps:
    target = fap.uploaded_file.file_name if fap.uploaded_file else fap.folder_path
    cpabe = fap.policy.cpabe_policy if fap.policy else 'NO_POLICY'
    print(f"[{fap.assigned_at}] Policy: {fap.policy.name} (CP-ABE: {cpabe}) -> Target: {target}")

