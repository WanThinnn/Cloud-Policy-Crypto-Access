"""
Crypto utilities for password-based key derivation and encryption
"""
import os
import hashlib
from typing import Tuple, Dict, Any
from argon2 import PasswordHasher
from argon2.low_level import hash_secret_raw, Type
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend
import logging

logger = logging.getLogger(__name__)

class CryptoUtils:
    """
    Utility class for cryptographic operations
    """
    
    # Argon2id parameters
    ARGON2_TIME_COST = 10      # Number of iterations
    ARGON2_MEMORY_COST = 65536 # 64 MB
    ARGON2_PARALLELISM = 1     # Threads
    ARGON2_HASH_LEN = 32       # 256 bits
    ARGON2_SALT_LEN = 16       # 128 bits
    
    # HKDF parameters
    HKDF_KEY_LEN = 32          # 256 bits for AES-256-GCM
    HKDF_INFO = b"ABE-PrivateKey-Encryption"
    
    # AES-GCM parameters
    GCM_NONCE_LEN = 12         # 96 bits (recommended for GCM)
    GCM_TAG_LEN = 16          # 128 bits
    
    @staticmethod
    def generate_salt() -> bytes:
        """Generate a random salt"""
        return os.urandom(CryptoUtils.ARGON2_SALT_LEN)
    
    @staticmethod
    def derive_key_from_password(password: str, salt: bytes) -> bytes:
        """
        Derive key from password using Argon2id + HKDF with SHA3-256
        
        Args:
            password: User password
            salt: Random salt
            
        Returns:
            Derived key (32 bytes)
        """
        try:
            # Step 1: Argon2id key derivation
            password_bytes = password.encode('utf-8')
            
            argon2_key = hash_secret_raw(
                secret=password_bytes,
                salt=salt,
                time_cost=CryptoUtils.ARGON2_TIME_COST,
                memory_cost=CryptoUtils.ARGON2_MEMORY_COST,
                parallelism=CryptoUtils.ARGON2_PARALLELISM,
                hash_len=CryptoUtils.ARGON2_HASH_LEN,
                type=Type.ID
            )
            
            # Step 2: HKDF with SHA3-256
            hkdf = HKDF(
                algorithm=hashes.SHA3_256(),
                length=CryptoUtils.HKDF_KEY_LEN,
                salt=salt,  # Use same salt for HKDF
                info=CryptoUtils.HKDF_INFO,
                backend=default_backend()
            )
            
            final_key = hkdf.derive(argon2_key)
            
            logger.info("Key derivation completed successfully")
            return final_key
            
        except Exception as e:
            logger.error(f"Key derivation failed: {e}")
            raise Exception(f"Key derivation failed: {str(e)}")
    
    @staticmethod
    def encrypt_private_key(private_key_data: bytes, password: str) -> Dict[str, Any]:
        """
        Encrypt private key data using AES-GCM with password-derived key
        Tối thiểu metadata để tránh leak thông tin
        
        Args:
            private_key_data: Raw private key data
            password: User password
            
        Returns:
            Dict containing only essential encrypted data
        """
        try:
            # Generate salt and derive key
            salt = CryptoUtils.generate_salt()
            encryption_key = CryptoUtils.derive_key_from_password(password, salt)
            
            # Generate nonce for AES-GCM
            nonce = os.urandom(CryptoUtils.GCM_NONCE_LEN)
            
            # Encrypt using AES-GCM
            aesgcm = AESGCM(encryption_key)
            ciphertext = aesgcm.encrypt(nonce, private_key_data, None)
            
            # Combine salt + nonce + ciphertext để giảm metadata
            # Format: [salt(16) + nonce(12) + ciphertext_with_tag]
            combined_data = salt + nonce + ciphertext
            
            logger.info("Private key encryption completed successfully")
            
            return {
                'encrypted_blob': combined_data,  # Chỉ 1 field thay vì nhiều fields
                'algorithm': 'AES-256-GCM'  # Minimal metadata
            }
            
        except Exception as e:
            logger.error(f"Private key encryption failed: {e}")
            raise Exception(f"Private key encryption failed: {str(e)}")
    
    @staticmethod
    def decrypt_private_key_from_blob(encrypted_blob: bytes, password: str) -> bytes:
        """
        Decrypt private key data from combined blob
        
        Args:
            encrypted_blob: Combined salt + nonce + ciphertext
            password: User password
            
        Returns:
            Decrypted private key data
        """
        try:
            # Extract components từ blob
            # Format: [salt(16) + nonce(12) + ciphertext_with_tag]
            if len(encrypted_blob) < CryptoUtils.ARGON2_SALT_LEN + CryptoUtils.GCM_NONCE_LEN + CryptoUtils.GCM_TAG_LEN:
                raise Exception("Invalid encrypted blob format")
            
            salt = encrypted_blob[:CryptoUtils.ARGON2_SALT_LEN]
            nonce = encrypted_blob[CryptoUtils.ARGON2_SALT_LEN:CryptoUtils.ARGON2_SALT_LEN + CryptoUtils.GCM_NONCE_LEN]
            ciphertext_with_tag = encrypted_blob[CryptoUtils.ARGON2_SALT_LEN + CryptoUtils.GCM_NONCE_LEN:]
            
            # Derive key from password and salt
            encryption_key = CryptoUtils.derive_key_from_password(password, salt)
            
            # Decrypt using AES-GCM
            aesgcm = AESGCM(encryption_key)
            private_key_data = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
            
            logger.info("Private key decryption completed successfully")
            return private_key_data
            
        except Exception as e:
            logger.error(f"Private key decryption failed: {e}")
            raise Exception(f"Private key decryption failed: {str(e)}")
    
    @staticmethod
    def verify_password_strength(password: str) -> Dict[str, Any]:
        """
        Verify password meets security requirements
        
        Args:
            password: Password to verify
            
        Returns:
            Dict with verification results
        """
        errors = []
        
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        
        if not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")
        
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Password must contain at least one special character")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }
