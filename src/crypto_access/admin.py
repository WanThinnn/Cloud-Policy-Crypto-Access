"""
Admin configuration for crypto_access app.
"""

from django.contrib import admin
from django.db import models
from django_json_widget.widgets import JSONEditorWidget
from .models import (
    UserProfile, SystemSetting, StorageBucket, UploadedFile, 
    FileAccessPolicy, UserType, AttributeDefinition, UserAttribute, 
    AccessPolicy, AccessLog, KeyRevocation
)

@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ('key', 'is_active', 'updated_at')
    list_filter = ('is_active', 'created_at', 'updated_at')
    search_fields = ('key', 'description')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Setting Information', {
            'fields': ('key', 'value', 'description', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    formfield_overrides = {
        models.JSONField: {'widget': JSONEditorWidget},
    }


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__username', 'user__email', 'phone')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Profile Details', {
            'fields': ('phone', 'address', 'bio')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(StorageBucket)
class StorageBucketAdmin(admin.ModelAdmin):
    list_display = ('name', 'bucket_type', 'created_at')
    list_filter = ('bucket_type',)
    search_fields = ('name',)

@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'bucket', 'uploaded_by', 'file_type', 'uploaded_at')
    list_filter = ('file_type', 'bucket', 'uploaded_at')
    search_fields = ('file_name', 'file_path', 'uploaded_by__username')

@admin.register(FileAccessPolicy)
class FileAccessPolicyAdmin(admin.ModelAdmin):
    list_display = ('target_type', 'bucket', 'policy', 'assigned_at')
    list_filter = ('target_type', 'bucket')
    search_fields = ('folder_path', 'uploaded_file__file_name')

@admin.register(UserType)
class UserTypeAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_system', 'is_active')
    list_filter = ('is_system', 'is_active')
    search_fields = ('code', 'name')

@admin.register(AttributeDefinition)
class AttributeDefinitionAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_name', 'data_type', 'is_required', 'is_active')
    list_filter = ('data_type', 'is_required', 'is_active')
    search_fields = ('name', 'display_name')

@admin.register(UserAttribute)
class UserAttributeAdmin(admin.ModelAdmin):
    list_display = ('user', 'attribute', 'value', 'status', 'effective_date')
    list_filter = ('status', 'attribute')
    search_fields = ('user__username', 'value')

@admin.register(AccessPolicy)
class AccessPolicyAdmin(admin.ModelAdmin):
    list_display = ('name', 'resource', 'action', 'effect', 'priority', 'is_active')
    list_filter = ('resource', 'action', 'effect', 'is_active')
    search_fields = ('name', 'subject_condition')

@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ('log_id', 'user', 'action', 'resource_type', 'resource_id', 'result', 'timestamp')
    list_filter = ('action', 'result', 'resource_type', 'timestamp')
    search_fields = ('log_id', 'user__username', 'request_path', 'error_message')

@admin.register(KeyRevocation)
class KeyRevocationAdmin(admin.ModelAdmin):
    list_display = ('user', 'reason', 'revoked_at', 'status')
    list_filter = ('status', 'revoked_at')
    search_fields = ('user__username', 'reason', 'details')
