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
    # File/Document actions - READ and DOWNLOAD are SEPARATE
    # File/Document actions
    'read': ['file_read', 'file_view', 'file_read_limited', 'file_download', '*'],  # Download permission implies read
    'download': ['file_download', '*'],  # Export file - requires explicit permission
    'write': ['file_create', 'file_write', 'file_upload', '*'],
    'update': ['file_update', 'file_write', '*'],
    'delete': ['file_delete', '*'],
    'upload': ['file_upload', '*'],
    
    # Encryption actions
    'encrypt': ['file_encrypt', 'key_manage', '*'],
    'decrypt': ['file_decrypt', 'key_manage', '*'],
    
    # Management actions
    'manage': ['*'],
    'view': ['file_read', 'file_view', 'file_read_limited', 'logs_view', 'reports_view', '*'],
    
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
        from django.db.utils import OperationalError, ProgrammingError
        
        # Clear existing policies
        self._enforcer.clear_policy()
        
        # Load from database
        try:
            policies = AccessPolicy.objects.filter(is_active=True).order_by('priority')
            for policy in policies:
                # Add policy: sub_rule, obj, act, eft
                self._enforcer.add_policy(
                    policy.subject_condition,
                    policy.resource,
                    policy.action,
                    policy.effect
                )
        except (OperationalError, ProgrammingError) as e:
            # This happens during makemigrations when the table/columns don't exist yet
            print(f"Skipping policy loading (likely during migrations): {e}")
    
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
        
        # Action aliases
        # If user requests X, check if they have policy for X OR any policy that implies X.
        # e.g. 'download' policy implies 'read' access, so if requesting 'read', check 'download' too.
        # 'write' policy implies 'upload' access, so if requesting 'upload', check 'write' too.
        action_aliases = {
            'read': ['read', 'download'],  # Requesting read -> check read OR download
            'view': ['view', 'read', 'download'],
            'download': ['download'],  # Requesting download -> ONLY check download
            'write': ['write'],
            'create': ['create', 'write'],
            'upload': ['upload', 'write', 'create'],
            'delete': ['delete', 'write']
        }
        
        actions_to_check = action_aliases.get(action, [action])
        
        try:
            # Check with Casbin enforcer for action and its aliases
            for check_action in actions_to_check:
                result = self._enforcer.enforce(sub, resource, check_action)
                if result:
                    return True, f"abac_policy_allowed:{check_action}"
            
            # No policy allowed - check if there's any matching policy at all
            # If no policy matched at all, return None to defer to RBAC
            all_actions = actions_to_check + ['*']
            matching_policies = AccessPolicy.objects.filter(
                is_active=True,
                resource__in=[resource, '*'],
                action__in=all_actions
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
        
        # Layer 2: ABAC Check
        abac_result, abac_reason = self._check_abac(user, resource, action)
        
        if abac_result is False:
            # Explicit ABAC deny (RESTRICT)
            return False
        elif abac_result is True:
            # Explicit ABAC allow (EXTEND)
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


    def check_file_access(self, user, bucket_name: str, file_path: str, action: str = 'read') -> Tuple[bool, str]:
        """
        Check if user has access to a specific file based on FileAccessPolicy.
        This checks the file-specific policies (assigned when uploading) rather than global policies.
        
        Flow:
        1. Get all policies assigned to this file (direct + inherited from folders)
        2. If no policies assigned → allow (default open, rely on RBAC)
        3. For each policy, evaluate if user matches the condition
        4. Apply effect (allow/deny) based on priority
        
        Args:
            user: Django User object
            bucket_name: Bucket name
            file_path: Path to the file
            action: Action being performed (read, download, etc.)
        
        Returns:
            Tuple[bool, str]: (is_allowed, reason)
        """
        from crypto_access.models import FileAccessPolicy
        
        # Get user attributes
        user_attrs = self.get_user_attributes(user)
        
        # Superuser always has access
        if user.is_superuser:
            return True, "superuser_bypass"
        
        # Get all policies for this file
        file_policies = FileAccessPolicy.get_policies_for_file(bucket_name, file_path)
        
        if not file_policies:
            # No file-specific policies - use general ABAC
            return True, "no_file_policy_default_allow"
        
        # Create namespace for condition evaluation
        class AttrNamespace:
            def __init__(self, attributes):
                for k, v in attributes.items():
                    setattr(self, k, v)
            
            def __getattr__(self, name):
                return None
        
        r_sub = AttrNamespace(user_attrs)
        
        # Evaluate each policy in priority order
        # Sort by priority (lower = higher priority)
        sorted_policies = sorted(file_policies, key=lambda p: p.priority)
        
        for policy in sorted_policies:
            # Check if action matches
            # If asking for download, requires explicit download or wildcard
            # If asking for read, download policy also grants read
            if action == 'download':
                if policy.action not in ['download', '*']:
                    continue
            elif action in ['read', 'view']:
                if policy.action not in ['read', 'view', 'download', '*']:
                    continue
            else:
                if policy.action not in [action, '*']:
                    continue
            
            # Evaluate the subject condition
            try:
                # Build evaluation context
                eval_context = {
                    'r': type('Request', (), {'sub': r_sub})(),
                    'True': True,
                    'False': False,
                    'true': True,
                    'false': False,
                }
                
                condition = policy.subject_condition
                
                # Evaluate the condition
                result = eval(condition, {"__builtins__": {}}, eval_context)
                
                if result:
                    # Condition matched - apply effect
                    if policy.effect == 'allow':
                        return True, f"file_policy_allowed:{policy.name}"
                    else:
                        return False, f"file_policy_denied:{policy.name}"
                        
            except Exception as e:
                # Log error but continue to next policy
                print(f"Error evaluating policy {policy.name}: {e}")
                continue
        
        # No policy matched user's attributes - deny by default when file has policies
        return False, "file_policy_no_match"
    
    def check_file_access_with_fallback(
        self, 
        user, 
        bucket_name: str, 
        file_path: str, 
        action: str = 'read'
    ) -> Tuple[bool, str]:
        """
        Combined check: File-specific policies + general RBAC/ABAC
        
        Flow:
        1. First check RBAC (base permission)
        2. Then check file-specific policies (if any)
        3. If no file policies, fall back to general ABAC
        """
        # Step 1: RBAC check
        rbac_allowed, rbac_reason = self._check_rbac(user, 'document', action)
        if not rbac_allowed:
            return False, rbac_reason
        
        # Step 2: Check file-specific policies
        file_access, file_reason = self.check_file_access(user, bucket_name, file_path, action)
        
        return file_access, file_reason


# Singleton instance
casbin_service = CasbinService()
