"""
Configuration settings for the Hybrid CP-ABE Flask application
"""
import os
import platform

class Config:
    """Base configuration"""
    # Server settings
    HOST = '127.0.0.1'
    PORT = 5000
    DEBUG = False
    
    # Upload folder
    UPLOAD_FOLDER = 'tmp'
    
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
