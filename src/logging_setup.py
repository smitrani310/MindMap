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