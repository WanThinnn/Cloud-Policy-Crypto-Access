"""
ABAC Attribute Models
- UserType: Configurable user types (replacing hard-coded choices)
- AttributeDefinition: Attribute schema (BM9)
- UserAttribute: User's ABAC attributes (BM4)
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from .base import BaseModel


class UserType(BaseModel):
    """
    Configurable user types (QĐ1)
    Replaces hard-coded USER_TYPE_CHOICES for flexibility
    """
    code = models.CharField(
        max_length=30, 
        unique=True,
        help_text="Unique code (e.g., 'super_admin', 'data_owner')"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name (e.g., 'Super Admin')"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of this user type"
    )

    is_system = models.BooleanField(
        default=False,
        help_text="System types cannot be deleted"
    )
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    

    class Meta:
        db_table = 'crypto_user_types'
        verbose_name = 'User Type'
        verbose_name_plural = 'User Types'
        ordering = ['name']


class AttributeDefinition(BaseModel):
    """
    Attribute schema definition (BM9)
    Defines valid attributes that can be assigned to users
    """
    DATA_TYPE_CHOICES = [
        ('enum', 'Enumeration'),
        ('string', 'String'),
        ('integer', 'Integer'),
        ('boolean', 'Boolean'),
        ('date', 'Date'),
    ]
    
    name = models.CharField(
        max_length=50, 
        unique=True,
        help_text="Attribute name (e.g., 'department', 'role')"
    )
    display_name = models.CharField(
        max_length=100,
        help_text="Display name for UI"
    )
    data_type = models.CharField(
        max_length=20,
        choices=DATA_TYPE_CHOICES,
        default='string'
    )
    allowed_values = models.JSONField(
        null=True,
        blank=True,
        help_text="List of allowed values for enum type"
    )
    default_value = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Default value for this attribute"
    )
    is_required = models.BooleanField(
        default=True,
        help_text="Whether this attribute is required for all users"
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    # Schema versioning
    version = models.IntegerField(default=1)
    
    def __str__(self):
        return f"{self.display_name} ({self.name})"
    
    def validate_value(self, value):
        """Validate if a value is valid for this attribute"""
        if self.data_type == 'enum':
            if self.allowed_values and value not in self.allowed_values:
                return False, f"Value must be one of: {', '.join(self.allowed_values)}"
        elif self.data_type == 'integer':
            try:
                int(value)
            except (ValueError, TypeError):
                return False, "Value must be an integer"
        elif self.data_type == 'boolean':
            if value not in ['true', 'false', True, False, '1', '0']:
                return False, "Value must be a boolean"
        return True, None
    
    class Meta:
        db_table = 'crypto_attribute_definitions'
        verbose_name = 'Attribute Definition'
        verbose_name_plural = 'Attribute Definitions'
        ordering = ['name']


class UserAttribute(BaseModel):
    """
    User's ABAC attributes (BM4)
    Single source of truth for ABAC and CP-ABE
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('pending', 'Pending Approval'),
        ('expired', 'Expired'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='abac_attributes'
    )
    attribute = models.ForeignKey(
        AttributeDefinition,
        on_delete=models.PROTECT,
        related_name='user_values'
    )
    value = models.CharField(
        max_length=255,
        help_text="Attribute value"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    effective_date = models.DateTimeField(
        default=timezone.now,
        help_text="Date when this attribute becomes effective"
    )
    expiry_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date when this attribute expires (null = never)"
    )
    
    # Versioning for audit trail
    version = models.IntegerField(default=1)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='attribute_updates',
        help_text="Admin who last updated this attribute"
    )
    
    def __str__(self):
        return f"{self.user.username}: {self.attribute.name}={self.value}"
    
    def is_active_now(self):
        """Check if this attribute is currently active"""
        if self.status != 'active':
            return False
        now = timezone.now()
        if self.effective_date > now:
            return False
        if self.expiry_date and self.expiry_date < now:
            return False
        return True
    
    @classmethod
    def get_user_attributes(cls, user):
        """Get all active attributes for a user as a dict"""
        attrs = cls.objects.filter(
            user=user,
            status='active',
            effective_date__lte=timezone.now()
        ).filter(
            models.Q(expiry_date__isnull=True) | models.Q(expiry_date__gt=timezone.now())
        ).select_related('attribute')
        
        return {attr.attribute.name: attr.value for attr in attrs}
    
    @classmethod
    def set_user_attribute(cls, user, attribute_name, value, updated_by=None):
        """Set or update a user attribute"""
        try:
            attr_def = AttributeDefinition.objects.get(name=attribute_name, is_active=True)
        except AttributeDefinition.DoesNotExist:
            raise ValueError(f"Attribute '{attribute_name}' does not exist")
        
        # Validate value
        is_valid, error = attr_def.validate_value(value)
        if not is_valid:
            raise ValueError(error)
        
        # Get or create attribute
        user_attr, created = cls.objects.get_or_create(
            user=user,
            attribute=attr_def,
            defaults={
                'value': value,
                'updated_by': updated_by,
            }
        )
        
        if not created:
            user_attr.value = value
            user_attr.version += 1
            user_attr.updated_by = updated_by
            user_attr.save()
        
        return user_attr
    
    class Meta:
        db_table = 'crypto_user_attributes'
        verbose_name = 'User Attribute'
        verbose_name_plural = 'User Attributes'
        unique_together = ['user', 'attribute']
        ordering = ['user', 'attribute__name']
