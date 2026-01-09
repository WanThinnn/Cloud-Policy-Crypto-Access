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
            'description': 'Quản trị viên cao nhất - Quản lý hệ thống, người dùng, chính sách, khóa',
            'permissions': ['*'],
            'is_system': True,
        },
        {
            'code': 'admin',
            'name': 'Admin',
            'description': 'Quản trị viên phòng ban - Quản lý người dùng trong phạm vi phòng ban',
            'permissions': ['user_management_department', 'file_view', 'policy_view'],
            'is_system': True,
        },
        {
            'code': 'data_owner',
            'name': 'Data Owner',
            'description': 'Chủ sở hữu dữ liệu - Tạo, mã hóa, định nghĩa chính sách file',
            'permissions': ['file_create', 'file_encrypt', 'file_upload', 'policy_define', 'file_share'],
            'is_system': True,
        },
        {
            'code': 'data_user',
            'name': 'Data User',
            'description': 'Người dùng dữ liệu - Đọc/ghi file theo chính sách được cấp',
            'permissions': ['file_read', 'file_download'],
            'is_system': True,
        },
        {
            'code': 'auditor',
            'name': 'Auditor',
            'description': 'Kiểm toán viên - Chỉ xem logs và báo cáo, không truy cập nội dung',
            'permissions': ['logs_view', 'reports_view', 'audit_export'],
            'is_system': True,
        },
        {
            'code': 'guest',
            'name': 'Guest',
            'description': 'Khách - Quyền hạn chế, thời hạn ngắn',
            'permissions': ['file_read_limited'],
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
            'display_name': 'Phòng ban',
            'data_type': 'enum',
            'allowed_values': ['hr', 'finance', 'it', 'operations', 'executive', 'security'],
            'is_required': True,
            'description': 'Phòng ban của nhân viên',
        },
        {
            'name': 'role',
            'display_name': 'Chức vụ',
            'data_type': 'enum',
            'allowed_values': ['intern', 'employee', 'manager', 'director', 'ceo'],
            'is_required': True,
            'description': 'Chức vụ trong tổ chức',
        },
        {
            'name': 'clearance_level',
            'display_name': 'Mức độ bảo mật',
            'data_type': 'enum',
            'allowed_values': ['public', 'confidential', 'secret', 'top_secret'],
            'default_value': 'public',
            'is_required': True,
            'description': 'Mức độ bảo mật được cấp phép truy cập',
        },
        {
            'name': 'location',
            'display_name': 'Địa điểm làm việc',
            'data_type': 'string',
            'is_required': False,
            'description': 'Địa điểm làm việc (e.g., hcm_office, hanoi_office)',
        },
        {
            'name': 'data_access',
            'display_name': 'Mức truy cập dữ liệu',
            'data_type': 'enum',
            'allowed_values': ['basic', 'advanced', 'full'],
            'default_value': 'basic',
            'is_required': True,
            'description': 'Mức độ truy cập dữ liệu được cấp',
        },
        {
            'name': 'employment_status',
            'display_name': 'Trạng thái công việc',
            'data_type': 'enum',
            'allowed_values': ['active', 'inactive', 'terminated', 'on_leave'],
            'default_value': 'active',
            'is_required': True,
            'description': 'Trạng thái làm việc hiện tại',
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
