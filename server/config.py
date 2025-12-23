"""
Configuration module for Arduino Discord Controller
Centralized settings for the entire application
"""

import logging

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
LOGGING_CONFIG = {
    'level': logging.INFO,
    'format': '[%(asctime)s] %(levelname)s: %(message)s',
    'handlers': {
        'console': logging.StreamHandler(),
    }
}


def setup_logging(name=__name__):
    """Configure and return logger"""
    logger = logging.getLogger(name)
    logger.setLevel(LOGGING_CONFIG['level'])
    
    formatter = logging.Formatter(LOGGING_CONFIG['format'])
    handler = LOGGING_CONFIG['handlers']['console']
    handler.setFormatter(formatter)
    
    if not logger.handlers:
        logger.addHandler(handler)
    
    return logger
