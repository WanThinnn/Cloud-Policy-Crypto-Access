"""
ABAC (Attribute-Based Access Control) API routes
"""
from flask import Blueprint, request, jsonify, session
import logging
import asyncio
import sys
import os
from datetime import datetime  # <-- THÊM DÒNG NÀY

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
    Check access với session-based authentication
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        # Lấy user từ session
        user_id = session.get('user_id')
        username = session.get('username')
        
        # Debug session info
        logger.info(f"Session user_id: {user_id}, username: {username}")
        
        # Allow manual user_id/username in request for testing
        if not user_id and not username:
            user_id = data.get('user_id')
            username = data.get('username')
        
        # Allow fallback to user_attributes directly
        if data.get('user_attributes'):
            user_attributes = data['user_attributes']
            logger.info(f"Using manual user_attributes: {user_attributes}")
        else:
            if not user_id and not username:
                return jsonify({
                    'success': False,
                    'error': 'User not authenticated and no user_attributes provided',
                    'session_info': {
                        'user_id': session.get('user_id'),
                        'username': session.get('username'),
                        'all_session_keys': list(session.keys())
                    }
                }), 401

            # Get user attributes from SuperAdmin system
            from module.super_admin import super_admin
            
            user_attributes = {}
            user_info = None
            
            # Try different approaches to get user info
            try:
                # Method 1: Direct API call style
                if hasattr(super_admin, 'get_all_users'):
                    users_result = super_admin.get_all_users()
                elif hasattr(super_admin, 'list_all_users'):
                    users_result = super_admin.list_all_users()
                elif hasattr(super_admin, 'get_users'):
                    users_result = super_admin.get_users()
                else:
                    # Check what methods are available
                    available_methods = [method for method in dir(super_admin) 
                                       if not method.startswith('_') and 'user' in method.lower()]
                    logger.info(f"Available SuperAdmin methods: {available_methods}")
                    
                    return jsonify({
                        'success': False,
                        'error': 'SuperAdmin user lookup methods not found',
                        'available_methods': available_methods
                    }), 500
                
                # Find user in results
                if users_result and users_result.get('success'):
                    for user in users_result.get('users', []):
                        if (user_id and user.get('id') == user_id) or \
                           (username and user.get('username') == username):
                            user_attributes = user.get('attributes', {})
                            user_info = user
                            break
                
                if not user_attributes:
                    return jsonify({
                        'success': False,
                        'error': 'User not found in SuperAdmin database',
                        'user_id': user_id,
                        'username': username,
                        'users_result': users_result
                    }), 404
                    
            except Exception as e:
                logger.error(f"Error getting user from SuperAdmin: {e}")
                return jsonify({
                    'success': False,
                    'error': f'Failed to get user info: {str(e)}'
                }), 500

        # Lấy resource và action từ request
        resource = data.get('resource')
        action = data.get('action')
        
        if not resource or not action:
            return jsonify({
                'success': False,
                'error': 'Missing resource or action'
            }), 400

        # Check access với ABAC engine
        try:
            access_result = abac.check_access(
                user_attributes=user_attributes,
                resource=resource,
                action=action
            )
        except Exception as e:
            logger.error(f"ABAC engine error: {e}")
            # Fallback: simple attribute-based check
            access_granted = False
            reason = f"ABAC engine error: {str(e)}"
            
            # Simple fallback logic
            if resource == "server_configuration" and action == "read":
                if user_attributes.get('role') == 'manager' and \
                   user_attributes.get('department') == 'it' and \
                   user_attributes.get('clearance_level') in ['high', 'top_secret']:
                    access_granted = True
                    reason = "Access granted by fallback policy"
                else:
                    reason = "Access denied by fallback policy"
            
            access_result = {
                'granted': access_granted,
                'reason': reason
            }

        return jsonify({
            'success': True,
            'access_granted': access_result.get('granted', False),
            'user_id': user_id,
            'username': username,
            'user_attributes': user_attributes,
            'resource': resource,
            'action': action,
            'reason': access_result.get('reason', 'Policy evaluation completed'),
            'debug_info': {
                'session_keys': list(session.keys()),
                'has_user_info': user_info is not None
            }
        })

    except Exception as e:
        logger.error(f"ABAC check access error: {e}")
        return jsonify({
            'success': False,
            'error': f'ABAC access check failed: {str(e)}',
            'debug_info': {
                'user_id': locals().get('user_id'),
                'username': locals().get('username'),
                'session_keys': list(session.keys())
            }
        }), 500

