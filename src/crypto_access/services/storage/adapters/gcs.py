import os
import logging
from typing import Optional, List, Dict, Any
from django.conf import settings
from ..interface import IStorageService

try:
    from google.cloud import storage
    from google.api_core.exceptions import GoogleAPIError
except ImportError:
    storage = None

logger = logging.getLogger('crypto_access.storage')

class GCSStorageAdapter(IStorageService):
    """
    Google Cloud Storage (GCS) Implementation for Storage operations.
    """
    
    def __init__(self):
        if not storage:
            raise ImportError("google-cloud-storage is required for GCSStorageAdapter. Install with 'pip install google-cloud-storage'")
            
        # For emulator usage (e.g. fsouza/fake-gcs-server)
        self.emulator_host = getattr(settings, 'STORAGE_EMULATOR_HOST', None) or os.environ.get('STORAGE_EMULATOR_HOST')
        if self.emulator_host:
            os.environ['STORAGE_EMULATOR_HOST'] = self.emulator_host
            
        project = getattr(settings, 'GCP_PROJECT_ID', None) or os.environ.get('GCP_PROJECT_ID', 'test-project')
        
        self.client = storage.Client(project=project)

    def create_bucket(
        self, 
        bucket_name: str, 
        public: bool = False,
        allowed_mime_types: Optional[List[str]] = None,
        file_size_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        try:
            bucket = self.client.create_bucket(bucket_name)
            if public:
                bucket.make_public(recursive=True, future=True)
                
            logger.info(f"Bucket '{bucket_name}' created successfully in GCS")
            return {"name": bucket.name}
        except Exception as e:
            logger.error(f"Failed to create bucket '{bucket_name}' in GCS: {e}")
            raise

    def list_buckets(self) -> List[Dict[str, Any]]:
        try:
            buckets = self.client.list_buckets()
            return [{"name": b.name} for b in buckets]
        except Exception as e:
            logger.error(f"Failed to list GCS buckets: {e}")
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
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(file_path)
            
            if content_type:
                blob.upload_from_string(file_data, content_type=content_type)
            else:
                blob.upload_from_string(file_data)
                
            logger.info(f"File uploaded to GCS: {bucket_name}/{file_path}")
            return {"path": file_path, "size": len(file_data)}
        except Exception as e:
            logger.error(f"Failed to upload file to GCS {bucket_name}/{file_path}: {e}")
            raise

    def download_file(self, bucket_name: str, file_path: str, user: Optional[Any] = None) -> bytes:
        try:
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(file_path)
            data = blob.download_as_bytes()
            logger.info(f"File downloaded from GCS: {bucket_name}/{file_path}")
            return data
        except Exception as e:
            logger.error(f"Failed to download file from GCS {bucket_name}/{file_path}: {e}")
            raise

    def get_public_url(self, bucket_name: str, file_path: str) -> str:
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(file_path)
        return blob.public_url

    def create_signed_url(
        self,
        bucket_name: str,
        file_path: str,
        expires_in: int = 3600
    ) -> str:
        try:
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(file_path)
            url = blob.generate_signed_url(
                version="v4",
                expiration=expires_in,
                method="GET"
            )
            return url
        except Exception as e:
            logger.error(f"Failed to create signed URL for GCS {bucket_name}/{file_path}: {e}")
            raise

    def delete_file(self, bucket_name: str, file_paths: List[str], user: Optional[Any] = None) -> Dict[str, Any]:
        try:
            bucket = self.client.bucket(bucket_name)
            bucket.delete_blobs(blobs=file_paths)
            logger.info(f"Files deleted from GCS {bucket_name}: {file_paths}")
            return {"deleted": file_paths}
        except Exception as e:
            logger.error(f"Failed to delete files from GCS {bucket_name}: {e}")
            raise

    def list_files(
        self,
        bucket_name: str,
        path: str = "",
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        try:
            bucket = self.client.bucket(bucket_name)
            blobs = bucket.list_blobs(prefix=path, max_results=limit)
            
            files = []
            for blob in blobs:
                files.append({
                    "name": blob.name.split('/')[-1] if '/' in blob.name else blob.name,
                    "path": blob.name,
                    "size": blob.size
                })
            return files
        except Exception as e:
            logger.error(f"Failed to list files in GCS {bucket_name}/{path}: {e}")
            raise

    def move_file(
        self,
        bucket_name: str,
        from_path: str,
        to_path: str
    ) -> Dict[str, Any]:
        try:
            bucket = self.client.bucket(bucket_name)
            source_blob = bucket.blob(from_path)
            bucket.rename_blob(source_blob, to_path)
            logger.info(f"File moved in GCS: {bucket_name}/{from_path} -> {to_path}")
            return {"message": "success"}
        except Exception as e:
            logger.error(f"Failed to move file in GCS {bucket_name}: {e}")
            raise

    def copy_file(
        self,
        bucket_name: str,
        from_path: str,
        to_path: str
    ) -> Dict[str, Any]:
        try:
            bucket = self.client.bucket(bucket_name)
            source_blob = bucket.blob(from_path)
            bucket.copy_blob(source_blob, bucket, to_path)
            logger.info(f"File copied in GCS: {bucket_name}/{from_path} -> {to_path}")
            return {"message": "success"}
        except Exception as e:
            logger.error(f"Failed to copy file in GCS {bucket_name}: {e}")
            raise
