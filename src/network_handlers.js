// Network interaction handlers for the Enhanced Mind Map

function initializeNetworkHandlers(network, searchQuery) {
    console.log('Initializing network handlers...');
    
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

    // Message passing via form submission
    function send(action, payload) {
        try {
            console.log('Sending message:', action, payload);
            document.getElementById('message-type').value = action;
            document.getElementById('message-payload').value = JSON.stringify(payload);
            document.getElementById('message-form').submit();
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
        console.log('Drag end event:', params);
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
        console.log('Click event:', params);
        if (params.nodes.length === 1) {
            const id = params.nodes[0];
            send('select_node', { id });
            // Also center the node
            send('center_node', { id });
        }
    });

    // Double-click for edit
    network.on('doubleClick', (params) => {
        console.log('Double click event:', params);
        if (params.nodes.length === 1) {
            const id = params.nodes[0];
            send('edit_modal', { id });
        }
    });

    // Context menu for delete
    network.on('contextmenu', (params) => {
        console.log('Context menu event:', params);
        params.event.preventDefault();
        if (params.nodes.length === 1) {
            const id = params.nodes[0];
            if (confirm('Delete this bubble?')) {
                send('delete', { id: id });
            }
        }
        return false;
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Only process if not in a text field
        if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
            // Ctrl+Space to center selected node
            if (e.ctrlKey && e.code === 'Space') {
                const selectedNodes = network.getSelectedNodes();
                if (selectedNodes.length === 1) {
                    send('center_node', { id: selectedNodes[0] });
                }
            }
        }
    });

    // Add button event listeners for center and delete
    document.querySelectorAll('.center-button').forEach(button => {
        button.addEventListener('click', (e) => {
            const id = e.target.getAttribute('data-id');
            if (id) {
                send('center_node', { id: parseInt(id) });
            }
        });
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
    const checkInterval = setInterval(() => {
        const networkDiv = document.getElementById('mynetwork');
        if (networkDiv) {
            const canvasElements = networkDiv.querySelectorAll('canvas');
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
    }, 100);
}

// Start waiting for the network
waitForNetwork(); 