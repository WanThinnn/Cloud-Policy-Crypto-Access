"""
Base models for crypto_access app.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist


class BaseModel(models.Model):
    """Base model with common fields"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserProfile(BaseModel):
    """
    Extended user profile (BM1)
    References user_attributes (BM4) for ABAC attributes
    """
    
    # Legacy choices - kept for backward compatibility during migration
    USER_TYPE_CHOICES = [
        ('super_admin', 'Super Admin'),
        ('admin', 'Admin'),
        ('data_owner', 'Data Owner'),
        ('data_user', 'Data User'),
        ('auditor', 'Auditor'),
        ('guest', 'Guest'),
    ]
    
    ACCOUNT_STATUS_CHOICES = [
        ('pending', 'Pending Activation'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
        ('expired', 'Expired'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # BM1 fields
    full_name = models.CharField(max_length=255, default='', verbose_name="Full Name")
    
    # New: ForeignKey to UserType model (flexible, configurable)
    user_type_ref = models.ForeignKey(
        'UserType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name="User Type"
    )
    
    # Legacy field - kept for backward compatibility
    user_type = models.CharField(
        max_length=20, 
        choices=USER_TYPE_CHOICES, 
        default='data_user',
        verbose_name="User Type (legacy)"
    )
    
    account_status = models.CharField(
        max_length=20,
        choices=ACCOUNT_STATUS_CHOICES,
        default='active',  # Temporarily active, later will be changed to pending
        verbose_name="Account Status"
    )
    account_expiry_date = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Account Expiry Date"
    )
    
    # Contact info
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    
    # Reference to user_attributes (BM4)
    # Will be implemented separately
    attribute_doc_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Reference to user_attributes collection (BM4)"
    )
    
    # Activation
    is_email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=255, blank=True, null=True)
    
    # Password reset
    password_reset_token = models.CharField(max_length=255, blank=True, null=True)
    password_reset_expires = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.full_name} ({self.user.username})"
    
    def get_user_type_code(self):
        """Get user type code (from new model or legacy field)"""
        if self.user_type_ref:
            return self.user_type_ref.code
        return self.user_type
    
    def is_admin(self):
        return self.get_user_type_code() in ['super_admin', 'admin']
    
    def is_super_admin(self):
        return self.get_user_type_code() == 'super_admin'
    
    def can_manage_users(self):
        """Check if user can manage other users"""
        return self.get_user_type_code() in ['super_admin', 'admin']
    
    def has_permission(self, permission):
        """Check if user has a specific permission via UserType"""
        if self.user_type_ref:
            return self.user_type_ref.has_permission(permission)
        # Fallback for legacy: super_admin has all permissions
        if self.user_type == 'super_admin':
            return True
        return False
    
    def get_abac_attributes(self):
        """Get all ABAC attributes for this user"""
        from .attributes import UserAttribute
        return UserAttribute.get_user_attributes(self.user)
    
    def is_account_active(self):
        """Check if account is active and not expired"""
        if self.account_status != 'active':
            return False
        if self.account_expiry_date and self.account_expiry_date < timezone.now():
            return False
        return True

    class Meta:
        db_table = 'crypto_user_profiles'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
