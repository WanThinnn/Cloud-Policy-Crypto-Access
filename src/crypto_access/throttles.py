from rest_framework.throttling import UserRateThrottle

class CPABEDecryptThrottle(UserRateThrottle):
    """
    Throttle for CP-ABE decryption endpoints (download, preview).
    These operations are CPU intensive, so we limit them strictly.
    Default: 10 requests per minute per user.
    """
    scope = 'cpabe_decrypt'


class CPABEEncryptThrottle(UserRateThrottle):
    """
    Throttle for CP-ABE encryption endpoints (upload).
    Default: 5 requests per minute per user.
    """
    scope = 'cpabe_encrypt'
