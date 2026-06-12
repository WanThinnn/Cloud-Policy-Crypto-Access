from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
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
    
    @action(detail=False, methods=['post'])
    def verify_chain(self, request):
        """Verify the integrity of the audit log chain.
        Pass ?mode=deep for full O(N) scan. Default is quick O(1) check.
        """
        mode = request.query_params.get('mode', 'quick')
        
        if mode == 'deep':
            result = AccessLog.deep_verify_chain()
            return Response({
                'is_valid': result['is_valid'],
                'mode': result['mode'],
                'corrupted_logs': result.get('corrupted_logs', []),
                'total_checked': result.get('total_checked', 0),
                'detail': f"Deep scan completed. {result.get('total_checked', 0)} logs checked."
            })
        else:
            result = AccessLog.verify_chain_quick()
            return Response({
                'is_valid': result['is_valid'],
                'mode': result['mode'],
                'corrupted_logs': [],
                'detail': result.get('detail', '')
            })
    
    def get_queryset(self):
        queryset = super().get_queryset()
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(timestamp__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__date__lte=end_date)
            
        return queryset

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
    
    def get_queryset(self):
        queryset = super().get_queryset()
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(revoked_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(revoked_at__date__lte=end_date)
            
        return queryset

def audit_logs_page(request):
    """Render System Logs page"""
    return render(request, 'admin/audit_logs.html')

def key_revocations_page(request):
    """Render Key Revocation List page"""
    return render(request, 'admin/keys.html')
