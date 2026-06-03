import json
from django.core.management.base import BaseCommand
from django.conf import settings
from crypto_access.models import SystemSetting

DEFAULT_ACTION_PERMISSION_MAP = {
    'read': ['file_read', 'file_view', 'file_read_limited', 'file_download', '*'],
    'download': ['file_download', '*'],
    'write': ['file_create', 'file_write', 'file_upload', '*'],
    'update': ['file_update', 'file_write', '*'],
    'delete': ['file_delete', '*'],
    'upload': ['file_upload', '*'],
    'encrypt': ['file_encrypt', 'key_manage', '*'],
    'decrypt': ['file_decrypt', 'key_manage', '*'],
    'manage': ['*'],
}

DEFAULT_ACTION_ALIASES = {
    'read': ['read', 'download'],
    'view': ['view', 'read', 'download'],
    'download': ['download'],
    'write': ['write'],
    'create': ['create', 'write'],
    'upload': ['upload', 'write', 'create'],
    'delete': ['delete', 'write']
}

class Command(BaseCommand):
    help = 'Initialize default dynamic settings in the database'

    def handle(self, *args, **kwargs):
        self.stdout.write("Initializing system settings...")

        # 1. ACTION_PERMISSION_MAP
        setting, created = SystemSetting.objects.get_or_create(
            key='ACTION_PERMISSION_MAP',
            defaults={
                'value': DEFAULT_ACTION_PERMISSION_MAP,
                'description': 'Map action names to required base permissions for RBAC layer.'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS("Created ACTION_PERMISSION_MAP"))
        else:
            self.stdout.write("ACTION_PERMISSION_MAP already exists.")

        # 2. ACTION_ALIASES
        setting, created = SystemSetting.objects.get_or_create(
            key='ACTION_ALIASES',
            defaults={
                'value': DEFAULT_ACTION_ALIASES,
                'description': 'Map actions to their implied sub-actions for ABAC layer (e.g. read -> read, download).'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS("Created ACTION_ALIASES"))
        else:
            self.stdout.write("ACTION_ALIASES already exists.")

        # 3. ABAC_PROTECTED_ROUTES
        default_routes = getattr(settings, 'ABAC_PROTECTED_ROUTES', [])
        setting, created = SystemSetting.objects.get_or_create(
            key='ABAC_PROTECTED_ROUTES',
            defaults={
                'value': default_routes,
                'description': 'List of API routes protected by ABAC middleware. Uses regex for patterns.'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS("Created ABAC_PROTECTED_ROUTES"))
        else:
            self.stdout.write("ABAC_PROTECTED_ROUTES already exists.")

        self.stdout.write(self.style.SUCCESS("Successfully initialized system settings!"))
