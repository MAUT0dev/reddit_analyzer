"""
Logging configuration for the Reddit Analyzer system.
"""

import logging
import sys
from typing import Optional
from datetime import datetime
import os

def setup_logging(
    name: str,
    log_level: str = "INFO",
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Configure logging for a component of the system.
    
    Args:
        name: Name of the logger/component
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for logging output
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        # Ensure log directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def get_component_logger(
    component_name: str,
    log_dir: str = "logs"
) -> logging.Logger:
    """
    Get a logger for a specific component with both console and file output.
    
    Args:
        component_name: Name of the component requesting the logger
        log_dir: Directory to store log files
        
    Returns:
        Configured logger instance
    """
    # Create log filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d')
    log_file = f"{log_dir}/{component_name}_{timestamp}.log"
    
    return setup_logging(
        name=component_name,
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        log_file=log_file
    )
