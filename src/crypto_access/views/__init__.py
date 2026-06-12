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

# Import policy management views
from .policy import (
    AccessPolicyViewSet,
    policies_page,
)

# Import user management views
from .users import (
    UserManagementViewSet,
    users_page,
)

# Import audit views
from .audit import (
    AccessLogViewSet,
    KeyRevocationViewSet,
    audit_logs_page,
    key_revocations_page,
)

from .errors import (
    custom_400,
    custom_403,
    custom_404,
    custom_500,
)

# Import session views
from .session_views import (
    SessionViewSet,
    sessions_page,
)

__all__ = [
    # Base views
    'index',
    'health_check',
    'api_health',
    
    # Error views
    'custom_400',
    'custom_403',
    'custom_404',
    'custom_500',
    
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
    
    # Policy management views
    'AccessPolicyViewSet',
    'policies_page',
    
    # User management views
    'UserManagementViewSet',
    'users_page',
    
    # Audit views
    'AccessLogViewSet',
    'KeyRevocationViewSet',
    'audit_logs_page',
    'key_revocations_page',
    
    # Session views
    'SessionViewSet',
    'sessions_page',
]

