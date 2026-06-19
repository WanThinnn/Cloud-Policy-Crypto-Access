"""
WebAuthn Credential Model for Passkey Login

Stores server-side WebAuthn credentials for passwordless authentication.
Separate from the PQC/PRF passkey used for E2EE document signing.
"""
from django.db import models
from django.contrib.auth.models import User
from .base import BaseModel


class WebAuthnCredential(BaseModel):
    """
    Stores a WebAuthn credential for server-side passkey authentication.
    
    This is separate from the PRF-based passkey used for E2EE key derivation
    in pqc-manager.js. The login passkey uses server-side verification 
    (challenge-response), while the E2EE passkey uses the PRF extension 
    for client-side key derivation.
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='webauthn_credentials',
        help_text="The user who owns this credential"
    )
    
    # WebAuthn credential data
    credential_id = models.BinaryField(
        unique=True,
        help_text="Unique credential identifier (raw bytes)"
    )
    
    public_key = models.BinaryField(
        help_text="COSE-encoded public key for signature verification"
    )
    
    sign_count = models.PositiveIntegerField(
        default=0,
        help_text="Signature counter for replay attack detection"
    )
    
    # Authenticator metadata
    device_name = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Friendly name for the authenticator device"
    )
    
    aaguid = models.CharField(
        max_length=36,
        blank=True,
        default='',
        help_text="Authenticator Attestation GUID"
    )
    
    transports = models.JSONField(
        default=list,
        blank=True,
        help_text="List of supported transports (usb, nfc, ble, internal, hybrid)"
    )
    
    # Status flags
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this credential is currently active"
    )
    
    backed_up = models.BooleanField(
        default=False,
        help_text="Whether this is a synced/backed-up passkey (cross-platform)"
    )
    
    class Meta:
        db_table = 'crypto_webauthn_credentials'
        verbose_name = 'WebAuthn Credential'
        verbose_name_plural = 'WebAuthn Credentials'
        ordering = ['-created_at']
    
    def __str__(self):
        device = self.device_name or 'Unknown Device'
        return f"{self.user.username} - {device} ({'active' if self.is_active else 'disabled'})"
