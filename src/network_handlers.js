// Network interaction handlers for the Enhanced Mind Map

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

function initializeNetworkHandlers(network, searchQuery) {
    if (window.debugToCanvas) {
        window.debugToCanvas('initializeNetworkHandlers called with network: ' + (network ? 'Yes' : 'No'));
    }
    
    sendLog('info', 'Initializing network handlers...', {
        networkExists: !!network,
        networkId: network?.id,
        searchQuery: searchQuery
    });
    
    // Create a hidden form for message passing
    const formDiv = document.createElement('div');
    formDiv.style.display = 'none';
    formDiv.innerHTML = `
        <form id="message-form" action="" method="get">
            <input type="hidden" id="message-type" name="action" value="">
            <input type="hidden" id="message-payload" name="payload" value="">
            <button type="submit" id="message-submit">Submit</button>
        </form>
    `;
    document.body.appendChild(formDiv);
    sendLog('debug', 'Message form created and appended to body');

    // Message passing via form submission
    function send(action, payload) {
        if (window.debugToCanvas) {
            window.debugToCanvas(`Sending message: ${action}`);
        }
        
        sendLog('debug', 'Attempting to send message:', {action, payload});
        try {
            const form = document.getElementById('message-form');
            const typeInput = document.getElementById('message-type');
            const payloadInput = document.getElementById('message-payload');
            
            sendLog('debug', 'Form elements found:', {
                form: !!form,
                typeInput: !!typeInput,
                payloadInput: !!payloadInput
            });
            
            if (!form || !typeInput || !payloadInput) {
                throw new Error('Required form elements not found');
            }
            
            typeInput.value = action;
            payloadInput.value = JSON.stringify(payload);
            sendLog('debug', 'Form values set:', {
                action: typeInput.value,
                payload: payloadInput.value
            });
            
            form.submit();
            sendLog('debug', 'Form submitted successfully');
        } catch (error) {
            sendLog('error', 'Failed to send message:', error);
        }
    }

    // Initialize physics
    network.once('afterDrawing', () => {
        sendLog('info', 'Network drawing complete, stabilizing...');
        network.stabilize(100);
    });

    // Handle node dragging
    network.on('dragEnd', (params) => {
        sendLog('debug', 'Drag end event:', {
            nodes: params.nodes,
            event: params.event,
            pointer: params.pointer
        });
        if (params.nodes.length === 1) {
            const pos = {};
            const id = params.nodes[0];
            const position = network.getPositions([id])[id];
            pos[id] = position;
            send('pos', pos);
        }
    });

    // Click for node details
    network.on('click', (params) => {
        if (window.debugToCanvas) {
            window.debugToCanvas(`Click event received on ${params.nodes.length} nodes`);
        }
        
        sendLog('debug', 'Click event received:', {
            nodes: params.nodes,
            event: params.event,
            pointer: params.pointer,
            networkState: {
                selectedNodes: network.getSelectedNodes(),
                isStabilized: network.isStabilized()
            }
        });
        
        if (params.nodes.length === 1) {
            const id = params.nodes[0];
            sendLog('info', 'Node clicked, sending messages for node:', id);
            // Directly show on canvas for debugging
            if (window.debugToCanvas) {
                window.debugToCanvas(`CLICK: Node ${id} selected, sending messages`);
            }
            send('select_node', { id });
            send('center_node', { id });
        } else {
            sendLog('debug', 'Click event received but no node was clicked');
        }
    });

    // Double-click for edit
    network.on('doubleClick', (params) => {
        sendLog('debug', 'Double click event:', {
            nodes: params.nodes,
            event: params.event,
            pointer: params.pointer
        });
        if (params.nodes.length === 1) {
            const id = params.nodes[0];
            send('edit_modal', { id });
        }
    });

    // Context menu for delete
    network.on('contextmenu', (params) => {
        sendLog('debug', 'Context menu event:', {
            nodes: params.nodes,
            event: params.event,
            pointer: params.pointer
        });
        params.event.preventDefault();
        if (params.nodes.length === 1) {
            const id = params.nodes[0];
            if (confirm('Delete this bubble?')) {
                send('delete', { id: id });
            }
        }
        return false;
    });

    // Log all attached event listeners
    sendLog('debug', 'Network event listeners:', {
        listeners: network._eventListeners ? Object.keys(network._eventListeners) : [],
        networkState: {
            isStabilized: network.isStabilized(),
            selectedNodes: network.getSelectedNodes(),
            nodeCount: network.body.data.nodes.length
        }
    });

    // Search highlight
    if (searchQuery) {
        sendLog('info', 'Applying search highlight for:', searchQuery);
        const nodes = network.body.data.nodes;
        nodes.forEach((n) => {
            if (n.label.toLowerCase().includes(searchQuery.toLowerCase())) {
                n.color = { background: 'yellow', border: 'orange' };
            }
        });
    }

    sendLog('info', 'Network handlers initialized successfully');
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
            initializeNetworkHandlers(window.visNetwork, window.searchQuery);
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
                        initializeNetworkHandlers(canvasElements[i].network, window.searchQuery);
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
                            initializeNetworkHandlers(obj, window.searchQuery);
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
        initializeNetworkHandlers(window.visNetwork, window.searchQuery);
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
                initializeNetworkHandlers(networkInstance, window.searchQuery);
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