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

    # Create Superuser if not exists
    admin_username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
    admin_email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@cyberfortress.local')
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
