import os
import platform
import ctypes
import tempfile
import logging
from typing import List
from django.conf import settings
from crypto_access.services.vault_service import vault_service
import base64

logger = logging.getLogger(__name__)

class CPABEError(Exception):
    pass

class CPABEService:
    """Wrapper for libhybrid-cp-abe using ctypes"""
    
    def __init__(self):
        system = platform.system()
        if system == 'Windows':
            lib_name = 'libhybrid-cp-abe.dll'
        else:
            lib_name = 'libhybrid-cp-abe.so'
            
        self.dll_path = os.path.join(settings.BASE_DIR, 'lib', lib_name)
        self.keys_dir = os.path.join(settings.BASE_DIR, 'config', 'keys')
        self.msk_path = os.path.join(self.keys_dir, 'cpabe_msk.key')
        self.pk_path = os.path.join(self.keys_dir, 'cpabe_pk.key')
        
        # Load DLL
        try:
            self._lib = ctypes.CDLL(self.dll_path)
            self._setup_bindings()
            self._ensure_keys_exist()
        except Exception as e:
            logger.error(f"Failed to initialize CPABE library: {e}")
            self._lib = None
            
    def _setup_bindings(self):
        """Define C function signatures"""
        # int setup(const char *path)
        self._lib.setup.argtypes = [ctypes.c_char_p]
        self._lib.setup.restype = ctypes.c_int
        
        # int generateSecretKey(const char *masterKeyFile, const char *attributes, const char *privateKeyFile)
        self._lib.generateSecretKey.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
        self._lib.generateSecretKey.restype = ctypes.c_int
        
        # int AC17encrypt(const char *publicKeyFile, const char *plaintextFile, const char *policy, const char *ciphertextFile)
        self._encrypt_func = getattr(self._lib, 'AC17encrypt', getattr(self._lib, 'hybrid_cpabe_encrypt', None))
        if self._encrypt_func:
            self._encrypt_func.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
            self._encrypt_func.restype = ctypes.c_int
        
        # int hybrid_cpabe_decrypt(const char *privateKeyFile, const char *ciphertextFile, const char *recovertextFile)
        self._decrypt_func = getattr(self._lib, 'AC17decrypt', getattr(self._lib, 'hybrid_cpabe_decrypt', None))
        if self._decrypt_func:
            self._decrypt_func.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
            self._decrypt_func.restype = ctypes.c_int
            
        # Buffer-based Operations
        self._encrypt_buffer_func = getattr(self._lib, 'AC17encryptBuffer', getattr(self._lib, 'hybrid_cpabe_encryptBuffer', None))
        if self._encrypt_buffer_func:
            self._encrypt_buffer_func.argtypes = [
                ctypes.POINTER(ctypes.c_ubyte), ctypes.c_size_t, # publicKey, pkLen
                ctypes.POINTER(ctypes.c_ubyte), ctypes.c_size_t, # plaintext, ptLen
                ctypes.c_char_p,                                 # policy
                ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)), ctypes.POINTER(ctypes.c_size_t) # ciphertext, ctLen
            ]
            self._encrypt_buffer_func.restype = ctypes.c_int
            
        self._decrypt_buffer_func = getattr(self._lib, 'AC17decryptBuffer', getattr(self._lib, 'hybrid_cpabe_decryptBuffer', None))
        if self._decrypt_buffer_func:
            self._decrypt_buffer_func.argtypes = [
                ctypes.POINTER(ctypes.c_ubyte), ctypes.c_size_t, # privateKey, skLen
                ctypes.POINTER(ctypes.c_ubyte), ctypes.c_size_t, # ciphertext, ctLen
                ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)), ctypes.POINTER(ctypes.c_size_t) # plaintext, ptLen
            ]
            self._decrypt_buffer_func.restype = ctypes.c_int
            
        # void freeBuffer(unsigned char *buffer)
        if hasattr(self._lib, 'freeBuffer'):
            self._lib.freeBuffer.argtypes = [ctypes.POINTER(ctypes.c_ubyte)]
            self._lib.freeBuffer.restype = None
            
        # const char* getVersion(void)
        if hasattr(self._lib, 'getVersion'):
            self._lib.getVersion.argtypes = []
            self._lib.getVersion.restype = ctypes.c_char_p
        
        # const char* getErrorMessage(int errorCode)
        self._lib.getErrorMessage.argtypes = [ctypes.c_int]
        self._lib.getErrorMessage.restype = ctypes.c_char_p
        
    def _ensure_keys_exist(self):
        """Load CP-ABE keys from Vault (primary) or local backup (fallback), or generate new ones.
        After loading/generating, always saves a local backup for disaster recovery."""
        backup_dir = os.environ.get('KEYS_DIR', self.keys_dir)
        backup_msk = os.path.join(backup_dir, 'cpabe_msk.key')
        backup_pk = os.path.join(backup_dir, 'cpabe_pk.key')
        
        # 1. Try Vault (primary source)
        cpabe_msk_b64 = vault_service.get_secret('CPABE_MSK')
        cpabe_pk_b64 = vault_service.get_secret('CPABE_PK')
        
        if cpabe_msk_b64 and cpabe_pk_b64:
            logger.info("CP-ABE keys fetched from Vault.")
            self.msk_data = base64.b64decode(cpabe_msk_b64)
            self.pk_data = base64.b64decode(cpabe_pk_b64)
            self._save_backup(backup_dir, backup_msk, backup_pk)
            return

        # 2. Try local backup (fallback if Vault lost data)
        if os.path.exists(backup_msk) and os.path.exists(backup_pk):
            logger.warning("Vault has no CP-ABE keys. Restoring from local backup...")
            with open(backup_msk, 'rb') as f:
                self.msk_data = f.read()
            with open(backup_pk, 'rb') as f:
                self.pk_data = f.read()
            # Re-push to Vault to restore
            vault_service.put_secret('CPABE_MSK', base64.b64encode(self.msk_data).decode('utf-8'))
            vault_service.put_secret('CPABE_PK', base64.b64encode(self.pk_data).decode('utf-8'))
            logger.info("CP-ABE keys restored to Vault from local backup.")
            return

        # 3. Generate new keys (first-time setup)
        logger.info("Generating CP-ABE Master and Public keys...")
        
        # We must generate to disk first because C library expects path
        tmp_dir = tempfile.mkdtemp()
        res = self._lib.setup(tmp_dir.encode('utf-8'))
        if res != 0:
            err_msg = self._lib.getErrorMessage(res).decode('utf-8')
            raise CPABEError(f"Setup failed ({res}): {err_msg}")
            
        msk_path = os.path.join(tmp_dir, 'cpabe_msk.key')
        pk_path = os.path.join(tmp_dir, 'cpabe_pk.key')
        
        with open(msk_path, 'rb') as f:
            self.msk_data = f.read()
        with open(pk_path, 'rb') as f:
            self.pk_data = f.read()
            
        logger.info("Pushing CP-ABE keys to Vault...")
        vault_service.put_secret('CPABE_MSK', base64.b64encode(self.msk_data).decode('utf-8'))
        vault_service.put_secret('CPABE_PK', base64.b64encode(self.pk_data).decode('utf-8'))
        
        # Save local backup
        self._save_backup(backup_dir, backup_msk, backup_pk)
        
        # Clean up temp files
        os.remove(msk_path)
        os.remove(pk_path)
        os.rmdir(tmp_dir)
    
    def _save_backup(self, backup_dir, backup_msk, backup_pk):
        """Save CP-ABE keys to local backup directory for disaster recovery."""
        try:
            os.makedirs(backup_dir, exist_ok=True)
            with open(backup_msk, 'wb') as f:
                f.write(self.msk_data)
            with open(backup_pk, 'wb') as f:
                f.write(self.pk_data)
            logger.info(f"CP-ABE keys backed up to {backup_dir}")
        except Exception as e:
            logger.warning(f"Could not save CP-ABE key backup: {e}")
                
    def expand_hierarchical_attributes(self, attrs: dict) -> List[str]:
        """
        Convert ABAC attributes to CP-ABE string attributes.
        Also expands hierarchical attributes (e.g. top_secret -> secret, confidential)
        """
        result = []
        for key, value in attrs.items():
            if not value:
                continue
                
            if isinstance(value, list):
                for v in value:
                    result.append(f"{key}:{v}")
            else:
                result.append(f"{key}:{value}")
                
            # Hierarchical expansion for clearance_level
            if key == 'clearance_level':
                levels = ['public', 'confidential', 'secret', 'top_secret']
                try:
                    idx = levels.index(value)
                    # Add all levels below the current one
                    for i in range(idx):
                        result.append(f"clearance_level:{levels[i]}")
                except ValueError:
                    pass
                    
            # Hierarchical expansion for role
            if key == 'role':
                levels = ['intern', 'employee', 'manager', 'director']
                try:
                    idx = levels.index(value)
                    for i in range(idx):
                        result.append(f"role:{levels[i]}")
                except ValueError:
                    pass
                    
        return list(set(result))
        
    def generate_user_key(self, user_attributes: dict, output_path: str):
        """Generate a private key file for a user based on their attributes"""
        if not self._lib:
            raise CPABEError("Library not loaded")
            
        attr_strings = self.expand_hierarchical_attributes(user_attributes)
        attr_str = " ".join(attr_strings)
        logger.info(f"Generating Private Key with attributes: {attr_str}")
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp_msk:
            tmp_msk.write(self.msk_data)
            tmp_msk_path = tmp_msk.name
            
        try:
            res = self._lib.generateSecretKey(
                tmp_msk_path.encode('utf-8'),
                attr_str.encode('utf-8'),
                output_path.encode('utf-8')
            )
            
            if res != 0:
                err_msg = self._lib.getErrorMessage(res).decode('utf-8')
                raise CPABEError(f"Key generation failed ({res}): {err_msg}")
        finally:
            os.remove(tmp_msk_path)
            
    def encrypt_file(self, input_path: str, output_path: str, policy: str):
        """Encrypt a file using CP-ABE policy"""
        if not self._lib:
            raise CPABEError("Library not loaded")
            
        logger.info(f"Encrypting file with policy: {policy}")
        if not self._encrypt_func:
            raise CPABEError("Encryption function not found in library")
            
        with tempfile.NamedTemporaryFile(delete=False) as tmp_pk:
            tmp_pk.write(self.pk_data)
            tmp_pk_path = tmp_pk.name
            
        try:
            result = self._encrypt_func(
                tmp_pk_path.encode('utf-8'),
                input_path.encode('utf-8'),
                policy.encode('utf-8'),
                output_path.encode('utf-8')
            )
            
            if result != 0:
                err_msg = self._lib.getErrorMessage(result).decode('utf-8')
                raise CPABEError(f"Encryption failed ({result}): {err_msg}")
        finally:
            os.remove(tmp_pk_path)
            
    def decrypt_file(self, private_key_path: str, input_path: str, output_path: str):
        """Decrypt a file using a user's private key"""
        if not self._lib:
            raise CPABEError("Library not loaded")
            
        logger.info(f"Decrypting file with key: {private_key_path}")
        if not self._decrypt_func:
            raise CPABEError("Decryption function not found in library")
            
        result = self._decrypt_func(
            private_key_path.encode('utf-8'),
            input_path.encode('utf-8'),
            output_path.encode('utf-8')
        )
        
        if result != 0:
            err_msg = self._lib.getErrorMessage(result).decode('utf-8')
            raise CPABEError(f"Decryption failed ({result}): {err_msg}")

    def get_version(self) -> str:
        """Get the library version"""
        if hasattr(self._lib, 'getVersion'):
            return self._lib.getVersion().decode('utf-8')
        return "Unknown"

    def encrypt_buffer(self, plaintext: bytes, policy: str) -> bytes:
        """Encrypt data buffer directly in memory"""
        if not self._encrypt_buffer_func:
            raise CPABEError("Buffer encryption function not found in library")

        # Use memory public key data
        pk_data = self.pk_data

        pk_ptr = ctypes.cast(ctypes.create_string_buffer(pk_data), ctypes.POINTER(ctypes.c_ubyte))
        pt_ptr = ctypes.cast(ctypes.create_string_buffer(plaintext), ctypes.POINTER(ctypes.c_ubyte))
        
        ct_ptr = ctypes.POINTER(ctypes.c_ubyte)()
        ct_len = ctypes.c_size_t(0)

        result = self._encrypt_buffer_func(
            pk_ptr, len(pk_data),
            pt_ptr, len(plaintext),
            policy.encode('utf-8'),
            ctypes.byref(ct_ptr), ctypes.byref(ct_len)
        )

        if result != 0:
            err_msg = self._lib.getErrorMessage(result).decode('utf-8')
            raise CPABEError(f"Buffer encryption failed ({result}): {err_msg}")

        # Copy data out of C memory
        ciphertext = bytes(ct_ptr[:ct_len.value])
        
        # Free C memory
        if hasattr(self._lib, 'freeBuffer'):
            self._lib.freeBuffer(ct_ptr)
            
        return ciphertext

    def decrypt_buffer(self, private_key_data: bytes, ciphertext: bytes) -> bytes:
        """Decrypt data buffer directly in memory"""
        if not self._decrypt_buffer_func:
            raise CPABEError("Buffer decryption function not found in library")

        sk_data = private_key_data

        sk_ptr = ctypes.cast(ctypes.create_string_buffer(sk_data), ctypes.POINTER(ctypes.c_ubyte))
        ct_ptr = ctypes.cast(ctypes.create_string_buffer(ciphertext), ctypes.POINTER(ctypes.c_ubyte))
        
        pt_ptr = ctypes.POINTER(ctypes.c_ubyte)()
        pt_len = ctypes.c_size_t(0)

        result = self._decrypt_buffer_func(
            sk_ptr, len(sk_data),
            ct_ptr, len(ciphertext),
            ctypes.byref(pt_ptr), ctypes.byref(pt_len)
        )

        if result != 0:
            err_msg = self._lib.getErrorMessage(result).decode('utf-8')
            raise CPABEError(f"Buffer decryption failed ({result}): {err_msg}")

        # Copy data out of C memory
        plaintext = bytes(pt_ptr[:pt_len.value])
        
        # Free C memory
        if hasattr(self._lib, 'freeBuffer'):
            self._lib.freeBuffer(pt_ptr)
            
        return plaintext

# Singleton instance
cpabe_service = CPABEService()
