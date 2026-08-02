import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from django.contrib.auth.models import User
from crypto_access.models import UserProfile
from django.core.management import call_command

def init():
    print("Initializing Database Data...")

    # Push MASTER_FIELD_ENCRYPTION_KEY to Vault if it exists in settings
    from django.conf import settings
    from crypto_access.services.vault_service import vault_service
    key_b64 = getattr(settings, 'MASTER_FIELD_ENCRYPTION_KEY', None)
    existing = vault_service.get_secret('MASTER_FIELD_ENCRYPTION_KEY')
    
    if existing:
        print("MASTER_FIELD_ENCRYPTION_KEY already exists in Vault.")
    elif key_b64:
        print("Pushing MASTER_FIELD_ENCRYPTION_KEY from settings to Vault KV Engine...")
        if vault_service.put_secret('MASTER_FIELD_ENCRYPTION_KEY', key_b64):
            print("Successfully stored MASTER_FIELD_ENCRYPTION_KEY in Vault.")
        else:
            print("\033[91m[ERROR] Failed to store MASTER_FIELD_ENCRYPTION_KEY in Vault!\033[0m")
            print("Setting MASTER_FIELD_ENCRYPTION_KEY as environment variable as fallback...")
            os.environ['MASTER_FIELD_ENCRYPTION_KEY'] = key_b64
    else:
        print("Generating a new random MASTER_FIELD_ENCRYPTION_KEY and storing in Vault...")
        import base64
        # Generate a massive 12288-bit (1536-byte) master key for extreme security
        new_key = base64.urlsafe_b64encode(os.urandom(1536)).decode('utf-8')
        if vault_service.put_secret('MASTER_FIELD_ENCRYPTION_KEY', new_key):
            print("Successfully generated and stored MASTER_FIELD_ENCRYPTION_KEY in Vault.")
            print("\033[92m[✓] Key is stored securely in Vault (encrypted at rest by Vault's barrier key).\033[0m")
        else:
            print("\033[91m[ERROR] Failed to store MASTER_FIELD_ENCRYPTION_KEY in Vault!\033[0m")
            print("Setting MASTER_FIELD_ENCRYPTION_KEY as environment variable as fallback...")
            os.environ['MASTER_FIELD_ENCRYPTION_KEY'] = new_key

    # Create Superuser if not exists
    super_admin_username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'super_admin')
    super_admin_email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'super_admin@example.local')
    super_admin_password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'super_admin123')

    if not User.objects.filter(username=super_admin_username).exists():
        print(f"Creating superuser: {super_admin_username}")
        user = User.objects.create_superuser(
            username=super_admin_username,
            email=super_admin_email,
            password=super_admin_password
        )
        
        # Get super_admin UserType reference
        from crypto_access.models import UserType
        super_admin_type = UserType.objects.filter(code='super_admin').first()

        # Create user profile
        UserProfile.objects.create(
            user=user,
            full_name='Super Administrator',
            phone='0123456789',
            address='CyberFortress HQ',
            bio='System Administrator',
            user_type='super_admin',
            user_type_ref=super_admin_type
        )
        print("Superuser created successfully.")
        print(f"\033[93m[!] SuperAdmin account: {super_admin_username} | Password: {super_admin_password}\033[0m")
        print("\033[93m[!] WARNING: Please log in and change your password immediately!\033[0m\n")
    else:
        print("Superuser already exists.")
        print(f"\033[93m[!] SuperAdmin account: {super_admin_username} | Password: {super_admin_password} (if not changed)\033[0m")
        print("\033[93m[!] WARNING: Please log in and change your password immediately!\033[0m\n")
        
    # Create default storage bucket
    # pyrefly: ignore [missing-import]
    from crypto_access.models.storage import StorageBucket
    bucket, created = StorageBucket.objects.get_or_create(
        name='documents',
        defaults={
            'description': 'Default bucket for secure documents',
            'bucket_type': 'private'
        }
    )
    if created:
        print("Created default StorageBucket record: 'documents'")
    else:
        print("StorageBucket record 'documents' already exists.")
        
    # Also attempt to physically create the bucket on the storage provider
    try:
        from crypto_access.services.storage import get_storage_service
        storage = get_storage_service()
        storage.create_bucket('documents', public=False)
        print("Physically created bucket 'documents' on the storage provider (if it didn't exist).")
    except Exception as e:
        print(f"Note: Could not physically create bucket (it may already exist or lack permissions): {e}")

    print("Data Initialization Complete.")

if __name__ == '__main__':
    init()
