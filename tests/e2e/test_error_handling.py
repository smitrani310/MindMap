#!/usr/bin/env python
"""
Debug test runner for MindMap application.
This script runs the debug tests and provides diagnostic information.
"""

import sys
import os
import subprocess
import importlib.util
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('debug_test_run.log')
    ]
)
logger = logging.getLogger("test_runner")

def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = ['pytest', 'pyvis']
    missing_packages = []
    
    for package in required_packages:
        if importlib.util.find_spec(package) is None:
            missing_packages.append(package)
    
    if missing_packages:
        logger.error(f"Missing dependencies: {', '.join(missing_packages)}")
        install = input(f"Would you like to install missing dependencies? (y/n): ")
        if install.lower() == 'y':
            try:
                for package in missing_packages:
                    logger.info(f"Installing {package}...")
                    subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                logger.info("All dependencies installed successfully.")
            except Exception as e:
                logger.error(f"Failed to install dependencies: {str(e)}")
                return False
        else:
            return False
    
    return True

def run_tests():
    """Run the debug tests."""
    logger.info("Running debug tests...")
    
    # Find all debug test files
    test_files = []
    
    if os.path.exists("tests/debug_canvas_actions.py"):
        test_files.append("tests/debug_canvas_actions.py")
    
    if os.path.exists("tests/debug_message_flow.py"):
        test_files.append("tests/debug_message_flow.py")
    
    if not test_files:
        logger.error("No debug test files found.")
        return False
    
    # Run each test file
    overall_success = True
    
    for test_file in test_files:
        logger.info(f"Running {test_file}...")
        try:
            # Run the test with pytest
            result = subprocess.run(
                [sys.executable, "-m", "pytest", test_file, "-v"],
                capture_output=True,
                text=True
            )
            
            # Print output
            logger.info(f"Test output for {test_file}:")
            print(result.stdout)
            
            if result.stderr:
                logger.warning(f"Test errors for {test_file}:")
                print(result.stderr)
            
            if result.returncode != 0:
                overall_success = False
                logger.error(f"Tests in {test_file} failed.")
            else:
                logger.info(f"Tests in {test_file} passed.")
                
        except Exception as e:
            overall_success = False
            logger.error(f"Error running {test_file}: {str(e)}")
            logger.error(traceback.format_exc())
    
    return overall_success

def check_system_config():
    """Check the system configuration for potential issues."""
    logger.info("Checking system configuration...")
    
    # Python version
    python_version = sys.version.split()[0]
    logger.info(f"Python version: {python_version}")
    
    # Streamlit version
    try:
        import streamlit
        streamlit_version = streamlit.__version__
        logger.info(f"Streamlit version: {streamlit_version}")
    except ImportError:
        logger.warning("Streamlit is not installed.")
    
    # PyVis version
    try:
        import pyvis
        pyvis_version = pyvis.__version__
        logger.info(f"PyVis version: {pyvis_version}")
    except ImportError:
        logger.warning("PyVis is not installed.")
    
    # Check for source files
    source_files = [
        "src/message_queue.py",
        "src/message_format.py",
        "src/state.py",
        "src/handlers.py",
        "src/utils.py",
        "main.py"
    ]
    
    for file in source_files:
        if os.path.exists(file):
            logger.info(f"Found source file: {file}")
        else:
            logger.warning(f"Missing source file: {file}")
    
    # Check for debug test files
    test_files = [
        "tests/debug_canvas_actions.py",
        "tests/debug_message_flow.py"
    ]
    
    for file in test_files:
        if os.path.exists(file):
            logger.info(f"Found test file: {file}")
        else:
            logger.warning(f"Missing test file: {file}")

def main():
    """Main function."""
    logger.info("Starting debug test runner...")
    
    # Check system configuration
    check_system_config()
    
    # Check dependencies
    if not check_dependencies():
        logger.error("Missing dependencies. Cannot run tests.")
        return 1
    
    # Run tests
    logger.info("Running tests...")
    success = run_tests()
    
    if success:
        logger.info("All tests passed successfully!")
        return 0
    else:
        logger.error("Some tests failed. See log for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 