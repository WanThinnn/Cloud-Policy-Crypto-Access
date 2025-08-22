"""
Enhanced logging utility with JSON formatter for ELK Stack compatibility
"""
import logging
import json
import os
from datetime import datetime

# Create logs directory
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'log')
os.makedirs(LOG_DIR, exist_ok=True)

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging compatible with ELK Stack"""
    
    def format(self, record):
        log_entry = {
            "@timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process_id": os.getpid(),
            "thread_id": record.thread,
            "service": "crypto-access-backend",
            "version": "1.0.0"
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info) if record.exc_info else None
            }
        
        # Add extra fields from record
        extra_fields = [
            'user_id', 'admin_id', 'request_id', 'ip_address', 'endpoint',
            'method', 'status_code', 'response_time', 'file_id', 'operation',
            'security_event', 'severity', 'error', 'execution_time', 'success'
        ]
        
        for field in extra_fields:
            if hasattr(record, field):
                log_entry[field] = getattr(record, field)
        
        return json.dumps(log_entry, ensure_ascii=False, default=str)

class StandardFormatter(logging.Formatter):
    """Standard formatter for console output"""
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

class ELKLogger:
    """Enhanced logger class with ELK Stack compatibility"""
    
    _loggers = {}
    
    @classmethod
    def get_logger(cls, name, use_json=False):
        """Get or create a logger with optional JSON formatting"""
        logger_key = f"{name}_{'json' if use_json else 'standard'}"
        
        if logger_key not in cls._loggers:
            logger = logging.getLogger(name)
            logger.setLevel(logging.INFO)
            
            # Remove existing handlers
            logger.handlers.clear()
            
            # File handler
            if use_json:
                log_file = os.path.join(LOG_DIR, f'{name}_json.log')
                formatter = JSONFormatter()
            else:
                log_file = os.path.join(LOG_DIR, f'{name}.log')
                formatter = StandardFormatter()
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
            # Console handler (always standard format)
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(StandardFormatter())
            logger.addHandler(console_handler)
            
            cls._loggers[logger_key] = logger
        
        return cls._loggers[logger_key]

# Create both standard and JSON loggers
def create_loggers():
    """Create all application loggers"""
    loggers = {}
    logger_names = [
        'app', 'auth', 'crypto', 'database', 'api', 
        'file_operations', 'admin', 'security', 'performance'
    ]
    
    for name in logger_names:
        # Standard logger
        loggers[name] = ELKLogger.get_logger(name, use_json=False)
        # JSON logger for ELK Stack
        loggers[f"{name}_json"] = ELKLogger.get_logger(name, use_json=True)
    
    return loggers

# Initialize loggers
all_loggers = create_loggers()

# Export standard loggers
app_logger = all_loggers['app']
auth_logger = all_loggers['auth']
crypto_logger = all_loggers['crypto']
database_logger = all_loggers['database']
api_logger = all_loggers['api']
file_logger = all_loggers['file_operations']
admin_logger = all_loggers['admin']
security_logger = all_loggers['security']
performance_logger = all_loggers['performance']

# Export JSON loggers for ELK Stack
app_json_logger = all_loggers['app_json']
auth_json_logger = all_loggers['auth_json']
crypto_json_logger = all_loggers['crypto_json']
database_json_logger = all_loggers['database_json']
api_json_logger = all_loggers['api_json']
file_json_logger = all_loggers['file_operations_json']
admin_json_logger = all_loggers['admin_json']
security_json_logger = all_loggers['security_json']
performance_json_logger = all_loggers['performance_json']

def log_with_context(logger, level, message, **context):
    """Log message with additional context for structured logging"""
    # Convert string level to integer
    if isinstance(level, str):
        level = getattr(logging, level.upper())
    
    record = logger.makeRecord(
        logger.name, level, __file__, 0, message, (), None
    )
    
    # Add context fields to record
    for key, value in context.items():
        setattr(record, key, value)
    
    logger.handle(record)
