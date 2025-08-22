"""
Simple logging utility for Cloud Firestore Crypto Access
"""
import logging
import os
import json
from datetime import datetime

# Create logs directory
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'log')
os.makedirs(LOG_DIR, exist_ok=True)

class AppLogger:
    _loggers = {}
    
    @classmethod
    def get_logger(cls, name):
        """Get or create a logger for the given name"""
        if name not in cls._loggers:
            logger = logging.getLogger(name)
            logger.setLevel(logging.INFO)
            
            # Remove existing handlers
            logger.handlers.clear()
            
            # File handler
            log_file = os.path.join(LOG_DIR, f'{name}.log')
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            
            # Formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            
            cls._loggers[name] = logger
            
        return cls._loggers[name]

# Global loggers
app_logger = AppLogger.get_logger('app')
auth_logger = AppLogger.get_logger('auth')
crypto_logger = AppLogger.get_logger('crypto')
database_logger = AppLogger.get_logger('database')
api_logger = AppLogger.get_logger('api')
file_logger = AppLogger.get_logger('file_operations')
admin_logger = AppLogger.get_logger('admin')
security_logger = AppLogger.get_logger('security')
performance_logger = AppLogger.get_logger('performance')
