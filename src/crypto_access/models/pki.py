"""
Public Key Infrastructure (PKI) Models
Stores ML-DSA-87 Public Keys and Encrypted Secret Keys for Users.
"""
from django.db import models
from django.contrib.auth.models import User
from .base import BaseModel


class UserPublicKey(BaseModel):
    """
    Stores the user's ML-DSA-87 Public Key for Dual-Layer Signatures.
    Also stores the encrypted Secret Key for cross-device syncing.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('revoked', 'Revoked'),
        ('expired', 'Expired'),
    ]

    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='pqc_keys',
        help_text="The user who owns this keypair"
    )
    
    # ML-DSA-87 public keys are large (~2.5KB)
    pqc_public_key = models.TextField(
        help_text="Base64 encoded ML-DSA-87 Public Key"
    )
    
    # Encrypted Secret Keys (~4.8KB when decrypted, slightly larger when encrypted + base64)
    encrypted_pqc_sk_primary = models.TextField(
        help_text="Base64 encoded string: [IV (12 bytes)] + [Ciphertext of Secret Key encrypted with WebAuthn PRF]"
    )
    
    encrypted_pqc_sk_recovery = models.TextField(
        blank=True,
        null=True,
        help_text="Base64 encoded string: [IV (12 bytes)] + [Ciphertext of Secret Key encrypted with Argon2 Mnemonic Fallback]"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    
    device_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional device/browser name where this key was generated"
    )
    
    ca_signature = models.TextField(
        blank=True,
        null=True,
        help_text="Base64 encoded ML-DSA-87 signature from the RootCA over the JSON representation of this key"
    )

    class Meta:
        db_table = 'crypto_user_pki_keys'
        verbose_name = 'User PQC Public Key'
        verbose_name_plural = 'User PQC Public Keys'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.status} ({self.created_at.strftime('%Y-%m-%d')})"
    
    def revoke(self):
        self.status = 'revoked'
        self.save()
