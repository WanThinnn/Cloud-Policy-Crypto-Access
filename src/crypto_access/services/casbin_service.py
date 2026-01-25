"""
PyCasbin Service for Hybrid RBAC + ABAC (Policy Decision Point - PDP)

Architecture:
============
Layer 1 - RBAC (UserType.permissions):
    - Defines BASE capabilities for each role
    - Quick coarse-grained check
    - If no base permission → DENY (fast path)
    
Layer 2 - ABAC (AccessPolicy):
    - Fine-grained conditional access
    - Can RESTRICT (deny with conditions) or EXTEND (allow with conditions)
    - Applied after RBAC passes

Flow:
=====
1. Check RBAC: Does user_type have permission for this action?
   - NO → DENY (no need to check ABAC)
   - YES → Continue to ABAC check
   
2. Check ABAC: Do any policies apply?
   - DENY policy matches → DENY
   - ALLOW policy matches → ALLOW
   - No policy matches → Use RBAC result (ALLOW)
"""

import casbin
import os
from django.conf import settings
from typing import Dict, Any, Optional, Tuple
from crypto_access.models import UserAttribute, AccessPolicy, UserType


# Permission mapping: action → required permissions
ACTION_PERMISSION_MAP = {
    # File/Document actions
    'read': ['file_read', 'file_view', '*'],
    'write': ['file_create', 'file_write', '*'],
    'update': ['file_update', 'file_write', '*'],
    'delete': ['file_delete', '*'],
    'upload': ['file_upload', 'file_create', '*'],
    'download': ['file_download', 'file_read', '*'],
    
    # Encryption actions
    'encrypt': ['file_encrypt', 'key_manage', '*'],
    'decrypt': ['file_decrypt', 'key_manage', '*'],
    
    # Management actions
    'manage': ['*'],
    'view': ['file_read', 'file_view', 'logs_view', 'reports_view', '*'],
    
    # Policy actions
    'policy_read': ['policy_view', '*'],
    'policy_write': ['policy_define', 'policy_manage', '*'],
    
    # User management
    'user_read': ['user_view', 'user_management', 'user_management_department', '*'],
    'user_write': ['user_create', 'user_management', '*'],
}

# Resource-specific permission prefixes
RESOURCE_PERMISSION_PREFIX = {
    'document': 'file_',
    'key': 'key_',
    'policy': 'policy_',
    'user': 'user_',
    'attribute': 'attribute_',
    'audit': 'logs_',
}


