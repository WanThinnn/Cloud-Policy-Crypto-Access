"""
Main application file for Hybrid CP-ABE Flask Backend
"""
from flask import Flask, jsonify, request, g
import logging
import platform
import os
import time
import uuid
import config
from utils.logger import app_logger, api_logger
from routes import (
    all_blueprints, abe_api, auth_api, files_api, 
    abac_api, ca_api, super_admin_api
)
from routes.health_routes import health_bp
from module import abe_lib

def create_app(config_name='default'):
    """Application factory with comprehensive logging"""
    # Chỉ backend API, không cần frontend paths
    app = Flask(__name__)
    
    # Load configuration
    from config import config as config_dict
    app.config.from_object(config_dict[config_name])
    
    # Setup request logging middleware
    @app.before_request
    def before_request():
        """Log incoming requests and set request ID"""
        g.request_id = str(uuid.uuid4())
        g.start_time = time.time()
        
        # Skip logging for health checks
        if request.endpoint not in ['health_check']:
            api_logger.info(f"Incoming request: {request.method} {request.path} from {request.remote_addr}")
    
    @app.after_request
    def after_request(response):
        """Log outgoing responses with performance metrics"""
        if hasattr(g, 'start_time') and request.endpoint not in ['health_check']:
            duration = round((time.time() - g.start_time) * 1000, 2)
            api_logger.info(f"Response: {response.status_code} for {request.method} {request.path} ({duration}ms)")
        return response
    
    @app.teardown_appcontext
    def teardown_appcontext(error):
        """Log any unhandled errors during request processing"""
        if error:
            app_logger.error(f"Unhandled error in request {request.method} {request.path}: {str(error)}")
    
    # Log application startup
    app_logger.info(f"Starting Cloud Firestore Crypto Access Backend (Python {platform.python_version()}, {platform.system()})")
    
    # Ensure upload directory exists
    upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    
    # Register blueprints with specific prefixes
    blueprint_configs = [
        (abe_api, '/api/abe'),
        (auth_api, '/api/auth'), 
        (files_api, '/api/files'),
        (abac_api, '/api/abac'),
        (ca_api, '/api/ca'),
        (super_admin_api, '/api/super-admin'),
        (health_bp, '/api')
    ]
    
    for blueprint, prefix in blueprint_configs:
        app.register_blueprint(blueprint, url_prefix=prefix)
        logging.info(f"Registered blueprint: {blueprint.name} with prefix: {prefix}")
    
    # API Root endpoint
    @app.route('/')
    def api_info():
        return jsonify({
            'message': 'Hybrid CP-ABE Flask Backend API',
            'version': '1.0.0',
            'status': 'running',
            'description': 'Complete SuperAdmin-managed CP-ABE system with attribute-based encryption',
            'features': [
                'Ciphertext-Policy Attribute-Based Encryption (CP-ABE)',
                'SuperAdmin user management system',
                'Attribute-based access control (ABAC)',
                'Secure password-encrypted private keys',
                'Admin-controlled user creation only'
            ],
            'endpoints': {
                'auth': {
                    'prefix': '/api/auth',
                    'description': 'Authentication (login, password reset)',
                    'note': 'Public registration disabled - admin creates accounts'
                },
                'super_admin': {
                    'prefix': '/api/super-admin',
                    'description': 'SuperAdmin management (setup, users, attributes)',
                    'authentication': 'SuperAdmin login required'
                },
                'ca': {
                    'prefix': '/api/ca', 
                    'description': 'Certificate Authority (ABE keys, setup)'
                },
                'abe': {
                    'prefix': '/api/abe',
                    'description': 'ABE operations (encrypt, decrypt)'
                },
                'files': {
                    'prefix': '/api/files',
                    'description': 'File management utilities'
                },
                'abac': {
                    'prefix': '/api/abac',
                    'description': 'Attribute-based access control'
                }
            },
            'quick_start': [
                '1. POST /api/ca/setup - Setup ABE system',
                '2. POST /api/super-admin/setup - Create super admin',
                '3. POST /api/auth/login - Login as super admin',
                '4. POST /api/super-admin/users - Create user accounts',
                '5. Use ABE encryption with user attributes'
            ]
        })
    
    @app.route('/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'abe_lib_loaded': abe_lib is not None and hasattr(abe_lib, 'is_loaded') and abe_lib.is_loaded()
        })
    
    @app.route('/debug/routes')
    def debug_routes():
        """Debug endpoint to show all registered routes"""
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods) if rule.methods else [],
                'rule': rule.rule
            })
        return jsonify({
            'total_routes': len(routes),
            'routes': routes
        })
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Endpoint not found'}, 404

    @app.errorhandler(500)
    def internal_error(error):
        logging.getLogger(__name__).error(f"Internal server error: {error}")
        return {'error': 'Internal server error'}, 500
    
    return app

