from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from crypto_access.models import AccessLog, KeyRevocation
from crypto_access.serializers.audit import AccessLogSerializer, KeyRevocationSerializer
from django.shortcuts import render

class AccessLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing System Access Logs.
    Only Super Admins can view logs.
    """
    queryset = AccessLog.objects.all().order_by('-timestamp').select_related('user')
    serializer_class = AccessLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['log_id', 'user__username', 'user__email', 'resource_id', 'error_message']
    ordering_fields = ['timestamp', 'user__username', 'result']

class KeyRevocationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing Key Revocations.
    Only Super Admins can view key revocations.
    """
    queryset = KeyRevocation.objects.all().order_by('-revoked_at').select_related('user', 'revoked_by')
    serializer_class = KeyRevocationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['revocation_id', 'user__username', 'key_id', 'reason_detail']
    ordering_fields = ['revoked_at', 'reissued_at', 'user__username', 'status']

def audit_logs_page(request):
    """Render System Logs page"""
    return render(request, 'admin/audit_logs.html')

def key_revocations_page(request):
    """Render Key Revocation List page"""
    return render(request, 'admin/keys.html')
