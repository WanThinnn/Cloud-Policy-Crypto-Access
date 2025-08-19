"""
File management API routes
For handling file uploads, downloads, and management
"""
from flask import Blueprint, request, jsonify, send_file, current_app
import logging
import sys
import os
from werkzeug.utils import secure_filename

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils import ensure_directory_exists, list_directory_files

logger = logging.getLogger(__name__)

# Create Files Blueprint
files_api = Blueprint('files', __name__, url_prefix='/files')

@files_api.route('/health', methods=['GET'])
def files_health():
    """Health check cho files API"""
    return jsonify({
        'success': True,
        'service': 'File Management API',
        'status': 'healthy',
        'endpoints': {
            'GET /files/health': 'Files health check',
            'GET /files/list': 'List uploaded files',
            'POST /files/upload': 'Upload file (future)',
            'GET /files/download/<filename>': 'Download file (future)',
            'DELETE /files/<filename>': 'Delete file (future)',
            'GET /files/info/<filename>': 'Get file info (future)'
        }
    }), 200

@files_api.route('/list', methods=['GET'])
def list_files():
    """List all files in upload directory"""
    try:
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'tmp')
        files = list_directory_files(upload_folder)
        
        return jsonify({
            'success': True,
            'files': files,
            'count': len(files),
            'upload_folder': upload_folder
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to list files'
        }), 500

# Future file management endpoints:
# @files_api.route('/upload', methods=['POST'])
# def upload_file():
#     """Upload a file to server"""
#     pass
# 
# @files_api.route('/download/<filename>', methods=['GET'])
# def download_file(filename):
#     """Download a file from server"""
#     pass
# 
# @files_api.route('/<filename>', methods=['DELETE'])
# def delete_file(filename):
#     """Delete a file from server"""
#     pass
