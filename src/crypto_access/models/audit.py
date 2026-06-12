"""
Audit Models for ABAC System
- AccessLog (BM12): Access log
- KeyRevocation (BM13): Key revocation list
"""

from django.db import models, transaction
from django.contrib.auth.models import User
from django.utils import timezone
import hashlib
from .base import BaseModel
from .fields import EncryptedJSONField


class AccessLog(BaseModel):
    """
    Access Log Model (BM12)
    Records all access requests for audit and compliance
    
    QĐ12: All access requests (including success and failure) 
    must be recorded in the log system.
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
    user_attributes = EncryptedJSONField(
        default=dict,
        help_text="User's ABAC attributes at time of access (Encrypted)"
    )
    
    # Environment attributes
    environment_attributes = EncryptedJSONField(
        default=dict,
        help_text="Environment context (IP, time, device, etc.) (Encrypted)"
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
    
    # Tamper-proof hash chain
    previous_hash = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="SHA3-256 hash of the previous log entry"
    )
    log_hash = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        unique=True,
        help_text="SHA3-256 hash of this log entry"
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
        
    def calculate_hash(self):
        """Calculate SHA3-256 hash for this log entry."""
        user_id = str(self.user.id) if self.user else "System"
        timestamp_str = self.timestamp.isoformat() if self.timestamp else ""
        prev_hash = self.previous_hash or ""
        
        data = f"{self.log_id}|{user_id}|{self.resource_type}|{self.resource_id or ''}|{self.action}|{self.result}|{timestamp_str}|{prev_hash}"
        return hashlib.sha3_256(data.encode('utf-8')).hexdigest()
        
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        
        if is_new and not self.log_hash:
            with transaction.atomic():
                last_log = AccessLog.objects.select_for_update().order_by('-timestamp', '-id').first()
                if last_log and last_log.log_hash:
                    self.previous_hash = last_log.log_hash
                else:
                    self.previous_hash = "GENESIS_BLOCK"
                
                if not self.timestamp:
                    self.timestamp = timezone.now()
                    
                self.log_hash = self.calculate_hash()
                super().save(*args, **kwargs)
                
                # Update chain state in cache for O(1) verification
                from django.core.cache import cache
                chain_state = {
                    'last_hash': self.log_hash,
                    'total_count': AccessLog.objects.count(),
                }
                cache.set('audit_chain_state', chain_state, timeout=None)
        else:
            super().save(*args, **kwargs)
    
    @classmethod
    def verify_chain_quick(cls):
        """
        O(1) Quick verification of audit log chain integrity.
        Checks the latest log entry against cached chain state
        and recomputes its hash to detect tampering.
        
        Returns:
            dict: {
                'is_valid': bool,
                'mode': 'quick',
                'detail': str
            }
        """
        from django.core.cache import cache
        
        total_count = cls.objects.count()
        if total_count == 0:
            return {'is_valid': True, 'mode': 'quick', 'detail': 'No logs exist.'}
        
        # Get the latest log
        last_log = cls.objects.order_by('-timestamp', '-id').first()
        if not last_log or not last_log.log_hash:
            return {
                'is_valid': False, 'mode': 'quick',
                'detail': 'Latest log has no hash — chain is not initialized.'
            }
        
        # 1) Recompute the latest log's hash to check for field tampering
        recalculated = last_log.calculate_hash()
        if recalculated != last_log.log_hash:
            return {
                'is_valid': False, 'mode': 'quick',
                'detail': f'Latest log [{last_log.log_id}] hash mismatch — data has been tampered with.'
            }
        
        # 2) Check against cached chain state
        chain_state = cache.get('audit_chain_state')
        if chain_state:
            if chain_state['last_hash'] != last_log.log_hash:
                return {
                    'is_valid': False, 'mode': 'quick',
                    'detail': 'Chain state mismatch — logs may have been inserted or deleted.'
                }
            if chain_state['total_count'] != total_count:
                return {
                    'is_valid': False, 'mode': 'quick',
                    'detail': f"Log count mismatch (expected {chain_state['total_count']}, found {total_count}) — logs may have been deleted or inserted."
                }
        else:
            # No cached state — rebuild it
            cache.set('audit_chain_state', {
                'last_hash': last_log.log_hash,
                'total_count': total_count,
            }, timeout=None)
        
        # 3) Spot-check: verify the link between the last 2 logs
        second_last = cls.objects.order_by('-timestamp', '-id')[1:2].first()
        if second_last:
            if last_log.previous_hash != second_last.log_hash:
                return {
                    'is_valid': False, 'mode': 'quick',
                    'detail': f'Chain link broken between [{second_last.log_id}] and [{last_log.log_id}].'
                }
        elif last_log.previous_hash != "GENESIS_BLOCK":
            return {
                'is_valid': False, 'mode': 'quick',
                'detail': 'First log does not point to GENESIS_BLOCK — chain origin corrupted.'
            }
        
        return {
            'is_valid': True, 'mode': 'quick',
            'detail': f'Quick check passed ({total_count} logs, latest hash verified).'
        }
            
    @classmethod
    def deep_verify_chain(cls):
        """
        O(N) Deep verification — scans every log entry sequentially.
        Use when quick check fails or for periodic full audit.
        
        Returns:
            dict: {
                'is_valid': bool,
                'mode': 'deep',
                'corrupted_logs': list of log_ids,
                'total_checked': int
            }
        """
        logs = cls.objects.all().order_by('timestamp', 'id').only(
            'id', 'log_id', 'user_id', 'resource_type', 'resource_id',
            'action', 'result', 'timestamp', 'previous_hash', 'log_hash'
        )
        
        if not logs.exists():
            return {'is_valid': True, 'mode': 'deep', 'corrupted_logs': [], 'total_checked': 0}
            
        corrupted = []
        expected_prev_hash = "GENESIS_BLOCK"
        total = 0
        
        for log in logs.iterator():
            total += 1
            if log.previous_hash != expected_prev_hash:
                corrupted.append(log.log_id)
                
            calculated = log.calculate_hash()
            if calculated != log.log_hash:
                if log.log_id not in corrupted:
                    corrupted.append(log.log_id)
            
            expected_prev_hash = log.log_hash
        
        # Update chain state after deep scan
        if not corrupted:
            from django.core.cache import cache
            cache.set('audit_chain_state', {
                'last_hash': expected_prev_hash,
                'total_count': total,
            }, timeout=None)
            
        return {
            'is_valid': len(corrupted) == 0,
            'mode': 'deep',
            'corrupted_logs': corrupted,
            'total_checked': total
        }
    
    @classmethod
    def verify_chain(cls):
        """
        Legacy wrapper — runs quick check first, falls back to deep scan.
        Returns:
            (bool, list): (is_valid, list of corrupted log_ids)
        """
        quick = cls.verify_chain_quick()
        if quick['is_valid']:
            return True, []
        # Quick check failed — run deep scan to find all corrupted entries
        deep = cls.deep_verify_chain()
        return deep['is_valid'], deep.get('corrupted_logs', [])
    
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
    
    QĐ13: When user attributes change or a security breach is detected,
    the current CP-ABE key must be immediately revoked.
    """
    
    REASON_CHOICES = [
        ('attribute_change', 'User attributes changed'),
        ('security_breach', 'Security breach'),
        ('account_termination', 'Account terminated'),
        ('key_expiration', 'Key expired'),
        ('admin_revoke', 'Admin revoked manually'),
        ('key_rotation', 'Periodic key rotation'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('revoked', 'Revoked'),
        ('reissued', 'Key reissued'),
        ('cancelled', 'Cancelled'),
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
    old_attributes = EncryptedJSONField(
        default=dict,
        help_text="User attributes before change (Encrypted)"
    )
    
    # New attributes (after change)
    new_attributes = EncryptedJSONField(
        default=dict,
        help_text="User attributes after change (Encrypted)"
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