class CasbinService:
    """
    Hybrid RBAC + ABAC Policy Decision Point (PDP)
    
    RBAC Layer: UserType.permissions (base capabilities)
    ABAC Layer: AccessPolicy (conditional overrides)
    """
    
    _instance = None
    _enforcer = None
    
    def __new__(cls):
        """Singleton pattern for enforcer"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._enforcer is None:
            self._init_enforcer()
    
    def _init_enforcer(self):
        """Initialize Casbin enforcer with model and policies from database"""
        model_path = os.path.join(
            settings.BASE_DIR, 
            'config', 
            'casbin', 
            'abac_model.conf'
        )
        
        # Create enforcer with model only (policies loaded from DB)
        self._enforcer = casbin.Enforcer(model_path)
        
        # Load policies from database
        self._load_policies_from_db()
    
    def _load_policies_from_db(self):
        """Load all active policies from AccessPolicy model"""
        # Clear existing policies
        self._enforcer.clear_policy()
        
        # Load from database
        policies = AccessPolicy.objects.filter(is_active=True).order_by('priority')
        for policy in policies:
            # Add policy: sub_rule, obj, act, eft
            self._enforcer.add_policy(
                policy.subject_condition,
                policy.resource,
                policy.action,
                policy.effect
            )
    
    def reload_policies(self):
        """Reload policies from database (call after policy changes)"""
        self._load_policies_from_db()
    
    def get_user_attributes(self, user) -> Dict[str, Any]:
        """
        Get all active attributes for a user as a dictionary
        Includes user_type from UserProfile
        """
        attrs = {}
        
        # Get user type from profile
        if hasattr(user, 'profile'):
            profile = user.profile
            attrs['user_type'] = profile.get_user_type_code()
            
            # Add user type permissions for reference
            if profile.user_type_ref:
                attrs['permissions'] = profile.user_type_ref.permissions
        
        # Get ABAC attributes from UserAttribute model
        user_attrs = UserAttribute.get_user_attributes(user)
        attrs.update(user_attrs)
        
        # Add basic user info
        attrs['username'] = user.username
        attrs['is_staff'] = user.is_staff
        attrs['is_superuser'] = user.is_superuser
        
        return attrs
    
    def _check_rbac(self, user, resource: str, action: str) -> Tuple[bool, str]:
        """
        Layer 1: RBAC Check - Does user_type have base permission?
        
        Returns:
            Tuple[bool, str]: (has_permission, reason)
        """
        # Superuser bypasses RBAC
        if user.is_superuser:
            return True, "superuser_bypass"
        
        if not hasattr(user, 'profile') or not user.profile.user_type_ref:
            return False, "no_user_type"
        
        user_type = user.profile.user_type_ref
        user_permissions = set(user_type.permissions)
        
        # Check for wildcard permission
        if '*' in user_permissions:
            return True, "wildcard_permission"
        
        # Get required permissions for this action
        required_perms = ACTION_PERMISSION_MAP.get(action, [action, '*'])
        
        # Add resource-specific permission
        prefix = RESOURCE_PERMISSION_PREFIX.get(resource, '')
        if prefix:
            required_perms = required_perms + [f"{prefix}{action}", f"{prefix}*"]
        
        # Check if user has any of the required permissions
        if user_permissions.intersection(required_perms):
            return True, f"rbac_allowed:{list(user_permissions.intersection(required_perms))[0]}"
        
        return False, f"rbac_denied:missing_permission_for_{action}"
    
    def _check_abac(self, user, resource: str, action: str) -> Tuple[Optional[bool], str]:
        """
        Layer 2: ABAC Check - Apply fine-grained policies
        
        Returns:
            Tuple[Optional[bool], str]: 
                - (True, reason) if explicitly allowed
                - (False, reason) if explicitly denied
                - (None, reason) if no matching policy (defer to RBAC)
        """
        # Get user attributes
        attrs = self.get_user_attributes(user)
        
        # Create a simple namespace for eval()
        class AttrNamespace:
            def __init__(self, attributes):
                for k, v in attributes.items():
                    setattr(self, k, v)
            
            def __getattr__(self, name):
                return None
        
        sub = AttrNamespace(attrs)
        
        try:
            # Check with Casbin enforcer
            result = self._enforcer.enforce(sub, resource, action)
            
            if result:
                return True, "abac_policy_allowed"
            else:
                # Check if there's an explicit deny policy
                # If no policy matched at all, return None
                matching_policies = AccessPolicy.objects.filter(
                    is_active=True,
                    resource__in=[resource, '*'],
                    action__in=[action, '*']
                )
                
                if matching_policies.exists():
                    return False, "abac_policy_denied"
                else:
                    return None, "no_abac_policy"
                    
        except Exception as e:
            print(f"ABAC check error: {e}")
            return None, f"abac_error:{str(e)}"
    
    def check_access(self, user, resource: str, action: str) -> bool:
        """
        Hybrid RBAC + ABAC Access Check
        
        Flow:
        1. RBAC Check (base permission)
           - DENY → Return False
           - ALLOW → Continue
        2. ABAC Check (conditional policies)  
           - Explicit DENY → Return False
           - Explicit ALLOW → Return True
           - No policy → Use RBAC result (True)
        
        Args:
            user: Django User object
            resource: Resource name (e.g., 'document', 'key')
            action: Action name (e.g., 'read', 'write', 'delete')
        
        Returns:
            bool: True if access is allowed, False otherwise
        """
        # Layer 1: RBAC Check
        rbac_allowed, rbac_reason = self._check_rbac(user, resource, action)
        
        if not rbac_allowed:
            # RBAC denied - no need to check ABAC
            return False
        
        # Layer 2: ABAC Check (only if RBAC passed)
        abac_result, abac_reason = self._check_abac(user, resource, action)
        
        if abac_result is False:
            # Explicit ABAC deny
            return False
        elif abac_result is True:
            # Explicit ABAC allow
            return True
        else:
            # No ABAC policy matched - use RBAC result
            return rbac_allowed
    
    def check_access_with_context(
        self, 
        user, 
        resource: str, 
        action: str,
        resource_attrs: Optional[Dict] = None
    ) -> bool:
        """
        Extended access check with resource attributes (for future use)
        """
        return self.check_access(user, resource, action)
    
    def get_allowed_actions(self, user, resource: str) -> list:
        """
        Get list of actions a user is allowed to perform on a resource
        """
        all_actions = ['read', 'write', 'update', 'delete', 'upload', 'download', 'encrypt', 'decrypt', 'manage']
        return [action for action in all_actions if self.check_access(user, resource, action)]
    
    def explain_decision(self, user, resource: str, action: str) -> dict:
        """
        Explain why an access decision was made (for debugging/audit)
        """
        attrs = self.get_user_attributes(user)
        
        # Check each layer
        rbac_allowed, rbac_reason = self._check_rbac(user, resource, action)
        abac_result, abac_reason = self._check_abac(user, resource, action)
        final_allowed = self.check_access(user, resource, action)
        
        # Find matching policies
        matching_policies = AccessPolicy.objects.filter(
            is_active=True,
            resource__in=[resource, '*'],
            action__in=[action, '*']
        ).order_by('priority')
        
        # Get user_type permissions
        user_type_perms = []
        if hasattr(user, 'profile') and user.profile.user_type_ref:
            user_type_perms = user.profile.user_type_ref.permissions
        
        return {
            'final_decision': 'ALLOW' if final_allowed else 'DENY',
            'user': user.username,
            'resource': resource,
            'action': action,
            
            # Layer 1: RBAC
            'rbac_layer': {
                'result': 'ALLOW' if rbac_allowed else 'DENY',
                'reason': rbac_reason,
                'user_type': attrs.get('user_type'),
                'user_type_permissions': user_type_perms,
            },
            
            # Layer 2: ABAC
            'abac_layer': {
                'result': 'ALLOW' if abac_result is True else ('DENY' if abac_result is False else 'NO_POLICY'),
                'reason': abac_reason,
                'matching_policies': [
                    {
                        'name': p.name,
                        'condition': p.subject_condition,
                        'effect': p.effect,
                        'priority': p.priority
                    }
                    for p in matching_policies
                ]
            },
            
            # User context
            'user_attributes': attrs,
        }


# Singleton instance
casbin_service = CasbinService()
