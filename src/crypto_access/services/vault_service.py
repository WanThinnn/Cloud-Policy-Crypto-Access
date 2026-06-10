import os
import hvac
import logging

logger = logging.getLogger(__name__)

class VaultService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VaultService, cls).__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        self.vault_addr = os.environ.get('VAULT_ADDR', 'http://vault:8200')
        self.secret_path = os.environ.get('VAULT_SECRET_PATH', 'secret/data/crypto_access')
        
        # Try to read token from file first (written by auto-unseal script)
        keys_dir = os.environ.get('KEYS_DIR', '/app/config/keys')
        token_file = os.path.join(keys_dir, 'vault_token.txt')
        if os.path.exists(token_file):
            with open(token_file, 'r') as f:
                self.vault_token = f.read().strip()
        else:
            self.vault_token = os.environ.get('VAULT_TOKEN', 'root')

        
        # Only initialize client if addr is provided and not empty
        if self.vault_addr:
            self.client = hvac.Client(url=self.vault_addr, token=self.vault_token)
        else:
            self.client = None
            
        self._cache = {}

    def is_authenticated(self):
        if not self.client:
            return False
        try:
            return self.client.is_authenticated()
        except Exception as e:
            logger.error(f"Failed to check Vault authentication: {e}")
            return False

    def get_secret(self, key_name, default=None):
        """Retrieve a secret from Vault. Uses simple memory cache."""
        if key_name in self._cache:
            return self._cache[key_name]
            
        if not self.is_authenticated():
            logger.warning("Vault client is not authenticated or unavailable.")
            return default
            
        try:
            read_response = self.client.secrets.kv.v2.read_secret_version(path=self.secret_path.replace('secret/data/', ''))
            secret_data = read_response['data']['data']
            
            # Cache all fetched secrets from this path
            for k, v in secret_data.items():
                self._cache[k] = v
                
            return self._cache.get(key_name, default)
        except hvac.exceptions.InvalidPath:
            logger.warning(f"Secret path {self.secret_path} not found in Vault.")
            return default
        except Exception as e:
            logger.error(f"Error reading from Vault: {e}")
            return default

    def put_secret(self, key_name, value):
        """Store or update a secret in Vault."""
        if not self.is_authenticated():
            logger.warning("Vault client is not authenticated. Cannot write secret.")
            return False
            
        try:
            path = self.secret_path.replace('secret/data/', '')
            # Read existing
            try:
                read_response = self.client.secrets.kv.v2.read_secret_version(path=path)
                current_data = read_response['data']['data']
            except hvac.exceptions.InvalidPath:
                current_data = {}
                
            current_data[key_name] = value
            
            self.client.secrets.kv.v2.create_or_update_secret(
                path=path,
                secret=current_data,
            )
            self._cache[key_name] = value
            return True
        except Exception as e:
            logger.error(f"Error writing to Vault: {e}")
            return False

vault_service = VaultService()
