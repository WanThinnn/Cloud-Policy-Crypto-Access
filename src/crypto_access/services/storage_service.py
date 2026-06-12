"""
Supabase Storage Service
Handles file uploads/downloads to Supabase Storage buckets
"""
import os
from typing import Optional, List, Dict, Any
from django.conf import settings
from supabase import create_client, Client
import logging

logger = logging.getLogger('crypto_access.storage')


class SupabaseStorageService:
    """
    Service class for Supabase Storage operations
    
    Bucket Types:
    - Private: Requires authentication, uses RLS policies
    - Public: Publicly accessible, cached for better performance
    """
    
    def __init__(self):
        supabase_url = getattr(settings, 'SUPABASE_URL', None) or os.environ.get('SUPABASE_URL')
        supabase_key = getattr(settings, 'SUPABASE_SERVICE_KEY', None) or os.environ.get('SUPABASE_SERVICE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        
        self.client: Client = create_client(supabase_url, supabase_key)
        self.storage = self.client.storage
    
    def create_bucket(
        self, 
        bucket_name: str, 
        public: bool = False,
        allowed_mime_types: Optional[List[str]] = None,
        file_size_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a new storage bucket
        
        Args:
            bucket_name: Name of the bucket
            public: True for public bucket, False for private (default)
            allowed_mime_types: List of allowed MIME types (e.g., ['image/png', 'application/pdf'])
            file_size_limit: Max file size in bytes (e.g., 5242880 for 5MB)
        
        Returns:
            Dict with bucket info
        """
        try:
            options = {
                "public": public,
            }
            
            if allowed_mime_types:
                options["allowedMimeTypes"] = allowed_mime_types
            
            if file_size_limit:
                options["fileSizeLimit"] = file_size_limit
            
            result = self.storage.create_bucket(id=bucket_name, name=bucket_name, options=options)
            logger.info(f"Bucket '{bucket_name}' created successfully (public={public})")
            return result
        except Exception as e:
            logger.error(f"Failed to create bucket '{bucket_name}': {e}")
            raise
    
    def list_buckets(self) -> List[Dict[str, Any]]:
        """List all storage buckets"""
        try:
            buckets = self.storage.list_buckets()
            return buckets
        except Exception as e:
            logger.error(f"Failed to list buckets: {e}")
            raise
    
    def upload_file(
        self,
        bucket_name: str,
        file_path: str,
        file_data: bytes,
        content_type: Optional[str] = None,
        upsert: bool = False
    ) -> Dict[str, Any]:
        """
        Upload file to bucket
        
        Args:
            bucket_name: Target bucket name
            file_path: Path within bucket (e.g., 'avatars/user123.jpg')
            file_data: File content as bytes
            content_type: MIME type (e.g., 'image/jpeg', 'application/pdf')
            upsert: If True, overwrite existing file
        
        Returns:
            Dict with upload result
        """
        try:
            options = {}
            if content_type:
                options["content-type"] = content_type
            if upsert:
                options["upsert"] = "true"
            
            result = self.storage.from_(bucket_name).upload(
                file_path,
                file_data,
                file_options=options
            )
            logger.info(f"File uploaded: {bucket_name}/{file_path}")
            return result
        except Exception as e:
            logger.error(f"Failed to upload file to {bucket_name}/{file_path}: {e}")
            raise
    
    def download_file(self, bucket_name: str, file_path: str) -> bytes:
        """
        Download file from bucket
        
        Args:
            bucket_name: Source bucket name
            file_path: Path within bucket
        
        Returns:
            File content as bytes
        """
        try:
            result = self.storage.from_(bucket_name).download(file_path)
            logger.info(f"File downloaded: {bucket_name}/{file_path}")
            return result
        except Exception as e:
            logger.error(f"Failed to download file from {bucket_name}/{file_path}: {e}")
            raise
    
    def get_public_url(self, bucket_name: str, file_path: str) -> str:
        """
        Get public URL for file (works only for public buckets)
        
        Args:
            bucket_name: Bucket name (must be public)
            file_path: Path within bucket
        
        Returns:
            Public URL string
        """
        try:
            result = self.storage.from_(bucket_name).get_public_url(file_path)
            return result
        except Exception as e:
            logger.error(f"Failed to get public URL for {bucket_name}/{file_path}: {e}")
            raise
    
    def create_signed_url(
        self,
        bucket_name: str,
        file_path: str,
        expires_in: int = 3600
    ) -> str:
        """
        Create temporary signed URL for private bucket file
        
        Args:
            bucket_name: Bucket name
            file_path: Path within bucket
            expires_in: URL expiration time in seconds (default: 1 hour)
        
        Returns:
            Signed URL string
        """
        try:
            result = self.storage.from_(bucket_name).create_signed_url(
                file_path,
                expires_in
            )
            return result.get('signedURL', '')
        except Exception as e:
            logger.error(f"Failed to create signed URL for {bucket_name}/{file_path}: {e}")
            raise
    
    def delete_file(self, bucket_name: str, file_paths: List[str]) -> Dict[str, Any]:
        """
        Delete file(s) from bucket
        
        Args:
            bucket_name: Bucket name
            file_paths: List of file paths to delete
        
        Returns:
            Dict with deletion result
        """
        try:
            result = self.storage.from_(bucket_name).remove(file_paths)
            logger.info(f"Files deleted from {bucket_name}: {file_paths}")
            return result
        except Exception as e:
            logger.error(f"Failed to delete files from {bucket_name}: {e}")
            raise
    
    def list_files(
        self,
        bucket_name: str,
        path: str = "",
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List files in bucket
        
        Args:
            bucket_name: Bucket name
            path: Folder path within bucket (default: root)
            limit: Max number of files to return
            offset: Number of files to skip
        
        Returns:
            List of file metadata dicts
        """
        try:
            result = self.storage.from_(bucket_name).list(
                path=path,
                options={"limit": limit, "offset": offset}
            )
            return result
        except Exception as e:
            logger.error(f"Failed to list files in {bucket_name}/{path}: {e}")
            raise
    
    def move_file(
        self,
        bucket_name: str,
        from_path: str,
        to_path: str
    ) -> Dict[str, Any]:
        """
        Move/rename file within bucket
        
        Args:
            bucket_name: Bucket name
            from_path: Current file path
            to_path: New file path
        
        Returns:
            Dict with move result
        """
        try:
            result = self.storage.from_(bucket_name).move(from_path, to_path)
            logger.info(f"File moved: {bucket_name}/{from_path} -> {to_path}")
            return result
        except Exception as e:
            logger.error(f"Failed to move file in {bucket_name}: {e}")
            raise
    
    def copy_file(
        self,
        bucket_name: str,
        from_path: str,
        to_path: str
    ) -> Dict[str, Any]:
        """
        Copy file within bucket
        
        Args:
            bucket_name: Bucket name
            from_path: Source file path
            to_path: Destination file path
        
        Returns:
            Dict with copy result
        """
        try:
            result = self.storage.from_(bucket_name).copy(from_path, to_path)
            logger.info(f"File copied: {bucket_name}/{from_path} -> {to_path}")
            return result
        except Exception as e:
            logger.error(f"Failed to copy file in {bucket_name}: {e}")
            raise


# Singleton instance
_storage_service_instance = None

def get_storage_service() -> SupabaseStorageService:
    """Get or create SupabaseStorageService singleton instance"""
    global _storage_service_instance
    if _storage_service_instance is None:
        _storage_service_instance = SupabaseStorageService()
    return _storage_service_instance
