"""
Debug ABE system setup process  
"""
import os
import tempfile
import sys
sys.path.append('.')
from module.central_authority import CentralAuthority

def debug_abe_setup():
    """Debug ABE setup process bằng cách gọi CA trực tiếp"""
    print("🔧 Debugging ABE Setup Process")
    print("=" * 50)
    
    try:
        # Create Central Authority instance
        ca = CentralAuthority()
        print("✅ Central Authority instance created")
        
        # Test setup
        print(f"\n🎯 Testing ABE Setup via CA...")
        result = ca.setup_abe_system()
        
        print(f"Setup result: {result}")
        
        if result['success']:
            print(f"✅ Setup successful: {result.get('setup_id')}")
            
            # Test getting active keys
            print(f"\n� Testing get active keys...")
            keys_result = ca.get_active_keys()
            print(f"Keys result: {keys_result}")
            
            if keys_result['success']:
                print(f"✅ Keys available:")
                print(f"   Public key: {keys_result.get('has_public_key', False)}")
                print(f"   Master key: {keys_result.get('has_master_key', False)}")
                print(f"   Setup ID: {keys_result.get('setup_id')}")
            else:
                print(f"❌ Failed to get keys: {keys_result.get('error')}")
        else:
            print(f"❌ Setup failed: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_abe_setup()