def print_startup_info(app):
    """Print startup information"""
    print("=" * 60)
    print("🚀 Hybrid CP-ABE Flask Backend API")
    print("=" * 60)
    print(f"System: {platform.system()}")
    print(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    
    # Check ABE library status safely
    if abe_lib and hasattr(abe_lib, 'is_loaded'):
        lib_loaded = abe_lib.is_loaded()
        print(f"Library loaded: {lib_loaded}")
        if lib_loaded and hasattr(abe_lib, 'get_lib_path'):
            print(f"Library path: {abe_lib.get_lib_path()}")
    else:
        print("Library loaded: False (ABE library not available)")
    print("=" * 60)
    print("\n📋 Available API Endpoints:")
    print("  🏠 Root:")
    print("    GET  /               - API information")
    print("    GET  /health         - Health check")
    print("    GET  /api/health     - Detailed health status")
    print("    GET  /api/health/ready - Readiness probe")
    print("    GET  /api/health/live  - Liveness probe")
    print("  👤 Authentication (Admin-controlled):")
    print("    POST /api/auth/login          - User login (Super Admin + Regular)")
    print("    POST /api/auth/logout         - User logout")
    print("    POST /api/auth/register       - DISABLED (Admin-only creation)")
    print("    POST /api/auth/forgot-password - Request password reset")
    print("    POST /api/auth/reset-password - Reset password with token")
    print("    GET  /api/auth/session        - Check session status")
    print("    GET  /api/auth/profile        - Get user profile")
    print("  🔐 Certificate Authority:")
    print("    POST /api/ca/setup            - Setup ABE system")
    print("    GET  /api/ca/public-key       - Get public key")
    print("    GET  /api/ca/keys/active      - Get active keys")
    print("    GET  /api/ca/status           - CA status")
    print("    GET  /api/ca/health           - CA health check")
    print("    POST /api/ca/users/<id>/private-key - Create user private key")
    print("    GET  /api/ca/users/<id>/private-key - Get user private key")
    print("    GET  /api/ca/users/<id>/policy      - Get user policy")
    print("    POST /api/ca/user/private-key/generate    - Generate private key")
    print("    POST /api/ca/user/private-key/authenticate - Authenticate private key")
    print("    GET  /api/ca/user/private-key/check       - Check private key")
    print("    POST /api/ca/user/decrypt-file            - Decrypt file for user")
    print("  👑 Super Admin Management:")
    print("    POST /api/super-admin/setup         - Create first super admin")
    print("    POST /api/super-admin/login         - Super admin login")
    print("    POST /api/super-admin/users         - Create user account")
    print("    GET  /api/super-admin/users         - List all users")
    print("    GET  /api/super-admin/system/users  - Get system user stats")
    print("    GET  /api/super-admin/users/<id>    - Get user details")
    print("    PUT  /api/super-admin/users/<id>/attributes - Set user attributes")
    print("    POST /api/super-admin/users/<id>/deactivate - Deactivate user")
    print("    POST /api/super-admin/users/<id>/activate   - Activate user")
    print("    GET  /api/super-admin/schema/attributes     - Get attribute schema")
    print("    POST /api/super-admin/users/<id>/abe-key/regenerate - Regenerate ABE key")
    print("    GET  /api/super-admin/stats         - System statistics")
    print("  🔒 ABE Operations:")
    print("    GET  /api/abe/               - ABE system info")
    print("    GET  /api/abe/health         - ABE health check")
    print("    POST /api/abe/encrypt        - Encrypt data")
    print("    POST /api/abe/decrypt        - Decrypt data")
    print("    GET  /api/abe/files          - List ABE files")
    print("  📁 File Management:")
    print("    GET  /api/files/              - List user files")
    print("    POST /api/files/upload        - Upload and encrypt file")
    print("    GET  /api/files/<file_id>     - Get file metadata")
    print("    GET  /api/files/<file_id>/download - Download and decrypt file")
    print("    DELETE /api/files/<file_id>   - Delete file")
    print("    PUT  /api/files/<file_id>/policy - Update file access policy")
    print("    GET  /api/files/<file_id>/access-logs - Get file access logs")
    print("    GET  /api/files/health        - File system health check")
    print("  🛡️  ABAC (Attribute-Based Access Control):")
    print("    POST /api/abac/policies                  - Create policy")
    print("    GET  /api/abac/policies                  - Get access policies")
    print("    DELETE /api/abac/policies/<id>           - Delete policy")
    print("    POST /api/abac/users/<id>/attributes     - Set user attributes")
    print("    GET  /api/abac/users/<id>/attributes     - Get user attributes")
    print("    POST /api/abac/check-access              - Check access permissions")
    print("    GET  /api/abac/health                    - ABAC health check")
    print("    POST /api/abac/setup-corporate-policies  - Setup corporate policies")
    print("    POST /api/abac/check-corporate-access    - Check corporate access")
    print("=" * 60)
    print(f"\n🌐 Server starting on http://{app.config['HOST']}:{app.config['PORT']}")
    print("💡 API Only Mode - No Frontend")
    print("🛠️  Test with curl, Postman, or your frontend application")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)

if __name__ == '__main__':
    app = create_app('development')
    print_startup_info(app)
    
    app.run(
        host=app.config['HOST'], 
        port=app.config['PORT'], 
        debug=app.config['DEBUG']
    )
