"""Test script for Hybrid RBAC + ABAC"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

import django
django.setup()

from crypto_access.models import AccessPolicy
from django.contrib.auth.models import User
from crypto_access.services.casbin_service import casbin_service

# Create ABAC policy for data_user to read documents
AccessPolicy.objects.filter(name='data_user_read_document').delete()
policy = AccessPolicy.objects.create(
    name='data_user_read_document',
    description='Allow data_user type to read documents',
    subject_condition='r.sub.user_type == "data_user"',
    resource='document',
    action='read',
    effect='allow',
    priority=50,
    is_active=True
)
print(f'Created policy: {policy.name}')
print(f'  Condition: {policy.subject_condition}')

# Reload casbin
casbin_service.reload_policies()
print('Reloaded Casbin policies')

# Test again
print()
print('=== HYBRID RBAC + ABAC TEST ===')
for username in ['superadmin', 'data_user_test']:
    user = User.objects.get(username=username)
    print()
    print(f'--- {username} ---')
    
    if hasattr(user, 'profile') and user.profile.user_type_ref:
        ut = user.profile.user_type_ref
        print(f'User Type: {ut.code}')
        print(f'Base Perms: {ut.permissions}')
    
    for resource, action in [('document', 'read'), ('document', 'upload'), ('document', 'delete')]:
        result = casbin_service.check_access(user, resource, action)
        exp = casbin_service.explain_decision(user, resource, action)
        
        status = 'ALLOW' if result else 'DENY'
        print(f'  {resource}/{action}: {status}')
        print(f'    RBAC: {exp["rbac_layer"]["result"]} - {exp["rbac_layer"]["reason"]}')
        print(f'    ABAC: {exp["abac_layer"]["result"]} - {exp["abac_layer"]["reason"]}')
