"""
Base models for crypto_access app.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


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
    full_name = models.CharField(max_length=255, default='', verbose_name="Họ và tên")
    user_type = models.CharField(
        max_length=20, 
        choices=USER_TYPE_CHOICES, 
        default='data_user',
        verbose_name="Loại người dùng"
    )
    account_status = models.CharField(
        max_length=20,
        choices=ACCOUNT_STATUS_CHOICES,
        default='active',  # Tạm thời active, sau này sẽ đổi thành pending
        verbose_name="Trạng thái tài khoản"
    )
    account_expiry_date = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Ngày hết hạn tài khoản"
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
    
    def is_admin(self):
        return self.user_type in ['super_admin', 'admin']
    
    def is_super_admin(self):
        return self.user_type == 'super_admin'
    
    def can_manage_users(self):
        """Check if user can manage other users"""
        return self.user_type in ['super_admin', 'admin']
    
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
