"""
Central Authority API routes for CP-ABE key management with JWT authentication
"""
from flask import Blueprint, request, jsonify
import logging
import sys
import os
import time
from datetime import datetime
import requests
from config import Config

# Add parent directory to path to import module
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from module.central_authority import central_authority
from module.auth_decorators import jwt_required, get_current_user

logger = logging.getLogger(__name__)

# Create CA Blueprint
ca_api = Blueprint('ca', __name__, url_prefix='/ca')

@ca_api.route('/setup', methods=['POST'])
def setup_abe_system():
    """
    Setup ABE system - tạo master key và public key
    """
    try:
        result = central_authority.setup_abe_system()
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Setup ABE system error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@ca_api.route('/keys/active', methods=['GET'])
def get_active_keys():
    """Lấy thông tin active keys (chỉ trả về metadata, không trả về key data)"""
    try:
        result = central_authority.get_active_keys()
        
        if result['success']:
            # Chỉ trả về metadata, không trả về key data thực tế
            response = {
                'success': True,
                'setup_id': result['setup_id'],
                'has_public_key': bool(result.get('public_key')),
                'has_master_key': bool(result.get('master_key')),
                'message': 'Active keys found'
            }
            return jsonify(response)
        else:
            return jsonify(result), 404
            
    except Exception as e:
        logger.error(f"Get active keys error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@ca_api.route('/users/<user_id>/private-key', methods=['POST'])
def generate_user_private_key_with_id(user_id):
    """
    Tạo private key cho user
    
    Expected JSON:
    {
        "attributes": ["role:doctor", "department:cardiology", "clearance:high"]
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'attributes' not in data:
            return jsonify({
                'success': False,
                'error': 'Attributes list is required'
            }), 400
        
        attributes = data['attributes']
        
        if not isinstance(attributes, list) or not attributes:
            return jsonify({
                'success': False,
                'error': 'Attributes must be a non-empty list'
            }), 400
        
        result = central_authority.generate_user_private_key(user_id, attributes)
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Generate user private key error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@ca_api.route('/users/<user_id>/private-key', methods=['GET'])
def get_user_private_key_info(user_id):
    """Lấy thông tin private key của user (chỉ metadata)"""
    try:
        result = central_authority.get_user_private_key(user_id)
        
        if result['success']:
            # Chỉ trả về metadata, không trả về private key thực tế
            response = {
                'success': True,
                'has_private_key': bool(result.get('private_key')),
                'attributes': result['attributes'],
                'message': 'User private key found'
            }
            return jsonify(response)
        else:
            return jsonify(result), 404
            
    except Exception as e:
        logger.error(f"Get user private key info error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@ca_api.route('/users/<user_id>/policy', methods=['GET'])
def generate_user_policy(user_id):
    """Tạo access policy cho user dựa trên attributes"""
    try:
        policy = central_authority.generate_policy_for_user(user_id)
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'policy': policy,
            'message': 'Policy generated successfully'
        })
        
    except Exception as e:
        logger.error(f"Generate user policy error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@ca_api.route('/encrypt', methods=['POST'])
def encrypt_data():
    """
    Mã hóa dữ liệu với policy
    
    Expected form data:
    - file: File to encrypt
    - policy: Access policy string
    """
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        policy = request.form.get('policy')
        
        if not policy:
            return jsonify({
                'success': False,
                'error': 'Policy is required'
            }), 400
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        # Read file data
        file_data = file.read()
        
        # Save to temp file
        import tempfile
        import os
        
        # Handle filename - use fallback if None
        filename = file.filename or 'uploaded_file'
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, filename)
        
        with open(temp_file_path, 'wb') as f:
            f.write(file_data)
        
        # Encrypt file
        result = central_authority.encrypt_file_for_policy(temp_file_path, policy)
        
        # Cleanup temp file
        import shutil
        shutil.rmtree(temp_dir)
        
        if result['success']:
            # Return encrypted data as base64
            import base64
            
            response = {
                'success': True,
                'policy': result['policy'],
                'encrypted_data_base64': base64.b64encode(result['encrypted_data']).decode('utf-8'),
                'original_filename': file.filename,
                'message': result['message']
            }
            return jsonify(response)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Encrypt data error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@ca_api.route('/decrypt', methods=['POST'])
def decrypt_data():
    """
    Giải mã dữ liệu cho user
    
    Expected JSON:
    {
        "encrypted_data_base64": "base64_encoded_data",
        "user_id": "user_123"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        encrypted_data_base64 = data.get('encrypted_data_base64')
        user_id = data.get('user_id')
        
        if not encrypted_data_base64 or not user_id:
            return jsonify({
                'success': False,
                'error': 'encrypted_data_base64 and user_id are required'
            }), 400
        
        # Decode base64 data
        import base64
        try:
            encrypted_data = base64.b64decode(encrypted_data_base64)
        except Exception:
            return jsonify({
                'success': False,
                'error': 'Invalid base64 encoded data'
            }), 400
        
        # Decrypt data
        result = central_authority.decrypt_file_for_user(encrypted_data, user_id)
        
        if result['success']:
            # Return decrypted data as base64
            response = {
                'success': True,
                'decrypted_data_base64': base64.b64encode(result['decrypted_data']).decode('utf-8'),
                'message': result['message']
            }
            return jsonify(response)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Decrypt data error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@ca_api.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Central Authority API',
        'message': 'CA service is running'
    })

