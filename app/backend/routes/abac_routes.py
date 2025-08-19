"""
ABAC (Attribute-Based Access Control) API routes
"""
from flask import Blueprint, request, jsonify, session
import logging
import asyncio
import sys
import os

# Add parent directory to path to import module
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from module.abac import abac

logger = logging.getLogger(__name__)

# Create ABAC Blueprint
abac_api = Blueprint('abac', __name__, url_prefix='/abac')

def run_async(async_func):
    """Helper to run async functions in sync context"""
    def wrapper(*args, **kwargs):
        return asyncio.run(async_func(*args, **kwargs))
    return wrapper

@abac_api.route('/policies', methods=['POST'])
def create_policy():
    """
    Tạo policy mới cho access control
    
    Expected JSON:
    {
        "name": "medical_records_read",
        "description": "Allow doctors to read medical records",
        "resource": "files",
        "action": "read",
        "conditions": {
            "subject_attributes": ["role:doctor", "department:cardiology"],
            "resource_attributes": ["type:medical_record"],
            "environment": ["time_range:work_hours"]
        },
        "effect": "permit"
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
        required_fields = ['name', 'resource', 'action', 'effect']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Validate effect
        if data['effect'] not in ['permit', 'deny']:
            return jsonify({
                'success': False,
                'error': 'Effect must be either "permit" or "deny"'
            }), 400
        
        result = abac.create_policy(data)
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Create policy error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@abac_api.route('/policies', methods=['GET'])
def list_policies():
    """Liệt kê tất cả policies"""
    try:
        policies = abac.list_policies()
        
        return jsonify({
            'success': True,
            'policies': policies,
            'total_count': len(policies)
        })
        
    except Exception as e:
        logger.error(f"List policies error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@abac_api.route('/policies/<policy_id>', methods=['DELETE'])
def delete_policy(policy_id):
    """Xóa policy"""
    try:
        result = abac.delete_policy(policy_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Delete policy error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@abac_api.route('/users/<user_id>/attributes', methods=['POST'])
def set_user_attributes(user_id):
    """
    Thiết lập attributes cho user
    
    Expected JSON:
    {
        "role": "doctor",
        "department": "cardiology", 
        "clearance_level": "high",
        "specialty": "heart_surgery",
        "organization": "hospital_a"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No attributes provided'
            }), 400
        
        result = abac.set_user_attributes(user_id, data)
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Set user attributes error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@abac_api.route('/users/<user_id>/attributes', methods=['GET'])
def get_user_attributes(user_id):
    """Lấy attributes của user"""
    try:
        result = abac.get_user_attributes(user_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 404
            
    except Exception as e:
        logger.error(f"Get user attributes error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@abac_api.route('/check-access', methods=['POST'])
def check_access():
    """
    Kiểm tra quyền truy cập
    
    Expected JSON:
    {
        "user_id": "user_123",
        "resource": "files",
        "action": "read",
        "resource_attributes": {
            "file_type": "medical_record",
            "owner_id": "patient_456",
            "sensitivity": "high"
        },
        "context": {
            "time": "2025-08-19T10:00:00Z",
            "ip_address": "192.168.1.1"
        }
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No request data provided'
            }), 400
        
        # Validate required fields
        required_fields = ['user_id', 'resource', 'action']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        result = abac.check_access(data)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Check access error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@abac_api.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'ABAC API',
        'message': 'ABAC service is running'
    })

# Example policies để test
@abac_api.route('/setup-example-policies', methods=['POST'])
def setup_example_policies():
    """Tạo các policies mẫu cho testing"""
    try:
        example_policies = [
            {
                'name': 'doctors_read_medical_files',
                'description': 'Allow doctors to read medical files',
                'resource': 'files',
                'action': 'read',
                'conditions': {
                    'subject_attributes': ['role:doctor'],
                    'resource_attributes': ['type:medical_record'],
                    'environment': []
                },
                'effect': 'permit'
            },
            {
                'name': 'nurses_read_department_files',
                'description': 'Allow nurses to read files in their department',
                'resource': 'files',
                'action': 'read',
                'conditions': {
                    'subject_attributes': ['role:nurse'],
                    'resource_attributes': ['type:nursing_note'],
                    'environment': []
                },
                'effect': 'permit'
            },
            {
                'name': 'patients_read_own_files',
                'description': 'Allow patients to read their own files',
                'resource': 'files',
                'action': 'read',
                'conditions': {
                    'subject_attributes': ['role:patient'],
                    'resource_attributes': [],
                    'environment': []
                },
                'effect': 'permit'
            },
            {
                'name': 'admins_full_access',
                'description': 'Allow admins full access to all files',
                'resource': 'files',
                'action': 'read',
                'conditions': {
                    'subject_attributes': ['role:admin'],
                    'resource_attributes': [],
                    'environment': []
                },
                'effect': 'permit'
            }
        ]
        
        created_policies = []
        errors = []
        
        for policy_data in example_policies:
            result = abac.create_policy(policy_data)
            if result['success']:
                created_policies.append(policy_data['name'])
            else:
                errors.append(f"{policy_data['name']}: {result['error']}")
        
        return jsonify({
            'success': True,
            'created_policies': created_policies,
            'errors': errors,
            'message': f'Created {len(created_policies)} example policies'
        })
        
    except Exception as e:
        logger.error(f"Setup example policies error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500
