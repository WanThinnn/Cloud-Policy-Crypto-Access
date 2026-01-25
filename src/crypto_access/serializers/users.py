"""
Serializers for User Management
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from ..models import UserProfile, UserType


class UserCreateSerializer(serializers.Serializer):
    """Serializer for creating new users"""
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(required=False, write_only=True, min_length=8)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    full_name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    user_type = serializers.CharField(required=False, default='data_user')
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)
    account_status = serializers.ChoiceField(
        choices=['pending', 'active', 'inactive', 'suspended'],
        default='active'
    )
    account_expiry_date = serializers.DateTimeField(required=False, allow_null=True)
    
    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Username đã tồn tại')
        return value
    
    def validate_email(self, value):
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email đã được sử dụng')
        return value
    
    def validate_user_type(self, value):
        if not UserType.objects.filter(code=value).exists():
            raise serializers.ValidationError(f'Loại người dùng "{value}" không tồn tại')
        return value


class UserProfileInlineSerializer(serializers.ModelSerializer):
    """Inline serializer for UserProfile"""
    user_type_code = serializers.SerializerMethodField()
    user_type_name = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'full_name', 'phone', 'account_status', 
            'account_expiry_date', 'user_type_code', 'user_type_name',
            'is_email_verified', 'created_at', 'updated_at'
        ]
    
    def get_user_type_code(self, obj):
        return obj.get_user_type_code()
    
    def get_user_type_name(self, obj):
        if obj.user_type_ref:
            return obj.user_type_ref.name
        return obj.user_type


class UserManagementSerializer(serializers.ModelSerializer):
    """Serializer for User management with profile"""
    profile = UserProfileInlineSerializer(read_only=True)
    user_type = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    account_status = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_active', 'is_staff', 'is_superuser', 'date_joined', 'last_login',
            'profile', 'user_type', 'full_name', 'account_status'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']
    
    def get_user_type(self, obj):
        if hasattr(obj, 'profile') and obj.profile:
            return obj.profile.get_user_type_code()
        return None
    
    def get_full_name(self, obj):
        if hasattr(obj, 'profile') and obj.profile:
            return obj.profile.full_name
        return f"{obj.first_name} {obj.last_name}".strip()
    
    def get_account_status(self, obj):
        if hasattr(obj, 'profile') and obj.profile:
            return obj.profile.account_status
        return 'unknown'
