from flask import Flask, request, jsonify
import ctypes
from ctypes import c_char_p
import os
import platform
import uuid
import logging
import traceback

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Cấu hình upload
UPLOAD_FOLDER = 'temp_files'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Tạo thư mục temp nếu chưa tồn tại
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Global variables
abe_lib = None
library_loaded = False
lib_path = ""

def load_library():
    """Load thư viện ABE"""
    global abe_lib, library_loaded, lib_path
    
    try:
        system = platform.system().lower()
        if system == 'windows':
            lib_path = os.path.join(os.path.dirname(__file__), "lib", "libhybrid-cp-abe.dll")
        elif system == 'linux':
            lib_path = os.path.join(os.path.dirname(__file__), "lib", "libhybrid-cp-abe.so")
        else:
            raise Exception(f"Unsupported operating system: {system}")
        
        if not os.path.exists(lib_path):
            raise Exception(f"Library file not found: {lib_path}")
        
        abe_lib = ctypes.CDLL(lib_path)
        
        # Setup function prototypes
        abe_lib.setup.argtypes = [c_char_p]
        abe_lib.setup.restype = None
        
        abe_lib.generateSecretKey.argtypes = [c_char_p, c_char_p, c_char_p, c_char_p]
        abe_lib.generateSecretKey.restype = None
        
        abe_lib.AC17encrypt.argtypes = [c_char_p, c_char_p, c_char_p, c_char_p]
        abe_lib.AC17encrypt.restype = None
        
        abe_lib.AC17decrypt.argtypes = [c_char_p, c_char_p, c_char_p, c_char_p]
        abe_lib.AC17decrypt.restype = None
        
        library_loaded = True
        logger.info(f"Successfully loaded library: {lib_path}")
        return True
        
    except Exception as e:
        library_loaded = False
        logger.error(f"Failed to load library: {e}")
        logger.error(traceback.format_exc())
        return False

def generate_temp_filename(prefix="", suffix=""):
    """Tạo tên file tạm thời"""
    return os.path.join(app.config['UPLOAD_FOLDER'], f"{prefix}{uuid.uuid4().hex}{suffix}")

@app.route('/', methods=['GET'])
def home():
    """Home endpoint với thông tin API"""
    return jsonify({
        'name': 'Hybrid CP-ABE Flask Backend',
        'version': '1.0.0',
        'system': platform.system(),
        'library_loaded': library_loaded,
        'endpoints': {
            'GET /health': 'Health check',
            'POST /setup': 'Setup ABE system',
            'POST /generate-key': 'Generate secret key',
            'POST /encrypt': 'Encrypt data',
            'POST /decrypt': 'Decrypt data'
        }
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy' if library_loaded else 'error',
        'system': platform.system(),
        'library_loaded': library_loaded,
        'library_path': lib_path if library_loaded else 'N/A',
        'upload_folder': app.config['UPLOAD_FOLDER']
    })

@app.route('/setup', methods=['POST'])
def setup():
    """Endpoint để setup ABE system"""
    if not library_loaded:
        return jsonify({'error': 'ABE library not loaded'}), 500
    
    try:
        # Tạo thư mục tạm thời để lưu keys
        setup_dir = generate_temp_filename("setup_", "")
        os.makedirs(setup_dir, exist_ok=True)  # Tạo thư mục trước
        
        logger.info(f"Setting up ABE system at: {setup_dir}")
        
        abe_lib.setup(setup_dir.encode('utf-8'))
        
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

@app.route('/generate-key', methods=['POST'])
def generate_key():
    """Endpoint để tạo secret key"""
    if not library_loaded:
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
        
        # Kiểm tra xem các file key có tồn tại không
        if not os.path.exists(public_key_path):
            return jsonify({'error': f'Public key file not found: {public_key_path}'}), 400
        if not os.path.exists(master_key_path):
            return jsonify({'error': f'Master key file not found: {master_key_path}'}), 400
        
        # Tạo đường dẫn cho private key
        private_key_path = generate_temp_filename("private_key_", ".key")
        
        logger.info(f"Generating secret key with attributes: {attributes}")
        
        abe_lib.generateSecretKey(
            public_key_path.encode('utf-8'),
            master_key_path.encode('utf-8'),
            attributes.encode('utf-8'),
            private_key_path.encode('utf-8')
        )
        
        logger.info(f"Secret key generated: {private_key_path}")
        
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

