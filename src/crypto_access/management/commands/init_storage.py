"""
Management command to initialize Supabase Storage buckets
Usage: python manage.py init_storage
"""
from django.core.management.base import BaseCommand
from crypto_access.models_storage import StorageBucket
from crypto_access.storage import get_storage


class Command(BaseCommand):
    help = 'Initialize Supabase Storage buckets'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--create-supabase',
            action='store_true',
            help='Create buckets in Supabase (not just in DB)',
        )
    
    def handle(self, *args, **options):
        """Create default storage buckets"""
        
        # Default buckets configuration
        buckets_config = [
            {
                'name': 'user-avatars',
                'bucket_type': 'public',
                'description': 'User profile pictures',
                'allowed_mime_types': ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
                'max_file_size': 5 * 1024 * 1024,  # 5MB
            },
            {
                'name': 'documents',
                'bucket_type': 'private',
                'description': 'Private user documents (PDFs, Word, etc.)',
                'allowed_mime_types': [
                    'application/pdf',
                    'application/msword',
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'application/vnd.ms-excel',
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                ],
                'max_file_size': 20 * 1024 * 1024,  # 20MB
            },
            {
                'name': 'images',
                'bucket_type': 'public',
                'description': 'Public images (blog posts, media, etc.)',
                'allowed_mime_types': ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml'],
                'max_file_size': 10 * 1024 * 1024,  # 10MB
            },
            {
                'name': 'videos',
                'bucket_type': 'private',
                'description': 'Video files',
                'allowed_mime_types': ['video/mp4', 'video/webm', 'video/ogg'],
                'max_file_size': 100 * 1024 * 1024,  # 100MB
            },
        ]
        
        storage = get_storage()
        create_in_supabase = options['create_supabase']
        
        for config in buckets_config:
            bucket, created = StorageBucket.objects.get_or_create(
                name=config['name'],
                defaults={
                    'bucket_type': config['bucket_type'],
                    'description': config['description'],
                    'allowed_mime_types': config['allowed_mime_types'],
                    'max_file_size': config['max_file_size'],
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Created bucket '{bucket.name}' in database")
                )
                
                if create_in_supabase:
                    try:
                        storage.create_bucket(
                            bucket_name=bucket.name,
                            public=(bucket.bucket_type == 'public'),
                            allowed_mime_types=bucket.allowed_mime_types,
                            file_size_limit=bucket.max_file_size
                        )
                        self.stdout.write(
                            self.style.SUCCESS(f"✓ Created bucket '{bucket.name}' in Supabase")
                        )
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(f"⚠ Failed to create '{bucket.name}' in Supabase: {e}")
                        )
            else:
                self.stdout.write(
                    self.style.WARNING(f"○ Bucket '{bucket.name}' already exists")
                )
        
        self.stdout.write(
            self.style.SUCCESS(f"\n✓ Initialized {len(buckets_config)} storage buckets")
        )
        
        if not create_in_supabase:
            self.stdout.write(
                self.style.WARNING("\n⚠ Use --create-supabase flag to create buckets in Supabase Storage")
            )
