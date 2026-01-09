"""
Upload sample files to Supabase storage
Run via: python manage.py upload_sample_files
"""

import os
from django.core.management.base import BaseCommand
from django.conf import settings
from crypto_access.services.storage_service import get_storage_service


class Command(BaseCommand):
    help = 'Upload sample files to Supabase storage'
    
    def handle(self, *args, **options):
        self.stdout.write('Uploading sample files to Supabase...\n')
        
        # Initialize storage client
        try:
            storage = get_storage_service()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to initialize storage: {e}'))
            return
        
        # Sample files directory
        sample_dir = os.path.join(settings.BASE_DIR, 'sample_files')
        
        if not os.path.exists(sample_dir):
            self.stdout.write(self.style.ERROR(f'Sample files directory not found: {sample_dir}'))
            return
        
        uploaded = 0
        bucket_name = 'documents'
        
        # Ensure bucket exists
        try:
            storage.create_bucket(bucket_name, public=False)
            self.stdout.write(f'Created bucket: {bucket_name}')
        except Exception as e:
            self.stdout.write(f'Bucket exists or error: {e}')
        
        # Walk through sample_files directory
        for root, dirs, files in os.walk(sample_dir):
            for filename in files:
                if filename.endswith('.md'):
                    local_path = os.path.join(root, filename)
                    
                    # Calculate relative path from sample_files
                    rel_path = os.path.relpath(local_path, sample_dir)
                    # Convert to forward slashes for storage
                    storage_path = rel_path.replace('\\', '/')
                    
                    try:
                        with open(local_path, 'rb') as f:
                            content = f.read()
                        
                        # Upload to Supabase
                        result = storage.upload_file(
                            bucket_name=bucket_name,
                            file_path=storage_path,
                            file_data=content,
                            content_type='text/markdown',
                            upsert=True
                        )
                        
                        self.stdout.write(f'  ✓ Uploaded: {storage_path}')
                        uploaded += 1
                        
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'  ✗ Failed {storage_path}: {e}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Uploaded {uploaded} files to Supabase'))
