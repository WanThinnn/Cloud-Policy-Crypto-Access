"""
PKI Serializers
"""
from rest_framework import serializers
from ..models import UserPublicKey


class UserPublicKeySerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = UserPublicKey
        fields = [
            'id', 'user', 'username', 'pqc_public_key',
            'encrypted_pqc_sk_primary', 'encrypted_pqc_sk_recovery',
            'status', 'device_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'status', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Set the user to the current request user
        validated_data['user'] = self.context['request'].user
        
        # We could potentially revoke all other keys for this user, 
        # or just allow multiple active keys per user. 
        # For now, allow multiple, but let's say the newest one is primary.
        
        return super().create(validated_data)
