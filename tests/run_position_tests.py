#!/usr/bin/env python3
"""
Script to run all node position update tests.
This tests the full flow from dragEnd event to position persistence.
"""

import unittest
import sys
import os
import subprocess
import argparse
import logging
import warnings

def configure_logging(verbose=False):
    """Configure logging to silence Streamlit warnings"""
    # Set up logging
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format='%(levelname)s: %(message)s')
    
    # Filter out Streamlit related warnings
    class StreamlitWarningFilter(logging.Filter):
        def filter(self, record):
            return not ('streamlit' in record.getMessage().lower() or 
                         'scriptruncontext' in record.getMessage().lower())
    
    # Apply the filter to the root logger
    logging.getLogger().addFilter(StreamlitWarningFilter())
    
    # Also filter warnings
    warnings.filterwarnings("ignore", category=UserWarning, module="streamlit")
    warnings.filterwarnings("ignore", message=".*ScriptRunContext.*")
    
    return logging.getLogger(__name__)

def run_python_tests(verbose=False):
    """Run all the Python unit and integration tests."""
    # Configure test loader
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add position tests
    position_tests = loader.discover(
        os.path.dirname(__file__),
        pattern="test_*position*.py"
    )
    suite.addTests(position_tests)
    
    # Add integration tests
    integration_tests = loader.discover(
        os.path.dirname(__file__),
        pattern="test_*integration*.py"
    )
    suite.addTests(integration_tests)
    
    # Configure environment for tests
    saved_env = os.environ.copy()
    os.environ["PYTHONPATH"] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Disable Streamlit warnings
    os.environ["STREAMLIT_DISABLE_WARNING"] = "true"
    
    try:
        # Run the tests
        runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
        results = runner.run(suite)
        
        if results.errors or results.failures:
            print("\n=== Diagnostic Information ===")
            print(f"Errors: {len(results.errors)}")
            print(f"Failures: {len(results.failures)}")
            
            if results.errors:
                print("\nFirst error:", results.errors[0][1])
            
            if results.failures:
                print("\nFirst failure:", results.failures[0][1])
        
        return results.wasSuccessful()
    finally:
        # Restore environment
        os.environ.clear()
        os.environ.update(saved_env)

def run_js_tests(verbose=False):
    """Run JavaScript tests for dragEnd event handling."""
    js_test_path = os.path.join(os.path.dirname(__file__), "test_dragend_event.js")
    
    # Check if the file exists
    if not os.path.exists(js_test_path):
        print(f"ERROR: JavaScript test file not found: {js_test_path}")
        return False
    
    try:
        # Try running with Node.js directly (no Jest needed anymore)
        result = subprocess.run(
            ["node", js_test_path],
            check=False,  # Don't throw on non-zero exit
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Print results
        print(result.stdout.decode())
        if result.stderr:
            print("STDERR:", result.stderr.decode())
        
        # Check for assertion failures in output
        has_errors = "ASSERTION FAILED" in result.stdout.decode() or "Error" in result.stderr.decode()
        return result.returncode == 0 and not has_errors
    except Exception as e:
        print(f"ERROR running JavaScript tests: {str(e)}")
        return False

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run node position update tests")
    parser.add_argument("-v", "--verbose", action="store_true", help="Run tests with verbose output")
    parser.add_argument("--python-only", action="store_true", help="Run only Python tests")
    parser.add_argument("--js-only", action="store_true", help="Run only JavaScript tests")
    parser.add_argument("--disable-streamlit-warnings", action="store_true", 
                     help="Suppress Streamlit warning messages")
    args = parser.parse_args()
    
    # Configure logging
    logger = configure_logging(args.verbose)
    
    # Run the tests
    python_success = True
    js_success = True
    
    # Run Python tests
    if not args.js_only:
        print("\n==== Running Python Tests ====\n")
        python_success = run_python_tests(args.verbose)
        
    # Run JavaScript tests
    if not args.python_only:
        print("\n==== Running JavaScript Tests ====\n")
        js_success = run_js_tests(args.verbose)
    
    # Report results
    print("\n==== Test Results Summary ====\n")
    if not args.js_only:
        print(f"Python Tests: {'PASSED' if python_success else 'FAILED'}")
    if not args.python_only:
        print(f"JavaScript Tests: {'PASSED' if js_success else 'FAILED'}")
    
    # Print additional help for common issues
    if not python_success or not js_success:
        print("\n==== Troubleshooting Guide ====")
        
        if not python_success:
            print("\nPython test issues:")
            print("1. Check that src.message_format.Message class has create_error and create_success methods")
            print("2. Verify that mock_handle_position implementation matches actual code")
            print("3. Try running individual tests with more verbosity:")
            print("   python -m unittest -v tests/test_node_position.py")
        
        if not js_success:
            print("\nJavaScript test issues:")
            print("1. Ensure Node.js is installed and in your PATH")
            print("2. Check for JavaScript syntax errors in the test file")
            print("3. Try running the JS test directly:")
            print("   node tests/test_dragend_event.js")
    
    # Set exit code based on test results
    if not (python_success and js_success):
        sys.exit(1)
    
    print("\nAll tests passed!")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 