"""
ABE (Attribute-Based Encryption) API routes - CLEANED VERSION
Removed duplicated endpoints: setup, public-key  
Only core ABE operations: encrypt, decrypt, generate-key
"""
from flask import Blueprint, request, jsonify, current_app
import logging
import os
import platform
from datetime import datetime
import sys

# Add parent directory to path to import module
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from module import abe_lib
from utils.logger import AppLogger

logger = AppLogger.get_logger('abe')

# Create ABE Blueprint
abe_api = Blueprint('abe', __name__, url_prefix='/abe')

@abe_api.route('/', methods=['GET'])
def abe_info():
    """
    ABE system information endpoint
    
    Returns:
        JSON response with ABE system info
    """
    return jsonify({
        'service': 'ABE (Attribute-Based Encryption) API',
        'version': '1.0.0',
        'description': 'Core ABE operations for encryption and decryption',
        'system': platform.system(),
        'library_loaded': abe_lib.is_loaded() if abe_lib and hasattr(abe_lib, 'is_loaded') else False,
        'library_path': abe_lib.get_lib_path() if abe_lib and hasattr(abe_lib, 'is_loaded') and abe_lib.is_loaded() else 'N/A',
        'upload_folder': current_app.config['UPLOAD_FOLDER']
    })

@abe_api.route('/health', methods=['GET'])
def health_check():
    """ABE health check endpoint"""
    return jsonify({
        'status': 'healthy' if abe_lib and hasattr(abe_lib, 'is_loaded') and abe_lib.is_loaded() else 'error',
        'service': 'ABE API',
        'library_loaded': abe_lib.is_loaded() if abe_lib and hasattr(abe_lib, 'is_loaded') else False,
        'library_path': abe_lib.get_lib_path() if abe_lib and hasattr(abe_lib, 'is_loaded') and abe_lib.is_loaded() else 'N/A',
        'timestamp': datetime.utcnow().isoformat()
    })

@abe_api.route('/encrypt', methods=['POST'])
def encrypt():
    """Encrypt data with ABE policy"""
    if not abe_lib or not hasattr(abe_lib, 'is_loaded') or not abe_lib.is_loaded():
        return jsonify({'error': 'ABE library not loaded'}), 500
    
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'File is required'}), 400
        
        file = request.files['file']
        policy = request.form.get('policy')
        
        if not policy:
            return jsonify({'error': 'Policy is required'}), 400
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Save uploaded file temporarily
        from utils import generate_temp_filename
        
        plaintext_path = generate_temp_filename(current_app.config['UPLOAD_FOLDER'], "plaintext_", ".txt")
        ciphertext_path = generate_temp_filename(current_app.config['UPLOAD_FOLDER'], "ciphertext_", ".cpabe")
        
        file.save(plaintext_path)
        
        # Use system public key
        public_key_path = os.path.join(current_app.config['UPLOAD_FOLDER'], '../abe_keys/public_key.key')
        
        # Encrypt using ABE library
        if abe_lib and hasattr(abe_lib, 'encrypt'):
            abe_lib.encrypt(public_key_path, plaintext_path, policy, ciphertext_path)
        
        # Read encrypted file
        with open(ciphertext_path, 'rb') as f:
            encrypted_data = f.read()
        
        # Cleanup temp files
        os.unlink(plaintext_path)
        os.unlink(ciphertext_path)
        
        # Return as base64
        import base64
        encrypted_b64 = base64.b64encode(encrypted_data).decode('utf-8')
        
        return jsonify({
            'success': True,
            'message': 'File encrypted successfully',
            'policy': policy,
            'encrypted_data': encrypted_b64,
            'original_filename': file.filename
        })
        
    except Exception as e:
        logger.error(f"Encryption error: {e}")
        return jsonify({'error': str(e)}), 500

@abe_api.route('/decrypt', methods=['POST'])
def decrypt():
    """Decrypt ABE encrypted data"""
    if not abe_lib or not hasattr(abe_lib, 'is_loaded') or not abe_lib.is_loaded():
        return jsonify({'error': 'ABE library not loaded'}), 500
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON data required'}), 400
        
        encrypted_data_b64 = data.get('encrypted_data')
        user_id = data.get('user_id')
        private_key_path = data.get('private_key_path')
        
        if not encrypted_data_b64 or not user_id:
            return jsonify({'error': 'encrypted_data and user_id are required'}), 400
        
        # Decode base64
        import base64
        try:
            encrypted_data = base64.b64decode(encrypted_data_b64)
        except Exception:
            return jsonify({'error': 'Invalid base64 data'}), 400
        
        # Create temp files
        from utils import generate_temp_filename
        
        ciphertext_path = generate_temp_filename(current_app.config['UPLOAD_FOLDER'], "ciphertext_", ".cpabe")
        recovertext_path = generate_temp_filename(current_app.config['UPLOAD_FOLDER'], "recovered_", ".txt")
        
        # Write encrypted data to file
        with open(ciphertext_path, 'wb') as f:
            f.write(encrypted_data)
        
        # Use system public key and user private key
        public_key_path = os.path.join(current_app.config['UPLOAD_FOLDER'], '../abe_keys/public_key.key')
        
        if not private_key_path:
            # Default private key path for user
            private_key_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f"key_{user_id}", f"private_key_{user_id}.key")
        
        if not os.path.exists(private_key_path):
            return jsonify({'error': 'Private key not found for user'}), 404
        
        # Decrypt using ABE library
        if abe_lib and hasattr(abe_lib, 'decrypt'):
            abe_lib.decrypt(public_key_path, private_key_path, ciphertext_path, recovertext_path)
        
        # Read decrypted data
        with open(recovertext_path, 'rb') as f:
            decrypted_data = f.read()
        
        # Cleanup temp files
        os.unlink(ciphertext_path)
        os.unlink(recovertext_path)
        
        # Return as base64
        decrypted_b64 = base64.b64encode(decrypted_data).decode('utf-8')
        
        return jsonify({
            'success': True,
            'message': 'File decrypted successfully',
            'user_id': user_id,
            'decrypted_data': decrypted_b64
        })
        
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        return jsonify({'error': str(e)}), 500

@abe_api.route('/files', methods=['GET'])
def list_files():
    """List ABE related files in upload directory"""
    try:
        upload_folder = current_app.config['UPLOAD_FOLDER']
        files = []
        
        for filename in os.listdir(upload_folder):
            file_path = os.path.join(upload_folder, filename)
            if os.path.isfile(file_path):
                files.append({
                    'name': filename,
                    'size': os.path.getsize(file_path),
                    'type': 'ciphertext' if filename.endswith('.cpabe') else 'other'
                })
        
        return jsonify({
            'success': True,
            'files': files,
            'total': len(files),
            'upload_folder': upload_folder
        })
        
    except Exception as e:
        logger.error(f"List files error: {e}")
        return jsonify({'error': str(e)}), 500
