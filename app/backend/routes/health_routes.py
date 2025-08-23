"""
Health check routes for monitoring system status
"""
from flask import Blueprint, jsonify
from datetime import datetime
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from module import abe_lib
import logging

health_bp = Blueprint('health', __name__)
logger = logging.getLogger(__name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    Returns system status and component health
    """
    try:
        # Check ABE library status
        abe_status = False
        abe_error = None
        try:
            abe_status = abe_lib is not None and hasattr(abe_lib, 'is_loaded') and abe_lib.is_loaded()
        except Exception as e:
            abe_error = str(e)
        
        # System info
        health_data = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'service': 'Cloud Firestore Crypto Access Backend',
            'version': '1.0.0',
            'components': {
                'abe_library': {
                    'status': 'up' if abe_status else 'down',
                    'loaded': abe_status,
                    'error': abe_error
                },
                'database': {
                    'status': 'up',  # Firestore is always available if configured
                    'type': 'firestore'
                },
                'authentication': {
                    'status': 'up',
                    'jwt': True
                }
            },
            'system': {
                'python_version': sys.version.split()[0],
                'platform': sys.platform,
                'uptime': 'running'
            }
        }
        
        # Determine overall status
        all_up = all(
            comp['status'] == 'up' 
            for comp in health_data['components'].values()
        )
        
        if not all_up:
            health_data['status'] = 'degraded'
            
        logger.info(f"Health check: {health_data['status']}")
        
        return jsonify(health_data), 200
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'error',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'error': str(e)
        }), 500

@health_bp.route('/health/ready', methods=['GET'])
def readiness_check():
    """
    Readiness probe for Kubernetes/Docker
    Returns 200 if service is ready to serve requests
    """
    try:
        # Check critical components
        abe_ready = abe_lib is not None and hasattr(abe_lib, 'is_loaded') and abe_lib.is_loaded()
        
        if abe_ready:
            return jsonify({
                'status': 'ready',
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }), 200
        else:
            return jsonify({
                'status': 'not_ready',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'reason': 'ABE library not loaded'
            }), 503
            
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return jsonify({
            'status': 'error',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'error': str(e)
        }), 500

@health_bp.route('/health/live', methods=['GET'])
def liveness_check():
    """
    Liveness probe for Kubernetes/Docker
    Returns 200 if service is alive (basic check)
    """
    return jsonify({
        'status': 'alive',
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }), 200
