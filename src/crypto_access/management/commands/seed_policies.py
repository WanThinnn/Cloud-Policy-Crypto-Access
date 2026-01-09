"""
Seed default ABAC policies for the system
Run via: python manage.py seed_policies
"""

from django.core.management.base import BaseCommand
from crypto_access.models import AccessPolicy
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Seed default ABAC policies'
    
    def handle(self, *args, **options):
        # Get or create admin user for created_by
        admin = User.objects.filter(is_superuser=True).first()
        
        policies = [
            # Super Admin - full access (highest priority)
            {
                'name': 'super_admin_full_access',
                'description': 'Super admins have full access to all resources',
                'subject_condition': "r.sub.user_type == 'super_admin'",
                'resource': '*',
                'action': '*',
                'effect': 'allow',
                'priority': 1,
            },
            
            # Admin policies
            {
                'name': 'admin_user_management',
                'description': 'Admins can manage users',
                'subject_condition': "r.sub.user_type == 'admin'",
                'resource': 'user',
                'action': 'manage',
                'effect': 'allow',
                'priority': 10,
            },
            {
                'name': 'admin_document_access',
                'description': 'Admins can access all documents',
                'subject_condition': "r.sub.user_type == 'admin'",
                'resource': 'document',
                'action': '*',
                'effect': 'allow',
                'priority': 10,
            },
            {
                'name': 'admin_audit_read',
                'description': 'Admins can read audit logs',
                'subject_condition': "r.sub.user_type == 'admin'",
                'resource': 'audit',
                'action': 'read',
                'effect': 'allow',
                'priority': 10,
            },
            
            # Data Owner policies
            {
                'name': 'data_owner_document_manage',
                'description': 'Data owners can manage documents',
                'subject_condition': "r.sub.user_type == 'data_owner'",
                'resource': 'document',
                'action': 'manage',
                'effect': 'allow',
                'priority': 20,
            },
            {
                'name': 'data_owner_key_manage',
                'description': 'Data owners can manage encryption keys',
                'subject_condition': "r.sub.user_type == 'data_owner'",
                'resource': 'key',
                'action': 'manage',
                'effect': 'allow',
                'priority': 20,
            },
            {
                'name': 'data_owner_policy_define',
                'description': 'Data owners can define access policies for their data',
                'subject_condition': "r.sub.user_type == 'data_owner'",
                'resource': 'policy',
                'action': 'write',
                'effect': 'allow',
                'priority': 20,
            },
            
            # Data User policies
            {
                'name': 'data_user_document_read',
                'description': 'Data users can read documents',
                'subject_condition': "r.sub.user_type == 'data_user'",
                'resource': 'document',
                'action': 'read',
                'effect': 'allow',
                'priority': 30,
            },
            {
                'name': 'data_user_document_download',
                'description': 'Data users can download documents',
                'subject_condition': "r.sub.user_type == 'data_user'",
                'resource': 'document',
                'action': 'download',
                'effect': 'allow',
                'priority': 30,
            },
            {
                'name': 'data_user_decrypt',
                'description': 'Data users can decrypt if attributes match',
                'subject_condition': "r.sub.user_type == 'data_user'",
                'resource': 'document',
                'action': 'decrypt',
                'effect': 'allow',
                'priority': 30,
            },
            
            # Auditor policies
            {
                'name': 'auditor_audit_full',
                'description': 'Auditors have full access to audit logs',
                'subject_condition': "r.sub.user_type == 'auditor'",
                'resource': 'audit',
                'action': '*',
                'effect': 'allow',
                'priority': 25,
            },
            {
                'name': 'auditor_document_read',
                'description': 'Auditors can read documents for audit purposes',
                'subject_condition': "r.sub.user_type == 'auditor'",
                'resource': 'document',
                'action': 'read',
                'effect': 'allow',
                'priority': 25,
            },
            
            # Guest policies (most restrictive)
            {
                'name': 'guest_public_read',
                'description': 'Guests can only read public documents',
                'subject_condition': "r.sub.user_type == 'guest'",
                'resource': 'document',
                'action': 'read',
                'effect': 'allow',
                'priority': 50,
            },
            
            # Attribute-based policies (examples)
            {
                'name': 'it_department_key_access',
                'description': 'IT department can manage encryption keys',
                'subject_condition': "r.sub.department == 'it'",
                'resource': 'key',
                'action': 'manage',
                'effect': 'allow',
                'priority': 40,
            },
            {
                'name': 'secret_clearance_document_access',
                'description': 'Users with secret clearance can access classified documents',
                'subject_condition': "r.sub.clearance_level in ['secret', 'top_secret']",
                'resource': 'document',
                'action': '*',
                'effect': 'allow',
                'priority': 35,
            },
        ]
        
        created_count = 0
        for policy_data in policies:
            policy, created = AccessPolicy.objects.get_or_create(
                name=policy_data['name'],
                defaults={
                    **policy_data,
                    'created_by': admin,
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f"  Created: {policy.name}")
            else:
                self.stdout.write(f"  Exists: {policy.name}")
        
        self.stdout.write(self.style.SUCCESS(f'\nSeeded {created_count} new policies'))
