"""
ABAC Middleware for Django (Policy Enforcement Point - PEP)
Provides route-based ABAC protection with Access Logging (BM12)
"""

import re
import logging
from django.http import JsonResponse
from django.conf import settings

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Extract client IP from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def get_environment_attributes(request):
    """Extract environment attributes from request for logging"""
    from django.utils import timezone
    
    return {
        'ip': get_client_ip(request),
        'user_agent': request.META.get('HTTP_USER_AGENT', 'unknown')[:200],
        'time': timezone.now().isoformat(),
        'method': request.method,
        'path': request.path,
    }


class ABACMiddleware:
    """
    Middleware to automatically enforce ABAC policies on configured routes
    Now with Access Logging (BM12) support
    
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
        self.enable_access_logging = getattr(settings, 'ABAC_ENABLE_ACCESS_LOGGING', True)
        
        # Compile regex patterns
        for route in self.protected_routes:
            route['_compiled'] = re.compile(route['pattern'])
    
    def _log_access(self, request, resource, action, result, 
                    user_attributes=None, policies_matched=None, error_message=None):
        """Log access attempt to database (BM12)"""
        if not self.enable_access_logging:
            return
        
        try:
            from crypto_access.models import AccessLog
            
            AccessLog.log_access(
                user=request.user if request.user.is_authenticated else None,
                resource_type=resource,
                action=action,
                result=result,
                resource_id=request.path,
                policies_matched=policies_matched or [],
                user_attributes=user_attributes or {},
                environment_attributes=get_environment_attributes(request),
                request_path=request.path,
                request_method=request.method,
                error_message=error_message
            )
        except Exception as e:
            logger.error(f"[ABAC-LOG] Failed to log access: {e}")
    
    def _check_file_ownership(self, request, action):
        """
        Check if user is the owner of the file being accessed OR has explicit access grant.
        Owner can always access their own files (download, delete).
        Users in granted_users list of FileAccessPolicy also bypass ABAC.
        
        Returns True if user is owner or has explicit grant, False otherwise.
        """
        if action not in ['download', 'delete', 'read']:
            return False
        
        # Get file path from query params
        file_path = request.GET.get('path', '')
        bucket_name = request.GET.get('bucket', 'documents')
        
        if not file_path:
            return False
        
        try:
            from crypto_access.models import UploadedFile, FileAccessPolicy
            
            uploaded_file = UploadedFile.objects.filter(
                bucket__name=bucket_name,
                file_path=file_path
            ).first()
            
            # Check 1: User is the owner
            if uploaded_file and uploaded_file.uploaded_by == request.user:
                logger.info(f"[ABAC-OWNER] User {request.user.username} is owner of {file_path}")
                return True
            
            # Check 2: User has explicit access grant via FileAccessPolicy
            if FileAccessPolicy.check_user_has_access(request.user, bucket_name, file_path):
                logger.info(f"[ABAC-GRANT] User {request.user.username} has explicit access to {file_path}")
                return True
                
        except Exception as e:
            logger.error(f"[ABAC-OWNER] Error checking ownership/grant: {e}")
        
        return False
    
    def __call__(self, request):
        # Debug: Log every request
        logger.info(f"[ABAC] Processing {request.method} {request.path}")
        
        # Check if request matches any protected route
        for route in self.protected_routes:
            if route['_compiled'].match(request.path):
                logger.warning(f"[ABAC-MATCH] Protected route matched - {request.path}")
                
                resource = route['resource']
                method = request.method
                action = route.get('methods', {}).get(method)
                
                # Check if user is authenticated
                if not request.user.is_authenticated:
                    logger.error(f"[ABAC-DENY] Unauthenticated access attempt to {request.path}")
                    
                    # Log denied access
                    self._log_access(
                        request=request,
                        resource=resource,
                        action=action or 'unknown',
                        result='deny',
                        error_message='Authentication required'
                    )
                    
                    return JsonResponse(
                        {'error': 'Authentication required'},
                        status=401
                    )
                
                # Get required action for this method
                if not action:
                    # Method not configured, allow by default
                    logger.info(f"[ABAC-ALLOW] Method {method} not configured for {request.path}, allowing")
                    continue
                
                logger.warning(f"[ABAC-CHECK] Checking {request.user.username} - resource:{resource} action:{action}")
                
                # Import here to avoid circular imports
                from crypto_access.services.casbin_service import casbin_service
                
                # Get user attributes for logging
                user_attributes = casbin_service.get_user_attributes(request.user)
                
                # Check if user is owner of the file (owners can always access their own files)
                is_owner = self._check_file_ownership(request, action)
                
                # For file download/read actions, check file-specific policies
                access_allowed = False
                access_reason = ''
                
                if is_owner:
                    access_allowed = True
                    access_reason = 'owner_bypass'
                elif action in ['download', 'read'] and request.GET.get('path'):
                    # Check file-specific policy
                    file_path = request.GET.get('path', '')
                    bucket_name = request.GET.get('bucket', 'documents')
                    
                    file_allowed, file_reason = casbin_service.check_file_access_with_fallback(
                        request.user, bucket_name, file_path, action
                    )
                    access_allowed = file_allowed
                    access_reason = file_reason
                    logger.info(f"[ABAC-FILE] File policy check: {file_path} -> {file_allowed} ({file_reason})")
                else:
                    # Use general ABAC check for non-file actions
                    access_allowed = casbin_service.check_access(request.user, resource, action)
                    access_reason = 'abac_allowed' if access_allowed else 'abac_denied'
                
                if not access_allowed:
                    logger.error(f"[ABAC-DENY] Access DENIED ({access_reason}) - user:{request.user.username} resource:{resource} action:{action}")
                    
                    # Log denied access
                    self._log_access(
                        request=request,
                        resource=resource,
                        action=action,
                        result='deny',
                        user_attributes=user_attributes,
                        error_message=f'Access denied: {access_reason}'
                    )
                    
                    return JsonResponse(
                        {
                            'error': 'You do not have permission to perform this action.',
                        },
                        status=403
                    )
                
                logger.warning(f"[ABAC-ALLOW] Access ALLOWED ({access_reason}) - user:{request.user.username} resource:{resource} action:{action}")
                
                # Log allowed access with reason
                self._log_access(
                    request=request,
                    resource=resource,
                    action=action,
                    result='allow',
                    user_attributes=user_attributes,
                    error_message=f'Allowed via {access_reason}'
                )
        
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
