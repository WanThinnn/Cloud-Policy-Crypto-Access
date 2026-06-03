import os
import platform
import ctypes
import tempfile
import logging
from typing import List
from django.conf import settings

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
        self.msk_path = os.path.join(self.keys_dir, 'master_key.key')
        self.pk_path = os.path.join(self.keys_dir, 'public_key.key')
        
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
        self._lib.AC17encrypt.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
        self._lib.AC17encrypt.restype = ctypes.c_int
        
        # int AC17decrypt(const char *publicKeyFile, const char *privateKeyFile, const char *ciphertextFile, const char *recovertextFile)
        self._lib.AC17decrypt.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
        self._lib.AC17decrypt.restype = ctypes.c_int
        
        # const char* getErrorMessage(int errorCode)
        self._lib.getErrorMessage.argtypes = [ctypes.c_int]
        self._lib.getErrorMessage.restype = ctypes.c_char_p
        
    def _ensure_keys_exist(self):
        """Run setup to generate master and public keys if they don't exist"""
        if not os.path.exists(self.keys_dir):
            os.makedirs(self.keys_dir)
            
        if not os.path.exists(self.msk_path) or not os.path.exists(self.pk_path):
            logger.info("Generating CP-ABE Master and Public keys...")
            res = self._lib.setup(self.keys_dir.encode('utf-8'))
            if res != 0:
                err_msg = self._lib.getErrorMessage(res).decode('utf-8')
                raise CPABEError(f"Setup failed ({res}): {err_msg}")
                
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
        
        res = self._lib.generateSecretKey(
            self.msk_path.encode('utf-8'),
            attr_str.encode('utf-8'),
            output_path.encode('utf-8')
        )
        
        if res != 0:
            err_msg = self._lib.getErrorMessage(res).decode('utf-8')
            raise CPABEError(f"Key generation failed ({res}): {err_msg}")
            
    def encrypt_file(self, input_path: str, output_path: str, policy: str):
        """Encrypt a file using CP-ABE policy"""
        if not self._lib:
            raise CPABEError("Library not loaded")
            
        logger.info(f"Encrypting file with policy: {policy}")
        res = self._lib.AC17encrypt(
            self.pk_path.encode('utf-8'),
            input_path.encode('utf-8'),
            policy.encode('utf-8'),
            output_path.encode('utf-8')
        )
        
        if res != 0:
            err_msg = self._lib.getErrorMessage(res).decode('utf-8')
            raise CPABEError(f"Encryption failed ({res}): {err_msg}")
            
    def decrypt_file(self, private_key_path: str, input_path: str, output_path: str):
        """Decrypt a file using a user's private key"""
        if not self._lib:
            raise CPABEError("Library not loaded")
            
        logger.info(f"Decrypting file with key: {private_key_path}")
        res = self._lib.AC17decrypt(
            self.pk_path.encode('utf-8'),
            private_key_path.encode('utf-8'),
            input_path.encode('utf-8'),
            output_path.encode('utf-8')
        )
        
        if res != 0:
            err_msg = self._lib.getErrorMessage(res).decode('utf-8')
            raise CPABEError(f"Decryption failed ({res}): {err_msg}")

# Singleton instance
cpabe_service = CPABEService()
