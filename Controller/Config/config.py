"""
Configuration module for Arduino Discord Controller
Centralized settings for the entire application
"""

import logging
import os

# Server configuration
SERVER_CONFIG = {
    'host': '0.0.0.0',
    'port': 8765,
    'reuse_port': True,
}

# Serial communication configuration
SERIAL_CONFIG = {
    'baudrate': 9600,
    'timeout': 1,
}

# Application settings
APP_CONFIG = {
    'read_interval': 0.1,
    'retry_interval': 1,
}

# Logging configuration
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

LOGGING_CONFIG = {
    'level': logging.INFO,
    'format': '[%(asctime)s] %(levelname)s: %(message)s',
    'file': os.path.join(LOG_DIR, 'controller.log'),
    'max_bytes': 5 * 1024 * 1024,  # 5MB
    'backup_count': 3,
}


def setup_logging(name=__name__):
    """Configure and return logger"""
    logger = logging.getLogger(name)
    logger.setLevel(LOGGING_CONFIG['level'])
    
    # Only configure if this is the root logger
    if not logger.handlers:
        formatter = logging.Formatter(LOGGING_CONFIG['format'])
        
        # File handler with rotation
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            LOGGING_CONFIG['file'],
            maxBytes=LOGGING_CONFIG['max_bytes'],
            backupCount=LOGGING_CONFIG['backup_count']
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger
