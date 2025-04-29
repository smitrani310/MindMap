// Network interaction handlers for the Enhanced Mind Map

function initializeNetworkHandlers(network, searchQuery) {
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
            document.getElementById('message-type').value = action;
            document.getElementById('message-payload').value = JSON.stringify(payload);
            document.getElementById('message-form').submit();
        } catch (error) {
            console.error("Failed to send message:", error);
        }
    }

    // Initialize physics
    network.once('afterDrawing', () => {
        network.stabilize(100);
    });

    // Handle node dragging
    network.on('dragEnd', (params) => {
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
        if (params.nodes.length === 1) {
            const id = params.nodes[0];
            send('select_node', { id });
        }
    });

    // Double-click for edit
    network.on('doubleClick', (params) => {
        if (params.nodes.length === 1) {
            const id = params.nodes[0];
            send('edit_modal', { id });
        }
    });

    // Context menu for delete
    network.on('contextmenu', (params) => {
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
        const nodes = network.body.data.nodes;
        nodes.forEach((n) => {
            if (n.label.toLowerCase().includes(searchQuery.toLowerCase())) {
                n.color = { background: 'yellow', border: 'orange' };
            }
        });
    }
} 