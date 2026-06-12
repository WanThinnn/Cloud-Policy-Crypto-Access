import base64
import json
import os
import hashlib
import hmac
import threading
from django.db import models
from django.conf import settings
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidTag

import logging

logger = logging.getLogger(__name__)

_derived_keys_cache = {}
_cache_lock = threading.Lock()

def get_encryption_key(info: bytes = b"") -> bytes:
    """Retrieve the 256-bit AES key from Vault or settings, and derive a sub-key."""
    try:
        from crypto_access.services.vault_service import vault_service
        key_b64 = vault_service.get_secret('FIELD_ENCRYPTION_KEY')
        if not key_b64:
            key_b64 = getattr(settings, 'FIELD_ENCRYPTION_KEY', None)
    except Exception as e:
        logger.warning(f"Failed to fetch key from Vault, falling back to settings: {e}")
        key_b64 = getattr(settings, 'FIELD_ENCRYPTION_KEY', None)

    if not key_b64:
        key_b64 = os.environ.get('FIELD_ENCRYPTION_KEY')
    
    if not key_b64:
        raise ValueError("FIELD_ENCRYPTION_KEY is not set in Vault, environment or settings.")
        
    try:
        master_key = base64.urlsafe_b64decode(key_b64)
        if len(master_key) != 32:
            raise ValueError(f"AES key must be 32 bytes (256 bits). Got {len(master_key)} bytes.")
            
        if not info:
            return master_key
            
        # Derive specific key using HKDF for Blast Radius isolation
        cache_key = info
        with _cache_lock:
            if cache_key in _derived_keys_cache:
                return _derived_keys_cache[cache_key]
                
            hkdf = HKDF(
                algorithm=hashes.SHA3_256(),
                length=32,
                salt=b"cyberfortress_static_salt_v1", 
                info=info,
            )
            derived_key = hkdf.derive(master_key)
            _derived_keys_cache[cache_key] = derived_key
            return derived_key
            
    except Exception as e:
        raise ValueError(f"Invalid FIELD_ENCRYPTION_KEY format: {e}")

class EncryptedFieldMixin:
    """Mixin to handle AES-GCM encryption for Django model fields with HKDF."""
    
    def _get_hkdf_info(self) -> bytes:
        table_name = getattr(self.model._meta, 'db_table', 'unknown_table') if getattr(self, 'model', None) else "unknown_table"
        column_name = getattr(self, 'name', 'unknown_column')
        return f"{table_name}.{column_name}".encode('utf-8')
        
    def encrypt_data(self, data: bytes, aad: bytes = None) -> str:
        if not getattr(settings, 'FIELD_ENCRYPTION', False):
            return data.decode('utf-8')
            
        info = self._get_hkdf_info()
        key = get_encryption_key(info)
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)  # 96-bit nonce is standard for AES-GCM
        ciphertext = aesgcm.encrypt(nonce, data, aad)
        # Store as base64 string with ENC: prefix
        return "ENC:" + base64.urlsafe_b64encode(nonce + ciphertext).decode('utf-8')

    def decrypt_data(self, encrypted_string: str, aad: bytes = None) -> bytes:
        if not encrypted_string:
            return b""
            
        info = self._get_hkdf_info()
        
        if encrypted_string.startswith("ENC:"):
            # New format
            b64_string = encrypted_string[4:]
            try:
                key = get_encryption_key(info)
                aesgcm = AESGCM(key)
                encrypted_data = base64.urlsafe_b64decode(b64_string.encode('utf-8'))
                nonce = encrypted_data[:12]
                ciphertext = encrypted_data[12:]
                return aesgcm.decrypt(nonce, ciphertext, aad)
            except InvalidTag:
                # Fallback: maybe it was encrypted before we added AAD support
                if aad is not None:
                    try:
                        return aesgcm.decrypt(nonce, ciphertext, None)
                    except Exception:
                        pass
                raise ValueError("Data corruption, invalid key, or AAD mismatch for ENC: prefixed data.")
            except Exception as e:
                raise ValueError(f"Data corruption or invalid key for ENC: prefixed data: {e}")
        
        # Fallback for data encrypted without ENC: prefix or plaintext data
        try:
            key = get_encryption_key(info)
            aesgcm = AESGCM(key)
            encrypted_data = base64.urlsafe_b64decode(encrypted_string.encode('utf-8'))
            nonce = encrypted_data[:12]
            ciphertext = encrypted_data[12:]
            return aesgcm.decrypt(nonce, ciphertext, aad)
        except InvalidTag:
            if aad is not None:
                try:
                    return aesgcm.decrypt(nonce, ciphertext, None)
                except Exception:
                    pass
            return encrypted_string.encode('utf-8')
        except Exception:
            # If it's not base64 or decryption fails, assume it's plaintext
            return encrypted_string.encode('utf-8')

