"""
Storage URL Configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from ..views.storage import StorageBucketViewSet, UploadedFileViewSet

router = DefaultRouter()
router.register('buckets', StorageBucketViewSet, basename='bucket')
router.register('files', UploadedFileViewSet, basename='file')

urlpatterns = [
    path('', include(router.urls)),
]
