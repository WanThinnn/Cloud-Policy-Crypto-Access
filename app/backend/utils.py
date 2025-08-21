"""
Utility functions for the Hybrid CP-ABE Flask application
"""
import os
import uuid
import logging

logger = logging.getLogger(__name__)

def generate_temp_filename(upload_folder, prefix="", suffix=""):
    """Generate a temporary filename with UUID"""
    return os.path.join(upload_folder, f"{prefix}{uuid.uuid4().hex}{suffix}")

def validate_file_exists(file_path, file_type="File"):
    """Validate if a file exists and return error message if not"""
    if not os.path.exists(file_path):
        return f"{file_type} not found: {file_path}"
    return None

def read_file_content(file_path, encoding='utf-8'):
    """Read file content with fallback encoding"""
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    except UnicodeDecodeError:
        logger.warning(f"Failed to read {file_path} with {encoding}, trying binary mode")
        with open(file_path, 'rb') as f:
            return f.read().decode('utf-8', errors='ignore')

def write_file_content(file_path, content, encoding='utf-8'):
    """Write content to file"""
    with open(file_path, 'w', encoding=encoding) as f:
        f.write(content)

def get_file_info(file_path):
    """Get file information"""
    if os.path.exists(file_path):
        return {
            'name': os.path.basename(file_path),
            'size': os.path.getsize(file_path),
            'path': file_path,
            'exists': True
        }
    else:
        return {
            'name': os.path.basename(file_path),
            'size': 0,
            'path': file_path,
            'exists': False
        }

def list_directory_files(directory_path):
    """List all files in a directory with their info"""
    files = []
    if os.path.exists(directory_path):
        for filename in os.listdir(directory_path):
            file_path = os.path.join(directory_path, filename)
            if os.path.isfile(file_path):
                files.append(get_file_info(file_path))
    return files

def ensure_directory_exists(directory_path):
    """Ensure directory exists, create if not"""
    os.makedirs(directory_path, exist_ok=True)
    return directory_path
