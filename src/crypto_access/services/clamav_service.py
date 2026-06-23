import clamd
import os
import logging
from io import BytesIO

logger = logging.getLogger(__name__)

class ClamdTLSSocket(clamd.ClamdNetworkSocket):
    def __init__(self, host, port, timeout=None, ca_certs=None):
        super().__init__(host, port, timeout)
        self.ca_certs = ca_certs

    def _init_socket(self):
        import socket, ssl, sys
        from clamd import ConnectionError
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if self.timeout:
                s.settimeout(self.timeout)
            s.connect((self.host, self.port))
            
            ctx = ssl.create_default_context(cafile=self.ca_certs)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            self.clamd_socket = ctx.wrap_socket(s, server_hostname=self.host)
        except Exception:
            e = sys.exc_info()[1]
            raise ConnectionError(f"Error connecting to {self.host}:{self.port} over TLS. {e}")

class ClamAVService:
    def __init__(self):
        self.host = os.environ.get('CLAMAV_HOST', 'clamav')
        self.port = int(os.environ.get('CLAMAV_PORT', 3310))
        self.use_tls = os.environ.get('CLAMAV_USE_TLS', 'False').lower() in ('true', '1', 'yes')
        self.ca_cert = os.environ.get('CLAMAV_CACERT', None)
        self.cd = None

    def _get_client(self):
        if not self.cd:
            try:
                if self.use_tls:
                    self.cd = ClamdTLSSocket(self.host, self.port, timeout=15.0, ca_certs=self.ca_cert)
                else:
                    self.cd = clamd.ClamdNetworkSocket(self.host, self.port, timeout=15.0)
            except Exception as e:
                logger.error(f"Failed to connect to ClamAV daemon: {e}")
                self.cd = None
        return self.cd

    def scan_file_buffer(self, file_data: bytes) -> tuple[bool, str]:
        """
        Scans a byte buffer for malware.
        Returns (is_safe, message_or_virus_name)
        """
        try:
            client = self._get_client()
            if not client:
                logger.warning("ClamAV client not available. Bypassing scan (fail-open) or failing upload.")
                # Depending on security policy, we might fail-open or fail-closed.
                # For high security, we fail-closed if scanner is unreachable.
                return False, "SCANNER_UNAVAILABLE"

            # Check if ClamAV is responding
            try:
                client.ping()
            except clamd.ConnectionError:
                self.cd = None # Reset connection for next time
                return False, "SCANNER_UNAVAILABLE"

            # Create a file-like object from the bytes
            f = BytesIO(file_data)
            
            # instream() returns a dict: {'stream': ('FOUND', 'Eicar-Test-Signature')}
            # or {'stream': ('OK', None)}
            result = client.instream(f)
            
            if not result or 'stream' not in result:
                return False, "SCANNER_ERROR"

            status, details = result['stream']
            
            if status == 'OK':
                return True, "Clean"
            elif status == 'FOUND':
                logger.warning(f"Malware detected: {details}")
                return False, details
            else:
                return False, f"Unknown status: {status}"
                
        except Exception as e:
            logger.error(f"Exception during ClamAV scan: {e}")
            return False, f"SCANNER_EXCEPTION: {str(e)}"

clamav_service = ClamAVService()
