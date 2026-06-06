from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed

class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom JWT Authentication that reads the token from HttpOnly cookies
    instead of the Authorization header.
    """
    def authenticate(self, request):
        # 1. Try to get token from Authorization header first (for compatibility/testing)
        header = self.get_header(request)
        if header is not None:
            raw_token = self.get_raw_token(header)
            if raw_token is not None:
                try:
                    validated_token = self.get_validated_token(raw_token)
                    return self.get_user(validated_token), validated_token
                except Exception:
                    pass
        
        # 2. Try to get token from cookies
        raw_token = request.COOKIES.get('access_token')
        if raw_token is None:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
            return self.get_user(validated_token), validated_token
        except (InvalidToken, AuthenticationFailed):
            return None
