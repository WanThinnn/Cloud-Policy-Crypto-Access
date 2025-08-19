"""
Simple Central Authority stub for testing without ABE
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class CentralAuthority:
    """
    Simple CA stub for testing
    """
    
    def __init__(self):
        pass
    
    def setup_abe_system(self) -> Dict[str, Any]:
        """Stub setup"""
        return {
            'success': False,
            'error': 'ABE library not available. This is a stub implementation.'
        }
    
    def generate_policy_for_user(self, user_id: str) -> str:
        """Generate basic policy"""
        return "(PUBLIC)"

# Global CA instance
central_authority = CentralAuthority()
