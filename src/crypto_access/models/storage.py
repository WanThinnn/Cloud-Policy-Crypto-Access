"""
Storage Models - Track uploaded files in database
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from .policy import AccessPolicy
from .fields import EncryptedCharField, EncryptedJSONField, BlindIndexField


class StorageBucket(models.Model):
    """Track storage buckets"""
    
    BUCKET_TYPE_CHOICES = [
        ('public', 'Public'),
        ('private', 'Private'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    bucket_type = models.CharField(max_length=10, choices=BUCKET_TYPE_CHOICES, default='private')
    description = models.TextField(blank=True)
    allowed_mime_types = models.JSONField(default=list, blank=True)
    max_file_size = models.BigIntegerField(null=True, blank=True, help_text="Max file size in bytes")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'storage_buckets'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.bucket_type})"


class UploadedFile(models.Model):
    """Track uploaded files metadata"""
    
    FILE_TYPE_CHOICES = [
        ('image', 'Image'),
        ('pdf', 'PDF Document'),
        ('document', 'Document'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('other', 'Other'),
    ]
    
    bucket = models.ForeignKey(StorageBucket, on_delete=models.CASCADE, related_name='files')
    file_path = EncryptedCharField(max_length=500, help_text="Path within bucket (Encrypted)")
    file_path_hash = BlindIndexField(source_field='file_path', help_text="HMAC-SHA3-256 for secure path search", null=True)
    file_name = EncryptedCharField(max_length=500, help_text="File name (Encrypted)")
    file_name_hash = BlindIndexField(source_field='file_name', help_text="HMAC-SHA3-256 for secure search", null=True)
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES, default='other')
    mime_type = models.CharField(max_length=100)
    file_size = models.BigIntegerField(help_text="File size in bytes")
    
    # URL paths - can be cached
    public_url = EncryptedCharField(max_length=1000, null=True, blank=True)
    signed_url = EncryptedCharField(max_length=1000, null=True, blank=True)
    signed_url_expires_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    metadata = EncryptedJSONField(default=dict, blank=True, help_text="Additional metadata (Encrypted)")
    
    # Soft Delete
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'uploaded_files'
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['bucket', 'file_path']),
            models.Index(fields=['uploaded_by']),
            models.Index(fields=['file_type']),
        ]
    
    def __str__(self):
        return f"{self.file_name} ({self.bucket.name})"
    
    def is_image(self):
        return self.file_type == 'image'
    
    def is_pdf(self):
        return self.file_type == 'pdf'
    
    def get_file_size_display(self):
        """Return human-readable file size"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"
    
    @classmethod
    def detect_file_type(cls, mime_type: str) -> str:
        """Detect file type from MIME type"""
        if mime_type.startswith('image/'):
            return 'image'
        elif mime_type == 'application/pdf':
            return 'pdf'
        elif mime_type.startswith('video/'):
            return 'video'
        elif mime_type.startswith('audio/'):
            return 'audio'
        elif mime_type in ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                           'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                           'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                           'text/plain']:
            return 'document'
        else:
            return 'other'

    def get_latest_version(self):
        """Get the latest FileVersion object"""
        return self.versions.order_by('-version_number').first()


class FileVersion(models.Model):
    """
    Track versions of an uploaded file. Each version points to a physical file 
    on the storage bucket and records the CP-ABE policy used to encrypt it.
    """
    file = models.ForeignKey(UploadedFile, on_delete=models.CASCADE, related_name='versions')
    version_number = models.IntegerField(default=1)
    physical_path = models.CharField(max_length=500, help_text="Actual path in storage (e.g. docs/report_v2.pdf)")
    file_size = models.BigIntegerField(help_text="File size in bytes")
    cpabe_policy = models.TextField(blank=True, null=True, help_text="CP-ABE policy string used to encrypt this specific version")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'file_versions'
        ordering = ['-version_number']
        unique_together = ('file', 'version_number')
        
    def __str__(self):
        return f"{self.file.file_name} - v{self.version_number}"

