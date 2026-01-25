"""
AccessPolicy Views for ABAC Admin API
"""

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import render

from crypto_access.models import AccessPolicy
from crypto_access.serializers import AccessPolicySerializer, AccessPolicyListSerializer
from crypto_access.permissions import IsSuperAdmin


class AccessPolicyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing ABAC Access Policies
    Only Super Admins can manage policies
    """
    queryset = AccessPolicy.objects.all().order_by('priority', 'name')
    serializer_class = AccessPolicySerializer
    permission_classes = [IsSuperAdmin]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AccessPolicyListSerializer
        return AccessPolicySerializer
    
    def perform_create(self, serializer):
        """Set created_by and reload Casbin policies"""
        serializer.save(created_by=self.request.user)
        self._reload_casbin_policies()
    
    def perform_update(self, serializer):
        """Reload Casbin policies after update"""
        serializer.save()
        self._reload_casbin_policies()
    
    def perform_destroy(self, instance):
        """Reload Casbin policies after delete"""
        instance.delete()
        self._reload_casbin_policies()
    
    def _reload_casbin_policies(self):
        """Reload policies in Casbin enforcer"""
        try:
            from crypto_access.services.casbin_service import casbin_service
            casbin_service.reload_policies()
        except Exception as e:
            print(f"Warning: Failed to reload Casbin policies: {e}")
    
    @action(detail=False, methods=['post'])
    def reload(self, request):
        """Manually reload all policies into Casbin"""
        self._reload_casbin_policies()
        return Response({'message': 'Policies reloaded successfully'})
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Toggle policy active status"""
        policy = self.get_object()
        policy.is_active = not policy.is_active
        policy.save()
        self._reload_casbin_policies()
        return Response({
            'id': policy.id,
            'name': policy.name,
            'is_active': policy.is_active
        })
    
    @action(detail=False, methods=['get'])
    def resources(self, request):
        """Get list of available resources"""
        return Response([
            {'value': choice[0], 'label': choice[1]}
            for choice in AccessPolicy.RESOURCE_CHOICES
        ])
    
    @action(detail=False, methods=['get'])
    def actions(self, request):
        """Get list of available actions"""
        return Response([
            {'value': choice[0], 'label': choice[1]}
            for choice in AccessPolicy.ACTION_CHOICES
        ])
    
    @action(detail=False, methods=['post'])
    def test_access(self, request):
        """
        Test access decision for debugging Hybrid RBAC+ABAC
        
        Request body:
        {
            "username": "john",  // or "user_id": 1
            "resource": "document",
            "action": "read"
        }
        
        Returns detailed explanation of the decision
        """
        from django.contrib.auth.models import User
        from crypto_access.services.casbin_service import casbin_service
        
        # Get user
        username = request.data.get('username')
        user_id = request.data.get('user_id')
        resource = request.data.get('resource', 'document')
        action = request.data.get('action', 'read')
        
        if not username and not user_id:
            return Response(
                {'error': 'username or user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            if user_id:
                user = User.objects.get(id=user_id)
            else:
                user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get detailed explanation
        explanation = casbin_service.explain_decision(user, resource, action)
        
        return Response(explanation)


def policies_page(request):
    """Render the policies admin page"""
    return render(request, 'admin/policies.html')
