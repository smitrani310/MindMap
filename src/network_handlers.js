// Network interaction handlers for the Enhanced Mind Map
import { messageUtils } from './message_utils';

// Function to send logs to Python
function sendLog(level, message, data = null) {
    try {
        // Direct debugging to canvas for visibility
        if (window.debugToCanvas) {
            window.debugToCanvas(`[${level}] ${message}`);
        }
        
        const logData = {
            level: level,
            message: message,
            data: data,
            timestamp: new Date().toISOString()
        };
        send('log', logData);
    } catch (error) {
        console.error('Failed to send log:', error);
        if (window.debugToCanvas) {
            window.debugToCanvas(`ERROR: Failed to send log: ${error.message}`);
        }
    }
}

// Position update specific function to ensure correct format
function sendNodePositionUpdate(nodeId, x, y) {
    try {
        // Convert coordinates to numbers to ensure proper format
        const xCoord = parseFloat(x);
        const yCoord = parseFloat(y);
        
        // Verify values are valid numbers
        if (isNaN(xCoord) || isNaN(yCoord)) {
            sendLog('error', `Invalid position values: x=${x}, y=${y}`);
            return false;
        }
        
        // Create standardized position message
        const positionMessage = {
            id: nodeId,
            x: xCoord,
            y: yCoord
        };
        
        // Log the position update attempt
        sendLog('info', `Sending position update for node ${nodeId}: (${xCoord}, ${yCoord})`, positionMessage);
        
        // Try multiple methods to send the position update
        let methodSuccess = false;
        
        // Method 1: Send using message utilities
        try {
            const message = messageUtils.createMessage('frontend', 'pos', positionMessage);
            const result = messageUtils.sendMessage(message);
            if (result) {
                methodSuccess = true;
                sendLog('info', `Position update sent via messageUtils for node ${nodeId}`);
            }
        } catch (err) {
            sendLog('error', `Failed to send position via messageUtils: ${err.message}`);
        }
        
        // Method 2: Direct parent communication
        if (window.directParentCommunication) {
            try {
                const result = window.directParentCommunication.sendMessage('pos', positionMessage);
                if (result) {
                    methodSuccess = true;
                    sendLog('info', `Position update sent via directParentCommunication for node ${nodeId}`);
                }
            } catch (err) {
                sendLog('error', `Failed to send position via directParentCommunication: ${err.message}`);
            }
        }
        
        // Method 3: URL parameters (as a fallback)
        if (!methodSuccess) {
            try {
                const params = new URLSearchParams(window.location.search);
                params.set('action', 'pos');
                params.set('payload', JSON.stringify(positionMessage));
                
                // Try to update URL without page reload
                window.history.pushState({}, '', window.location.pathname + '?' + params.toString());
                
                // Force a reload after a brief delay
                setTimeout(() => {
                    window.location.reload();
                }, 100);
                
                methodSuccess = true;
                sendLog('info', `Position update sent via URL parameters for node ${nodeId} (page will reload)`);
            } catch (err) {
                sendLog('error', `Failed to send position via URL parameters: ${err.message}`);
            }
        }
        
        // Report overall success
        if (methodSuccess) {
            sendLog('info', `Successfully sent position update for node ${nodeId}: (${xCoord}, ${yCoord})`);
        } else {
            sendLog('error', `All position update methods failed for node ${nodeId}`);
        }
        
        return methodSuccess;
    } catch (error) {
        sendLog('error', `Failed to send position update: ${error.message}`);
        return false;
    }
}

