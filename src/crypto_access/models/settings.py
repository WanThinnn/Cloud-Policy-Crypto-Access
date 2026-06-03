from django.db import models
from .base import BaseModel

class SystemSetting(BaseModel):
    """
    Dynamic configuration for the system.
    Stores JSON values for system-wide settings like ABAC_PROTECTED_ROUTES, ACTION_PERMISSION_MAP, etc.
    """
    key = models.CharField(max_length=255, unique=True, help_text="Unique key for the setting (e.g. ACTION_PERMISSION_MAP)")
    value = models.JSONField(help_text="JSON value for this setting")
    description = models.TextField(blank=True, help_text="Description of what this setting does")
    is_active = models.BooleanField(default=True, help_text="Whether this setting is currently active")

    class Meta:
        db_table = 'crypto_system_settings'
        verbose_name = 'System Setting'
        verbose_name_plural = 'System Settings'
        ordering = ['key']

    def __str__(self):
        return f"{self.key} ({'Active' if self.is_active else 'Inactive'})"
