# Test Utilities

This directory contains utility scripts for debugging and analyzing the MindMap application, particularly focusing on position-related functionality.

## Available Utilities

### `check_position_export.py`

This utility analyzes node position data in exported JSON files to verify that positions are correctly saved.

**Usage:**
```bash
python -m tests.utils.check_position_export
```

**Features:**
- Finds and analyzes the mindmap_data.json file
- Counts nodes with default (0,0) positions vs. non-default positions
- Identifies nodes missing position data
- Creates a test export and compares with the original data

### `debug_position_flow.py`

A comprehensive debugging tool that traces the flow of position data through the application.

**Usage:**
```bash
python -m tests.utils.debug_position_flow [--node-id NODE_ID]
```

**Features:**
- Adds verbose logging for position updates
- Tracks position changes from frontend to backend
- Shows the complete call stack for position updates
- Identifies potential issues in the position update flow

### `inspect_data_file.py`

Examines the MindMap data file for integrity and potential issues.

**Usage:**
```bash
python -m tests.utils.inspect_data_file [--fix]
```

**Features:**
- Validates all nodes for required fields
- Checks position data for consistency
- Identifies nodes with invalid or missing position data
- Can fix common position data issues (with `--fix` flag)

## Common Usage Patterns

### Debugging Position Issues

If nodes are not maintaining their positions:

1. Verify the data file integrity:
   ```bash
   python -m tests.utils.inspect_data_file
   ```

2. Check if positions are being properly exported:
   ```bash
   python -m tests.utils.check_position_export
   ```

3. Trace the position update flow:
   ```bash
   python -m tests.utils.debug_position_flow --node-id 1
   ```

### Fixing Position Data

If the data file contains invalid position data:

```bash
python -m tests.utils.inspect_data_file --fix
```

This will:
- Convert string positions to float values
- Initialize missing position data
- Validate all position formats

## Integration with Tests

These utilities can be used alongside the formal tests to diagnose issues:

1. Run the position verification test:
   ```bash
   python -m tests.e2e.verify_position_fix
   ```

2. If the test fails, use the utilities to diagnose:
   ```bash
   python -m tests.utils.debug_position_flow
   ```

3. Check the data file for issues:
   ```bash
   python -m tests.utils.inspect_data_file
   ``` 