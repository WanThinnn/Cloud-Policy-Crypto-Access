"""
AccessPolicy Model (BM7)
Stores ABAC policy rules in database for PyCasbin
"""

from django.db import models
from django.contrib.auth.models import User
from .base import BaseModel


class AccessPolicy(BaseModel):
    """
    Access Policy for ABAC (BM7)
    Defines who can access what resources under which conditions
    """
    EFFECT_CHOICES = [
        ('allow', 'Allow'),
        ('deny', 'Deny'),
    ]
    
    RESOURCE_CHOICES = [
        ('document', 'Document'),
        ('key', 'Encryption Key'),
        ('user', 'User Management'),
        ('policy', 'Policy Management'),
        ('attribute', 'Attribute Management'),
        ('audit', 'Audit Logs'),
        ('*', 'All Resources'),
    ]
    
    ACTION_CHOICES = [
        ('read', 'Read'),
        ('write', 'Write/Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('upload', 'Upload'),
        ('download', 'Download'),
        ('encrypt', 'Encrypt'),
        ('decrypt', 'Decrypt'),
        ('manage', 'Full Management'),
        ('*', 'All Actions'),
    ]
    
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Policy name for identification"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of what this policy does"
    )
    
    # Subject condition (ABAC expression)
    # Examples:
    # - "r.sub.user_type == 'admin'"
    # - "r.sub.department == 'it' && r.sub.clearance_level >= 'secret'"
    # - "r.sub.role in ['manager', 'director']"
    subject_condition = models.TextField(
        help_text="ABAC condition expression using r.sub attributes. Example: r.sub.department == 'it'"
    )
    
    cpabe_policy = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Equivalent CP-ABE policy string. Example: (department:it and clearance_level:secret)"
    )
    
    # Resource and Action
    resource = models.CharField(
        max_length=50,
        choices=RESOURCE_CHOICES,
        help_text="Resource this policy applies to"
    )
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        help_text="Action this policy permits/denies"
    )
    
    # Effect
    effect = models.CharField(
        max_length=10,
        choices=EFFECT_CHOICES,
        default='allow',
        help_text="Whether to allow or deny this access"
    )
    
    # Priority (lower = higher priority)
    priority = models.IntegerField(
        default=100,
        help_text="Policy priority (lower number = higher priority)"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this policy is active"
    )
    
    # Audit fields
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_policies',
        help_text="Admin who created this policy"
    )
    
    def __str__(self):
        return f"{self.name}: {self.subject_condition} -> {self.resource}/{self.action} ({self.effect})"
    
    def to_casbin_policy(self):
        """Convert to Casbin policy format: [sub_rule, obj, act, eft]"""
        return [self.subject_condition, self.resource, self.action, self.effect]
    
    class Meta:
        db_table = 'crypto_access_policies'
        verbose_name = 'Access Policy'
        verbose_name_plural = 'Access Policies'
        ordering = ['priority', 'name']
