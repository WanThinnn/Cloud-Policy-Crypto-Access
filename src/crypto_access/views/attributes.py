"""
Views for ABAC attribute management
Super Admin APIs for managing UserTypes, AttributeDefinitions, and UserAttributes
"""

from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from ..models import UserType, AttributeDefinition, UserAttribute
from ..serializers import (
    UserTypeSerializer,
    AttributeDefinitionSerializer,
    UserAttributeSerializer,
    UserAttributeAssignSerializer,
    UserAttributeBulkAssignSerializer,
    UserWithAttributesSerializer,
)
from ..permissions import IsSuperAdmin, IsAdminOrSuperAdmin, CanManageAttributes


# =============================================================================
# Template Views (HTML Pages) - Permission check done via API
# =============================================================================

def user_types_page(request):
    """Render user types management page"""
    return render(request, 'admin/user_types.html')


def attributes_page(request):
    """Render attribute definitions management page"""
    return render(request, 'admin/attributes.html')


def user_attributes_page(request):
    """Render user attributes management page"""
    return render(request, 'admin/user_attributes.html')


# =============================================================================
# UserType ViewSet
# =============================================================================

class UserTypeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing UserTypes
    Only Super Admin can create/update/delete
    """
    queryset = UserType.objects.all()
    serializer_class = UserTypeSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Filter system types
        is_system = self.request.query_params.get('is_system')
        if is_system is not None:
            queryset = queryset.filter(is_system=is_system.lower() == 'true')
        
        return queryset
    
    def destroy(self, request, *args, **kwargs):
        """Prevent deletion of system types"""
        instance = self.get_object()
        if instance.is_system:
            return Response(
                {'error': 'Cannot delete system user types'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)


# =============================================================================
# AttributeDefinition ViewSet
# =============================================================================

class AttributeDefinitionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing AttributeDefinitions (BM9)
    Only Super Admin can create/update/delete
    """
    queryset = AttributeDefinition.objects.all()
    serializer_class = AttributeDefinitionSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Filter by required
        is_required = self.request.query_params.get('is_required')
        if is_required is not None:
            queryset = queryset.filter(is_required=is_required.lower() == 'true')
        
        # Filter by data type
        data_type = self.request.query_params.get('data_type')
        if data_type:
            queryset = queryset.filter(data_type=data_type)
        
        return queryset
    
    def perform_update(self, serializer):
        """Increment version on update"""
        instance = serializer.save()
        instance.version += 1
        instance.save()


# =============================================================================
# UserAttribute APIs
# =============================================================================

@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOrSuperAdmin])
def list_user_attributes(request, user_id):
    """
    GET /api/admin/users/<user_id>/attributes/
    List all attributes for a specific user
    """
    user = get_object_or_404(User, pk=user_id)
    
    attributes = UserAttribute.objects.filter(user=user).select_related('attribute', 'updated_by')
    serializer = UserAttributeSerializer(attributes, many=True)
    
    # Get user type info
    user_type_info = None
    if hasattr(user, 'profile'):
        profile = user.profile
        if profile.user_type_ref:
            user_type_info = {
                'code': profile.user_type_ref.code,
                'name': profile.user_type_ref.name
            }
        else:
            user_type_info = {
                'code': profile.user_type,
                'name': profile.get_user_type_display()
            }
    
    return Response({
        'user_id': user_id,
        'username': user.username,
        'email': user.email,
        'full_name': getattr(user.profile, 'full_name', '') if hasattr(user, 'profile') else '',
        'user_type': user_type_info,
        'attributes': serializer.data,
        'active_attributes': UserAttribute.get_user_attributes(user)
    })


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated, CanManageAttributes])
def assign_user_attribute(request, user_id):
    """
    POST /api/admin/users/<user_id>/attributes/
    Assign or update a single attribute for user
    """
    user = get_object_or_404(User, pk=user_id)
    
    serializer = UserAttributeAssignSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    try:
        user_attr = UserAttribute.set_user_attribute(
            user=user,
            attribute_name=data['attribute_name'],
            value=data['value'],
            updated_by=request.user
        )
        
        # Update effective/expiry dates if provided
        if 'effective_date' in data:
            user_attr.effective_date = data['effective_date']
        if 'expiry_date' in data:
            user_attr.expiry_date = data['expiry_date']
        user_attr.save()
        
        return Response({
            'message': f"Attribute '{data['attribute_name']}' assigned successfully",
            'attribute': UserAttributeSerializer(user_attr).data
        }, status=status.HTTP_201_CREATED)
        
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated, CanManageAttributes])
def bulk_assign_user_attributes(request, user_id):
    """
    POST /api/admin/users/<user_id>/attributes/bulk/
    Assign multiple attributes at once
    """
    user = get_object_or_404(User, pk=user_id)
    
    serializer = UserAttributeBulkAssignSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    results = []
    errors = []
    
    for attr_data in serializer.validated_data['attributes']:
        try:
            user_attr = UserAttribute.set_user_attribute(
                user=user,
                attribute_name=attr_data['attribute_name'],
                value=attr_data['value'],
                updated_by=request.user
            )
            results.append({
                'attribute_name': attr_data['attribute_name'],
                'value': attr_data['value'],
                'status': 'success'
            })
        except ValueError as e:
            errors.append({
                'attribute_name': attr_data['attribute_name'],
                'error': str(e)
            })
    
    return Response({
        'message': f"Assigned {len(results)} attributes, {len(errors)} errors",
        'results': results,
        'errors': errors
    }, status=status.HTTP_201_CREATED if results else status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['DELETE'])
