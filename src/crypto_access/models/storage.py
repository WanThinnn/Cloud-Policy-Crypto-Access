"""
Storage Models - Track uploaded files in database
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


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
    file_path = models.CharField(max_length=500, help_text="Path within bucket")
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES, default='other')
    mime_type = models.CharField(max_length=100)
    file_size = models.BigIntegerField(help_text="File size in bytes")
    
    # Access URLs
    public_url = models.URLField(blank=True, null=True)
    signed_url = models.URLField(blank=True, null=True)
    signed_url_expires_at = models.DateTimeField(blank=True, null=True)
    
    # Metadata
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional metadata")
    
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
