import os
import json
import time
import urllib.request
import urllib.error

# Install hvac if running outside container but we assume it's running inside `web` container
try:
    import hvac
except ImportError:
    print("hvac not installed. Run 'pip install hvac'")
    exit(1)

VAULT_ADDR = os.environ.get('VAULT_ADDR', 'http://vault:8200')
KEYS_DIR = os.environ.get('KEYS_DIR', '/app/config/keys')
UNSEAL_KEYS_FILE = os.path.join(KEYS_DIR, 'vault_unseal_keys.json')
TOKEN_FILE = os.path.join(KEYS_DIR, 'vault_token.txt')

def wait_for_vault():
    print(f"Waiting for Vault at {VAULT_ADDR}...")
    for _ in range(30):
        try:
            req = urllib.request.Request(f"{VAULT_ADDR}/v1/sys/health")
            try:
                with urllib.request.urlopen(req) as response:
                    if response.status in [200, 429, 472, 473, 501, 503]:
                        return True
            except urllib.error.HTTPError as e:
                # Vault returns 501/503 when uninitialized/sealed, which is fine!
                return True
        except Exception:
            pass
        time.sleep(1)
    print("Vault did not become reachable in time.")
    return False

def init_and_unseal():
    if not wait_for_vault():
        return

    client = hvac.Client(url=VAULT_ADDR)
    
    try:
        is_initialized = client.sys.is_initialized()
    except Exception as e:
        print(f"Failed to check initialization status: {e}")
        return

    if not is_initialized:
        print("Vault is not initialized. Initializing...")
        result = client.sys.initialize(secret_shares=1, secret_threshold=1)
        root_token = result['root_token']
        keys = result['keys']
        
        # Save keys and token
        os.makedirs(KEYS_DIR, exist_ok=True)
        with open(UNSEAL_KEYS_FILE, 'w') as f:
            json.dump({'keys': keys}, f)
        
        with open(TOKEN_FILE, 'w') as f:
            f.write(root_token)
            
        print(f"Vault initialized. Unseal keys saved to {UNSEAL_KEYS_FILE}")
        
        # Re-authenticate with root token
        client.token = root_token
        
        # Unseal
        print("Unsealing Vault...")
        client.sys.submit_unseal_key(keys[0])
        
        # Enable KV v2 secrets engine
        print("Enabling KV v2 secrets engine at 'secret/'...")
        client.sys.enable_secrets_engine(
            backend_type='kv',
            path='secret',
            options={'version': '2'}
        )
        print("Vault setup complete.")

    else:
        print("Vault is already initialized.")
        is_sealed = client.sys.is_sealed()
        if is_sealed:
            print("Vault is sealed. Attempting auto-unseal...")
            if not os.path.exists(UNSEAL_KEYS_FILE):
                print(f"Cannot unseal: {UNSEAL_KEYS_FILE} not found!")
                return
            
            with open(UNSEAL_KEYS_FILE, 'r') as f:
                data = json.load(f)
                keys = data.get('keys', [])
                
            if not keys:
                print("No keys found in unseal file!")
                return
                
            client.sys.submit_unseal_key(keys[0])
            print("Vault unsealed successfully.")
        else:
            print("Vault is already unsealed.")

if __name__ == '__main__':
    init_and_unseal()