class FileAccessPolicy(models.Model):
    """
    Link files/folders to access policies
    Allows assigning existing policies to files or creating file-specific policies
    """
    
    TARGET_TYPE_CHOICES = [
        ('file', 'Single File'),
        ('folder', 'Folder (recursive)'),
    ]
    
    # Target: either a specific file or a folder path
    uploaded_file = models.ForeignKey(
        UploadedFile, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='access_policies',
        help_text="Link to specific file (for file targets)"
    )
    folder_path = models.CharField(
        max_length=500, 
        blank=True,
        null=True,
        help_text="Folder path for folder-level policies (e.g., 'hr/', 'finance/reports/')"
    )
    bucket = models.ForeignKey(
        StorageBucket, 
        on_delete=models.CASCADE,
        related_name='folder_policies',
        help_text="Storage bucket for folder policies"
    )
    target_type = models.CharField(
        max_length=10, 
        choices=TARGET_TYPE_CHOICES, 
        default='file'
    )
    
    # The policy to apply
    policy = models.ForeignKey(
        AccessPolicy,
        on_delete=models.CASCADE,
        related_name='file_assignments',
        help_text="The access policy to apply to this file/folder"
    )
    
    # Override: allows granting specific users direct access regardless of ABAC
    granted_users = models.ManyToManyField(
        User,
        blank=True,
        related_name='granted_file_access',
        help_text="Users with explicit access to this file (bypasses ABAC)"
    )
    
    # Audit
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assigned_file_policies'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, help_text="Notes about why this policy was assigned")
    
    class Meta:
        db_table = 'file_access_policies'
        verbose_name = 'File Access Policy'
        verbose_name_plural = 'File Access Policies'
        ordering = ['-assigned_at']
        # Ensure unique policy per file/folder
        unique_together = [
            ('uploaded_file', 'policy'),
            ('folder_path', 'bucket', 'policy'),
        ]
    
    def __str__(self):
        target = self.uploaded_file.file_name if self.uploaded_file else f"Folder: {self.folder_path}"
        return f"{target} -> {self.policy.name}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.uploaded_file and not self.folder_path:
            raise ValidationError("Either uploaded_file or folder_path must be set")
        if self.uploaded_file and self.folder_path:
            raise ValidationError("Cannot set both uploaded_file and folder_path")
    
    @classmethod
    def get_policies_for_file(cls, bucket_name: str, file_path: str):
        """
        Get all policies that apply to a specific file.
        Includes both direct file policies and inherited folder policies.
        """
        policies = []
        
        # Direct file policy
        try:
            bucket = StorageBucket.objects.get(name=bucket_name)
            file_record = UploadedFile.objects.filter(
                bucket=bucket, 
                file_path=file_path
            ).first()
            
            if file_record:
                file_policies = cls.objects.filter(
                    uploaded_file=file_record
                ).select_related('policy')
                policies.extend([fp.policy for fp in file_policies])
            
            # Folder policies (check all parent folders)
            path_parts = file_path.split('/')
            for i in range(len(path_parts)):
                folder_path = '/'.join(path_parts[:i+1]) + '/' if i < len(path_parts) - 1 else '/'.join(path_parts[:i]) + '/'
                folder_policies = cls.objects.filter(
                    bucket=bucket,
                    folder_path=folder_path,
                    target_type='folder'
                ).select_related('policy')
                policies.extend([fp.policy for fp in folder_policies])
                
        except StorageBucket.DoesNotExist:
            pass
        
        return list(set(policies))  # Remove duplicates
    
    @classmethod
    def check_user_has_access(cls, user, bucket_name: str, file_path: str):
        """
        Check if user has explicit access to a file via granted_users.
        Returns True if user is in granted_users of any applicable FileAccessPolicy.
        """
        try:
            bucket = StorageBucket.objects.get(name=bucket_name)
            file_record = UploadedFile.objects.filter(
                bucket=bucket, 
                file_path=file_path
            ).first()
            
            if file_record:
                # Check direct file grants
                if cls.objects.filter(
                    uploaded_file=file_record,
                    granted_users=user
                ).exists():
                    return True
            
            # Check folder grants
            path_parts = file_path.split('/')
            for i in range(len(path_parts)):
                folder_path = '/'.join(path_parts[:i+1]) + '/' if i < len(path_parts) - 1 else '/'.join(path_parts[:i]) + '/'
                if cls.objects.filter(
                    bucket=bucket,
                    folder_path=folder_path,
                    target_type='folder',
                    granted_users=user
                ).exists():
                    return True
                    
        except StorageBucket.DoesNotExist:
            pass
        
        return False
