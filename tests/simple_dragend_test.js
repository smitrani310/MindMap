/**
 * Simple test for vis.js dragEnd handling without Jest
 */

// Simple assertions
function assert(condition, message) {
    if (!condition) {
        console.error(`ASSERTION FAILED: ${message}`);
        throw new Error(message);
    } else {
        console.log(`PASSED: ${message}`);
    }
}

// Mock window object for testing
const window = {
    // Mock vis.js network
    visNetwork: {
        // Mock events
        eventHandlers: {},
        // Mock on method to register event handlers
        on: function(eventName, handler) {
            this.eventHandlers[eventName] = handler;
            console.log(`Registered handler for ${eventName}`);
        },
        // Mock getPositions method to return node positions
        getPositions: function(nodeIds) {
            const result = {};
            nodeIds.forEach(id => {
                result[id] = { x: 100 + parseInt(id), y: 200 + parseInt(id) };
            });
            return result;
        }
    },
    
    // Track sent messages
    sentMessages: [],
    
    // Mock communication
    directParentCommunication: {
        sendMessage: function(action, payload) {
            console.log(`Sending message: ${action}, payload:`, payload);
            window.sentMessages.push({ action, payload });
            return true;
        }
    }
};

// Implement the simpleSendMessage function as used in the app
function simpleSendMessage(action, payload) {
    console.log(`simpleSendMessage called with action: ${action}`);
    window.directParentCommunication.sendMessage(action, payload);
    return true;
}

// Code under test - dragEnd handler setup
function setupDragEndHandler() {
    console.log('Setting up dragEnd handler');
    
    if (window.visNetwork) {
        window.visNetwork.on('dragEnd', function(params) {
            if (params.nodes && params.nodes.length > 0) {
                const nodeId = params.nodes[0];
                const nodePosition = window.visNetwork.getPositions([nodeId])[nodeId];
                
                console.log(`Node ${nodeId} dragged to position:`, nodePosition);
                
                // Send position update
                simpleSendMessage('pos', {
                    id: nodeId,
                    x: nodePosition.x,
                    y: nodePosition.y
                });
            }
        });
        
        return true;
    } else {
        console.error('visNetwork not available');
        return false;
    }
}

// ---- Tests ----
console.log("===== STARTING TESTS =====");

// Test 1: Setup handler
console.log("\n--- Test 1: Setup dragEnd handler ---");
const setupResult = setupDragEndHandler();
assert(setupResult === true, "dragEnd handler should be set up successfully");
assert(typeof window.visNetwork.eventHandlers.dragEnd === 'function', 
    "dragEnd handler should be registered");

// Test 2: Trigger dragEnd event
console.log("\n--- Test 2: Trigger dragEnd event ---");
const dragEndEvent = {
    nodes: ['1']
};
window.visNetwork.eventHandlers.dragEnd(dragEndEvent);
assert(window.sentMessages.length === 1, "One message should be sent");
assert(window.sentMessages[0].action === 'pos', "Message action should be 'pos'");
assert(window.sentMessages[0].payload.id === '1', "Node ID should be preserved");
assert(window.sentMessages[0].payload.x === 101, "X position should be correct");
assert(window.sentMessages[0].payload.y === 201, "Y position should be correct");

// Test 3: Multiple nodes
console.log("\n--- Test 3: Handle multiple drag events ---");
window.sentMessages = []; // Clear previous messages
const nodeIds = ['2', '3', '4'];

nodeIds.forEach(id => {
    window.visNetwork.eventHandlers.dragEnd({ nodes: [id] });
});

assert(window.sentMessages.length === 3, "Three messages should be sent");
nodeIds.forEach((id, index) => {
    assert(window.sentMessages[index].payload.id === id, 
        `Message ${index+1} should have correct node ID: ${id}`);
});

// Test 4: No nodes in params
console.log("\n--- Test 4: Handle event with no nodes ---");
window.sentMessages = []; // Clear previous messages
window.visNetwork.eventHandlers.dragEnd({ nodes: [] });
assert(window.sentMessages.length === 0, "No messages should be sent for empty nodes array");

// Test 5: Null params
console.log("\n--- Test 5: Handle null params ---");
window.sentMessages = []; // Clear previous messages
window.visNetwork.eventHandlers.dragEnd({});
assert(window.sentMessages.length === 0, "No messages should be sent for null params");

console.log("\n===== ALL TESTS PASSED =====");
console.log(`Total messages sent: ${window.sentMessages.length}`); 