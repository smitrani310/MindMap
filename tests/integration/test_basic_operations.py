#!/usr/bin/env python
"""
Simple test runner for MindMap application.
This script runs tests without requiring PyVis.
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
    """Run the simple queue tests."""
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
    """Check the message queue implementation."""
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
            "_worker_loop",
            "_process_next_message",
            "enqueue",
            "start",
            "stop"
        ]
        
        for method in methods:
            if method in content:
                logger.info(f"Found method: {method}")
            else:
                logger.warning(f"Missing method: {method}")
                
    except Exception as e:
        logger.error(f"Error checking message queue: {str(e)}")

def main():
    """Main function."""
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