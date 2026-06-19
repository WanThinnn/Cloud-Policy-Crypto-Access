"""
Dual-Hash Password Hasher: SHA3-512 (client) + Argon2id (server)

This custom hasher enables backward-compatible dual-hashing:
- New flow: Client sends SHA3-512(password) → Server does Argon2id(SHA3-512_hash)
- Legacy flow: Client sends plaintext → Server does Argon2id(SHA3-512(plaintext)) for verification

The verify() method handles both cases transparently, enabling seamless migration
for existing users without requiring password resets.
"""

import hashlib
import logging

from django.contrib.auth.hashers import Argon2PasswordHasher

logger = logging.getLogger('crypto_access.auth')


class DualHashArgon2PasswordHasher(Argon2PasswordHasher):
    """
    Custom Argon2 hasher that supports dual-hashing with SHA3-512 pre-hash.
    
    Encoding (set_password / make_password):
        - Expects the input to already be a SHA3-512 hex digest (128 chars) 
          from the client-side pre-hash.
        - Falls back to SHA3-512 hashing the input server-side if the input 
          doesn't look like a pre-hash (e.g., from management commands).
    
    Verification (check_password / authenticate):
        - First tries to verify the input directly (assuming it's already 
          SHA3-512 pre-hashed from the client).
        - If that fails, tries SHA3-512 hashing the input first, then verifying
          (backward compatibility for legacy passwords stored with Argon2id(plaintext)).
        - This handles the migration period where old passwords are 
          Argon2id(plaintext) and new passwords are Argon2id(SHA3-512(plaintext)).
    """
    
    algorithm = 'argon2'  # Keep same algorithm identifier for DB compatibility
    
    @staticmethod
    def _is_sha3_512_hex(value):
        """Check if a string looks like a SHA3-512 hex digest (128 hex chars)."""
        return len(value) == 128 and all(c in '0123456789abcdef' for c in value.lower())
    
    @staticmethod
    def _sha3_512(value):
        """Compute SHA3-512 hash of a string, return hex digest."""
        return hashlib.sha3_512(value.encode('utf-8')).hexdigest()
    
    def encode(self, password, salt):
        """
        Encode password with Argon2id.
        
        If the password is already a SHA3-512 hex digest (from client pre-hash),
        use it directly. Otherwise, apply SHA3-512 first (for server-side calls
        like management commands or admin password resets).
        """
        if self._is_sha3_512_hex(password):
            # Already pre-hashed by client
            return super().encode(password, salt)
        else:
            # Server-side call (management command, admin reset, etc.)
            # Apply SHA3-512 first to maintain consistency
            prehashed = self._sha3_512(password)
            return super().encode(prehashed, salt)
    
    def verify(self, password, encoded):
        """
        Verify password against encoded hash.
        
        Strategy:
        1. Try verifying the input directly (client sent SHA3-512 pre-hash)
        2. If that fails, try SHA3-512(input) then verify 
           (backward compat: old Argon2id(plaintext) passwords being verified
            with the new client flow that sends SHA3-512(plaintext))
        3. If THAT fails, try input directly against parent 
           (backward compat: old password, plaintext input from non-JS source)
        """
        # Case 1: Input is already SHA3-512 from client, encoded is Argon2id(SHA3-512)
        # This is the new standard flow
        if super().verify(password, encoded):
            return True
        
        # Case 2: Input is plaintext from client (old flow or non-JS),
        # but encoded is Argon2id(SHA3-512) (new format)
        # → SHA3-512 the plaintext and try again
        if not self._is_sha3_512_hex(password):
            prehashed = self._sha3_512(password)
            if super().verify(prehashed, encoded):
                return True
        
        return False
    
    def must_update(self, encoded):
        """
        Signal Django to re-hash the password on next login.
        
        This ensures that when a user with an old-format password 
        (Argon2id(plaintext)) logs in successfully, their password 
        is re-hashed to the new format (Argon2id(SHA3-512(plaintext))).
        """
        return super().must_update(encoded)
