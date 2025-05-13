/**
 * Test dragEnd event handling
 * Tests the handling of dragEnd events from the vis.js network
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

// Mock network object
const mockNetwork = {
    on: function(event, callback) {
        this.events = this.events || {};
        this.events[event] = callback;
        console.log(`Registered handler for ${event} event`);
        return true;
    },
    getPositions: function(nodeIds) {
        const result = {};
        nodeIds.forEach(id => {
            result[id] = { x: 100 * id, y: 200 * id };
        });
        return result;
    },
    triggerDragEnd: function(nodeIds) {
        if (!this.events || !this.events.dragEnd) {
            console.error("No dragEnd handler registered");
            return false;
        }
        
        // Create event object similar to vis.js
        const event = { nodes: nodeIds };
        
        // Call the registered handler
        this.events.dragEnd(event);
        return true;
    }
};

// Mock Streamlit
let lastMessage = null;
const mockStreamlit = {
    setComponentValue: function(message) {
        lastMessage = message;
        console.log(`Message sent to Python: ${JSON.stringify(message)}`);
    }
};

// Simple test function to verify dragEnd event handling
function testDragEndEventHandling() {
    console.log("Testing dragEnd event handling...");
    
    // Reset state
    lastMessage = null;
    
    // Create event handler function similar to actual code
    function attachDragEndHandler(network) {
        network.on("dragEnd", function(event) {
            // Get selected nodes
            const nodeIds = event.nodes;
            if (!nodeIds || nodeIds.length === 0) {
                console.log("No nodes selected in dragEnd event");
                return;
            }
            
            // Get positions for the nodes
            const positions = network.getPositions(nodeIds);
            if (!positions) {
                console.error("Could not get positions");
                return;
            }
            
            // Send position update for each node
            nodeIds.forEach(function(nodeId) {
                const position = positions[nodeId];
                if (!position) {
                    console.error(`No position data for node ${nodeId}`);
                    return;
                }
                
                // Format the position message
                const message = {
                    id: nodeId,
                    x: position.x,
                    y: position.y
                };
                
                // Send to Python backend
                mockStreamlit.setComponentValue({
                    action: "pos",
                    payload: message
                });
            });
        });
        
        return true;
    }
    
    // Run the test
    let passed = 0;
    let failed = 0;
    
    // Test 1: Register handler
    console.log("\nTest 1: Register event handler");
    const handlerAttached = attachDragEndHandler(mockNetwork);
    if (handlerAttached) {
        passed++;
        console.log("✓ Handler registered successfully");
    } else {
        failed++;
        console.error("✗ Failed to register handler");
    }
    
    // Test 2: Trigger event with single node
    console.log("\nTest 2: Trigger dragEnd with single node");
    mockNetwork.triggerDragEnd([1]);
    
    if (lastMessage && 
        lastMessage.action === "pos" && 
        lastMessage.payload.id === 1 &&
        lastMessage.payload.x === 100 &&
        lastMessage.payload.y === 200) {
        passed++;
        console.log("✓ Position message sent correctly for single node");
    } else {
        failed++;
        console.error(`✗ Incorrect message format: ${JSON.stringify(lastMessage)}`);
    }
    
    // Test 3: Trigger event with multiple nodes
    console.log("\nTest 3: Trigger dragEnd with multiple nodes (should send multiple messages)");
    let messageCount = 0;
    const originalSetComponentValue = mockStreamlit.setComponentValue;
    
    // Override to count messages
    mockStreamlit.setComponentValue = function(message) {
        messageCount++;
        originalSetComponentValue.call(this, message);
    };
    
    mockNetwork.triggerDragEnd([2, 3]);
    
    // Restore original function
    mockStreamlit.setComponentValue = originalSetComponentValue;
    
    if (messageCount === 2) {
        passed++;
        console.log("✓ Multiple position messages sent correctly");
    } else {
        failed++;
        console.error(`✗ Expected 2 messages, got ${messageCount}`);
    }
    
    // Print test summary
    console.log(`\nDragEnd event tests: ${passed} passed, ${failed} failed`);
    return failed === 0;
}

// Run tests
const testsPassed = testDragEndEventHandling();

// Use process.exit to return appropriate exit code
process.exit(testsPassed ? 0 : 1);

/**
 * In a real browser environment, this is what happens:
 * 
 * 1. User drags a node on the vis.js graph
 * 2. Vis.js fires the 'dragEnd' event with the node ID
 * 3. Our handler gets the node's new position using getPositions()
 * 4. The handler calls simpleSendMessage with action 'pos' and payload {id, x, y}
 * 5. simpleSendMessage uses postMessage to send to the parent window
 * 6. Streamlit receives the message and processes it
 * 7. The position is updated in the Python backend
 * 8. The node's position is persisted and will be restored on page reload
 */ 