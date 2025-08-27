"""
Authentication API routes - JWT Bearer Token based authentication
Admin-controlled user system with JWT tokens
"""
from flask import Blueprint, request, jsonify
import asyncio
import logging
import uuid
from datetime import datetime, timedelta

# Import modules
try:
    from ..module.user_management import user_manager, UserManager
    from ..module.super_admin import super_admin
    from ..module.jwt_auth import jwt_manager
    from ..module.auth_decorators import jwt_required, get_current_user
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from module.user_management import user_manager, UserManager
    from module.super_admin import super_admin
    from module.jwt_auth import jwt_manager
    from module.auth_decorators import jwt_required, get_current_user

logger = logging.getLogger(__name__)

# Create auth Blueprint
auth_api = Blueprint('auth', __name__, url_prefix='/auth')

def run_async(async_func):
    """Helper to run async functions in sync context"""
    def wrapper(*args, **kwargs):
        return asyncio.run(async_func(*args, **kwargs))
    return wrapper

@auth_api.route('/register', methods=['POST'])
def register_disabled():
    """Public registration is disabled - Admin only user creation"""
    return jsonify({
        'success': False,
        'error': 'Public registration is disabled. Please contact administrator for account creation.',
        'admin_only': True,
        'contact_info': {
            'message': 'Contact your system administrator to create an account',
            'admin_endpoints': [
                'POST /super-admin/setup - Create first super admin',
                'POST /super-admin/users - Create user account (admin only)'
            ]
        }
    }), 403

