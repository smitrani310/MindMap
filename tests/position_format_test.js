/**
 * Position Format Test
 * 
 * This test verifies that the format of position data sent by vis.js
 * is compatible with what the backend expects.
 */

// Test assertion utilities
function assert(condition, message) {
    if (!condition) {
        console.error(`❌ ASSERTION FAILED: ${message}`);
        throw new Error(message);
    } else {
        console.log(`✅ PASSED: ${message}`);
    }
}

// Test log
function log(message) {
    console.log(`ℹ️ ${message}`);
}

// Create mock objects
const mockVisNetwork = {
    // Mock for getPositions method
    getPositions: function(nodeIds) {
        // This reproduces how the actual vis.js library formats position data
        const result = {};
        nodeIds.forEach(id => {
            result[id] = {
                x: 100 + parseInt(id),
                y: 200 + parseInt(id)
            };
        });
        return result;
    },
    
    // Method to simulate how vis.js provides positions during events
    simulateDragEndEvent: function(nodeId) {
        const params = {
            nodes: [nodeId]
        };
        
        // This is how vis.js provides position data
        const positions = this.getPositions([nodeId]);
        
        return {
            params: params,
            positions: positions
        };
    }
};

// Mock various sendMessage implementations
const messageFormats = {
    // Format 1: Direct object with id, x, y (standard)
    format1: function(nodeId, position) {
        return {
            id: nodeId,
            x: position.x,
            y: position.y
        };
    },
    
    // Format 2: Nested object with node ID as key (alternative)
    format2: function(nodeId, position) {
        const result = {};
        result[nodeId] = {
            x: position.x,
            y: position.y
        };
        return result;
    },
    
    // Format 3: Array of positions
    format3: function(nodeId, position) {
        return {
            id: nodeId,
            pos: [position.x, position.y]
        };
    },
    
    // Format 4: Mixed types - string ID with numeric coordinates
    format4: function(nodeId, position) {
        return {
            id: String(nodeId),
            x: Number(position.x),
            y: Number(position.y)
        };
    }
};

// Simulate backend position handling
function mockBackendPositionHandler(payload) {
    log(`Backend received: ${JSON.stringify(payload)}`);
    
    // Extract position data based on potential formats
    let nodeId, x, y;
    
    // Try format 1: {id, x, y}
    if (payload.id !== undefined && payload.x !== undefined && payload.y !== undefined) {
        nodeId = payload.id;
        x = payload.x;
        y = payload.y;
        log(`Format 1 detected: id=${nodeId}, x=${x}, y=${y}`);
    } 
    // Try format 2: {nodeId: {x, y}}
    else {
        const keys = Object.keys(payload).filter(k => k !== 'id' && k !== 'x' && k !== 'y');
        if (keys.length > 0) {
            nodeId = keys[0];
            const posData = payload[nodeId];
            if (posData && typeof posData === 'object') {
                x = posData.x;
                y = posData.y;
                log(`Format 2 detected: id=${nodeId}, x=${x}, y=${y}`);
            }
        }
    }
    
    // Try format 3: {id, pos: [x, y]}
    if (nodeId === undefined && payload.id !== undefined && Array.isArray(payload.pos)) {
        nodeId = payload.id;
        x = payload.pos[0];
        y = payload.pos[1];
        log(`Format 3 detected: id=${nodeId}, x=${x}, y=${y}`);
    }
    
    // Validate extracted data
    if (nodeId === undefined || x === undefined || y === undefined) {
        log(`❌ Failed to extract position data from: ${JSON.stringify(payload)}`);
        return {
            success: false,
            error: 'Failed to extract position data'
        };
    }
    
    // Convert types if needed (backend may expect specific types)
    nodeId = typeof nodeId === 'string' ? parseInt(nodeId, 10) : nodeId;
    x = typeof x === 'string' ? parseFloat(x) : x;
    y = typeof y === 'string' ? parseFloat(y) : y;
    
    log(`✅ Extracted data: id=${nodeId}, x=${x}, y=${y}`);
    
    // Simulate updating a node
    return {
        success: true,
        nodeId: nodeId,
        position: { x, y }
    };
}

