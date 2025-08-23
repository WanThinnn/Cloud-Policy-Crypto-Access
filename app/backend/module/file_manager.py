"""
File management module for secure file sharing with CP-ABE encryption
"""
import os
import uuid
import logging
import mimetypes
from typing import Dict, Any, List, Optional
from datetime import datetime
from firebase_admin import firestore, storage
from google.cloud.firestore_v1 import SERVER_TIMESTAMP, Increment, Query
from .database import db
from .central_authority import central_authority
from .abac import abac
import tempfile
import requests
from config import Config

logger = logging.getLogger(__name__)

class FileManager:
    """
    File Manager quản lý việc upload, share, download files với mã hóa CP-ABE
    """
    
    def __init__(self):
        self.files_collection = db.collection('shared_files')
        self.access_logs_collection = db.collection('file_access_logs')
        
    def upload_file(self, file_data: bytes, filename: str, owner_id: str, 
                   access_policy: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Upload và mã hóa file
        
        Args:
            file_data: Dữ liệu file
            filename: Tên file
            owner_id: ID của người upload
            access_policy: Policy cho access control (nếu không có sẽ tự generate)
            metadata: Metadata bổ sung
            
        Returns:
            Dict with file info
        """
        try:
            # Tạo file ID unique
            file_id = str(uuid.uuid4())
            
            # Tạo temp file để mã hóa
            temp_dir = tempfile.mkdtemp()
            temp_file_path = os.path.join(temp_dir, filename)
            
            with open(temp_file_path, 'wb') as f:
                f.write(file_data)
            
            # Tạo access policy nếu chưa có
            if not access_policy:
                access_policy = central_authority.generate_policy_for_user(owner_id)
            
            # Mã hóa file
            encrypt_result = central_authority.encrypt_file_for_policy(temp_file_path, access_policy)
            
            if not encrypt_result['success']:
                import shutil
                shutil.rmtree(temp_dir)
                return encrypt_result
            
            # Lấy thông tin file
            file_size = len(file_data)
            file_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            
            # Tạo metadata
            file_metadata = {
                'id': file_id,
                'filename': filename,
                'original_size': file_size,
                'file_type': file_type,
                'owner_id': owner_id,
                'access_policy': access_policy,
                'encrypted_data': encrypt_result['encrypted_data'],
                'upload_time': SERVER_TIMESTAMP,
                'last_accessed': None,
                'access_count': 0,
                'is_active': True,
                'metadata': metadata or {}
            }
            
            # Lưu vào Firestore
            self.files_collection.document(file_id).set(file_metadata)
            
            # Cleanup temp files
            import shutil
            shutil.rmtree(temp_dir)
            
            logger.info(f"File uploaded and encrypted: {file_id}")
            
            return {
                'success': True,
                'file_id': file_id,
                'filename': filename,
                'access_policy': access_policy,
                'message': 'File uploaded and encrypted successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            return {
                'success': False,
                'error': f'Failed to upload file: {str(e)}'
            }
    
    def download_file(self, file_id: str, user_id: str) -> Dict[str, Any]:
        """
        Download và giải mã file
        
        Args:
            file_id: File ID
            user_id: User ID của người download
            
        Returns:
            Dict with file data
        """
        try:
            # Lấy thông tin file
            file_doc = self.files_collection.document(file_id).get()
            
            if not file_doc.exists:
                return {
                    'success': False,
                    'error': 'File not found'
                }
            
            file_data = file_doc.to_dict()
            
            if not file_data['is_active']:
                return {
                    'success': False,
                    'error': 'File is no longer available'
                }
            
            # Kiểm tra quyền truy cập 
            # Option 1: Owner can always access
            if file_data['owner_id'] == user_id:
                access_granted = True
                access_reason = "File owner access"
            else:
                # Option 2: Check if user can decrypt with their private key
                # This is the real CP-ABE access control
                decrypt_result = central_authority.decrypt_file_for_user(
                    file_data['encrypted_data'], 
                    user_id
                )
                
                if decrypt_result['success']:
                    access_granted = True
                    access_reason = "CP-ABE policy match"
                    decrypted_data = decrypt_result['decrypted_data']
                else:
                    access_granted = False
                    access_reason = f"CP-ABE access denied: {decrypt_result.get('error', 'No matching attributes')}"
            
            if not access_granted:
                # Log access attempt
                self._log_access_attempt(file_id, user_id, 'denied', access_reason)
                
                return {
                    'success': False,
                    'error': f"Access denied: {access_reason}"
                }
            
            # If we reach here and haven't decrypted yet (owner case), decrypt now
            if file_data['owner_id'] == user_id and 'decrypted_data' not in locals():
                decrypt_result = central_authority.decrypt_file_for_user(
                    file_data['encrypted_data'], 
                    user_id
                )
                
                if not decrypt_result['success']:
                    # Log failed decryption
                    self._log_access_attempt(file_id, user_id, 'failed', 'Owner decryption failed')
                    
                    return decrypt_result
                
                decrypted_data = decrypt_result['decrypted_data']
            
            # Update access statistics
            self.files_collection.document(file_id).update({
                'last_accessed': SERVER_TIMESTAMP,
                'access_count': Increment(1)
            })
            
            # Log successful access
            self._log_access_attempt(file_id, user_id, 'success', 'File downloaded successfully')
            
            logger.info(f"File downloaded: {file_id} by user: {user_id}")
            
            return {
                'success': True,
                'filename': file_data['filename'],
                'file_type': file_data['file_type'],
                'file_data': decrypt_result['decrypted_data'],
                'message': 'File downloaded successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            self._log_access_attempt(file_id, user_id, 'error', str(e))
            
            return {
                'success': False,
                'error': f'Failed to download file: {str(e)}'
            }
    
    def list_user_files(self, user_id: str, include_shared: bool = True) -> Dict[str, Any]:
        """
        Liệt kê files của user
        
        Args:
            user_id: User ID
            include_shared: Có bao gồm files được share không
            
        Returns:
            Dict with files list
        """
        try:
            files_list = []
            
            # Files do user upload
            owned_files = self.files_collection.where('owner_id', '==', user_id)\
                                              .where('is_active', '==', True)\
                                              .get()
            
            for file_doc in owned_files:
                file_data = file_doc.to_dict()
                files_list.append({
                    'file_id': file_data['id'],
                    'filename': file_data['filename'],
                    'file_type': file_data['file_type'],
                    'original_size': file_data['original_size'],
                    'upload_time': file_data['upload_time'],
                    'access_count': file_data['access_count'],
                    'access_policy': file_data['access_policy'],
                    'is_owner': True
                })
            
            # Files được share nếu include_shared = True
            if include_shared:
                # Lấy tất cả files và check access
                all_files = self.files_collection.where('is_active', '==', True)\
                                                .where('owner_id', '!=', user_id)\
                                                .get()
                
                for file_doc in all_files:
                    file_data = file_doc.to_dict()
                    
                    # Check access với ABAC
                    access_request = {
                        'user_id': user_id,
                        'resource': 'files',
                        'action': 'read',
                        'resource_attributes': {
                            'file_id': file_data['id'],
                            'owner_id': file_data['owner_id'],
                            'file_type': file_data['file_type']
                        }
                    }
                    
                    access_check = abac.check_access(access_request)
                    
                    if access_check['success'] and access_check['access_granted']:
                        files_list.append({
                            'file_id': file_data['id'],
                            'filename': file_data['filename'],
                            'file_type': file_data['file_type'],
                            'original_size': file_data['original_size'],
                            'upload_time': file_data['upload_time'],
                            'access_count': file_data['access_count'],
                            'owner_id': file_data['owner_id'],
                            'is_owner': False
                        })
            
            return {
                'success': True,
                'files': files_list,
                'total_count': len(files_list)
            }
            
        except Exception as e:
            logger.error(f"Failed to list user files: {e}")
            return {
                'success': False,
                'error': f'Failed to list files: {str(e)}'
            }
    
    def delete_file(self, file_id: str, user_id: str) -> Dict[str, Any]:
        """
        Xóa file (chỉ owner mới được xóa)
        
        Args:
            file_id: File ID
            user_id: User ID
            
        Returns:
            Dict with success status
        """
        try:
            # Lấy thông tin file
            file_doc = self.files_collection.document(file_id).get()
            
            if not file_doc.exists:
                return {
                    'success': False,
                    'error': 'File not found'
                }
            
            file_data = file_doc.to_dict()
            
            # Kiểm tra quyền owner
            if file_data['owner_id'] != user_id:
                return {
                    'success': False,
                    'error': 'Only file owner can delete the file'
                }
            
            # Soft delete - set is_active = False
            self.files_collection.document(file_id).update({
                'is_active': False,
                'deleted_at': SERVER_TIMESTAMP,
                'deleted_by': user_id
            })
            
            logger.info(f"File deleted: {file_id} by user: {user_id}")
            
            return {
                'success': True,
                'message': 'File deleted successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            return {
                'success': False,
                'error': f'Failed to delete file: {str(e)}'
            }
    
    def update_file_policy(self, file_id: str, user_id: str, new_policy: str) -> Dict[str, Any]:
        """
        Cập nhật access policy của file
        
        Args:
            file_id: File ID
            user_id: User ID
            new_policy: Policy mới
            
        Returns:
            Dict with success status
        """
        try:
            # Lấy thông tin file
            file_doc = self.files_collection.document(file_id).get()
            
            if not file_doc.exists:
                return {
                    'success': False,
                    'error': 'File not found'
                }
            
            file_data = file_doc.to_dict()
            
            # Kiểm tra quyền owner
            if file_data['owner_id'] != user_id:
                return {
                    'success': False,
                    'error': 'Only file owner can update access policy'
                }
            
            # Re-encrypt file với policy mới
            temp_dir = tempfile.mkdtemp()
            temp_file_path = os.path.join(temp_dir, file_data['filename'])
            
            # Giải mã file hiện tại
            decrypt_result = central_authority.decrypt_file_for_user(
                file_data['encrypted_data'], 
                user_id
            )
            
            if not decrypt_result['success']:
                import shutil
                shutil.rmtree(temp_dir)
                return decrypt_result
            
            # Ghi file tạm
            with open(temp_file_path, 'wb') as f:
                f.write(decrypt_result['decrypted_data'])
            
            # Mã hóa lại với policy mới
            encrypt_result = central_authority.encrypt_file_for_policy(temp_file_path, new_policy)
            
            if not encrypt_result['success']:
                import shutil
                shutil.rmtree(temp_dir)
                return encrypt_result
            
            # Update file trong Firestore
            self.files_collection.document(file_id).update({
                'access_policy': new_policy,
                'encrypted_data': encrypt_result['encrypted_data'],
                'policy_updated_at': SERVER_TIMESTAMP,
                'policy_updated_by': user_id
            })
            
            # Cleanup temp files
            import shutil
            shutil.rmtree(temp_dir)
            
            logger.info(f"File policy updated: {file_id}")
            
            return {
                'success': True,
                'new_policy': new_policy,
                'message': 'File access policy updated successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to update file policy: {e}")
            return {
                'success': False,
                'error': f'Failed to update file policy: {str(e)}'
            }
    
    def get_file_info(self, file_id: str, user_id: str) -> Dict[str, Any]:
        """
        Lấy thông tin file
        
        Args:
            file_id: File ID
            user_id: User ID
            
        Returns:
            Dict with file info
        """
        try:
            # Lấy thông tin file
            file_doc = self.files_collection.document(file_id).get()
            
            if not file_doc.exists:
                return {
                    'success': False,
                    'error': 'File not found'
                }
            
            file_data = file_doc.to_dict()
            
            if not file_data['is_active']:
                return {
                    'success': False,
                    'error': 'File is no longer available'
                }
            
            # Kiểm tra quyền xem thông tin file
            access_request = {
                'user_id': user_id,
                'resource': 'files',
                'action': 'read',
                'resource_attributes': {
                    'file_id': file_id,
                    'owner_id': file_data['owner_id'],
                    'file_type': file_data['file_type']
                }
            }
            
            access_check = abac.check_access(access_request)
            
            if not access_check['success'] or not access_check['access_granted']:
                return {
                    'success': False,
                    'error': f"Access denied: {access_check.get('reason', 'Insufficient permissions')}"
                }
            
            # Return file info (không bao gồm encrypted_data)
            file_info = {
                'file_id': file_data['id'],
                'filename': file_data['filename'],
                'file_type': file_data['file_type'],
                'original_size': file_data['original_size'],
                'owner_id': file_data['owner_id'],
                'upload_time': file_data['upload_time'],
                'last_accessed': file_data.get('last_accessed'),
                'access_count': file_data['access_count'],
                'access_policy': file_data['access_policy'],
                'metadata': file_data.get('metadata', {}),
                'is_owner': file_data['owner_id'] == user_id
            }
            
            return {
                'success': True,
                'file_info': file_info
            }
            
        except Exception as e:
            logger.error(f"Failed to get file info: {e}")
            return {
                'success': False,
                'error': f'Failed to get file info: {str(e)}'
            }
    
    def _log_access_attempt(self, file_id: str, user_id: str, status: str, details: str):
        """Log access attempt"""
        try:
            log_entry = {
                'file_id': file_id,
                'user_id': user_id,
                'status': status,  # 'success', 'denied', 'failed', 'error'
                'details': details,
                'timestamp': SERVER_TIMESTAMP
            }
            
            self.access_logs_collection.add(log_entry)
            
        except Exception as e:
            logger.error(f"Failed to log access attempt: {e}")
    
    def get_access_logs(self, file_id: str, user_id: str) -> Dict[str, Any]:
        """
        Lấy access logs của file (chỉ owner mới xem được)
        
        Args:
            file_id: File ID
            user_id: User ID
            
        Returns:
            Dict with access logs
        """
        try:
            # Kiểm tra quyền owner
            file_doc = self.files_collection.document(file_id).get()
            
            if not file_doc.exists:
                return {
                    'success': False,
                    'error': 'File not found'
                }
            
            file_data = file_doc.to_dict()
            
            if file_data['owner_id'] != user_id:
                return {
                    'success': False,
                    'error': 'Only file owner can view access logs'
                }
            
            # Lấy access logs
            logs = self.access_logs_collection.where('file_id', '==', file_id)\
                                             .order_by('timestamp', direction=Query.DESCENDING)\
                                             .limit(100).get()
            
            logs_list = []
            for log_doc in logs:
                log_data = log_doc.to_dict()
                logs_list.append(log_data)
            
            return {
                'success': True,
                'logs': logs_list,
                'total_count': len(logs_list)
            }
            
        except Exception as e:
            logger.error(f"Failed to get access logs: {e}")
            return {
                'success': False,
                'error': f'Failed to get access logs: {str(e)}'
            }
    
    def fetch_user_attributes(self, user_id: str) -> Dict[str, Any]:
        """Fetch user attributes from SuperAdmin system"""
        try:
            server_host = Config.HOST
            server_port = Config.PORT  
            service_token = Config.SYSTEM_SERVICE_TOKEN
            
            response = requests.get(
                f'http://{server_host}:{server_port}/api/super-admin/system/users',
                headers={
                    'Authorization': f'Bearer {service_token}',
                    'X-Service-Name': 'file-manager'
                },
                timeout=10
            )
            
            if response.status_code != 200:
                return {'success': False, 'error': f'HTTP {response.status_code}'}
                
            api_data = response.json()
            users = api_data.get('users', [])
            
            # Find target user
            for user in users:
                if user.get('id') == user_id:
                    return {
                        'success': True,
                        'user': user,
                        'attributes': user.get('attributes', {})
                    }
            
            return {'success': False, 'error': 'User not found'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

# Global file manager instance
file_manager = FileManager()