@auth_api.route('/login', methods=['POST'])
def login():
    """User login - returns JWT Bearer token for authentication"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        if not data.get('username') or not data.get('password'):
            return jsonify({
                'success': False,
                'error': 'Username and password are required'
            }), 400
        
        # Check if it's a super admin login attempt first
        try:
            super_admin_result = super_admin.authenticate_super_admin(
                username=data['username'],
                password=data['password']
            )
            
            if super_admin_result['success']:
                # Super admin login successful - generate JWT token
                admin_data = super_admin_result['admin']
                admin_data['user_type'] = 'super_admin'
                
                token = jwt_manager.generate_token(admin_data)
                
                logger.info(f"Super admin logged in: {data['username']}")
                
                return jsonify({
                    'success': True,
                    'user_type': 'super_admin',
                    'user': admin_data,
                    'access_token': token,
                    'token_type': 'Bearer',
                    'expires_in': jwt_manager.token_expiry_hours * 3600,  # seconds
                    'message': 'Super admin login successful'
                }), 200
        except Exception as e:
            logger.warning(f"Super admin login attempt failed: {e}")
        
        # Try regular user login
        try:
            result = run_async(user_manager.authenticate_user)(
                username=data['username'],
                password=data['password']
            )
            
            if result['success']:
                # Regular user login successful - get user attributes and generate JWT
                user_id = result.get('user_id', data['username'])
                must_change_password = result.get('must_change_password', False)
                
                # If user must change password, return special response
                if must_change_password:
                    return jsonify({
                        'success': True,
                        'must_change_password': True,
                        'user_id': user_id,
                        'message': 'Password must be changed before accessing the system',
                        'action_required': 'change_password'
                    }), 200
                
                # Get user attributes
                try:
                    attrs_result = super_admin.get_user_attributes(user_id)
                    user_attributes = attrs_result['attributes'] if attrs_result['success'] else {}
                except Exception as e:
                    logger.warning(f"Could not get user attributes: {e}")
                    user_attributes = {}
                
                # Prepare user data for JWT token
                user_data = {
                    'id': user_id,
                    'user_id': user_id,
                    'username': data['username'],
                    'user_type': 'regular',
                    'attributes': user_attributes
                }
                
                token = jwt_manager.generate_token(user_data)
                
                logger.info(f"User logged in: {data['username']}")
                
                return jsonify({
                    'success': True,
                    'user_type': 'regular',
                    'user_id': user_id,
                    'username': data['username'],
                    'attributes': user_attributes,
                    'access_token': token,
                    'token_type': 'Bearer',
                    'expires_in': jwt_manager.token_expiry_hours * 3600,  # seconds
                    'message': 'Login successful'
                }), 200
        except Exception as e:
            logger.warning(f"Regular user login attempt failed: {e}")
        
        # Both login attempts failed
        return jsonify({
            'success': False,
            'error': 'Invalid credentials'
        }), 401
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({
            'success': False,
            'error': 'Login failed due to server error'
        }), 500

@auth_api.route('/logout', methods=['POST'])
@jwt_required
def logout():
    """Logout user - with JWT tokens, logout is handled client-side by discarding token"""
    try:
        current_user = get_current_user()
        username = current_user.get('username', 'unknown') if current_user else 'unknown'
        user_type = current_user.get('user_type', 'unknown') if current_user else 'unknown'
        
        logger.info(f"User logged out: {username} (type: {user_type})")
        
        return jsonify({
            'success': True,
            'message': 'Logged out successfully',
            'note': 'Please discard your JWT token on the client side'
        }), 200
            
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({
            'success': False,
            'error': 'Logout failed due to server error'
        }), 500

@auth_api.route('/session', methods=['GET'])
@jwt_required
def check_session():
    """Check authentication status using JWT token"""
    try:
        current_user = get_current_user()
        
        if current_user:
            return jsonify({
                'success': True,
                'authenticated': True,
                'user_id': current_user.get('user_id'),
                'username': current_user.get('username'),
                'user_type': current_user.get('user_type', 'regular'),
                'attributes': current_user.get('attributes', {}),
                'token_exp': current_user.get('exp')
            }), 200
        else:
            return jsonify({
                'success': False,
                'authenticated': False,
                'message': 'No user data found'
            }), 401
            
    except Exception as e:
        logger.error(f"Session check error: {e}")
        return jsonify({
            'success': False,
            'error': 'Session check failed'
        }), 500

@auth_api.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Request password reset"""
    try:
        data = request.get_json()
        
        if not data or not data.get('username'):
            return jsonify({
                'success': False,
                'error': 'Username or email is required'
            }), 400
        
        username = data['username']
        
        # Find user by username or email
        users_collection = super_admin.users_collection
        
        # Try username first
        users_query = users_collection.where('username', '==', username).limit(1).get()
        if not users_query:
            # Try email
            users_query = users_collection.where('email', '==', username).limit(1).get()
        
        if users_query:
            user_doc = users_query[0]
            user_data = user_doc.to_dict()
            
            # Generate password reset token
            reset_token = str(uuid.uuid4())
            reset_expires = datetime.utcnow() + timedelta(hours=1)
            
            # Store reset token in database
            super_admin.users_collection.document(user_data['id']).update({
                'reset_token': reset_token,
                'reset_token_expires': reset_expires,
                'reset_requested_at': datetime.utcnow()
            })
            
            logger.info(f"Password reset requested for user: {username}")
            
            return jsonify({
                'success': True,
                'message': 'Password reset instructions have been sent to your email',
                'reset_token': reset_token,  # Remove this in production
                'expires_in': '1 hour',
                'note': 'In production, this would be sent via email'
            }), 200
        else:
            # For security, don't reveal if user exists or not
            return jsonify({
                'success': True,
                'message': 'If the username/email exists, password reset instructions have been sent'
            }), 200
            
    except Exception as e:
        logger.error(f"Forgot password error: {e}")
        return jsonify({
            'success': False,
            'error': 'Password reset request failed'
        }), 500

