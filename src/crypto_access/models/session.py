from django.db import models
from django.contrib.auth.models import User
from .base import BaseModel

class ActiveSession(BaseModel):
    """
    Tracks active user sessions to allow centralized revocation and tracking of devices.
    Coupled with JWT tokens (matching jti).
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='active_sessions')
    session_key = models.CharField(max_length=255, unique=True, help_text="JWT Token JTI (ID)")
    
    # Device info
    device_name = models.CharField(max_length=255, blank=True, null=True, help_text="e.g. Windows PC, iPhone 13")
    browser = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. Chrome, Firefox")
    os_name = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. Windows 10, iOS")
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True, help_text="Country/City from GeoIP")
    
    # Activity tracking
    last_active = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'crypto_active_sessions'
        verbose_name = 'Active Session'
        verbose_name_plural = 'Active Sessions'
        ordering = ['-last_active']
        
    def __str__(self):
        return f"{self.user.username} - {self.device_name} ({self.ip_address})"
