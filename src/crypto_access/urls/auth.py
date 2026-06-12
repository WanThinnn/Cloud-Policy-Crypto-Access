"""
Authentication URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from ..views import auth, SessionViewSet, sessions_page

# Separate URL patterns for template pages and API endpoints
# Template pages are included via /auth/ prefix in config/urls.py
# API endpoints are included via /api/auth/ prefix in config/urls.py

router = DefaultRouter()
router.register(r'sessions', SessionViewSet, basename='session')

urlpatterns = [
    path('', include(router.urls)),
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
    
    # User Profile & Permissions
    path('profile/', auth.user_profile, name='user_profile'),
    path('permissions/', auth.user_permissions, name='user_permissions'),
]

from django.contrib.auth import views as auth_views

# Separate patterns for template pages (accessed via /auth/ prefix)
template_patterns = [
    path('login/', auth.login_page, name='login_page'),
    path('register/', auth.register_page, name='register_page'),
    
    # Password Reset
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(template_name='accounts/password_reset.html',
                                              email_template_name='accounts/password_reset_email.txt',
                                              html_email_template_name='accounts/password_reset_email.html',
                                              subject_template_name='accounts/password_reset_subject.txt',
                                              success_url='/auth/password-reset/done/'),
         name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(template_name='accounts/password_reset_done.html'), 
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name='accounts/password_reset_confirm.html',
                                                     success_url='/auth/password-reset-complete/'), 
         name='password_reset_confirm'),
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(template_name='accounts/password_reset_complete.html'), 
         name='password_reset_complete'),
    
    # Sessions Page
    path('sessions/', sessions_page, name='sessions_page'),
]