@abac_api.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'ABAC API',
        'message': 'ABAC service is running'
    })

# Thay thế endpoint setup-example-policies bằng corporate policies
@abac_api.route('/setup-corporate-policies', methods=['POST'])
def setup_corporate_policies():
    """Tạo các policies thật cho Corporate CP-ABE system"""
    try:
        corporate_policies = [
            # ===========================================
            # IT DEPARTMENT POLICIES
            # ===========================================
            {
                'name': 'it_managers_server_access',
                'description': 'IT Managers can access server configuration and infrastructure data',
                'resource': 'server_configuration',
                'action': 'read',
                'conditions': {
                    'subject_attributes': ['role:manager', 'department:it'],
                    'resource_attributes': ['classification:confidential'],
                    'environment': ['business_hours:true']
                },
                'effect': 'permit'
            },
            {
                'name': 'it_staff_technical_docs',
                'description': 'IT Staff can read technical documentation',
                'resource': 'technical_documents',
                'action': 'read',
                'conditions': {
                    'subject_attributes': ['department:it', 'clearance_level:medium'],
                    'resource_attributes': ['type:technical_doc'],
                    'environment': []
                },
                'effect': 'permit'
            },
            {
                'name': 'it_high_clearance_sensitive',
                'description': 'High clearance IT personnel access sensitive systems',
                'resource': 'sensitive_data',
                'action': 'read',
                'conditions': {
                    'subject_attributes': ['department:it', 'clearance_level:high'],
                    'resource_attributes': ['sensitivity:high'],
                    'environment': ['location:office']
                },
                'effect': 'permit'
            },
            
            # ===========================================
            # HR DEPARTMENT POLICIES
            # ===========================================
            {
                'name': 'hr_staff_employee_records',
                'description': 'HR Staff can access employee records and personal information',
                'resource': 'employee_records',
                'action': 'read',
                'conditions': {
                    'subject_attributes': ['role:hr_staff', 'department:hr'],
                    'resource_attributes': ['type:personnel_data'],
                    'environment': ['compliance_audit:false']
                },
                'effect': 'permit'
            },
            {
                'name': 'hr_managers_payroll_access',
                'description': 'HR Managers can access payroll and salary information',
                'resource': 'payroll_data',
                'action': 'read',
                'conditions': {
                    'subject_attributes': ['role:manager', 'department:hr', 'clearance_level:high'],
                    'resource_attributes': ['classification:restricted'],
                    'environment': ['business_hours:true']
                },
                'effect': 'permit'
            },
            {
                'name': 'hr_recruitment_documents',
                'description': 'HR Staff can manage recruitment documents',
                'resource': 'recruitment_files',
                'action': 'write',
                'conditions': {
                    'subject_attributes': ['department:hr', 'role:hr_staff'],
                    'resource_attributes': ['type:recruitment'],
                    'environment': []
                },
                'effect': 'permit'
            },
            
            # ===========================================
            # FINANCE DEPARTMENT POLICIES
            # ===========================================
            {
                'name': 'finance_staff_financial_reports',
                'description': 'Finance Staff can access financial reports and accounting data',
                'resource': 'financial_data',
                'action': 'read',
                'conditions': {
                    'subject_attributes': ['role:finance_staff', 'department:finance'],
                    'resource_attributes': ['type:financial_report'],
                    'environment': ['audit_period:false']
                },
                'effect': 'permit'
            },
            {
                'name': 'finance_managers_budget_control',
                'description': 'Finance Managers can access and modify budget information',
                'resource': 'budget_data',
                'action': 'write',
                'conditions': {
                    'subject_attributes': ['role:manager', 'department:finance', 'clearance_level:high'],
                    'resource_attributes': ['classification:restricted'],
                    'environment': ['business_hours:true']
                },
                'effect': 'permit'
            },
            {
                'name': 'finance_restricted_data',
                'description': 'Only high-clearance Finance personnel can access restricted financial data',
                'resource': 'financial_data',
                'action': 'read',
                'conditions': {
                    'subject_attributes': ['department:finance', 'data_access:restricted'],
                    'resource_attributes': ['sensitivity:restricted'],
                    'environment': ['secure_network:true']
                },
                'effect': 'permit'
            },
            
            # ===========================================
            # EXECUTIVE POLICIES
            # ===========================================
            {
                'name': 'executives_all_access',
                'description': 'Executive level has access to all company data',
                'resource': 'all_documents',
                'action': 'read',
                'conditions': {
                    'subject_attributes': ['role:executive'],
                    'resource_attributes': [],
                    'environment': ['executive_session:true']
                },
                'effect': 'permit'
            },
            {
                'name': 'ceo_unrestricted_access',
                'description': 'CEO has unrestricted access to all resources',
                'resource': 'all_resources',
                'action': 'read',
                'conditions': {
                    'subject_attributes': ['role:ceo'],
                    'resource_attributes': [],
                    'environment': []
                },
                'effect': 'permit'
            },
            
            # ===========================================
            # GENERAL EMPLOYEE POLICIES
            # ===========================================
            {
                'name': 'employees_public_documents',
                'description': 'All employees can access public company documents',
                'resource': 'public_documents',
                'action': 'read',
                'conditions': {
                    'subject_attributes': ['role:employee'],
                    'resource_attributes': ['classification:public'],
                    'environment': []
                },
                'effect': 'permit'
            },
            {
                'name': 'employees_internal_communication',
                'description': 'Employees can access internal communications and announcements',
                'resource': 'internal_communications',
                'action': 'read',
                'conditions': {
                    'subject_attributes': ['data_access:internal'],
                    'resource_attributes': ['type:announcement'],
                    'environment': ['work_hours:true']
                },
                'effect': 'permit'
            },
            
            # ===========================================
            # SECURITY POLICIES (DENY RULES)
            # ===========================================
            {
                'name': 'deny_external_network_sensitive',
                'description': 'Deny access to sensitive data from external networks',
                'resource': 'sensitive_data',
                'action': 'read',
                'conditions': {
                    'subject_attributes': [],
                    'resource_attributes': ['sensitivity:high'],
                    'environment': ['network_location:external']
                },
                'effect': 'deny'
            },
            {
                'name': 'deny_after_hours_restricted',
                'description': 'Deny access to restricted data outside business hours',
                'resource': 'financial_data',
                'action': 'read',
                'conditions': {
                    'subject_attributes': [],
                    'resource_attributes': ['classification:restricted'],
                    'environment': ['business_hours:false']
                },
                'effect': 'deny'
            },
            {
                'name': 'deny_low_clearance_confidential',
                'description': 'Deny low clearance users access to confidential data',
                'resource': 'confidential_data',
                'action': 'read',
                'conditions': {
                    'subject_attributes': ['clearance_level:low'],
                    'resource_attributes': ['classification:confidential'],
                    'environment': []
                },
                'effect': 'deny'
            },
            
            # ===========================================
            # DEPARTMENT CROSS-ACCESS POLICIES
            # ===========================================
            {
                'name': 'cross_department_managers',
                'description': 'Managers from any department can access general management documents',
                'resource': 'management_documents',
                'action': 'read',
                'conditions': {
                    'subject_attributes': ['role:manager'],
                    'resource_attributes': ['target_audience:managers'],
                    'environment': []
                },
                'effect': 'permit'
            },
            {
                'name': 'project_collaboration_access',
                'description': 'Team members can access shared project documents regardless of department',
                'resource': 'project_documents',
                'action': 'read',
                'conditions': {
                    'subject_attributes': ['project_member:true'],
                    'resource_attributes': ['type:project_file'],
                    'environment': ['project_active:true']
                },
                'effect': 'permit'
            }
        ]
        
        created_policies = []
        errors = []
        
        for policy_data in corporate_policies:
            try:
                result = abac.create_policy(policy_data)
                if result.get('success', False):
                    created_policies.append(policy_data['name'])
                else:
                    errors.append(f"{policy_data['name']}: {result.get('error', 'Unknown error')}")
            except Exception as e:
                errors.append(f"{policy_data['name']}: {str(e)}")
        
        return jsonify({
            'success': True,
            'created_policies': created_policies,
            'errors': errors,
            'total_policies': len(corporate_policies),
            'created_count': len(created_policies),
            'error_count': len(errors),
            'message': f'Corporate policies setup completed. Created {len(created_policies)}/{len(corporate_policies)} policies.'
        })
        
    except Exception as e:
        logger.error(f"Setup corporate policies error: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to setup corporate policies: {str(e)}'
        }), 500

