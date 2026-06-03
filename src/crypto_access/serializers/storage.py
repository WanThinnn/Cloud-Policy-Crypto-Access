"""
Storage Serializers
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from ..models import StorageBucket, UploadedFile, FileAccessPolicy, AccessPolicy


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
            'tags', 'metadata', 'uploaded_at', 'updated_at',
            'is_deleted', 'deleted_at'
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
    policy_id = serializers.IntegerField(required=False, help_text="Policy ID for CP-ABE encryption")
    
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


class FileAccessPolicySerializer(serializers.ModelSerializer):
    """Serializer for FileAccessPolicy - assign policies to files/folders"""
    
    policy_name = serializers.CharField(source='policy.name', read_only=True)
    policy_description = serializers.CharField(source='policy.description', read_only=True)
    policy_effect = serializers.CharField(source='policy.effect', read_only=True)
    file_name = serializers.CharField(source='uploaded_file.file_name', read_only=True)
    bucket_name = serializers.CharField(source='bucket.name', read_only=True)
    assigned_by_username = serializers.CharField(source='assigned_by.username', read_only=True)
    granted_users_info = serializers.SerializerMethodField()
    
    class Meta:
        model = FileAccessPolicy
        fields = [
            'id', 'uploaded_file', 'file_name', 'folder_path', 
            'bucket', 'bucket_name', 'target_type',
            'policy', 'policy_name', 'policy_description', 'policy_effect',
            'granted_users', 'granted_users_info',
            'assigned_by', 'assigned_by_username', 'assigned_at', 'notes'
        ]
        read_only_fields = ['assigned_by', 'assigned_at']
    
    def get_granted_users_info(self, obj):
        return [
            {'id': u.id, 'username': u.username, 'email': u.email}
            for u in obj.granted_users.all()
        ]


class AssignPolicyToFileSerializer(serializers.Serializer):
    """Serializer for assigning policy to file/folder"""
    
    # Target info
    file_path = serializers.CharField(max_length=500, help_text="File path within bucket")
    bucket_name = serializers.CharField(max_length=100, default='documents')
    target_type = serializers.ChoiceField(
        choices=['file', 'folder'], 
        default='file',
        help_text="'file' for single file, 'folder' for all files in folder"
    )
    
    # Policy assignment
    policy_id = serializers.IntegerField(required=False, help_text="Existing policy ID to assign")
    
    # For creating new policy (optional)
    create_new_policy = serializers.BooleanField(default=False)
    new_policy_name = serializers.CharField(max_length=100, required=False)
    new_policy_description = serializers.CharField(required=False, allow_blank=True)
    new_policy_subject_condition = serializers.CharField(required=False)
    new_policy_effect = serializers.ChoiceField(choices=['allow', 'deny'], required=False)
    new_policy_priority = serializers.IntegerField(required=False, default=100)
    new_policy_resource = serializers.CharField(required=False, default='document')
    new_policy_action = serializers.CharField(required=False, default='read')
    
    # Direct user grants (optional)
    grant_user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="List of user IDs to grant direct access"
    )
    
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        # Either policy_id or create_new_policy with required fields
        if not data.get('policy_id') and not data.get('create_new_policy'):
            raise serializers.ValidationError(
                "Either 'policy_id' or 'create_new_policy' with policy details is required"
            )
        
        if data.get('create_new_policy'):
            required_fields = ['new_policy_name', 'new_policy_subject_condition', 'new_policy_effect']
            for field in required_fields:
                if not data.get(field):
                    raise serializers.ValidationError(
                        f"'{field}' is required when creating new policy"
                    )
        
        return data


class PolicyListForAssignmentSerializer(serializers.ModelSerializer):
    """Simplified policy serializer for assignment dropdown"""
    
    class Meta:
        model = AccessPolicy
        fields = ['id', 'name', 'description', 'resource', 'action', 'effect', 'subject_condition', 'is_active']