// Initialize network handlers
export function initializeNetworkHandlers() {
    // Remove any existing event listeners first
    cleanupNetworkHandlers();
    
    // Set up message event listener
    window.addEventListener('message', handleIncomingMessage);
    
    // Initialize message handling
    messageUtils.initializeMessageHandling();
    
    // Add canvas event listeners
    const networkDiv = document.getElementById('mynetwork');
    if (networkDiv) {
        // Add click handler
        networkDiv.addEventListener('click', function(event) {
            const rect = networkDiv.getBoundingClientRect();
            const relX = event.clientX - rect.left;
            const relY = event.clientY - rect.top;
            
            const message = messageUtils.createMessage('frontend', 'canvas_click', {
                x: relX,
                y: relY,
                canvasWidth: rect.width,
                canvasHeight: rect.height,
                timestamp: Date.now()
            });
            
            messageUtils.sendMessage(message);
            sendLog('debug', 'Sent canvas click message', message);
        });
        
        // Add double-click handler
        networkDiv.addEventListener('dblclick', function(event) {
            event.preventDefault();
            
            const rect = networkDiv.getBoundingClientRect();
            const relX = event.clientX - rect.left;
            const relY = event.clientY - rect.top;
            
            const message = messageUtils.createMessage('frontend', 'canvas_dblclick', {
                x: relX,
                y: relY,
                canvasWidth: rect.width,
                canvasHeight: rect.height,
                timestamp: Date.now()
            });
            
            messageUtils.sendMessage(message);
            sendLog('debug', 'Sent canvas double-click message', message);
        });
        
        // Add context menu handler
        networkDiv.addEventListener('contextmenu', function(event) {
            event.preventDefault();
            
            const rect = networkDiv.getBoundingClientRect();
            const relX = event.clientX - rect.left;
            const relY = event.clientY - rect.top;
            
            if (confirm('Delete this bubble?')) {
                const message = messageUtils.createMessage('frontend', 'canvas_contextmenu', {
                    x: relX,
                    y: relY,
                    canvasWidth: rect.width,
                    canvasHeight: rect.height,
                    timestamp: Date.now()
                });
                
                messageUtils.sendMessage(message);
                sendLog('debug', 'Sent canvas context menu message', message);
            }
            
            return false;
        });
        
        // Attach dragEnd handler to network if available
        if (window.visNetwork) {
            attachDragEndHandler(window.visNetwork);
        }
        
        sendLog('info', 'Canvas event handlers initialized');
    } else {
        sendLog('error', 'Network div not found');
    }
}

// Specifically attach dragEnd handler to ensure it's connected
function attachDragEndHandler(network) {
    if (!network) {
        sendLog('error', 'Cannot attach dragEnd handler: network is null');
        return false;
    }
    
    try {
        // Remove any existing dragEnd handler first
        try {
            network.off('dragEnd'); 
        } catch (e) {
            // Ignore errors when no handler exists
            sendLog('debug', 'No existing dragEnd handler to remove');
        }
        
        // Add new handler
        network.on('dragEnd', function(params) {
            sendLog('info', '🔍 DRAG END EVENT TRIGGERED', params);
            
            if (!params || !params.nodes || params.nodes.length === 0) {
                sendLog('warning', 'Drag end event with no nodes!');
                return;
            }
            
            const nodeId = params.nodes[0];
            const positions = network.getPositions([nodeId]);
            
            if (!positions || !positions[nodeId]) {
                sendLog('error', `Failed to get position for node ${nodeId}`);
                return;
            }
            
            const position = positions[nodeId];
            sendLog('info', `🎯 Node ${nodeId} dragged to position:`, position);
            
            // Log more position details
            console.log(`POSITION DEBUG - Node: ${nodeId}, New position: (${position.x}, ${position.y})`);
            sendLog('debug', `Position type check - x: ${typeof position.x}, y: ${typeof position.y}`);
            
            // Verify that position contains valid numbers
            if (isNaN(position.x) || isNaN(position.y)) {
                sendLog('error', `Invalid position values for node ${nodeId}: x=${position.x}, y=${position.y}`);
                return;
            }
            
            // Send position update via multiple methods to ensure delivery
            // Method 1: Use the dedicated function
            const primaryMethod = sendNodePositionUpdate(nodeId, position.x, position.y);
            sendLog('debug', `Primary position update method result: ${primaryMethod}`);
            
            // Method 2: Direct URL update as backup
            try {
                const params = new URLSearchParams(window.location.search);
                params.set('action', 'pos');
                const payload = {
                    id: nodeId,
                    x: position.x,
                    y: position.y
                };
                params.set('payload', JSON.stringify(payload));
                
                // Update URL without navigation (history state only)
                window.history.pushState({}, '', window.location.pathname + '?' + params.toString());
                sendLog('debug', 'Updated URL with position parameters');
            } catch (e) {
                sendLog('error', `Failed to update URL with position: ${e.message}`);
            }
            
            // Method 3: Use directParentCommunication if available
            if (window.directParentCommunication) {
                window.directParentCommunication.sendMessage('pos', {
                    id: nodeId,
                    x: position.x,
                    y: position.y
                });
                sendLog('debug', 'Sent position update via directParentCommunication');
            }
        });
        
        sendLog('info', 'dragEnd handler attached successfully');
        return true;
    } catch (error) {
        sendLog('error', `Failed to attach dragEnd handler: ${error.message}`);
        return false;
    }
}

