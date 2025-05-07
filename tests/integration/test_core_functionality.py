#!/usr/bin/env python
"""
Simple test runner for the core message queue functionality.
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
logger = logging.getLogger("simplest_test_runner")

def run_simplest_tests():
    """Run the simplest queue tests."""
    logger.info("Running simplest message queue tests...")
    
    # Check if test file exists
    test_file = "tests/simplest_queue_test.py"
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
            logger.error("Simplest queue tests failed.")
            return False
        
        logger.info("Simplest queue tests passed.")
        return True
        
    except Exception as e:
        logger.error(f"Error running simplest queue tests: {str(e)}")
        return False

def main():
    """Main function."""
    logger.info("Starting simplest test runner...")
    
    # Run tests
    success = run_simplest_tests()
    
    if success:
        logger.info("All simplest tests passed!")
        return 0
    else:
        logger.error("Some tests failed. See output for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 