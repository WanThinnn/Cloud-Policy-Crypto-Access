"""
SuperAdmin routes for user management and attribute assignment with JWT authentication
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import logging

# Import modules with fallback for direct execution
try:
    from ..module.super_admin import super_admin
    from ..module.central_authority import central_authority
    from ..module.auth_decorators import super_admin_required, get_current_user
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from module.super_admin import super_admin
    from module.central_authority import central_authority
    from module.auth_decorators import super_admin_required, get_current_user

logger = logging.getLogger(__name__)

super_admin_api = Blueprint('super_admin', __name__, url_prefix='/super-admin')

@super_admin_api.route('/setup', methods=['POST'])
def create_super_admin():
    """Create SuperAdmin account (Multiple SuperAdmins supported)"""
    try:
        data = request.get_json()
        
        required_fields = ['username', 'email', 'password']
        if not all(field in data for field in required_fields):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: username, email, password'
            }), 400
        
        result = super_admin.create_super_admin(
            username=data['username'],
            email=data['email'],
            password=data['password']
        )
        
        status_code = 201 if result['success'] else 400
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to create super admin: {str(e)}'
        }), 500

@super_admin_api.route('/login', methods=['POST'])
def login_super_admin():
    """SuperAdmin login with JWT token generation"""
    try:
        data = request.get_json()
        
        if 'username' not in data or 'password' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing username or password'
            }), 400
        
        result = super_admin.authenticate_super_admin(
            username=data['username'],
            password=data['password']
        )
        
        if result['success']:
            # Generate JWT token for SuperAdmin
            from module.jwt_auth import jwt_manager
            
            admin_data = result['admin']
            token_payload = {
                'id': admin_data['id'],
                'user_id': admin_data['id'],
                'username': admin_data['username'],
                'user_type': 'super_admin',
                'email': admin_data['email'],
                'permissions': admin_data.get('permissions', ['all'])
            }
            
            access_token = jwt_manager.generate_token(token_payload)
            
            return jsonify({
                'success': True,
                'message': 'Super admin authenticated successfully',
                'admin': admin_data,
                'access_token': access_token,
                'token_type': 'Bearer',
                'expires_in': jwt_manager.token_expiry_hours * 3600
            }), 200
        else:
            return jsonify(result), 401
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Login failed: {str(e)}'
        }), 500

@super_admin_api.route('/users', methods=['POST'])
@super_admin_required
def create_user():
    """Create new user account with attributes"""
    try:
        data = request.get_json()
        
        # Get admin info from JWT token
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401
            
        admin_id = current_user.get('admin_id') or current_user.get('user_id')
        if not admin_id:
            return jsonify({
                'success': False,
                'error': 'Admin ID not found in token'
            }), 401
        
        # Validate request data
        if 'user_data' not in data or 'user_attributes' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing user_data or user_attributes'
            }), 400
        
        result = super_admin.create_user_account(
            admin_id=admin_id,
            user_data=data['user_data'],
            user_attributes=data['user_attributes']
        )
        
        # If user created successfully, generate ABE private key
        if result['success']:
            user_id = result['user']['id']
            
            # Convert attributes to ABE format (key:value pairs)
            abe_attributes = []
            for key, value in data['user_attributes'].items():
                if isinstance(value, list):
                    # For multiple values, create separate attributes
                    for val in value:
                        abe_attributes.append(f"{key}:{val}")
                else:
                    abe_attributes.append(f"{key}:{value}")
            
            # Generate encrypted private key
            temp_password = data['user_data']['password']  # Use initial password
            abe_result = central_authority.generate_encrypted_user_private_key(
                user_id=user_id,
                password=temp_password,
                attributes=abe_attributes
            )
            
            if not abe_result['success']:
                # Log warning but don't fail user creation
                result['warning'] = f'User created but ABE key generation failed: {abe_result["error"]}'
        
        status_code = 201 if result['success'] else 400
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to create user: {str(e)}'
        }), 500

# SYSTEM SERVICE ENDPOINTS - For internal service communication
@super_admin_api.route('/system/users', methods=['GET'])
def system_list_users():
    """
    List all users - SYSTEM SERVICE ENDPOINT
    Authentication: Service Token instead of Admin ID
    This endpoint is for internal service communication (CA, File Manager, etc.)
    """
    try:
        # Check service authentication
        auth_header = request.headers.get('Authorization', '')
        service_name = request.headers.get('X-Service-Name', '')
        service_token = None
        
        if auth_header.startswith('Bearer '):
            service_token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        # Verify service token
        import os
        expected_token = os.getenv('SYSTEM_SERVICE_TOKEN', 'ca-service-token-change-in-production')
        
        if not service_token or service_token != expected_token:
            return jsonify({
                'success': False,
                'error': 'Invalid service authentication'
            }), 401
        
        # Valid service names
        valid_services = ['ca-service', 'file-manager', 'abac-service']
        if service_name not in valid_services:
            return jsonify({
                'success': False,
                'error': f'Invalid service name. Valid services: {valid_services}'
            }), 401
        
        # Get all users (no pagination for system services)
        try:
            users_ref = super_admin.users_collection
            users_docs = users_ref.stream()
            
            users_list = []
            for doc in users_docs:
                user_data = doc.to_dict()
                user_data['id'] = doc.id
                
                # Remove sensitive data
                if 'password' in user_data:
                    del user_data['password']
                
                # IMPORTANT: Fetch user attributes from separate collection
                try:
                    attrs_result = super_admin.get_user_attributes(doc.id)
                    if attrs_result.get('success'):
                        user_data['attributes'] = attrs_result.get('attributes', {})
                    else:
                        user_data['attributes'] = {}
                except Exception as attr_error:
                    logger.warning(f"Failed to fetch attributes for user {doc.id}: {attr_error}")
                    user_data['attributes'] = {}
                
                users_list.append(user_data)
            
            return jsonify({
                'success': True,
                'users': users_list,
                'total_count': len(users_list),
                'service_name': service_name,
                'message': f'Users retrieved for {service_name}'
            }), 200
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Database error: {str(e)}'
            }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'System service error: {str(e)}'
        }), 500

@super_admin_api.route('/users', methods=['GET'])
@super_admin_required
def list_users():
    """List all users in the system with JWT authentication"""
    try:
        # Get admin info from JWT token
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401
            
        admin_id = current_user.get('admin_id') or current_user.get('user_id')
        if not admin_id:
            return jsonify({
                'success': False,
                'error': 'Admin ID not found in token'
            }), 401
        
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        
        result = super_admin.list_all_users(
            admin_id=admin_id,
            page=page,
            limit=limit
        )
        
        status_code = 200 if result['success'] else 403
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to list users: {str(e)}'
        }), 500

@super_admin_api.route('/users/<string:user_id>', methods=['GET'])
@super_admin_required
def get_user_details(user_id: str):
    """Get detailed user information with JWT authentication"""
    try:
        # Get admin info from JWT token
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401
            
        admin_id = current_user.get('admin_id') or current_user.get('user_id')
        if not admin_id:
            return jsonify({
                'success': False,
                'error': 'Admin ID not found in token'
            }), 401
        
        # Verify admin permissions
        if not super_admin._verify_super_admin(admin_id):
            return jsonify({
                'success': False,
                'error': 'Unauthorized: Super admin access required'
            }), 403
        
        # Get user data
        user_doc = super_admin.users_collection.document(user_id).get()
        if not user_doc.exists:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        user_data = user_doc.to_dict()
        if 'password' in user_data:
            del user_data['password']
        
        # Get user attributes
        attrs_result = super_admin.get_user_attributes(user_id)
        if attrs_result['success']:
            user_data['attributes'] = attrs_result['attributes']
        else:
            user_data['attributes'] = {}
        
        # Get ABE key status
        abe_key_status = central_authority.check_user_has_private_key(user_id)
        user_data['abe_key_status'] = abe_key_status
        
        return jsonify({
            'success': True,
            'user': user_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get user details: {str(e)}'
        }), 500

@super_admin_api.route('/users/<string:user_id>/attributes', methods=['PUT'])
@super_admin_required
def update_user_attributes(user_id: str):
    """Update user attributes with JWT authentication"""
    try:
        # Get admin info from JWT token
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401
            
        admin_id = current_user.get('admin_id') or current_user.get('user_id')
        if not admin_id:
            return jsonify({
                'success': False,
                'error': 'Admin ID not found in token'
            }), 401
        
        data = request.get_json()
        
        if 'attributes' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing attributes field'
            }), 400
        
        result = super_admin.update_user_attributes(
            admin_id=admin_id,
            user_id=user_id,
            new_attributes=data['attributes']
        )
        
        # If attributes updated successfully, regenerate ABE private key
        if result['success'] and data.get('regenerate_abe_key', True):
            # Get user's current password (would need to be provided or use a temporary one)
            if 'password' in data:
                # Convert attributes to ABE format
                abe_attributes = []
                for key, value in data['attributes'].items():
                    if isinstance(value, list):
                        for val in value:
                            abe_attributes.append(f"{key}:{val}")
                    else:
                        abe_attributes.append(f"{key}:{value}")
                
                # Regenerate ABE key
                abe_result = central_authority.generate_encrypted_user_private_key(
                    user_id=user_id,
                    password=data['password'],
                    attributes=abe_attributes
                )
                
                if not abe_result['success']:
                    result['warning'] = f'Attributes updated but ABE key regeneration failed: {abe_result["error"]}'
        
        status_code = 200 if result['success'] else 400
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to update user attributes: {str(e)}'
        }), 500

@super_admin_api.route('/users/<string:user_id>/deactivate', methods=['POST'])
@super_admin_required
def deactivate_user(user_id: str):
    """Deactivate user account with JWT authentication"""
    try:
        # Get admin info from JWT token
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401
            
        admin_id = current_user.get('admin_id') or current_user.get('user_id')
        if not admin_id:
            return jsonify({
                'success': False,
                'error': 'Admin ID not found in token'
            }), 401
        
        result = super_admin.deactivate_user(
            admin_id=admin_id,
            user_id=user_id
        )
        
        status_code = 200 if result['success'] else 400
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to deactivate user: {str(e)}'
        }), 500

@super_admin_api.route('/users/<string:user_id>/activate', methods=['POST'])
@super_admin_required
def activate_user(user_id: str):
    """Activate user account with JWT authentication"""
    try:
        # Get admin info from JWT token
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401
            
        admin_id = current_user.get('admin_id') or current_user.get('user_id')
        if not admin_id:
            return jsonify({
                'success': False,
                'error': 'Admin ID not found in token'
            }), 401
        
        # Verify admin permissions
        if not super_admin._verify_super_admin(admin_id):
            return jsonify({
                'success': False,
                'error': 'Unauthorized: Super admin access required'
            }), 403
        
        # Update user status
        super_admin.users_collection.document(user_id).update({
            'is_active': True,
            'activated_by': admin_id,
            'activated_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })
        
        return jsonify({
            'success': True,
            'message': 'User account activated successfully'
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to activate user: {str(e)}'
        }), 500

@super_admin_api.route('/schema/attributes', methods=['GET'])
def get_attribute_schema():
    """Get the current attribute schema"""
    try:
        result = super_admin.get_attribute_schema()
        
        status_code = 200 if result['success'] else 404
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get attribute schema: {str(e)}'
        }), 500

@super_admin_api.route('/users/<string:user_id>/abe-key/regenerate', methods=['POST'])
@super_admin_required
def regenerate_abe_key(user_id: str):
    """Regenerate ABE private key for user with JWT authentication"""
    try:
        # Get admin info from JWT token
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401
            
        admin_id = current_user.get('admin_id') or current_user.get('user_id')
        if not admin_id:
            return jsonify({
                'success': False,
                'error': 'Admin ID not found in token'
            }), 401
        
        data = request.get_json()
        
        if 'password' not in data:
            return jsonify({
                'success': False,
                'error': 'User password required for ABE key generation'
            }), 400
        
        # Get user attributes
        attrs_result = super_admin.get_user_attributes(user_id)
        if not attrs_result['success']:
            return jsonify({
                'success': False,
                'error': 'Could not get user attributes'
            }), 400
        
        # Convert attributes to ABE format
        abe_attributes = []
        for key, value in attrs_result['attributes'].items():
            if isinstance(value, list):
                for val in value:
                    abe_attributes.append(f"{key}:{val}")
            else:
                abe_attributes.append(f"{key}:{value}")
        
        # Generate ABE key
        result = central_authority.generate_encrypted_user_private_key(
            user_id=user_id,
            password=data['password'],
            attributes=abe_attributes
        )
        
        status_code = 200 if result['success'] else 400
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to regenerate ABE key: {str(e)}'
        }), 500

@super_admin_api.route('/stats', methods=['GET'])
@super_admin_required
def get_system_stats():
    """Get system statistics with JWT authentication"""
    try:
        # Get admin info from JWT token
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401
        
        # Get user statistics
        total_users = len(list(super_admin.users_collection.where('user_type', '==', 'regular').get()))
        active_users = len(list(super_admin.users_collection.where('user_type', '==', 'regular').where('is_active', '==', True).get()))
        inactive_users = total_users - active_users
        
        # Get attribute statistics
        all_attrs = list(super_admin.attributes_collection.get())
        role_stats = {}
        dept_stats = {}
        
        for attr_doc in all_attrs:
            attrs = attr_doc.to_dict().get('attributes', {})
            
            role = attrs.get('role')
            if role:
                role_stats[role] = role_stats.get(role, 0) + 1
            
            dept = attrs.get('department')
            if dept:
                dept_stats[dept] = dept_stats.get(dept, 0) + 1
        
        return jsonify({
            'success': True,
            'stats': {
                'users': {
                    'total': total_users,
                    'active': active_users,
                    'inactive': inactive_users
                },
                'attributes': {
                    'by_role': role_stats,
                    'by_department': dept_stats
                }
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get system stats: {str(e)}'
        }), 500
