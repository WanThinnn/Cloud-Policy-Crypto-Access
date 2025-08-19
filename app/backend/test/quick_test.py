#!/usr/bin/env python3
"""
Quick test script for the fixed API
"""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000"

def test_full_workflow():
    print("🧪 Testing Full ABE Workflow")
    print("=" * 50)
    
    # 1. Health Check
    print("\n1️⃣ Health Check")
    r = requests.get(f"{BASE_URL}/health")
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        print("✅ Health check passed")
    else:
        print("❌ Health check failed")
        return
    
    # 2. Setup
    print("\n2️⃣ Setup")
    r = requests.post(f"{BASE_URL}/setup")
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        setup_data = r.json()
        public_key = setup_data['public_key_path']
        master_key = setup_data['master_key_path']
        print(f"✅ Setup success")
        print(f"   Public key: {public_key}")
        print(f"   Master key: {master_key}")
    else:
        print("❌ Setup failed")
        print(r.text)
        return
    
    # 3. Generate Key
    print("\n3️⃣ Generate Secret Key")
    gen_data = {
        'public_key_path': public_key,
        'master_key_path': master_key,
        'attributes': 'student teacher admin researcher'
    }
    r = requests.post(f"{BASE_URL}/generate-key", json=gen_data)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        key_data = r.json()
        private_key = key_data['private_key_path']
        print(f"✅ Key generation success")
        print(f"   Private key: {private_key}")
        print(f"   Attributes: {key_data['attributes']}")
    else:
        print("❌ Key generation failed")
        print(r.text)
        return
    
    # 4. Encrypt
    print("\n4️⃣ Encrypt")
    encrypt_data = {
        'public_key_path': public_key,
        'policy': '(student AND teacher) OR (admin AND researcher)',
        'plaintext': 'Hello ABE! This is a test message with Vietnamese: Xin chào! 🎉'
    }
    r = requests.post(f"{BASE_URL}/encrypt", json=encrypt_data)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        enc_data = r.json()
        ciphertext = enc_data['ciphertext_path']
        print(f"✅ Encryption success")
        print(f"   Ciphertext: {ciphertext}")
        print(f"   Policy: {enc_data['policy']}")
    else:
        print("❌ Encryption failed")
        print(r.text)
        return
    
    # 5. Decrypt
    print("\n5️⃣ Decrypt")
    decrypt_data = {
        'public_key_path': public_key,
        'private_key_path': private_key,
        'ciphertext_path': ciphertext
    }
    r = requests.post(f"{BASE_URL}/decrypt", json=decrypt_data)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        dec_data = r.json()
        recovered = dec_data['recovered_content']
        print(f"✅ Decryption success")
        print(f"   Recovered: {recovered}")
        print(f"   Original: {encrypt_data['plaintext']}")
        print(f"   Match: {'✅ Yes' if recovered.strip() == encrypt_data['plaintext'].strip() else '❌ No'}")
    else:
        print("❌ Decryption failed")
        print(r.text)
        return
    
    print("\n" + "=" * 50)
    print("🎉 ALL TESTS PASSED! ABE API is working correctly! 🎉")
    print("=" * 50)

if __name__ == "__main__":
    print("Waiting for server...")
    time.sleep(1)
    test_full_workflow()
