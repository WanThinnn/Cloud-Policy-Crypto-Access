"""
Admin management API routes
Admin operations for user and system management
"""
from flask import Blueprint, request, jsonify, session
import logging
import sys
import os
import asyncio
from datetime import datetime

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from module.user_management import user_manager
from module.file_manager import file_manager
from module.database import db

logger = logging.getLogger(__name__)

# Create Admin Blueprint
admin_api = Blueprint('admin', __name__)

def run_async(async_func):
    """Helper to run async functions in sync context"""
    def wrapper(*args, **kwargs):
        return asyncio.run(async_func(*args, **kwargs))
    return wrapper

def is_admin(user_id):
    """Check if user has admin privileges"""
    try:
        user_doc = db.collection('users').document(user_id).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            return user_data.get('role') == 'admin' or user_data.get('is_admin', False)
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
    return False

@admin_api.route('/health', methods=['GET'])
def admin_health():
    """Health check cho admin API"""
    return jsonify({
        'success': True,
        'service': 'Admin API',
        'status': 'healthy',
        'endpoints': {
            'GET /admin/health': 'Admin health check',
            'GET /admin/users': 'List all users',
            'POST /admin/users': 'Create new user',
            'PUT /admin/users/<id>': 'Update user',
            'DELETE /admin/users/<id>': 'Delete user',
            'PUT /admin/users/<id>/attributes': 'Set user attributes',
            'GET /admin/stats': 'System statistics'
        }
    }), 200

@admin_api.route('/users', methods=['GET'])
def list_all_users():
    """Lấy danh sách tất cả users"""
    try:
        # Get all users from users collection
        users_ref = db.collection('users')
        users = users_ref.get()
        
        users_list = []
        for user in users:
            user_data = user.to_dict()
            # Remove sensitive data
            user_data.pop('password', None)
            user_data['id'] = user.id
            users_list.append(user_data)
        
        return jsonify({
            'success': True,
            'users': users_list,
            'total_count': len(users_list)
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch users'
        }), 500

@admin_api.route('/users', methods=['POST'])
def create_user():
    """Create new user (Admin only)"""
    try:
        # Check admin permission
        user_id = session.get('user_id')
        if not user_id or not is_admin(user_id):
            return jsonify({
                'success': False,
                'error': 'Admin privileges required'
            }), 403
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validate required fields
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'Field {field} is required'
                }), 400
        
        # Create user
        result = run_async(user_manager.create_user)(
            username=data['username'],
            email=data['email'],
            password=data['password']
        )
        
        if not result['success']:
            return jsonify(result), 400
        
        # Set attributes if provided
        attributes = data.get('attributes', [])
        if attributes:
            try:
                user_ref = db.collection('user_attributes').document(result['user_id'])
                user_ref.set({
                    'user_id': result['user_id'],
                    'attributes': attributes,
                    'created_at': datetime.utcnow().isoformat(),
                    'created_by': user_id
                })
                result['attributes_set'] = True
                result['attributes'] = attributes
            except Exception as e:
                logger.error(f"Error setting user attributes: {e}")
                result['attributes_set'] = False
        
        return jsonify(result), 201
        
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to create user'
        }), 500

@admin_api.route('/users/<user_id>/attributes', methods=['PUT'])
def set_user_attributes(user_id):
    """Set user attributes (Admin only)"""
    try:
        # Check admin permission
        admin_user_id = session.get('user_id')
        if not admin_user_id or not is_admin(admin_user_id):
            return jsonify({
                'success': False,
                'error': 'Admin privileges required'
            }), 403
        
        data = request.get_json()
        if not data or 'attributes' not in data:
            return jsonify({
                'success': False,
                'error': 'Attributes are required'
            }), 400
        
        attributes = data['attributes']
        if not isinstance(attributes, list):
            return jsonify({
                'success': False,
                'error': 'Attributes must be a list'
            }), 400
        
        # Verify user exists
        user_doc = db.collection('users').document(user_id).get()
        if not user_doc.exists:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Set attributes
        user_attr_ref = db.collection('user_attributes').document(user_id)
        user_attr_ref.set({
            'user_id': user_id,
            'attributes': attributes,
            'updated_at': datetime.utcnow().isoformat(),
            'updated_by': admin_user_id
        })
        
        return jsonify({
            'success': True,
            'message': 'User attributes updated successfully',
            'user_id': user_id,
            'attributes': attributes
        }), 200
        
    except Exception as e:
        logger.error(f"Error setting user attributes: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to set user attributes'
        }), 500

@admin_api.route('/stats', methods=['GET'])
def get_system_stats():
    """Lấy thống kê hệ thống"""
    try:
        # Count documents in each collection
        stats = {}
        
        # Users count
        users_count = len(list(db.collection('users').get()))
        stats['total_users'] = users_count
        
        # Files count
        files_count = len(list(db.collection('shared_files').get()))
        stats['total_files'] = files_count
        
        # Access policies count
        policies_count = len(list(db.collection('access_policies').get()))
        stats['total_policies'] = policies_count
        
        # ABE keys count
        keys_count = len(list(db.collection('abe_keys').get()))
        stats['total_keys'] = keys_count
        
        # User attributes count
        attributes_count = len(list(db.collection('user_attributes').get()))
        stats['total_user_attributes'] = attributes_count
        
        # File access logs count
        logs_count = len(list(db.collection('file_access_logs').get()))
        stats['total_access_logs'] = logs_count
        
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting system stats: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get system statistics'
        }), 500
