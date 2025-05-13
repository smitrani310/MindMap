#!/usr/bin/env python3
"""
Reorganize test files into the appropriate directories.
This script will create a better structure for our test suite.
"""

import os
import shutil
from pathlib import Path

# Create directory structure if it doesn't exist
def ensure_dirs(dirs):
    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)
        # Create __init__.py if it doesn't exist
        init_file = os.path.join(dir_path, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write("# Test directory initialization\n")

# Move files to their new locations
def move_files(file_mappings):
    for src, dest in file_mappings:
        if os.path.exists(src):
            # Create destination directory if it doesn't exist
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            # Copy the file to the new location
            shutil.copy2(src, dest)
            print(f"Copied {src} -> {dest}")
        else:
            print(f"Source file not found: {src}")

# Main execution
if __name__ == "__main__":
    # Get the base directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define directory structure
    directories = [
        os.path.join(base_dir, "unit"),
        os.path.join(base_dir, "integration"),
        os.path.join(base_dir, "e2e"),
        os.path.join(base_dir, "utils"),
        os.path.join(base_dir, "scripts"),
    ]
    
    # Create directories
    ensure_dirs(directories)
    
    # Define file mappings (source -> destination)
    file_mappings = [
        # Unit tests
        (os.path.join(base_dir, "test_node_position.py"), os.path.join(base_dir, "unit", "test_node_position.py")),
        (os.path.join(base_dir, "simple_position_test.py"), os.path.join(base_dir, "unit", "test_simple_position.py")),
        
        # Integration tests
        (os.path.join(base_dir, "test_dragend_integration.py"), os.path.join(base_dir, "integration", "test_dragend_integration.py")),
        (os.path.join(base_dir, "test_dragend_event.js"), os.path.join(base_dir, "integration", "test_dragend_event.js")),
        (os.path.join(base_dir, "simple_dragend_test.js"), os.path.join(base_dir, "integration", "test_simple_dragend.js")),
        
        # E2E tests
        (os.path.join(base_dir, "verify_position_fix.py"), os.path.join(base_dir, "e2e", "verify_position_fix.py")),
        (os.path.join(base_dir, "position_format_test.js"), os.path.join(base_dir, "e2e", "test_position_format.js")),
        
        # Utility scripts
        (os.path.join(base_dir, "debug_position_flow.py"), os.path.join(base_dir, "utils", "debug_position_flow.py")),
        (os.path.join(base_dir, "inspect_data_file.py"), os.path.join(base_dir, "utils", "inspect_data_file.py")),
        (os.path.join(base_dir, "check_position_export.py"), os.path.join(base_dir, "utils", "check_position_export.py")),
        
        # Scripts
        (os.path.join(base_dir, "run_position_tests.py"), os.path.join(base_dir, "scripts", "run_position_tests.py")),
    ]
    
    # Move files to their new locations
    move_files(file_mappings)
    
    print("Test reorganization complete. Check the new directory structure.") 