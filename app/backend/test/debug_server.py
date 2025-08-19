"""
Debug script to test server startup with auth routes
"""
from flask import Flask
from auth_routes import auth_api
from routes import api

def test_server():
    """Test server with auth routes"""
    app = Flask(__name__)
    
    # Register blueprints
    app.register_blueprint(api)
    app.register_blueprint(auth_api)
    
    # Print registered routes
    print("Registered routes:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.methods} {rule.rule}")
    
    return app

if __name__ == "__main__":
    print("Testing server startup with auth routes...")
    app = test_server()
    print("\nStarting test server on port 5001...")
    app.run(host='127.0.0.1', port=5001, debug=True)
