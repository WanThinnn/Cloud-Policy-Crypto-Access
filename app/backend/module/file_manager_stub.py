"""
Simple File Manager stub for testing without ABE
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class FileManager:
    """
    Simple File Manager stub for testing
    """
    
    def __init__(self):
        pass
    
    def upload_file(self, file_data: bytes, filename: str, owner_id: str, 
                   access_policy: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Stub upload"""
        return {
            'success': False,
            'error': 'File manager not available. This is a stub implementation.'
        }
    
    def list_user_files(self, user_id: str, include_shared: bool = True) -> Dict[str, Any]:
        """Stub list files"""
        return {
            'success': True,
            'files': [],
            'total_count': 0
        }

# Global file manager instance
file_manager = FileManager()
