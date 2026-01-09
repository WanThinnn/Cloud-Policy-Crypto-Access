"""
Views package for crypto_access app
Organized by functionality
"""

# Import base views
from .base import index, health_check, api_health

# Import auth views
from .auth import (
    login_page,
    register_page,
    register,
    login,
    logout,
    change_password,
    password_reset_request,
    password_reset_confirm,
    user_profile,
)

# Import storage views
from .storage import StorageBucketViewSet, UploadedFileViewSet

__all__ = [
    # Base views
    'index',
    'health_check',
    'api_health',
    
    # Auth views
    'login_page',
    'register_page',
    'register',
    'login',
    'logout',
    'change_password',
    'password_reset_request',
    'password_reset_confirm',
    'user_profile',
    
    # Storage views
    'StorageBucketViewSet',
    'UploadedFileViewSet',
]