@ca_api.route('/public-key', methods=['GET'])
def get_public_key():
    """
    Lấy public key của hệ thống ABE
    
    Returns:
        JSON response với public key data
    """
    try:
        # Lấy active keys từ CA
        keys_result = central_authority.get_active_keys()
        
        if not keys_result['success']:
            return jsonify({
                'success': False,
                'error': keys_result['error']
            }), 404
        
        # Kiểm tra có public key không
        if not keys_result.get('has_public_key') or not keys_result.get('public_key'):
            return jsonify({
                'success': False,
                'error': 'Public key not found. Please setup ABE system first.'
            }), 404
        
        # Encode public key as base64 để return qua JSON
        import base64
        public_key_b64 = base64.b64encode(keys_result['public_key']).decode('utf-8')
        
        return jsonify({
            'success': True,
            'setup_id': keys_result['setup_id'],
            'public_key': public_key_b64,
            'storage_type': keys_result.get('storage_type', 'local'),
            'message': 'Public key retrieved successfully'
        })
        
    except Exception as e:
        logger.error(f"Failed to get public key: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get public key: {str(e)}'
        }), 500

@ca_api.route('/status', methods=['GET'])
def get_ca_status():
    """
    Lấy status của CA system
    """
    try:
        keys_result = central_authority.get_active_keys()
        
        return jsonify({
            'success': True,
            'abe_system_setup': keys_result['success'],
            'has_public_key': keys_result.get('has_public_key', False),
            'has_master_key': keys_result.get('has_master_key', False),
            'storage_type': keys_result.get('storage_type', 'unknown'),
            'setup_id': keys_result.get('setup_id', None),
            'message': 'CA status retrieved successfully'
        })
        
    except Exception as e:
        logger.error(f"Failed to get CA status: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get CA status: {str(e)}'
        }), 500

