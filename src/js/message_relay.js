/**
 * message_relay.js - Handles communication between parent window and iframes
 * 
 * This file contains:
 * - Message sending functions from iframe to parent window
 * - Message handling for postMessage events
 * - Multiple fallback methods for communication
 * - Debug logging
 */

// Create a hidden form for direct form submissions
document.addEventListener('DOMContentLoaded', function() {
    var hiddenForm = document.createElement('form');
    hiddenForm.id = 'hidden-message-form';
    hiddenForm.method = 'GET';
    hiddenForm.target = '_top'; // Target the top window
    hiddenForm.style.display = 'none';

    // Add input fields
    var actionInput = document.createElement('input');
    actionInput.type = 'hidden';
    actionInput.id = 'hidden-action-input';
    actionInput.name = 'action';

    var payloadInput = document.createElement('input');
    payloadInput.type = 'hidden';
    payloadInput.id = 'hidden-payload-input';
    payloadInput.name = 'payload';

    // Add submit button
    var submitButton = document.createElement('button');
    submitButton.type = 'submit';
    submitButton.id = 'hidden-submit-button';
    submitButton.style.display = 'none';

    // Assemble the form
    hiddenForm.appendChild(actionInput);
    hiddenForm.appendChild(payloadInput);
    hiddenForm.appendChild(submitButton);

    // Add form to document
    document.body.appendChild(hiddenForm);
});

// Create global helper for direct parent-frame communication using pure postMessage
window.directParentCommunication = {
    sendMessage: function(action, payload) {
        try {
            console.log('POSTMESSAGE: Sending message to parent: ' + action);
            
            // Create the message object
            var message = {
                source: 'network_canvas',
                action: action,
                payload: payload,
                timestamp: Date.now()
            };
            
            // Send to parent directly - this works even in sandboxed iframes
            window.parent.postMessage(message, '*');
            console.log('POSTMESSAGE: Message sent to parent');
            return true;
        } catch(e) {
            console.error('POSTMESSAGE: Communication failed: ' + e.message);
            return false;
        }
    }
};

// Communication helper for sending messages to Streamlit with multiple fallback methods
function simpleSendMessage(action, payload) {
    try {
        // Package the message with source identifier
        var message = {
            source: 'network_canvas',
            action: action,
            payload: payload,
            timestamp: Date.now()
        };
        
        // Track if any communication method succeeds
        var communicationSucceeded = false;
        
        // Try direct parent communication first (most reliable)
        try {
            const directResult = window.directParentCommunication.sendMessage(action, payload);
            if (directResult) {
                communicationSucceeded = true;
                return; // Exit early if successful
            }
        } catch(e) {
            console.error('Direct parent communication failed: ' + e.message);
        }
        
        // Method 1: Send via postMessage (main method)
        try {
            // Try multiple targets (sometimes frames can be nested)
            const targets = [window.parent, window.top, window];
            
            for (let i = 0; i < targets.length; i++) {
                try {
                    const target = targets[i];
                    if (target && target !== window) {
                        target.postMessage(message, '*');
                        communicationSucceeded = true;
                        break;
                    }
                } catch (e) {
                    console.error(`Failed to send to target ${i}: ${e.message}`);
                }
            }
            
            if (!communicationSucceeded) {
                // Try standard window.parent as last resort
                window.parent.postMessage(message, '*');
                communicationSucceeded = true;
            }
        } catch(e) {
            console.error('All postMessage attempts failed: ' + e.message);
        }
        
        // Method 2: Direct URL parameter modification if postMessage failed
        if (!communicationSucceeded) {
            try {
                var params = new URLSearchParams(window.location.search);
                params.set('action', action);
                
                // Make sure to preserve all payload fields for coordinate calculations
                if (payload) {
                    // Include canvas dimensions with click coordinates
                    if (payload.x !== undefined && payload.y !== undefined) {
                        var networkDiv = document.getElementById('mynetwork');
                        if (networkDiv) {
                            var rect = networkDiv.getBoundingClientRect();
                            payload.canvasWidth = rect.width;
                            payload.canvasHeight = rect.height;
                        }
                    }
                }
                
                params.set('payload', JSON.stringify(payload));
                var newUrl = window.top.location.pathname + '?' + params.toString();
                window.top.location.href = newUrl;
                communicationSucceeded = true;
                return; // Success, so return early
            } catch(e) {
                console.error('URL parameter method failed: ' + e.message);
            }
        }
        
        // Method 3: Try localStorage if available and previous methods failed
        if (!communicationSucceeded && window.localStorage) {
            try {
                localStorage.setItem('mindmap_message', JSON.stringify(message));
                localStorage.setItem('mindmap_trigger_reload', Date.now().toString());
                communicationSucceeded = true;
            } catch(e) {
                console.error('localStorage method failed: ' + e.message);
            }
        }
        
        // Method 4: Form submission as last resort
        if (!communicationSucceeded) {
            try {
                var form = document.getElementById('hidden-message-form');
                var actionInput = document.getElementById('hidden-action-input');
                var payloadInput = document.getElementById('hidden-payload-input');
                
                if (form && actionInput && payloadInput) {
                    actionInput.value = action;
                    payloadInput.value = JSON.stringify(payload);
                    form.submit();
                    communicationSucceeded = true;
                }
            } catch(e) {
                console.error('Form submission method failed: ' + e.message);
            }
        }
    } catch(e) {
        console.error('CRITICAL ERROR in simpleSendMessage: ' + e.message);
    }
}

