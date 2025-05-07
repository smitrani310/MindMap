#!/usr/bin/env python
"""
Test runner focused on message flow tests.
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
logger = logging.getLogger("message_flow_test_runner")

def run_message_flow_tests():
    """Run message flow tests."""
    logger.info("Running message flow tests...")
    
    test_file = "tests/debug_message_flow.py"
    if not os.path.exists(test_file):
        logger.error(f"Test file {test_file} not found.")
        return False
    
    try:
        # Run test with pytest
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_file, "-v"],
            capture_output=True,
            text=True
        )
        
        # Print output
        print(result.stdout)
        
        if result.stderr:
            print("Error output:")
            print(result.stderr)
        
        if result.returncode != 0:
            logger.error("Message flow tests failed.")
            return False
        
        logger.info("Message flow tests passed.")
        return True
        
    except Exception as e:
        logger.error(f"Error running message flow tests: {str(e)}")
        return False

def main():
    """Main function."""
    logger.info("Starting message flow test runner...")
    
    # Run tests
    success = run_message_flow_tests()
    
    if success:
        logger.info("All message flow tests passed!")
        return 0
    else:
        logger.error("Some tests failed. See output for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 