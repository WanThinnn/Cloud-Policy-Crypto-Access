"""
PKI Views - API endpoints for ML-DSA-87 Public Key Management
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ..models import UserPublicKey
from ..serializers.pki import UserPublicKeySerializer


class UserPublicKeyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user PQC keys for Dual-Layer Signatures.
    """
    serializer_class = UserPublicKeySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Users can only see their own keys, unless they are an admin
        if self.request.user.is_superuser:
            qs = UserPublicKey.objects.all()
            user_id = self.request.query_params.get('user')
            if user_id:
                qs = qs.filter(user_id=user_id)
            return qs
        return UserPublicKey.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_keys(self, request):
        """Get all keys belonging to the current user"""
        keys = self.get_queryset()
        serializer = self.get_serializer(keys, many=True)
        return Response(serializer.data)
        
    @action(detail=False, methods=['get'])
    def active_key(self, request):
        """Get the current active key for the user"""
        key = self.get_queryset().filter(status='active').order_by('-created_at').first()
        if not key:
            return Response({'error': 'No active key found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(key)
        return Response(serializer.data)
        
    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """Revoke a specific key"""
        key = self.get_object()
        if key.status == 'revoked':
            return Response({'message': 'Key is already revoked'}, status=status.HTTP_400_BAD_REQUEST)
            
        key.revoke()
        return Response({'message': 'Key revoked successfully'})
