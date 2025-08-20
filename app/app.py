"""
INTEGRATED FLASK APPLICATION
Combines frontend templates with backend API
"""

import sys
import os
from flask import Flask, render_template, request, jsonify, session, flash, redirect, url_for
from datetime import datetime
import requests
import logging

# Add backend to path
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

# Import backend modules
from config import config
from routes import all_blueprints
from utils import ensure_directory_exists

def create_app():
    """Create integrated Flask application"""
    
    # Configure template and static folders for frontend
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'frontend', 'templates'))
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'frontend', 'static'))
    
    app = Flask(__name__, 
                template_folder=template_dir, 
                static_folder=static_dir,
                static_url_path='/static')
    
    # Load backend configuration
    app.config.from_object(config['default'])
    app.secret_key = 'your-secret-key-change-in-production'
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Ensure directories exist
    ensure_directory_exists(app.config.get('UPLOAD_FOLDER', './temp_files'))
    
    # Register backend API blueprints
    for blueprint in all_blueprints:
        app.register_blueprint(blueprint, url_prefix='/api')
        logging.info(f"Registered API blueprint: {blueprint.name}")
    
    # ====== FRONTEND ROUTES ======
    
    @app.route('/')
    def home():
        """Dashboard home page"""
        # Get user session info
        user_id = session.get('user_id', 'demo_user')
        
        # Fetch dashboard data from backend API
        dashboard_data = get_dashboard_data(user_id)
        
        return render_template('home.html', **dashboard_data)
    
    @app.route('/files')
    def files():
        """Files listing page"""
        user_id = session.get('user_id', 'demo_user')
        
        # Fetch files from backend API
        files_data = get_user_files(user_id)
        
        return render_template('files.html', files=files_data)
    
    @app.route('/files/<file_id>')
    def file_detail(file_id):
        """File detail page"""
        user_id = session.get('user_id', 'demo_user')
        
        # Fetch file details from backend API
        file_data = get_file_details(file_id, user_id)
        
        if not file_data:
            flash('File not found or access denied', 'error')
            return redirect(url_for('files'))
        
        return render_template('detail.html',
                             item_title=file_data.get('filename', 'Unknown File'),
                             item_description=file_data.get('description', 'No description available'),
                             item_id=file_data.get('file_id', file_id),
                             item_owner=file_data.get('owner', 'Unknown'),
                             item_created_date=file_data.get('upload_time', 'Unknown'),
                             item_modified_date=file_data.get('modified_time', 'Unknown'),
                             item_size=format_file_size(file_data.get('file_size', 0)),
                             item_status='Active' if file_data.get('status') == 'active' else 'Inactive',
                             item_access_level=file_data.get('access_policy', 'Private'),
                             item_type='file',
                             breadcrumb_parent_url=url_for('files'),
                             breadcrumb_parent_name='Files',
                             show_tabs=True,
                             show_statistics=True)
    
    @app.route('/users')
    def users():
        """Users listing page"""
        # Only allow admin users
        if not is_admin_user():
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('home'))
        
        # Fetch users from backend API
        users_data = get_all_users()
        
        return render_template('users.html', users=users_data)
    
    @app.route('/users/<user_id>')
    def user_detail(user_id):
        """User detail page"""
        if not is_admin_user():
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('home'))
        
        # Fetch user details from backend API
        user_data = get_user_details(user_id)
        
        if not user_data:
            flash('User not found', 'error')
            return redirect(url_for('users'))
        
        return render_template('detail.html',
                             item_title=user_data.get('username', 'Unknown User'),
                             item_description=user_data.get('email', 'No email provided'),
                             item_id=user_data.get('user_id', user_id),
                             item_owner='System Administrator',
                             item_created_date=user_data.get('created_at', 'Unknown'),
                             item_modified_date=user_data.get('last_login', 'Never'),
                             item_size=None,
                             item_status='Active' if user_data.get('is_active', True) else 'Inactive',
                             item_access_level=user_data.get('role', 'User'),
                             item_type='user',
                             breadcrumb_parent_url=url_for('users'),
                             breadcrumb_parent_name='Users',
                             show_tabs=True,
                             show_statistics=False)
    
    @app.route('/upload')
    def upload_page():
        """Upload page"""
        return render_template('upload.html')
    
    @app.route('/login')
    def login_page():
        """Login page"""
        return render_template('login.html')
    
    @app.route('/register')
    def register_page():
        """Register page"""
        return render_template('register.html')
    
    @app.route('/forgot-password')
    def forgot_password_page():
        """Forgot password page"""
        return render_template('forgot_password.html')
    
    @app.route('/security')
    def security():
        """Security settings page"""
        user_id = session.get('user_id', 'demo_user')
        security_data = get_security_settings(user_id)
        return render_template('security.html', **security_data)
    
    @app.route('/analytics')
    def analytics():
        """Analytics dashboard"""
        if not is_admin_user():
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('home'))
        
        analytics_data = get_analytics_data()
        return render_template('analytics.html', **analytics_data)
    
    @app.route('/profile')
    def profile():
        """User profile page"""
        user_id = session.get('user_id')
        if not user_id:
            flash('Please login to view your profile', 'warning')
            return redirect(url_for('login'))
        
        profile_data = get_user_details(user_id)
        return render_template('profile.html', **profile_data)
    
    @app.route('/login')
    def login():
        """Login page"""
        return render_template('login.html')
    
    @app.route('/logout')
    def logout():
        """Logout functionality"""
        session.clear()
        flash('You have been logged out successfully', 'info')
        return redirect(url_for('home'))
    
    # ====== API INTEGRATION HELPERS ======
    
    def get_dashboard_data(user_id):
        """Fetch dashboard data from backend"""
        try:
            # In production, make actual API calls to backend
            return {
                'total_files': 1247,
                'active_users': 89,
                'storage_used': '2.4 TB',
                'storage_total': '5 TB',
                'security_score': 98,
                'system_uptime': '99.9%',
                'avg_response_time': '1.2s',
                'active_alerts': 0
            }
        except Exception as e:
            logging.error(f"Dashboard data fetch error: {e}")
            return {}
    
    def get_user_files(user_id):
        """Fetch user files from backend"""
        try:
            # In production, make actual API call
            # response = requests.get(f'/api/files?user_id={user_id}')
            return [
                {
                    'id': '1',
                    'title': 'Important Document.pdf',
                    'description': 'Confidential business document with encryption',
                    'owner': 'john.doe@company.com',
                    'created_date': '2025-01-15 10:30:00',
                    'size': '2.4 MB',
                    'status': 'Active'
                },
                {
                    'id': '2',
                    'title': 'Financial Report Q4.xlsx',
                    'description': 'Quarterly financial analysis and projections',
                    'owner': 'finance@company.com',
                    'created_date': '2025-01-10 14:20:00',
                    'size': '1.8 MB',
                    'status': 'Active'
                }
            ]
        except Exception as e:
            logging.error(f"Files fetch error: {e}")
            return []
    
    def get_file_details(file_id, user_id):
        """Fetch file details from backend"""
        try:
            # In production, make actual API call
            return {
                'file_id': file_id,
                'filename': 'Important Document.pdf',
                'description': 'Confidential business document with ABE encryption',
                'owner': 'john.doe@company.com',
                'upload_time': '2025-01-15 10:30:00',
                'modified_time': '2025-01-18 14:20:00',
                'file_size': 2457600,  # bytes
                'status': 'active',
                'access_policy': 'HR AND Manager'
            }
        except Exception as e:
            logging.error(f"File details fetch error: {e}")
            return None
    
    def get_all_users():
        """Fetch all users (admin only)"""
        try:
            return [
                {
                    'id': '1',
                    'title': 'John Doe',
                    'description': 'Senior Developer with full system access',
                    'owner': 'john.doe@company.com',
                    'created_date': '2025-01-01 08:00:00',
                    'status': 'Active',
                    'access_level': 'Full Access'
                },
                {
                    'id': '2',
                    'title': 'Jane Smith',
                    'description': 'HR Manager with departmental access',
                    'owner': 'jane.smith@company.com',
                    'created_date': '2025-01-05 09:15:00',
                    'status': 'Active',
                    'access_level': 'HR Access'
                }
            ]
        except Exception as e:
            logging.error(f"Users fetch error: {e}")
            return []
    
    def get_user_details(user_id):
        """Fetch user details"""
        try:
            # Mock data for demo
            return {
                'user_id': user_id,
                'username': 'john.doe',
                'email': 'john.doe@company.com',
                'created_at': '2025-01-01 08:00:00',
                'last_login': '2025-01-20 10:30:00',
                'is_active': True,
                'role': 'Developer'
            }
        except Exception as e:
            logging.error(f"User details fetch error: {e}")
            return None
    
    def get_security_settings(user_id):
        """Fetch security settings"""
        return {
            'encryption_enabled': True,
            'two_factor_enabled': True,
            'last_security_scan': '2025-01-20 08:00:00',
            'security_score': 98
        }
    
    def get_analytics_data():
        """Fetch analytics data"""
        return {
            'daily_uploads': 45,
            'monthly_users': 234,
            'storage_growth': '+12%',
            'security_incidents': 0
        }
    
    def is_admin_user():
        """Check if current user is admin"""
        # In production, check user role from session/database
        return session.get('user_role') == 'admin' or session.get('user_id') == 'demo_admin'
    
    def format_file_size(bytes_size):
        """Format file size in human readable format"""
        if bytes_size == 0:
            return '0 B'
        
        size_names = ['B', 'KB', 'MB', 'GB', 'TB']
        i = 0
        while bytes_size >= 1024 and i < len(size_names) - 1:
            bytes_size /= 1024
            i += 1
        
        return f"{bytes_size:.1f} {size_names[i]}"
    
    # ====== ERROR HANDLERS ======
    
    @app.errorhandler(404)
    def not_found_error(error):
        flash('Page not found', 'error')
        return redirect(url_for('home'))
    
    @app.errorhandler(500)
    def internal_error(error):
        logging.error(f"Internal server error: {error}")
        flash('An internal error occurred', 'error')
        return redirect(url_for('home'))
    
    # ====== CONTEXT PROCESSORS ======
    
    @app.context_processor
    def inject_user():
        """Inject user info into all templates"""
        return {
            'current_user_id': session.get('user_id'),
            'current_user_role': session.get('user_role', 'user'),
            'is_authenticated': 'user_id' in session
        }
    
    return app

if __name__ == '__main__':
    app = create_app()
    
    # Set demo session for testing
    with app.app_context():
        with app.test_request_context():
            session.permanent = True
            session['user_id'] = 'demo_user'
            session['user_role'] = 'admin'  # For testing admin features
    
    print("=" * 60)
    print("INTEGRATED CLOUD FIRESTORE CRYPTO ACCESS")
    print("=" * 60)
    print("Frontend + Backend API Integration")
    print("Available at: http://localhost:5000")
    print("API endpoints available at: /api/*")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
