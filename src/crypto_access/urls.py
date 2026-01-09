"""
URL configuration for crypto_access app.
"""

from django.urls import path
from . import views

app_name = 'crypto_access'

urlpatterns = [
    path('', views.index, name='index'),
    path('health/', views.health_check, name='health_check'),
]
