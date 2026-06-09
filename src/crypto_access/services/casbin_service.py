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
import re
import ast
import logging
from django.conf import settings
from django.core.cache import cache
from typing import Dict, Any, Optional, Tuple, List
from crypto_access.models import UserAttribute, AccessPolicy, UserType
from crypto_access.services.setting_service import SettingService

logger = logging.getLogger(__name__)


class ASTEvaluator(ast.NodeVisitor):
    def __init__(self, context):
        self.context = context
        
    def visit_BoolOp(self, node):
        if isinstance(node.op, ast.And):
            for value in node.values:
                if not self.visit(value):
                    return False
            return True
        elif isinstance(node.op, ast.Or):
            for value in node.values:
                if self.visit(value):
                    return True
            return False
            
    def visit_UnaryOp(self, node):
        if isinstance(node.op, ast.Not):
            return not self.visit(node.operand)
        raise ValueError(f"Unsupported unary operator: {type(node.op)}")
        
    def visit_Compare(self, node):
        left = self.visit(node.left)
        
        for op, comparator in zip(node.ops, node.comparators):
            right = self.visit(comparator)
            if isinstance(op, ast.Eq):
                if left != right: return False
            elif isinstance(op, ast.NotEq):
                if left == right: return False
            elif isinstance(op, ast.In):
                if left not in right: return False
            elif isinstance(op, ast.NotIn):
                if left in right: return False
            elif isinstance(op, ast.Lt):
                if left >= right: return False
            elif isinstance(op, ast.LtE):
                if left > right: return False
            elif isinstance(op, ast.Gt):
                if left <= right: return False
            elif isinstance(op, ast.GtE):
                if left < right: return False
            else:
                raise ValueError(f"Unsupported comparison operator: {type(op)}")
            left = right
        return True
        
    def visit_Name(self, node):
        # Could be a boolean or None
        if node.id == 'True': return True
        if node.id == 'False': return False
        if node.id == 'None': return None
        return node.id
        
    def visit_Attribute(self, node):
        def get_full_name(n):
            if isinstance(n, ast.Name):
                return n.id
            elif isinstance(n, ast.Attribute):
                return f"{get_full_name(n.value)}.{n.attr}"
            return ""
            
        full_name = get_full_name(node)
        
        # We strip the r.sub. prefix to lookup in flat context directly
        if full_name.startswith("r.sub."):
            attr_name = full_name[6:]
            return self.context.get(attr_name)
            
        return self.context.get(full_name)
        
    def visit_Constant(self, node):
        return node.value
        
    def visit_List(self, node):
        return [self.visit(elt) for elt in node.elts]
        
    def visit_Set(self, node):
        return {self.visit(elt) for elt in node.elts}
        
    def visit_Tuple(self, node):
        return tuple(self.visit(elt) for elt in node.elts)
        
    def generic_visit(self, node):
        raise ValueError(f"Unsupported AST node: {type(node)}")


def safe_eval_condition(condition: str, context: dict) -> bool:
    """
    Safely evaluate ABAC policy conditions using Python's AST module.
    Supports arbitrarily nested boolean grouping, compares, and attribute access.
    """
    try:
        if not condition or not condition.strip():
            return False
            
        # Normalize operators and syntax
        expr = condition.replace('&&', ' and ').replace('||', ' or ')
        expr = expr.strip()
        
        # Parse into an AST expression node
        tree = ast.parse(expr, mode='eval')
        
        # Evaluate safely using our strict visitor
        evaluator = ASTEvaluator(context)
        result = evaluator.visit(tree.body)
        return bool(result)
    except Exception as e:
        logger.error(f"AST evaluation error for condition '{condition}': {e}")
        return False

# Default mappings if settings are not available
DEFAULT_ACTION_PERMISSION_MAP = {
    'read': ['file_read', 'file_view', 'file_read_limited', 'file_download', '*'],
    'download': ['file_download', '*'],
    'write': ['file_create', 'file_write', 'file_upload', '*'],
    'update': ['file_update', 'file_write', '*'],
    'delete': ['file_delete', '*'],
    'upload': ['file_upload', '*'],
    'encrypt': ['file_encrypt', 'key_manage', '*'],
    'decrypt': ['file_decrypt', 'key_manage', '*'],
    'manage': ['*'],
    'view': ['file_read', 'file_view', 'file_read_limited', 'logs_view', 'reports_view', '*'],
    'policy_read': ['policy_view', '*'],
    'policy_write': ['policy_define', 'policy_manage', '*'],
    # User management
    'user_read': ['user_view', 'user_management', 'user_management_department', '*'],
    'user_write': ['user_create', 'user_management', '*'],
}

