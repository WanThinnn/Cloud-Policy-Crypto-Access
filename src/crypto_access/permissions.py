"""
Custom permissions for crypto_access app
"""

from rest_framework import permissions


class IsSuperAdmin(permissions.BasePermission):
    """
    Permission class that only allows Super Admins to access
    """
    message = "Only Super Admin can perform this action."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user has profile and is super_admin
        if hasattr(request.user, 'profile'):
            return request.user.profile.is_super_admin()
        return False


class IsAdminOrSuperAdmin(permissions.BasePermission):
    """
    Permission class that allows Admin or Super Admin to access
    """
    message = "Only Admin or Super Admin can perform this action."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if hasattr(request.user, 'profile'):
            return request.user.profile.is_admin()
        return False


class IsDataOwnerOrAdmin(permissions.BasePermission):
    """
    Permission class that allows Data Owner, Admin or Super Admin
    """
    message = "Only Data Owner or Admin can perform this action."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if hasattr(request.user, 'profile'):
            user_type = request.user.profile.get_user_type_code()
            return user_type in ['super_admin', 'admin', 'data_contributor']
        return False


class CanManageAttributes(permissions.BasePermission):
    """
    Permission for managing user attributes
    Super Admin: can manage all users' attributes
    Admin: can manage attributes within their department
    """
    message = "You don't have permission to manage user attributes."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if hasattr(request.user, 'profile'):
            return request.user.profile.is_admin()
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check if user can manage specific user's attributes"""
        if not hasattr(request.user, 'profile'):
            return False
        
        profile = request.user.profile
        
        # Super Admin can manage anyone
        if profile.is_super_admin():
            return True
        
        # Admin can manage users in same department (when ABAC is implemented)
        if profile.is_admin():
            # For now, allow admin to manage non-admin users
            target_user = obj.user if hasattr(obj, 'user') else obj
            if hasattr(target_user, 'profile'):
                return not target_user.profile.is_admin()
        
        return False
