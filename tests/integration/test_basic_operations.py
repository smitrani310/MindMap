#!/usr/bin/env python
"""
Integration tests for basic Mind Map operations.

This module tests the fundamental operations of the Mind Map application,
including:
- Message queue functionality
- Basic node operations
- State management
- Error handling
- System initialization

The tests are designed to run without external dependencies like PyVis,
making them suitable for quick verification of core functionality.
"""

import sys
import os
import subprocess
import unittest
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("simple_test_runner")

def run_simple_tests():
    """Run the simple queue tests.
    
    Executes basic message queue tests to verify core functionality.
    Tests include:
    - Message creation and validation
    - Queue operations (enqueue, dequeue)
    - Message processing
    - Error handling
    - State management
    
    Returns:
        bool: True if all tests pass, False otherwise
    """
    logger.info("Running simple message queue tests...")
    
    # Check if test file exists
    test_file = "tests/simple_queue_test.py"
    if not os.path.exists(test_file):
        logger.error(f"Test file {test_file} not found.")
        return False
    
    # Run the test
    try:
        # Run test with unittest module
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True
        )
        
        # Print output
        print(result.stdout)
        
        if result.stderr:
            print("Error output:")
            print(result.stderr)
        
        if result.returncode != 0:
            logger.error("Simple queue tests failed.")
            return False
        
        logger.info("Simple queue tests passed.")
        return True
        
    except Exception as e:
        logger.error(f"Error running simple queue tests: {str(e)}")
        return False

def check_message_queue():
    """Check the message queue implementation.
    
    Verifies the presence and structure of the message queue implementation.
    Checks for:
    - Required file existence
    - File size and line count
    - Presence of critical methods
    - Basic code structure
    
    This function helps ensure the message queue is properly implemented
    before running tests.
    """
    logger.info("Checking message queue implementation...")
    
    # Check if message queue file exists
    message_queue_file = "src/message_queue.py"
    if not os.path.exists(message_queue_file):
        logger.error(f"Message queue file {message_queue_file} not found.")
        return
    
    # Print message queue file info
    try:
        with open(message_queue_file, 'r') as f:
            content = f.read()
            
        # Print simple stats
        logger.info(f"Message queue file size: {len(content)} bytes")
        logger.info(f"Message queue file lines: {len(content.split(os.linesep))}")
        
        # Check for critical methods
        methods = [
            "_worker_loop",      # Main processing loop
            "_process_next_message",  # Message processing
            "enqueue",           # Message addition
            "start",            # Queue initialization
            "stop"              # Queue cleanup
        ]
        
        for method in methods:
            if method in content:
                logger.info(f"Found method: {method}")
            else:
                logger.warning(f"Missing method: {method}")
                
    except Exception as e:
        logger.error(f"Error checking message queue: {str(e)}")

def main():
    """Main function to run basic operation tests.
    
    Orchestrates the testing process by:
    1. Checking message queue implementation
    2. Running simple queue tests
    3. Reporting results
    
    Returns:
        int: 0 for success, 1 for failure
    """
    logger.info("Starting simple test runner...")
    
    # Check message queue implementation
    check_message_queue()
    
    # Run tests
    success = run_simple_tests()
    
    if success:
        logger.info("All simple tests passed!")
        return 0
    else:
        logger.error("Some tests failed. See output for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 