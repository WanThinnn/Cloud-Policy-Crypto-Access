"""
Authentication Views - Registration, Login, Password Management
"""
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.utils import timezone
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from datetime import timedelta
import secrets
import logging

logger = logging.getLogger(__name__)


class AuthRateThrottle(AnonRateThrottle):
    """Rate limit: 5 attempts per minute for auth endpoints"""
    rate = '5/min'

from ..serializers import (
    RegisterSerializer,
    LoginSerializer,
    ChangePasswordSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    UserDetailSerializer,
)
from ..models import UserProfile


# Template views
def login_page(request):
    """Render login page"""
    return render(request, 'accounts/login.html')


def register_page(request):
    """Render register page"""
    return render(request, 'accounts/register.html')


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthRateThrottle])
def register(request):
    """
    Register new user
    
    POST /api/auth/register/
    Body:
    {
        "username": "nva_it",
        "email": "user@example.com",
        "password": "SecurePass123!",
        "password2": "SecurePass123!",
        "full_name": "Nguyễn Văn A",
        "phone": "0123456789"
    }
    """
    serializer = RegisterSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.save()
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        
        response = Response({
            'message': 'User registered successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.profile.full_name,
            }
        }, status=status.HTTP_201_CREATED)
        
        # Set HttpOnly cookies
        is_secure = getattr(settings, 'SESSION_COOKIE_SECURE', False)
        response.set_cookie(
            'access_token', access_token,
            max_age=3600, httponly=True, samesite='Lax', secure=is_secure
        )
        response.set_cookie(
            'refresh_token', refresh_token,
            max_age=7*24*3600, httponly=True, samesite='Lax', secure=is_secure
        )
        
        return response
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthRateThrottle])
def login(request):
    """
    Login user
    
    POST /api/auth/login/
    Body:
    {
        "username": "nva_it",
        "password": "SecurePass123!"
    }
    """
    serializer = LoginSerializer(data=request.data)
    
    if serializer.is_valid():
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        
        user = authenticate(username=username, password=password)
        
        if user is None:
            return Response({
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user.is_active:
            return Response({
                'error': 'Account is disabled'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check account status
        if hasattr(user, 'profile'):
            if not user.profile.is_account_active():
                return Response({
                    'error': f'Account is {user.profile.account_status}'
                }, status=status.HTTP_403_FORBIDDEN)
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        
        response = Response({
            'message': 'Login successful',
            'user': UserDetailSerializer(user).data
        })
        
        # Set HttpOnly cookies
        is_secure = getattr(settings, 'SESSION_COOKIE_SECURE', False)
        response.set_cookie(
            'access_token', access_token,
            max_age=3600, httponly=True, samesite='Lax', secure=is_secure
        )
        response.set_cookie(
            'refresh_token', refresh_token,
            max_age=7*24*3600, httponly=True, samesite='Lax', secure=is_secure
        )
        
        return response
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    Logout user (blacklist refresh token)
    
    POST /api/auth/logout/
    Body:
    {
        "refresh": "<refresh_token>"
    }
    """
    try:
        # Get refresh token from cookies instead of body
        refresh_token = request.COOKIES.get('refresh_token') or request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
            
        response = Response({
            'message': 'Logout successful'
        }, status=status.HTTP_200_OK)
        
        # Delete cookies
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        
        return response
        
    except Exception as e:
        response = Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        return response

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    Change password for authenticated user
    
    POST /api/auth/change-password/
    Body:
    {
        "old_password": "OldPass123!",
        "new_password": "NewPass123!",
        "new_password2": "NewPass123!"
    }
    """
    serializer = ChangePasswordSerializer(data=request.data)
    
    if serializer.is_valid():
        user = request.user
        
        # Check old password
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({
                'error': 'Old password is incorrect'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Set new password
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({
            'message': 'Password changed successfully'
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthRateThrottle])
def password_reset_request(request):
    """
    Request password reset (send reset token)
    
    POST /api/auth/password-reset/request/
    Body:
    {
        "email": "user@example.com"
    }
    """
    serializer = PasswordResetRequestSerializer(data=request.data)
    
    if serializer.is_valid():
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email=email)
            profile = user.profile
            
            # Generate reset token
            reset_token = secrets.token_urlsafe(32)
            profile.password_reset_token = reset_token
            profile.password_reset_expires = timezone.now() + timedelta(hours=1)
            profile.save()
            
            # TODO: Send email with reset link
            # send_password_reset_email(user.email, reset_token)
            
            logger.info(f"[AUTH] Password reset token generated for {email}")
            
            return Response({
                'message': 'Password reset instructions sent to email'
            })
            
        except User.DoesNotExist:
            # Don't reveal if email exists
            return Response({
                'message': 'If email exists, reset instructions will be sent'
            })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    """
    Confirm password reset with token
    
    POST /api/auth/password-reset/confirm/
    Body:
    {
        "token": "<reset_token>",
        "new_password": "NewPass123!",
        "new_password2": "NewPass123!"
    }
    """
    serializer = PasswordResetConfirmSerializer(data=request.data)
    
    if serializer.is_valid():
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']
        
        try:
            profile = UserProfile.objects.get(password_reset_token=token)
            
            # Check token expiry
            if profile.password_reset_expires < timezone.now():
                return Response({
                    'error': 'Reset token has expired'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Reset password
            user = profile.user
            user.set_password(new_password)
            user.save()
            
            # Clear reset token
            profile.password_reset_token = None
            profile.password_reset_expires = None
            profile.save()
            
            return Response({
                'message': 'Password reset successfully'
            })
            
        except UserProfile.DoesNotExist:
            return Response({
                'error': 'Invalid reset token'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """
    Get current user profile
    
    GET /api/auth/profile/
    """
    serializer = UserDetailSerializer(request.user)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_permissions(request):
    """
    Get current user's permissions and role info
    Used by frontend to show/hide admin menu items and control features
    
    GET /api/auth/permissions/
    """
    user = request.user
    
    # Default permissions
    permissions = {
        'is_authenticated': True,
        'is_admin': False,
        'is_super_admin': False,
        'user_type': None,
        'can_manage_users': False,
        'can_manage_policies': False,
        'can_manage_files': False,
        'can_view_audit_logs': False,
        # File permissions (for files manager)
        'can_upload_files': False,
        'can_download_files': False,
        'can_delete_files': False,
    }
    
    if hasattr(user, 'profile') and user.profile:
        profile = user.profile
        user_type = profile.get_user_type_code()
        
        # Import casbin service to evaluate ABAC policies
        from crypto_access.services.casbin_service import casbin_service
        from crypto_access.services.casbin_service import casbin_service
        
        permissions.update({
            'user_type': user_type,
            'is_admin': profile.is_admin(),
            'is_super_admin': profile.is_super_admin(),
            # Base Admin UI toggles (Requires at least admin status)
            'can_access_admin': profile.is_admin() or profile.is_super_admin(),
            # ABAC-based Management Permissions
            'can_manage_users': casbin_service.check_access(user, 'user', 'manage'),
            'can_manage_policies': casbin_service.check_access(user, 'policy', 'manage'),
            'can_manage_keys': casbin_service.check_access(user, 'key', 'manage'),
            'can_view_audit_logs': casbin_service.check_access(user, 'audit', 'read'),
            'can_manage_attributes': casbin_service.check_access(user, 'attribute', 'manage'),
            # File system generic checks
            'can_manage_files': user_type in ['super_admin', 'admin', 'data_contributor'],
            # File permissions based on ABAC
            'can_upload_files': casbin_service.check_access(user, 'document', 'upload'),
            'can_download_files': casbin_service.check_access(user, 'document', 'download'),
            'can_delete_files': casbin_service.check_access(user, 'document', 'delete'),
        })
    
    return Response(permissions)
