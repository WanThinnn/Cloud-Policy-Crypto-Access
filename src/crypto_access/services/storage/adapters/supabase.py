import os
import logging
from typing import Optional, List, Dict, Any
from django.conf import settings
from supabase import create_client, Client
from ..interface import IStorageService

logger = logging.getLogger('crypto_access.storage')

class SupabaseStorageAdapter(IStorageService):
    """
    Supabase Implementation for Storage operations
    """
    
    def __init__(self):
        supabase_url = getattr(settings, 'SUPABASE_URL', None) or os.environ.get('SUPABASE_URL')
        supabase_key = getattr(settings, 'SUPABASE_SERVICE_KEY', None) or os.environ.get('SUPABASE_SERVICE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set for SupabaseStorageAdapter")
        
        self.client: Client = create_client(supabase_url, supabase_key)
        self.storage = self.client.storage

    def create_bucket(
        self, 
        bucket_name: str, 
        public: bool = False,
        allowed_mime_types: Optional[List[str]] = None,
        file_size_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        try:
            options = {
                "public": public,
            }
            if allowed_mime_types:
                options["allowedMimeTypes"] = allowed_mime_types
            if file_size_limit:
                options["fileSizeLimit"] = file_size_limit
            
            result = self.storage.create_bucket(id=bucket_name, name=bucket_name, options=options)
            logger.info(f"Bucket '{bucket_name}' created successfully (public={public}) via Supabase")
            return result
        except Exception as e:
            logger.error(f"Failed to create bucket '{bucket_name}' via Supabase: {e}")
            raise
    
    def list_buckets(self) -> List[Dict[str, Any]]:
        try:
            buckets = self.storage.list_buckets()
            return buckets
        except Exception as e:
            logger.error(f"Failed to list buckets via Supabase: {e}")
            raise
    
    def upload_file(
        self,
        bucket_name: str,
        file_path: str,
        file_data: bytes,
        content_type: Optional[str] = None,
        upsert: bool = False,
        user: Optional[Any] = None
    ) -> Dict[str, Any]:
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
            
            extra = {}
            user_msg = ""
            if user and hasattr(user, 'username'):
                extra = {"user.name": user.username, "user.id": getattr(user, 'id', '')}
                user_msg = f" by user {user.username}"
                
            logger.info(f"File uploaded to Supabase: {bucket_name}/{file_path}{user_msg}", extra=extra)
            return result
        except Exception as e:
            logger.error(f"Failed to upload file to Supabase {bucket_name}/{file_path}: {e}")
            raise
    
    def download_file(self, bucket_name: str, file_path: str, user: Optional[Any] = None) -> bytes:
        try:
            result = self.storage.from_(bucket_name).download(file_path)
            
            extra = {}
            user_msg = ""
            if user and hasattr(user, 'username'):
                extra = {"user.name": user.username, "user.id": getattr(user, 'id', '')}
                user_msg = f" by user {user.username}"
                
            logger.info(f"File downloaded from Supabase: {bucket_name}/{file_path}{user_msg}", extra=extra)
            return result
        except Exception as e:
            logger.error(f"Failed to download file from Supabase {bucket_name}/{file_path}: {e}")
            raise
    
    def get_public_url(self, bucket_name: str, file_path: str) -> str:
        try:
            result = self.storage.from_(bucket_name).get_public_url(file_path)
            return result
        except Exception as e:
            logger.error(f"Failed to get public URL for Supabase {bucket_name}/{file_path}: {e}")
            raise
    
    def create_signed_url(
        self,
        bucket_name: str,
        file_path: str,
        expires_in: int = 3600
    ) -> str:
        try:
            result = self.storage.from_(bucket_name).create_signed_url(
                file_path,
                expires_in
            )
            return result.get('signedURL', '')
        except Exception as e:
            logger.error(f"Failed to create signed URL for Supabase {bucket_name}/{file_path}: {e}")
            raise
    
    def delete_file(self, bucket_name: str, file_paths: List[str], user: Optional[Any] = None) -> Dict[str, Any]:
        try:
            result = self.storage.from_(bucket_name).remove(file_paths)
            
            extra = {}
            user_msg = ""
            if user and hasattr(user, 'username'):
                extra = {"user.name": user.username, "user.id": getattr(user, 'id', '')}
                user_msg = f" by user {user.username}"
                
            logger.info(f"Files deleted from Supabase {bucket_name}: {file_paths}{user_msg}", extra=extra)
            return result
        except Exception as e:
            logger.error(f"Failed to delete files from Supabase {bucket_name}: {e}")
            raise
    
    def list_files(
        self,
        bucket_name: str,
        path: str = "",
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        try:
            result = self.storage.from_(bucket_name).list(
                path=path,
                options={"limit": limit, "offset": offset}
            )
            return result
        except Exception as e:
            logger.error(f"Failed to list files in Supabase {bucket_name}/{path}: {e}")
            raise
    
    def move_file(
        self,
        bucket_name: str,
        from_path: str,
        to_path: str
    ) -> Dict[str, Any]:
        try:
            result = self.storage.from_(bucket_name).move(from_path, to_path)
            logger.info(f"File moved in Supabase: {bucket_name}/{from_path} -> {to_path}")
            return result
        except Exception as e:
            logger.error(f"Failed to move file in Supabase {bucket_name}: {e}")
            raise
    
    def copy_file(
        self,
        bucket_name: str,
        from_path: str,
        to_path: str
    ) -> Dict[str, Any]:
        try:
            result = self.storage.from_(bucket_name).copy(from_path, to_path)
            logger.info(f"File copied in Supabase: {bucket_name}/{from_path} -> {to_path}")
            return result
        except Exception as e:
            logger.error(f"Failed to copy file in Supabase {bucket_name}: {e}")
            raise
