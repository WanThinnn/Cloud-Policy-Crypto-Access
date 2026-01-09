"""
Seed ABAC Policies for testing
Run via: python manage.py seed_abac_policies
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from crypto_access.models import AccessPolicy


class Command(BaseCommand):
    help = 'Seed ABAC policies for document access control'
    
    def handle(self, *args, **options):
        self.stdout.write('Creating ABAC policies...\n')
        
        # Get admin user for created_by
        admin = User.objects.filter(is_superuser=True).first()
        
        # Define policies
        policies = [
            # Admin policies - Full document access
            {
                'name': 'Admin Document Read',
                'description': 'Admins có thể đọc tất cả tài liệu',
                'subject_condition': "r.sub.user_type == 'admin'",
                'resource': 'document',
                'action': 'read',
                'effect': 'allow',
                'priority': 10,
            },
            {
                'name': 'Admin Document Download',
                'description': 'Admins có thể download tất cả tài liệu',
                'subject_condition': "r.sub.user_type == 'admin'",
                'resource': 'document',
                'action': 'download',
                'effect': 'allow',
                'priority': 10,
            },
            {
                'name': 'Admin Document Upload',
                'description': 'Admins có thể upload tài liệu',
                'subject_condition': "r.sub.user_type == 'admin'",
                'resource': 'document',
                'action': 'upload',
                'effect': 'allow',
                'priority': 10,
            },
            {
                'name': 'Admin Document Write',
                'description': 'Admins có thể tạo/sửa tài liệu',
                'subject_condition': "r.sub.user_type == 'admin'",
                'resource': 'document',
                'action': 'write',
                'effect': 'allow',
                'priority': 10,
            },
            {
                'name': 'Admin Document Delete',
                'description': 'Admins có thể xóa tài liệu',
                'subject_condition': "r.sub.user_type == 'admin'",
                'resource': 'document',
                'action': 'delete',
                'effect': 'allow',
                'priority': 10,
            },
            
            # Data Owner policies
            {
                'name': 'Data Owner Read',
                'description': 'Data Owners có thể đọc tài liệu',
                'subject_condition': "r.sub.user_type == 'data_owner'",
                'resource': 'document',
                'action': 'read',
                'effect': 'allow',
                'priority': 20,
            },
            {
                'name': 'Data Owner Download',
                'description': 'Data Owners có thể download tài liệu',
                'subject_condition': "r.sub.user_type == 'data_owner'",
                'resource': 'document',
                'action': 'download',
                'effect': 'allow',
                'priority': 20,
            },
            {
                'name': 'Data Owner Upload',
                'description': 'Data Owners có thể upload tài liệu',
                'subject_condition': "r.sub.user_type == 'data_owner'",
                'resource': 'document',
                'action': 'upload',
                'effect': 'allow',
                'priority': 20,
            },
            {
                'name': 'Data Owner Write',
                'description': 'Data Owners có thể tạo/sửa tài liệu',
                'subject_condition': "r.sub.user_type == 'data_owner'",
                'resource': 'document',
                'action': 'write',
                'effect': 'allow',
                'priority': 20,
            },
            
            # Department-based access
            {
                'name': 'IT Department Read Access',
                'description': 'Nhân viên IT có thể đọc và download tài liệu',
                'subject_condition': "r.sub.department == 'it'",
                'resource': 'document',
                'action': 'read',
                'effect': 'allow',
                'priority': 30,
            },
            {
                'name': 'IT Department Download',
                'description': 'Nhân viên IT có thể download tài liệu',
                'subject_condition': "r.sub.department == 'it'",
                'resource': 'document',
                'action': 'download',
                'effect': 'allow',
                'priority': 30,
            },
            {
                'name': 'IT Department Upload',
                'description': 'Nhân viên IT có thể upload tài liệu',
                'subject_condition': "r.sub.department == 'it' and r.sub.clearance_level in ['confidential', 'secret', 'top_secret']",
                'resource': 'document',
                'action': 'upload',
                'effect': 'allow',
                'priority': 35,
            },
            
            # HR Department access
            {
                'name': 'HR Department Read Access',
                'description': 'Nhân viên HR có thể đọc tài liệu của phòng mình',
                'subject_condition': "r.sub.department == 'hr'",
                'resource': 'document',
                'action': 'read',
                'effect': 'allow',
                'priority': 40,
            },
            {
                'name': 'HR Manager Upload',
                'description': 'HR Manager có thể upload tài liệu',
                'subject_condition': "r.sub.department == 'hr' and r.sub.role == 'manager'",
                'resource': 'document',
                'action': 'upload',
                'effect': 'allow',
                'priority': 35,
            },
            
            # Finance Department access
            {
                'name': 'Finance Read Access',
                'description': 'Nhân viên Finance có thể đọc tài liệu',
                'subject_condition': "r.sub.department == 'finance' and r.sub.clearance_level in ['secret', 'top_secret']",
                'resource': 'document',
                'action': 'read',
                'effect': 'allow',
                'priority': 40,
            },
            {
                'name': 'Finance Download Access',
                'description': 'Nhân viên Finance có thể download tài liệu',
                'subject_condition': "r.sub.department == 'finance' and r.sub.clearance_level == 'secret'",
                'resource': 'document',
                'action': 'download',
                'effect': 'allow',
                'priority': 40,
            },
            
            # Auditor access
            {
                'name': 'Auditor Read All',
                'description': 'Auditor có thể đọc tất cả tài liệu để kiểm toán',
                'subject_condition': "r.sub.user_type == 'auditor'",
                'resource': 'document',
                'action': 'read',
                'effect': 'allow',
                'priority': 25,
            },
            
            # Deny Guest uploads
            {
                'name': 'Block Guest Upload',
                'description': 'Khách không được phép upload',
                'subject_condition': "r.sub.user_type == 'guest'",
                'resource': 'document',
                'action': 'upload',
                'effect': 'deny',
                'priority': 5,
            },
            {
                'name': 'Block Guest Download',
                'description': 'Khách không được phép download',
                'subject_condition': "r.sub.user_type == 'guest'",
                'resource': 'document',
                'action': 'download',
                'effect': 'deny',
                'priority': 5,
            },
            
            # Admin policy management
            {
                'name': 'Admin Manage Policies',
                'description': 'Admin có thể quản lý policies',
                'subject_condition': "r.sub.user_type in ['admin', 'data_owner']",
                'resource': 'policy',
                'action': 'manage',
                'effect': 'allow',
                'priority': 10,
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for policy_data in policies:
            policy, created = AccessPolicy.objects.update_or_create(
                name=policy_data['name'],
                defaults={
                    'description': policy_data['description'],
                    'subject_condition': policy_data['subject_condition'],
                    'resource': policy_data['resource'],
                    'action': policy_data['action'],
                    'effect': policy_data['effect'],
                    'priority': policy_data['priority'],
                    'is_active': True,
                    'created_by': admin,
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f"  ✓ Created: {policy_data['name']}")
            else:
                updated_count += 1
                self.stdout.write(f"  ↻ Updated: {policy_data['name']}")
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Created {created_count} new policies'))
        self.stdout.write(self.style.SUCCESS(f'↻ Updated {updated_count} existing policies'))
        
        # Display summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write('ABAC Policy Summary:')
        self.stdout.write('='*60)
        
        for policy in AccessPolicy.objects.filter(is_active=True).order_by('priority', 'name'):
            self.stdout.write(f"\n[{policy.priority}] {policy.name}")
            self.stdout.write(f"  Condition: {policy.subject_condition}")
            self.stdout.write(f"  Resource: {policy.resource} | Action: {policy.action} | Effect: {policy.effect}")
