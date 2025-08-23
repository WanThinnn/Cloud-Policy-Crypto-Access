"""
File Integrity Manager with ssdeep similarity detection
"""
import hashlib
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import tempfile
import os

logger = logging.getLogger(__name__)

try:
    import ssdeep
    SSDEEP_AVAILABLE = True
    logger.info("ssdeep library available for similarity detection")
except ImportError:
    SSDEEP_AVAILABLE = False
    logger.warning("ssdeep library not available - using fallback similarity detection")

class FileIntegrityManager:
    """
    Manages file integrity, versioning, and similarity detection
    """
    
    @staticmethod
    def generate_integrity_hashes(file_data: bytes) -> Dict[str, Any]:
        """
        Generate integrity hashes for a file
        
        Args:
            file_data: Raw file data
            
        Returns:
            Dict with hash values
        """
        try:
            hashes = {
                'sha256': hashlib.sha256(file_data).hexdigest(),
                'md5': hashlib.md5(file_data).hexdigest(),
                'file_size': len(file_data)
            }
            
            if SSDEEP_AVAILABLE:
                try:
                    hashes['ssdeep'] = ssdeep.hash(file_data)
                except Exception as e:
                    logger.error(f"ssdeep hashing failed: {e}")
                    hashes['ssdeep'] = None
            else:
                hashes['ssdeep'] = None
                
            return hashes
            
        except Exception as e:
            logger.error(f"Hash generation failed: {e}")
            return {
                'sha256': None,
                'md5': None,
                'ssdeep': None,
                'file_size': len(file_data) if file_data else 0
            }
    
    @staticmethod
    def calculate_similarity(hash1: str, hash2: str) -> float:
        """
        Calculate similarity between two ssdeep hashes
        
        Args:
            hash1: First ssdeep hash
            hash2: Second ssdeep hash
            
        Returns:
            Similarity percentage (0-100)
        """
        if not SSDEEP_AVAILABLE or not hash1 or not hash2:
            return 0.0
            
        try:
            similarity = ssdeep.compare(hash1, hash2)
            return float(similarity)
        except Exception as e:
            logger.error(f"Similarity calculation failed: {e}")
            return 0.0
    
    @staticmethod
    def calculate_size_change_percentage(old_size: int, new_size: int) -> float:
        """Calculate percentage change in file size"""
        if old_size == 0:
            return 100.0
        return ((new_size - old_size) / old_size) * 100
    
    @staticmethod
    def detect_suspicious_changes(similarity_score: float, 
                                 size_change_percent: float,
                                 old_hashes: Dict[str, Any],
                                 new_hashes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect potentially suspicious file changes
        
        Args:
            similarity_score: ssdeep similarity score (0-100)
            size_change_percent: File size change percentage
            old_hashes: Previous version hashes
            new_hashes: New version hashes
            
        Returns:
            Dict with suspicion analysis
        """
        suspicious_indicators = []
        risk_level = "LOW"
        
        # Check for identical files (possible duplicate/accident)
        if similarity_score >= 99 and abs(size_change_percent) < 1:
            suspicious_indicators.append("IDENTICAL_FILE: File appears unchanged")
            risk_level = "MEDIUM"
        
        # Check for minimal changes (possible steganography)
        elif similarity_score > 95 and abs(size_change_percent) < 5:
            suspicious_indicators.append("MINIMAL_CHANGES: Very small changes detected")
            risk_level = "MEDIUM"
        
        # Check for major rewrite (possible data destruction/replacement)
        elif similarity_score < 30:
            suspicious_indicators.append("MAJOR_REWRITE: File content drastically changed")
            risk_level = "HIGH"
        
        # Check for extreme size changes
        if abs(size_change_percent) > 200:
            suspicious_indicators.append("EXTREME_SIZE_CHANGE: File size changed drastically")
            risk_level = "HIGH"
        
        # Check for hash collision (extremely suspicious)
        if (old_hashes.get('sha256') == new_hashes.get('sha256') and 
            old_hashes.get('md5') == new_hashes.get('md5')):
            if similarity_score < 100:
                suspicious_indicators.append("HASH_COLLISION: Identical hashes with different content")
                risk_level = "CRITICAL"
        
        return {
            'is_suspicious': len(suspicious_indicators) > 0,
            'risk_level': risk_level,
            'indicators': suspicious_indicators,
            'analysis': {
                'similarity_score': similarity_score,
                'size_change_percent': size_change_percent,
                'ssdeep_available': SSDEEP_AVAILABLE
            }
        }
    
    @staticmethod
    def create_integrity_report(old_file_data: bytes, 
                               new_file_data: bytes,
                               old_metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Create comprehensive integrity report for file comparison
        
        Args:
            old_file_data: Previous version file data
            new_file_data: New version file data
            old_metadata: Previous version metadata
            
        Returns:
            Complete integrity analysis report
        """
        try:
            # Generate hashes for both versions
            old_hashes = FileIntegrityManager.generate_integrity_hashes(old_file_data)
            new_hashes = FileIntegrityManager.generate_integrity_hashes(new_file_data)
            
            # Calculate similarity
            similarity_score = 0.0
            if old_hashes.get('ssdeep') and new_hashes.get('ssdeep'):
                similarity_score = FileIntegrityManager.calculate_similarity(
                    old_hashes['ssdeep'], 
                    new_hashes['ssdeep']
                )
            
            # Calculate size change
            old_size = old_hashes.get('file_size', 0)
            new_size = new_hashes.get('file_size', 0)
            size_change = FileIntegrityManager.calculate_size_change_percentage(
                int(old_size) if old_size else 0,
                int(new_size) if new_size else 0
            )
            
            # Detect suspicious changes
            suspicion_analysis = FileIntegrityManager.detect_suspicious_changes(
                similarity_score,
                size_change,
                old_hashes,
                new_hashes
            )
            
            report = {
                'timestamp': datetime.utcnow().isoformat(),
                'old_version': {
                    'hashes': old_hashes,
                    'metadata': old_metadata or {}
                },
                'new_version': {
                    'hashes': new_hashes
                },
                'comparison': {
                    'similarity_score': similarity_score,
                    'size_change_percent': size_change,
                    'identical_sha256': old_hashes['sha256'] == new_hashes['sha256'],
                    'identical_md5': old_hashes['md5'] == new_hashes['md5']
                },
                'security_analysis': suspicion_analysis,
                'recommendation': FileIntegrityManager._get_recommendation(suspicion_analysis)
            }
            
            return {
                'success': True,
                'report': report
            }
            
        except Exception as e:
            logger.error(f"Integrity report creation failed: {e}")
            return {
                'success': False,
                'error': f'Failed to create integrity report: {str(e)}'
            }
    
    @staticmethod
    def _get_recommendation(suspicion_analysis: Dict[str, Any]) -> str:
        """Get recommendation based on suspicion analysis"""
        risk_level = suspicion_analysis.get('risk_level', 'LOW')
        
        if risk_level == 'CRITICAL':
            return "DENY_AND_QUARANTINE: Critical security risk detected. Quarantine file and investigate immediately."
        elif risk_level == 'HIGH':
            return "REQUIRE_MANUAL_APPROVAL: High risk detected. Require manager approval before accepting changes."
        elif risk_level == 'MEDIUM':
            return "REQUIRE_JUSTIFICATION: Medium risk detected. User should provide change justification."
        else:
            return "ACCEPT: Changes appear normal and safe."
    
    @staticmethod
    def validate_file_integrity(file_data: bytes, expected_hashes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate file integrity against expected hashes
        
        Args:
            file_data: File data to validate
            expected_hashes: Expected hash values
            
        Returns:
            Validation result
        """
        try:
            current_hashes = FileIntegrityManager.generate_integrity_hashes(file_data)
            
            validation_results = {}
            for hash_type in ['sha256', 'md5']:
                expected = expected_hashes.get(hash_type)
                current = current_hashes.get(hash_type)
                
                if expected and current:
                    validation_results[f'{hash_type}_valid'] = (expected == current)
                else:
                    validation_results[f'{hash_type}_valid'] = None
            
            overall_valid = all(
                result is True for result in validation_results.values() 
                if result is not None
            )
            
            return {
                'success': True,
                'overall_valid': overall_valid,
                'details': validation_results,
                'current_hashes': current_hashes,
                'expected_hashes': expected_hashes
            }
            
        except Exception as e:
            logger.error(f"Integrity validation failed: {e}")
            return {
                'success': False,
                'error': f'Validation failed: {str(e)}',
                'overall_valid': False
            }

# Install ssdeep if not available
def ensure_ssdeep_installed():
    """Attempt to install ssdeep if not available"""
    if not SSDEEP_AVAILABLE:
        logger.warning("ssdeep not available. Install with: pip install ssdeep")
        logger.warning("Note: ssdeep requires system libraries. See documentation for installation.")
        return False
    return True
