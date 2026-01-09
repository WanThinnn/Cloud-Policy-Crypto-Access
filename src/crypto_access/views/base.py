"""
Base views for crypto_access app.
"""

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status


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
