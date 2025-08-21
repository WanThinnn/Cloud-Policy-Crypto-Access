"""
Debug script to check registered routes
"""
import requests
import json

def check_routes():
    try:
        response = requests.get("http://192.168.1.2:5000/debug/routes")
        if response.status_code == 200:
            data = response.json()
            print(f"Total routes: {data['total_routes']}")
            print("\nRegistered routes:")
            
            # Group by blueprint
            blueprints = {}
            for route in data['routes']:
                endpoint_parts = route['endpoint'].split('.')
                if len(endpoint_parts) > 1:
                    blueprint = endpoint_parts[0]
                    if blueprint not in blueprints:
                        blueprints[blueprint] = []
                    blueprints[blueprint].append(route)
                else:
                    if 'main' not in blueprints:
                        blueprints['main'] = []
                    blueprints['main'].append(route)
            
            for blueprint, routes in blueprints.items():
                print(f"\n📋 {blueprint.upper()} Blueprint:")
                for route in routes:
                    methods = ', '.join([m for m in route['methods'] if m not in ['HEAD', 'OPTIONS']])
                    print(f"  {methods:<10} {route['rule']}")
                    
        else:
            print(f"Failed to get routes: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_routes()
