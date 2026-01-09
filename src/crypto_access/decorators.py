"""
ABAC Decorators for Django views (Policy Enforcement Point - PEP)
Use these decorators to protect views with ABAC policies
"""

from functools import wraps
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework import status


def require_permission(resource: str, action: str):
    """
    Decorator to require ABAC permission for a view
    
    Usage:
        @require_permission('document', 'read')
        def view_document(request, doc_id):
            ...
        
        # For DRF views:
        @require_permission('key', 'manage')
        @api_view(['POST'])
        def create_key(request):
            ...
    
    Args:
        resource: Resource name (e.g., 'document', 'key', 'user')
        action: Action name (e.g., 'read', 'write', 'delete')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Import here to avoid circular imports
            from crypto_access.services.casbin_service import casbin_service
            
            # Check if user is authenticated
            if not request.user.is_authenticated:
                return JsonResponse(
                    {'error': 'Authentication required'},
                    status=401
                )
            
            # Check ABAC permission
            if not casbin_service.check_access(request.user, resource, action):
                return JsonResponse(
                    {
                        'error': 'Access denied',
                        'detail': f'You do not have permission to {action} {resource}',
                        'resource': resource,
                        'action': action
                    },
                    status=403
                )
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_any_permission(permissions: list):
    """
    Decorator to require any one of multiple permissions
    
    Usage:
        @require_any_permission([
            ('document', 'read'),
            ('document', 'manage')
        ])
        def view_document(request):
            ...
    
    Args:
        permissions: List of (resource, action) tuples
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from crypto_access.services.casbin_service import casbin_service
            
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'Authentication required'}, status=401)
            
            # Check if any permission is granted
            for resource, action in permissions:
                if casbin_service.check_access(request.user, resource, action):
                    return view_func(request, *args, **kwargs)
            
            return JsonResponse(
                {
                    'error': 'Access denied',
                    'detail': 'You do not have any of the required permissions'
                },
                status=403
            )
        return wrapper
    return decorator


def require_all_permissions(permissions: list):
    """
    Decorator to require all of multiple permissions
    
    Usage:
        @require_all_permissions([
            ('document', 'read'),
            ('key', 'decrypt')
        ])
        def decrypt_document(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from crypto_access.services.casbin_service import casbin_service
            
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'Authentication required'}, status=401)
            
            # Check if all permissions are granted
            for resource, action in permissions:
                if not casbin_service.check_access(request.user, resource, action):
                    return JsonResponse(
                        {
                            'error': 'Access denied',
                            'detail': f'Missing permission: {action} on {resource}'
                        },
                        status=403
                    )
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


class ABACPermissionMixin:
    """
    Mixin for DRF ViewSets/Views to add ABAC permission checking
    
    Usage:
        class DocumentViewSet(ABACPermissionMixin, ModelViewSet):
            abac_resource = 'document'
            abac_action_map = {
                'list': 'read',
                'retrieve': 'read',
                'create': 'write',
                'update': 'update',
                'destroy': 'delete',
            }
    """
    abac_resource = None
    abac_action_map = {
        'list': 'read',
        'retrieve': 'read',
        'create': 'write',
        'update': 'update',
        'partial_update': 'update',
        'destroy': 'delete',
    }
    
    def check_abac_permission(self, request, action=None):
        """Check ABAC permission for current action"""
        from crypto_access.services.casbin_service import casbin_service
        
        if not self.abac_resource:
            return True
        
        action = action or self.abac_action_map.get(self.action, self.action)
        return casbin_service.check_access(request.user, self.abac_resource, action)
    
    def permission_denied(self, request, message=None, code=None):
        """Override to provide ABAC-specific error message"""
        raise PermissionDenied(
            detail=message or f'ABAC: Access denied to {self.abac_resource}',
            code=code or 'abac_denied'
        )
    
    def initial(self, request, *args, **kwargs):
        """Called before dispatch, check ABAC permission here"""
        super().initial(request, *args, **kwargs)
        
        if request.user.is_authenticated and self.abac_resource:
            if not self.check_abac_permission(request):
                action = self.abac_action_map.get(self.action, self.action)
                self.permission_denied(
                    request,
                    message=f'You do not have permission to {action} {self.abac_resource}'
                )
