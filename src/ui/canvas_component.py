"""
Canvas Component Wrapper

This module provides a Streamlit component wrapper for reliable canvas communication
without causing page reloads or nested iframe issues.
"""

import streamlit as st
import streamlit.components.v1 as components
from typing import Dict, Any, Optional
import json
import logging

logger = logging.getLogger(__name__)

def canvas_communication_component(html_content: str, height: int = 600) -> Optional[Dict[str, Any]]:
    """
    Render HTML content with reliable canvas communication.
    
    Args:
        html_content: The HTML content to render
        height: Height of the component
        
    Returns:
        Any messages received from the canvas
    """
    
    # Add the communication wrapper
    wrapped_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ margin: 0; padding: 0; }}
            #canvas-container {{ width: 100%; height: 100%; }}
        </style>
    </head>
    <body>
        <div id="canvas-container">
            {html_content}
        </div>
        
        <script>
        // Enhanced Streamlit communication
        window.streamlitCanvasComm = {{
            sendMessage: function(message) {{
                console.log('📤 Sending message to Streamlit:', message);
                
                try {{
                    // Method 1: Direct Streamlit communication
                    if (window.Streamlit && window.Streamlit.setComponentValue) {{
                        window.Streamlit.setComponentValue({{
                            type: 'canvas_interaction',
                            timestamp: Date.now(),
                            data: message
                        }});
                        console.log('✅ Message sent via Streamlit.setComponentValue');
                        return true;
                    }}
                    
                    // Method 2: Session storage for polling
                    sessionStorage.setItem('canvas_message', JSON.stringify({{
                        ...message,
                        timestamp: Date.now()
                    }}));
                    sessionStorage.setItem('canvas_message_trigger', Date.now().toString());
                    console.log('✅ Message stored in sessionStorage');
                    
                    return true;
                }} catch (e) {{
                    console.error('❌ Failed to send message:', e);
                    return false;
                }}
            }}
        }};
        
        // Override the reliable communication to use our wrapper
        document.addEventListener('DOMContentLoaded', function() {{
            // Wait for the reliable communication system to load
            setTimeout(function() {{
                if (window.reliableCanvasCommunication) {{
                    const originalSendMessage = window.reliableCanvasCommunication.sendMessage;
                    
                    window.reliableCanvasCommunication.sendMessage = function(action, payload) {{
                        const message = {{
                            id: ++this.messageId,
                            action: action,
                            payload: payload,
                            timestamp: Date.now()
                        }};
                        
                        console.log('🔄 Intercepted message:', message);
                        
                        // Use our enhanced communication instead
                        return window.streamlitCanvasComm.sendMessage(message);
                    }};
                    
                    console.log('✅ Canvas communication intercepted and enhanced');
                }}
            }}, 1000);
        }});
        
        // Initialize Streamlit component
        if (window.Streamlit) {{
            window.Streamlit.setComponentReady();
            console.log('✅ Canvas component ready');
        }}
        </script>
    </body>
    </html>
    """
    
    # Render the component and get any return value
    component_value = components.html(
        wrapped_html,
        height=height,
        scrolling=False
    )
    
    # Check for messages in session storage as fallback
    if not component_value:
        # This would be implemented with a separate polling mechanism
        # For now, we'll rely on the component communication
        pass
    
    return component_value

def process_canvas_component_message(component_value: Any) -> Optional[Dict[str, Any]]:
    """
    Process a message received from the canvas component.
    
    Args:
        component_value: The value returned from the component
        
    Returns:
        Processed message data or None
    """
    if not component_value:
        return None
    
    try:
        if isinstance(component_value, dict):
            if component_value.get('type') == 'canvas_interaction':
                message_data = component_value.get('data', {})
                
                logger.info(f"📨 Received canvas component message: {message_data.get('action')}")
                
                return {
                    'id': message_data.get('id', 0),
                    'action': message_data.get('action'),
                    'payload': message_data.get('payload', {}),
                    'timestamp': message_data.get('timestamp', 0),
                    'source': 'component'
                }
        
    except Exception as e:
        logger.error(f"Error processing canvas component message: {e}")
    
    return None