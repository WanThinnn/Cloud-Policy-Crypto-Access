"""
Enhanced ABAC decorator for API endpoint protection
"""
from functools import wraps
from flask import request, jsonify, g
from typing import Dict, Any, Optional, Callable
import logging
from datetime import datetime
from .abac import abac
from .auth_decorators import get_current_user

logger = logging.getLogger(__name__)

def abac_required(resource: str, action: str = "access", 
                 context_extractor: Optional[Callable] = None):
    """
    ABAC decorator for API endpoint protection
    
    Args:
        resource: Resource being accessed (e.g., 'files', 'admin_panel', 'user_management')
        action: Action being performed (e.g., 'read', 'write', 'delete', 'create')
        context_extractor: Optional function to extract additional context from request
        
    Usage:
        @files_api.route('/upload', methods=['POST'])
        @jwt_required
        @abac_required('files', 'create', extract_file_context)
        def upload_file():
            # API logic here
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Get authenticated user (assumes jwt_required is applied first)
                current_user = get_current_user()
                if not current_user:
                    return jsonify({
                        'success': False,
                        'error': 'Authentication required',
                        'abac_error': 'No authenticated user found'
                    }), 401
                
                # Extract user attributes
                user_attributes = current_user.get('attributes', {})
                user_id = current_user.get('user_id')
                
                # Extract additional context if provided
                environment = {}
                if context_extractor and callable(context_extractor):
                    environment = context_extractor(request, current_user)
                
                # Default context
                environment.update({
                    'endpoint': request.endpoint,
                    'method': request.method,
                    'ip_address': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', ''),
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                # Prepare ABAC request
                abac_request = {
                    'user_id': user_id,
                    'user_attributes': user_attributes,
                    'resource': resource,
                    'action': action,
                    'environment': environment,
                    'resource_attributes': {
                        'endpoint': request.endpoint,
                        'method': request.method
                    }
                }
                
                # Check ABAC access
                access_result = abac.check_access(abac_request)
                
                if not access_result['success']:
                    logger.error(f"ABAC engine error for user {user_id}: {access_result.get('error')}")
                    return jsonify({
                        'success': False,
                        'error': 'Access control system error',
                        'abac_error': 'Policy evaluation failed'
                    }), 500
                
                if not access_result['access_granted']:
                    logger.warning(f"ABAC access denied for user {user_id} on {resource}:{action}")
                    logger.warning(f"Reason: {access_result.get('reason')}")
                    
                    return jsonify({
                        'success': False,
                        'error': 'Access denied',
                        'reason': access_result.get('reason', 'Insufficient permissions'),
                        'abac_info': {
                            'resource': resource,
                            'action': action,
                            'user_attributes': user_attributes,
                            'matched_policies': access_result.get('matched_policies', [])
                        }
                    }), 403
                
                # Access granted - continue to API function
                logger.info(f"ABAC access granted for user {user_id} on {resource}:{action}")
                
                # Store ABAC result in Flask g for later use
                g.abac_result = access_result
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"ABAC decorator error: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Access control system error',
                    'abac_error': str(e)
                }), 500
        
        return decorated_function
    return decorator

# Context extractors for different endpoint types
def extract_file_context(request, current_user) -> Dict[str, Any]:
    """Extract context for file operations"""
    context = {}
    
    # File upload context
    if request.method == 'POST' and 'file' in request.files:
        file = request.files['file']
        context.update({
            'file_size_mb': len(file.read()) / (1024 * 1024) if file else 0,
            'file_type': file.content_type if file else 'unknown',
            'filename': file.filename if file else ''
        })
        file.seek(0)  # Reset file pointer
    
    # Time-based context
    from datetime import datetime, time
    now = datetime.now()
    business_start = time(8, 0)  # 8:00 AM
    business_end = time(18, 0)   # 6:00 PM
    
    context['business_hours'] = business_start <= now.time() <= business_end
    context['day_of_week'] = now.weekday()  # 0=Monday, 6=Sunday
    context['is_weekend'] = now.weekday() >= 5
    
    return context

def extract_admin_context(request, current_user) -> Dict[str, Any]:
    """Extract context for admin operations"""
    context = {}
    
    # Administrative action context
    if request.method in ['PUT', 'DELETE', 'PATCH']:
        context['high_risk_operation'] = True
    
    # User management context
    if 'user' in request.endpoint:
        context['user_management_operation'] = True
    
    return context

def extract_system_context(request, current_user) -> Dict[str, Any]:
    """Extract context for system operations"""
    context = {
        'network_location': 'internal',  # Could be determined by IP ranges
        'requires_audit': True,
        'security_level': 'high'
    }
    
    return context
