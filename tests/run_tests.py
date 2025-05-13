#!/usr/bin/env python3
"""
Master test runner for the MindMap application.
This script discovers and runs all tests in the test directory structure.
"""

import argparse
import os
import subprocess
import sys
import unittest
from pathlib import Path

def discover_tests(directory, pattern="test_*.py", is_js=False):
    """Discover tests in the specified directory."""
    if not os.path.exists(directory):
        print(f"Warning: Directory {directory} does not exist, skipping.")
        return []
    
    tests = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.startswith("test_"):
                # Check if we're looking for Python files or JavaScript files
                if (is_js and file.endswith(".js")) or (not is_js and file.endswith(".py")):
                    test_path = os.path.join(root, file)
                    tests.append(test_path)
    
    return tests

def run_python_tests(tests, verbose=False, show_output=False):
    """Run Python tests using unittest."""
    print(f"\n{'='*30}\nRunning {len(tests)} Python tests\n{'='*30}")
    
    if not tests:
        print("No Python tests found.")
        return True
    
    success = True
    
    for test in tests:
        rel_path = os.path.relpath(test)
        print(f"\nRunning: {rel_path}")
        
        # Convert file path to module path
        module_path = rel_path.replace(os.path.sep, ".").replace(".py", "")
        
        try:
            command = [sys.executable, "-m", "unittest", module_path]
            if verbose:
                command.append("-v")
            
            if show_output:
                result = subprocess.run(command)
                if result.returncode != 0:
                    success = False
            else:
                result = subprocess.run(command, 
                                        stdout=subprocess.PIPE, 
                                        stderr=subprocess.PIPE)
                if result.returncode != 0:
                    success = False
                    print(f"Test failed: {rel_path}")
                    if verbose:
                        print("\nStdout:")
                        print(result.stdout.decode())
                        print("\nStderr:")
                        print(result.stderr.decode())
                else:
                    print(f"Test passed: {rel_path}")
        except Exception as e:
            success = False
            print(f"Error running test {rel_path}: {str(e)}")
    
    return success

def is_nodejs_available():
    """Check if Node.js is available on the system."""
    try:
        subprocess.run(["node", "--version"], 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE,
                      check=False)
        return True
    except Exception:
        return False

def run_js_tests(tests, verbose=False, show_output=False):
    """Run JavaScript tests using Node.js."""
    print(f"\n{'='*30}\nRunning {len(tests)} JavaScript tests\n{'='*30}")
    
    if not tests:
        print("No JavaScript tests found.")
        return True
    
    # Check if Node.js is installed
    if not is_nodejs_available():
        print("Node.js is not installed or not in PATH. Skipping JavaScript tests.")
        print("To run JavaScript tests, install Node.js from https://nodejs.org/")
        return True  # Return success to not fail the test run
    
    success = True
    
    for test in tests:
        # Use absolute path to avoid issues with file not found
        abs_path = os.path.abspath(test)
        rel_path = os.path.relpath(test)
        print(f"\nRunning: {rel_path}")
        
        try:
            command = ["node", abs_path]
            
            if show_output:
                result = subprocess.run(command)
                if result.returncode != 0:
                    success = False
            else:
                result = subprocess.run(command, 
                                        stdout=subprocess.PIPE, 
                                        stderr=subprocess.PIPE)
                if result.returncode != 0:
                    success = False
                    print(f"Test failed: {rel_path}")
                    if verbose:
                        print("\nStdout:")
                        print(result.stdout.decode())
                        print("\nStderr:")
                        print(result.stderr.decode())
                else:
                    print(f"Test passed: {rel_path}")
        except Exception as e:
            success = False
            print(f"Error running test {rel_path}: {str(e)}")
    
    return success

def main():
    """Main function to parse arguments and run tests."""
    parser = argparse.ArgumentParser(description="Run MindMap tests")
    parser.add_argument("--verbose", action="store_true", help="Show verbose output")
    parser.add_argument("--show-output", action="store_true", help="Show test output")
    parser.add_argument("--python-only", action="store_true", help="Run only Python tests")
    parser.add_argument("--js-only", action="store_true", help="Run only JavaScript tests")
    parser.add_argument("--unit-only", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration-only", action="store_true", help="Run only integration tests")
    parser.add_argument("--e2e-only", action="store_true", help="Run only end-to-end tests")
    args = parser.parse_args()
    
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Test directories
    test_directories = {
        "unit": os.path.join(script_dir, "unit"),
        "integration": os.path.join(script_dir, "integration"),
        "e2e": os.path.join(script_dir, "e2e")
    }
    
    # Filter directories based on arguments
    selected_dirs = {}
    if args.unit_only:
        selected_dirs["unit"] = test_directories["unit"]
    elif args.integration_only:
        selected_dirs["integration"] = test_directories["integration"]
    elif args.e2e_only:
        selected_dirs["e2e"] = test_directories["e2e"]
    else:
        selected_dirs = test_directories
    
    all_py_tests = []
    all_js_tests = []
    
    # Discover tests in each selected directory
    for dir_name, dir_path in selected_dirs.items():
        print(f"Discovering tests in {dir_name} directory...")
        
        py_tests = discover_tests(dir_path, "test_*.py", is_js=False)
        all_py_tests.extend(py_tests)
        
        js_tests = discover_tests(dir_path, "test_*.js", is_js=True)
        all_js_tests.extend(js_tests)
        
        print(f"Found {len(py_tests)} Python tests and {len(js_tests)} JavaScript tests")
    
    # Run tests based on arguments
    success = True
    
    if not args.js_only:
        py_success = run_python_tests(all_py_tests, args.verbose, args.show_output)
        success = success and py_success
    
    if not args.python_only:
        js_success = run_js_tests(all_js_tests, args.verbose, args.show_output)
        success = success and js_success
    
    # Print summary
    print(f"\n{'='*50}")
    if success:
        print("✅ All tests passed successfully!")
    else:
        print("❌ Some tests failed. See output above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main() 