"""
Admin configuration for crypto_access app.
"""

from django.contrib import admin
from django.db import models
from django_json_widget.widgets import JSONEditorWidget
from .models import UserProfile, SystemSetting  # Works because models/__init__.py exports it


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
