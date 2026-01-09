"""
PyCasbin Service for ABAC (Policy Decision Point - PDP)
Integrates Casbin with Django models for attribute-based access control
"""

import casbin
import os
from django.conf import settings
from typing import Dict, Any, Optional
from crypto_access.models import UserAttribute, AccessPolicy, UserType


class CasbinService:
    """
    Policy Decision Point (PDP) using PyCasbin
    Handles all authorization decisions based on ABAC policies
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
            
            # Add user type permissions
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
    
    def check_access(self, user, resource: str, action: str) -> bool:
        """
        Check if a user has access to perform an action on a resource
        
        Args:
            user: Django User object
            resource: Resource name (e.g., 'document', 'key')
            action: Action name (e.g., 'read', 'write', 'delete')
        
        Returns:
            bool: True if access is allowed, False otherwise
        """
        # Super admins have full access
        if user.is_superuser:
            return True
        
        # Get user attributes
        attrs = self.get_user_attributes(user)
        
        # Create a simple namespace for eval()
        class AttrNamespace:
            def __init__(self, attributes):
                for k, v in attributes.items():
                    setattr(self, k, v)
            
            def __getattr__(self, name):
                # Return None for missing attributes instead of raising error
                return None
        
        # Create request subject with attributes
        sub = AttrNamespace(attrs)
        
        try:
            # Check with Casbin enforcer
            return self._enforcer.enforce(sub, resource, action)
        except Exception as e:
            # Log error and deny access on failure (fail-safe)
            print(f"ABAC check error: {e}")
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
        
        Args:
            user: Django User object
            resource: Resource name
            action: Action name
            resource_attrs: Additional resource attributes (e.g., document owner)
        """
        # For now, delegate to basic check
        # Can be extended to include resource attributes in condition
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
        allowed = self.check_access(user, resource, action)
        
        # Find matching policies
        matching_policies = AccessPolicy.objects.filter(
            is_active=True,
            resource__in=[resource, '*'],
            action__in=[action, '*']
        ).order_by('priority')
        
        return {
            'allowed': allowed,
            'user': user.username,
            'resource': resource,
            'action': action,
            'user_attributes': attrs,
            'matching_policies': [
                {
                    'name': p.name,
                    'condition': p.subject_condition,
                    'effect': p.effect,
                    'priority': p.priority
                }
                for p in matching_policies
            ]
        }


# Singleton instance
casbin_service = CasbinService()