@app.route('/encrypt', methods=['POST'])
def encrypt():
    """Endpoint để mã hóa"""
    if not library_loaded:
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
        
        # Kiểm tra public key có tồn tại không
        if not os.path.exists(public_key_path):
            return jsonify({'error': f'Public key file not found: {public_key_path}'}), 400
        
        # Tạo file plaintext từ text
        plaintext_path = generate_temp_filename("plaintext_", ".txt")
        plaintext_content = data.get('plaintext', '')
        
        with open(plaintext_path, 'w', encoding='utf-8') as f:
            f.write(plaintext_content)
        
        # Tạo đường dẫn cho ciphertext
        ciphertext_path = generate_temp_filename("ciphertext_", ".enc")
        
        logger.info(f"Encrypting with policy: {policy}")
        
        abe_lib.AC17encrypt(
            public_key_path.encode('utf-8'),
            plaintext_path.encode('utf-8'),
            policy.encode('utf-8'),
            ciphertext_path.encode('utf-8')
        )
        
        logger.info(f"Encryption completed: {ciphertext_path}")
        
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

@app.route('/decrypt', methods=['POST'])
def decrypt():
    """Endpoint để giải mã"""
    if not library_loaded:
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
        
        # Kiểm tra các file có tồn tại không
        if not os.path.exists(public_key_path):
            return jsonify({'error': f'Public key file not found: {public_key_path}'}), 400
        if not os.path.exists(private_key_path):
            return jsonify({'error': f'Private key file not found: {private_key_path}'}), 400
        if not os.path.exists(ciphertext_path):
            return jsonify({'error': f'Ciphertext file not found: {ciphertext_path}'}), 400
        
        # Tạo đường dẫn cho recovered text
        recovertext_path = generate_temp_filename("recovered_", ".txt")
        
        logger.info(f"Decrypting ciphertext: {ciphertext_path}")
        
        abe_lib.AC17decrypt(
            public_key_path.encode('utf-8'),
            private_key_path.encode('utf-8'),
            ciphertext_path.encode('utf-8'),
            recovertext_path.encode('utf-8')
        )
        
        # Đọc nội dung file đã giải mã
        recovered_content = ""
        if os.path.exists(recovertext_path):
            try:
                with open(recovertext_path, 'r', encoding='utf-8') as f:
                    recovered_content = f.read()
            except UnicodeDecodeError:
                # Nếu không đọc được UTF-8, thử binary
                with open(recovertext_path, 'rb') as f:
                    recovered_content = f.read().decode('utf-8', errors='ignore')
        else:
            logger.warning(f"Recovered text file not found: {recovertext_path}")
        
        logger.info(f"Decryption completed: {recovertext_path}")
        
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

@app.route('/files', methods=['GET'])
def list_files():
    """List các file trong temp folder"""
    try:
        files = []
        if os.path.exists(app.config['UPLOAD_FOLDER']):
            for filename in os.listdir(app.config['UPLOAD_FOLDER']):
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                if os.path.isfile(file_path):
                    file_info = {
                        'name': filename,
                        'size': os.path.getsize(file_path),
                        'path': file_path
                    }
                    files.append(file_info)
        
        return jsonify({
            'status': 'success',
            'files': files,
            'count': len(files)
        })
        
    except Exception as e:
        logger.error(f"List files error: {e}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

# Initialize library when module is loaded
load_library()

if __name__ == '__main__':
    print("=" * 60)
    print("Starting Hybrid CP-ABE Flask Backend")
    print("=" * 60)
    print(f"System: {platform.system()}")
    print(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    print(f"Library loaded: {library_loaded}")
    if library_loaded:
        print(f"Library path: {lib_path}")
    print("=" * 60)
    print("\nAvailable endpoints:")
    print("  GET  /          - API information")
    print("  GET  /health    - Health check")
    print("  POST /setup     - Setup ABE system")
    print("  POST /generate-key - Generate secret key")
    print("  POST /encrypt   - Encrypt data")
    print("  POST /decrypt   - Decrypt data")
    print("  GET  /files     - List temp files")
    print("=" * 60)
    print(f"\nServer starting on http://127.0.0.1:5000")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    
    # Chạy server mà không có debug mode để tránh restart
    app.run(host='127.0.0.1', port=5000, debug=False)
