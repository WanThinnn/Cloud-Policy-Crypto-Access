"""
Simple startup test để kiểm tra imports
"""
import sys
import os

print("Testing imports...")

try:
    # Test basic imports
    print("1. Testing Flask...")
    from flask import Flask
    print("✅ Flask OK")
    
    print("2. Testing Firebase...")
    import firebase_admin
    from firebase_admin import firestore
    print("✅ Firebase OK")
    
    print("3. Testing database module...")
    from module.database import db
    print("✅ Database module OK")
    
    print("4. Testing user management...")
    from module.user_management import user_manager
    print("✅ User management OK")
    
    print("5. Testing ABAC...")
    from module.abac import abac
    print("✅ ABAC OK")
    
    print("6. Testing ABE library...")
    try:
        from module.hybrid_cp_abe import abe_lib
        if abe_lib and abe_lib.is_loaded():
            print("✅ ABE library loaded")
        else:
            print("⚠️ ABE library not loaded (but import OK)")
    except Exception as e:
        print(f"❌ ABE library error: {e}")
    
    print("7. Testing routes...")
    from routes.auth_routes import auth_api
    print("✅ Auth routes OK")
    
    from routes.abac_routes import abac_api
    print("✅ ABAC routes OK")
    
    print("\n🎉 All basic imports successful!")
    print("Server should be able to start...")
    
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