class EncryptedCharField(EncryptedFieldMixin, models.CharField):
    """A CharField that automatically encrypts its content using AES-GCM."""
    
    def get_internal_type(self):
        # We need a longer field to store the base64 encoded ciphertext + nonce + auth tag
        return "TextField"
        
    def get_db_prep_value(self, value, connection, prepared=False):
        value = super().get_db_prep_value(value, connection, prepared)
        if value is not None and value != '':
            aad = self.name.encode('utf-8') if getattr(self, 'name', None) else None
            return self.encrypt_data(str(value).encode('utf-8'), aad=aad)
        return value

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        try:
            aad = self.name.encode('utf-8') if getattr(self, 'name', None) else None
            decrypted_bytes = self.decrypt_data(value, aad=aad)
            return decrypted_bytes.decode('utf-8')
        except Exception:
            return value # Return original if decryption fails (e.g. legacy plaintext data)

    def to_python(self, value):
        # to_python is called during deserialization and form cleaning
        if value is None:
            return value
        # If it's already a decrypted string (not looking like base64 of our format), just return it
        # This is a simple heuristic. A better approach is handling it carefully.
        return super().to_python(value)

class EncryptedJSONField(EncryptedFieldMixin, models.JSONField):
    """A JSONField that encrypts its content before saving to the DB."""
    
    def get_internal_type(self):
        return "TextField"
        
    def get_db_prep_value(self, value, connection, prepared=False):
        if value is None:
            return value
        # Serialize JSON to string then encrypt
        json_string = json.dumps(value)
        aad = self.name.encode('utf-8') if getattr(self, 'name', None) else None
        return self.encrypt_data(json_string.encode('utf-8'), aad=aad)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        try:
            aad = self.name.encode('utf-8') if getattr(self, 'name', None) else None
            decrypted_bytes = self.decrypt_data(value, aad=aad)
            return json.loads(decrypted_bytes.decode('utf-8'))
        except Exception:
            # Try to parse as normal JSON if decryption fails
            try:
                return json.loads(value)
            except:
                return value

class BlindIndexField(models.CharField):
    """
    A field that automatically calculates an HMAC-SHA3-256 hash of another field.
    Used for searching securely without decrypting the data.
    """
    def __init__(self, *args, source_field=None, **kwargs):
        self.source_field = source_field
        kwargs['max_length'] = 64  # SHA3-256 hex digest length
        kwargs['editable'] = False
        kwargs['blank'] = True
        kwargs['null'] = True
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.source_field:
            kwargs['source_field'] = self.source_field
        return name, path, args, kwargs

    def pre_save(self, model_instance, add):
        """Calculate the hash before saving."""
        if not self.source_field:
            return None
            
        source_value = getattr(model_instance, self.source_field)
        if source_value is None or source_value == '':
            return ''
            
        # Use master key for blind index (or derive a specific blind index key)
        # Using master key to ensure consistency
        key = get_encryption_key(info=b"blind_index")
        # Using SHA3-256 as explicitly requested by user
        h = hmac.new(key, str(source_value).encode('utf-8'), hashlib.sha3_256)
        hash_value = h.hexdigest()
        
        setattr(model_instance, self.attname, hash_value)
        return hash_value
