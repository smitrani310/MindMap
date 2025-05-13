/**
 * Test script for dragEnd event handling and position updates
 * To run: node test_dragend_event.js
 */

// Mock browser environment for testing
const window = {
    visNetwork: {
        on: function(event, handler) {
            console.log(`Registered handler for ${event} event`);
            // Store the handler for testing
            window.registeredHandlers = window.registeredHandlers || {};
            window.registeredHandlers[event] = handler;
            return true;
        },
        getPositions: function(nodeIds) {
            console.log(`Getting positions for nodes: ${nodeIds}`);
            // Return mock positions for testing
            const result = {};
            nodeIds.forEach(id => {
                result[id] = {
                    x: 100 + parseInt(id) * 10,
                    y: 200 + parseInt(id) * 15
                };
            });
            return result;
        }
    },
    directParentCommunication: {
        sendMessage: function(action, payload) {
            console.log(`Sending message: ${action}`, JSON.stringify(payload, null, 2));
            // Store sent messages for testing
            window.sentMessages = window.sentMessages || [];
            window.sentMessages.push({
                action: action,
                payload: payload
            });
            return true;
        }
    },
    // Store for testing
    registeredHandlers: {},
    sentMessages: []
};

// Simple assert function
function assert(condition, message) {
    if (!condition) {
        console.error(`ASSERTION FAILED: ${message}`);
        throw new Error(`Assertion failed: ${message}`);
    } else {
        console.log(`ASSERTION PASSED: ${message}`);
    }
}

// Implementation of setupDragEndHandler function (from the application code)
function setupDragEndHandler() {
    if (window.visNetwork) {
        console.log('Adding dragEnd event listener to visNetwork');
        
        // Add the dragEnd event to track node position changes
        window.visNetwork.on('dragEnd', function(params) {
            if (params.nodes && params.nodes.length > 0) {
                const nodeId = params.nodes[0];
                const nodePosition = window.visNetwork.getPositions([nodeId])[nodeId];
                
                console.log('Node dragged:', nodeId, 'to position:', nodePosition);
                
                // Send position update to backend
                simpleSendMessage('pos', {
                    id: nodeId,
                    x: nodePosition.x,
                    y: nodePosition.y
                });
            }
        });
        
        console.log('dragEnd event handler attached successfully');
        return true;
    } else {
        console.error('visNetwork not available when trying to attach dragEnd handler');
        return false;
    }
}

// Implementation of simpleSendMessage function (from the application code)
function simpleSendMessage(action, payload) {
    console.log(`Sending message: ${action}`, JSON.stringify(payload, null, 2));
    window.directParentCommunication.sendMessage(action, payload);
    return true;
}

// --- TEST SUITE ---

console.log('=== RUNNING DRAGEND EVENT TESTS ===');

// Test 1: Initialize handler
console.log('\n--- Test 1: Initialize dragEnd handler ---');
const initResult = setupDragEndHandler();
assert(initResult === true, 'Handler should initialize successfully');
assert(window.registeredHandlers['dragEnd'] !== undefined, 'Should register dragEnd event handler');
console.log('Test 1 completed successfully');

// Test 2: Simulate dragEnd event and verify message
console.log('\n--- Test 2: Simulate dragEnd event ---');
const nodeId = '1';
const dragEvent = {
    nodes: [nodeId]
};

// Call the registered handler
const dragEndHandler = window.registeredHandlers['dragEnd'];
assert(typeof dragEndHandler === 'function', 'dragEnd handler should be a function');
dragEndHandler(dragEvent);

// Verify message was sent
assert(window.sentMessages.length > 0, 'A message should be sent');
const lastMessage = window.sentMessages[window.sentMessages.length - 1];
assert(lastMessage.action === 'pos', 'Message action should be "pos"');
assert(lastMessage.payload.id === nodeId, `Node ID should be ${nodeId}`);
assert(typeof lastMessage.payload.x === 'number', 'X coordinate should be a number');
assert(typeof lastMessage.payload.y === 'number', 'Y coordinate should be a number');
console.log('Test 2 completed successfully');

// Test 3: Test multiple node drags
console.log('\n--- Test 3: Multiple node drags ---');
// Clear sent messages
window.sentMessages = [];

// Drag multiple nodes
const nodeIds = ['2', '3', '4'];
nodeIds.forEach(nid => {
    dragEndHandler({ nodes: [nid] });
});

// Verify all messages were sent
assert(window.sentMessages.length === nodeIds.length, `Should send ${nodeIds.length} messages`);
for (let i = 0; i < nodeIds.length; i++) {
    assert(window.sentMessages[i].payload.id === nodeIds[i], 
        `Message ${i+1} should have nodeId ${nodeIds[i]}`);
}
console.log('Test 3 completed successfully');

// Print test results
console.log('\n=== TEST RESULTS ===');
console.log(`Total event handlers registered: ${Object.keys(window.registeredHandlers).length}`);
console.log(`Total messages sent: ${window.sentMessages.length}`);
console.log('Most recent message:');
console.log(JSON.stringify(window.sentMessages[window.sentMessages.length - 1], null, 2));

console.log('\n=== ALL TESTS PASSED ===');

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