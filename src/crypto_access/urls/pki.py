from django.urls import path, include
from rest_framework.routers import DefaultRouter
from ..views.pki import UserPublicKeyViewSet

router = DefaultRouter()
router.register(r'keys', UserPublicKeyViewSet, basename='pki-keys')

urlpatterns = [
    path('', include(router.urls)),
]
