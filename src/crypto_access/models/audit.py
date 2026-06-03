"""
Audit Models for ABAC System
- AccessLog (BM12): Nhật ký truy cập
- KeyRevocation (BM13): Danh sách thu hồi khóa
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from .base import BaseModel


class AccessLog(BaseModel):
    """
    Access Log Model (BM12)
    Records all access requests for audit and compliance
    
    QĐ12: Mọi yêu cầu truy cập (bao gồm cả thành công và thất bại) 
    đều phải được ghi lại trong hệ thống nhật ký.
    """
    
    RESULT_CHOICES = [
        ('allow', 'Allowed'),
        ('deny', 'Denied'),
        ('error', 'Error'),
    ]
    
    # Log identification
    log_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique log ID (e.g., log_20250908_143052_001)"
    )
    
    # Request info
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='access_logs',
        help_text="User who made the request"
    )
    
    # Resource and action
    resource_type = models.CharField(
        max_length=50,
        help_text="Type of resource (document, key, user, etc.)"
    )
    resource_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="ID of the specific resource"
    )
    action = models.CharField(
        max_length=50,
        help_text="Action attempted (read, write, download, etc.)"
    )
    
    # PDP decision
    result = models.CharField(
        max_length=20,
        choices=RESULT_CHOICES,
        help_text="Result of access decision"
    )
    
    # Policies applied
    policies_evaluated = models.JSONField(
        default=list,
        help_text="List of policy names that were evaluated"
    )
    policies_matched = models.JSONField(
        default=list,
        help_text="List of policies that matched the request"
    )
    
    # User attributes at time of request (snapshot)
    user_attributes = models.JSONField(
        default=dict,
        help_text="User's ABAC attributes at time of access"
    )
    
    # Environment attributes
    environment_attributes = models.JSONField(
        default=dict,
        help_text="Environment context (IP, time, device, etc.)"
    )
    
    # Request details
    request_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="Full request path"
    )
    request_method = models.CharField(
        max_length=10,
        blank=True,
        help_text="HTTP method (GET, POST, etc.)"
    )
    
    # Error details
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text="Error details if access check failed"
    )
    
    # Timestamps
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="When the access request occurred"
    )
    
    class Meta:
        db_table = 'crypto_access_logs'
        verbose_name = 'Access Log'
        verbose_name_plural = 'Access Logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['resource_type', 'action']),
            models.Index(fields=['result', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.log_id}: {self.user} -> {self.resource_type}/{self.action} [{self.result}]"
    
    @classmethod
    def generate_log_id(cls):
        """Generate unique log ID using uuid to avoid race conditions"""
        import uuid
        now = timezone.now()
        date_str = now.strftime('%Y%m%d_%H%M%S')
        short_uuid = uuid.uuid4().hex[:8]
        return f"log_{date_str}_{short_uuid}"
    
    @classmethod
    def log_access(
        cls,
        user,
        resource_type,
        action,
        result,
        resource_id=None,
        policies_evaluated=None,
        policies_matched=None,
        user_attributes=None,
        environment_attributes=None,
        request_path='',
        request_method='',
        error_message=None
    ):
        """
        Create an access log entry
        
        Args:
            user: Django User object
            resource_type: Type of resource being accessed
            action: Action being performed
            result: 'allow', 'deny', or 'error'
            ... other optional fields
        
        Returns:
            AccessLog instance
        """
        return cls.objects.create(
            log_id=cls.generate_log_id(),
            user=user,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            result=result,
            policies_evaluated=policies_evaluated or [],
            policies_matched=policies_matched or [],
            user_attributes=user_attributes or {},
            environment_attributes=environment_attributes or {},
            request_path=request_path,
            request_method=request_method,
            error_message=error_message
        )


class KeyRevocation(BaseModel):
    """
    Key Revocation List Model (BM13)
    Tracks revoked CP-ABE keys for users
    
    QĐ13: Khi thuộc tính người dùng thay đổi hoặc phát hiện vi phạm bảo mật,
    khóa CP-ABE hiện tại phải được thu hồi ngay lập tức.
    """
    
    REASON_CHOICES = [
        ('attribute_change', 'Thuộc tính người dùng thay đổi'),
        ('security_breach', 'Vi phạm bảo mật'),
        ('account_termination', 'Chấm dứt tài khoản'),
        ('key_expiration', 'Khóa hết hạn'),
        ('admin_revoke', 'Admin thu hồi thủ công'),
        ('key_rotation', 'Luân chuyển khóa định kỳ'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Đang chờ xử lý'),
        ('revoked', 'Đã thu hồi'),
        ('reissued', 'Đã cấp khóa mới'),
        ('cancelled', 'Đã hủy'),
    ]
    
    # Revocation identification
    revocation_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique revocation ID (e.g., rev_22520001_20250910)"
    )
    
    # User whose key is being revoked
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='key_revocations',
        help_text="User whose key is revoked"
    )
    
    # Key info
    key_id = models.CharField(
        max_length=100,
        help_text="ID of the revoked key"
    )
    key_version = models.IntegerField(
        default=1,
        help_text="Version of the revoked key"
    )
    
    # Revocation reason
    reason = models.CharField(
        max_length=30,
        choices=REASON_CHOICES,
        help_text="Reason for key revocation"
    )
    reason_detail = models.TextField(
        blank=True,
        help_text="Additional details about revocation reason"
    )
    
    # Old attributes (at time of revocation)
    old_attributes = models.JSONField(
        default=dict,
        help_text="User attributes before change (for attribute_change reason)"
    )
    
    # New attributes (after change)
    new_attributes = models.JSONField(
        default=dict,
        help_text="User attributes after change"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Current status of revocation"
    )
    
    # New key (if reissued)
    new_key_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="ID of newly issued key (if applicable)"
    )
    
    # Revocation timestamps
    revoked_at = models.DateTimeField(
        default=timezone.now,
        help_text="When the key was revoked"
    )
    reissued_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When new key was issued"
    )
    
    # Admin who performed revocation
    revoked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='revocations_performed',
        help_text="Admin who performed the revocation"
    )
    
    class Meta:
        db_table = 'crypto_key_revocations'
        verbose_name = 'Key Revocation'
        verbose_name_plural = 'Key Revocations'
        ordering = ['-revoked_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['key_id']),
            models.Index(fields=['revoked_at']),
        ]
    
    def __str__(self):
        return f"{self.revocation_id}: {self.user.username} - {self.reason} [{self.status}]"
    
    @classmethod
    def generate_revocation_id(cls, user):
        """Generate unique revocation ID with microseconds for uniqueness"""
        import uuid
        now = timezone.now()
        date_str = now.strftime('%Y%m%d')
        time_str = now.strftime('%H%M%S')
        # Add microseconds and short uuid for uniqueness
        unique_suffix = f"{now.microsecond:06d}_{uuid.uuid4().hex[:4]}"
        return f"rev_{user.id}_{date_str}_{time_str}_{unique_suffix}"
    
    @classmethod
    def revoke_user_key(
        cls,
        user,
        key_id,
        reason,
        revoked_by=None,
        old_attributes=None,
        new_attributes=None,
        reason_detail='',
        key_version=1
    ):
        """
        Create a key revocation record
        
        Args:
            user: User whose key is being revoked
            key_id: ID of the key to revoke
            reason: Revocation reason code
            revoked_by: Admin performing revocation
            old_attributes: User's attributes before change
            new_attributes: User's new attributes
            reason_detail: Additional details
            key_version: Version of the key
        
        Returns:
            KeyRevocation instance
        """
        return cls.objects.create(
            revocation_id=cls.generate_revocation_id(user),
            user=user,
            key_id=key_id,
            key_version=key_version,
            reason=reason,
            reason_detail=reason_detail,
            old_attributes=old_attributes or {},
            new_attributes=new_attributes or {},
            status='revoked',
            revoked_by=revoked_by
        )
    
    def mark_reissued(self, new_key_id):
        """Mark this revocation as reissued with new key"""
        self.status = 'reissued'
        self.new_key_id = new_key_id
        self.reissued_at = timezone.now()
        self.save()
    
    @classmethod
    def is_key_revoked(cls, key_id):
        """Check if a key has been revoked"""
        return cls.objects.filter(
            key_id=key_id,
            status__in=['revoked', 'reissued']
        ).exists()
    
    @classmethod
    def get_user_revocations(cls, user, status=None):
        """Get all revocations for a user"""
        qs = cls.objects.filter(user=user)
        if status:
            qs = qs.filter(status=status)
        return qs
