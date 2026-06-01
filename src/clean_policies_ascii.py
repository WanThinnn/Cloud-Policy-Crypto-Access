import os
import django

from crypto_access.models import AccessPolicy, AttributeDefinition, UserAttribute, UserProfile
from django.contrib.auth.models import User

def main():
    # 1. Clean up existing policies
    AccessPolicy.objects.all().delete()
    print("Deleted all existing policies.")

    # 2. Create 5 logical policies
    policies = [
        {
            "name": "superadmin_full_access",
            "description": "SuperAdmin full access",
            "subject_condition": "r.sub.user_type == 'super_admin'",
            "cpabe_policy": "user_type:super_admin",
            "resource": "*",
            "action": "*",
            "effect": "allow",
            "priority": 1,
            "is_active": True
        },
        {
            "name": "hr_department_read",
            "description": "HR can read and download hr documents",
            "subject_condition": "r.sub.department == 'hr'",
            "cpabe_policy": "department:hr",
            "resource": "document",
            "action": "read",
            "effect": "allow",
            "priority": 10,
            "is_active": True
        },
        {
            "name": "it_department_download",
            "description": "IT can download and read it docs",
            "subject_condition": "r.sub.department == 'it'",
            "cpabe_policy": "department:it",
            "resource": "document",
            "action": "download",
            "effect": "allow",
            "priority": 10,
            "is_active": True
        },
        {
            "name": "manager_view_only",
            "description": "Manager can preview only",
            "subject_condition": "r.sub.role == 'manager'",
            "cpabe_policy": "role:manager",
            "resource": "document",
            "action": "read",
            "effect": "allow",
            "priority": 20,
            "is_active": True
        },
        {
            "name": "active_employee_write",
            "description": "Active employee can upload docs",
            "subject_condition": "r.sub.employment_status == 'active'",
            "cpabe_policy": "employment_status:active",
            "resource": "document",
            "action": "write",
            "effect": "allow",
            "priority": 50,
            "is_active": True
        }
    ]

    for p in policies:
        AccessPolicy.objects.update_or_create(name=p['name'], defaults=p)
    print(f"Created {len(policies)} logical policies.")

    # 3. Clean up Attributes to make them logical
    # We must delete UserAttributes first
    UserAttribute.objects.all().delete()
    AttributeDefinition.objects.all().delete()
    
    # Create standard attributes
    attrs = [
        {"name": "user_type", "display_name": "Account Type", "data_type": "string"},
        {"name": "department", "display_name": "Department", "data_type": "enum", "allowed_values": ["it", "hr", "marketing", "sales", "finance"]},
        {"name": "role", "display_name": "Role", "data_type": "enum", "allowed_values": ["staff", "manager", "director"]},
        {"name": "employment_status", "display_name": "Status", "data_type": "enum", "allowed_values": ["active", "probation", "suspended"]}
    ]
    
    attr_map = {}
    for a in attrs:
        attr_map[a["name"]] = AttributeDefinition.objects.create(**a)
    
    try:
        superadmin = User.objects.get(username='superadmin')
        UserAttribute.objects.create(user=superadmin, attribute=attr_map['user_type'], value='super_admin')
        UserAttribute.objects.create(user=superadmin, attribute=attr_map['department'], value='it')
        UserAttribute.objects.create(user=superadmin, attribute=attr_map['role'], value='director')
        UserAttribute.objects.create(user=superadmin, attribute=attr_map['employment_status'], value='active')
    except User.DoesNotExist:
        pass
        
    try:
        thienlq = User.objects.get(username='thienlq')
        UserAttribute.objects.create(user=thienlq, attribute=attr_map['user_type'], value='employee')
        UserAttribute.objects.create(user=thienlq, attribute=attr_map['department'], value='it')
        UserAttribute.objects.create(user=thienlq, attribute=attr_map['role'], value='staff')
        UserAttribute.objects.create(user=thienlq, attribute=attr_map['employment_status'], value='active')
    except User.DoesNotExist:
        pass
        
    try:
        hr_user = User.objects.get(username='hr_user')
        UserAttribute.objects.create(user=hr_user, attribute=attr_map['user_type'], value='employee')
        UserAttribute.objects.create(user=hr_user, attribute=attr_map['department'], value='hr')
        UserAttribute.objects.create(user=hr_user, attribute=attr_map['role'], value='manager')
        UserAttribute.objects.create(user=hr_user, attribute=attr_map['employment_status'], value='active')
    except User.DoesNotExist:
        pass

    print("Attributes cleaned and re-assigned logically.")

main()
