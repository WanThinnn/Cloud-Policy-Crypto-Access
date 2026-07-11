import json
import subprocess
import tempfile
import base64
import os
from django.conf import settings

# Path to the Root CA Key
ROOT_CA_KEY_PATH = os.environ.get('PQC_SSL_CA_KEY_FILE', '/certs/pq-CyberFortress-RootCA.key')
if not os.path.exists(ROOT_CA_KEY_PATH):
    ROOT_CA_KEY_PATH = os.path.join(settings.BASE_DIR, '..', 'config', 'certs', 'pq-CyberFortress-RootCA.key')

class PKIService:
    """Service to handle PKI operations using OpenSSL and the Root CA."""
    
    @classmethod
    def sign_payload(cls, payload_dict: dict) -> str:
        """
        Signs a JSON dictionary payload using the Root CA private key.
        Returns the base64-encoded signature.
        """
        # Ensure consistent JSON serialization
        payload_json = json.dumps(payload_dict, separators=(',', ':'), sort_keys=True).encode('utf-8')
        
        # Verify the key exists
        if not os.path.exists(ROOT_CA_KEY_PATH):
            raise FileNotFoundError(f"Root CA Key not found at {ROOT_CA_KEY_PATH}")
            
        # We use a temporary file to safely pass the payload to openssl
        with tempfile.NamedTemporaryFile(delete=False) as temp_in:
            temp_in.write(payload_json)
            temp_in_path = temp_in.name
            
        try:
            import urllib.request
            import urllib.error
            import ssl
            # Try to use the dedicated pki_signer service first
            pki_url = os.environ.get('PKI_SIGNER_URL', 'https://pki_signer:5000')
            pki_token = os.environ.get('PKI_AUTH_TOKEN', 'pki-default-token')
            req = urllib.request.Request(pki_url, data=payload_json, method="POST")
            req.add_header('Content-Length', str(len(payload_json)))
            req.add_header('Authorization', f'Bearer {pki_token}')
            
            ctx = ssl.create_default_context()
            ca_cert_path = os.environ.get('PKI_CACERT', '/certs/CyberFortress-RootCA.crt')
            if pki_url.startswith('https') and os.path.exists(ca_cert_path):
                ctx.load_verify_locations(cafile=ca_cert_path)
                # Disable strict hostname checking for internal Docker networks 
                # (since the cert might not have a SAN for the internal pki_signer alias)
                ctx.check_hostname = False
            else:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

            try:
                with urllib.request.urlopen(req, context=ctx, timeout=5) as response:
                    signature_bytes = response.read()
                    return base64.b64encode(signature_bytes).decode('utf-8')
            except urllib.error.URLError:
                # Fallback to local subprocess (if running on host or container with oqs)
                cmd = [
                    "openssl", "pkeyutl",
                    "-sign",
                    "-inkey", ROOT_CA_KEY_PATH,
                    "-rawin",
                    "-in", temp_in_path
                ]
                result = subprocess.run(cmd, capture_output=True, check=True)
                signature_bytes = result.stdout
                return base64.b64encode(signature_bytes).decode('utf-8')
                
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"OpenSSL signing failed: {e.stderr.decode('utf-8')}")
        finally:
            # Cleanup temp file
            if os.path.exists(temp_in_path):
                os.remove(temp_in_path)
