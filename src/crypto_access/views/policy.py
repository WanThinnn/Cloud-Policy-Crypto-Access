"""
AccessPolicy Views for ABAC Admin API
"""

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import render

from crypto_access.models import AccessPolicy
from crypto_access.serializers import AccessPolicySerializer, AccessPolicyListSerializer
from rest_framework.permissions import IsAuthenticated


class AccessPolicyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing ABAC Access Policies
    Only Super Admins can manage policies
    """
    queryset = AccessPolicy.objects.all().order_by('priority', 'name')
    serializer_class = AccessPolicySerializer
    permission_classes = [IsAuthenticated]
    
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

    @action(detail=False, methods=['post'])
    def test_policy(self, request):
        """
        Test ABAC syntax and CP-ABE compilation of a policy condition.
        """
        condition = request.data.get('condition', '')
        if not condition:
            return Response({'error': 'Condition is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        import ast
        from crypto_access.services.cpabe_service import cpabe_service
        
        result = {
            'abac_valid': False,
            'cpabe_valid': False,
            'cpabe_policy': None,
            'error': None
        }
        
        # 1. Test ABAC Syntax
        try:
            expr = condition.replace('&&', ' and ').replace('||', ' or ')
            ast.parse(expr, mode='eval')
            result['abac_valid'] = True
        except Exception as e:
            result['error'] = f"ABAC Syntax Error: {str(e)}"
            return Response(result)
            
        # 2. Test CP-ABE compilation
        try:
            # Use dummy policy object to invoke the generator logic
            dummy_policy = AccessPolicy(subject_condition=condition)
            cpabe_str = dummy_policy._generate_cpabe_policy()
            result['cpabe_policy'] = cpabe_str
            
            if not cpabe_str:
                result['error'] = "Generated empty CP-ABE policy."
                return Response(result)
                
            # Attempt to encrypt a dummy buffer to see if libhybrid-cp-abe rejects the syntax
            # The encrypt_buffer function throws CPABEError if the policy syntax is invalid.
            cpabe_service.encrypt_buffer(b"dummy_test_payload", cpabe_str)
            result['cpabe_valid'] = True
            
        except Exception as e:
            result['error'] = f"CP-ABE Compilation Error: {str(e)}"
            
        return Response(result)

    @action(detail=False, methods=['post'])
    def parse_ast(self, request):
        """
        Parse an ABAC condition string into a structured JSON tree for the frontend Visual Query Builder.
        """
        condition = request.data.get('condition', '')
        if not condition:
            return Response({'tree': None})
            
        import ast
        
        def _ast_to_json(node):
            if isinstance(node, ast.BoolOp):
                connector = 'and' if isinstance(node.op, ast.And) else 'or'
                return {
                    'type': 'group',
                    'connector': connector,
                    'children': [child for v in node.values if (child := _ast_to_json(v)) is not None]
                }
            elif isinstance(node, ast.Compare):
                try:
                    attr_name = ""
                    if isinstance(node.left, ast.Attribute):
                        def get_full_name(n):
                            if isinstance(n, ast.Name): return n.id
                            elif isinstance(n, ast.Attribute): return f"{get_full_name(n.value)}.{n.attr}"
                            return ""
                        attr_name = get_full_name(node.left)
                    elif isinstance(node.left, ast.Name):
                        attr_name = node.left.id
                        
                    attr = attr_name.replace('r.sub.', '')
                    
                    op_node = node.ops[0]
                    if isinstance(op_node, ast.Eq): op = '=='
                    elif isinstance(op_node, ast.NotEq): op = '!='
                    elif isinstance(op_node, ast.In): op = 'in'
                    elif isinstance(op_node, ast.NotIn): op = 'not in'
                    else: op = '=='
                    
                    val_node = node.comparators[0]
                    if isinstance(val_node, ast.Constant):
                        val = val_node.value
                    elif isinstance(val_node, ast.List) or isinstance(val_node, ast.Set):
                        val = [v.value if isinstance(v, ast.Constant) else str(v) for v in val_node.elts]
                    else:
                        val = str(val_node)
                        
                    return {
                        'type': 'rule',
                        'attr': attr,
                        'op': op,
                        'value': val
                    }
                except Exception as e:
                    return None
            return None

        try:
            expr = condition.replace('&&', ' and ').replace('||', ' or ')
            tree = ast.parse(expr, mode='eval')
            json_tree = _ast_to_json(tree.body)
            
            # If the root is a single rule, wrap it in a group
            if json_tree and json_tree.get('type') == 'rule':
                json_tree = {
                    'type': 'group',
                    'connector': 'and',
                    'children': [json_tree]
                }
                
            return Response({'tree': json_tree})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)



def policies_page(request):
    """Render the policies admin page - permission check done via API"""
    return render(request, 'admin/policies.html')
