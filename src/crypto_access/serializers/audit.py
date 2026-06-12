from rest_framework import serializers
from crypto_access.models import AccessLog, KeyRevocation
from django.contrib.auth.models import User

class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class AccessLogSerializer(serializers.ModelSerializer):
    user = UserSimpleSerializer(read_only=True)
    
    class Meta:
        model = AccessLog
        fields = [
            'id', 'log_id', 'user', 'resource_type', 'resource_id',
            'action', 'result', 'policies_evaluated', 'policies_matched',
            'user_attributes', 'environment_attributes', 'request_path',
            'request_method', 'error_message', 'timestamp',
            'log_hash', 'previous_hash'
        ]
        read_only_fields = fields

class KeyRevocationSerializer(serializers.ModelSerializer):
    user = UserSimpleSerializer(read_only=True)
    revoked_by = UserSimpleSerializer(read_only=True)
    
    class Meta:
        model = KeyRevocation
        fields = [
            'id', 'revocation_id', 'user', 'key_id', 'key_version',
            'reason', 'reason_detail', 'old_attributes', 'new_attributes',
            'status', 'new_key_id', 'revoked_at', 'reissued_at', 'revoked_by'
        ]
        read_only_fields = fields