@auth_api.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset password using reset token"""
    try:
        data = request.get_json()
        
        if not data or not data.get('reset_token') or not data.get('new_password'):
            return jsonify({
                'success': False,
                'error': 'Reset token and new password are required'
            }), 400
        
        reset_token = data['reset_token']
        new_password = data['new_password']
        
        # Validate new password
        password_validation = user_manager.validate_password(new_password)
        if not password_validation['valid']:
            return jsonify({
                'success': False,
                'error': 'Password requirements not met',
                'details': password_validation['errors']
            }), 400
        
        # Find user with this reset token
        users_collection = super_admin.users_collection
        users_query = users_collection.where('reset_token', '==', reset_token).limit(1).get()
        
        if not users_query:
            return jsonify({
                'success': False,
                'error': 'Invalid or expired reset token'
            }), 400
        
        user_doc = users_query[0]
        user_data = user_doc.to_dict()
        
        # Check if token is expired
        if datetime.utcnow() > user_data.get('reset_token_expires', datetime.utcnow()):
            return jsonify({
                'success': False,
                'error': 'Reset token has expired'
            }), 400
        
        # Hash new password
        hashed_password = user_manager.hash_password(new_password)
        
        # Update user password and clear reset token
        super_admin.users_collection.document(user_data['id']).update({
            'password': hashed_password,
            'reset_token': None,
            'reset_token_expires': None,
            'password_changed_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })
        
        logger.info(f"Password reset successful for user: {user_data['username']}")
        
        return jsonify({
            'success': True,
            'message': 'Password has been reset successfully. You can now login with your new password.'
        }), 200
        
    except Exception as e:
        logger.error(f"Reset password error: {e}")
        return jsonify({
            'success': False,
            'error': 'Password reset failed'
        }), 500

@auth_api.route('/profile', methods=['GET'])
@jwt_required
def get_profile():
    """Get current user profile"""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401
        
        user_id = current_user.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'User ID not found in token'
            }), 401
        
        # Get user details from database
        user_doc = super_admin.users_collection.document(user_id).get()
        if not user_doc.exists:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        user_data = user_doc.to_dict()
        
        # Return safe user profile (without sensitive data)
        profile = {
            'id': user_data['id'],
            'username': user_data['username'],
            'email': user_data.get('email', ''),
            'full_name': user_data.get('full_name', ''),
            'role': user_data.get('role', 'user'),
            'department': user_data.get('department', ''),
            'attributes': user_data.get('attributes', {}),
            'is_active': user_data.get('is_active', True),
            'created_at': user_data.get('created_at'),
            'last_login': user_data.get('last_login')
        }
        
        return jsonify({
            'success': True,
            'profile': profile
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get user profile'
        }), 500

@auth_api.route('/change-password', methods=['POST'])
def change_password():
    """Change user password - handles both forced and voluntary password changes"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validate required fields
        required_fields = ['username', 'old_password', 'new_password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        username = data['username']
        old_password = data['old_password']
        new_password = data['new_password']
        
        # Authenticate user with old password first
        auth_result = run_async(user_manager.authenticate_user)(username, old_password)
        if not auth_result['success']:
            return jsonify({
                'success': False,
                'error': 'Invalid current password'
            }), 401
        
        user_id = auth_result['user_id']
        
        # Validate new password
        password_validation = UserManager.validate_password(new_password)
        if not password_validation['valid']:
            return jsonify({
                'success': False,
                'error': 'New password does not meet requirements',
                'details': password_validation['errors']
            }), 400
        
        # Update password in database
        hashed_new_password = UserManager.hash_password(new_password)
        
        # Get user document
        from module.super_admin import super_admin
        users_collection = super_admin.users_collection
        
        users_collection.document(user_id).update({
            'password': hashed_new_password,
            'must_change_password': False,  # Clear the flag
            'password_changed_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })
        
        # Re-encrypt private key with new password if user has one
        from module.central_authority import central_authority
        
        # Check if user has private key
        key_status = central_authority.check_user_has_private_key(user_id)
        if key_status['has_key']:
            logger.info(f"Regenerating private key for user {user_id} with new password")
            
            # Regenerate key with new password
            rekey_result = central_authority.regenerate_key_for_password_change(
                user_id=user_id,
                new_password=new_password
            )
            
            if not rekey_result['success']:
                logger.error(f"Failed to regenerate private key for user {user_id}: {rekey_result.get('error')}")
                # Don't fail the password change, but log the error
            else:
                logger.info(f"Successfully regenerated private key for user {user_id}")
        
        logger.info(f"Password changed successfully for user: {username}")
        
        return jsonify({
            'success': True,
            'message': 'Password changed successfully',
            'private_key_updated': key_status['has_key']
        }), 200
        
    except Exception as e:
        logger.error(f"Change password error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to change password due to server error'
        }), 500
