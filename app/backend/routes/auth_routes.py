"""
Authentication API routes - Admin-controlled user system
Only login and password reset functionality available
Public registration is disabled
"""
from flask import Blueprint, request, jsonify, session
import asyncio
import logging
import uuid
from datetime import datetime, timedelta

# Import modules
try:
    from ..module.user_management import user_manager
    from ..module.super_admin import super_admin
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from module.user_management import user_manager
    from module.super_admin import super_admin

logger = logging.getLogger(__name__)

# Create auth Blueprint
auth_api = Blueprint('auth', __name__, url_prefix='/auth')

def run_async(async_func):
    """Helper to run async functions in sync context"""
    def wrapper(*args, **kwargs):
        return asyncio.run(async_func(*args, **kwargs))
    return wrapper

@auth_api.route('/test', methods=['GET'])
def test_auth():
    """Test route to check if auth API is working"""
    return jsonify({
        'success': True,
        'message': 'Auth API is working!',
        'timestamp': str(datetime.now()),
        'features': [
            'Login',
            'Password Reset', 
            'Admin-controlled user creation only'
        ]
    })

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
    """User login - supports both super admin and regular users"""
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
                # Super admin login successful
                session['user_id'] = super_admin_result['admin']['id']
                session['username'] = super_admin_result['admin']['username']
                session['user_type'] = 'super_admin'
                session['authenticated'] = True
                
                logger.info(f"Super admin logged in: {data['username']}")
                
                return jsonify({
                    'success': True,
                    'user_type': 'super_admin',
                    'user': super_admin_result['admin'],
                    'message': 'Super admin login successful',
                    'redirect': '/admin-dashboard'
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
                # Regular user login successful
                session['user_id'] = result.get('user_id', data['username'])
                session['username'] = data['username'] 
                session['user_type'] = 'regular'
                session['authenticated'] = True
                
                logger.info(f"User logged in: {data['username']}")
                
                # Get user attributes
                try:
                    attrs_result = super_admin.get_user_attributes(result['user_id'])
                    user_attributes = attrs_result['attributes'] if attrs_result['success'] else {}
                except Exception as e:
                    logger.warning(f"Could not get user attributes: {e}")
                    user_attributes = {}
                
                return jsonify({
                    'success': True,
                    'user_type': 'regular',
                    'user_id': result['user_id'],
                    'username': data['username'],
                    'attributes': user_attributes,
                    'message': 'Login successful',
                    'redirect': '/dashboard'
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
def logout():
    """Logout user - clear session"""
    try:
        username = session.get('username', 'unknown')
        user_type = session.get('user_type', 'unknown')
        
        # Clear session
        session.clear()
        
        logger.info(f"User logged out: {username} (type: {user_type})")
        
        return jsonify({
            'success': True,
            'message': 'Logged out successfully'
        }), 200
            
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({
            'success': False,
            'error': 'Logout failed due to server error'
        }), 500

@auth_api.route('/session', methods=['GET'])
def check_session():
    """Check current session status"""
    try:
        if session.get('authenticated'):
            return jsonify({
                'success': True,
                'authenticated': True,
                'user_id': session.get('user_id'),
                'username': session.get('username'),
                'user_type': session.get('user_type', 'regular')
            }), 200
        else:
            return jsonify({
                'success': False,
                'authenticated': False,
                'message': 'No active session'
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
