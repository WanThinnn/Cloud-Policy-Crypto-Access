"""
Base views for crypto_access app.
"""

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from ..models import AccessPolicy, UploadedFile


def index(request):
    """Main index view"""
    return render(request, 'crypto_access/index.html')


@require_http_methods(["GET"])
def health_check(request):
    """Health check endpoint"""
    return JsonResponse({
        'status': 'healthy',
        'service': 'crypto_access',
    })


@api_view(['GET'])
def api_health(request):
    """API health check endpoint"""
    return Response({
        'status': 'healthy',
        'service': 'crypto_access',
        'version': '1.0.0',
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """API endpoint for dashboard statistics"""
    User = get_user_model()
    
    try:
        total_users = User.objects.count()
        total_policies = AccessPolicy.objects.count()
        total_documents = UploadedFile.objects.filter(is_deleted=False).count()
        total_trash = UploadedFile.objects.filter(is_deleted=True).count()
        
        return Response({
            'users': total_users,
            'policies': total_policies,
            'documents': total_documents,
            'trash': total_trash
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
