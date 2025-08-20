"""
Main application file for Hybrid CP-ABE Flask Backend
"""
from flask import Flask, render_template, session, redirect, url_for
import logging
import platform
import os
from config import config
from routes import all_blueprints
from module import abe_lib
from utils import ensure_directory_exists

def create_app(config_name='default'):
    """Application factory"""
    app = Flask(__name__, 
                static_folder='../fontend',
                template_folder='../fontend/html')
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, app.config['LOG_LEVEL']),
        format=app.config['LOG_FORMAT']
    )
    
    # Ensure upload directory exists
    ensure_directory_exists(app.config['UPLOAD_FOLDER'])
    
    # Register blueprints dynamically
    for blueprint in all_blueprints:
        app.register_blueprint(blueprint, url_prefix='/api')
        logging.info(f"Registered blueprint: {blueprint.name}")
    
    # Frontend routes
    @app.route('/')
    def index():
        if 'user_id' not in session:
            return redirect('/login')
        return render_template('index.html')
    
    @app.route('/login')
    def login_page():
        if 'user_id' in session:
            return redirect('/')
        return render_template('login.html')
    
    @app.route('/admin')
    def admin_page():
        if 'user_id' not in session:
            return redirect('/login')
        
        # Check if user is admin (basic check)
        from module.database import db
        try:
            user_doc = db.collection('users').document(session['user_id']).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                if user_data.get('role') == 'admin' or user_data.get('is_admin', False):
                    return render_template('admin.html')
        except Exception as e:
            logging.error(f"Error checking admin status: {e}")
        
        return "Access denied - Admin privileges required", 403
    
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
    print("Hybrid CP-ABE Flask Backend")
    print("=" * 60)
    print(f"System: {platform.system()}")
    print(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    print(f"Library loaded: {abe_lib.is_loaded()}")
    if abe_lib.is_loaded():
        print(f"Library path: {abe_lib.get_lib_path()}")
    print("=" * 60)
    print("\nAvailable endpoints:")
    print("  📋 ABE Endpoints:")
    print("    GET  /          - API information")
    print("    GET  /health    - Health check")
    print("    POST /setup     - Setup ABE system")
    print("    POST /generate-key - Generate secret key")
    print("    POST /encrypt   - Encrypt data")
    print("    POST /decrypt   - Decrypt data")
    print("    GET  /files     - List temp files")
    print("  👤 Auth Endpoints:")
    print("    POST /auth/register - User registration")
    print("    POST /auth/login    - User login")
    print("    GET  /auth/user/<id> - Get user info")
    print("    PUT  /auth/user/<id> - Update user info")
    print("    POST /auth/change-password - Change password")
    print("    POST /auth/validate-password - Validate password")
    print("    GET  /auth/health   - Auth health check")
    print("=" * 60)
    print(f"\nServer starting on http://{app.config['HOST']}:{app.config['PORT']}")
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
