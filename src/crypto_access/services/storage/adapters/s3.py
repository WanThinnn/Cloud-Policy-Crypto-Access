import os
import logging
from typing import Optional, List, Dict, Any
from django.conf import settings
from ..interface import IStorageService

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None

logger = logging.getLogger('crypto_access.storage')

class S3StorageAdapter(IStorageService):
    """
    AWS S3 (or MinIO compatible) Implementation for Storage operations.
    """
    
    def __init__(self):
        if not boto3:
            raise ImportError("boto3 is required for S3StorageAdapter. Install with 'pip install boto3'")
            
        self.aws_access_key = getattr(settings, 'AWS_ACCESS_KEY_ID', None) or os.environ.get('AWS_ACCESS_KEY_ID')
        self.aws_secret_key = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None) or os.environ.get('AWS_SECRET_ACCESS_KEY')
        self.endpoint_url = getattr(settings, 'AWS_S3_ENDPOINT_URL', None) or os.environ.get('AWS_S3_ENDPOINT_URL')
        self.region = getattr(settings, 'AWS_S3_REGION_NAME', None) or os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')
        
        if not self.aws_access_key or not self.aws_secret_key:
            raise ValueError("AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be set for S3StorageAdapter")
            
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_key,
            endpoint_url=self.endpoint_url,
            region_name=self.region
        )

    def create_bucket(
        self, 
        bucket_name: str, 
        public: bool = False,
        allowed_mime_types: Optional[List[str]] = None,
        file_size_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        try:
            if self.region == 'us-east-1':
                self.s3_client.create_bucket(Bucket=bucket_name)
            else:
                self.s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': self.region}
                )
            
            if public:
                # Basic public policy for MinIO/S3
                policy = f'{{"Version":"2012-10-17","Statement":[{{"Effect":"Allow","Principal":"*","Action":["s3:GetObject"],"Resource":["arn:aws:s3:::{bucket_name}/*"]}}]}}'
                self.s3_client.put_bucket_policy(Bucket=bucket_name, Policy=policy)
                
            logger.info(f"Bucket '{bucket_name}' created successfully in S3")
            return {"name": bucket_name}
        except ClientError as e:
            logger.error(f"Failed to create bucket '{bucket_name}' in S3: {e}")
            raise

    def list_buckets(self) -> List[Dict[str, Any]]:
        try:
            response = self.s3_client.list_buckets()
            return [{"name": bucket["Name"]} for bucket in response.get("Buckets", [])]
        except ClientError as e:
            logger.error(f"Failed to list S3 buckets: {e}")
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
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
                
            self.s3_client.put_object(
                Bucket=bucket_name,
                Key=file_path,
                Body=file_data,
                **extra_args
            )
            
            logger.info(f"File uploaded to S3: {bucket_name}/{file_path}")
            return {"path": file_path, "size": len(file_data)}
        except ClientError as e:
            logger.error(f"Failed to upload file to S3 {bucket_name}/{file_path}: {e}")
            raise

    def download_file(self, bucket_name: str, file_path: str, user: Optional[Any] = None) -> bytes:
        try:
            response = self.s3_client.get_object(Bucket=bucket_name, Key=file_path)
            data = response['Body'].read()
            logger.info(f"File downloaded from S3: {bucket_name}/{file_path}")
            return data
        except ClientError as e:
            logger.error(f"Failed to download file from S3 {bucket_name}/{file_path}: {e}")
            raise

    def get_public_url(self, bucket_name: str, file_path: str) -> str:
        if self.endpoint_url:
            return f"{self.endpoint_url.rstrip('/')}/{bucket_name}/{file_path}"
        return f"https://{bucket_name}.s3.{self.region}.amazonaws.com/{file_path}"

    def create_signed_url(
        self,
        bucket_name: str,
        file_path: str,
        expires_in: int = 3600
    ) -> str:
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': file_path},
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to create signed URL for S3 {bucket_name}/{file_path}: {e}")
            raise

    def delete_file(self, bucket_name: str, file_paths: List[str], user: Optional[Any] = None) -> Dict[str, Any]:
        try:
            objects = [{'Key': path} for path in file_paths]
            response = self.s3_client.delete_objects(
                Bucket=bucket_name,
                Delete={'Objects': objects}
            )
            logger.info(f"Files deleted from S3 {bucket_name}: {file_paths}")
            return response
        except ClientError as e:
            logger.error(f"Failed to delete files from S3 {bucket_name}: {e}")
            raise

    def list_files(
        self,
        bucket_name: str,
        path: str = "",
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=path,
                MaxKeys=limit
                # Note: offset is complex in S3, normally requires ContinuationToken
            )
            files = []
            for item in response.get('Contents', []):
                files.append({
                    "name": item['Key'].split('/')[-1] if '/' in item['Key'] else item['Key'],
                    "path": item['Key'],
                    "size": item['Size']
                })
            return files
        except ClientError as e:
            logger.error(f"Failed to list files in S3 {bucket_name}/{path}: {e}")
            raise

    def move_file(
        self,
        bucket_name: str,
        from_path: str,
        to_path: str
    ) -> Dict[str, Any]:
        self.copy_file(bucket_name, from_path, to_path)
        self.delete_file(bucket_name, [from_path])
        return {"message": "success"}

    def copy_file(
        self,
        bucket_name: str,
        from_path: str,
        to_path: str
    ) -> Dict[str, Any]:
        try:
            copy_source = {'Bucket': bucket_name, 'Key': from_path}
            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=bucket_name,
                Key=to_path
            )
            logger.info(f"File copied in S3: {bucket_name}/{from_path} -> {to_path}")
            return {"message": "success"}
        except ClientError as e:
            logger.error(f"Failed to copy file in S3 {bucket_name}: {e}")
            raise