// Parent window handler for receiving messages
document.addEventListener('DOMContentLoaded', function() {
    // Log that this parent window script is loaded
    console.log('Parent window message handler initialized');

    try {
        // Create debug logging functions for console only, no visual overlay
        function parentDebugLog(message) {
            console.log(message);
        }

        // Helper to process a message no matter how it was received
        function processMessage(action, payload) {
            try {
                if (!action) {
                    parentDebugLog('No action provided');
                    return;
                }
                
                parentDebugLog('Processing message: ' + action);
                
                // Store in session or local storage as backup
                try {
                    localStorage.setItem('last_message_action', action);
                    localStorage.setItem('last_message_payload', JSON.stringify(payload));
                    localStorage.setItem('last_message_time', new Date().toISOString());
                } catch (e) {
                    parentDebugLog('Failed to store in localStorage: ' + e.message);
                }
                
                // Set URL parameters
                var params = new URLSearchParams(window.location.search);
                params.set('action', action);
                params.set('payload', JSON.stringify(payload));
                
                // Update URL without navigation
                try {
                    window.history.pushState({}, '', window.location.pathname + '?' + params.toString());
                    parentDebugLog('URL updated with parameters');
                } catch (e) {
                    parentDebugLog('Failed to update URL: ' + e.message);
                }
                
                // Force a page reload to process the message
                parentDebugLog('Reloading page to process message');
                setTimeout(function() {
                    location.reload();
                }, 100);
            } catch (e) {
                parentDebugLog('Error processing message: ' + e.message);
                console.error(e);
            }
        }

        // Listen for messages from the iframe
        window.addEventListener('message', function(event) {
            console.log('Received message event', event);
            parentDebugLog('Received message: ' + JSON.stringify(event.data).substring(0, 50) + '...');
            
            // Check if message has the right format
            if (event.data) {
                try {
                    let action, payload;
                    
                    // Try multiple known formats
                    if (event.data.source === 'network_canvas' && event.data.action) {
                        // Standard format
                        action = event.data.action;
                        payload = event.data.payload;
                        parentDebugLog('Recognized standard format message');
                    } else if (event.data.action) {
                        // Alternative format
                        action = event.data.action;
                        payload = event.data.payload;
                        parentDebugLog('Recognized alternative format message');
                    } else if (typeof event.data === 'object') {
                        // Try to infer format
                        if (event.data.type && event.data.payload) {
                            action = event.data.type;
                            payload = event.data.payload;
                            parentDebugLog('Inferred message format from type/payload');
                        } else if (event.data.canvas_click || event.data.canvas_dblclick || event.data.canvas_contextmenu) {
                            // Event-named format
                            const keys = Object.keys(event.data);
                            for (const key of keys) {
                                if (key.startsWith('canvas_')) {
                                    action = key;
                                    payload = event.data[key];
                                    break;
                                }
                            }
                            parentDebugLog('Inferred message from event-named keys');
                        }
                    }
                    
                    if (action) {
                        processMessage(action, payload);
                    } else {
                        parentDebugLog('Could not determine message format: ' + JSON.stringify(event.data).substring(0, 100));
                    }
                } catch (error) {
                    parentDebugLog('ERROR in message processing: ' + error.message);
                    console.error(error);
                }
            } else {
                parentDebugLog('Empty message received');
            }
        });
        
        parentDebugLog('Parent handler initialized successfully');
    } catch (setupError) {
        console.error('Critical error in parent handler setup:', setupError);
    }
}); 