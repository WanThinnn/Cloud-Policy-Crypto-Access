"""
Utilities package for Cloud Firestore Crypto Access
"""

# Import functions directly from utils.py at parent level
import sys
import os

# Add parent directory to path to import utils.py
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
utils_path = os.path.join(parent_dir, 'utils.py')

# Import specific functions we need
if os.path.exists(utils_path):
    # Load the utils module dynamically to avoid circular import
    import importlib.util
    spec = importlib.util.spec_from_file_location("utils_module", utils_path)
    utils_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(utils_module)
    
    # Export the functions
    generate_temp_filename = getattr(utils_module, 'generate_temp_filename', None)
    validate_file_exists = getattr(utils_module, 'validate_file_exists', None)
    read_file_content = getattr(utils_module, 'read_file_content', None)
    write_file_content = getattr(utils_module, 'write_file_content', None)
    safe_remove_file = getattr(utils_module, 'safe_remove_file', None)
    ensure_directory_exists = getattr(utils_module, 'ensure_directory_exists', None)
    get_file_size = getattr(utils_module, 'get_file_size', None)
    get_file_mime_type = getattr(utils_module, 'get_file_mime_type', None)
    is_valid_filename = getattr(utils_module, 'is_valid_filename', None)
    sanitize_filename = getattr(utils_module, 'sanitize_filename', None)
    create_secure_filename = getattr(utils_module, 'create_secure_filename', None)
    validate_upload_file = getattr(utils_module, 'validate_upload_file', None)
    extract_file_metadata = getattr(utils_module, 'extract_file_metadata', None)
    list_directory_files = getattr(utils_module, 'list_directory_files', None)
    get_file_info = getattr(utils_module, 'get_file_info', None)
else:
    # Create dummy functions if utils.py doesn't exist
    def generate_temp_filename(*args, **kwargs): return ""
    def validate_file_exists(*args, **kwargs): return None
    def read_file_content(*args, **kwargs): return ""
    def write_file_content(*args, **kwargs): return True
    def safe_remove_file(*args, **kwargs): return True
    def ensure_directory_exists(*args, **kwargs): return True
    def get_file_size(*args, **kwargs): return 0
    def get_file_mime_type(*args, **kwargs): return "application/octet-stream"
    def is_valid_filename(*args, **kwargs): return True
    def sanitize_filename(*args, **kwargs): return ""
    def create_secure_filename(*args, **kwargs): return ""
    def validate_upload_file(*args, **kwargs): return True
    def extract_file_metadata(*args, **kwargs): return {}
    def list_directory_files(*args, **kwargs): return []
    def get_file_info(*args, **kwargs): return {}
