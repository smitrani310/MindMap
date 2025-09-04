"""
Reliable Canvas Communication Module

This module implements multiple communication methods between the JavaScript canvas
and Python backend to ensure canvas interactions work consistently with Streamlit.

Methods implemented:
1. Session state polling
2. URL parameter updates with auto-refresh
3. Hidden form submissions
4. LocalStorage with periodic checks
"""

import json
import time
import logging
import streamlit as st
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class ReliableCanvasCommunicator:
    """Handles reliable communication between canvas and Python backend."""
    
    def __init__(self):
        self.init_session_state()
    
    def init_session_state(self):
        """Initialize session state for canvas communication."""
        if 'canvas_messages' not in st.session_state:
            st.session_state.canvas_messages = []
        
        if 'canvas_message_counter' not in st.session_state:
            st.session_state.canvas_message_counter = 0
        
        if 'last_processed_message_id' not in st.session_state:
            st.session_state.last_processed_message_id = 0
    
    def get_enhanced_javascript(self) -> str:
        """Get enhanced JavaScript for reliable canvas communication."""
        return """
        <script>
        // Enhanced Canvas Communication System
        window.reliableCanvasCommunication = {
            messageQueue: [],
            messageId: 0,
            
            // Send message with multiple fallback methods
            sendMessage: function(action, payload) {
                this.messageId++;
                const message = {
                    id: this.messageId,
                    action: action,
                    payload: payload,
                    timestamp: Date.now()
                };
                
                console.log('📤 Sending reliable message:', message);
                
                // Method 1: Try Streamlit component communication
                if (this.sendViaStreamlit(message)) {
                    console.log('✅ Message sent via Streamlit communication');
                    return message.id;
                }
                
                // Method 2: Store in localStorage for polling
                this.sendViaLocalStorage(message);
                
                // Method 3: Add to message queue for polling
                this.messageQueue.push(message);
                
                // Method 4: Use DOM events as fallback
                this.sendViaDOMEvent(message);
                
                return message.id;
            },
            
            // Method 1: Session state update via Streamlit component communication
            sendViaStreamlit: function(message) {
                try {
                    // Try to use Streamlit's component communication if available
                    if (window.Streamlit && window.Streamlit.setComponentValue) {
                        console.log('📡 Streamlit method: Sending via setComponentValue');
                        window.Streamlit.setComponentValue({
                            type: 'canvas_interaction',
                            data: message
                        });
                        return true;
                    }
                    
                    // Fallback: Try to communicate with parent window
                    if (window.parent && window.parent !== window) {
                        console.log('📡 Parent method: Sending to parent window');
                        window.parent.postMessage({
                            type: 'streamlit_canvas_message',
                            data: message
                        }, '*');
                        return true;
                    }
                    
                    return false;
                } catch (e) {
                    console.error('❌ Streamlit method failed:', e);
                    return false;
                }
            },
            
            // Method 2: LocalStorage with timestamp for polling
            sendViaLocalStorage: function(message) {
                try {
                    const storageKey = 'mindmap_canvas_message_' + message.id;
                    localStorage.setItem(storageKey, JSON.stringify(message));
                    localStorage.setItem('mindmap_latest_message_id', message.id.toString());
                    localStorage.setItem('mindmap_message_trigger', Date.now().toString());
                    console.log('💾 LocalStorage method: Stored message', message.id);
                    return true;
                } catch (e) {
                    console.error('❌ LocalStorage method failed:', e);
                    return false;
                }
            },
            
            // Method 3: DOM event dispatch
            sendViaDOMEvent: function(message) {
                try {
                    const event = new CustomEvent('mindmapCanvasInteraction', {
                        detail: message,
                        bubbles: true
                    });
                    document.dispatchEvent(event);
                    console.log('🎯 DOM Event method: Dispatched custom event');
                    return true;
                } catch (e) {
                    console.error('❌ DOM Event method failed:', e);
                    return false;
                }
            },
            
            // Get pending messages from queue
            getPendingMessages: function() {
                const pending = [...this.messageQueue];
                this.messageQueue = []; // Clear queue
                return pending;
            },
            
            // Clear old localStorage messages
            cleanupOldMessages: function() {
                try {
                    const keys = Object.keys(localStorage);
                    const messageKeys = keys.filter(key => key.startsWith('mindmap_canvas_message_'));
                    
                    // Keep only the last 10 messages
                    if (messageKeys.length > 10) {
                        const sortedKeys = messageKeys.sort((a, b) => {
                            const idA = parseInt(a.split('_').pop());
                            const idB = parseInt(b.split('_').pop());
                            return idA - idB;
                        });
                        
                        // Remove oldest messages
                        for (let i = 0; i < sortedKeys.length - 10; i++) {
                            localStorage.removeItem(sortedKeys[i]);
                        }
                    }
                } catch (e) {
                    console.error('Cleanup failed:', e);
                }
            }
        };
        
        // Enhanced canvas event handlers
        function setupReliableCanvasEvents() {
            const networkDiv = document.getElementById('mynetwork');
            if (!networkDiv) {
                console.warn('⚠️ mynetwork div not found for reliable events');
                return false;
            }
            
            console.log('🎯 Setting up reliable canvas events');
            
            // Click handler
            networkDiv.addEventListener('click', function(event) {
                const rect = networkDiv.getBoundingClientRect();
                const payload = {
                    x: event.clientX - rect.left,
                    y: event.clientY - rect.top,
                    canvasWidth: rect.width,
                    canvasHeight: rect.height
                };
                
                console.log('🖱️ Canvas click detected:', payload);
                window.reliableCanvasCommunication.sendMessage('canvas_click', payload);
            });
            
            // Double-click handler
            networkDiv.addEventListener('dblclick', function(event) {
                event.preventDefault();
                const rect = networkDiv.getBoundingClientRect();
                const payload = {
                    x: event.clientX - rect.left,
                    y: event.clientY - rect.top,
                    canvasWidth: rect.width,
                    canvasHeight: rect.height
                };
                
                console.log('🖱️🖱️ Canvas double-click detected:', payload);
                window.reliableCanvasCommunication.sendMessage('canvas_dblclick', payload);
            });
            
            // Right-click handler
            networkDiv.addEventListener('contextmenu', function(event) {
                event.preventDefault();
                const rect = networkDiv.getBoundingClientRect();
                const payload = {
                    x: event.clientX - rect.left,
                    y: event.clientY - rect.top,
                    canvasWidth: rect.width,
                    canvasHeight: rect.height
                };
                
                if (confirm('Delete this node?')) {
                    console.log('🖱️➡️ Canvas right-click detected:', payload);
                    window.reliableCanvasCommunication.sendMessage('canvas_contextmenu', payload);
                }
                
                return false;
            });
            
            console.log('✅ Reliable canvas events set up successfully');
            return true;
        }
        
        // Set up drag handler for position updates
        function setupReliableDragHandler() {
            if (!window.visNetwork) {
                console.warn('⚠️ visNetwork not available for drag handler');
                return false;
            }
            
            window.visNetwork.on('dragEnd', function(params) {
                if (params.nodes && params.nodes.length > 0) {
                    const nodeId = params.nodes[0];
                    const positions = window.visNetwork.getPositions([nodeId]);
                    const position = positions[nodeId];
                    
                    if (position) {
                        const payload = {
                            id: nodeId,
                            x: position.x,
                            y: position.y
                        };
                        
                        console.log('🔄 Node dragged:', payload);
                        window.reliableCanvasCommunication.sendMessage('pos', payload);
                    }
                }
            });
            
            console.log('✅ Reliable drag handler set up');
            return true;
        }
        
        // Initialize when DOM is ready
        document.addEventListener('DOMContentLoaded', function() {
            console.log('🚀 Initializing reliable canvas communication');
            
            // Try to set up events immediately
            if (!setupReliableCanvasEvents()) {
                // Retry with delays if network div not ready
                let attempts = 0;
                const maxAttempts = 20;
                
                const retrySetup = setInterval(function() {
                    attempts++;
                    console.log(`🔄 Retry attempt ${attempts}/${maxAttempts} for canvas events`);
                    
                    if (setupReliableCanvasEvents()) {
                        clearInterval(retrySetup);
                        console.log('✅ Canvas events set up on retry');
                    } else if (attempts >= maxAttempts) {
                        clearInterval(retrySetup);
                        console.error('❌ Failed to set up canvas events after all retries');
                    }
                }, 500);
            }
            
            // Set up drag handler with retry
            setTimeout(function() {
                if (!setupReliableDragHandler()) {
                    let dragAttempts = 0;
                    const maxDragAttempts = 10;
                    
                    const retryDrag = setInterval(function() {
                        dragAttempts++;
                        console.log(`🔄 Retry attempt ${dragAttempts}/${maxDragAttempts} for drag handler`);
                        
                        if (setupReliableDragHandler()) {
                            clearInterval(retryDrag);
                            console.log('✅ Drag handler set up on retry');
                        } else if (dragAttempts >= maxDragAttempts) {
                            clearInterval(retryDrag);
                            console.error('❌ Failed to set up drag handler after all retries');
                        }
                    }, 1000);
                }
            }, 2000);
            
            // Clean up old messages periodically
            setInterval(function() {
                window.reliableCanvasCommunication.cleanupOldMessages();
            }, 30000); // Every 30 seconds
            
            // Set up Streamlit component communication
            if (window.Streamlit) {
                window.Streamlit.setComponentReady();
                console.log('✅ Streamlit component ready');
                
                // Listen for messages from localStorage and forward to Streamlit
                setInterval(function() {
                    try {
                        const latestId = localStorage.getItem('mindmap_latest_message_id');
                        const trigger = localStorage.getItem('mindmap_message_trigger');
                        
                        if (latestId && trigger) {
                            const messageKey = 'mindmap_canvas_message_' + latestId;
                            const messageData = localStorage.getItem(messageKey);
                            
                            if (messageData) {
                                const message = JSON.parse(messageData);
                                console.log('📥 Forwarding localStorage message to Streamlit:', message);
                                
                                // Send to Streamlit
                                window.Streamlit.setComponentValue({
                                    type: 'canvas_message',
                                    message: message
                                });
                                
                                // Clean up
                                localStorage.removeItem(messageKey);
                                localStorage.removeItem('mindmap_message_trigger');
                                localStorage.removeItem('mindmap_latest_message_id');
                            }
                        }
                    } catch (e) {
                        console.error('Error forwarding localStorage message:', e);
                    }
                }, 100); // Check every 100ms
            }
        });
        </script>
        """
    
    def check_component_messages(self) -> Optional[Dict[str, Any]]:
        """Check for messages from Streamlit component communication."""
        try:
            # Ensure session state is initialized
            self.init_session_state()
            
            # Check if there's a component message in session state
            if hasattr(st.session_state, 'canvas_component_message'):
                message_data = st.session_state.canvas_component_message
                
                if message_data and 'id' in message_data:
                    message_id = message_data['id']
                    
                    # Check if we've already processed this message
                    if message_id <= st.session_state.last_processed_message_id:
                        return None
                    
                    message = {
                        'id': message_id,
                        'action': message_data['action'],
                        'payload': message_data['payload'],
                        'timestamp': message_data.get('timestamp', int(time.time() * 1000)),
                        'source': 'component'
                    }
                    
                    # Clear the message after processing
                    del st.session_state.canvas_component_message
                    
                    logger.info(f"📨 Received component message: {message['action']} (ID: {message_id})")
                    return message
                
        except Exception as e:
            logger.error(f"Error processing component message: {e}")
        
        return None
    
    def create_localStorage_checker(self) -> str:
        """Create JavaScript code to check localStorage and update session state."""
        return """
        <script>
        // Check localStorage for new messages and update Streamlit
        function checkLocalStorageMessages() {
            try {
                const latestId = localStorage.getItem('mindmap_latest_message_id');
                if (!latestId) return;
                
                const messageKey = 'mindmap_canvas_message_' + latestId;
                const messageData = localStorage.getItem(messageKey);
                
                if (messageData) {
                    const message = JSON.parse(messageData);
                    console.log('📥 Found localStorage message:', message);
                    
                    // Try to send to Streamlit via component communication
                    if (window.Streamlit && window.Streamlit.setComponentValue) {
                        window.Streamlit.setComponentValue({
                            type: 'canvas_message',
                            message: message
                        });
                        console.log('📤 Sent message to Streamlit');
                        
                        // Clean up processed message
                        localStorage.removeItem(messageKey);
                    }
                }
            } catch (e) {
                console.error('Error checking localStorage messages:', e);
            }
        }
        
        // Check for messages periodically
        setInterval(checkLocalStorageMessages, 100);
        
        // Also check immediately
        checkLocalStorageMessages();
        </script>
        """
    
    def process_canvas_messages(self) -> bool:
        """Process any pending canvas messages."""
        message_processed = False
        
        # Check component messages first (most reliable)
        component_message = self.check_component_messages()
        if component_message:
            success = self.handle_canvas_message(component_message)
            if success:
                st.session_state.last_processed_message_id = component_message['id']
                message_processed = True
        
        return message_processed
    
    def handle_canvas_message(self, message: Dict[str, Any]) -> bool:
        """Handle a canvas message."""
        try:
            action = message['action']
            payload = message['payload']
            
            logger.info(f"🎯 Processing canvas message: {action}")
            
            # Import here to avoid circular imports
            from src.events import handle_canvas_click, handle_position_update
            
            if action.startswith('canvas_'):
                # Handle canvas interactions
                success = handle_canvas_click(payload, action)
                if success:
                    st.success(f"✅ Canvas {action.replace('canvas_', '')} processed successfully!")
                    return True
                else:
                    st.warning(f"⚠️ Canvas {action.replace('canvas_', '')} - no node found at click position")
                    return False
            
            elif action == 'pos':
                # Handle position updates
                success = handle_position_update(payload)
                if success:
                    logger.info(f"✅ Position update processed for node {payload.get('id')}")
                    return True
                else:
                    logger.warning(f"⚠️ Position update failed for node {payload.get('id')}")
                    return False
            
            else:
                logger.warning(f"Unknown canvas action: {action}")
                return False
                
        except Exception as e:
            logger.error(f"Error handling canvas message: {e}")
            st.error(f"Error processing canvas interaction: {e}")
            return False
    


# Global instance
_communicator = None

def get_canvas_communicator() -> ReliableCanvasCommunicator:
    """Get the global canvas communicator instance."""
    global _communicator
    if _communicator is None:
        _communicator = ReliableCanvasCommunicator()
    return _communicator