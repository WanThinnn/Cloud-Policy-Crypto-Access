"""
Authentication decorators for JWT Bearer Token authentication
"""
from functools import wraps
from flask import request, jsonify, g
from .jwt_auth import jwt_manager
import logging

logger = logging.getLogger(__name__)

def jwt_required(f):
    """
    Decorator to require JWT authentication for any user type
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({
                'success': False,
                'error': 'Authorization header required',
                'message': 'Please provide Authorization: Bearer <token>'
            }), 401
        
        token = jwt_manager.extract_token_from_header(auth_header)
        if not token:
            return jsonify({
                'success': False,
                'error': 'Invalid authorization header format',
                'message': 'Use format: Authorization: Bearer <token>'
            }), 401
        
        user_data = jwt_manager.get_user_from_token(token)
        if not user_data:
            return jsonify({
                'success': False,
                'error': 'Invalid or expired token',
                'message': 'Please login again to get a valid token'
            }), 401
        
        # Add user data to Flask g object
        g.current_user = user_data
        
        return f(*args, **kwargs)
    return decorated_function

def super_admin_required(f):
    """
    Decorator to require Super Admin JWT authentication
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({
                'success': False,
                'error': 'Authorization header required',
                'message': 'Please provide Authorization: Bearer <super_admin_token>'
            }), 401
        
        token = jwt_manager.extract_token_from_header(auth_header)
        if not token:
            return jsonify({
                'success': False,
                'error': 'Invalid authorization header format',
                'message': 'Use format: Authorization: Bearer <token>'
            }), 401
        
        user_data = jwt_manager.get_user_from_token(token)
        if not user_data:
            return jsonify({
                'success': False,
                'error': 'Invalid or expired token',
                'message': 'Please login again to get a valid token'
            }), 401
        
        # Check if user is super admin
        if user_data.get('user_type') != 'super_admin':
            return jsonify({
                'success': False,
                'error': 'SuperAdmin access required',
                'message': 'Insufficient privileges to access this endpoint'
            }), 403
        
        # Add user data to Flask g object
        g.current_user = user_data
        
        return f(*args, **kwargs)
    return decorated_function

def regular_user_required(f):
    """
    Decorator to require Regular User JWT authentication (exclude super admin)
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({
                'success': False,
                'error': 'Authorization header required',
                'message': 'Please provide Authorization: Bearer <user_token>'
            }), 401
        
        token = jwt_manager.extract_token_from_header(auth_header)
        if not token:
            return jsonify({
                'success': False,
                'error': 'Invalid authorization header format',
                'message': 'Use format: Authorization: Bearer <token>'
            }), 401
        
        user_data = jwt_manager.get_user_from_token(token)
        if not user_data:
            return jsonify({
                'success': False,
                'error': 'Invalid or expired token',
                'message': 'Please login again to get a valid token'
            }), 401
        
        # Check if user is regular user (not super admin)
        if user_data.get('user_type') == 'super_admin':
            return jsonify({
                'success': False,
                'error': 'Regular user access required',
                'message': 'Super admin cannot access regular user endpoints'
            }), 403
        
        # Add user data to Flask g object
        g.current_user = user_data
        
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """
    Get current authenticated user from Flask g object
    
    Returns:
        User data dict if authenticated, None otherwise
    """
    return getattr(g, 'current_user', None)
