"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from crypto_access.urls.auth import template_patterns as auth_template_patterns

urlpatterns = [
    path('admin/', admin.site.urls),
    path('__reload__/', include('django_browser_reload.urls')),
    path('', include('crypto_access.urls', namespace='crypto_access')),
    path('auth/', include(auth_template_patterns)),  # Auth template pages (/auth/login/, /auth/register/)
    path('api/auth/', include('crypto_access.urls.auth')),  # Auth API endpoints (/api/auth/login/)
    path('api/storage/', include('crypto_access.urls.storage')),  # Storage API
    path('api/admin/', include('crypto_access.urls.admin')),  # Admin API for ABAC management
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
