"""
URL configuration package for crypto_access app
"""

from django.urls import path, include
from ..views import index, health_check

app_name = 'crypto_access'

# Import storage URLs
from . import storage as storage_urls

urlpatterns = [
    # Base URLs
    path('', index, name='index'),
    path('health/', health_check, name='health_check'),
]
