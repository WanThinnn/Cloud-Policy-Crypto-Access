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
        vault_service.put_secret('MASTER_FIELD_ENCRYPTION_KEY', key_b64)
        print("Successfully stored MASTER_FIELD_ENCRYPTION_KEY in Vault.")
    else:
        print("Generating a new random MASTER_FIELD_ENCRYPTION_KEY and storing in Vault...")
        import base64
        # Generate a massive 12288-bit (1536-byte) master key for extreme security
        new_key = base64.urlsafe_b64encode(os.urandom(1536)).decode('utf-8')
        vault_service.put_secret('MASTER_FIELD_ENCRYPTION_KEY', new_key)
        print("Successfully generated and stored MASTER_FIELD_ENCRYPTION_KEY in Vault.")
        
        # Backup the generated key to config/keys directory
        key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'keys', 'master_field_encryption.key')
        try:
            os.makedirs(os.path.dirname(key_path), exist_ok=True)
            with open(key_path, 'w') as f:
                f.write(new_key)
            print(f"\n\033[93m[!] IMPORTANT: A backup of the MASTER_FIELD_ENCRYPTION_KEY has been saved to: {key_path}\033[0m")
            print("\033[93m[!] Please store this key securely! If Vault loses data, you will need this key to decrypt your database fields.\033[0m\n")
        except Exception as e:
            print(f"Warning: Failed to save backup key to {key_path}: {e}")

    # Create Superuser if not exists
    admin_username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
    admin_email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.local')
    admin_password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')

    if not User.objects.filter(username=admin_username).exists():
        print(f"Creating superuser: {admin_username}")
        user = User.objects.create_superuser(
            username=admin_username,
            email=admin_email,
            password=admin_password
        )
        
        # Get super_admin UserType reference
        from crypto_access.models import UserType
        super_admin_type = UserType.objects.filter(code='super_admin').first()

        # Create user profile
        UserProfile.objects.create(
            user=user,
            phone='0123456789',
            address='CyberFortress HQ',
            bio='System Administrator',
            user_type='super_admin',
            user_type_ref=super_admin_type
        )
        print("Superuser created successfully.")
    else:
        print("Superuser already exists.")
        
    # Create default storage bucket
    from crypto_access.models.storage import StorageBucket
    bucket, created = StorageBucket.objects.get_or_create(
        name='documents',
        defaults={
            'description': 'Default bucket for secure documents',
            'bucket_type': 'private'
        }
    )
    if created:
        print("Created default StorageBucket: 'documents'")
    else:
        print("StorageBucket 'documents' already exists.")

    print("Data Initialization Complete.")

if __name__ == '__main__':
    init()
