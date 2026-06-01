import os
import django
import sys

sys.path.append(r"d:\Documents\UIT\Nam_4\Cloud-Firestore-Crypto-Access\src")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User
from crypto_access.services.casbin_service import casbin_service
from crypto_access.services.cpabe_service import cpabe_service
from crypto_access.models import AccessPolicy

def test_flow():
    print("--- Testing CP-ABE Service ---")
    print(f"DLL loaded: {cpabe_service._lib is not None}")
    
    # Create a dummy plaintext file
    plaintext = "This is a highly confidential document for IT department."
    with open("dummy.txt", "w") as f:
        f.write(plaintext)
        
    # Get IT policy
    policy = AccessPolicy.objects.get(name="IT Department Read Access")
    cpabe_policy_str = policy.cpabe_policy
    print(f"Selected Policy: {policy.name} -> {cpabe_policy_str}")
    
    # 1. Encrypt
    print("\nEncrypting file...")
    cpabe_service.encrypt_file("dummy.txt", "dummy.enc", cpabe_policy_str)
    print(f"Encrypted file created: {os.path.exists('dummy.enc')}")
    
    # 2. Get IT user attributes and try to decrypt
    print("\nAttempting Decryption with IT User...")
    it_user = User.objects.get(username="test_it_user")
    it_attrs = casbin_service.get_user_attributes(it_user)
    print(f"IT User attributes: {it_attrs}")
    
    try:
        cpabe_service.generate_user_key(it_attrs, "it_user.key")
        cpabe_service.decrypt_file("it_user.key", "dummy.enc", "dummy_recovered.txt")
        with open("dummy_recovered.txt", "r") as f:
            recovered = f.read()
            print(f"Recovered text: '{recovered}'")
            if recovered == plaintext:
                print("✅ Decryption SUCCESS!")
            else:
                print("❌ Decryption FAILED (content mismatch)")
    except Exception as e:
        print(f"❌ IT Decryption Error: {e}")
        
    # 3. Get HR user attributes and try to decrypt
    print("\nAttempting Decryption with HR User (Should Fail)...")
    hr_user = User.objects.get(username="hr_user")
    hr_attrs = casbin_service.get_user_attributes(hr_user)
    print(f"HR User attributes: {hr_attrs}")
    
    try:
        cpabe_service.generate_user_key(hr_attrs, "hr_user.key")
        cpabe_service.decrypt_file("hr_user.key", "dummy.enc", "dummy_hr_recovered.txt")
        print("❌ HR Decryption SUCCEEDED (This is a BUG!)")
    except Exception as e:
        print(f"✅ HR Decryption FAILED as expected: {e}")
        
    # Cleanup
    for f in ["dummy.txt", "dummy.enc", "it_user.key", "hr_user.key", "dummy_recovered.txt", "dummy_hr_recovered.txt"]:
        if os.path.exists(f):
            os.remove(f)

if __name__ == "__main__":
    test_flow()
