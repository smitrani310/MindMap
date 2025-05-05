// Message utilities for the Enhanced Mind Map application

// Generate a unique message ID
function generateMessageId() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

// Create a standardized message object
function createMessage(source, action, payload) {
    return {
        source: source,
        action: action,
        payload: payload,
        message_id: generateMessageId(),
        timestamp: Date.now(),
        status: 'pending'
    };
}

// Validate a message object
function validateMessage(message) {
    const requiredFields = ['source', 'action', 'payload', 'message_id', 'timestamp'];
    return requiredFields.every(field => field in message);
}

// Send a message using the standardized format
function sendMessage(source, action, payload) {
    try {
        // Create the message
        const message = createMessage(source, action, payload);
        
        // Validate the message
        if (!validateMessage(message)) {
            console.error('Invalid message format:', message);
            return false;
        }

        // Try to send via postMessage first
        try {
            window.parent.postMessage(message, '*');
            console.log('Message sent via postMessage:', message);
            return true;
        } catch (e) {
            console.error('postMessage failed:', e);
        }

        // Fallback to URL parameters if postMessage fails
        try {
            const params = new URLSearchParams(window.location.search);
            params.set('message', JSON.stringify(message));
            window.location.href = window.location.pathname + '?' + params.toString();
            return true;
        } catch (e) {
            console.error('URL parameter method failed:', e);
        }

        // Last resort: localStorage
        try {
            localStorage.setItem('mindmap_message', JSON.stringify(message));
            localStorage.setItem('mindmap_trigger_reload', Date.now().toString());
            return true;
        } catch (e) {
            console.error('localStorage method failed:', e);
        }

        return false;
    } catch (e) {
        console.error('Error sending message:', e);
        return false;
    }
}

// Handle incoming messages
function handleIncomingMessage(event) {
    try {
        const message = event.data;
        
        // Validate the message
        if (!validateMessage(message)) {
            console.error('Received invalid message format:', message);
            return;
        }

        // Process the message based on its source
        if (message.source === 'backend') {
            // Handle backend responses
            console.log('Received backend response:', message);
            
            // Update UI based on message status
            if (message.status === 'completed') {
                console.log('Action completed successfully:', message.action);
            } else if (message.status === 'failed') {
                console.error('Action failed:', message.error);
            }
        }
    } catch (e) {
        console.error('Error handling incoming message:', e);
    }
}

// Initialize message handling
function initializeMessageHandling() {
    // Add message event listener
    window.addEventListener('message', handleIncomingMessage);
    
    // Check for stored messages on page load
    try {
        const storedMessage = localStorage.getItem('mindmap_message');
        if (storedMessage) {
            const message = JSON.parse(storedMessage);
            if (validateMessage(message)) {
                sendMessage(message.source, message.action, message.payload);
            }
            localStorage.removeItem('mindmap_message');
        }
    } catch (e) {
        console.error('Error checking stored messages:', e);
    }
}

// Export the functions
window.messageUtils = {
    sendMessage,
    createMessage,
    validateMessage,
    handleIncomingMessage,
    initializeMessageHandling
}; 