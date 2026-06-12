from rest_framework import serializers
from ..models import ActiveSession

class ActiveSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActiveSession
        fields = [
            'id', 'session_key', 'device_name', 'browser', 'os_name', 
            'ip_address', 'location', 'last_active', 'is_active', 'created_at'
        ]
        read_only_fields = fields
