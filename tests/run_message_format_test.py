#!/usr/bin/env python
"""
Run message format tests without complex dependencies.
"""

import sys
import os
import subprocess
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("message_format_test_runner")

def run_message_format_tests():
    """Run message format tests."""
    logger.info("Running message format tests...")
    
    test_file = "tests/modified_message_test.py"
    if not os.path.exists(test_file):
        logger.error(f"Test file {test_file} not found.")
        return False
    
    try:
        # Run test with Python
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
            logger.error("Message format tests failed.")
            return False
        
        logger.info("Message format tests passed.")
        return True
        
    except Exception as e:
        logger.error(f"Error running message format tests: {str(e)}")
        return False

def main():
    """Main function."""
    logger.info("Starting message format test runner...")
    
    # Run tests
    success = run_message_format_tests()
    
    if success:
        logger.info("All message format tests passed!")
        return 0
    else:
        logger.error("Some tests failed. See output for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 