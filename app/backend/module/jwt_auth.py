"""
JWT Token utility for authentication
Handles JWT token generation, validation and decoding
"""
import jwt
import datetime
from typing import Dict, Any, Optional
import os
import uuid

class JWTManager:
    def __init__(self, secret_key: Optional[str] = None):
        """Initialize JWT Manager with secret key"""
        self.secret_key = secret_key or os.environ.get('JWT_SECRET_KEY', 'corporate-cp-abe-jwt-secret-2025')
        self.algorithm = 'HS256'
        self.token_expiry_hours = 24  # 24 hours default
        
    def generate_token(self, user_data: Dict[str, Any], token_type: str = 'access') -> str:
        """
        Generate JWT token for user authentication
        
        Args:
            user_data: User information to encode in token
            token_type: Type of token ('access' or 'refresh')
        
        Returns:
            JWT token string
        """
        now = datetime.datetime.utcnow()
        
        # Token payload
        payload = {
            'user_id': user_data.get('id') or user_data.get('user_id'),
            'username': user_data.get('username'),
            'user_type': user_data.get('user_type', 'regular'),
            'role': user_data.get('role'),
            'token_type': token_type,
            'jti': str(uuid.uuid4()),  # JWT ID for token blacklisting
            'iat': now,  # Issued at
            'exp': now + datetime.timedelta(hours=self.token_expiry_hours),  # Expires at
            'iss': 'corporate-cp-abe-system'  # Issuer
        }
        
        # Add additional fields based on user type
        if user_data.get('user_type') == 'super_admin':
            payload['permissions'] = user_data.get('permissions', ['all'])
            payload['admin_id'] = user_data.get('id')
        else:
            # Regular user - add attributes if available
            payload['attributes'] = user_data.get('attributes', {})
            
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Decode and validate JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded payload if valid, None if invalid
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check if token is expired
            if datetime.datetime.utcnow() > datetime.datetime.fromtimestamp(payload['exp']):
                return None
                
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def validate_token(self, token: str) -> bool:
        """
        Validate JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            True if valid, False if invalid
        """
        return self.decode_token(token) is not None
    
    def extract_token_from_header(self, auth_header: str) -> Optional[str]:
        """
        Extract token from Authorization header
        
        Args:
            auth_header: Authorization header value (Bearer <token>)
            
        Returns:
            Token string if valid format, None otherwise
        """
        if not auth_header:
            return None
            
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return None
            
        return parts[1]
    
    def get_user_from_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get user information from valid token
        
        Args:
            token: JWT token string
            
        Returns:
            User data if token is valid, None otherwise
        """
        payload = self.decode_token(token)
        if not payload:
            return None
            
        return {
            'user_id': payload.get('user_id'),
            'username': payload.get('username'),
            'user_type': payload.get('user_type', 'regular'),
            'role': payload.get('role'),
            'attributes': payload.get('attributes', {}),
            'permissions': payload.get('permissions', []),
            'admin_id': payload.get('admin_id'),
            'token_type': payload.get('token_type', 'access'),
            'exp': payload.get('exp')
        }

# Global JWT manager instance
jwt_manager = JWTManager()
