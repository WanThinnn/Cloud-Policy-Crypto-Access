"""
Configuration settings for the Hybrid CP-ABE Flask application
"""
import os
import platform

class Config:
    """Base configuration"""
    # Server settings
    HOST = '192.168.1.2'
    PORT = 5000
    DEBUG = False
    
    # Flask secret key for sessions
    SECRET_KEY = 'your-secret-key-change-in-production'
    
    # Upload folder
    UPLOAD_FOLDER = 'tmp'
    
    # System Service Authentication (SECURE WAY)
    # Thay vì hard-code admin ID, dùng service token để authenticate as system service
    SYSTEM_SERVICE_TOKEN = os.getenv('SYSTEM_SERVICE_TOKEN', 'ca-service-token-change-in-production')
    
    # Library settings
    @staticmethod
    def get_library_path():
        """Get library path based on OS"""
        system = platform.system().lower()
        # Library files are in app/lib folder
        base_dir = os.path.dirname(__file__)
        
        if system == 'windows':
            return os.path.join(base_dir, "lib", "libhybrid-cp-abe.dll")
        elif system == 'linux':
            return os.path.join(base_dir, "lib", "libhybrid-cp-abe.so")
        else:
            raise Exception(f"Unsupported operating system: {system}")
    
    # Logging
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    LOG_LEVEL = 'WARNING'

# Default config
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
