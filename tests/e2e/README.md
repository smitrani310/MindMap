# End-to-End Tests

This directory contains end-to-end tests that verify the complete functionality of the MindMap application, particularly focusing on node position persistence.

## Available Tests

### `verify_position_fix.py`

A comprehensive test script that verifies the fixes implemented for node position persistence.

**Usage:**
```bash
python -m tests.e2e.verify_position_fix
```

**What it tests:**
1. Creates test nodes with specific initial positions
2. Verifies that the positions are correctly saved
3. Updates the positions to new values
4. Verifies that the updated positions are persisted
5. Tests various position format conversions

This script is the primary verification tool for ensuring that the position persistence fixes are working correctly. It simulates the complete flow of creating, positioning, and updating nodes.

### `test_position_format.js`

JavaScript test for frontend position format handling.

**Usage:**
```bash
node tests/e2e/test_position_format.js
```

**What it tests:**
1. Validates conversion between different position formats
2. Tests position application to the network visualization
3. Ensures consistency between UI positions and stored values

## Running the Tests

### Automated Testing

To run all end-to-end tests:

```bash
python -m tests.scripts.run_position_tests --e2e-only
```

### Manual Verification

You can also use the `verify_position_fix.py` script for manual verification:

1. Run the script and observe the output:
   ```bash
   python -m tests.e2e.verify_position_fix
   ```

2. Check for the success message:
   ```
   ✓✓✓ All position tests passed! The fix is working correctly. ✓✓✓
   ```

3. If there are failures, review the detailed error messages

## Test Implementation Details

The `verify_position_fix.py` script:

1. **Creates a test environment**:
   - Loads the current MindMap data file
   - Sets up a controlled test scenario
   - Creates test nodes with specific positions

2. **Performs verification steps**:
   - Tests node creation with positions
   - Tests position reading/writing
   - Tests position format conversion
   - Tests position updates

3. **Verifies persistence**:
   - Updates node positions
   - Saves the data
   - Reloads and verifies positions are maintained

4. **Cleans up after testing**:
   - Removes test nodes
   - Restores original data state

## JavaScript Console Testing

For manual verification in the browser:

1. Open the MindMap application in your browser
2. Open the browser developer console (F12)
3. Use the `positionDebug` API to test position persistence:

```javascript
// Start tracking a node
window.positionDebug.trackNode(1);  // Replace 1 with any node ID

// Drag the node to a new position

// Check the position tracking
window.positionDebug.getDebugInfo(1);

// Run a position persistence test
window.positionDebug.testPositionPersistence(1);

// Reload the page, then verify persistence
window.positionDebug.verifyPersistence();
``` 