# Corporate Access Check với enhanced logic
@abac_api.route('/check-corporate-access', methods=['POST'])
def check_corporate_access():
    """
    Enhanced corporate access check với specific business rules
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        # Extract parameters
        user_attributes = data.get('user_attributes', {})
        resource = data.get('resource')
        action = data.get('action')
        environment = data.get('environment', {})
        
        if not all([user_attributes, resource, action]):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: user_attributes, resource, action'
            }), 400

        # Enhanced corporate access logic
        access_granted = False
        reason = "Access denied by default"
        matching_policies = []
        
        # Corporate business rules
        role = user_attributes.get('role')
        department = user_attributes.get('department')
        clearance = user_attributes.get('clearance_level')
        data_access = user_attributes.get('data_access')
        
        # Rule 1: Executive override
        if role in ['executive', 'ceo']:
            access_granted = True
            reason = "Executive access granted"
            matching_policies.append('executives_all_access')
            
        # Rule 2: IT Department rules
        elif department == 'it':
            if resource == 'server_configuration' and role == 'manager':
                access_granted = True
                reason = "IT Manager server access"
                matching_policies.append('it_managers_server_access')
            elif resource in ['technical_documents', 'system_logs'] and clearance in ['medium', 'high']:
                access_granted = True
                reason = "IT staff technical access"
                matching_policies.append('it_staff_technical_docs')
            elif resource == 'sensitive_data' and clearance == 'high':
                access_granted = True
                reason = "High clearance IT access"
                matching_policies.append('it_high_clearance_sensitive')
                
        # Rule 3: HR Department rules
        elif department == 'hr':
            if resource == 'employee_records' and role in ['hr_staff', 'manager']:
                access_granted = True
                reason = "HR employee records access"
                matching_policies.append('hr_staff_employee_records')
            elif resource == 'payroll_data' and role == 'manager' and clearance == 'high':
                access_granted = True
                reason = "HR Manager payroll access"
                matching_policies.append('hr_managers_payroll_access')
                
        # Rule 4: Finance Department rules
        elif department == 'finance':
            if resource == 'financial_data' and role in ['finance_staff', 'manager']:
                access_granted = True
                reason = "Finance staff financial data access"
                matching_policies.append('finance_staff_financial_reports')
            elif resource == 'budget_data' and role == 'manager':
                access_granted = True
                reason = "Finance Manager budget access"
                matching_policies.append('finance_managers_budget_control')
            elif data_access == 'restricted' and clearance == 'high':
                access_granted = True
                reason = "High clearance finance access"
                matching_policies.append('finance_restricted_data')
                
        # Rule 5: General employee rules
        elif role == 'employee':
            if resource == 'public_documents' or data_access == 'public':
                access_granted = True
                reason = "Employee public document access"
                matching_policies.append('employees_public_documents')
            elif resource == 'internal_communications' and data_access == 'internal':
                access_granted = True
                reason = "Employee internal communication access"
                matching_policies.append('employees_internal_communication')
                
        # Rule 6: Cross-department manager access
        if role == 'manager' and resource == 'management_documents':
            access_granted = True
            reason = "Cross-department manager access"
            matching_policies.append('cross_department_managers')
            
        # Rule 7: Security denials (overrides permits)
        security_violations = []
        
        if environment.get('network_location') == 'external' and resource in ['sensitive_data', 'confidential_data']:
            access_granted = False
            reason = "SECURITY VIOLATION: External network access denied"
            security_violations.append('deny_external_network_sensitive')
            
        if not environment.get('business_hours', True) and resource in ['payroll_data', 'financial_data']:
            if data_access == 'restricted':
                access_granted = False
                reason = "SECURITY VIOLATION: After hours restricted access denied"
                security_violations.append('deny_after_hours_restricted')
                
        if clearance == 'low' and resource in ['confidential_data', 'server_configuration']:
            access_granted = False
            reason = "SECURITY VIOLATION: Insufficient clearance level"
            security_violations.append('deny_low_clearance_confidential')

        return jsonify({
            'success': True,
            'access_granted': access_granted,
            'reason': reason,
            'matching_policies': matching_policies,
            'security_violations': security_violations,
            'user_attributes': user_attributes,
            'resource': resource,
            'action': action,
            'environment': environment,
            'timestamp': datetime.utcnow().isoformat(),
            'policy_engine': 'Corporate CP-ABE ABAC'
        })

    except Exception as e:
        logger.error(f"Corporate access check error: {e}")
        return jsonify({
            'success': False,
            'error': f'Corporate access check failed: {str(e)}'
        }), 500
