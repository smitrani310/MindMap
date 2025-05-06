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

// Initialize network handlers
export function initializeNetworkHandlers() {
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
            
            const message = messageUtils.createMessage('network_canvas', 'canvas_click', {
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
            
            const message = messageUtils.createMessage('network_canvas', 'canvas_dblclick', {
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
                const message = messageUtils.createMessage('network_canvas', 'canvas_contextmenu', {
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
        
        sendLog('info', 'Canvas event handlers initialized');
    } else {
        sendLog('error', 'Network div not found');
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
                break;
                
            case 'edit_node_response':
                // Node is being edited
                sendLog('info', 'Node being edited', message.payload);
                break;
                
            case 'delete_node_response':
                // Node was deleted
                sendLog('info', 'Node deleted', message.payload);
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
    const message = messageUtils.createMessage('pos', {
        [nodeId]: position
    });
    messageUtils.sendMessage(message);
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
                        clearInterval(checkInterval);
                        initializeNetworkHandlers();
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
                            initializeNetworkHandlers();
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