# Mind Map Test Suite

This directory contains the test suite for the Mind Map application, organized into three main categories:

## Test Structure

```
tests/
├── unit/                           # Unit tests
│   ├── test_message_format.py      # Message format validation tests
│   ├── test_message_queue.py       # Queue operations tests
│   ├── test_utils.py              # Utility function tests
│   └── test_handlers.py           # Message handler tests
│
├── integration/                    # Integration tests
│   ├── test_message_flow.py       # Message flow between components
│   ├── test_core_functionality.py # Core feature integration
│   ├── test_canvas_events.py      # Canvas interaction tests
│   ├── test_basic_operations.py   # Basic operation integration
│   └── test_state_sync.py        # State synchronization tests
│
└── e2e/                           # End-to-end tests
    ├── test_node_operations.py    # Complete node operation workflows
    ├── test_error_handling.py     # Error scenario testing
    ├── test_ui_rendering.html     # UI rendering tests
    └── test_message_utils.html    # Message utilities in UI context
```

## Running Tests

Use the `run_tests.py` script to execute tests. The script provides several options for running different categories of tests.

### Basic Usage

1. Run all tests:
   ```bash
   python tests/run_tests.py
   ```

2. Run specific test category:
   ```bash
   python tests/run_tests.py unit        # Run unit tests only
   python tests/run_tests.py integration # Run integration tests only
   python tests/run_tests.py e2e        # Run end-to-end tests only
   ```

### Additional Options

- `-v` or `--verbose`: Enable verbose output
  ```bash
  python tests/run_tests.py unit -v
  ```

- `--show-output`: Show test output (stdout/stderr)
  ```bash
  python tests/run_tests.py integration --show-output
  ```

### Exit Codes

- 0: All tests passed
- 1: Some tests failed
- 2: Test execution was interrupted
- 3: Internal error
- 4: pytest command line usage error
- 5: No tests were collected

## Test Categories

1. **Unit Tests** (`unit/`)
   - Tests for individual components in isolation
   - Fast execution, no external dependencies
   - Focus on specific functionality

2. **Integration Tests** (`integration/`)
   - Tests component interactions
   - Verifies different parts work together
   - May use minimal external dependencies

3. **End-to-End Tests** (`e2e/`)
   - Tests complete workflows
   - UI and system integration tests
   - Closest to real user scenarios 