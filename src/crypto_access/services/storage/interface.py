from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

class IStorageService(ABC):
    """
    Abstract Base Class for Storage Services (Adapter Pattern).
    Defines the contract that all storage vendors (Supabase, S3, GCS, Local) must implement.
    """

    @abstractmethod
    def create_bucket(
        self, 
        bucket_name: str, 
        public: bool = False,
        allowed_mime_types: Optional[List[str]] = None,
        file_size_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def list_buckets(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def upload_file(
        self,
        bucket_name: str,
        file_path: str,
        file_data: bytes,
        content_type: Optional[str] = None,
        upsert: bool = False,
        user: Optional[Any] = None
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def download_file(self, bucket_name: str, file_path: str, user: Optional[Any] = None) -> bytes:
        pass

    @abstractmethod
    def get_public_url(self, bucket_name: str, file_path: str) -> str:
        pass

    @abstractmethod
    def create_signed_url(
        self,
        bucket_name: str,
        file_path: str,
        expires_in: int = 3600
    ) -> str:
        pass

    @abstractmethod
    def delete_file(self, bucket_name: str, file_paths: List[str], user: Optional[Any] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def list_files(
        self,
        bucket_name: str,
        path: str = "",
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def move_file(
        self,
        bucket_name: str,
        from_path: str,
        to_path: str
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def copy_file(
        self,
        bucket_name: str,
        from_path: str,
        to_path: str
    ) -> Dict[str, Any]:
        pass
