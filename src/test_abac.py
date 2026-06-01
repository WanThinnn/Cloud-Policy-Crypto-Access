import os
import django
import sys

sys.path.append(r"d:\Documents\UIT\Nam_4\Cloud-Firestore-Crypto-Access\src")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User
from crypto_access.services.casbin_service import casbin_service
from crypto_access.models import UserProfile, UserType, AccessPolicy

def test_abac():
    print("Seeding policies...")
    from django.core.management import call_command
    # Run seed to ensure policies exist
    call_command("seed_abac_policies")
    
    # Create test user
    test_user, _ = User.objects.get_or_create(username="test_it_user")
    test_type, _ = UserType.objects.get_or_create(code="employee", defaults={"name": "Employee", "permissions": ["file_read"]})
    
    # Setup profile
    profile, _ = UserProfile.objects.get_or_create(user=test_user, defaults={"user_type_ref": test_type})
    
    # Setup attributes
    from crypto_access.models import AttributeDefinition, UserAttribute
    dept_attr, _ = AttributeDefinition.objects.get_or_create(name="department", defaults={"data_type": "string"})
    clearance_attr, _ = AttributeDefinition.objects.get_or_create(name="clearance_level", defaults={"data_type": "string"})
    
    UserAttribute.objects.update_or_create(user=test_user, attribute=dept_attr, defaults={"value": "it"})
    UserAttribute.objects.update_or_create(user=test_user, attribute=clearance_attr, defaults={"value": "secret"})
    
    # Reload policies
    casbin_service.reload_policies()
    
    # Test
    print("\n--- Testing Access ---")
    attrs = casbin_service.get_user_attributes(test_user)
    print(f"User attributes: {attrs}")
    
    # Test read (should be allowed via IT dept policy)
    can_read = casbin_service.check_access(test_user, 'document', 'read')
    print(f"Can Read Document: {can_read}")
    
    # Test upload (should be allowed via IT dept + secret clearance policy)
    can_upload = casbin_service.check_access(test_user, 'document', 'upload')
    print(f"Can Upload Document: {can_upload}")
    
    # Explain decision
    print("\n--- Explanation for Upload ---")
    explanation = casbin_service.explain_decision(test_user, 'document', 'upload')
    print(explanation)

if __name__ == "__main__":
    test_abac()
