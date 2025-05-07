import os
import sys
import pytest
import argparse
from typing import List, Optional

def run_tests(test_paths: List[str], verbose: bool = False, capture_output: bool = True) -> int:
    """Run pytest with the specified test paths."""
    args = [
        '-v' if verbose else '-q',
        '--capture=no' if not capture_output else '--capture=fd',
        '--tb=short',  # Shorter traceback format
        '--color=yes'  # Force color output
    ]
    args.extend(test_paths)
    return pytest.main(args)

def get_test_paths(category: Optional[str] = None) -> List[str]:
    """Get test paths based on category."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    if category == 'unit':
        return [os.path.join(base_dir, 'unit')]
    elif category == 'integration':
        return [os.path.join(base_dir, 'integration')]
    elif category == 'e2e':
        return [os.path.join(base_dir, 'e2e')]
    else:
        # Run all Python test files
        return [
            os.path.join(base_dir, 'unit'),
            os.path.join(base_dir, 'integration'),
            os.path.join(base_dir, 'e2e')
        ]

def main():
    parser = argparse.ArgumentParser(description='Run Mind Map tests by category.')
    parser.add_argument(
        'category',
        nargs='?',
        choices=['unit', 'integration', 'e2e', 'all'],
        default='all',
        help='Test category to run (default: all)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument(
        '--show-output',
        action='store_true',
        help='Show test output (stdout/stderr)'
    )
    
    args = parser.parse_args()
    
    # Print test run information
    print(f"\n{'='*60}")
    print(f"Running {'all' if args.category == 'all' else args.category} tests...")
    print(f"{'='*60}\n")
    
    # Get test paths based on category
    category = None if args.category == 'all' else args.category
    test_paths = get_test_paths(category)
    
    # Run tests
    result = run_tests(
        test_paths,
        verbose=args.verbose,
        capture_output=not args.show_output
    )
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"Test run completed with exit code: {result}")
    print(f"{'='*60}\n")
    
    sys.exit(result)

if __name__ == '__main__':
    main() 