// Handle incoming messages from the backend
function handleIncomingMessage(event) {
    try {
        const message = event.data;
        if (!message || !message.action) {
            return;
        }
        
        sendLog('debug', 'Received message', message);
        
        // Handle different message types
        switch (message.action) {
            case 'view_node_response':
                // Node was selected
                sendLog('info', 'Node selected', message.payload);
                if (message.status === 'completed') {
                    // Update UI to show selected node
                    const nodeId = message.payload.node_id;
                    if (window.visNetwork) {
                        window.visNetwork.selectNodes([nodeId]);
                    }
                }
                break;
                
            case 'edit_node_response':
                // Node is being edited
                sendLog('info', 'Node being edited', message.payload);
                if (message.status === 'completed') {
                    // Show edit modal
                    const nodeId = message.payload.node_id;
                    if (window.showEditModal) {
                        window.showEditModal(nodeId);
                    }
                }
                break;
                
            case 'delete_node_response':
                // Node was deleted
                sendLog('info', 'Node deleted', message.payload);
                if (message.status === 'completed') {
                    // Remove node from visualization
                    const nodeId = message.payload.node_id;
                    if (window.visNetwork) {
                        window.visNetwork.deleteSelected();
                    }
                }
                break;
                
            default:
                sendLog('warning', 'Unknown message type', message);
        }
    } catch (error) {
        sendLog('error', 'Error handling message', error);
    }
}

// Send node position updates
export function sendNodePosition(nodeId, position) {
    // Use the dedicated position function to ensure correct format
    return sendNodePositionUpdate(nodeId, position.x, position.y);
}

// Send node selection
export function sendNodeSelection(nodeId) {
    const message = messageUtils.createMessage('select_node', {
        id: nodeId
    });
    messageUtils.sendMessage(message);
}

// Send node centering
export function sendNodeCentering(nodeId) {
    const message = messageUtils.createMessage('center_node', {
        id: nodeId
    });
    messageUtils.sendMessage(message);
}

// Send node editing
export function sendNodeEditing(nodeId) {
    const message = messageUtils.createMessage('edit_modal', {
        id: nodeId
    });
    messageUtils.sendMessage(message);
}

// Send node deletion
export function sendNodeDeletion(nodeId) {
    const message = messageUtils.createMessage('delete', {
        id: nodeId
    });
    messageUtils.sendMessage(message);
}

// Send node reparenting
export function sendNodeReparenting(childId, parentId) {
    const message = messageUtils.createMessage('reparent', {
        id: childId,
        parent: parentId
    });
    messageUtils.sendMessage(message);
}

// Send new node creation
export function sendNewNode(label, parentId = null) {
    const message = messageUtils.createMessage('new_node', {
        label: label,
        parent: parentId
    });
    messageUtils.sendMessage(message);
}

// Send undo action
export function sendUndo() {
    const message = messageUtils.createMessage('undo', {});
    messageUtils.sendMessage(message);
}

// Send redo action
export function sendRedo() {
    const message = messageUtils.createMessage('redo', {});
    messageUtils.sendMessage(message);
}

