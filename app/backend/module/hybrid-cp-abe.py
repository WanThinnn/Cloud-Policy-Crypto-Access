"""
ABE Library wrapper for Hybrid CP-ABE operations
"""
import ctypes
from ctypes import c_char_p
import os
import logging
import traceback
from config import Config

logger = logging.getLogger(__name__)

class ABELibrary:
    """Wrapper class for ABE library operations"""
    
    def __init__(self):
        self.abe_lib = None
        self.library_loaded = False
        self.lib_path = ""
        self.load_library()
    
    def load_library(self):
        """Load the ABE library"""
        try:
            self.lib_path = Config.get_library_path()
            
            if not os.path.exists(self.lib_path):
                raise Exception(f"Library file not found: {self.lib_path}")
            
            self.abe_lib = ctypes.CDLL(self.lib_path)
            self._setup_function_prototypes()
            
            self.library_loaded = True
            logger.info(f"Successfully loaded library: {self.lib_path}")
            return True
            
        except Exception as e:
            self.library_loaded = False
            logger.error(f"Failed to load library: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def _setup_function_prototypes(self):
        """Setup function prototypes for the C++ library"""
        # Setup function
        self.abe_lib.setup.argtypes = [c_char_p]
        self.abe_lib.setup.restype = None
        
        # Generate secret key function
        self.abe_lib.generateSecretKey.argtypes = [c_char_p, c_char_p, c_char_p, c_char_p]
        self.abe_lib.generateSecretKey.restype = None
        
        # Encrypt function
        self.abe_lib.AC17encrypt.argtypes = [c_char_p, c_char_p, c_char_p, c_char_p]
        self.abe_lib.AC17encrypt.restype = None
        
        # Decrypt function
        self.abe_lib.AC17decrypt.argtypes = [c_char_p, c_char_p, c_char_p, c_char_p]
        self.abe_lib.AC17decrypt.restype = None
    
    def is_loaded(self):
        """Check if library is loaded"""
        return self.library_loaded
    
    def get_lib_path(self):
        """Get library path"""
        return self.lib_path
    
    def setup(self, setup_dir):
        """Setup ABE system"""
        if not self.library_loaded:
            raise Exception("ABE library not loaded")
        
        self.abe_lib.setup(setup_dir.encode('utf-8'))
        logger.info(f"ABE setup completed at: {setup_dir}")
    
    def generate_secret_key(self, public_key_path, master_key_path, attributes, private_key_path):
        """Generate secret key"""
        if not self.library_loaded:
            raise Exception("ABE library not loaded")
        
        self.abe_lib.generateSecretKey(
            public_key_path.encode('utf-8'),
            master_key_path.encode('utf-8'),
            attributes.encode('utf-8'),
            private_key_path.encode('utf-8')
        )
        logger.info(f"Secret key generated: {private_key_path}")
    
    def encrypt(self, public_key_path, plaintext_path, policy, ciphertext_path):
        """Encrypt data"""
        if not self.library_loaded:
            raise Exception("ABE library not loaded")
        
        self.abe_lib.AC17encrypt(
            public_key_path.encode('utf-8'),
            plaintext_path.encode('utf-8'),
            policy.encode('utf-8'),
            ciphertext_path.encode('utf-8')
        )
        logger.info(f"Encryption completed: {ciphertext_path}")
    
    def decrypt(self, public_key_path, private_key_path, ciphertext_path, recovertext_path):
        """Decrypt data"""
        if not self.library_loaded:
            raise Exception("ABE library not loaded")
        
        self.abe_lib.AC17decrypt(
            public_key_path.encode('utf-8'),
            private_key_path.encode('utf-8'),
            ciphertext_path.encode('utf-8'),
            recovertext_path.encode('utf-8')
        )
        logger.info(f"Decryption completed: {recovertext_path}")

# Global ABE library instance
abe_lib = ABELibrary()
