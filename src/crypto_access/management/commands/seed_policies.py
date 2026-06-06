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
            # 1. Super Admin - full access (highest priority)
            {
                'name': 'super_admin_full_access',
                'description': 'Super admins have full access to all resources',
                'subject_condition': "r.sub.user_type == 'super_admin'",
                'resource': '*',
                'action': '*',
                'effect': 'allow',
                'priority': 1,
            },
            
            # 2. Admin - user management
            {
                'name': 'admin_user_management',
                'description': 'Admins can manage users',
                'subject_condition': "r.sub.user_type == 'admin'",
                'resource': 'user',
                'action': 'manage',
                'effect': 'allow',
                'priority': 10,
            },
            
            # 3. Data Contributor (DO) - document management
            {
                'name': 'data_contributor_document_manage',
                'description': 'Data Contributors (DO) can manage documents',
                'subject_condition': "r.sub.user_type == 'data_contributor'",
                'resource': 'document',
                'action': 'manage',
                'effect': 'allow',
                'priority': 20,
            },
            
            # 4. Data User (DU) - basic document read
            {
                'name': 'data_user_document_read',
                'description': 'Data Users (DU) can read documents',
                'subject_condition': "r.sub.user_type == 'data_user'",
                'resource': 'document',
                'action': 'read',
                'effect': 'allow',
                'priority': 30,
            },
            
            # 5. IT Department Key Access
            {
                'name': 'it_department_key_access',
                'description': 'IT department can manage key revocation list',
                'subject_condition': "r.sub.department == 'it'",
                'resource': 'key',
                'action': 'manage',
                'effect': 'allow',
                'priority': 40,
            },
            
            # 6. Secret Clearance Access
            {
                'name': 'secret_clearance_document_access',
                'description': 'Users with secret clearance can access classified documents',
                'subject_condition': "r.sub.clearance_level in ['secret', 'top_secret']",
                'resource': 'document',
                'action': '*',
                'effect': 'allow',
                'priority': 35,
            },

            # 7. Multi-attribute Complex 1: HR Managers
            {
                'name': 'hr_manager_full_access',
                'description': 'HR Managers have full access to employee records',
                'subject_condition': "r.sub.department == 'hr' and r.sub.role == 'manager'",
                'resource': 'document',
                'action': '*',
                'effect': 'allow',
                'priority': 45,
            },

            # 8. Multi-attribute Complex 2: Active Employee Read
            {
                'name': 'active_employee_read',
                'description': 'Active employees can read basic documents',
                'subject_condition': "r.sub.employment_status == 'active'",
                'resource': 'document',
                'action': 'read',
                'effect': 'allow',
                'priority': 50,
            },

            # 9. Multi-attribute Complex 3: Director strategic access
            {
                'name': 'director_strategic_access',
                'description': 'Directors or CEOs can access strategic data',
                'subject_condition': "r.sub.role in ['director', 'ceo']",
                'resource': 'document',
                'action': '*',
                'effect': 'allow',
                'priority': 25,
            },

            # 10. Multi-attribute Complex 4: Strict Finance Policy
            {
                'name': 'strict_finance_policy',
                'description': 'Only active finance employees with full access can manage financial data',
                'subject_condition': "r.sub.department == 'finance' and r.sub.employment_status == 'active' and r.sub.data_access == 'full'",
                'resource': 'document',
                'action': 'manage',
                'effect': 'allow',
                'priority': 15,
            },
        ]
        
        # Delete old policies first
        AccessPolicy.objects.all().delete()
        self.stdout.write("Deleted old policies")

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