DEFAULT_ACTION_ALIASES = {
    'read': ['read', 'download'],
    'view': ['view', 'read', 'download'],
    'download': ['download'],
    'write': ['write'],
    'create': ['create', 'write'],
    'upload': ['upload', 'write', 'create'],
    'delete': ['delete', 'write']
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
        # Enforcer is initialized lazily when first accessed
        pass
        
    @property
    def enforcer(self):
        """Lazy initialization of enforcer"""
        if self._enforcer is None:
            self._init_enforcer()
        return self._enforcer
    
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
                resources = [r.strip() for r in policy.resource.split(',')]
                actions = [a.strip() for a in policy.action.split(',')]
                
                for res in resources:
                    if not res: continue
                    for act in actions:
                        if not act: continue
                        # Add policy: sub_rule, obj, act, eft
                        self._enforcer.add_policy(
                            policy.subject_condition,
                            res,
                            act,
                            policy.effect
                        )
        except Exception as e:
            # This happens during makemigrations/collectstatic when the DB is not ready
            print(f"Skipping policy loading (likely during setup/migrations): {e}")
    
    def reload_policies(self):
        """Reload policies from database (call after policy changes)"""
        if self._enforcer is not None:
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
        # Get ABAC attributes from UserAttribute model
        user_attrs = UserAttribute.get_user_attributes(user)
        attrs.update(user_attrs)
        
        # Add basic user info
        attrs['username'] = user.username
        attrs['is_staff'] = user.is_staff
        attrs['is_superuser'] = user.is_superuser
        
        return attrs
    
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
        
        # Create a simple namespace for condition evaluation
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
        action_aliases = SettingService.get_setting('ACTION_ALIASES', DEFAULT_ACTION_ALIASES)
        
        actions_to_check = action_aliases.get(action, [action])
        
        try:
            # Check with Casbin enforcer for action and its aliases
            for check_action in actions_to_check:
                result = self.enforcer.enforce(sub, resource, check_action)
                if result:
                    return True, f"abac_policy_allowed:{check_action}"
            
            # No policy allowed - check if there's any explicitly DENY matching policy
            # If no explicitly DENY policy matched, return None to defer to RBAC
            all_actions = actions_to_check + ['*']
            matching_policies = AccessPolicy.objects.filter(
                is_active=True,
                effect='deny'
            )
            
            # Since resource/action can be comma separated now, we just filter python-side
            # or evaluate all deny policies to see if they apply to this resource/action
            # Actually we can just let Casbin check deny policies! But Casbin enforcer
            # doesn't have an easy way to check if it matched a deny.
            # We'll manually check the DENY policies in the DB.
            for policy in matching_policies:
                resources = [r.strip() for r in policy.resource.split(',')]
                actions = [a.strip() for a in policy.action.split(',')]
                
                if (resource in resources or '*' in resources) and \
                   (any(act in actions for act in all_actions) or '*' in actions):
                    # Resource and action match, check condition
                    if safe_eval_condition(policy.subject_condition, attrs):
                        return False, "abac_policy_explicit_deny"
            
            return None, "no_abac_policy"
                    
        except Exception as e:
            logger.error(f"ABAC check error: {e}")
            return None, f"abac_error:{str(e)}"
    
    def check_access(self, user, resource: str, action: str) -> bool:
        """
        Pure ABAC Access Check
        
        Flow:
        - Check ABAC (conditional policies)  
           - Explicit ALLOW → Return True
           - Explicit DENY → Return False
           - No policy → Return False (Default Deny)
           
        Superusers bypass all checks.
        """
        if user.is_superuser:
            return True
            
        abac_result, abac_reason = self._check_abac(user, resource, action)
        
        if abac_result is True:
            # Explicit ABAC allow
            return True
        else:
            # Deny if explicit deny or no policy matches
            return False
    
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
        
        # Check ABAC layer
        abac_result, abac_reason = self._check_abac(user, resource, action)
        final_allowed = self.check_access(user, resource, action)
        
        # Find matching policies
        matching_policies = AccessPolicy.objects.filter(
            is_active=True,
            resource__in=[resource, '*'],
            action__in=[action, '*']
        ).order_by('priority')
        
        return {
            'final_decision': 'ALLOW' if final_allowed else 'DENY',
            'user': user.username,
            'resource': resource,
            'action': action,
            
            # Layer: ABAC
            'abac_layer': {
                'result': 'ALLOW' if abac_result is True else ('DENY' if abac_result is False else 'NO_POLICY'),
                'reason': abac_reason,
            },
            
            'matching_policies_count': matching_policies.count(),
            'user_attributes': attrs
        }


    def get_allowed_policies_for_user(self, user, action: str = 'read') -> list[int]:
        """
        Pre-evaluates all active policies for a given user and action.
        Returns a list of AccessPolicy IDs that evaluate to 'allow' for the user.
        Results are cached for 30 seconds per user+action combination.
        """
        import hashlib, json
        from crypto_access.models import AccessPolicy
        
        # Check cache first
        user_attrs = self.get_user_attributes(user)
        attrs_str = json.dumps(user_attrs, sort_keys=True)
        attrs_hash = hashlib.sha256(attrs_str.encode()).hexdigest()[:16]
        cache_key = f"allowed_policies_{user.id}_{action}_{attrs_hash}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        
        if user.is_superuser:
            return list(AccessPolicy.objects.filter(is_active=True).values_list('id', flat=True))
            
        user_attrs = self.get_user_attributes(user)
        
        class AttrNamespace:
            def __init__(self, attributes):
                for k, v in attributes.items():
                    setattr(self, k, v)
            
            def __getattr__(self, name):
                return None
        
        r_sub = AttrNamespace(user_attrs)
        eval_context = {
            'r': type('Request', (), {'sub': r_sub})(),
            'True': True,
            'False': False,
            'true': True,
            'false': False,
        }
        
        allowed_policy_ids = []
        all_policies = AccessPolicy.objects.filter(is_active=True)
        
        for policy in all_policies:
            if action == 'download':
                if policy.action not in ['download', 'manage', '*']:
                    continue
            elif action in ['read', 'view']:
                if policy.action not in ['read', 'view', 'download', 'manage', '*']:
                    continue
            else:
                if policy.action not in [action, 'manage', '*']:
                    continue
                    
            try:
                if safe_eval_condition(policy.subject_condition, eval_context):
                    if policy.effect == 'allow':
                        allowed_policy_ids.append(policy.id)
            except Exception as e:
                logger.error(f"[ABAC] Failed to evaluate policy {policy.id} condition: {e}")
                continue
                
        # Cache for 30 seconds
        cache.set(cache_key, allowed_policy_ids, timeout=30)
        return allowed_policy_ids


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
                if policy.action not in ['download', 'manage', '*']:
                    continue
            elif action in ['read', 'view']:
                if policy.action not in ['read', 'view', 'download', 'manage', '*']:
                    continue
            else:
                if policy.action not in [action, 'manage', '*']:
                    continue
            
            # Evaluate the subject condition
            try:
                eval_context = {
                    'r': type('Request', (), {'sub': r_sub})(),
                }
                
                result = safe_eval_condition(policy.subject_condition, eval_context)
                
                if result:
                    if policy.effect == 'allow':
                        return True, f"file_policy_allowed:{policy.name}"
                    else:
                        return False, f"file_policy_denied:{policy.name}"
                        
            except Exception as e:
                logger.error(f"Error evaluating policy {policy.name}: {e}")
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
        Combined check: File-specific policies + general ABAC
        
        Flow:
        1. First check general ABAC permission
        2. Then check file-specific policies (if any)
        """
        # Step 1: General ABAC check
        abac_allowed = self.check_access(user, 'document', action)
        if not abac_allowed:
            return False, "general_abac_denied"
        
        # Step 2: Check file-specific policies
        file_access, file_reason = self.check_file_access(user, bucket_name, file_path, action)
        
        return file_access, file_reason


# Singleton instance
casbin_service = CasbinService()
