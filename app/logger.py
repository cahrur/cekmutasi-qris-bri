"""
Structured logging configuration for QRIS mutation scraper
"""
import logging
import sys
from datetime import datetime
from typing import Optional


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Create structured log entry
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'level': record.levelname,
            'module': record.name,
            'message': record.getMessage(),
        }
        
        # Format as readable string
        formatted = f"[{log_data['timestamp']}] {log_data['level']:<8} {log_data['module']:<20} | {log_data['message']}"
        
        # Add extra data if present
        if hasattr(record, 'extra_data') and getattr(record, 'extra_data', None):
            extra_parts = []
            extra_data = getattr(record, 'extra_data')
            for key, value in extra_data.items():
                extra_parts.append(f"{key}={value}")
            if extra_parts:
                formatted += f" | {' '.join(extra_parts)}"
        
        return formatted


def setup_logger(name: str = 'qris_scraper', level: int = logging.INFO) -> logging.Logger:
    """Setup structured logger"""
    logger = logging.getLogger(name)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(StructuredFormatter())
    
    logger.addHandler(console_handler)
    
    return logger


class LoggerMixin:
    """Mixin class to add logging capabilities"""
    
    def __init__(self):
        self.logger = setup_logger(self.__class__.__name__)
    
    def log_info(self, message: str, **kwargs):
        """Log info message with optional extra data"""
        if kwargs:
            self.logger.info(message, extra={'extra_data': kwargs})
        else:
            self.logger.info(message)
    
    def log_error(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log error message with optional exception and extra data"""
        extra_data = kwargs.copy()
        if error:
            extra_data['error_type'] = type(error).__name__
            extra_data['error_message'] = str(error)
        
        if extra_data:
            self.logger.error(message, extra={'extra_data': extra_data})
        else:
            self.logger.error(message)
    
    def log_warning(self, message: str, **kwargs):
        """Log warning message with optional extra data"""
        if kwargs:
            self.logger.warning(message, extra={'extra_data': kwargs})
        else:
            self.logger.warning(message)
    
    def log_debug(self, message: str, **kwargs):
        """Log debug message with optional extra data"""
        if kwargs:
            self.logger.debug(message, extra={'extra_data': kwargs})
        else:
            self.logger.debug(message)


# Global logger instance
logger = setup_logger()
