"""
Seed test data: Users, Profiles, and ABAC Attributes
Run via: python manage.py seed_test_data
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from crypto_access.models import UserProfile, UserType, UserAttribute, AttributeDefinition


class Command(BaseCommand):
    help = 'Seed test users with ABAC attributes for testing'
    
    def handle(self, *args, **options):
        self.stdout.write('Creating test users...\n')
        
        # Disconnect signals temporarily to avoid constraint errors during bulk delete
        from django.db.models.signals import pre_delete, post_save, pre_save
        from crypto_access.signals import (
            user_deleted_handler, handle_attribute_change, 
            handle_attribute_deletion, capture_old_attribute_value,
            capture_old_profile_state, handle_profile_changes
        )
        from django.contrib.auth.models import User
        
        pre_delete.disconnect(user_deleted_handler, sender=User)
        pre_save.disconnect(capture_old_attribute_value)
        post_save.disconnect(handle_attribute_change)
        pre_delete.disconnect(handle_attribute_deletion)
        pre_save.disconnect(capture_old_profile_state)
        post_save.disconnect(handle_profile_changes)
        
        # Delete old test users (exclude superusers)
        User.objects.filter(is_superuser=False).delete()
        self.stdout.write("Deleted old test users")
        
        # Reconnect signals
        pre_delete.connect(user_deleted_handler, sender=User)
        pre_save.connect(capture_old_attribute_value)
        post_save.connect(handle_attribute_change)
        pre_delete.connect(handle_attribute_deletion)
        pre_save.connect(capture_old_profile_state)
        post_save.connect(handle_profile_changes)
        
        
        # Test users configuration
        test_users = [
            {
                'username': 'it_owner',
                'email': 'it_owner@company.com',
                'password': 'Test@123',
                'full_name': 'Trần IT Manager',
                'user_type': 'data_owner',
                'attributes': {
                    'department': 'it',
                    'role': 'director',
                    'clearance_level': 'top_secret',
                    'employment_status': 'active',
                }
            },
            {
                'username': 'hr_admin',
                'email': 'hr_admin@company.com',
                'password': 'Test@123',
                'full_name': 'Lê HR Manager',
                'user_type': 'admin',
                'attributes': {
                    'department': 'hr',
                    'role': 'manager',
                    'clearance_level': 'secret',
                    'employment_status': 'active',
                }
            },
            {
                'username': 'dev_user',
                'email': 'dev@company.com',
                'password': 'Test@123',
                'full_name': 'Phạm Developer',
                'user_type': 'data_user',
                'attributes': {
                    'department': 'it',
                    'role': 'employee',
                    'clearance_level': 'confidential',
                    'employment_status': 'active',
                }
            },
            {
                'username': 'hr_user',
                'email': 'hr_user@company.com',
                'password': 'Test@123',
                'full_name': 'Nguyễn HR Staff',
                'user_type': 'data_user',
                'attributes': {
                    'department': 'hr',
                    'role': 'employee',
                    'clearance_level': 'confidential',
                    'employment_status': 'active',
                }
            },
            {
                'username': 'finance_user',
                'email': 'finance@company.com',
                'password': 'Test@123',
                'full_name': 'Hoàng Kế Toán',
                'user_type': 'data_user',
                'attributes': {
                    'department': 'finance',
                    'role': 'employee',
                    'clearance_level': 'secret',
                    'data_access': 'full',
                    'employment_status': 'active',
                }
            },
        ]
        
        created_count = 0
        for user_data in test_users:
            # Get or create user
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={'email': user_data['email']}
            )
            
            if created:
                user.set_password(user_data['password'])
                user.save()
                created_count += 1
                self.stdout.write(f"  ✓ Created user: {user_data['username']}")
            else:
                self.stdout.write(f"  - Exists: {user_data['username']}")
            
            # Create or update profile
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.full_name = user_data['full_name']
            profile.user_type = user_data['user_type']
            
            # Link to UserType model
            try:
                user_type_ref = UserType.objects.get(code=user_data['user_type'])
                profile.user_type_ref = user_type_ref
            except UserType.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"    UserType '{user_data['user_type']}' not found"))
            
            profile.save()
            
            # Set ABAC attributes
            for attr_name, attr_value in user_data['attributes'].items():
                try:
                    UserAttribute.set_user_attribute(
                        user=user,
                        attribute_name=attr_name,
                        value=attr_value,
                        updated_by=User.objects.filter(is_superuser=True).first()
                    )
                except ValueError as e:
                    self.stdout.write(self.style.WARNING(f"    Attribute error: {e}"))
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Created {created_count} new users'))
        self.stdout.write(self.style.SUCCESS('All users password: Test@123'))
