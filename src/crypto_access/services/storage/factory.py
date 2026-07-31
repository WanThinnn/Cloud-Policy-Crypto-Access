import os
from django.conf import settings
from .interface import IStorageService

# Singleton instance
_storage_service_instance = None

def get_storage_service() -> IStorageService:
    """
    Factory function to get the appropriate Storage Service Adapter based on environment variables.
    Supported vendors: 'supabase', 'aws_s3', 'google_cloud_storage', 'local_disk'
    """
    global _storage_service_instance
    if _storage_service_instance is not None:
        return _storage_service_instance

    vendor = getattr(settings, 'STORAGE_VENDOR', None) or os.environ.get('STORAGE_VENDOR', 'supabase').lower()

    if vendor == 'supabase':
        from .adapters.supabase import SupabaseStorageAdapter
        _storage_service_instance = SupabaseStorageAdapter()
    elif vendor == 'aws_s3':
        from .adapters.s3 import S3StorageAdapter
        _storage_service_instance = S3StorageAdapter()
    elif vendor == 'google_cloud_storage':
        from .adapters.gcs import GCSStorageAdapter
        _storage_service_instance = GCSStorageAdapter()
    elif vendor == 'local_disk':
        from .adapters.local import LocalStorageAdapter
        _storage_service_instance = LocalStorageAdapter()
    else:
        # Fallback to Supabase if unknown vendor
        from .adapters.supabase import SupabaseStorageAdapter
        _storage_service_instance = SupabaseStorageAdapter()

    return _storage_service_instance
