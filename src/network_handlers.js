// Network interaction handlers for the Enhanced Mind Map

function initializeNetworkHandlers(network, searchQuery) {
    console.log('Initializing network handlers...', {
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
    console.log('Message form created and appended to body');

    // Message passing via form submission
    function send(action, payload) {
        console.log('Attempting to send message:', {action, payload});
        try {
            const form = document.getElementById('message-form');
            const typeInput = document.getElementById('message-type');
            const payloadInput = document.getElementById('message-payload');
            
            console.log('Form elements found:', {
                form: !!form,
                typeInput: !!typeInput,
                payloadInput: !!payloadInput
            });
            
            if (!form || !typeInput || !payloadInput) {
                throw new Error('Required form elements not found');
            }
            
            typeInput.value = action;
            payloadInput.value = JSON.stringify(payload);
            console.log('Form values set:', {
                action: typeInput.value,
                payload: payloadInput.value
            });
            
            form.submit();
            console.log('Form submitted successfully');
        } catch (error) {
            console.error("Failed to send message:", error);
        }
    }

    // Initialize physics
    network.once('afterDrawing', () => {
        console.log('Network drawing complete, stabilizing...');
        network.stabilize(100);
    });

    // Handle node dragging
    network.on('dragEnd', (params) => {
        console.log('Drag end event:', {
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
        console.log('Click event received:', {
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
            console.log('Node clicked, sending messages for node:', id);
            send('select_node', { id });
            send('center_node', { id });
        } else {
            console.log('Click event received but no node was clicked');
        }
    });

    // Double-click for edit
    network.on('doubleClick', (params) => {
        console.log('Double click event:', {
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
        console.log('Context menu event:', {
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
    console.log('Network event listeners:', {
        listeners: network._eventListeners ? Object.keys(network._eventListeners) : [],
        networkState: {
            isStabilized: network.isStabilized(),
            selectedNodes: network.getSelectedNodes(),
            nodeCount: network.body.data.nodes.length
        }
    });

    // Search highlight
    if (searchQuery) {
        console.log('Applying search highlight for:', searchQuery);
        const nodes = network.body.data.nodes;
        nodes.forEach((n) => {
            if (n.label.toLowerCase().includes(searchQuery.toLowerCase())) {
                n.color = { background: 'yellow', border: 'orange' };
            }
        });
    }

    console.log('Network handlers initialized successfully');
}

// Wait for the network to be available
function waitForNetwork() {
    console.log('Waiting for network...');
    let attempts = 0;
    const maxAttempts = 50; // 5 seconds maximum wait time
    
    const checkInterval = setInterval(() => {
        attempts++;
        console.log(`Network check attempt ${attempts}/${maxAttempts}`);
        
        const networkDiv = document.getElementById('mynetwork');
        console.log('Network div found:', !!networkDiv);
        
        if (networkDiv) {
            const canvasElements = networkDiv.querySelectorAll('canvas');
            console.log('Canvas elements found:', canvasElements.length);
            
            if (canvasElements.length > 0) {
                for (let i = 0; i < canvasElements.length; i++) {
                    if (canvasElements[i].network) {
                        console.log('Network found, initializing handlers...');
                        clearInterval(checkInterval);
                        initializeNetworkHandlers(canvasElements[i].network, window.searchQuery);
                        break;
                    }
                }
            }
        }
        
        if (attempts >= maxAttempts) {
            console.error('Network initialization timeout - network not found after', maxAttempts, 'attempts');
            clearInterval(checkInterval);
        }
    }, 100);
}

// Start waiting for the network
waitForNetwork(); 