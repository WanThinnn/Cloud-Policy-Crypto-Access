import clamd
import os
import logging
from io import BytesIO

logger = logging.getLogger(__name__)

class ClamAVService:
    def __init__(self):
        self.host = os.environ.get('CLAMAV_HOST', 'clamav')
        self.port = int(os.environ.get('CLAMAV_PORT', 3310))
        self.cd = None

    def _get_client(self):
        if not self.cd:
            try:
                self.cd = clamd.ClamdNetworkSocket(self.host, self.port)
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
