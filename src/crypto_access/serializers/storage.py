"""
Storage Serializers
"""
from rest_framework import serializers
from ..models import StorageBucket, UploadedFile


class StorageBucketSerializer(serializers.ModelSerializer):
    file_count = serializers.SerializerMethodField()
    
    class Meta:
        model = StorageBucket
        fields = [
            'id', 'name', 'bucket_type', 'description',
            'allowed_mime_types', 'max_file_size',
            'file_count', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_file_count(self, obj):
        return obj.files.count()


class UploadedFileSerializer(serializers.ModelSerializer):
    bucket_name = serializers.CharField(source='bucket.name', read_only=True)
    file_size_display = serializers.CharField(source='get_file_size_display', read_only=True)
    uploaded_by_username = serializers.CharField(source='uploaded_by.username', read_only=True)
    
    class Meta:
        model = UploadedFile
        fields = [
            'id', 'bucket', 'bucket_name', 'file_path', 'file_name',
            'file_type', 'mime_type', 'file_size', 'file_size_display',
            'public_url', 'signed_url', 'signed_url_expires_at',
            'uploaded_by', 'uploaded_by_username', 'description',
            'tags', 'metadata', 'uploaded_at', 'updated_at'
        ]
        read_only_fields = ['uploaded_at', 'updated_at']


class FileUploadSerializer(serializers.Serializer):
    """Serializer for file upload requests"""
    file = serializers.FileField()
    bucket_name = serializers.CharField(max_length=100)
    file_path = serializers.CharField(max_length=500, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    tags = serializers.ListField(child=serializers.CharField(), required=False)
    is_public = serializers.BooleanField(default=False)
    
    def validate_file(self, value):
        """Validate file size and type"""
        max_size = 10 * 1024 * 1024  # 10MB default
        if value.size > max_size:
            raise serializers.ValidationError(f"File size cannot exceed {max_size / 1024 / 1024}MB")
        return value


class SignedUrlRequestSerializer(serializers.Serializer):
    """Request serializer for creating signed URLs"""
    file_id = serializers.IntegerField()
    expires_in = serializers.IntegerField(default=3600, min_value=60, max_value=86400)
