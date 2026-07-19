import os
import platform
import ctypes
import tempfile
import logging
from typing import List
from django.conf import settings
from crypto_access.services.vault_service import vault_service
import base64
import requests
import urllib3

logger = logging.getLogger(__name__)

class CPABEError(Exception):
    pass

class CPABEService:
    """Wrapper for libhybrid-cp-abe using ctypes"""
    
    def __init__(self):
        self.use_vault_plugin = getattr(settings, 'USE_VAULT_ABE_PLUGIN', False)
        
        system = platform.system()
        if system == 'Windows':
            lib_name = 'libhybrid-pq-cp-abe.dll'
        else:
            lib_name = 'libhybrid-pq-cp-abe.so'
            
        self.dll_path = os.path.join(settings.BASE_DIR, 'lib', lib_name)
        self.keys_dir = os.path.join(settings.BASE_DIR, 'config', 'keys')
        self.msk_path = os.path.join(self.keys_dir, 'cpabe_msk.key')
        self.pk_path = os.path.join(self.keys_dir, 'cpabe_pk.key')
        self.pqc_sk_path = os.path.join(self.keys_dir, 'pqc_sk.key')
        self.pqc_pk_path = os.path.join(self.keys_dir, 'pqc_pk.key')
        
        self._lib = None
        if not self.use_vault_plugin:
            try:
                self._lib = ctypes.CDLL(self.dll_path)
                self._setup_bindings()
            except Exception as e:
                logger.error(f"Failed to initialize CPABE library: {e}")
                
        # Vault CA cert for TLS verification on plugin API calls
        vault_ca = os.environ.get('VAULT_CACERT')
        self._vault_verify = vault_ca if (vault_ca and os.path.exists(vault_ca)) else True

        self._ensure_keys_exist()
            
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
            
        # PQC functions
        self._setup_pqc_func = getattr(self._lib, 'hybrid_cpabe_setup_with_pqc', None)
        if self._setup_pqc_func:
            self._setup_pqc_func.argtypes = [ctypes.c_char_p]
            self._setup_pqc_func.restype = ctypes.c_int

        self._encrypt_buffer_sign_func = getattr(self._lib, 'hybrid_cpabe_encryptBuffer_and_sign', None)
        if self._encrypt_buffer_sign_func:
            self._encrypt_buffer_sign_func.argtypes = [
                ctypes.POINTER(ctypes.c_ubyte), ctypes.c_size_t, # publicKey, pkLen
                ctypes.POINTER(ctypes.c_ubyte), ctypes.c_size_t, # masterKey, mskLen
                ctypes.POINTER(ctypes.c_ubyte), ctypes.c_size_t, # plaintext, ptLen
                ctypes.c_char_p,                                 # policy
                ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)), ctypes.POINTER(ctypes.c_size_t) # ciphertext, ctLen
            ]
            self._encrypt_buffer_sign_func.restype = ctypes.c_int

        self._decrypt_buffer_verify_func = getattr(self._lib, 'hybrid_cpabe_decryptBuffer_and_verify', None)
        if self._decrypt_buffer_verify_func:
            self._decrypt_buffer_verify_func.argtypes = [
                ctypes.POINTER(ctypes.c_ubyte), ctypes.c_size_t, # privateKey, skLen
                ctypes.POINTER(ctypes.c_ubyte), ctypes.c_size_t, # publicKey, pkLen
                ctypes.POINTER(ctypes.c_ubyte), ctypes.c_size_t, # ciphertext, ctLen
                ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)), ctypes.POINTER(ctypes.c_size_t) # plaintext, ptLen
            ]
            self._decrypt_buffer_verify_func.restype = ctypes.c_int
            
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
        from django.conf import settings
        
        if self.use_vault_plugin:
            is_pqc_enabled = getattr(settings, 'ENABLE_PQC_FEATURES', False)
            current_scheme = getattr(settings, 'CPABE_SCHEME', 'ac17')
            
            headers = {"X-Vault-Token": vault_service.get_token, "Content-Type": "application/json"}
            
            # Setup AC17
            ac17_pk_b64 = vault_service.get_secret('CPABE_PK_AC17')
            if not ac17_pk_b64:
                logger.info("Initializing Vault ABE Plugin (AC17)...")
                try:
                    payload = {"scheme": "ac17", "pqc": is_pqc_enabled}
                    resp = requests.put(f"{vault_service.get_addr}/v1/abe_ac17/setup", headers=headers, json=payload, verify=self._vault_verify)
                    resp.raise_for_status()
                    data = resp.json()["data"]
                    vault_service.put_secret('CPABE_PK_AC17', data["public_key"])
                    ac17_pk_b64 = data["public_key"]
                    if is_pqc_enabled:
                        vault_service.put_secret('PQC_PK_AC17', data["pqc_public_key"])
                except Exception as e:
                    logger.error(f"Failed to initialize Vault ABE Plugin (AC17): {e}")

            # Setup TKN20
            tkn20_pk_b64 = vault_service.get_secret('CPABE_PK_TKN20')
            if not tkn20_pk_b64:
                logger.info("Initializing Vault ABE Plugin (TKN20)...")
                try:
                    payload = {"scheme": "tkn20", "pqc": is_pqc_enabled}
                    resp = requests.put(f"{vault_service.get_addr}/v1/abe_tkn20/setup", headers=headers, json=payload, verify=self._vault_verify)
                    resp.raise_for_status()
                    data = resp.json()["data"]
                    vault_service.put_secret('CPABE_PK_TKN20', data["public_key"])
                    tkn20_pk_b64 = data["public_key"]
                    if is_pqc_enabled:
                        vault_service.put_secret('PQC_PK_TKN20', data["pqc_public_key"])
                except Exception as e:
                    logger.error(f"Failed to initialize Vault ABE Plugin (TKN20): {e}")

            # Set self.pk_data to current scheme's PK just in case it's read by the frontend/API
            if current_scheme == 'tkn20' and tkn20_pk_b64:
                self.pk_data = base64.b64decode(tkn20_pk_b64)
            elif ac17_pk_b64:
                self.pk_data = base64.b64decode(ac17_pk_b64)

            logger.info("CP-ABE keys (Vault Plugin Mode) verified/initialized for dual-scheme.")
            return
            
        # Legacy ctypes mode below
        is_pqc_enabled = getattr(settings, 'ENABLE_PQC_FEATURES', False) and bool(getattr(self, '_setup_pqc_func', None))
        
        backup_dir = os.environ.get('KEYS_DIR', self.keys_dir)
        backup_msk = os.path.join(backup_dir, 'cpabe_msk.key')
        backup_pk = os.path.join(backup_dir, 'cpabe_pk.key')
        backup_pqc_sk = os.path.join(backup_dir, 'pqc_sk.key')
        backup_pqc_pk = os.path.join(backup_dir, 'pqc_pk.key')
        
        # 1. Fetch from Vault
        cpabe_msk_b64 = vault_service.get_secret('CPABE_MSK')
        cpabe_pk_b64 = vault_service.get_secret('CPABE_PK')
        pqc_sk_b64 = vault_service.get_secret('PQC_SK')
        pqc_pk_b64 = vault_service.get_secret('PQC_PK')
        
        has_vault_keys = cpabe_msk_b64 and cpabe_pk_b64
        has_backup_keys = os.path.exists(backup_msk) and os.path.exists(backup_pk)
        
        if is_pqc_enabled:
            has_vault_keys = has_vault_keys and pqc_sk_b64 and pqc_pk_b64
            has_backup_keys = has_backup_keys and os.path.exists(backup_pqc_sk) and os.path.exists(backup_pqc_pk)

        # Split-brain check: Mismatch between Vault and Local Backup
        if has_vault_keys and has_backup_keys:
            vault_msk = base64.b64decode(cpabe_msk_b64)
            with open(backup_msk, 'rb') as f:
                local_msk = f.read()
                
            if vault_msk != local_msk:
                err_msg = "CRITICAL ERROR: CP-ABE Key mismatch between Vault and local backup! System halted to prevent data loss. Please manually resolve this conflict."
                logger.critical(err_msg)
                raise CPABEError(err_msg)
                
            logger.info("CP-ABE keys fetched from Vault (matches local backup).")
            self.msk_data = vault_msk
            self.pk_data = base64.b64decode(cpabe_pk_b64)
            if is_pqc_enabled:
                self.pqc_sk_data = base64.b64decode(pqc_sk_b64)
                self.pqc_pk_data = base64.b64decode(pqc_pk_b64)
            return

        # Vault has keys, but no backup exists
        if has_vault_keys:
            logger.info("CP-ABE keys fetched from Vault. Saving new local backup...")
            self.msk_data = base64.b64decode(cpabe_msk_b64)
            self.pk_data = base64.b64decode(cpabe_pk_b64)
            if is_pqc_enabled:
                self.pqc_sk_data = base64.b64decode(pqc_sk_b64)
                self.pqc_pk_data = base64.b64decode(pqc_pk_b64)
            self._save_backup(backup_dir, backup_msk, backup_pk, backup_pqc_sk, backup_pqc_pk, is_pqc_enabled)
            return

        # Backup has keys, but Vault is empty
        if has_backup_keys:
            logger.warning("Vault has no CP-ABE keys. Restoring from local backup...")
            with open(backup_msk, 'rb') as f:
                self.msk_data = f.read()
            with open(backup_pk, 'rb') as f:
                self.pk_data = f.read()
            vault_service.put_secret('CPABE_MSK', base64.b64encode(self.msk_data).decode('utf-8'))
            vault_service.put_secret('CPABE_PK', base64.b64encode(self.pk_data).decode('utf-8'))
            
            if is_pqc_enabled:
                with open(backup_pqc_sk, 'rb') as f:
                    self.pqc_sk_data = f.read()
                with open(backup_pqc_pk, 'rb') as f:
                    self.pqc_pk_data = f.read()
                vault_service.put_secret('PQC_SK', base64.b64encode(self.pqc_sk_data).decode('utf-8'))
                vault_service.put_secret('PQC_PK', base64.b64encode(self.pqc_pk_data).decode('utf-8'))
                
            logger.info("CP-ABE keys restored to Vault from local backup.")
            return

        # 3. Generate new keys (first-time setup or overwrite requested due to missing keys)
        logger.info("Generating CP-ABE Master and Public keys...")
        
        # We must generate to disk first because C library expects path
        tmp_dir = tempfile.mkdtemp()
        
        if is_pqc_enabled:
            logger.info("PQC features enabled. Generating ML-DSA keys along with CP-ABE keys...")
            res = self._setup_pqc_func(tmp_dir.encode('utf-8'))
        else:
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
        os.remove(msk_path)
        os.remove(pk_path)
        
        if is_pqc_enabled:
            pqc_sk_tmp_path = os.path.join(tmp_dir, 'pqc_sk.key')
            pqc_pk_tmp_path = os.path.join(tmp_dir, 'pqc_pk.key')
            with open(pqc_sk_tmp_path, 'rb') as f:
                self.pqc_sk_data = f.read()
            with open(pqc_pk_tmp_path, 'rb') as f:
                self.pqc_pk_data = f.read()
            vault_service.put_secret('PQC_SK', base64.b64encode(self.pqc_sk_data).decode('utf-8'))
            vault_service.put_secret('PQC_PK', base64.b64encode(self.pqc_pk_data).decode('utf-8'))
            os.remove(pqc_sk_tmp_path)
            os.remove(pqc_pk_tmp_path)
        
        # Save local backup
        self._save_backup(backup_dir, backup_msk, backup_pk, backup_pqc_sk, backup_pqc_pk, is_pqc_enabled)
        
        # Clean up temp files
        os.rmdir(tmp_dir)

    def _save_backup(self, backup_dir, backup_msk, backup_pk, backup_pqc_sk, backup_pqc_pk, is_pqc_enabled):
        """Save CP-ABE keys to local backup directory for disaster recovery."""
        try:
            os.makedirs(backup_dir, exist_ok=True)
            with open(backup_msk, 'wb') as f:
                f.write(self.msk_data)
            with open(backup_pk, 'wb') as f:
                f.write(self.pk_data)
                
            if is_pqc_enabled:
                with open(backup_pqc_sk, 'wb') as f:
                    f.write(self.pqc_sk_data)
                with open(backup_pqc_pk, 'wb') as f:
                    f.write(self.pqc_pk_data)
                    
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
        
    def generate_user_key(self, user_attributes: dict, output_path: str, scheme: str = None):
        """Generate a private key file for a user based on their attributes"""
        if scheme is None:
            scheme = getattr(settings, 'CPABE_SCHEME', 'ac17')
            
        attr_strings = self.expand_hierarchical_attributes(user_attributes)
        attr_str = " ".join(attr_strings)
        logger.info(f"Generating Private Key (Scheme: {scheme}) with attributes: {attr_str}")
        
        if self.use_vault_plugin:
            headers = {"X-Vault-Token": vault_service.get_token, "Content-Type": "application/json"}
            payload = {"scheme": scheme, "attributes": attr_str}
            endpoint = f"/v1/abe_{scheme}/genkey"
            try:
                resp = requests.put(f"{vault_service.get_addr}{endpoint}", headers=headers, json=payload, verify=self._vault_verify)
                resp.raise_for_status()
                sk_b64 = resp.json()["data"]["secret_key"]
                with open(output_path, 'wb') as f:
                    f.write(base64.b64decode(sk_b64))
                return
            except Exception as e:
                raise CPABEError(f"Vault ABE Plugin GenKey ({scheme}) failed: {e}")

        if not self._lib:
            raise CPABEError("Library not loaded")
        
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

    def encrypt_buffer(self, plaintext: bytes, policy: str, scheme: str = None) -> bytes:
        """Encrypt data buffer directly in memory"""
        if scheme is None:
            scheme = getattr(settings, 'CPABE_SCHEME', 'ac17')
            
        if self.use_vault_plugin:
            headers = {"X-Vault-Token": vault_service.get_token, "Content-Type": "application/json"}
            pk_b64 = vault_service.get_secret(f'CPABE_PK_{scheme.upper()}') or base64.b64encode(self.pk_data).decode('utf-8')
            
            payload = {
                "scheme": scheme,
                "plaintext": base64.b64encode(plaintext).decode('utf-8'),
                "policy": policy,
                "public_key": pk_b64
            }
            try:
                resp = requests.put(f"{vault_service.get_addr}/v1/abe_{scheme}/encrypt", headers=headers, json=payload, verify=self._vault_verify)
                resp.raise_for_status()
                return base64.b64decode(resp.json()["data"]["ciphertext"])
            except Exception as e:
                raise CPABEError(f"Vault ABE Plugin encrypt ({scheme}) failed: {e}")

        if not self._encrypt_buffer_func:
            raise CPABEError("Buffer encryption function not found in library")

        pk_json = base64.b64decode(self.pk_data)

        pk_ptr = ctypes.cast(ctypes.create_string_buffer(pk_json), ctypes.POINTER(ctypes.c_ubyte))
        pt_ptr = ctypes.cast(ctypes.create_string_buffer(plaintext), ctypes.POINTER(ctypes.c_ubyte))
        
        ct_ptr = ctypes.POINTER(ctypes.c_ubyte)()
        ct_len = ctypes.c_size_t(0)

        result = self._encrypt_buffer_func(
            pk_ptr, len(pk_json),
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

    def decrypt_buffer(self, private_key_data: bytes, ciphertext: bytes, scheme: str = None) -> bytes:
        """Decrypt data buffer directly in memory"""
        if scheme is None:
            scheme = getattr(settings, 'CPABE_SCHEME', 'ac17')
            
        if self.use_vault_plugin:
            headers = {"X-Vault-Token": vault_service.get_token, "Content-Type": "application/json"}
            pk_b64 = vault_service.get_secret(f'CPABE_PK_{scheme.upper()}') or base64.b64encode(self.pk_data).decode('utf-8')
            payload = {
                "scheme": scheme,
                "ciphertext": base64.b64encode(ciphertext).decode('utf-8'),
                "secret_key": base64.b64encode(private_key_data).decode('utf-8'),
                "public_key": pk_b64
            }
            try:
                resp = requests.put(f"{vault_service.get_addr}/v1/abe_{scheme}/decrypt", headers=headers, json=payload, verify=self._vault_verify)
                resp.raise_for_status()
                return base64.b64decode(resp.json()["data"]["plaintext"])
            except Exception as e:
                raise CPABEError(f"Vault ABE Plugin decrypt ({scheme}) failed: {e}")

        if not self._decrypt_buffer_func:
            raise CPABEError("Buffer decryption function not found in library")

        sk_json = base64.b64decode(private_key_data)

        sk_ptr = ctypes.cast(ctypes.create_string_buffer(sk_json), ctypes.POINTER(ctypes.c_ubyte))
        ct_ptr = ctypes.cast(ctypes.create_string_buffer(ciphertext), ctypes.POINTER(ctypes.c_ubyte))
        
        pt_ptr = ctypes.POINTER(ctypes.c_ubyte)()
        pt_len = ctypes.c_size_t(0)

        result = self._decrypt_buffer_func(
            sk_ptr, len(sk_json),
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

    def encrypt_buffer_and_sign(self, plaintext: bytes, policy: str, scheme: str = None) -> bytes:
        self._ensure_keys_exist()
        if scheme is None:
            scheme = getattr(settings, 'CPABE_SCHEME', 'ac17')
        
        if self.use_vault_plugin:
            headers = {"X-Vault-Token": vault_service.get_token, "Content-Type": "application/json"}
            pk_b64 = vault_service.get_secret(f'CPABE_PK_{scheme.upper()}') or base64.b64encode(self.pk_data).decode('utf-8')
            
            payload = {
                "scheme": scheme,
                "plaintext": base64.b64encode(plaintext).decode('utf-8'),
                "policy": policy,
                "public_key": pk_b64
            }
            try:
                resp = requests.put(f"{vault_service.get_addr}/v1/abe_{scheme}/encrypt", headers=headers, json=payload, verify=self._vault_verify)
                resp.raise_for_status()
                return base64.b64decode(resp.json()["data"]["ciphertext"])
            except Exception as e:
                raise CPABEError(f"Vault ABE Plugin PQC encrypt ({scheme}) failed: {e}")

        if not getattr(self, '_encrypt_buffer_sign_func', None):
            raise CPABEError("PQC encryptBuffer_and_sign function not found in DLL")

        pk_json = base64.b64decode(self.pk_data)
        pqc_sk_json = base64.b64decode(self.pqc_sk_data)
        
        pk_ptr = ctypes.cast(ctypes.create_string_buffer(pk_json), ctypes.POINTER(ctypes.c_ubyte))
        pqc_sk_ptr = ctypes.cast(ctypes.create_string_buffer(pqc_sk_json), ctypes.POINTER(ctypes.c_ubyte))
        pt_ptr = ctypes.cast(ctypes.create_string_buffer(plaintext), ctypes.POINTER(ctypes.c_ubyte))
        
        ct_ptr = ctypes.POINTER(ctypes.c_ubyte)()
        ct_len = ctypes.c_size_t(0)
        
        result = self._encrypt_buffer_sign_func(
            pk_ptr, len(pk_json),
            pqc_sk_ptr, len(pqc_sk_json),
            pt_ptr, len(plaintext),
            policy.encode('utf-8'),
            ctypes.byref(ct_ptr), ctypes.byref(ct_len)
        )

        if result != 0:
            err_msg = self._lib.getErrorMessage(result).decode('utf-8')
            raise CPABEError(f"Buffer PQC encryption failed ({result}): {err_msg}")

        ciphertext = bytes(ct_ptr[:ct_len.value])
        if hasattr(self._lib, 'freeBuffer'):
            self._lib.freeBuffer(ct_ptr)
            
        return ciphertext

    def decrypt_buffer_and_verify(self, sk_data: bytes, ciphertext: bytes, scheme: str = None) -> bytes:
        self._ensure_keys_exist()
        if scheme is None:
            scheme = getattr(settings, 'CPABE_SCHEME', 'ac17')
        
        if self.use_vault_plugin:
            headers = {"X-Vault-Token": vault_service.get_token, "Content-Type": "application/json"}
            pqc_pk_b64 = vault_service.get_secret(f'PQC_PK_{scheme.upper()}') or base64.b64encode(self.pqc_pk_data).decode('utf-8')
            pk_b64 = vault_service.get_secret(f'CPABE_PK_{scheme.upper()}') or base64.b64encode(self.pk_data).decode('utf-8')
            
            payload = {
                "scheme": scheme,
                "ciphertext": base64.b64encode(ciphertext).decode('utf-8'),
                "secret_key": base64.b64encode(sk_data).decode('utf-8'),
                "pqc_public_key": pqc_pk_b64,
                "public_key": pk_b64
            }
            try:
                resp = requests.put(f"{vault_service.get_addr}/v1/abe_{scheme}/decrypt", headers=headers, json=payload, verify=self._vault_verify)
                resp.raise_for_status()
                return base64.b64decode(resp.json()["data"]["plaintext"])
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 400 or e.response.status_code == 403:
                    raise CPABEError("Decryption failed or signature invalid (unauthorized)")
                raise CPABEError(f"Vault ABE Plugin PQC decrypt ({scheme}) failed: {e}")
            except Exception as e:
                raise CPABEError(f"Vault ABE Plugin PQC decrypt ({scheme}) failed: {e}")

        if not getattr(self, '_decrypt_buffer_verify_func', None):
            raise CPABEError("PQC decryptBuffer_and_verify function not found in DLL")

        sk_json = base64.b64decode(sk_data)
        pqc_pk_json = base64.b64decode(self.pqc_pk_data)

        sk_ptr = ctypes.cast(ctypes.create_string_buffer(sk_json), ctypes.POINTER(ctypes.c_ubyte))
        pqc_pk_ptr = ctypes.cast(ctypes.create_string_buffer(pqc_pk_json), ctypes.POINTER(ctypes.c_ubyte))
        ct_ptr = ctypes.cast(ctypes.create_string_buffer(ciphertext), ctypes.POINTER(ctypes.c_ubyte))
        
        pt_ptr = ctypes.POINTER(ctypes.c_ubyte)()
        pt_len = ctypes.c_size_t(0)
        
        result = self._decrypt_buffer_verify_func(
            sk_ptr, len(sk_json),
            pqc_pk_ptr, len(pqc_pk_json),
            ct_ptr, len(ciphertext),
            ctypes.byref(pt_ptr), ctypes.byref(pt_len)
        )

        if result != 0:
            err_msg = self._lib.getErrorMessage(result).decode('utf-8')
            raise CPABEError(f"Buffer PQC decryption failed ({result}): {err_msg}")

        plaintext = bytes(pt_ptr[:pt_len.value])
        if hasattr(self._lib, 'freeBuffer'):
            self._lib.freeBuffer(pt_ptr)
            
        return plaintext

# Lazy singleton – CPABEService is only created the first time it is accessed,
# giving Vault enough time to start up before any connection is attempted.
class _LazyCPABEService:
    """Proxy that delays CPABEService() creation until first attribute access."""
    def __init__(self):
        self._instance = None

    def _get_instance(self):
        if self._instance is None:
            self._instance = CPABEService()
        return self._instance

    def __getattr__(self, name):
        return getattr(self._get_instance(), name)

cpabe_service = _LazyCPABEService()