// Test the flow from vis.js to backend
function testPositionFormat(format) {
    const nodeId = '1';
    
    // Step 1: Get position data as vis.js would provide it
    log('\n--- Step 1: Simulate vis.js dragEnd event ---');
    const eventData = mockVisNetwork.simulateDragEndEvent(nodeId);
    log(`Vis.js dragEnd event: ${JSON.stringify(eventData)}`);
    
    // Step 2: Extract position from the event data
    log('\n--- Step 2: Extract position from event ---');
    const position = eventData.positions[nodeId];
    log(`Extracted position: ${JSON.stringify(position)}`);
    assert(position.x !== undefined, 'Position should have x coordinate');
    assert(position.y !== undefined, 'Position should have y coordinate');
    
    // Step 3: Format the message in the given format
    log(`\n--- Step 3: Format message using ${format} ---`);
    const formatFunc = messageFormats[format];
    const message = formatFunc(nodeId, position);
    log(`Formatted message: ${JSON.stringify(message)}`);
    
    // Step 4: Send to mock backend handler
    log('\n--- Step 4: Process message in backend ---');
    const result = mockBackendPositionHandler(message);
    log(`Backend result: ${JSON.stringify(result)}`);
    
    // Verify the result
    assert(result.success, `Backend should successfully process ${format}`);
    assert(result.nodeId == nodeId, `Node ID should match: ${result.nodeId} != ${nodeId}`);
    assert(result.position.x === position.x, `X coordinate should match: ${result.position.x} != ${position.x}`);
    assert(result.position.y === position.y, `Y coordinate should match: ${result.position.y} != ${position.y}`);
    
    return result;
}

// Run tests for all formats
function runAllTests() {
    log('===== POSITION FORMAT TESTS =====');
    
    // Test all formats
    const formats = Object.keys(messageFormats);
    const results = {};
    
    formats.forEach(format => {
        log(`\n\n===== Testing ${format.toUpperCase()} =====`);
        try {
            const result = testPositionFormat(format);
            results[format] = {
                success: true,
                details: result
            };
            log(`✅ ${format.toUpperCase()} TEST PASSED`);
        } catch (error) {
            results[format] = {
                success: false,
                error: error.message
            };
            log(`❌ ${format.toUpperCase()} TEST FAILED: ${error.message}`);
        }
    });
    
    // Report results
    log('\n\n===== TEST RESULTS SUMMARY =====');
    formats.forEach(format => {
        const status = results[format].success ? '✅ PASSED' : '❌ FAILED';
        log(`${format}: ${status}`);
    });
    
    // Check if all formats worked
    const allPassed = Object.values(results).every(r => r.success);
    if (allPassed) {
        log('\n✅✅✅ ALL FORMATS WORK CORRECTLY');
    } else {
        log('\n⚠️ SOME FORMATS FAILED - CHECK WHICH FORMAT IS USED IN PRODUCTION');
    }
    
    return results;
}

// Run all the tests
const testResults = runAllTests();

// Recommend a format based on test results
log('\n===== RECOMMENDATION =====');
if (testResults.format1.success) {
    log('✅ RECOMMENDED FORMAT: Standard format {id, x, y}');
    log('This is the most direct and clear format, which should work best in most scenarios.');
} else if (testResults.format4.success) {
    log('✅ FALLBACK RECOMMENDATION: String ID with numeric coordinates {id: "1", x: 100, y: 200}');
    log('This format ensures type consistency which can help prevent type-related bugs.');
} else if (testResults.format2.success) {
    log('⚠️ FALLBACK RECOMMENDATION: Alternative format {nodeId: {x, y}}');
    log('This format works but is less direct. Use only if needed for compatibility.');
} else {
    log('❌ NO RECOMMENDED FORMAT - All test formats had issues!');
    log('You may need to modify the backend to handle a specific format or debug further.');
}

// Actual format verification - what is used in real code
log('\n===== ACTUAL CODE FORMAT VERIFICATION =====');
// This is a copy of the actual code from network_handlers.js
const actualFormat = function(nodeId, position) {
    return {
        id: nodeId,
        x: position.x,
        y: position.y
    };
};

// Test with the actual format
const actualFormatResult = mockBackendPositionHandler(
    actualFormat('1', {x: 123, y: 456})
);

if (actualFormatResult.success) {
    log('✅ ACTUAL CODE FORMAT WORKS CORRECTLY');
    log(`Format: ${JSON.stringify(actualFormat('1', {x: 123, y: 456}))}`);
} else {
    log('❌ ACTUAL CODE FORMAT FAILS!');
    log('The format used in the actual code does not work with the backend!');
}

// Export results for potential use in automated tests
if (typeof module !== 'undefined') {
    module.exports = {
        testResults,
        actualFormatResult
    };
} 