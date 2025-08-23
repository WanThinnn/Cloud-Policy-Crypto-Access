"""
Super Admin module for managing users and attributes
"""
import uuid
import hashlib
import bcrypt
import random
from datetime import datetime
from typing import Dict, Any, List, Optional
from firebase_admin import firestore
from .database import db
from .user_management import UserManager
from .attribute_validator import attribute_validator

class SuperAdmin:
    """
    SuperUser system for managing users and their attributes
    """
    
    def __init__(self):
        self.users_collection = db.collection('users')
        self.attributes_collection = db.collection('user_attributes')
        self.attribute_schema_collection = db.collection('attributes_schema')
        self.super_admin_collection = db.collection('super_admin')
        
        # Initialize attribute schema if not exists
        self._initialize_attribute_schema()
    
    def _generate_super_admin_id(self) -> str:
        """Generate SuperAdmin ID with format 21520001, 21520002, ..."""
        try:
            # Get all existing super admin documents
            admins = self.super_admin_collection.stream()
            admin_ids = []
            
            for admin in admins:
                admin_id = admin.id
                # Extract numeric part if it follows the pattern 2152xxxx
                if admin_id.startswith('2152') and len(admin_id) == 8:
                    try:
                        numeric_part = int(admin_id[4:])  # Extract last 4 digits
                        admin_ids.append(numeric_part)
                    except ValueError:
                        continue
            
            if admin_ids:
                # Get max ID and increment
                max_id = max(admin_ids)
                new_id = max_id + 1
            else:
                # Start from 1 if no existing IDs
                new_id = 1
            
            return f"2152{new_id:04d}"  # Format as 21520001, 21520002, etc.
            
        except Exception as e:
            # Fallback to random generation if query fails
            import random
            random_suffix = random.randint(1000, 9999)
            return f"2152{random_suffix}"
    
    def _generate_user_id(self) -> str:
        """Generate User ID with format 22520001, 22520002, ..."""
        try:
            # Get all existing user documents
            users = self.users_collection.stream()
            user_ids = []
            
            for user in users:
                user_id = user.id
                # Extract numeric part if it follows the pattern 2252xxxx
                if user_id.startswith('2252') and len(user_id) == 8:
                    try:
                        numeric_part = int(user_id[4:])  # Extract last 4 digits
                        user_ids.append(numeric_part)
                    except ValueError:
                        continue
            
            if user_ids:
                # Get max ID and increment
                max_id = max(user_ids)
                new_id = max_id + 1
            else:
                # Start from 1 if no existing IDs
                new_id = 1
            
            return f"2252{new_id:04d}"  # Format as 22520001, 22520002, etc.
            
        except Exception as e:
            # Fallback to random generation if query fails
            import random
            random_suffix = random.randint(1000, 9999)
            return f"2252{random_suffix}"
    
    def _initialize_attribute_schema(self):
        """Initialize default attribute schema"""
        try:
            # Check if schema exists
            schema_doc = self.attribute_schema_collection.document('default').get()
            
            if not schema_doc.exists:
                default_schema = {
                    'schema_id': 'default',
                    'version': '1.0',
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow(),
                    'attributes': {
                        # Role attributes - Corporate roles
                        'role': {
                            'type': 'single_choice',
                            'required': True,
                            'description': 'Employee role in the organization',
                            'values': ['employee', 'manager', 'it_admin', 'hr_staff', 'finance_staff', 'executive']
                        },
                        
                        # Department attributes - Corporate departments
                        'department': {
                            'type': 'single_choice',
                            'required': True,
                            'description': 'Department/Division assignment',
                            'values': ['it', 'hr', 'finance', 'sales', 'marketing', 'operations']
                        },
                        
                        # Clearance level - Corporate security levels
                        'clearance_level': {
                            'type': 'single_choice',
                            'required': True,
                            'description': 'Security clearance level',
                            'values': ['low', 'medium', 'high', 'top_secret']
                        },
                        
                        # Specialization - Professional skills/expertise
                        'specialization': {
                            'type': 'multiple_choice',
                            'required': False,
                            'description': 'Professional specialization and skills',
                            'values': ['management', 'technical', 'analytics', 'customer_service', 'project_management', 'business_development']
                        },
                        
                        # Years of experience
                        'experience_years': {
                            'type': 'range',
                            'required': False,
                            'description': 'Years of professional experience',
                            'min_value': 0,
                            'max_value': 50
                        },
                        
                        # Location - Office locations
                        'location': {
                            'type': 'single_choice',
                            'required': False,
                            'description': 'Primary work location',
                            'values': ['hanoi', 'hcm', 'remote', 'hybrid']
                        },
                        
                        # Shift assignment
                        'shift': {
                            'type': 'single_choice',
                            'required': False,
                            'description': 'Work shift assignment',
                            'values': ['day', 'night', 'rotating', 'on_call']
                        },
                        
                        # Data access level
                        'data_access': {
                            'type': 'single_choice',
                            'required': True,
                            'description': 'Data access classification',
                            'values': ['public', 'internal', 'confidential', 'restricted', 'top_secret']
                        }
                    }
                }
                
                self.attribute_schema_collection.document('default').set(default_schema)
                print("✅ Attribute schema initialized successfully")
                
        except Exception as e:
            print(f"❌ Error initializing attribute schema: {e}")
    
    def create_super_admin(self, username: str, email: str, password: str) -> Dict[str, Any]:
        """
        Create SuperAdmin account (Multiple SuperAdmins allowed)
        """
        try:
            # Check if username already exists among SuperAdmins
            existing_by_username = self.super_admin_collection.where('username', '==', username).limit(1).get()
            if list(existing_by_username):
                return {
                    'success': False,
                    'error': f'SuperAdmin with username "{username}" already exists'
                }
                
            # Check if email already exists among SuperAdmins
            existing_by_email = self.super_admin_collection.where('email', '==', email).limit(1).get()
            if list(existing_by_email):
                return {
                    'success': False,
                    'error': f'SuperAdmin with email "{email}" already exists'
                }
            
            # Validate inputs
            if not UserManager.validate_username(username):
                return {
                    'success': False,
                    'error': 'Invalid username format'
                }
            
            if not UserManager.validate_email(email):
                return {
                    'success': False,
                    'error': 'Invalid email format'
                }
            
            password_validation = UserManager.validate_password(password)
            if not password_validation['valid']:
                return {
                    'success': False,
                    'error': 'Password requirements not met',
                    'details': password_validation['errors']
                }
            
            # Create super admin with custom ID format
            admin_id = self._generate_super_admin_id()
            hashed_password = UserManager.hash_password(password)
            
            admin_data = {
                'id': admin_id,
                'username': username,
                'email': email,
                'password': hashed_password,
                'role': 'super_admin',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'is_active': True,
                'permissions': ['all']
            }
            
            # Save to super_admin collection
            self.super_admin_collection.document(admin_id).set(admin_data)
            
            # Also add to users collection with super admin role
            user_data = admin_data.copy()
            user_data['user_type'] = 'super_admin'
            self.users_collection.document(admin_id).set(user_data)
            
            # Set super admin attributes with corporate schema
            self.set_user_attributes(admin_id, {
                'role': 'executive',
                'department': 'operations',
                'clearance_level': 'top_secret',
                'data_access': 'top_secret'
            })
            
            return {
                'success': True,
                'message': 'Super admin created successfully',
                'admin_id': admin_id
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to create super admin: {str(e)}'
            }
    
    def authenticate_super_admin(self, username: str, password: str) -> Dict[str, Any]:
        """
        Authenticate super admin login
        """
        try:
            # Find admin by username or email
            query = self.super_admin_collection.where('username', '==', username).limit(1).get()
            
            if not query:
                # Try email
                query = self.super_admin_collection.where('email', '==', username).limit(1).get()
            
            if not query:
                return {
                    'success': False,
                    'error': 'Super admin not found'
                }
            
            admin_doc = query[0]
            admin_data = admin_doc.to_dict()
            
            # Verify password
            if not UserManager.verify_password(password, admin_data['password']):
                return {
                    'success': False,
                    'error': 'Invalid credentials'
                }
            
            # Check if active
            if not admin_data.get('is_active', False):
                return {
                    'success': False,
                    'error': 'Super admin account is disabled'
                }
            
            # Update last login
            self.super_admin_collection.document(admin_data['id']).update({
                'last_login': datetime.utcnow()
            })
            
            # Return admin info without password
            admin_response = admin_data.copy()
            del admin_response['password']
            
            return {
                'success': True,
                'admin': admin_response,
                'message': 'Super admin authenticated successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Authentication failed: {str(e)}'
            }
    
    def create_user_account(self, admin_id: str, user_data: Dict[str, Any], user_attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create new user account (only by SuperAdmin)
        UserID will be automatically used as Username (format: 2252xxxx)
        """
        try:
            # Verify admin permissions
            if not self._verify_super_admin(admin_id):
                return {
                    'success': False,
                    'error': 'Unauthorized: Super admin access required'
                }
            
            # Validate required fields (username không cần nữa vì tự động generate)
            required_fields = ['email', 'password', 'full_name']
            for field in required_fields:
                if field not in user_data:
                    return {
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }
            
            if not UserManager.validate_email(user_data['email']):
                return {
                    'success': False,
                    'error': 'Invalid email format'
                }
            
            password_validation = UserManager.validate_password(user_data['password'])
            if not password_validation['valid']:
                return {
                    'success': False,
                    'error': 'Password requirements not met',
                    'details': password_validation['errors']
                }
            
            # Check for existing email only (username sẽ tự động unique vì là user_id)
            existing_email = list(self.users_collection.where('email', '==', user_data['email']).limit(1).get())
            if existing_email:
                return {
                    'success': False,
                    'error': 'Email already exists'
                }
            
            # Validate attributes against schema
            schema_validation = self._validate_user_attributes(user_attributes)
            if not schema_validation['valid']:
                return {
                    'success': False,
                    'error': 'Invalid user attributes',
                    'details': schema_validation['errors']
                }
            
            # Generate user_id and use it as username
            user_id = self._generate_user_id()
            username = user_id  # UserID chính là Username
            hashed_password = UserManager.hash_password(user_data['password'])
            
            final_user_data = {
                'id': user_id,
                'username': username,  # Username = UserID (2252xxxx)
                'email': user_data['email'],
                'password': hashed_password,
                'full_name': user_data['full_name'],
                'phone': user_data.get('phone', ''),
                'user_type': 'regular',
                'created_by': admin_id,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'is_active': True,
                'must_change_password': True,  # Force password change on first login
                'password_changed_at': None    # Track when password was changed
            }
            
            # Save user to Firestore
            self.users_collection.document(user_id).set(final_user_data)
            
            # Set user attributes
            self.set_user_attributes(user_id, user_attributes, admin_id)
            
            # Return response without password
            user_response = final_user_data.copy()
            del user_response['password']
            user_response['attributes'] = user_attributes
            
            return {
                'success': True,
                'user': user_response,
                'message': 'User account created successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to create user account: {str(e)}'
            }
    
    def set_user_attributes(self, user_id: str, attributes: Dict[str, Any], admin_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Set attributes for a user
        """
        try:
            # Validate attributes against schema
            schema_validation = self._validate_user_attributes(attributes)
            if not schema_validation['valid']:
                return {
                    'success': False,
                    'error': 'Invalid attributes',
                    'details': schema_validation['errors']
                }
            
            # Prepare attribute document
            attr_data = {
                'user_id': user_id,
                'attributes': attributes,
                'updated_by': admin_id or 'system',
                'updated_at': datetime.utcnow()
            }
            
            # Use consistent document ID format: UA+UserID
            attr_document_id = f"UA{user_id}"
            
            # Create or update with consistent document ID
            self.attributes_collection.document(attr_document_id).set(attr_data)
            
            return {
                'success': True,
                'message': 'User attributes updated successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to set user attributes: {str(e)}'
            }
    
    def get_user_attributes(self, user_id: str) -> Dict[str, Any]:
        """
        Get attributes for a user
        """
        try:
            # Use consistent document ID format: UA+UserID
            attr_document_id = f"UA{user_id}"
            attr_doc = self.attributes_collection.document(attr_document_id).get()
            
            if not attr_doc.exists:
                return {
                    'success': False,
                    'error': 'User attributes not found'
                }
            
            attr_data = attr_doc.to_dict()
            
            return {
                'success': True,
                'attributes': attr_data['attributes'],
                'updated_at': attr_data['updated_at'],
                'updated_by': attr_data.get('updated_by', 'unknown')
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to get user attributes: {str(e)}'
            }
    
    def list_all_users(self, admin_id: str, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """
        List all users in the system (SuperAdmin only)
        """
        try:
            # Verify admin permissions
            if not self._verify_super_admin(admin_id):
                return {
                    'success': False,
                    'error': 'Unauthorized: Super admin access required'
                }
            
            # Calculate offset
            offset = (page - 1) * limit
            
            # Get users with pagination
            users_query = self.users_collection.where('user_type', '==', 'regular').limit(limit).offset(offset).get()
            
            users_list = []
            for user_doc in users_query:
                user_data = user_doc.to_dict()
                
                # Remove password
                if 'password' in user_data:
                    del user_data['password']
                
                # Get user attributes
                attrs_result = self.get_user_attributes(user_data['id'])
                if attrs_result['success']:
                    user_data['attributes'] = attrs_result['attributes']
                else:
                    user_data['attributes'] = {}
                
                users_list.append(user_data)
            
            # Get total count
            total_users = len(list(self.users_collection.where('user_type', '==', 'regular').get()))
            
            return {
                'success': True,
                'users': users_list,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total_users,
                    'pages': (total_users + limit - 1) // limit
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to list users: {str(e)}'
            }
    
    def update_user_attributes(self, admin_id: str, user_id: str, new_attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update user attributes (SuperAdmin only)
        """
        try:
            # Verify admin permissions
            if not self._verify_super_admin(admin_id):
                return {
                    'success': False,
                    'error': 'Unauthorized: Super admin access required'
                }
            
            # Check if user exists
            user_doc = self.users_collection.document(user_id).get()
            if not user_doc.exists:
                return {
                    'success': False,
                    'error': 'User not found'
                }
            
            # Update attributes
            return self.set_user_attributes(user_id, new_attributes, admin_id)
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to update user attributes: {str(e)}'
            }
    
    def deactivate_user(self, admin_id: str, user_id: str) -> Dict[str, Any]:
        """
        Deactivate user account (SuperAdmin only)
        """
        try:
            # Verify admin permissions
            if not self._verify_super_admin(admin_id):
                return {
                    'success': False,
                    'error': 'Unauthorized: Super admin access required'
                }
            
            # Update user status
            self.users_collection.document(user_id).update({
                'is_active': False,
                'deactivated_by': admin_id,
                'deactivated_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
            
            return {
                'success': True,
                'message': 'User account deactivated successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to deactivate user: {str(e)}'
            }
    
    def get_attribute_schema(self) -> Dict[str, Any]:
        """
        Get the current attribute schema
        """
        try:
            schema_doc = self.attribute_schema_collection.document('default').get()
            
            if not schema_doc.exists:
                return {
                    'success': False,
                    'error': 'Attribute schema not found'
                }
            
            schema_data = schema_doc.to_dict()
            
            return {
                'success': True,
                'schema': schema_data['attributes'],
                'version': schema_data.get('version', '1.0'),
                'updated_at': schema_data.get('updated_at')
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to get attribute schema: {str(e)}'
            }
    
    def _verify_super_admin(self, admin_id: str) -> bool:
        """
        Verify if the user is a valid super admin
        """
        try:
            admin_doc = self.super_admin_collection.document(admin_id).get()
            if not admin_doc.exists:
                return False
            
            admin_data = admin_doc.to_dict()
            return admin_data.get('is_active', False) and admin_data.get('role') == 'super_admin'
            
        except Exception:
            return False
    
    def _validate_user_attributes(self, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate user attributes against database schemas
        """
        try:
            # Use the new attribute validator
            validation_result = attribute_validator.validate_attributes(attributes)
            
            if not validation_result['success']:
                return {
                    'valid': False,
                    'errors': [validation_result.get('error', 'Validation failed')]
                }
            
            return {
                'valid': validation_result['valid'],
                'errors': validation_result.get('errors', []),
                'warnings': validation_result.get('warnings', []),
                'details': validation_result.get('errors', [])  # For backward compatibility
            }
            
        except Exception as e:
            return {
                'valid': False,
                'errors': [f'Validation error: {str(e)}']
            }

# Global instance
super_admin = SuperAdmin()
