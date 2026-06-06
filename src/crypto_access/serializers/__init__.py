"""
Serializers package for crypto_access app
"""

# Base serializers
from .base import UserSerializer, UserProfileSerializer

# Auth serializers
from .auth import (
    RegisterSerializer,
    LoginSerializer,
    ChangePasswordSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    UserDetailSerializer,
)

# Storage serializers
from .storage import (
    StorageBucketSerializer,
    UploadedFileSerializer,
    FileUploadSerializer,
    SignedUrlRequestSerializer,
)

# ABAC Attribute serializers
from .attributes import (
    UserTypeSerializer,
    AttributeDefinitionSerializer,
    UserAttributeSerializer,
    UserAttributeAssignSerializer,
    UserAttributeBulkAssignSerializer,
    UserWithAttributesSerializer,
)

# ABAC Policy serializers
from .policy import (
    AccessPolicySerializer,
    AccessPolicyListSerializer,
)

# User Management serializers
from .users import (
    UserManagementSerializer,
    UserCreateSerializer,
    UserProfileInlineSerializer,
)

# Audit serializers
from .audit import (
    AccessLogSerializer,
    KeyRevocationSerializer,
)

__all__ = [
    # Base
    'UserSerializer',
    'UserProfileSerializer',
    
    # Auth
    'RegisterSerializer',
    'LoginSerializer',
    'ChangePasswordSerializer',
    'PasswordResetRequestSerializer',
    'PasswordResetConfirmSerializer',
    'UserDetailSerializer',
    
    # Storage
    'StorageBucketSerializer',
    'UploadedFileSerializer',
    'FileUploadSerializer',
    'SignedUrlRequestSerializer',
    
    # ABAC Attributes
    'UserTypeSerializer',
    'AttributeDefinitionSerializer',
    'UserAttributeSerializer',
    'UserAttributeAssignSerializer',
    'UserAttributeBulkAssignSerializer',
    'UserWithAttributesSerializer',
    
    # ABAC Policies
    'AccessPolicySerializer',
    'AccessPolicyListSerializer',
    
    # User Management
    'UserManagementSerializer',
    'UserCreateSerializer',
    'UserProfileInlineSerializer',
    
    # Audit
    'AccessLogSerializer',
    'KeyRevocationSerializer',
]

