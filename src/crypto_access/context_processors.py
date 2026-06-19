import os
from django.conf import settings

def pqc_settings(request):
    """
    Expose PQC settings and Root CA to templates.
    """
    root_ca_path = os.path.join(settings.BASE_DIR, '..', 'config', 'certs', 'pq-CyberFortress-RootCA.crt')
    root_ca_pem = ""
    if os.path.exists(root_ca_path):
        with open(root_ca_path, 'r') as f:
            root_ca_pem = f.read()
            
    return {
        'ENABLE_PQC_FEATURES': getattr(settings, 'ENABLE_PQC_FEATURES', True),
        'ROOT_CA_PUBLIC_KEY': root_ca_pem
    }
