"""
Passkey Authentication Views
Implements WebAuthn server-side authentication for login.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.conf import settings
# pyrefly: ignore [missing-import]
from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
    base64url_to_bytes,
)
from webauthn.helpers import bytes_to_base64url
# pyrefly: ignore [missing-import]
from webauthn.helpers.structs import (
    AttestationConveyancePreference,
    AuthenticatorSelectionCriteria,
    AuthenticatorAttachment,
    ResidentKeyRequirement,
    UserVerificationRequirement,
    RegistrationCredential,
    AuthenticationCredential,
)
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from django.utils import timezone
from django.core.cache import cache
import uuid
import logging

from ..models import WebAuthnCredential, ActiveSession, AccessLog
from ..serializers import UserDetailSerializer
from .auth import get_client_ip

logger = logging.getLogger('crypto_access.auth')

# Default WebAuthn settings (configured in settings.py)
RP_ID = getattr(settings, 'WEBAUTHN_RP_ID', 'localhost')
RP_NAME = getattr(settings, 'WEBAUTHN_RP_NAME', 'Cloud Policy Crypto Access')
ORIGIN = getattr(settings, 'WEBAUTHN_ORIGIN', 'http://localhost:8000')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def passkey_register_options(request):
    """
    Generate options for registering a new passkey.
    Called after successful password login if user chooses to set up a passkey.
    """
    user = request.user
    
    # Exclude existing credentials
    exclude_credentials = [
        {"id": cred.credential_id, "type": "public-key"}
        for cred in user.webauthn_credentials.filter(is_active=True)
    ]
    
    # Generate options using py-webauthn
    try:
        options = generate_registration_options(
            rp_id=RP_ID,
            rp_name=RP_NAME,
            user_id=str(user.id).encode('utf-8'),
            user_name=f"{user.username} (Login)",
            user_display_name=f"{getattr(user.profile, 'full_name', user.username) if hasattr(user, 'profile') else user.username} (Login)",
            attestation=AttestationConveyancePreference.NONE,
            authenticator_selection=AuthenticatorSelectionCriteria(
                # Allow platform and cross-platform
                authenticator_attachment=None,
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.REQUIRED,
            ),
            exclude_credentials=exclude_credentials,
        )
        
        # Store challenge in cache (valid for 5 mins)
        cache_key = f"webauthn_reg_challenge_{user.id}"
        cache.set(cache_key, options.challenge, timeout=300)
        
        import json
        response_dict = json.loads(options_to_json(options))
        return Response(response_dict)
    except Exception as e:
        logger.error(f"Passkey register options error: {str(e)}")
        return Response({"error": "Failed to generate passkey options"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def passkey_register_complete(request):
    """
    Verify the attestation response and save the passkey.
    """
    user = request.user
    cache_key = f"webauthn_reg_challenge_{user.id}"
    expected_challenge = cache.get(cache_key)
    
    if not expected_challenge:
        return Response({"error": "Registration session expired. Please try again."}, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        verification = verify_registration_response(
            credential=request.data,
            expected_challenge=expected_challenge,
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
        )
        
        # Save the verified credential
        WebAuthnCredential.objects.create(
            user=user,
            credential_id=verification.credential_id,
            public_key=verification.credential_public_key,
            sign_count=verification.sign_count,
            aaguid=str(verification.aaguid),
            backed_up=verification.credential_device_type == "multi_device",
            device_name=request.META.get('HTTP_USER_AGENT', '')[:200]
        )
        
        # Clear challenge
        cache.delete(cache_key)
        
        # Log audit event
        AccessLog.log_access(
            user=user,
            resource_type='account',
            action='passkey_register',
            result='allow',
            error_message="Passkey setup successful"
        )
        
        return Response({"success": True, "message": "Passkey registered successfully"})
        
    except Exception as e:
        logger.error(f"Passkey registration verification failed: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def passkey_login_options(request):
    """
    Generate authentication options for login.
    If username is provided, restricts to that user's credentials.
    Otherwise, leaves allowCredentials empty for discoverable credentials.
    """
    username = request.data.get('username')
    allow_credentials = []
    
    if username:
        try:
            user = User.objects.get(username=username)
            if not user.is_active:
                return Response({"error": "Account is disabled"}, status=status.HTTP_403_FORBIDDEN)
                
            allow_credentials = [
                {"id": cred.credential_id, "type": "public-key"}
                for cred in user.webauthn_credentials.filter(is_active=True)
            ]
        except User.DoesNotExist:
            # Avoid username enumeration by returning a fake challenge without allow_credentials
            pass

    try:
        options = generate_authentication_options(
            rp_id=RP_ID,
            allow_credentials=allow_credentials,
            user_verification=UserVerificationRequirement.REQUIRED,
        )
        
        # We need to map this challenge to a temporary ID for the login completion
        temp_id = str(uuid.uuid4())
        cache_key = f"webauthn_auth_challenge_{temp_id}"
        cache.set(cache_key, options.challenge, timeout=300)
        
        response_data = options_to_json(options)
        import json
        response_dict = json.loads(response_data)
        response_dict['temp_auth_id'] = temp_id  # Send temp_id to client
        
        return Response(response_dict)
    except Exception as e:
        logger.error(f"Passkey login options error: {str(e)}")
        return Response({"error": "Failed to generate login options"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def passkey_login_complete(request):
    """
    Verify the assertion response and log the user in.
    """
    temp_id = request.data.get('temp_auth_id')
    if not temp_id:
        return Response({"error": "Missing temp_auth_id"}, status=status.HTTP_400_BAD_REQUEST)
        
    cache_key = f"webauthn_auth_challenge_{temp_id}"
    expected_challenge = cache.get(cache_key)
    
    if not expected_challenge:
        return Response({"error": "Login session expired. Please try again."}, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        credential_id_str = request.data.get('id')
        credential_id_bytes = base64url_to_bytes(credential_id_str)
        
        # Find the credential in DB
        db_cred = WebAuthnCredential.objects.filter(
            credential_id=credential_id_bytes,
            is_active=True
        ).first()
        
        if not db_cred:
            return Response({"error": "Credential not found or disabled"}, status=status.HTTP_404_NOT_FOUND)
            
        user = db_cred.user
        if not user.is_active:
            return Response({"error": "Account is disabled"}, status=status.HTTP_403_FORBIDDEN)
            
        # Check account profile status
        if hasattr(user, 'profile') and not user.profile.is_account_active():
            return Response({"error": f"Account is {user.profile.account_status}"}, status=status.HTTP_403_FORBIDDEN)

        verification = verify_authentication_response(
            credential=request.data,
            expected_challenge=expected_challenge,
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
            credential_public_key=db_cred.public_key,
            credential_current_sign_count=db_cred.sign_count,
            require_user_verification=True,
        )
        
        # Update sign count
        db_cred.sign_count = verification.new_sign_count
        db_cred.save()
        
        # Clear challenge
        cache.delete(cache_key)
        
        # Log successful authentication
        ip_address = get_client_ip(request)
        logger.info(f"Passkey login successful: {user.username} from IP: {ip_address}")
        
        # Issue JWT tokens (similar to password login)
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        
        user_agent_str = request.META.get('HTTP_USER_AGENT', '')
        
        # Simple browser/OS parsing
        browser = "Unknown Browser"
        os_name = "Unknown OS"
        if "Chrome" in user_agent_str: browser = "Chrome"
        elif "Firefox" in user_agent_str: browser = "Firefox"
        elif "Safari" in user_agent_str and "Chrome" not in user_agent_str: browser = "Safari"
        elif "Edge" in user_agent_str: browser = "Edge"
        
        if "Windows" in user_agent_str: os_name = "Windows"
        elif "Mac OS" in user_agent_str: os_name = "macOS"
        elif "Linux" in user_agent_str: os_name = "Linux"
        elif "Android" in user_agent_str: os_name = "Android"
        elif "iPhone" in user_agent_str or "iPad" in user_agent_str: os_name = "iOS"
        
        # Extract JTI from token to use as session key
        try:
            access_obj = AccessToken(access_token)
            session_key = access_obj.get('jti', str(uuid.uuid4()))
        except Exception:
            session_key = str(uuid.uuid4())
            
        ActiveSession.objects.create(
            user=user,
            session_key=session_key,
            ip_address=ip_address,
            browser=browser,
            os_name=os_name,
            device_name=user_agent_str[:200]
        )
        
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
        
    except Exception as e:
        logger.error(f"Passkey login verification failed: {str(e)}")
        return Response({"error": "Invalid passkey response"}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def passkey_list(request):
    """List all WebAuthn credentials for the current user."""
    credentials = request.user.webauthn_credentials.filter(is_active=True).order_by('-created_at')
    
    result = []
    for cred in credentials:
        result.append({
            'id': str(cred.id),
            'credential_id': bytes_to_base64url(cred.credential_id),
            'device_name': cred.device_name,
            'created_at': cred.created_at,
            'last_used': cred.updated_at,
            'sign_count': cred.sign_count
        })
        
    return Response(result)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def passkey_delete(request, pk):
    """Delete a WebAuthn credential."""
    try:
        cred = request.user.webauthn_credentials.get(id=pk, is_active=True)
        cred.is_active = False  # Soft delete
        cred.save()
        
        # Log audit event
        AccessLog.log_access(
            user=request.user,
            resource_type='account',
            action='passkey_delete',
            result='allow',
            error_message=f"Deleted passkey ID: {pk}"
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
    except WebAuthnCredential.DoesNotExist:
        return Response({'error': 'Passkey not found'}, status=status.HTTP_404_NOT_FOUND)
