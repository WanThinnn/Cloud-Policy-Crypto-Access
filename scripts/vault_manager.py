import os
import json
import time
import urllib.request
import urllib.error
import argparse
import ssl
import urllib3

# Install hvac if running outside container but we assume it's running inside `web` container
try:
    import hvac
except ImportError:
    print("hvac not installed. Run 'pip install hvac'")
    exit(1)

VAULT_ADDR = os.environ.get('VAULT_ADDR', 'http://localhost:8200')
KEYS_DIR = os.environ.get('KEYS_DIR', '/app/config/keys')
UNSEAL_KEYS_FILE = os.path.join(KEYS_DIR, 'vault_unseal_keys.json')
TOKEN_FILE = os.path.join(KEYS_DIR, 'vault_token.txt')

def get_ca_cert_path():
    ca_cert_path = os.environ.get('VAULT_CACERT', '/certs/CyberFortress-RootCA.crt')
    if os.path.exists(ca_cert_path):
        return ca_cert_path
    # Fallback to local path when running outside container (e.g., via start.py on Windows)
    local_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'certs', 'CyberFortress-RootCA.crt')
    if os.path.exists(local_path):
        return local_path
    return None

def wait_for_vault():
    print(f"Waiting for Vault at {VAULT_ADDR}...")
    
    ctx = ssl.create_default_context()
    ca_cert_path = get_ca_cert_path()
    if VAULT_ADDR.startswith('https') and ca_cert_path:
        ctx.load_verify_locations(cafile=ca_cert_path)
    else:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    for _ in range(30):
        try:
            req = urllib.request.Request(f"{VAULT_ADDR}/v1/sys/health")
            try:
                with urllib.request.urlopen(req, context=ctx) as response:
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

def register_abe_plugin(client):
    use_plugin = os.environ.get('USE_VAULT_ABE_PLUGIN', 'False').lower() in ('true', '1', 't')
    if not use_plugin:
        return
        
    plugin_path = '/vault/plugins/vault-plugin-abe'
    if not os.path.exists(plugin_path):
        print(f"Plugin binary not found at {plugin_path}. Please build it first.")
        return
        
    import hashlib
    with open(plugin_path, "rb") as f:
        plugin_hash = hashlib.sha256(f.read()).hexdigest()
        
    print(f"Registering vault-plugin-abe (sha256: {plugin_hash})...")
    try:
        client.sys.register_plugin(
            name='vault-plugin-abe',
            plugin_type='secret',
            command='vault-plugin-abe',
            sha256=plugin_hash
        )
    except Exception as e:
        if "already registered" not in str(e):
            print(f"Failed to register plugin: {e}")
            return
            
    try:
        client.sys.enable_secrets_engine(
            backend_type='vault-plugin-abe',
            path='abe',
            description='Hybrid PQC CP-ABE Engine'
        )
        print("ABE Secrets engine successfully enabled at 'abe/'.")
    except Exception as e:
        if "path is already in use" in str(e):
            print("ABE engine already enabled.")
        else:
            print(f"Failed to enable ABE secrets engine: {e}")

def init_and_unseal():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prod', action='store_true', help='Enable production mode (no auto-unseal)')
    args = parser.parse_args()
    is_prod = args.prod

    if not wait_for_vault():
        return

    ca_cert_path = get_ca_cert_path()
    if VAULT_ADDR.startswith('https'):
        if ca_cert_path:
            client = hvac.Client(url=VAULT_ADDR, verify=ca_cert_path)
        else:
            # Running locally on Windows without the cert mounted, disable verification
            client = hvac.Client(url=VAULT_ADDR, verify=False)
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    else:
        client = hvac.Client(url=VAULT_ADDR)
    
    try:
        is_initialized = client.sys.is_initialized()
    except Exception as e:
        print(f"Failed to check initialization status: {e}")
        return

    if not is_initialized:
        shares = 5 if is_prod else 1
        threshold = 3 if is_prod else 1

        print("Vault is not initialized. Initializing...")
        result = client.sys.initialize(secret_shares=shares, secret_threshold=threshold)
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
        
        # Unseal for initial setup
        print("Unsealing Vault for initial setup...")
        for key in keys:
            res = client.sys.submit_unseal_key(key)
            if not res.get('sealed', True):
                break
        
        # Wait for Raft leader election
        print("Waiting for Raft leader election...")
        time.sleep(2)
        
        # Enable KV v2 secrets engine
        print("Enabling KV v2 secrets engine at 'secret/'...")
        for attempt in range(10):
            try:
                client.sys.enable_secrets_engine(
                    backend_type='kv',
                    path='secret',
                    options={'version': '2'}
                )
                break
            except Exception as e:
                if "path is already in use" in str(e):
                    break
                elif "local node not active" in str(e):
                    print(f"Raft leader not ready yet (attempt {attempt+1}/10), waiting...")
                    time.sleep(2)
                else:
                    raise
        print("Vault setup complete.")

        if is_prod:
            print("\n\033[1;93m=======================================================")
            print("🚨 [WARNING] PRODUCTION ENVIRONMENT DETECTED 🚨")
            print(f"Vault initialized with {shares} keys, {threshold} required to unseal.")
            print(f"Keys are saved in {UNSEAL_KEYS_FILE}.")
            print("Please backup these keys securely and DELETE THE FILE!")
            print("Auto-unseal will be DISABLED for all subsequent restarts.")
            print("=======================================================\033[0m\n")

    else:
        print("Vault is already initialized.")
        is_sealed = client.sys.is_sealed()
        if is_sealed:
            if is_prod:
                print("\n\033[1;93m=======================================================")
                print("🚨 [WARNING] PRODUCTION ENVIRONMENT DETECTED 🚨")
                print("Vault is SEALED. Auto-unseal is DISABLED for security.")
                print(f"Please log in to Vault UI at {VAULT_ADDR} and unseal manually.")
                print("=======================================================\033[0m\n")
                return

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
                
            for key in keys:
                res = client.sys.submit_unseal_key(key)
                if not res.get('sealed', True):
                    break
            print("Vault unsealed successfully.")
        else:
            print("Vault is already unsealed.")
            
    # Try to authenticate with root token if available to register the plugin
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as f:
            client.token = f.read().strip()
        register_abe_plugin(client)
    else:
        print("No root token found. Skipping plugin registration.")

if __name__ == '__main__':
    init_and_unseal()
