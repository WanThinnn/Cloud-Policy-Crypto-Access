"""
AccessPolicy Serializer for ABAC Admin API
"""

from rest_framework import serializers
from crypto_access.models import AccessPolicy
import re


class AccessPolicySerializer(serializers.ModelSerializer):
    """Serializer for AccessPolicy CRUD operations"""
    
    created_by_username = serializers.CharField(
        source='created_by.username',
        read_only=True
    )
    
    class Meta:
        model = AccessPolicy
        fields = [
            'id',
            'name',
            'description',
            'subject_condition',
            'resource',
            'action',
            'effect',
            'priority',
            'is_active',
            'created_by',
            'created_by_username',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'created_by_username']
    
    def validate_name(self, value):
        """Validate policy name format"""
        if not re.match(r'^[a-z][a-z0-9_]*$', value):
            raise serializers.ValidationError(
                "Name must be lowercase letters, numbers, and underscores, starting with a letter"
            )
        return value
    
    def validate_subject_condition(self, value):
        """Basic validation for subject condition"""
        if not value.strip():
            raise serializers.ValidationError("Subject condition is required")
        
        # Check for basic ABAC pattern
        if 'r.sub.' not in value:
            raise serializers.ValidationError(
                "Subject condition should reference r.sub attributes, e.g., r.sub.department == 'it'"
            )
        return value
    
    def create(self, validated_data):
        """Set created_by to current user"""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class AccessPolicyListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing policies"""
    
    class Meta:
        model = AccessPolicy
        fields = [
            'id',
            'name',
            'subject_condition',
            'resource',
            'action',
            'effect',
            'priority',
            'is_active',
        ]
