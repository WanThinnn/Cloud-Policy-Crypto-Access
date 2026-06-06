"""
JWT Authentication Middleware
Processes JWT tokens from Authorization header before other middleware
"""

import logging
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed

logger = logging.getLogger(__name__)


class JWTAuthenticationMiddleware:
    """
    Middleware to authenticate JWT tokens from Authorization header
    Should be placed after AuthenticationMiddleware and before ABACMiddleware
    
    This middleware extracts JWT tokens and authenticates users for
    non-view contexts (like middleware) where DRF authentication doesn't run.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_authenticator = JWTAuthentication()
    
    def __call__(self, request):
        # Only process if Authorization header is present and user is not already authenticated
        if not request.user.is_authenticated:
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            raw_token = None
            
            if auth_header.startswith('Bearer '):
                raw_token = auth_header.split(' ')[1]
            elif 'access_token' in request.COOKIES:
                raw_token = request.COOKIES['access_token']
                
            if raw_token:
                try:
                    # Try to authenticate using JWT
                    validated_token = self.jwt_authenticator.get_validated_token(raw_token)
                    user = self.jwt_authenticator.get_user(validated_token)
                    
                    if user:
                        request.user = user
                        logger.debug(f"[JWT-AUTH] Authenticated user: {user.username}")
                    
                except (InvalidToken, AuthenticationFailed) as e:
                    logger.warning(f"[JWT-AUTH] Token validation failed: {str(e)}")
                    # Leave user as AnonymousUser
                    
                except Exception as e:
                    logger.error(f"[JWT-AUTH] Unexpected error: {str(e)}")
        
        response = self.get_response(request)
        return response
