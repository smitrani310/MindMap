/**
 * Test position formatting in the frontend
 * This file tests the conversion between different position formats
 */

// Mock console output for testing
const originalConsole = console;
let testOutput = [];

// Override console methods for testing
console = {
    log: (message) => { 
        testOutput.push(`LOG: ${message}`); 
        originalConsole.log(message);
    },
    error: (message) => { 
        testOutput.push(`ERROR: ${message}`); 
        originalConsole.error(message);
    },
    warn: (message) => { 
        testOutput.push(`WARN: ${message}`); 
        originalConsole.warn(message);
    }
};

// Test position conversion utilities
function testPositionFormatting() {
    console.log("Testing position formatting...");
    
    // Test position objects
    const positions = {
        direct: { id: 1, x: 100, y: 200 },
        alternative: { "1": { x: 100, y: 200 } },
        stringValues: { id: "1", x: "100", y: "200" },
        invalid: { id: 1, x: "not a number", y: 200 }
    };
    
    // Test conversion functions
    function validatePositionFormat(position) {
        // Check if it's the alternative format (nodeId: {x, y})
        if (typeof position === 'object' && position !== null) {
            // Check for direct format (id, x, y)
            if ('id' in position && 'x' in position && 'y' in position) {
                try {
                    return {
                        id: parseInt(position.id, 10),
                        x: parseFloat(position.x),
                        y: parseFloat(position.y)
                    };
                } catch (e) {
                    console.error(`Invalid position format: ${e.message}`);
                    return null;
                }
            }
            
            // Look for the first property that could be a node ID
            for (const key in position) {
                if (position[key] && typeof position[key] === 'object' && 
                    'x' in position[key] && 'y' in position[key]) {
                    try {
                        return {
                            id: parseInt(key, 10),
                            x: parseFloat(position[key].x),
                            y: parseFloat(position[key].y)
                        };
                    } catch (e) {
                        console.error(`Invalid alternative position format: ${e.message}`);
                        return null;
                    }
                }
            }
        }
        
        console.error("Unrecognized position format");
        return null;
    }
    
    // Test and report results
    let passed = 0;
    let failed = 0;
    
    // Test direct format
    const directResult = validatePositionFormat(positions.direct);
    if (directResult && directResult.id === 1 && directResult.x === 100 && directResult.y === 200) {
        passed++;
        console.log("Direct format test: PASSED");
    } else {
        failed++;
        console.error("Direct format test: FAILED");
    }
    
    // Test alternative format
    const altResult = validatePositionFormat(positions.alternative);
    if (altResult && altResult.id === 1 && altResult.x === 100 && altResult.y === 200) {
        passed++;
        console.log("Alternative format test: PASSED");
    } else {
        failed++;
        console.error("Alternative format test: FAILED");
    }
    
    // Test string values
    const stringResult = validatePositionFormat(positions.stringValues);
    if (stringResult && stringResult.id === 1 && stringResult.x === 100 && stringResult.y === 200) {
        passed++;
        console.log("String values test: PASSED");
    } else {
        failed++;
        console.error("String values test: FAILED");
    }
    
    // Test invalid format
    const invalidResult = validatePositionFormat(positions.invalid);
    if (invalidResult === null) {
        passed++;
        console.log("Invalid format test: PASSED");
    } else {
        failed++;
        console.error("Invalid format test: FAILED");
    }
    
    // Print test summary
    console.log(`\nPosition format tests: ${passed} passed, ${failed} failed`);
    return failed === 0;
}

// Run tests
const testsPassed = testPositionFormatting();

// Use process.exit to return appropriate exit code
process.exit(testsPassed ? 0 : 1); 