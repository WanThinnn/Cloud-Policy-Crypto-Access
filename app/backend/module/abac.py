"""
ABAC (Attribute-Based Access Control) module for Flask backend
"""
import logging
from typing import Dict, Any, List
from firebase_admin import firestore
from .database import db
from .user_management import user_manager

logger = logging.getLogger(__name__)

class AttributeBasedAccessControl:
    """
    ABAC implementation for access control based on user attributes
    """
    
    def __init__(self):
        self.policies_collection = db.collection('access_policies')
        self.user_attributes_collection = db.collection('user_attributes')
        
    def create_policy(self, policy_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tạo policy mới cho access control
        
        Args:
            policy_data: {
                'name': 'policy_name',
                'description': 'Policy description',
                'resource': 'files',  # hoặc 'users', 'admin', etc.
                'action': 'read',     # 'read', 'write', 'delete', 'share'
                'conditions': {
                    'subject_attributes': ['role:doctor', 'department:cardiology'],
                    'resource_attributes': ['type:medical_record', 'sensitivity:high'],
                    'environment': ['time_range:work_hours']
                },
                'effect': 'permit'  # 'permit' hoặc 'deny'
            }
            
        Returns:
            Dict with success status and policy data
        """
        try:
            policy_id = policy_data.get('name', f"policy_{len(list(self.policies_collection.get()))}")
            
            policy_doc = {
                'id': policy_id,
                'name': policy_data['name'],
                'description': policy_data.get('description', ''),
                'resource': policy_data['resource'],
                'action': policy_data['action'],
                'conditions': policy_data['conditions'],
                'effect': policy_data['effect'],
                'created_at': firestore.SERVER_TIMESTAMP,
                'is_active': True
            }
            
            self.policies_collection.document(policy_id).set(policy_doc)
            
            logger.info(f"Policy created: {policy_id}")
            return {
                'success': True,
                'policy_id': policy_id,
                'message': 'Policy created successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to create policy: {e}")
            return {
                'success': False,
                'error': f'Failed to create policy: {str(e)}'
            }
    
    def set_user_attributes(self, user_id: str, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Thiết lập attributes cho user
        
        Args:
            user_id: User ID
            attributes: {
                'role': 'doctor',
                'department': 'cardiology', 
                'clearance_level': 'high',
                'specialty': 'heart_surgery',
                'organization': 'hospital_a'
            }
            
        Returns:
            Dict with success status
        """
        try:
            attribute_doc = {
                'user_id': user_id,
                'attributes': attributes,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            self.user_attributes_collection.document(user_id).set(attribute_doc)
            
            logger.info(f"User attributes set for user: {user_id}")
            return {
                'success': True,
                'message': 'User attributes set successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to set user attributes: {e}")
            return {
                'success': False,
                'error': f'Failed to set user attributes: {str(e)}'
            }
    
    def get_user_attributes(self, user_id: str) -> Dict[str, Any]:
        """
        Lấy attributes của user
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with user attributes
        """
        try:
            attr_doc = self.user_attributes_collection.document(user_id).get()
            
            if not attr_doc.exists:
                return {
                    'success': False,
                    'error': 'User attributes not found'
                }
            
            return {
                'success': True,
                'attributes': attr_doc.to_dict()['attributes']
            }
            
        except Exception as e:
            logger.error(f"Failed to get user attributes: {e}")
            return {
                'success': False,
                'error': f'Failed to get user attributes: {str(e)}'
            }
    
    def check_access(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Kiểm tra quyền truy cập dựa trên ABAC
        
        Args:
            request_data: {
                'user_id': 'user_123',
                'resource': 'files',
                'action': 'read',
                'resource_attributes': {
                    'file_type': 'medical_record',
                    'owner_id': 'patient_456',
                    'sensitivity': 'high'
                },
                'context': {
                    'time': '2025-08-19T10:00:00Z',
                    'ip_address': '192.168.1.1'
                }
            }
            
        Returns:
            Dict with access decision
        """
        try:
            user_id = request_data['user_id']
            resource = request_data['resource']
            action = request_data['action']
            resource_attributes = request_data.get('resource_attributes', {})
            context = request_data.get('context', {})
            
            # Lấy attributes của user
            user_attrs_result = self.get_user_attributes(user_id)
            if not user_attrs_result['success']:
                return {
                    'success': False,
                    'access_granted': False,
                    'reason': 'User attributes not found'
                }
            
            user_attributes = user_attrs_result['attributes']
            
            # Lấy các policies có liên quan
            relevant_policies = self._get_relevant_policies(resource, action)
            
            # Đánh giá từng policy
            access_decision = self._evaluate_policies(
                relevant_policies, 
                user_attributes, 
                resource_attributes, 
                context
            )
            
            logger.info(f"Access check for user {user_id}: {access_decision['access_granted']}")
            
            return {
                'success': True,
                'access_granted': access_decision['access_granted'],
                'reason': access_decision['reason'],
                'matched_policies': access_decision['matched_policies']
            }
            
        except Exception as e:
            logger.error(f"Failed to check access: {e}")
            return {
                'success': False,
                'access_granted': False,
                'error': f'Failed to check access: {str(e)}'
            }
    
    def _get_relevant_policies(self, resource: str, action: str) -> List[Dict]:
        """Lấy các policies liên quan đến resource và action"""
        try:
            policies = self.policies_collection.where('resource', '==', resource)\
                                              .where('action', '==', action)\
                                              .where('is_active', '==', True)\
                                              .get()
            
            return [policy.to_dict() for policy in policies]
            
        except Exception as e:
            logger.error(f"Failed to get relevant policies: {e}")
            return []
    
    def _evaluate_policies(self, policies: List[Dict], user_attributes: Dict, 
                          resource_attributes: Dict, context: Dict) -> Dict[str, Any]:
        """Đánh giá các policies"""
        matched_policies = []
        permit_found = False
        deny_found = False
        
        for policy in policies:
            if self._evaluate_single_policy(policy, user_attributes, resource_attributes, context):
                matched_policies.append(policy['name'])
                
                if policy['effect'] == 'permit':
                    permit_found = True
                elif policy['effect'] == 'deny':
                    deny_found = True
        
        # Deny có ưu tiên cao hơn permit
        if deny_found:
            return {
                'access_granted': False,
                'reason': 'Access denied by policy',
                'matched_policies': matched_policies
            }
        elif permit_found:
            return {
                'access_granted': True,
                'reason': 'Access granted by policy',
                'matched_policies': matched_policies
            }
        else:
            return {
                'access_granted': False,
                'reason': 'No matching policy found',
                'matched_policies': []
            }
    
    def _evaluate_single_policy(self, policy: Dict, user_attributes: Dict, 
                               resource_attributes: Dict, context: Dict) -> bool:
        """Đánh giá một policy cụ thể"""
        try:
            conditions = policy.get('conditions', {})
            
            # Kiểm tra subject attributes
            subject_conditions = conditions.get('subject_attributes', [])
            if not self._check_attribute_conditions(subject_conditions, user_attributes):
                return False
            
            # Kiểm tra resource attributes
            resource_conditions = conditions.get('resource_attributes', [])
            if not self._check_attribute_conditions(resource_conditions, resource_attributes):
                return False
            
            # Kiểm tra environment conditions
            env_conditions = conditions.get('environment', [])
            if not self._check_environment_conditions(env_conditions, context):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to evaluate policy {policy.get('name', 'unknown')}: {e}")
            return False
    
    def _check_attribute_conditions(self, conditions: List[str], attributes: Dict) -> bool:
        """Kiểm tra attribute conditions"""
        if not conditions:
            return True
            
        for condition in conditions:
            if ':' not in condition:
                continue
                
            attr_name, attr_value = condition.split(':', 1)
            user_attr_value = attributes.get(attr_name)
            
            if user_attr_value != attr_value:
                return False
                
        return True
    
    def _check_environment_conditions(self, conditions: List[str], context: Dict) -> bool:
        """Kiểm tra environment conditions"""
        if not conditions:
            return True
            
        # Implement environment condition checking here
        # Ví dụ: time_range, IP range, etc.
        return True
    
    def list_policies(self) -> List[Dict]:
        """Liệt kê tất cả policies"""
        try:
            policies = self.policies_collection.where('is_active', '==', True).get()
            return [policy.to_dict() for policy in policies]
            
        except Exception as e:
            logger.error(f"Failed to list policies: {e}")
            return []
    
    def delete_policy(self, policy_id: str) -> Dict[str, Any]:
        """Xóa policy"""
        try:
            self.policies_collection.document(policy_id).update({'is_active': False})
            
            return {
                'success': True,
                'message': 'Policy deleted successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to delete policy: {e}")
            return {
                'success': False,
                'error': f'Failed to delete policy: {str(e)}'
            }

# Global ABAC instance
abac = AttributeBasedAccessControl()
