import os
import shutil

def create_directory(path):
    """Create directory if it doesn't exist."""
    if not os.path.exists(path):
        os.makedirs(path)

def move_file(source, destination):
    """Move file from source to destination."""
    if os.path.exists(source):
        shutil.move(source, destination)
        print(f"Moved {source} to {destination}")

def main():
    # Create new directory structure
    directories = [
        'tests/unit',
        'tests/integration',
        'tests/e2e'
    ]
    
    for directory in directories:
        create_directory(directory)
    
    # Move files to their new locations
    moves = [
        # Unit tests
        ('tests/run_message_format_test.py', 'tests/unit/test_message_format.py'),
        ('tests/simplest_queue_test.py', 'tests/unit/test_message_queue.py'),
        ('tests/test_utils.py', 'tests/unit/test_utils.py'),
        
        # Integration tests
        ('tests/run_message_flow_test.py', 'tests/integration/test_message_flow.py'),
        ('tests/run_simple_tests.py', 'tests/integration/test_basic_operations.py'),
        ('tests/run_simplest_tests.py', 'tests/integration/test_core_functionality.py'),
        
        # E2E tests
        ('tests/test_graph_ui.html', 'tests/e2e/test_ui_rendering.html'),
        ('tests/test_message_utils.html', 'tests/e2e/test_message_utils.html')
    ]
    
    for source, destination in moves:
        move_file(source, destination)
    
    # Create __init__.py files in each directory
    for directory in directories:
        init_file = os.path.join(directory, '__init__.py')
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write('"""Test package initialization."""\n')

if __name__ == '__main__':
    main() 