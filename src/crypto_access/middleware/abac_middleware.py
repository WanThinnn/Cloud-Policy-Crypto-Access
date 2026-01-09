"""
ABAC Middleware for Django (Policy Enforcement Point - PEP)
Provides route-based ABAC protection
"""

import re
import logging
from django.http import JsonResponse
from django.conf import settings

logger = logging.getLogger(__name__)


class ABACMiddleware:
    """
    Middleware to automatically enforce ABAC policies on configured routes
    
    Configure in settings.py:
        ABAC_PROTECTED_ROUTES = [
            {
                'pattern': r'^/api/documents/',
                'resource': 'document',
                'methods': {
                    'GET': 'read',
                    'POST': 'write',
                    'PUT': 'update',
                    'DELETE': 'delete',
                }
            },
            {
                'pattern': r'^/api/keys/',
                'resource': 'key',
                'methods': {
                    'GET': 'read',
                    'POST': 'manage',
                }
            },
        ]
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.protected_routes = getattr(settings, 'ABAC_PROTECTED_ROUTES', [])
        
        # Compile regex patterns
        for route in self.protected_routes:
            route['_compiled'] = re.compile(route['pattern'])
    
    def __call__(self, request):
        # Debug: Log every request
        logger.info(f"[ABAC] Processing {request.method} {request.path}")
        
        # Check if request matches any protected route
        for route in self.protected_routes:
            if route['_compiled'].match(request.path):
                logger.warning(f"[ABAC-MATCH] Protected route matched - {request.path}")
                
                # Check if user is authenticated
                if not request.user.is_authenticated:
                    logger.error(f"[ABAC-DENY] Unauthenticated access attempt to {request.path}")
                    return JsonResponse(
                        {'error': 'Authentication required'},
                        status=401
                    )
                
                # Get required action for this method
                method = request.method
                if method not in route.get('methods', {}):
                    # Method not configured, allow by default
                    logger.info(f"[ABAC-ALLOW] Method {method} not configured for {request.path}, allowing")
                    continue
                
                action = route['methods'][method]
                resource = route['resource']
                
                logger.warning(f"[ABAC-CHECK] Checking {request.user.username} - resource:{resource} action:{action}")
                
                # Import here to avoid circular imports
                from crypto_access.services.casbin_service import casbin_service
                
                # Check ABAC permission
                if not casbin_service.check_access(request.user, resource, action):
                    logger.error(f"[ABAC-DENY] Access DENIED - user:{request.user.username} resource:{resource} action:{action}")
                    return JsonResponse(
                        {
                            'error': 'Access denied by ABAC policy',
                            'resource': resource,
                            'action': action,
                            'path': request.path,
                            'user': request.user.username
                        },
                        status=403
                    )
                
                logger.warning(f"[ABAC-ALLOW] Access ALLOWED - user:{request.user.username} resource:{resource} action:{action}")
        
        # Continue with request
        logger.info(f"[ABAC-PASS] Request passed - {request.path}")
        response = self.get_response(request)
        return response


class ABACContextMiddleware:
    """
    Middleware to inject ABAC context into request for use in views
    
    Usage in views:
        def my_view(request):
            # Access user's ABAC attributes
            attrs = request.abac_attributes
            
            # Check permission
            can_read = request.abac_check('document', 'read')
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Add ABAC helper methods to request
        if request.user.is_authenticated:
            from crypto_access.services.casbin_service import casbin_service
            
            # Lazy-loaded attributes
            request._abac_attributes = None
            
            def get_abac_attributes():
                if request._abac_attributes is None:
                    request._abac_attributes = casbin_service.get_user_attributes(request.user)
                return request._abac_attributes
            
            def abac_check(resource, action):
                return casbin_service.check_access(request.user, resource, action)
            
            request.abac_attributes = property(lambda self: get_abac_attributes())
            request.abac_check = abac_check
        
        response = self.get_response(request)
        return response
