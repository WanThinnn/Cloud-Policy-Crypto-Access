"""
Debug script để kiểm tra ABE system và keys
"""
import requests
import json

BASE_URL = "http://localhost:5000"

def debug_abe_status():
    """Debug ABE system status"""
    print("🔍 Debugging ABE system...")
    
    try:
        # Check CA status
        response = requests.get(f"{BASE_URL}/ca/status")
        print(f"\n📊 CA Status ({response.status_code}):")
        if response.status_code == 200:
            status = response.json()
            print(json.dumps(status, indent=2))
        else:
            print(f"Error: {response.text}")
        
        # Check active keys
        response = requests.get(f"{BASE_URL}/ca/keys/active")
        print(f"\n🔑 Active Keys ({response.status_code}):")
        if response.status_code == 200:
            keys = response.json()
            print(json.dumps(keys, indent=2))
        else:
            print(f"Error: {response.text}")
            
        # Setup new ABE system
        print(f"\n🔧 Setting up new ABE system...")
        response = requests.post(f"{BASE_URL}/ca/setup")
        print(f"Setup Result ({response.status_code}):")
        if response.status_code == 201:
            setup_result = response.json()
            print(json.dumps(setup_result, indent=2))
            
            # Check keys again
            print(f"\n🔑 Active Keys after setup:")
            response = requests.get(f"{BASE_URL}/ca/keys/active")
            if response.status_code == 200:
                keys = response.json()
                print(json.dumps(keys, indent=2))
            else:
                print(f"Error: {response.text}")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_abe_status()