// Clean up network handlers
export function cleanupNetworkHandlers() {
    window.removeEventListener('message', handleIncomingMessage);
    
    const networkDiv = document.getElementById('mynetwork');
    if (networkDiv) {
        networkDiv.removeEventListener('click', null);
        networkDiv.removeEventListener('dblclick', null);
        networkDiv.removeEventListener('contextmenu', null);
    }
    
    // Remove dragEnd handler if network exists
    if (window.visNetwork) {
        try {
            window.visNetwork.off('dragEnd');
        } catch (e) {
            // Ignore errors
        }
    }
}

// Wait for the network to be available
function waitForNetwork() {
    if (window.debugToCanvas) {
        window.debugToCanvas('waitForNetwork called');
    }
    
    sendLog('info', 'Waiting for network...');
    let attempts = 0;
    const maxAttempts = 50; // 5 seconds maximum wait time
    
    const checkInterval = setInterval(() => {
        attempts++;
        sendLog('debug', `Network check attempt ${attempts}/${maxAttempts}`);
        
        // First check if the network is available via window.visNetwork
        if (window.visNetwork) {
            sendLog('info', 'Network found via window.visNetwork');
            if (window.debugToCanvas) {
                window.debugToCanvas(`SUCCESS: Network found via window.visNetwork on attempt ${attempts}`);
            }
            clearInterval(checkInterval);
            initializeNetworkHandlers();
            // Explicitly attach dragEnd handler
            attachDragEndHandler(window.visNetwork);
            return;
        }
        
        const networkDiv = document.getElementById('mynetwork');
        sendLog('debug', 'Network div found:', !!networkDiv);
        
        if (networkDiv) {
            const canvasElements = networkDiv.querySelectorAll('canvas');
            sendLog('debug', 'Canvas elements found:', canvasElements.length);
            
            if (canvasElements.length > 0) {
                for (let i = 0; i < canvasElements.length; i++) {
                    if (canvasElements[i].network) {
                        sendLog('info', 'Network found in canvas element, initializing handlers...');
                        if (window.debugToCanvas) {
                            window.debugToCanvas(`SUCCESS: Network found in canvas on attempt ${attempts}`);
                        }
                        window.visNetwork = canvasElements[i].network;
                        clearInterval(checkInterval);
                        initializeNetworkHandlers();
                        // Explicitly attach dragEnd handler
                        attachDragEndHandler(window.visNetwork);
                        return;
                    }
                }
            }
        }
        
        if (attempts >= maxAttempts) {
            sendLog('error', 'Network initialization timeout - network not found after ' + maxAttempts + ' attempts');
            if (window.debugToCanvas) {
                window.debugToCanvas(`ERROR: Network not found after ${maxAttempts} attempts`);
                
                // Final attempt: directly scan the global namespace
                for (let key in window) {
                    try {
                        const obj = window[key];
                        if (obj && 
                            typeof obj === 'object' && 
                            obj.body && 
                            obj.canvas && 
                            typeof obj.on === 'function') {
                            window.debugToCanvas(`FOUND NETWORK-LIKE OBJECT AT window.${key}, using it`);
                            window.visNetwork = obj;
                            initializeNetworkHandlers();
                            // Explicitly attach dragEnd handler
                            attachDragEndHandler(window.visNetwork);
                            return;
                        }
                    } catch (e) {
                        // Skip if accessing property throws error
                    }
                }
                
                window.debugToCanvas("CRITICAL ERROR: No valid network found anywhere");
            }
            clearInterval(checkInterval);
        }
    }, 100);
}

// Try to directly access the network to ensure proper binding
function forceNetworkAccess() {
    if (window.debugToCanvas) {
        window.debugToCanvas("Attempting direct network access...");
    }
    
    // First try window.visNetwork (set by our modified script)
    if (window.visNetwork) {
        if (window.debugToCanvas) {
            window.debugToCanvas("SUCCESS: Network found at window.visNetwork");
        }
        initializeNetworkHandlers();
        // Explicitly attach dragEnd handler
        attachDragEndHandler(window.visNetwork);
        return true;
    }
    
    // Try to get the network instance from vis global object if available
    if (typeof vis !== 'undefined' && vis.network && vis.network.instances) {
        if (window.debugToCanvas) {
            window.debugToCanvas(`Found ${Object.keys(vis.network.instances).length} network instances via vis.network.instances`);
        }
        
        // Get the first network instance
        const networkKeys = Object.keys(vis.network.instances);
        if (networkKeys.length > 0) {
            const networkInstance = vis.network.instances[networkKeys[0]];
            if (networkInstance) {
                if (window.debugToCanvas) {
                    window.debugToCanvas("SUCCESS: Network instance found via vis.network.instances");
                }
                window.visNetwork = networkInstance;
                initializeNetworkHandlers();
                // Explicitly attach dragEnd handler
                attachDragEndHandler(window.visNetwork);
                return true;
            }
        }
    }
    
    // If we couldn't get the network from the global object, try the traditional approach
    waitForNetwork();
    return false;
}

