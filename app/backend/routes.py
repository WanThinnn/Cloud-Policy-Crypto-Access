"""
API routes for the Hybrid CP-ABE Flask application
"""
from flask import Blueprint, request, jsonify, current_app
import os
import platform
import logging
import traceback
from module import abe_lib
from utils import (
    generate_temp_filename, validate_file_exists, 
    read_file_content, write_file_content,
    list_directory_files, ensure_directory_exists
)

logger = logging.getLogger(__name__)

# Create Blueprint
api = Blueprint('api', __name__)

@api.route('/', methods=['GET'])
def home():
    """Home endpoint với thông tin API"""
    return jsonify({
        'name': 'Hybrid CP-ABE Flask Backend',
        'version': '1.0.0',
        'system': platform.system(),
        'library_loaded': abe_lib.is_loaded(),
        'endpoints': {
            'GET /': 'API information',
            'GET /health': 'Health check',
            'POST /setup': 'Setup ABE system',
            'POST /generate-key': 'Generate secret key',
            'POST /encrypt': 'Encrypt data',
            'POST /decrypt': 'Decrypt data',
            'GET /files': 'List temp files'
        }
    })

@api.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy' if abe_lib.is_loaded() else 'error',
        'system': platform.system(),
        'library_loaded': abe_lib.is_loaded(),
        'library_path': abe_lib.get_lib_path() if abe_lib.is_loaded() else 'N/A',
        'upload_folder': current_app.config['UPLOAD_FOLDER']
    })

@api.route('/setup', methods=['POST'])
def setup():
    """Endpoint để setup ABE system"""
    if not abe_lib.is_loaded():
        return jsonify({'error': 'ABE library not loaded'}), 500
    
    try:
        # Tạo thư mục tạm thời để lưu keys
        setup_dir = generate_temp_filename(current_app.config['UPLOAD_FOLDER'], "setup_", "")
        ensure_directory_exists(setup_dir)
        
        logger.info(f"Setting up ABE system at: {setup_dir}")
        
        # Gọi ABE setup
        abe_lib.setup(setup_dir)
        
        # Đường dẫn public key và master key được tạo bởi thư viện C++
        public_key_path = os.path.join(setup_dir, "public_key.key")
        master_key_path = os.path.join(setup_dir, "master_key.key")
        
        # Kiểm tra xem file có được tạo không
        if os.path.exists(public_key_path) and os.path.exists(master_key_path):
            logger.info(f"Setup completed successfully. Files created: {public_key_path}, {master_key_path}")
        else:
            logger.warning(f"Setup completed but files may not exist: {public_key_path}, {master_key_path}")
        
        response_data = {
            'status': 'success',
            'message': 'Setup completed successfully',
            'public_key_path': public_key_path,
            'master_key_path': master_key_path,
            'setup_directory': setup_dir
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Setup error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e), 'details': 'Check server logs for more information'}), 500

@api.route('/generate-key', methods=['POST'])
def generate_key():
    """Endpoint để tạo secret key"""
    if not abe_lib.is_loaded():
        return jsonify({'error': 'ABE library not loaded'}), 500
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        required_fields = ['public_key_path', 'master_key_path', 'attributes']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        public_key_path = data['public_key_path']
        master_key_path = data['master_key_path']
        attributes = data['attributes']
        
        # Validate key files exist
        error = validate_file_exists(public_key_path, "Public key file")
        if error:
            return jsonify({'error': error}), 400
        
        error = validate_file_exists(master_key_path, "Master key file")
        if error:
            return jsonify({'error': error}), 400
        
        # Tạo đường dẫn cho private key
        private_key_path = generate_temp_filename(current_app.config['UPLOAD_FOLDER'], "private_key_", ".key")
        
        logger.info(f"Generating secret key with attributes: {attributes}")
        
        # Gọi ABE generate secret key
        abe_lib.generate_secret_key(public_key_path, master_key_path, attributes, private_key_path)
        
        return jsonify({
            'status': 'success',
            'message': 'Secret key generated successfully',
            'private_key_path': private_key_path,
            'attributes': attributes
        })
        
    except Exception as e:
        logger.error(f"Generate key error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e), 'details': 'Check server logs for more information'}), 500

@api.route('/encrypt', methods=['POST'])
def encrypt():
    """Endpoint để mã hóa"""
    if not abe_lib.is_loaded():
        return jsonify({'error': 'ABE library not loaded'}), 500
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        required_fields = ['public_key_path', 'policy']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        public_key_path = data['public_key_path']
        policy = data['policy']
        
        # Validate public key exists
        error = validate_file_exists(public_key_path, "Public key file")
        if error:
            return jsonify({'error': error}), 400
        
        # Tạo file plaintext từ text
        plaintext_path = generate_temp_filename(current_app.config['UPLOAD_FOLDER'], "plaintext_", ".txt")
        plaintext_content = data.get('plaintext', '')
        
        write_file_content(plaintext_path, plaintext_content)
        
        # Tạo đường dẫn cho ciphertext
        ciphertext_path = generate_temp_filename(current_app.config['UPLOAD_FOLDER'], "ciphertext_", ".enc")
        
        logger.info(f"Encrypting with policy: {policy}")
        
        # Gọi ABE encrypt
        abe_lib.encrypt(public_key_path, plaintext_path, policy, ciphertext_path)
        
        return jsonify({
            'status': 'success',
            'message': 'Encryption completed successfully',
            'ciphertext_path': ciphertext_path,
            'plaintext_path': plaintext_path,
            'policy': policy
        })
        
    except Exception as e:
        logger.error(f"Encryption error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e), 'details': 'Check server logs for more information'}), 500

@api.route('/decrypt', methods=['POST'])
def decrypt():
    """Endpoint để giải mã"""
    if not abe_lib.is_loaded():
        return jsonify({'error': 'ABE library not loaded'}), 500
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        required_fields = ['public_key_path', 'private_key_path', 'ciphertext_path']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        public_key_path = data['public_key_path']
        private_key_path = data['private_key_path']
        ciphertext_path = data['ciphertext_path']
        
        # Validate all files exist
        for file_path, file_type in [
            (public_key_path, "Public key file"),
            (private_key_path, "Private key file"),
            (ciphertext_path, "Ciphertext file")
        ]:
            error = validate_file_exists(file_path, file_type)
            if error:
                return jsonify({'error': error}), 400
        
        # Tạo đường dẫn cho recovered text
        recovertext_path = generate_temp_filename(current_app.config['UPLOAD_FOLDER'], "recovered_", ".txt")
        
        logger.info(f"Decrypting ciphertext: {ciphertext_path}")
        
        # Gọi ABE decrypt
        abe_lib.decrypt(public_key_path, private_key_path, ciphertext_path, recovertext_path)
        
        # Đọc nội dung file đã giải mã
        recovered_content = ""
        if os.path.exists(recovertext_path):
            recovered_content = read_file_content(recovertext_path)
        else:
            logger.warning(f"Recovered text file not found: {recovertext_path}")
        
        return jsonify({
            'status': 'success',
            'message': 'Decryption completed successfully',
            'recovered_content': recovered_content,
            'recovertext_path': recovertext_path
        })
        
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e), 'details': 'Check server logs for more information'}), 500

@api.route('/files', methods=['GET'])
def list_files():
    """List các file trong temp folder"""
    try:
        files = list_directory_files(current_app.config['UPLOAD_FOLDER'])
        
        return jsonify({
            'status': 'success',
            'files': files,
            'count': len(files)
        })
        
    except Exception as e:
        logger.error(f"List files error: {e}")
        return jsonify({'error': str(e)}), 500
