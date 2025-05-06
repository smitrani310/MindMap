// Message utilities for the Enhanced Mind Map application
import { v4 as uuidv4 } from 'uuid';

// Create a message with the standardized format
function createMessage(source, action, payload) {
    return {
        source: source,
        action: action,
        payload: payload,
        message_id: uuidv4(),
        timestamp: Date.now(),
        status: 'pending'
    };
}

// Validate a message object
function validateMessage(message) {
    try {
        if (!message || typeof message !== 'object') {
            console.error('Invalid message: not an object');
            return false;
        }

        // Check required fields
        const requiredFields = ['source', 'action', 'payload', 'message_id', 'timestamp'];
        for (const field of requiredFields) {
            if (!(field in message)) {
                console.error(`Invalid message: missing ${field}`);
                return false;
            }
        }

        // Validate field types
        if (typeof message.source !== 'string' || message.source.trim() === '') {
            console.error('Invalid message: invalid source');
            return false;
        }

        if (typeof message.action !== 'string' || message.action.trim() === '') {
            console.error('Invalid message: invalid action');
            return false;
        }

        if (typeof message.payload !== 'object') {
            console.error('Invalid message: invalid payload');
            return false;
        }

        if (typeof message.message_id !== 'string' || message.message_id.trim() === '') {
            console.error('Invalid message: invalid message_id');
            return false;
        }

        if (typeof message.timestamp !== 'number' || message.timestamp <= 0) {
            console.error('Invalid message: invalid timestamp');
            return false;
        }

        return true;
    } catch (error) {
        console.error('Error validating message:', error);
        return false;
    }
}

// Send a message using the standardized format
function sendMessage(message) {
    try {
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
                sendMessage(message);
            }
            localStorage.removeItem('mindmap_message');
        }
    } catch (e) {
        console.error('Error checking stored messages:', e);
    }
}

// Export the functions
window.messageUtils = {
    createMessage,
    validateMessage,
    sendMessage,
    handleIncomingMessage,
    initializeMessageHandling
}; 