// Start trying to access the network
document.addEventListener('DOMContentLoaded', function() {
    if (window.debugToCanvas) {
        window.debugToCanvas("DOM loaded, initializing network access...");
    }
    
    // Try direct access first
    if (!forceNetworkAccess()) {
        // Fallback to polling approach
        setTimeout(waitForNetwork, 100);
    }
    
    // Set up a recurring check to ensure dragEnd handler stays attached
    setInterval(function() {
        if (window.visNetwork) {
            attachDragEndHandler(window.visNetwork);
        }
    }, 5000); // Check every 5 seconds
});

// Add this at the end to guarantee it runs even if DOMContentLoaded already fired
if (document.readyState === 'complete' || document.readyState === 'interactive') {
    if (window.debugToCanvas) {
        window.debugToCanvas("Document already loaded, initializing immediately");
    }
    forceNetworkAccess();
} else {
    if (window.debugToCanvas) {
        window.debugToCanvas("Waiting for document to load...");
    }
}

// Function to apply stored positions to nodes in the network
function applyStoredPositions(network, positions) {
    if (!network || !positions) {
        sendLog('warning', 'Cannot apply positions: network or positions object missing');
        return false;
    }
    
    try {
        // Count applied positions for logging
        let appliedCount = 0;
        let skippedCount = 0;
        
        // Get all node IDs
        const nodeIds = network.body.data.nodes.getIds();
        sendLog('info', `Applying positions to ${nodeIds.length} nodes`);
        
        // Apply positions to each node
        nodeIds.forEach(nodeId => {
            if (positions[nodeId]) {
                // Apply position if valid
                const x = parseFloat(positions[nodeId].x);
                const y = parseFloat(positions[nodeId].y);
                
                if (!isNaN(x) && !isNaN(y)) {
                    // Create a proper position object
                    const posObj = { x: x, y: y };
                    
                    // Apply position to the node and ensure it remains fixed
                    try {
                        // Get current network positions for comparison
                        const currentPos = network.getPositions([nodeId])[nodeId];
                        if (currentPos && 
                            (Math.abs(currentPos.x - x) < 0.001 && Math.abs(currentPos.y - y) < 0.001)) {
                            // Position is already correct, skip
                            skippedCount++;
                            return;
                        }
                        
                        // Set the node position
                        network.moveNode(nodeId, x, y);
                        
                        // Also ensure it's stored in the data structure
                        const nodeData = network.body.data.nodes.get(nodeId);
                        if (nodeData) {
                            nodeData.x = x;
                            nodeData.y = y;
                            network.body.data.nodes.update(nodeData);
                        }
                        
                        // Log the position application
                        sendLog('info', `Applied position (${x}, ${y}) to node ${nodeId}`);
                        appliedCount++;
                    } catch (e) {
                        sendLog('error', `Failed to apply position to node ${nodeId}: ${e.message}`);
                    }
                } else {
                    sendLog('warning', `Invalid position values for node ${nodeId}: (${positions[nodeId].x}, ${positions[nodeId].y})`);
                    skippedCount++;
                }
            } else {
                skippedCount++;
            }
        });
        
        sendLog('info', `Position application complete: ${appliedCount} applied, ${skippedCount} skipped`);
        return true;
    } catch (error) {
        sendLog('error', `Error applying positions: ${error.message}`);
        return false;
    }
} 