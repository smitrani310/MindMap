# Test Scripts

This directory contains scripts for running tests and performing test-related tasks in the MindMap application.

## Available Scripts

### `run_position_tests.py`

A comprehensive test runner that executes all position-related tests, both Python and JavaScript.

**Usage:**
```bash
python -m tests.scripts.run_position_tests [options]
```

**Options:**
- `--python-only`: Run only Python tests (skips JavaScript tests)
- `--js-only`: Run only JavaScript tests (skips Python tests)
- `--verbose`: Show detailed output from tests
- `--show-output`: Display stdout/stderr from tests
- `--specific-test TEST_NAME`: Run only a specific test by name

**Examples:**
```bash
# Run all position tests
python -m tests.scripts.run_position_tests

# Run only the Python tests with verbose output
python -m tests.scripts.run_position_tests --python-only --verbose

# Run only the dragend integration test
python -m tests.scripts.run_position_tests --specific-test test_dragend_integration
```

## Test Organization

The `run_position_tests.py` script organizes tests into the following categories:

1. **Unit Tests**
   - Tests for individual components in isolation
   - Fast to run and diagnose issues

2. **Integration Tests**
   - Tests for how components work together
   - Tests both Python and JavaScript interfaces

3. **End-to-End Tests**
   - Tests complete application functionality
   - Verifies overall behavior from a user perspective

## Adding New Tests

When adding new position-related tests:

1. Place the test in the appropriate directory:
   - Python unit tests: `tests/unit/`
   - JavaScript integration tests: `tests/integration/`
   - End-to-end tests: `tests/e2e/`

2. Follow the naming conventions:
   - Python tests: `test_*.py`
   - JavaScript tests: `test_*.js`

3. Update the `run_position_tests.py` script to include your test by adding it to the appropriate test list.

## Troubleshooting

If you encounter issues running the tests:

1. **Missing Dependencies**:
   - For Python tests, ensure pytest is installed: `pip install pytest`
   - For JavaScript tests, ensure Node.js is installed

2. **Path Issues**:
   - Run the script from the project root directory
   - Use the module path: `python -m tests.scripts.run_position_tests`

3. **Test Failures**:
   - Use `--verbose` and `--show-output` to see detailed error information
   - Check the logs for specific error messages
   - Try running individual tests to isolate the issue 