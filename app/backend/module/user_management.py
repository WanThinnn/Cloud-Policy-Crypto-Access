"""
User management module for authentication and user operations
"""
import hashlib
import bcrypt
import uuid
import re
from datetime import datetime
from typing import Optional, Dict, Any
from firebase_admin import firestore
from .database import db

class UserManager:
    """Class quản lý người dùng"""
    
    def __init__(self):
        self.collection = db.collection('users')
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Mã hóa password với bcrypt(sha3-512(password))
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        # Step 1: SHA-3-512 hash
        sha3_512_hash = hashlib.sha3_512(password.encode('utf-8')).hexdigest()

        # Step 2: bcrypt hash
        bcrypt_hash = bcrypt.hashpw(sha3_512_hash.encode('utf-8'), bcrypt.gensalt())

        return bcrypt_hash.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """
        Xác thực password
        
        Args:
            password: Plain text password
            hashed_password: Stored hashed password
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            # Step 1: SHA-3-512 hash
            sha3_512_hash = hashlib.sha3_512(password.encode('utf-8')).hexdigest()

            # Step 2: Verify with bcrypt
            return bcrypt.checkpw(sha3_512_hash.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception:
            return False
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate username (3-30 chars, alphanumeric + underscore)"""
        pattern = r'^[a-zA-Z0-9_]{3,30}$'
        return bool(re.match(pattern, username))
    
    @staticmethod
    def validate_password(password: str) -> Dict[str, Any]:
        """
        Validate password strength
        Returns dict with validation result and requirements
        """
        result = {
            'valid': True,
            'errors': [],
            'requirements': {
                'min_length': len(password) >= 8,
                'has_upper': bool(re.search(r'[A-Z]', password)),
                'has_lower': bool(re.search(r'[a-z]', password)),
                'has_digit': bool(re.search(r'\d', password)),
                'has_special': bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
            }
        }
        
        if not result['requirements']['min_length']:
            result['errors'].append('Password must be at least 8 characters long')
        
        if not result['requirements']['has_upper']:
            result['errors'].append('Password must contain at least one uppercase letter')
            
        if not result['requirements']['has_lower']:
            result['errors'].append('Password must contain at least one lowercase letter')
            
        if not result['requirements']['has_digit']:
            result['errors'].append('Password must contain at least one digit')
            
        if not result['requirements']['has_special']:
            result['errors'].append('Password must contain at least one special character')
        
        result['valid'] = len(result['errors']) == 0
        return result
    
    # Disable user_management.create_user()
    async def create_user(self, username: str, email: str, password: str):
        return {
            'success': False,
            'error': 'Self-registration is disabled. Contact system administrator.',
            'redirect': '/admin/contact'
        }
    
    async def authenticate_user(self, username: str, password: str) -> Dict[str, Any]:
        """
        Xác thực user đăng nhập
        
        Args:
            username: Username hoặc email
            password: Plain text password
            
        Returns:
            Dict with authentication result
        """
        try:
            # Try to find user by username or email
            user_doc = None
            
            # Search by username
            username_query = self.collection.where('username', '==', username).limit(1).get()
            if len(username_query) > 0:
                user_doc = username_query[0]
            else:
                # Search by email if not found by username
                email_query = self.collection.where('email', '==', username).limit(1).get()
                if len(email_query) > 0:
                    user_doc = email_query[0]
            
            if not user_doc:
                return {
                    'success': False,
                    'error': 'User not found.'
                }
            
            user_data = user_doc.to_dict()
            
            # Check if user is active
            if not user_data.get('is_active', True):
                return {
                    'success': False,
                    'error': 'User account is deactivated.'
                }
            
            # Verify password
            if not self.verify_password(password, user_data['password']):
                return {
                    'success': False,
                    'error': 'Invalid password.'
                }
            
            # Update last login
            self.collection.document(user_data['id']).update({
                'last_login': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
            
            # Return user data without password
            user_response = user_data.copy()
            del user_response['password']
            
            # Check if user must change password
            must_change_password = user_data.get('must_change_password', False)
            
            return {
                'success': True,
                'user': user_response,
                'user_id': user_data['id'],
                'must_change_password': must_change_password,
                'message': 'Authentication successful.'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Authentication failed: {str(e)}'
            }
    
    async def get_user(self, user_id: str) -> Dict[str, Any]:
        """
        Lấy thông tin user theo ID
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with user data or error
        """
        try:
            user_doc = self.collection.document(user_id).get()
            
            if not user_doc.exists:
                return {
                    'success': False,
                    'error': 'User not found.'
                }
            
            user_data = user_doc.to_dict()
            
            # Remove password from response
            del user_data['password']
            
            return {
                'success': True,
                'user': user_data
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to get user: {str(e)}'
            }
    
    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cập nhật thông tin user
        
        Args:
            user_id: User ID
            updates: Dict containing fields to update
            
        Returns:
            Dict with success status and updated user data
        """
        try:
            # Check if user exists
            user_doc = self.collection.document(user_id).get()
            if not user_doc.exists:
                return {
                    'success': False,
                    'error': 'User not found.'
                }
            
            # Prepare allowed updates
            allowed_fields = ['email', 'is_active']
            filtered_updates = {}
            
            for field, value in updates.items():
                if field in allowed_fields:
                    if field == 'email' and not self.validate_email(value):
                        return {
                            'success': False,
                            'error': 'Invalid email format.'
                        }
                    filtered_updates[field] = value
            
            if not filtered_updates:
                return {
                    'success': False,
                    'error': 'No valid fields to update.'
                }
            
            # Add updated timestamp
            filtered_updates['updated_at'] = datetime.utcnow()
            
            # Update user
            self.collection.document(user_id).update(filtered_updates)
            
            # Get updated user data
            updated_user = await self.get_user(user_id)
            
            return {
                'success': True,
                'user': updated_user['user'],
                'message': 'User updated successfully.'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to update user: {str(e)}'
            }
    
    async def change_password(self, user_id: str, old_password: str, new_password: str) -> Dict[str, Any]:
        """
        Đổi mật khẩu
        
        Args:
            user_id: User ID
            old_password: Current password
            new_password: New password
            
        Returns:
            Dict with success status
        """
        try:
            # Get user data
            user_doc = self.collection.document(user_id).get()
            if not user_doc.exists:
                return {
                    'success': False,
                    'error': 'User not found.'
                }
            
            user_data = user_doc.to_dict()
            
            # Verify old password
            if not self.verify_password(old_password, user_data['password']):
                return {
                    'success': False,
                    'error': 'Current password is incorrect.'
                }
            
            # Validate new password
            password_validation = self.validate_password(new_password)
            if not password_validation['valid']:
                return {
                    'success': False,
                    'error': 'New password requirements not met.',
                    'details': password_validation['errors']
                }
            
            # Hash new password
            new_hashed_password = self.hash_password(new_password)
            
            # Update password
            self.collection.document(user_id).update({
                'password': new_hashed_password,
                'updated_at': datetime.utcnow()
            })
            
            return {
                'success': True,
                'message': 'Password changed successfully.'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to change password: {str(e)}'
            }

# Global user manager instance
user_manager = UserManager()
