"""
Configuration module for Arduino Discord Controller
Centralized settings for the entire application
"""

import logging
import os
from functools import lru_cache
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv
    config_env_path = Path(__file__).parent / 'config.env'
    load_dotenv(config_env_path)
except ImportError:
    pass  # dotenv not installed, use environment variables directly


def _get_env_int(key: str, default: int) -> int:
    """Get integer environment variable with fallback"""
    try:
        return int(os.getenv(key, default))
    except (ValueError, TypeError):
        return default


def _get_env_str(key: str, default: str) -> str:
    """Get string environment variable with fallback"""
    return os.getenv(key, default)


def _get_env_float(key: str, default: float) -> float:
    """Get float environment variable with fallback"""
    try:
        return float(os.getenv(key, default))
    except (ValueError, TypeError):
        return default


# Setup log directory
LOG_DIR = Path(__file__).parent.parent / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Server configuration
SERVER_CONFIG = {
    'host': '0.0.0.0',
    'port': _get_env_int('WEBSOCKET_PORT', 8765),
    'reuse_port': True,
}

# Serial communication configuration
SERIAL_CONFIG = {
    'baudrate': _get_env_int('ARDUINO_BAUDRATE', 9600),
    'timeout': _get_env_int('ARDUINO_TIMEOUT', 1),
}

# Application settings
APP_CONFIG = {
    'read_interval': 0.1,
    'retry_interval': 1,
    'reconnect_attempts': _get_env_int('RECONNECT_ATTEMPTS', 10),
    'reconnect_delay': _get_env_int('RECONNECT_DELAY', 2000) / 1000,  # Convert ms to seconds
}

# Logging settings
LOGGING_CONFIG = {
    'level': getattr(logging, _get_env_str('LOG_LEVEL', 'INFO').upper()),
    'format': '[%(asctime)s] %(levelname)s: %(message)s',
    'file': LOG_DIR / 'controller.log',
    'max_bytes': 5 * 1024 * 1024,  # 5MB
    'backup_count': 3,
}


@lru_cache(maxsize=1)
def setup_logging(name: str = __name__) -> logging.Logger:
    """Configure and return logger (cached for performance)"""
    logger = logging.getLogger(name)
    logger.setLevel(LOGGING_CONFIG['level'])
    
    # Only configure if no handlers exist
    if not logger.handlers:
        try:
            formatter = logging.Formatter(LOGGING_CONFIG['format'])
            
            # File handler with rotation
            file_handler = RotatingFileHandler(
                str(LOGGING_CONFIG['file']),
                maxBytes=LOGGING_CONFIG['max_bytes'],
                backupCount=LOGGING_CONFIG['backup_count']
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except (OSError, IOError) as e:
            logger.warning(f"Could not setup file handler: {e}")
    
    return logger
