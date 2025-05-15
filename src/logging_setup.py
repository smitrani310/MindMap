"""Logging setup for the mindmap application."""

import logging
import datetime
import os

# Create logs directory if it doesn't exist
logs_dir = "logs"
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

def get_logger(name=None):
    """Get a logger instance with proper configuration.
    
    Args:
        name: Optional name for the logger, defaults to the root logger
        
    Returns:
        A configured logger instance
    """
    # Get the logger - either named or root
    logger = logging.getLogger(name)
    
    # Only configure if handlers haven't been set up
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        
        # Generate a unique log filename with timestamp if needed
        current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = os.path.join(logs_dir, f"mindmap_session_{current_time}.log")
        
        # Set up file handler for debug+ messages
        file_handler = logging.FileHandler(log_filename)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        
        # Set up console handler for info+ messages
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(
            logging.Formatter('%(levelname)s: %(message)s')
        )
        
        # Add the handlers to the logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        # Log initialization
        logger.info(f"Logger initialized. Logging to: {log_filename}")
    
    return logger

def create_new_log():
    """Create a new log file and reset the logger.
    
    Returns:
        str: Path to the new log file
    """
    # Close existing file handlers
    for handler in logging.getLogger().handlers[:]:
        handler.close()
        logging.getLogger().removeHandler(handler)
    
    # Generate a new log filename with timestamp
    current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(logs_dir, f"mindmap_session_{current_time}.log")
    
    # Set up new handlers
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers = []  # Remove any existing handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Log initialization
    root_logger.info(f"Created new log file: {log_filename}")
    
    return log_filename 