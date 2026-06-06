"""
Seed default UserTypes and AttributeDefinitions (BM9)
"""

from django.db import migrations


def seed_user_types(apps, schema_editor):
    """Create default user types (QĐ1)"""
    UserType = apps.get_model('crypto_access', 'UserType')
    
    user_types = [
        {
            'code': 'super_admin',
            'name': 'Super Admin',
            'description': 'Highest level administrator - Manages system, users, policies, and keys',
            'permissions': ['*'],
            'is_system': True,
        },
        {
            'code': 'admin',
            'name': 'Admin',
            'description': 'Department administrator - Manages users within their department',
            'permissions': ['user_management_department', 'file_view', 'policy_view'],
            'is_system': True,
        },
        {
            'code': 'data_contributor',
            'name': 'Data Contributor',
            'description': 'Data contributor - Can upload files, create policies, encrypt, and view/download other files',
            'permissions': ['file_read', 'file_download', 'file_create', 'file_encrypt', 'file_upload', 'policy_define', 'file_share'],
            'is_system': True,
        },
        {
            'code': 'data_viewer',
            'name': 'Data Viewer',
            'description': 'Data viewer - Only has permission to read and download files according to assigned policies',
            'permissions': ['file_read', 'file_download'],
            'is_system': True,
        },
    ]
    
    for ut in user_types:
        UserType.objects.get_or_create(code=ut['code'], defaults=ut)


def seed_attribute_definitions(apps, schema_editor):
    """Create default attribute definitions (BM9)"""
    AttributeDefinition = apps.get_model('crypto_access', 'AttributeDefinition')
    
    attribute_defs = [
        {
            'name': 'department',
            'display_name': 'Department',
            'data_type': 'enum',
            'allowed_values': ['hr', 'finance', 'it', 'operations', 'executive', 'security'],
            'is_required': True,
            'description': 'Employee department',
        },
        {
            'name': 'role',
            'display_name': 'Role',
            'data_type': 'enum',
            'allowed_values': ['intern', 'employee', 'manager', 'director', 'ceo'],
            'is_required': True,
            'description': 'Role in the organization',
        },
        {
            'name': 'clearance_level',
            'display_name': 'Security clearance level',
            'data_type': 'enum',
            'allowed_values': ['public', 'confidential', 'secret', 'top_secret'],
            'default_value': 'public',
            'is_required': True,
            'description': 'Security clearance level for access',
        },
        {
            'name': 'location',
            'display_name': 'Location',
            'data_type': 'string',
            'is_required': False,
            'description': 'Work location (e.g., hcm_office, hanoi_office)',
        },
        {
            'name': 'data_access',
            'display_name': 'Data access level',
            'data_type': 'enum',
            'allowed_values': ['basic', 'advanced', 'full'],
            'default_value': 'basic',
            'is_required': True,
            'description': 'Granted data access level',
        },
        {
            'name': 'employment_status',
            'display_name': 'Employment status',
            'data_type': 'enum',
            'allowed_values': ['active', 'inactive', 'terminated', 'on_leave'],
            'default_value': 'active',
            'is_required': True,
            'description': 'Current employment status',
        },
    ]
    
    for attr in attribute_defs:
        AttributeDefinition.objects.get_or_create(name=attr['name'], defaults=attr)


def reverse_seed(apps, schema_editor):
    """Reverse migration - remove seeded data"""
    UserType = apps.get_model('crypto_access', 'UserType')
    AttributeDefinition = apps.get_model('crypto_access', 'AttributeDefinition')
    
    UserType.objects.filter(is_system=True).delete()
    AttributeDefinition.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('crypto_access', '0004_attributedefinition_usertype_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_user_types, reverse_seed),
        migrations.RunPython(seed_attribute_definitions, reverse_seed),
    ]