@permission_classes([IsAuthenticated, CanManageAttributes])
def delete_user_attribute(request, user_id, attribute_id):
    """
    DELETE /api/admin/users/<user_id>/attributes/<attribute_id>/
    Remove an attribute from user
    """
    user = get_object_or_404(User, pk=user_id)
    user_attr = get_object_or_404(UserAttribute, pk=attribute_id, user=user)
    
    attr_name = user_attr.attribute.name
    user_attr.delete()
    
    return Response({
        'message': f"Attribute '{attr_name}' removed from user '{user.username}'"
    })


@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOrSuperAdmin])
def list_users_with_attributes(request):
    """
    GET /api/admin/users-with-attributes/
    List all users with their ABAC attributes
    """
    users = User.objects.select_related('profile').all()
    
    # Filter by department
    department = request.query_params.get('department')
    if department:
        user_ids = UserAttribute.objects.filter(
            attribute__name='department',
            value=department,
            status='active'
        ).values_list('user_id', flat=True)
        users = users.filter(id__in=user_ids)
    
    # Filter by user type
    user_type = request.query_params.get('user_type')
    if user_type:
        users = users.filter(profile__user_type=user_type)
    
    serializer = UserWithAttributesSerializer(users, many=True)
    return Response({'users': serializer.data})


@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_policy_builder_attributes(request):
    """
    GET /api/attributes/policy-builder/
    Get all attribute definitions with their possible values for Policy Builder UI
    Returns dynamic data from database instead of hardcoded values
    """
    # Get all active attribute definitions
    attributes = AttributeDefinition.objects.filter(is_active=True).order_by('display_order', 'name')
    
    result = []
    for attr in attributes:
        attr_data = {
            'key': attr.name,
            'label': attr.display_name or attr.name.replace('_', ' ').title(),
            'data_type': attr.data_type,
            'is_required': attr.is_required,
        }
        
        # Get possible values based on data type
        if attr.data_type == 'enum' and attr.allowed_values:
            attr_data['values'] = attr.allowed_values
        elif attr.data_type == 'boolean':
            attr_data['values'] = ['true', 'false']
        else:
            # For string/number types, get distinct values from user attributes
            distinct_values = UserAttribute.objects.filter(
                attribute=attr,
                status='active'
            ).values_list('value', flat=True).distinct()
            attr_data['values'] = list(distinct_values) if distinct_values else []
        
        result.append(attr_data)
    
    # Also include user_type from UserType model
    user_types = UserType.objects.filter(is_active=True).values_list('code', flat=True)
    if user_types:
        # Check if user_type is already in result
        has_user_type = any(a['key'] == 'user_type' for a in result)
        if not has_user_type:
            result.insert(0, {
                'key': 'user_type',
                'label': 'Loại người dùng',
                'data_type': 'choice',
                'values': list(user_types),
                'is_required': True
            })
    
    return Response(result)
