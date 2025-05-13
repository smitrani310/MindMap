# MindMap Test Suite Documentation

This directory contains test files for the MindMap application, organized by test type and functionality.

## Folder Structure

The test suite is organized into the following directory structure:

```
tests/
├── unit/             # Unit tests for individual components
├── integration/      # Tests for interactions between components
├── e2e/              # End-to-end tests
├── utils/            # Testing utilities and inspection tools
├── scripts/          # Scripts for running tests and automation
└── README.md         # This documentation file
```

## Test Types

### Unit Tests (`unit/`)

Unit tests focus on testing individual components in isolation, with mocked dependencies.

- **test_node_position.py**: Tests the position update handler's behavior with different message formats
  - Validates proper position format handling
  - Tests error handling for various scenarios
  - Ensures proper position type conversion

- **test_simple_position.py**: Simple direct tests for the position validation and update functions
  - Tests basic node position updates using the utility functions
  - Avoids complex mocking that might hide issues
  - Validates both standard and alternative position formats

### Integration Tests (`integration/`)

Integration tests verify that multiple components work together correctly.

- **test_dragend_integration.py**: Tests the complete flow from dragEnd event to position update
  - Simulates the complete pipeline from frontend event to backend update
  - Tests both direct and message queue-based position update paths
  - Verifies position persistence after multiple events

- **test_dragend_event.js**: JavaScript tests for the frontend dragEnd event handler
  - Tests event listener registration and event capturing
  - Validates message creation and sending to the backend
  - Tests multiple messaging methods for redundancy

- **test_simple_dragend.js**: Simplified JavaScript tests that can run without Jest
  - Tests core event handling functionality
  - Verifies proper message formatting for position updates
  - Can be run directly with Node.js

### End-to-End Tests (`e2e/`)

E2E tests validate the application's behavior as a whole from a user's perspective.

- **verify_position_fix.py**: Comprehensive test to verify position persistence
  - Creates nodes with specific positions
  - Verifies positions are saved correctly
  - Updates positions and confirms changes are persisted
  - Tests position format conversion between frontend and backend

- **test_position_format.js**: Tests frontend position format handling
  - Validates conversion between different position formats
  - Tests position application to the network visualization
  - Ensures consistency between UI positions and stored values

### Utilities (`utils/`)

Utilities help with debugging and inspection during testing.

- **check_position_export.py**: Analyzes exported JSON to verify positions
  - Scans node data for missing or invalid position values
  - Reports statistics on position distribution
  - Compares positions between different exports

- **debug_position_flow.py**: Traces position updates through the application
  - Adds detailed logging for position-related operations
  - Provides visualizations of position changes
  - Helps identify where position data might be lost

- **inspect_data_file.py**: Examines the data file for integrity
  - Validates node structure and required fields
  - Reports on position data quality
  - Can fix common issues with position data

### Scripts (`scripts/`)

Scripts automate testing and other common operations.

- **run_position_tests.py**: Script to run all position-related tests
  - Provides options to run Python or JavaScript tests separately
  - Includes verbose output options for debugging
  - Reports detailed test results

## Running Tests

You can run tests individually or by category:

### Running Unit Tests

```bash
python -m unittest tests/unit/test_node_position.py
python -m unittest tests/unit/test_simple_position.py
```

### Running Integration Tests

```bash
python -m unittest tests/integration/test_dragend_integration.py
node tests/integration/test_simple_dragend.js
```

### Running E2E Tests

```bash
python -m tests.e2e.verify_position_fix
node tests/e2e/test_position_format.js
```

### Running All Position Tests

```bash
python tests/scripts/run_position_tests.py
```

Options:
- `--python-only`: Run only Python tests
- `--js-only`: Run only JavaScript tests
- `--verbose`: Show detailed output

## Position Fix Verification

The position persistence issue has been addressed through multiple fixes:

1. **Enhanced Node Validation**
   - Proper type conversion for position values
   - Detailed logging for position updates
   - New dedicated utility functions for consistent updates

2. **Improved Event Handling**
   - Multiple methods to ensure dragEnd events are captured
   - Redundant message passing between frontend and backend
   - Periodic checks to verify position consistency

3. **Data Format Standardization**
   - Consistent position format throughout the application
   - Validation before saving to prevent data corruption
   - Type conversion to ensure compatibility

You can verify these fixes are working using:

```bash
python -m tests.e2e.verify_position_fix
```

This script will create test nodes, verify their positions, update them, and confirm the changes persist. 