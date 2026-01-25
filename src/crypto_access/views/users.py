"""
Views for User Management
Create, Update, Delete users with profiles
"""

from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.shortcuts import get_object_or_404, render
from django.db import transaction, models
from django.utils import timezone
import secrets
import string

from ..models import UserProfile, UserType
from ..serializers import UserManagementSerializer, UserCreateSerializer
from ..permissions import IsSuperAdmin, IsAdminOrSuperAdmin


# =============================================================================
# Template View (HTML Page)
# =============================================================================

def users_page(request):
    """Render user management page - permission check done via API"""
    return render(request, 'admin/users.html')


# =============================================================================
# Helper Functions
# =============================================================================

def generate_default_password(length=12):
    """Generate a secure default password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


# =============================================================================
# User Management ViewSet
# =============================================================================

class UserManagementViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Users with their profiles
    Admin can manage users in their department
    Super Admin can manage all users
    """
    queryset = User.objects.select_related('profile', 'profile__user_type_ref').all()
    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserManagementSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by user type
        user_type = self.request.query_params.get('user_type')
        if user_type:
            queryset = queryset.filter(profile__user_type_ref__code=user_type)
        
        # Filter by account status
        account_status = self.request.query_params.get('status')
        if account_status:
            queryset = queryset.filter(profile__account_status=account_status)
        
        # Search by username or full_name
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(username__icontains=search) |
                models.Q(email__icontains=search) |
                models.Q(profile__full_name__icontains=search)
            )
        
        # Exclude superusers from non-superadmin view
        if not self.request.user.is_superuser:
            queryset = queryset.exclude(is_superuser=True)
        
        return queryset.order_by('-date_joined')
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Create a new user with profile"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        # Generate default password if not provided
        password = data.get('password') or generate_default_password()
        
        # Create User
        user = User.objects.create_user(
            username=data['username'],
            email=data.get('email', ''),
            password=password,
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
        )
        
        # Get or create UserType
        user_type_code = data.get('user_type', 'data_user')
        user_type = UserType.objects.filter(code=user_type_code).first()
        
        # Create UserProfile
        profile = UserProfile.objects.create(
            user=user,
            full_name=data.get('full_name', f"{user.first_name} {user.last_name}".strip()),
            user_type_ref=user_type,
            user_type=user_type_code,  # Legacy field
            account_status=data.get('account_status', 'active'),
            account_expiry_date=data.get('account_expiry_date'),
            phone=data.get('phone', ''),
        )
        
        # Return created user info
        response_data = UserManagementSerializer(user).data
        
        # Include generated password only on creation
        if not data.get('password'):
            response_data['generated_password'] = password
            response_data['password_note'] = 'Mật khẩu được tạo tự động. Vui lòng lưu lại và gửi cho người dùng.'
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        """Update user and profile"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        data = request.data
        
        # Update User fields
        if 'email' in data:
            instance.email = data['email']
        if 'first_name' in data:
            instance.first_name = data['first_name']
        if 'last_name' in data:
            instance.last_name = data['last_name']
        if 'is_active' in data:
            instance.is_active = data['is_active']
        
        instance.save()
        
        # Update Profile fields
        if hasattr(instance, 'profile'):
            profile = instance.profile
            
            if 'full_name' in data:
                profile.full_name = data['full_name']
            if 'phone' in data:
                profile.phone = data['phone']
            if 'account_status' in data:
                profile.account_status = data['account_status']
            if 'account_expiry_date' in data:
                profile.account_expiry_date = data['account_expiry_date']
            
            # Update user type
            if 'user_type' in data:
                user_type = UserType.objects.filter(code=data['user_type']).first()
                profile.user_type_ref = user_type
                profile.user_type = data['user_type']  # Legacy
            
            profile.save()
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """Delete user and all related data"""
        user = self.get_object()
        
        # Prevent deleting superusers
        if user.is_superuser:
            return Response({
                'error': 'Không thể xóa tài khoản superuser'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Prevent self-deletion
        if user.id == request.user.id:
            return Response({
                'error': 'Không thể xóa chính tài khoản của bạn'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        username = user.username
        
        try:
            # Delete related records first (to avoid FK constraint)
            # Import here to avoid circular imports
            from ..models import AccessLog, KeyRevocation, UserAttribute, UploadedFile
            
            # Delete access logs
            AccessLog.objects.filter(user=user).delete()
            
            # Delete key revocations  
            KeyRevocation.objects.filter(user=user).delete()
            
            # Delete user attributes
            UserAttribute.objects.filter(user=user).delete()
            
            # Set uploaded files owner to None or delete
            UploadedFile.objects.filter(uploaded_by=user).update(uploaded_by=None)
            
            # Delete profile (if exists)
            if hasattr(user, 'profile'):
                user.profile.delete()
            
            # Finally delete the user
            user.delete()
            
            return Response({
                'success': True,
                'message': f'Đã xóa người dùng {username}'
            })
            
        except Exception as e:
            return Response({
                'error': f'Lỗi khi xóa người dùng: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        """Reset user password to a new generated password"""
        user = self.get_object()
        
        # Check if custom password provided
        new_password = request.data.get('password')
        
        if new_password:
            # Use provided password
            user.set_password(new_password)
            user.save()
            return Response({
                'success': True,
                'message': f'Đã đặt mật khẩu mới cho {user.username}'
            })
        else:
            # Generate new password
            new_password = generate_default_password()
            user.set_password(new_password)
            user.save()
            return Response({
                'success': True,
                'message': f'Đã reset mật khẩu cho {user.username}',
                'new_password': new_password,
                'note': 'Vui lòng lưu lại mật khẩu này và gửi cho người dùng.'
            })
    
    @action(detail=True, methods=['post'])
    def toggle_status(self, request, pk=None):
        """Toggle user account status (active/inactive)"""
        user = self.get_object()
        
        if hasattr(user, 'profile'):
            profile = user.profile
            if profile.account_status == 'active':
                profile.account_status = 'inactive'
                message = f'Đã vô hiệu hóa tài khoản {user.username}'
            else:
                profile.account_status = 'active'
                message = f'Đã kích hoạt tài khoản {user.username}'
            profile.save()
            
            return Response({
                'success': True,
                'message': message,
                'new_status': profile.account_status
            })
        
        return Response({
            'error': 'User profile not found'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get user statistics"""
        total = User.objects.count()
        by_type = {}
        by_status = {}
        
        for profile in UserProfile.objects.select_related('user_type_ref').all():
            # Count by type
            type_code = profile.get_user_type_code()
            by_type[type_code] = by_type.get(type_code, 0) + 1
            
            # Count by status
            by_status[profile.account_status] = by_status.get(profile.account_status, 0) + 1
        
        return Response({
            'total_users': total,
            'by_type': by_type,
            'by_status': by_status
        })
