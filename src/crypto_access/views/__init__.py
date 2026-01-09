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

# Import attribute management views
from .attributes import (
    UserTypeViewSet,
    AttributeDefinitionViewSet,
    user_types_page,
    attributes_page,
    user_attributes_page,
    list_user_attributes,
    assign_user_attribute,
    bulk_assign_user_attributes,
    delete_user_attribute,
    list_users_with_attributes,
)

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
    
    # Attribute management views
    'UserTypeViewSet',
    'AttributeDefinitionViewSet',
    'user_types_page',
    'attributes_page',
    'user_attributes_page',
    'list_user_attributes',
    'assign_user_attribute',
    'bulk_assign_user_attributes',
    'delete_user_attribute',
    'list_users_with_attributes',
]

