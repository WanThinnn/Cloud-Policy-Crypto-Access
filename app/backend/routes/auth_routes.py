"""
Authentication API routes
"""
from flask import Blueprint, request, jsonify
import asyncio
import logging
from module import user_manager

logger = logging.getLogger(__name__)

# Create auth Blueprint
auth_api = Blueprint('auth', __name__, url_prefix='/auth')

def run_async(async_func):
    """Helper to run async functions in sync context"""
    def wrapper(*args, **kwargs):
        return asyncio.run(async_func(*args, **kwargs))
    return wrapper

@auth_api.route('/register', methods=['POST'])
def register():
    """
    Đăng ký tài khoản mới
    
    Expected JSON:
    {
        "username": "string",
        "email": "string",
        "password": "string"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validate required fields
        required_fields = ['username', 'email', 'password']
        missing_fields = [field for field in required_fields if field not in data or not data[field]]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Create user
        result = run_async(user_manager.create_user)(
            username=data['username'],
            email=data['email'],
            password=data['password']
        )
        
        if result['success']:
            logger.info(f"New user registered: {data['username']}")
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({
            'success': False,
            'error': 'Registration failed due to server error'
        }), 500

@auth_api.route('/login', methods=['POST'])
def login():
    """
    Đăng nhập
    
    Expected JSON:
    {
        "username": "string",  # Username hoặc email
        "password": "string"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validate required fields
        if not data.get('username') or not data.get('password'):
            return jsonify({
                'success': False,
                'error': 'Username and password are required'
            }), 400
        
        # Authenticate user
        result = run_async(user_manager.authenticate_user)(
            username=data['username'],
            password=data['password']
        )
        
        if result['success']:
            logger.info(f"User logged in: {data['username']}")
            return jsonify(result), 200
        else:
            return jsonify(result), 401
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({
            'success': False,
            'error': 'Login failed due to server error'
        }), 500

@auth_api.route('/user/<user_id>', methods=['GET'])
def get_user(user_id):
    """
    Lấy thông tin user theo ID
    """
    try:
        result = run_async(user_manager.get_user)(user_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
            
    except Exception as e:
        logger.error(f"Get user error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get user information'
        }), 500

@auth_api.route('/user/<user_id>', methods=['PUT'])
def update_user(user_id):
    """
    Cập nhật thông tin user
    
    Expected JSON:
    {
        "email": "string (optional)",
        "is_active": "boolean (optional)"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        result = run_async(user_manager.update_user)(user_id, data)
        
        if result['success']:
            logger.info(f"User updated: {user_id}")
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Update user error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to update user'
        }), 500

@auth_api.route('/change-password', methods=['POST'])
def change_password():
    """
    Đổi mật khẩu
    
    Expected JSON:
    {
        "user_id": "string",
        "old_password": "string",
        "new_password": "string"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validate required fields
        required_fields = ['user_id', 'old_password', 'new_password']
        missing_fields = [field for field in required_fields if field not in data or not data[field]]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        result = run_async(user_manager.change_password)(
            user_id=data['user_id'],
            old_password=data['old_password'],
            new_password=data['new_password']
        )
        
        if result['success']:
            logger.info(f"Password changed for user: {data['user_id']}")
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Change password error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to change password'
        }), 500

@auth_api.route('/validate-password', methods=['POST'])
def validate_password():
    """
    Kiểm tra độ mạnh của password
    
    Expected JSON:
    {
        "password": "string"
    }
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('password'):
            return jsonify({
                'success': False,
                'error': 'Password is required'
            }), 400
        
        validation_result = user_manager.validate_password(data['password'])
        
        return jsonify({
            'success': True,
            'validation': validation_result
        }), 200
        
    except Exception as e:
        logger.error(f"Password validation error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to validate password'
        }), 500

@auth_api.route('/health', methods=['GET'])
def auth_health():
    """Health check cho auth API"""
    return jsonify({
        'success': True,
        'service': 'Authentication API',
        'status': 'healthy',
        'endpoints': {
            'POST /auth/register': 'User registration',
            'POST /auth/login': 'User login',
            'GET /auth/user/<id>': 'Get user info',
            'PUT /auth/user/<id>': 'Update user info',
            'POST /auth/change-password': 'Change password',
            'POST /auth/validate-password': 'Validate password strength',
            'GET /auth/health': 'Health check'
        }
    }), 200
