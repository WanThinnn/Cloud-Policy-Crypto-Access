import os
import shutil
import logging
from typing import Optional, List, Dict, Any
from django.conf import settings
from ..interface import IStorageService

logger = logging.getLogger('crypto_access.storage')

class LocalStorageAdapter(IStorageService):
    """
    Local Disk Implementation for Storage operations.
    Files are stored in MEDIA_ROOT.
    """
    
    def __init__(self):
        self.base_dir = getattr(settings, 'MEDIA_ROOT', os.path.join(settings.BASE_DIR, 'media'))
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

    def _get_bucket_path(self, bucket_name: str) -> str:
        return os.path.join(self.base_dir, bucket_name)

    def _get_file_path(self, bucket_name: str, file_path: str) -> str:
        return os.path.join(self._get_bucket_path(bucket_name), file_path)

    def create_bucket(
        self, 
        bucket_name: str, 
        public: bool = False,
        allowed_mime_types: Optional[List[str]] = None,
        file_size_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        bucket_path = self._get_bucket_path(bucket_name)
        if not os.path.exists(bucket_path):
            os.makedirs(bucket_path)
            logger.info(f"Local bucket '{bucket_name}' created successfully")
            return {"name": bucket_name, "public": public}
        return {"name": bucket_name, "error": "Bucket already exists"}

    def list_buckets(self) -> List[Dict[str, Any]]:
        buckets = []
        if os.path.exists(self.base_dir):
            for item in os.listdir(self.base_dir):
                if os.path.isdir(os.path.join(self.base_dir, item)):
                    buckets.append({"name": item})
        return buckets

    def upload_file(
        self,
        bucket_name: str,
        file_path: str,
        file_data: bytes,
        content_type: Optional[str] = None,
        upsert: bool = False,
        user: Optional[Any] = None
    ) -> Dict[str, Any]:
        full_path = self._get_file_path(bucket_name, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        if os.path.exists(full_path) and not upsert:
            raise Exception("File already exists and upsert is False")
            
        with open(full_path, 'wb') as f:
            f.write(file_data)
            
        logger.info(f"File uploaded to Local: {bucket_name}/{file_path}")
        return {"path": file_path, "size": len(file_data)}

    def download_file(self, bucket_name: str, file_path: str, user: Optional[Any] = None) -> bytes:
        full_path = self._get_file_path(bucket_name, file_path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File {file_path} not found in bucket {bucket_name}")
            
        with open(full_path, 'rb') as f:
            data = f.read()
        logger.info(f"File downloaded from Local: {bucket_name}/{file_path}")
        return data

    def get_public_url(self, bucket_name: str, file_path: str) -> str:
        # For local dev, return a relative media URL
        media_url = getattr(settings, 'MEDIA_URL', '/media/')
        return f"{media_url}{bucket_name}/{file_path}"

    def create_signed_url(
        self,
        bucket_name: str,
        file_path: str,
        expires_in: int = 3600
    ) -> str:
        # Local doesn't really support signed URLs, just return public URL
        return self.get_public_url(bucket_name, file_path)

    def delete_file(self, bucket_name: str, file_paths: List[str], user: Optional[Any] = None) -> Dict[str, Any]:
        deleted = []
        for path in file_paths:
            full_path = self._get_file_path(bucket_name, path)
            if os.path.exists(full_path):
                os.remove(full_path)
                deleted.append(path)
        logger.info(f"Files deleted from Local {bucket_name}: {deleted}")
        return {"deleted": deleted}

    def list_files(
        self,
        bucket_name: str,
        path: str = "",
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        bucket_dir = self._get_bucket_path(bucket_name)
        target_dir = os.path.join(bucket_dir, path)
        files = []
        
        if os.path.exists(target_dir):
            # Simple non-recursive listing for local mockup
            for item in os.listdir(target_dir):
                item_path = os.path.join(target_dir, item)
                if os.path.isfile(item_path):
                    files.append({
                        "name": item,
                        "size": os.path.getsize(item_path)
                    })
                    
        return files[offset:offset+limit]

    def move_file(
        self,
        bucket_name: str,
        from_path: str,
        to_path: str
    ) -> Dict[str, Any]:
        src = self._get_file_path(bucket_name, from_path)
        dst = self._get_file_path(bucket_name, to_path)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
        logger.info(f"File moved in Local: {bucket_name}/{from_path} -> {to_path}")
        return {"message": "success"}

    def copy_file(
        self,
        bucket_name: str,
        from_path: str,
        to_path: str
    ) -> Dict[str, Any]:
        src = self._get_file_path(bucket_name, from_path)
        dst = self._get_file_path(bucket_name, to_path)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        logger.info(f"File copied in Local: {bucket_name}/{from_path} -> {to_path}")
        return {"message": "success"}
