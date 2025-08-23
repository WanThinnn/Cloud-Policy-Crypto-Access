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
from .crypto_utils import CryptoUtils
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
        self.policies_collection = db.collection('access_policies')
        self.user_attributes_collection = db.collection('user_attributes')
        
        # Local key storage path
        self.local_keys_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'abe_keys')
        self.master_key_path = os.path.join(self.local_keys_dir, 'master_key.key')
        self.public_key_path = os.path.join(self.local_keys_dir, 'public_key.key')
        self.setup_info_path = os.path.join(self.local_keys_dir, 'setup_info.json')
        
        # Ensure local keys directory exists
        os.makedirs(self.local_keys_dir, exist_ok=True)
        
    def setup_abe_system(self) -> Dict[str, Any]:
        """
        Setup ABE system - tạo master key và public key (chỉ tạo 1 lần duy nhất)
        Lưu keys ở local thay vì cloud để tăng bảo mật
        
        Returns:
            Dict with success status and keys info
        """
        try:
            # Kiểm tra xem đã có keys ở local chưa
            existing_keys = self.get_active_keys()
            if existing_keys['success'] and existing_keys['has_public_key'] and existing_keys['has_master_key']:
                logger.info("ABE system already setup with local keys")
                return {
                    'success': True,
                    'setup_id': existing_keys['setup_id'],
                    'message': 'ABE system already setup with local keys',
                    'already_exists': True,
                    'storage': 'local'
                }
            
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
            temp_public_key_path = os.path.join(setup_dir, 'public_key.key')
            temp_master_key_path = os.path.join(setup_dir, 'master_key.key')
            
            # Copy keys to local storage
            import shutil
            shutil.copy2(temp_public_key_path, self.public_key_path)
            shutil.copy2(temp_master_key_path, self.master_key_path)
            
            # Tạo setup info
            setup_id = str(uuid.uuid4())
            setup_info = {
                'setup_id': setup_id,
                'created_at': datetime.utcnow().isoformat(),
                'storage_type': 'local',
                'master_key_path': self.master_key_path,
                'public_key_path': self.public_key_path
            }
            
            # Lưu setup info
            import json
            with open(self.setup_info_path, 'w') as f:
                json.dump(setup_info, f, indent=2)
            
            # Cleanup temp files
            shutil.rmtree(temp_dir)
            
            logger.info(f"ABE system setup completed with ID: {setup_id} (local storage)")
            
            return {
                'success': True,
                'setup_id': setup_id,
                'message': 'ABE system setup completed successfully (local storage)',
                'storage': 'local'
            }
            
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
        Lấy active public key và master key từ local storage
        
        Returns:
            Dict with keys data
        """
        try:
            # Kiểm tra setup info file
            if not os.path.exists(self.setup_info_path):
                return {
                    'success': False,
                    'error': 'No setup info found. Please setup ABE system first.'
                }
            
            # Đọc setup info
            import json
            with open(self.setup_info_path, 'r') as f:
                setup_info = json.load(f)
            
            # Kiểm tra key files
            has_public_key = os.path.exists(self.public_key_path)
            has_master_key = os.path.exists(self.master_key_path)
            
            if not has_public_key or not has_master_key:
                return {
                    'success': False,
                    'error': 'Key files not found. Please setup ABE system first.'
                }
            
            # Đọc key data nếu cần
            public_key_data = None
            master_key_data = None
            
            if has_public_key:
                with open(self.public_key_path, 'rb') as f:
                    public_key_data = f.read()
            
            if has_master_key:
                with open(self.master_key_path, 'rb') as f:
                    master_key_data = f.read()
            
            return {
                'success': True,
                'setup_id': setup_info['setup_id'],
                'has_public_key': has_public_key,
                'has_master_key': has_master_key,
                'public_key': public_key_data,
                'master_key': master_key_data,
                'storage_type': 'local',
                'message': 'Active keys found (local storage)'
            }
            
        except Exception as e:
            logger.error(f"Failed to get active keys: {e}")
            return {
                'success': False,
                'error': f'Failed to get active keys: {str(e)}'
            }
    
    def generate_user_private_key(self, user_id: str, password: str, user_attributes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Tạo/Update private key cho user dựa trên attributes
        - Chỉ có 1 private key duy nhất per user
        - Regenerate khi có attributes mới
        - Keep existing key nếu attributes không đổi
        
        Args:
            user_id: User ID
            password: User password để mã hóa private key
            user_attributes: Dict with user attributes (optional, for direct input)
            
        Returns:
            Dict with private key data
        """
        try:
            # Convert user_attributes to consistent format
            if isinstance(user_attributes, dict):
                # If dict, convert values to list format
                attr_list = []
                for key, value in user_attributes.items():
                    if isinstance(value, list):
                        for v in value:
                            attr_list.append(f"{key}:{v}")
                    else:
                        attr_list.append(f"{key}:{value}")
                user_attributes_list = attr_list
            elif isinstance(user_attributes, list):
                user_attributes_list = user_attributes
            else:
                user_attributes_list = []
            
            # 1. Check existing private key
            existing_key_result = self.get_user_private_key(user_id)
            
            if existing_key_result['success']:
                existing_attributes = set(existing_key_result['key_data'].get('attributes', []))
                new_attributes = set(user_attributes_list)
                
                # Compare attributes
                if existing_attributes == new_attributes:
                    logger.info(f"Private key for user {user_id} already exists with same attributes")
                    return {
                        'success': True,
                        'message': 'Private key already exists with same attributes',
                        'private_key_id': existing_key_result['key_data']['private_key_id'],
                        'attributes': user_attributes_list,
                        'action': 'kept_existing'
                    }
                else:
                    logger.info(f"User {user_id} attributes changed, regenerating private key")
                    # Continue to regenerate with new attributes
            
            # 2. Lấy active keys
            keys_result = self.get_active_keys()
            if not keys_result['success']:
                return keys_result
            
            # 3. Tạo temp files
            temp_dir = tempfile.mkdtemp()
            
            public_key_path = os.path.join(temp_dir, 'public_key.key')
            master_key_path = os.path.join(temp_dir, 'master_key.key')
            private_key_path = os.path.join(temp_dir, 'private_key.key')
            
            # Write keys to temp files
            with open(public_key_path, 'wb') as f:
                f.write(keys_result['public_key'])
            
            with open(master_key_path, 'wb') as f:
                f.write(keys_result['master_key'])
            
            # 4. Check ABE library availability
            if not abe_lib:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
                return {
                    'success': False,
                    'error': 'ABE library not loaded. Please check library installation.'
                }
            
            if not hasattr(abe_lib, 'generate_secret_key'):
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
                return {
                    'success': False,
                    'error': 'ABE library method generate_secret_key not available.'
                }
                
            # 5. Generate private key với ABE library
            try:
                attributes_str = ' '.join(user_attributes_list)
                logger.info(f"Generating private key for user {user_id} with attributes: {attributes_str}")
                logger.info(f"Temp files: pub={public_key_path}, master={master_key_path}, private={private_key_path}")
                
                abe_lib.generate_secret_key(public_key_path, master_key_path, attributes_str, private_key_path)
                
                # Check if private key file was created
                if not os.path.exists(private_key_path):
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return {
                        'success': False,
                        'error': f'Private key file was not created at {private_key_path}'
                    }
                
            except Exception as abe_error:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.error(f"ABE library error: {abe_error}")
                return {
                    'success': False,
                    'error': f'Failed to generate private key: {str(abe_error)}'
                }
            
            # Read generated private key
            with open(private_key_path, 'rb') as f:
                private_key_data = f.read()
            
            # 5. Save user private key to Firestore (REPLACE existing)
            user_key_doc = {
                'user_id': user_id,
                'private_key': private_key_data,
                'attributes': user_attributes_list,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'is_active': True,
                'key_version': 1  # For future versioning if needed
            }
            
            # 6. CRITICAL: Remove ALL old private keys for this user (ensure uniqueness)
            old_keys = self.keys_collection.where('user_id', '==', user_id).get()
            deleted_count = 0
            for old_key in old_keys:
                self.keys_collection.document(old_key.id).delete()
                deleted_count += 1
                
            logger.info(f"Deleted {deleted_count} old private keys for user {user_id}")
            
            # 7. Save the ONE AND ONLY private key for this user
            private_key_id = f"privkey_{user_id}_{int(datetime.utcnow().timestamp())}"
            self.keys_collection.document(private_key_id).set(user_key_doc)
            
            # 8. Cleanup temp files
            import shutil
            shutil.rmtree(temp_dir)
            
            logger.info(f"Private key generated/updated for user: {user_id} with {len(user_attributes_list)} attributes")
            
            return {
                'success': True,
                'private_key_id': private_key_id,
                'attributes': user_attributes_list,
                'message': 'Private key generated/updated successfully',
                'action': 'generated_new',
                'old_keys_removed': deleted_count
            }
            
        except Exception as e:
            logger.error(f"Failed to generate private key: {e}")
            return {
                'success': False,
                'error': f'Failed to generate private key: {str(e)}'
            }
    
    def get_user_private_key(self, user_id: str) -> Dict[str, Any]:
        """
        Lấy private key của user (chỉ có 1 key duy nhất per user)
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with private key data
        """
        try:
            # Query for user's active private key (should only be 1)
            user_keys = self.keys_collection.where('user_id', '==', user_id)\
                                           .where('is_active', '==', True)\
                                           .get()
            
            if not user_keys:
                return {
                    'success': False,
                    'error': 'User private key not found',
                    'has_key': False
                }
                
            if len(user_keys) > 1:
                logger.warning(f"User {user_id} has {len(user_keys)} active private keys, should only have 1")
            
            # Get the first (should be only) key
            key_doc = user_keys[0]
            key_data = key_doc.to_dict()
            key_data['private_key_id'] = key_doc.id
            
            return {
                'success': True,
                'has_key': True,
                'private_key': key_data['encrypted_blob'],
                'attributes': key_data['attributes'],
                'created_at': key_data.get('created_at'),
                'updated_at': key_data.get('updated_at'),
                'key_data': key_data
            }
            
        except Exception as e:
            logger.error(f"Failed to get user private key: {e}")
            return {
                'success': False,
                'error': f'Failed to get user private key: {str(e)}',
                'has_key': False
            }
    
    def check_user_private_key_status(self, user_id: str, current_attributes: List[str]) -> Dict[str, Any]:
        """
        Kiểm tra trạng thái private key của user và xem có cần update không
        
        Args:
            user_id: User ID
            current_attributes: Current attributes of user
            
        Returns:
            Dict with key status and recommendations
        """
        try:
            existing_key_result = self.get_user_private_key(user_id)
            
            if not existing_key_result['success']:
                return {
                    'success': True,
                    'has_key': False,
                    'needs_generation': True,
                    'needs_update': False,
                    'recommendation': 'GENERATE_NEW',
                    'reason': 'No private key exists'
                }
            
            existing_attributes = set(existing_key_result['attributes'])
            new_attributes = set(current_attributes)
            
            if existing_attributes == new_attributes:
                return {
                    'success': True,
                    'has_key': True,
                    'needs_generation': False,
                    'needs_update': False,
                    'recommendation': 'KEEP_EXISTING',
                    'reason': 'Attributes unchanged',
                    'existing_attributes': list(existing_attributes)
                }
            else:
                added_attrs = new_attributes - existing_attributes
                removed_attrs = existing_attributes - new_attributes
                
                return {
                    'success': True,
                    'has_key': True,
                    'needs_generation': False,
                    'needs_update': True,
                    'recommendation': 'UPDATE_REQUIRED',
                    'reason': 'Attributes changed',
                    'existing_attributes': list(existing_attributes),
                    'new_attributes': list(new_attributes),
                    'added_attributes': list(added_attrs),
                    'removed_attributes': list(removed_attrs)
                }
                
        except Exception as e:
            logger.error(f"Failed to check private key status: {e}")
            return {
                'success': False,
                'error': f'Failed to check private key status: {str(e)}'
            }
    
    def generate_encrypted_user_private_key(self, user_id: str, password: str, attributes: List[str]) -> Dict[str, Any]:
        """
        Tạo và mã hóa private key cho user bằng password
        
        Args:
            user_id: User ID
            password: User password để mã hóa private key
            attributes: List of attributes ['role:doctor', 'department:cardiology']
            
        Returns:
            Dict with success status and encrypted key info
        """
        try:
            # Kiểm tra xem user đã có private key chưa
            existing_key = self.check_user_has_private_key(user_id)
            if existing_key['has_key']:
                return {
                    'success': False,
                    'error': 'User already has a private key. Use password authentication to retrieve it.',
                    'has_existing_key': True
                }
            
            # Validate password strength
            password_check = CryptoUtils.verify_password_strength(password)
            if not password_check['is_valid']:
                return {
                    'success': False,
                    'error': 'Password does not meet security requirements',
                    'password_errors': password_check['errors']
                }
            
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
            if abe_lib and abe_lib.is_loaded():
                abe_lib.generate_secret_key(public_key_path, master_key_path, attributes_str, private_key_path)
            else:
                # Fallback for testing without ABE library
                with open(private_key_path, 'wb') as f:
                    f.write(b"dummy_private_key_for_testing")
            
            # Read generated private key
            with open(private_key_path, 'rb') as f:
                private_key_data = f.read()
            
            # Encrypt private key with password
            encrypted_key_info = CryptoUtils.encrypt_private_key(private_key_data, password)
            
            # Save encrypted user private key to Firestore với minimal metadata
            user_key_doc = {
                'user_id': user_id,
                'encrypted_blob': encrypted_key_info['encrypted_blob'],
                'algorithm': encrypted_key_info['algorithm'],
                'attributes': attributes,
                'created_at': datetime.utcnow(),
                'is_active': True
            }
            
            # Save new encrypted private key with consistent format
            private_key_id = f"privkey_{user_id}_{int(datetime.utcnow().timestamp())}"
            self.keys_collection.document(private_key_id).set(user_key_doc)
            
            # Cleanup temp files
            import shutil
            shutil.rmtree(temp_dir)
            
            logger.info(f"Encrypted private key generated for user: {user_id}")
            
            return {
                'success': True,
                'private_key_id': private_key_id,
                'attributes': attributes,
                'message': 'Encrypted private key generated and saved to cloud successfully (minimal metadata)'
            }
            
        except Exception as e:
            logger.error(f"Failed to generate encrypted private key: {e}")
            return {
                'success': False,
                'error': f'Failed to generate encrypted private key: {str(e)}'
            }
    
    def get_user_private_key_with_password(self, user_id: str, password: str) -> Dict[str, Any]:
        """
        Lấy và giải mã private key của user bằng password
        
        Args:
            user_id: User ID
            password: User password để giải mã
            
        Returns:
            Dict with decrypted private key data
        """
        try:
            # Tìm encrypted private key của user
            user_keys = self.keys_collection.where('user_id', '==', user_id)\
                                           .where('is_active', '==', True)\
                                           .limit(1).get()
            
            if not user_keys:
                return {
                    'success': False,
                    'error': 'User encrypted private key not found. Please generate a private key first.'
                }
            
            key_data = user_keys[0].to_dict()
            
            # Extract encrypted blob
            encrypted_blob = key_data['encrypted_blob']
            
            # Decrypt private key using new method
            private_key_data = CryptoUtils.decrypt_private_key_from_blob(encrypted_blob, password)
            
            logger.info(f"Private key decrypted successfully for user: {user_id}")
            
            return {
                'success': True,
                'private_key': private_key_data,
                'attributes': key_data['attributes'],
                'message': 'Private key retrieved and decrypted successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to get user private key with password: {e}")
            if "decryption failed" in str(e).lower() or "authentication" in str(e).lower():
                return {
                    'success': False,
                    'error': 'Invalid password. Please check your password and try again.',
                    'is_auth_error': True
                }
            return {
                'success': False,
                'error': f'Failed to retrieve private key: {str(e)}'
            }
    
    def check_user_has_private_key(self, user_id: str) -> Dict[str, Any]:
        """
        Kiểm tra user đã có private key chưa
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with check results
        """
        try:
            user_keys = self.keys_collection.where('user_id', '==', user_id)\
                                           .where('is_active', '==', True)\
                                           .limit(1).get()
            
            has_key = len(user_keys) > 0
            key_info = None
            
            if has_key:
                key_data = user_keys[0].to_dict()
                key_info = {
                    'created_at': key_data.get('created_at'),
                    'attributes': key_data.get('attributes', []),
                    'algorithm': key_data.get('algorithm', 'AES-256-GCM')
                }
            
            return {
                'success': True,
                'has_key': has_key,
                'key_info': key_info
            }
            
        except Exception as e:
            logger.error(f"Failed to check user private key: {e}")
            return {
                'success': False,
                'error': f'Failed to check user private key: {str(e)}'
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
            # Check ABE library availability
            if not abe_lib or not abe_lib.is_loaded():
                return {
                    'success': False,
                    'error': 'ABE library not loaded. Please check library installation.'
                }
            
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
            
            # Encrypt file with error checking
            try:
                abe_lib.encrypt(public_key_path, file_path, policy, encrypted_file_path)
                
                # Check if encrypted file was created
                if not os.path.exists(encrypted_file_path):
                    raise FileNotFoundError("ABE encryption did not produce output file")
                    
            except Exception as encrypt_error:
                logger.error(f"ABE encryption failed: {encrypt_error}")
                raise encrypt_error
            
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
            if not abe_lib:
                import shutil
                shutil.rmtree(temp_dir)
                return {
                    'success': False,
                    'error': 'ABE library not loaded'
                }
                
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
