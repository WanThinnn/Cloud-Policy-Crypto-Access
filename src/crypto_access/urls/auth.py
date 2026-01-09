"""
Authentication URLs
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from ..views import auth

# Separate URL patterns for template pages and API endpoints
# Template pages are included via /auth/ prefix in config/urls.py
# API endpoints are included via /api/auth/ prefix in config/urls.py

urlpatterns = [
    # These work for both /auth/* and /api/auth/* prefixes
    # Template pages: /auth/login/, /auth/register/
    # API endpoints: /api/auth/login/, /api/auth/register/
    path('login/', auth.login, name='login'),
    path('register/', auth.register, name='register'),
    path('logout/', auth.logout, name='logout'),
    
    # JWT Token refresh
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Password Management
    path('change-password/', auth.change_password, name='change_password'),
    path('password-reset/request/', auth.password_reset_request, name='password_reset_request'),
    path('password-reset/confirm/', auth.password_reset_confirm, name='password_reset_confirm'),
    
    # User Profile
    path('profile/', auth.user_profile, name='user_profile'),
]

# Separate patterns for template pages (accessed via /auth/ prefix)
template_patterns = [
    path('login/', auth.login_page, name='login_page'),
    path('register/', auth.register_page, name='register_page'),
]
