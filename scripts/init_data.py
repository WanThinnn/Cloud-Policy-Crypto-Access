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
        
        # Create user profile
        UserProfile.objects.create(
            user=user,
            phone='0123456789',
            address='CyberFortress HQ',
            bio='System Administrator'
        )
        print("Superuser created successfully.")
    else:
        print("Superuser already exists.")

    print("Data Initialization Complete.")

if __name__ == '__main__':
    init()
