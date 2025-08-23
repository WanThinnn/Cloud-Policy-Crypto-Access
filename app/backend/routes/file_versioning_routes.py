"""
File Versioning Routes with JWT authentication
For now, using basic JWT authentication without ABAC until ABAC policies are fully implemented
"""
from flask import Blueprint, request, jsonify
import logging
import base64
from module.auth_decorators import jwt_required, get_current_user
from module.file_versioning import FileVersionManager
from module.file_integrity import FileIntegrityManager

logger = logging.getLogger(__name__)

# Create Blueprint
file_versioning_bp = Blueprint('file_versioning', __name__)

@file_versioning_bp.route('/file/<file_id>/version', methods=['POST'])
@jwt_required
def create_file_version(file_id):
    """
    Create a new version of a file
    
    Expected JSON payload:
    {
        "file_data": "base64_encoded_file_data",
        "version_type": "MAJOR|MINOR|PATCH",
        "change_description": "Description of changes"
    }
    """
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'success': False,
                'error': 'User not authenticated'
            }), 401
            
        current_user_id = current_user.get('user_id')
        
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validate required fields
        if 'file_data' not in data:
            return jsonify({
                'success': False,
                'error': 'file_data is required'
            }), 400
        
        # Decode base64 file data
        try:
            file_data = base64.b64decode(data['file_data'])
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Invalid base64 file data: {str(e)}'
            }), 400
        
        # Get optional parameters
        version_type = data.get('version_type', 'MINOR').upper()
        change_description = data.get('change_description', '')
        
        # Validate version type
        if version_type not in ['MAJOR', 'MINOR', 'PATCH']:
            return jsonify({
                'success': False,
                'error': 'version_type must be MAJOR, MINOR, or PATCH'
            }), 400
        
        # Create version
        result = FileVersionManager.create_version(
            file_id=file_id,
            file_data=file_data,
            uploader_id=current_user_id,
            version_type=version_type,
            change_description=change_description
        )
        
        if result['success']:
            status_code = 201
            logger.info(f"Version {result['version_number']} created for file {file_id} by user {current_user_id}")
        else:
            status_code = 400
            logger.error(f"Version creation failed for file {file_id}: {result.get('error')}")
        
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"Create version error: {e}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@file_versioning_bp.route('/version/<version_id>/approve', methods=['POST'])
@jwt_required
def approve_file_version(version_id):
    """
    Approve a pending file version
    
    Expected JSON payload:
    {
        "approval_notes": "Optional approval notes"
    }
    """
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'success': False,
                'error': 'User not authenticated'
            }), 401
            
        current_user_id = current_user.get('user_id')
        data = request.get_json() or {}
        approval_notes = data.get('approval_notes', '')
        
        # Approve version
        result = FileVersionManager.approve_version(
            version_id=version_id,
            approver_id=current_user_id,
            approval_notes=approval_notes
        )
        
        if result['success']:
            status_code = 200
            logger.info(f"Version {version_id} approved by user {current_user_id}")
        else:
            status_code = 400
            logger.error(f"Version approval failed for version {version_id}: {result.get('error')}")
        
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"Approve version error: {e}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@file_versioning_bp.route('/version/<version_id>/reject', methods=['POST'])
@jwt_required
def reject_file_version(version_id):
    """
    Reject a pending file version
    
    Expected JSON payload:
    {
        "rejection_reason": "Reason for rejection (required)"
    }
    """
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'success': False,
                'error': 'User not authenticated'
            }), 401
            
        current_user_id = current_user.get('user_id')
        data = request.get_json()
        
        if not data or 'rejection_reason' not in data:
            return jsonify({
                'success': False,
                'error': 'rejection_reason is required'
            }), 400
        
        rejection_reason = data['rejection_reason']
        
        if not rejection_reason.strip():
            return jsonify({
                'success': False,
                'error': 'rejection_reason cannot be empty'
            }), 400
        
        # Reject version
        result = FileVersionManager.reject_version(
            version_id=version_id,
            rejector_id=current_user_id,
            rejection_reason=rejection_reason
        )
        
        if result['success']:
            status_code = 200
            logger.info(f"Version {version_id} rejected by user {current_user_id}")
        else:
            status_code = 400
            logger.error(f"Version rejection failed for version {version_id}: {result.get('error')}")
        
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"Reject version error: {e}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@file_versioning_bp.route('/file/<file_id>/versions', methods=['GET'])
@jwt_required
def get_file_version_history(file_id):
    """
    Get version history for a file
    
    Query parameters:
    - limit: Maximum number of versions to return (default: 10, max: 50)
    """
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'success': False,
                'error': 'User not authenticated'
            }), 401
            
        # Get limit parameter
        limit = min(int(request.args.get('limit', 10)), 50)
        
        # Get version history
        result = FileVersionManager.get_version_history(
            file_id=file_id,
            limit=limit
        )
        
        if result['success']:
            status_code = 200
        else:
            status_code = 400
        
        return jsonify(result), status_code
        
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid limit parameter'
        }), 400
    except Exception as e:
        logger.error(f"Get version history error: {e}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@file_versioning_bp.route('/versions/pending', methods=['GET'])
@jwt_required
def get_pending_approvals():
    """
    Get versions pending approval for the current user
    """
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'success': False,
                'error': 'User not authenticated'
            }), 401
            
        current_user_id = current_user.get('user_id')
        
        # Get pending approvals
        result = FileVersionManager.get_pending_approvals(
            approver_id=current_user_id
        )
        
        if result['success']:
            status_code = 200
        else:
            status_code = 400
        
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"Get pending approvals error: {e}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@file_versioning_bp.route('/integrity/analyze', methods=['POST'])
@jwt_required
def analyze_file_integrity():
    """
    Analyze file integrity between two versions
    
    Expected JSON payload:
    {
        "old_file_data": "base64_encoded_old_file_data",
        "new_file_data": "base64_encoded_new_file_data",
        "old_metadata": {...} // Optional
    }
    """
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'success': False,
                'error': 'User not authenticated'
            }), 401
            
        current_user_id = current_user.get('user_id')
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validate required fields
        required_fields = ['old_file_data', 'new_file_data']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'{field} is required'
                }), 400
        
        # Decode base64 file data
        try:
            old_file_data = base64.b64decode(data['old_file_data'])
            new_file_data = base64.b64decode(data['new_file_data'])
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Invalid base64 file data: {str(e)}'
            }), 400
        
        # Get optional metadata
        old_metadata = data.get('old_metadata')
        
        # Create integrity report
        result = FileIntegrityManager.create_integrity_report(
            old_file_data=old_file_data,
            new_file_data=new_file_data,
            old_metadata=old_metadata
        )
        
        if result['success']:
            status_code = 200
            logger.info(f"Integrity analysis completed by user {current_user_id}")
        else:
            status_code = 400
        
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"Integrity analysis error: {e}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@file_versioning_bp.route('/integrity/validate', methods=['POST'])
@jwt_required
def validate_file_integrity():
    """
    Validate file integrity against expected hashes
    
    Expected JSON payload:
    {
        "file_data": "base64_encoded_file_data",
        "expected_hashes": {
            "sha256": "expected_sha256_hash",
            "md5": "expected_md5_hash"
        }
    }
    """
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'success': False,
                'error': 'User not authenticated'
            }), 401
            
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validate required fields
        required_fields = ['file_data', 'expected_hashes']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'{field} is required'
                }), 400
        
        # Decode base64 file data
        try:
            file_data = base64.b64decode(data['file_data'])
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Invalid base64 file data: {str(e)}'
            }), 400
        
        expected_hashes = data['expected_hashes']
        
        # Validate integrity
        result = FileIntegrityManager.validate_file_integrity(
            file_data=file_data,
            expected_hashes=expected_hashes
        )
        
        if result['success']:
            status_code = 200
        else:
            status_code = 400
        
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"Integrity validation error: {e}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

# Health check for versioning service
@file_versioning_bp.route('/versions/health', methods=['GET'])
def versioning_health():
    """Health check endpoint for file versioning service"""
    try:
        # Check if ssdeep is available
        from module.file_integrity import SSDEEP_AVAILABLE
        
        return jsonify({
            'status': 'healthy',
            'service': 'file_versioning',
            'features': {
                'version_management': True,
                'integrity_checking': True,
                'approval_workflow': True,
                'ssdeep_similarity': SSDEEP_AVAILABLE
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Versioning health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'service': 'file_versioning',
            'error': str(e)
        }), 500
