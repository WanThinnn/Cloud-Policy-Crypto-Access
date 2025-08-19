"""
Central Authority (CA) module for managing CP-ABE keys and policies
"""
import logging
import uuid
from typing import Dict, Any, List, Optional
from firebase_admin import firestore
from datetime import datetime
from .database import db
from .user_management import user_manager
import os
import tempfile

# Import ABE library - sẽ được set sau khi module được import hoàn chỉnh
abe_lib = None

logger = logging.getLogger(__name__)

class CentralAuthority:
    """
    Central Authority quản lý khóa và policy cho CP-ABE system
    """
    
    def __init__(self):
        self.keys_collection = db.collection('abe_keys')
        self.policies_collection = db.collection('abe_policies')
        self.user_attributes_collection = db.collection('user_attributes')
        
    def setup_abe_system(self) -> Dict[str, Any]:
        """
        Setup ABE system - tạo master key và public key
        
        Returns:
            Dict with success status and keys info
        """
        try:
            # Tạo thư mục tạm để lưu keys
            temp_dir = tempfile.mkdtemp()
            setup_dir = os.path.join(temp_dir, 'abe_setup')
            os.makedirs(setup_dir, exist_ok=True)
            
            # Check if ABE library is available
            if not abe_lib or not abe_lib.is_loaded():
                return {
                    'success': False,
                    'error': 'ABE library not loaded. Please check library installation.'
                }
            
            # Gọi ABE setup từ library
            abe_lib.setup(setup_dir)
            
            # Đọc các key files
            public_key_path = os.path.join(setup_dir, 'public_key.key')
            master_key_path = os.path.join(setup_dir, 'master_key.key')
            
            # Lưu keys vào Firestore
            setup_id = str(uuid.uuid4())
            
            with open(public_key_path, 'rb') as pk_file:
                public_key_data = pk_file.read()
            
            with open(master_key_path, 'rb') as mk_file:
                master_key_data = mk_file.read()
            
            keys_doc = {
                'id': setup_id,
                'public_key': public_key_data,
                'master_key': master_key_data,
                'created_at': datetime.utcnow(),
                'is_active': True
            }
            
            # Deactivate old keys
            old_keys = self.keys_collection.where('is_active', '==', True).get()
            for old_key in old_keys:
                self.keys_collection.document(old_key.id).update({'is_active': False})
            
            # Save new keys
            self.keys_collection.document(setup_id).set(keys_doc)
            
            # Cleanup temp files
            import shutil
            shutil.rmtree(temp_dir)
            
            logger.info(f"ABE system setup completed with ID: {setup_id}")
            
            return {
                'success': True,
                'setup_id': setup_id,
                'message': 'ABE system setup completed successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to setup ABE system: {e}")
            return {
                'success': False,
                'error': f'Failed to setup ABE system: {str(e)}'
            }
    
    def get_active_keys(self) -> Dict[str, Any]:
        """
        Lấy active public key và master key
        
        Returns:
            Dict with keys data
        """
        try:
            active_keys = self.keys_collection.where('is_active', '==', True).limit(1).get()
            
            if not active_keys:
                return {
                    'success': False,
                    'error': 'No active keys found. Please setup ABE system first.'
                }
            
            keys_doc = active_keys[0]
            keys_data = keys_doc.to_dict()
            
            # Check if keys exist
            has_public_key = 'public_key' in keys_data and keys_data['public_key'] is not None
            has_master_key = 'master_key' in keys_data and keys_data['master_key'] is not None
            
            return {
                'success': True,
                'setup_id': keys_doc.id,
                'has_public_key': has_public_key,
                'has_master_key': has_master_key,
                'public_key': keys_data.get('public_key'),
                'master_key': keys_data.get('master_key'),
                'message': 'Active keys found'
            }
            
        except Exception as e:
            logger.error(f"Failed to get active keys: {e}")
            return {
                'success': False,
                'error': f'Failed to get active keys: {str(e)}'
            }
    
    def generate_user_private_key(self, user_id: str, attributes: List[str]) -> Dict[str, Any]:
        """
        Tạo private key cho user dựa trên attributes
        
        Args:
            user_id: User ID
            attributes: List of attributes ['role:doctor', 'department:cardiology']
            
        Returns:
            Dict with private key data
        """
        try:
            # Lấy active keys
            keys_result = self.get_active_keys()
            if not keys_result['success']:
                return keys_result
            
            # Tạo temp files
            temp_dir = tempfile.mkdtemp()
            
            public_key_path = os.path.join(temp_dir, 'public_key.key')
            master_key_path = os.path.join(temp_dir, 'master_key.key')
            private_key_path = os.path.join(temp_dir, 'private_key.key')
            
            # Write keys to temp files
            with open(public_key_path, 'wb') as f:
                f.write(keys_result['public_key'])
            
            with open(master_key_path, 'wb') as f:
                f.write(keys_result['master_key'])
            
            # Generate private key
            attributes_str = ' '.join(attributes)
            abe_lib.generate_secret_key(public_key_path, master_key_path, attributes_str, private_key_path)
            
            # Read generated private key
            with open(private_key_path, 'rb') as f:
                private_key_data = f.read()
            
            # Save user private key to Firestore
            user_key_doc = {
                'user_id': user_id,
                'private_key': private_key_data,
                'attributes': attributes,
                'created_at': firestore.SERVER_TIMESTAMP,
                'is_active': True
            }
            
            # Deactivate old private keys for this user
            old_keys = self.keys_collection.where('user_id', '==', user_id).where('is_active', '==', True).get()
            for old_key in old_keys:
                self.keys_collection.document(old_key.id).update({'is_active': False})
            
            # Save new private key
            private_key_id = str(uuid.uuid4())
            self.keys_collection.document(private_key_id).set(user_key_doc)
            
            # Cleanup temp files
            import shutil
            shutil.rmtree(temp_dir)
            
            logger.info(f"Private key generated for user: {user_id}")
            
            return {
                'success': True,
                'private_key_id': private_key_id,
                'attributes': attributes,
                'message': 'Private key generated successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to generate private key: {e}")
            return {
                'success': False,
                'error': f'Failed to generate private key: {str(e)}'
            }
    
    def get_user_private_key(self, user_id: str) -> Dict[str, Any]:
        """
        Lấy private key của user
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with private key data
        """
        try:
            user_keys = self.keys_collection.where('user_id', '==', user_id)\
                                           .where('is_active', '==', True)\
                                           .limit(1).get()
            
            if not user_keys:
                return {
                    'success': False,
                    'error': 'User private key not found'
                }
            
            key_data = user_keys[0].to_dict()
            
            return {
                'success': True,
                'private_key': key_data['private_key'],
                'attributes': key_data['attributes']
            }
            
        except Exception as e:
            logger.error(f"Failed to get user private key: {e}")
            return {
                'success': False,
                'error': f'Failed to get user private key: {str(e)}'
            }
    
    def generate_policy_for_user(self, user_id: str) -> str:
        """
        Tạo access policy cho user dựa trên attributes
        
        Args:
            user_id: User ID
            
        Returns:
            Policy string
        """
        try:
            # Lấy user attributes từ ABAC module
            from .abac import abac
            
            attrs_result = abac.get_user_attributes(user_id)
            if not attrs_result['success']:
                return "(PUBLIC)"  # Default policy
            
            attributes = attrs_result['attributes']
            role = attributes.get('role', 'public')
            department = attributes.get('department', '')
            clearance = attributes.get('clearance_level', 'low')
            
            # Tạo policy dựa trên role và attributes
            if role == 'admin':
                return "(ADMIN)"
            elif role == 'doctor':
                if department:
                    return f"(DOCTOR AND {department.upper()})"
                else:
                    return "(DOCTOR)"
            elif role == 'nurse':
                if department:
                    return f"(NURSE AND {department.upper()})"
                else:
                    return "(NURSE)"
            elif role == 'patient':
                return "(PATIENT)"
            else:
                return "(PUBLIC)"
                
        except Exception as e:
            logger.error(f"Failed to generate policy for user {user_id}: {e}")
            return "(PUBLIC)"
    
    def encrypt_file_for_policy(self, file_path: str, policy: str) -> Dict[str, Any]:
        """
        Mã hóa file với policy cho trước
        
        Args:
            file_path: Đường dẫn file cần mã hóa
            policy: Policy string
            
        Returns:
            Dict with encrypted file info
        """
        try:
            # Lấy active public key
            keys_result = self.get_active_keys()
            if not keys_result['success']:
                return keys_result
            
            # Check if public key exists
            if not keys_result.get('public_key'):
                return {
                    'success': False,
                    'error': 'Public key not found. Please setup ABE system first.'
                }
            
            # Tạo temp files
            temp_dir = tempfile.mkdtemp()
            
            public_key_path = os.path.join(temp_dir, 'public_key.key')
            encrypted_file_path = os.path.join(temp_dir, 'encrypted_file.enc')
            
            # Write public key to temp file
            with open(public_key_path, 'wb') as f:
                f.write(keys_result['public_key'])
            
            # Encrypt file
            abe_lib.encrypt(public_key_path, file_path, policy, encrypted_file_path)
            
            # Read encrypted data
            with open(encrypted_file_path, 'rb') as f:
                encrypted_data = f.read()
            
            # Cleanup temp files
            import shutil
            shutil.rmtree(temp_dir)
            
            logger.info(f"File encrypted with policy: {policy}")
            
            return {
                'success': True,
                'encrypted_data': encrypted_data,
                'policy': policy,
                'message': 'File encrypted successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to encrypt file: {e}")
            return {
                'success': False,
                'error': f'Failed to encrypt file: {str(e)}'
            }
    
    def decrypt_file_for_user(self, encrypted_data: bytes, user_id: str) -> Dict[str, Any]:
        """
        Giải mã file cho user
        
        Args:
            encrypted_data: Dữ liệu đã mã hóa
            user_id: User ID
            
        Returns:
            Dict with decrypted data
        """
        try:
            # Lấy active public key
            keys_result = self.get_active_keys()
            if not keys_result['success']:
                return keys_result
            
            # Lấy user private key
            private_key_result = self.get_user_private_key(user_id)
            if not private_key_result['success']:
                return private_key_result
            
            # Tạo temp files
            temp_dir = tempfile.mkdtemp()
            
            public_key_path = os.path.join(temp_dir, 'public_key.key')
            private_key_path = os.path.join(temp_dir, 'private_key.key')
            encrypted_file_path = os.path.join(temp_dir, 'encrypted_file.enc')
            decrypted_file_path = os.path.join(temp_dir, 'decrypted_file.txt')
            
            # Write keys and encrypted data to temp files
            with open(public_key_path, 'wb') as f:
                f.write(keys_result['public_key'])
            
            with open(private_key_path, 'wb') as f:
                f.write(private_key_result['private_key'])
            
            with open(encrypted_file_path, 'wb') as f:
                f.write(encrypted_data)
            
            # Decrypt file
            abe_lib.decrypt(public_key_path, private_key_path, encrypted_file_path, decrypted_file_path)
            
            # Read decrypted data
            with open(decrypted_file_path, 'rb') as f:
                decrypted_data = f.read()
            
            # Cleanup temp files
            import shutil
            shutil.rmtree(temp_dir)
            
            logger.info(f"File decrypted for user: {user_id}")
            
            return {
                'success': True,
                'decrypted_data': decrypted_data,
                'message': 'File decrypted successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to decrypt file for user {user_id}: {e}")
            return {
                'success': False,
                'error': f'Failed to decrypt file: {str(e)}'
            }

# Global CA instance
central_authority = CentralAuthority()
