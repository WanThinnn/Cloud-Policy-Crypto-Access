"""
Debug script to test ABAC functionality directly
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from module.abac import AttributeBasedAccessControl
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_abac_user_attributes():
    """Test ABAC user attributes fetching"""
    print("=== Testing ABAC User Attributes ===")
    
    abac = AttributeBasedAccessControl()
    user_id = "22528337"
    
    print(f"Testing user ID: {user_id}")
    result = abac.get_user_attributes(user_id)
    
    print(f"Result: {result}")
    
    if result['success']:
        print(f"✅ SUCCESS: Found attributes for user {user_id}")
        print(f"Attributes: {result['attributes']}")
    else:
        print(f"❌ FAILED: {result['error']}")

def test_abac_access_check():
    """Test ABAC access check"""
    print("\n=== Testing ABAC Access Check ===")
    
    abac = AttributeBasedAccessControl()
    
    # Test access request
    access_request = {
        'user_id': '22528337',
        'resource': 'files',
        'action': 'read',
        'resource_attributes': {
            'file_id': '3987c7fc-73dc-46bf-ae67-4485ab5bbab9',
            'owner_id': '22528337',
            'file_type': 'text/plain'
        }
    }
    
    print(f"Testing access request: {access_request}")
    result = abac.check_access(access_request)
    
    print(f"Result: {result}")
    
    if result['success']:
        if result['access_granted']:
            print("✅ SUCCESS: Access granted")
        else:
            print(f"❌ ACCESS DENIED: {result['reason']}")
    else:
        print(f"❌ FAILED: {result}")

if __name__ == '__main__':
    test_abac_user_attributes()
    test_abac_access_check()
