import os
from django.conf import settings

def pqc_settings(request):
    """
    Expose PQC settings and Root CA raw public key to templates.
    """
    # Raw ML-DSA-87 public key (2592 bytes) encoded as base64
    raw_pk_path = os.path.join(settings.BASE_DIR, '..', 'config', 'certs', 'root_ca_raw_pk.b64')
    root_ca_pk_b64 = ""
    if os.path.exists(raw_pk_path):
        with open(raw_pk_path, 'r') as f:
            root_ca_pk_b64 = f.read().strip()
            
    return {
        'ENABLE_PQC_FEATURES': getattr(settings, 'ENABLE_PQC_FEATURES', True),
        'ROOT_CA_PUBLIC_KEY': root_ca_pk_b64
    }