@ca_api.route('/user/private-key/generate', methods=['POST'])
def generate_encrypted_user_private_key():
    """
    Tạo và mã hóa private key cho user bằng password
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400
        
        # Validate required fields
        required_fields = ['user_id', 'password', 'attributes']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        user_id = data['user_id']
        password = data['password']
        attributes = data['attributes']
        
        if not isinstance(attributes, list):
            return jsonify({
                'success': False,
                'error': 'Attributes must be a list'
            }), 400
        
        result = central_authority.generate_encrypted_user_private_key(
            user_id, password, attributes
        )
        
        if result['success']:
            return jsonify(result), 201
        else:
            if result.get('has_existing_key'):
                return jsonify(result), 409  # Conflict
            else:
                return jsonify(result), 400
                
    except Exception as e:
        logger.error(f"Generate encrypted private key error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@ca_api.route('/user/private-key/authenticate', methods=['POST'])
def authenticate_user_private_key():
    """
    Xác thực và lấy private key của user bằng password
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400
        
        # Validate required fields
        required_fields = ['user_id', 'password']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        user_id = data['user_id']
        password = data['password']
        
        result = central_authority.get_user_private_key_with_password(user_id, password)
        
        if result['success']:
            # Don't return the actual private key, just success status and metadata
            response = {
                'success': True,
                'attributes': result['attributes'],
                'message': 'Authentication successful. Private key retrieved.'
            }
            return jsonify(response)
        else:
            if result.get('is_auth_error'):
                return jsonify(result), 401  # Unauthorized
            else:
                return jsonify(result), 400
                
    except Exception as e:
        logger.error(f"Authenticate private key error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@ca_api.route('/user/private-key/check', methods=['GET'])
def check_user_private_key():
    """
    Kiểm tra user đã có private key chưa
    """
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id parameter is required'
            }), 400
        
        result = central_authority.check_user_has_private_key(user_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
                
    except Exception as e:
        logger.error(f"Check user private key error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@ca_api.route('/user/decrypt-file', methods=['POST'])
def decrypt_file_with_password():
    """
    Giải mã file cho user bằng password
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400
        
        # Validate required fields
        required_fields = ['user_id', 'password', 'encrypted_data_base64']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        user_id = data['user_id']
        password = data['password']
        encrypted_data_base64 = data['encrypted_data_base64']
        
        # Decode base64 data
        import base64
        try:
            encrypted_data = base64.b64decode(encrypted_data_base64)
        except Exception:
            return jsonify({
                'success': False,
                'error': 'Invalid base64 encoded data'
            }), 400
        
        # First authenticate user and get private key
        auth_result = central_authority.get_user_private_key_with_password(user_id, password)
        if not auth_result['success']:
            if auth_result.get('is_auth_error'):
                return jsonify(auth_result), 401
            else:
                return jsonify(auth_result), 400
        
        # Then decrypt file using the private key
        # This is a placeholder - you would use the decrypted private key here
        # For now, we'll use the existing decrypt method
        result = central_authority.decrypt_file_for_user(encrypted_data, user_id)
        
        if result['success']:
            # Return decrypted data as base64
            response = {
                'success': True,
                'decrypted_data_base64': base64.b64encode(result['decrypted_data']).decode('utf-8'),
                'message': 'File decrypted successfully'
            }
            return jsonify(response)
        else:
            return jsonify(result), 400
                
    except Exception as e:
        logger.error(f"Decrypt file with password error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@ca_api.route('/user/generate-private-key', methods=['POST'])
@jwt_required
def generate_user_private_key():
    """
    Generate private key for authenticated user với JWT authentication
    User ID và attributes được lấy từ JWT token
    """
    try:
        # Get authenticated user from JWT token
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

        logger.info(f"Generating private key for authenticated user: {user_id}")

        # TỰ ĐỘNG LẤY USER ATTRIBUTES TỪ JWT TOKEN
        user_attributes = current_user.get('attributes', {})
        
        if not user_attributes:
            return jsonify({
                'success': False,
                'error': 'No user attributes found in token'
            }), 400
        
        # Convert JWT attributes to CP-ABE format
        cpabe_attributes = []
        for key, value in user_attributes.items():
            if value:  # Only add non-empty values
                cpabe_attributes.append(f"{key}:{value}")
                logger.info(f"DEBUG: Added attribute {key}:{value}")

        if not cpabe_attributes:
            return jsonify({
                'success': False,
                'error': 'No valid attributes found for private key generation'
            }), 400

        logger.info(f"Generating private key for user {user_id} with attributes: {cpabe_attributes}")

        # GENERATE PRIVATE KEY - SIMPLE & DIRECT
        try:
            if not cpabe_attributes:
                return jsonify({
                    'success': False,
                    'error': 'No valid attributes found for user. Cannot generate private key.'
                }), 400

            # TRỰC TIẾP GỌI CA METHOD
            result = central_authority.generate_user_private_key(
                user_id, 
                cpabe_attributes
            )

            if result.get('success'):
                return jsonify({
                    'success': True,
                    'message': 'Private key generated successfully from JWT token attributes',
                    'user_id': user_id,
                    'attributes_used': cpabe_attributes,
                    'private_key_info': {
                        'has_private_key': True,
                        'attributes': cpabe_attributes,
                        'user_id': user_id
                    },
                    'generated_at': datetime.utcnow().isoformat()
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f'Failed to generate private key: {result.get("error", "Unknown error")}'
                }), 500

        except Exception as e:
            logger.error(f"Private key generation error: {e}")
            return jsonify({
                'success': False,
                'error': f'Private key generation failed: {str(e)}'
            }), 500

    except Exception as e:
        logger.error(f"Generate user private key error: {e}")
        return jsonify({
            'success': False,
            'error': f'Request processing failed: {str(e)}'
        }), 500


def generate_cpabe_private_key(user_id, attributes, public_key_path, master_key_path):
    """Generate CP-ABE private key with user attributes"""
    try:
        # Use existing CA method instead of calling external CP-ABE
        result = central_authority.generate_user_private_key(user_id, attributes)
        
        if result.get('success'):
            return {
                'success': True,
                'private_key_path': f"/tmp/cpabe_keys/{user_id}_private.key",
                'key_id': f"cpabe_key_{user_id}_{int(time.time())}"
            }
        else:
            return {'success': False, 'error': result.get('error')}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

def generate_policy_examples(user_attributes):
    """Generate example policies that user can access"""
    examples = []
    
    role = user_attributes.get('role')
    department = user_attributes.get('department')
    clearance = user_attributes.get('clearance_level')
    
    # Basic department policy
    if department:
        examples.append(f"department:{department}")
    
    # Role-based policy
    if role:
        examples.append(f"role:{role}")
        
    # Department + Role combination
    if department and role:
        examples.append(f"(department:{department} AND role:{role})")
    
    # Clearance-based policies
    if clearance:
        examples.append(f"clearance_level:{clearance}")
        if clearance in ['high', 'top_secret']:
            examples.append(f"(clearance_level:{clearance} OR role:manager)")
    
    return examples
