"""
Serializers for ABAC attribute management
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from ..models import UserType, AttributeDefinition, UserAttribute


class UserTypeSerializer(serializers.ModelSerializer):
    """Serializer for UserType model"""
    
    class Meta:
        model = UserType
        fields = [
            'id', 'code', 'name', 'description', 
            'is_system', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_code(self, value):
        """Ensure code is lowercase and contains only valid characters"""
        import re
        if not re.match(r'^[a-z][a-z0-9_]*$', value):
            raise serializers.ValidationError(
                "Code must start with lowercase letter and contain only lowercase letters, numbers, and underscores"
            )
        return value
    
    def validate(self, data):
        """Prevent modification of system types"""
        if self.instance and self.instance.is_system:
            # Check if protected fields are actually being changed to a different value
            protected_fields = {'code', 'name'}
            changed_protected = set()
            for field in protected_fields:
                if field in data and data[field] != getattr(self.instance, field):
                    changed_protected.add(field)
            if changed_protected:
                raise serializers.ValidationError(
                    f"Cannot modify these fields for system types: {changed_protected}"
                )
        return data


class AttributeDefinitionSerializer(serializers.ModelSerializer):
    """Serializer for AttributeDefinition model"""
    
    class Meta:
        model = AttributeDefinition
        fields = [
            'id', 'name', 'display_name', 'data_type',
            'allowed_values', 'default_value', 'is_required',
            'description', 'is_active', 'version',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']
    
    def validate_name(self, value):
        """Ensure name is lowercase and valid identifier"""
        import re
        if not re.match(r'^[a-z][a-z0-9_]*$', value):
            raise serializers.ValidationError(
                "Name must start with lowercase letter and contain only lowercase letters, numbers, and underscores"
            )
        return value
    
    def validate(self, data):
        """Validate allowed_values for enum type"""
        data_type = data.get('data_type', self.instance.data_type if self.instance else 'string')
        allowed_values = data.get('allowed_values')
        
        if data_type == 'enum':
            if not allowed_values or not isinstance(allowed_values, list):
                raise serializers.ValidationError({
                    'allowed_values': 'Enum type requires a list of allowed values'
                })
            if len(allowed_values) == 0:
                raise serializers.ValidationError({
                    'allowed_values': 'Enum type requires at least one allowed value'
                })
        
        # Validate default_value if provided
        default_value = data.get('default_value')
        if default_value and data_type == 'enum' and allowed_values:
            if default_value not in allowed_values:
                raise serializers.ValidationError({
                    'default_value': f'Default value must be one of: {allowed_values}'
                })
        
        return data


class UserAttributeSerializer(serializers.ModelSerializer):
    """Serializer for reading UserAttribute"""
    attribute_name = serializers.CharField(source='attribute.name', read_only=True)
    attribute_display_name = serializers.CharField(source='attribute.display_name', read_only=True)
    attribute_type = serializers.CharField(source='attribute.data_type', read_only=True)
    updated_by_username = serializers.CharField(source='updated_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = UserAttribute
        fields = [
            'id', 'user', 'attribute', 'attribute_name', 
            'attribute_display_name', 'attribute_type',
            'value', 'status', 'effective_date', 'expiry_date',
            'version', 'updated_by', 'updated_by_username',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class UserAttributeAssignSerializer(serializers.Serializer):
    """Serializer for assigning a single attribute to user"""
    attribute_name = serializers.CharField(max_length=50)
    value = serializers.CharField(max_length=255)
    effective_date = serializers.DateTimeField(required=False)
    expiry_date = serializers.DateTimeField(required=False, allow_null=True)
    
    def validate_attribute_name(self, value):
        """Check attribute exists"""
        try:
            AttributeDefinition.objects.get(name=value, is_active=True)
        except AttributeDefinition.DoesNotExist:
            raise serializers.ValidationError(f"Attribute '{value}' does not exist or is inactive")
        return value
    
    def validate(self, data):
        """Validate the value against attribute definition"""
        attr_name = data.get('attribute_name')
        value = data.get('value')
        
        try:
            attr_def = AttributeDefinition.objects.get(name=attr_name)
            is_valid, error = attr_def.validate_value(value)
            if not is_valid:
                raise serializers.ValidationError({'value': error})
        except AttributeDefinition.DoesNotExist:
            pass  # Already validated in validate_attribute_name
        
        return data


class UserAttributeBulkAssignSerializer(serializers.Serializer):
    """Serializer for bulk assigning attributes to user"""
    attributes = serializers.ListField(
        child=UserAttributeAssignSerializer(),
        min_length=1,
        max_length=20
    )
    
    def validate_attributes(self, value):
        """Check for duplicate attribute names"""
        names = [item['attribute_name'] for item in value]
        if len(names) != len(set(names)):
            raise serializers.ValidationError("Duplicate attribute names found")
        return value


class UserWithAttributesSerializer(serializers.ModelSerializer):
    """Serializer for user with their ABAC attributes"""
    attributes = serializers.SerializerMethodField()
    user_type = serializers.SerializerMethodField()
    full_name = serializers.CharField(source='profile.full_name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name', 'user_type', 'attributes']
    
    def get_attributes(self, obj):
        """Get user's active ABAC attributes"""
        return UserAttribute.get_user_attributes(obj)
    
    def get_user_type(self, obj):
        """Get user type info"""
        if hasattr(obj, 'profile'):
            if obj.profile.user_type_ref:
                return {
                    'code': obj.profile.user_type_ref.code,
                    'name': obj.profile.user_type_ref.name
                }
            return {
                'code': obj.profile.user_type,
                'name': obj.profile.get_user_type_display()
            }
        return None
