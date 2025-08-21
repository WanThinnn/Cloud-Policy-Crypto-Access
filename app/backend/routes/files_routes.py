"""
File management API routes with CP-ABE encryption
"""
from flask import Blueprint, request, jsonify, send_file
import logging
import io
import sys
import os

# Add parent directory to path to import module
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from module.file_manager import file_manager

logger = logging.getLogger(__name__)

# Create files Blueprint
files_api = Blueprint('files', __name__, url_prefix='/files')

@files_api.route('/', methods=['GET'])
def list_files():
    """
    Liệt kê files của user
    
    Query parameters:
    - user_id: User ID (required)
    - include_shared: Include shared files (default: true)
    """
    try:
        user_id = request.args.get('user_id')
        include_shared = request.args.get('include_shared', 'true').lower() == 'true'
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id parameter is required'
            }), 400
        
        result = file_manager.list_user_files(user_id, include_shared)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"List files error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@files_api.route('/upload', methods=['POST'])
def upload_file():
    """
    Upload và mã hóa file
    
    Form data:
    - file: File to upload (required)
    - owner_id: Owner user ID (required)
    - access_policy: Custom access policy (optional)
    - metadata: JSON metadata (optional)
    """
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        owner_id = request.form.get('owner_id')
        access_policy = request.form.get('access_policy')
        
        if not owner_id:
            return jsonify({
                'success': False,
                'error': 'owner_id is required'
            }), 400
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        # Read file data
        file_data = file.read()
        
        # Parse metadata if provided
        metadata = None
        metadata_str = request.form.get('metadata')
        if metadata_str:
            try:
                import json
                metadata = json.loads(metadata_str)
            except json.JSONDecodeError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid metadata JSON format'
                }), 400
        
        # Upload file
        result = file_manager.upload_file(
            file_data=file_data,
            filename=file.filename,
            owner_id=owner_id,
            access_policy=access_policy,
            metadata=metadata
        )
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Upload file error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@files_api.route('/<file_id>', methods=['GET'])
def get_file_info(file_id):
    """
    Lấy thông tin file
    
    Query parameters:
    - user_id: User ID (required)
    """
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id parameter is required'
            }), 400
        
        result = file_manager.get_file_info(file_id, user_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 404 if 'not found' in result.get('error', '').lower() else 403
            
    except Exception as e:
        logger.error(f"Get file info error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@files_api.route('/<file_id>/download', methods=['GET'])
def download_file(file_id):
    """
    Download và giải mã file
    
    Query parameters:
    - user_id: User ID (required)
    """
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id parameter is required'
            }), 400
        
        result = file_manager.download_file(file_id, user_id)
        
        if result['success']:
            # Return file as download
            file_data = result['file_data']
            filename = result['filename']
            file_type = result['file_type']
            
            return send_file(
                io.BytesIO(file_data),
                as_attachment=True,
                download_name=filename,
                mimetype=file_type
            )
        else:
            return jsonify(result), 403 if 'denied' in result.get('error', '').lower() else 404
            
    except Exception as e:
        logger.error(f"Download file error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@files_api.route('/<file_id>', methods=['DELETE'])
def delete_file(file_id):
    """
    Xóa file
    
    Query parameters:
    - user_id: User ID (required)
    """
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id parameter is required'
            }), 400
        
        result = file_manager.delete_file(file_id, user_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 403 if 'owner' in result.get('error', '').lower() else 404
            
    except Exception as e:
        logger.error(f"Delete file error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@files_api.route('/<file_id>/policy', methods=['PUT'])
def update_file_policy(file_id):
    """
    Cập nhật access policy của file
    
    Expected JSON:
    {
        "user_id": "user_123",
        "new_policy": "(DOCTOR AND CARDIOLOGY)"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        user_id = data.get('user_id')
        new_policy = data.get('new_policy')
        
        if not user_id or not new_policy:
            return jsonify({
                'success': False,
                'error': 'user_id and new_policy are required'
            }), 400
        
        result = file_manager.update_file_policy(file_id, user_id, new_policy)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 403 if 'owner' in result.get('error', '').lower() else 404
            
    except Exception as e:
        logger.error(f"Update file policy error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@files_api.route('/<file_id>/access-logs', methods=['GET'])
def get_file_access_logs(file_id):
    """
    Lấy access logs của file
    
    Query parameters:
    - user_id: User ID (required)
    """
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id parameter is required'
            }), 400
        
        result = file_manager.get_access_logs(file_id, user_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 403 if 'owner' in result.get('error', '').lower() else 404
            
    except Exception as e:
        logger.error(f"Get file access logs error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@files_api.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Files API',
        'message': 'Files service is running'
    })
