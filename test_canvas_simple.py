#!/usr/bin/env python3
"""
Simple canvas interaction test with enhanced debugging.

This script will:
1. Start the app with debug logging
2. Show what to look for in browser console
3. Provide simple test instructions
"""

import streamlit as st
import logging
import json
from datetime import datetime

# Configure logging to show debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

st.set_page_config(page_title="Canvas Interaction Test", layout="wide")

st.title("🧪 Canvas Interaction Debug Test")

st.markdown("""
## How to Test Canvas Interactions

1. **Open Browser Developer Tools** (F12)
2. **Go to Console tab**
3. **Try these interactions on the canvas below:**
   - Single click on a node
   - Double click on a node  
   - Right click on a node
   - Click on empty space

## What to Look For in Console:

### ✅ SUCCESS Indicators:
- `🚀 Loading canvas interaction JavaScript...`
- `✅ Canvas interaction JavaScript loaded`
- `POSTMESSAGE: Sending message to parent: canvas_click`
- `Canvas clicked at (x, y) on canvas WxH`
- `Selected node X: NodeName`

### ❌ ERROR Indicators:
- `ERROR: mynetwork div not found`
- `POSTMESSAGE: Communication failed`
- `No node found near click position`
- Any JavaScript errors in red

### 🐛 Debug Commands (run in console):
```javascript
// Check if network object is available
window.visNetwork

// Check node positions
window.serverNodePositions

// Test message sending
window.directParentCommunication.sendMessage('test', {test: true})

// Check position debugging
window.positionDebug.getDebugInfo()
```
""")

# Show current URL parameters
st.subheader("📨 Current URL Parameters")
params = dict(st.query_params)
if params:
    st.json(params)
    
    # Process any action
    action = params.get('action')
    payload_str = params.get('payload')
    
    if action and payload_str:
        st.success(f"🎯 **Message Received!** Action: `{action}`")
        try:
            payload = json.loads(payload_str)
            st.json(payload)
            
            # Clear the parameters after showing them
            if st.button("Clear Message"):
                st.query_params.clear()
                st.rerun()
                
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON payload: {e}")
else:
    st.info("No messages received yet. Try clicking on the canvas below.")

# Show message history from session state
if 'message_history' not in st.session_state:
    st.session_state.message_history = []

st.subheader("📋 Message History")
if st.session_state.message_history:
    for i, msg in enumerate(reversed(st.session_state.message_history[-10:])):  # Show last 10
        with st.expander(f"Message {len(st.session_state.message_history) - i}: {msg['action']} at {msg['time']}"):
            st.json(msg)
else:
    st.info("No messages in history yet.")

# Add a simple test canvas
st.subheader("🎯 Test Canvas")

# Create a simple HTML canvas for testing
test_html = """
<div id="test-area" style="border: 2px solid #ccc; padding: 20px; background: #f9f9f9;">
    <h3>Simple Click Test</h3>
    <div id="click-target" style="
        width: 100px; 
        height: 100px; 
        background: #007acc; 
        border-radius: 50%; 
        margin: 20px auto; 
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
    ">
        Click Me!
    </div>
    <div id="debug-output" style="margin-top: 20px; padding: 10px; background: white; border: 1px solid #ddd;">
        <strong>Debug Output:</strong><br>
        <div id="debug-log">Click the blue circle above to test...</div>
    </div>
</div>

<script>
function debugLog(message) {
    const log = document.getElementById('debug-log');
    const timestamp = new Date().toLocaleTimeString();
    log.innerHTML += '<br>[' + timestamp + '] ' + message;
    console.log('[DEBUG] ' + message);
}

document.getElementById('click-target').addEventListener('click', function(event) {
    debugLog('🎯 Click detected on test target');
    
    // Test message sending
    const payload = {
        x: 50,
        y: 50,
        canvasWidth: 100,
        canvasHeight: 100,
        test: true,
        timestamp: Date.now()
    };
    
    try {
        // Method 1: postMessage
        window.parent.postMessage({
            source: 'test_canvas',
            action: 'canvas_click',
            payload: payload
        }, '*');
        debugLog('✅ postMessage sent successfully');
        
        // Method 2: URL parameters
        const params = new URLSearchParams(window.location.search);
        params.set('action', 'canvas_click');
        params.set('payload', JSON.stringify(payload));
        
        const newUrl = window.location.pathname + '?' + params.toString();
        debugLog('🔄 Updating URL: ' + newUrl);
        
        // Update URL and reload
        setTimeout(function() {
            window.location.href = newUrl;
        }, 1000);
        
    } catch (e) {
        debugLog('❌ Error: ' + e.message);
    }
});

debugLog('🚀 Test canvas initialized');
</script>
"""

st.components.v1.html(test_html, height=300)

# Add the actual mind map canvas
st.subheader("🗺️ Mind Map Canvas")
st.info("The actual mind map canvas will appear below (if the app is running properly)")

# Try to render the actual canvas
try:
    from src.ui.network_visualization import render_network_visualization
    render_network_visualization("400px")
except Exception as e:
    st.error(f"Error loading mind map canvas: {e}")
    st.code(str(e))

# Add manual message testing
st.subheader("🧪 Manual Message Testing")

col1, col2 = st.columns(2)

with col1:
    if st.button("Test Canvas Click"):
        # Simulate a canvas click message
        test_payload = {
            'x': 100,
            'y': 100,
            'canvasWidth': 400,
            'canvasHeight': 300,
            'timestamp': datetime.now().timestamp() * 1000
        }
        
        # Add to history
        st.session_state.message_history.append({
            'action': 'canvas_click',
            'payload': test_payload,
            'time': datetime.now().strftime("%H:%M:%S"),
            'source': 'manual_test'
        })
        
        st.success("✅ Test message added to history")
        st.rerun()

with col2:
    if st.button("Clear History"):
        st.session_state.message_history = []
        st.success("🗑️ Message history cleared")
        st.rerun()

# Show JavaScript debugging tips
with st.expander("🔧 JavaScript Debugging Tips"):
    st.markdown("""
    ### In Browser Console, try these commands:
    
    ```javascript
    // Check if Streamlit is available
    window.Streamlit
    
    // Check for network objects
    window.visNetwork
    window.network
    
    // Check position data
    window.serverNodePositions
    
    // Test message sending
    window.parent.postMessage({
        source: 'test',
        action: 'canvas_click',
        payload: {x: 100, y: 100, canvasWidth: 400, canvasHeight: 300}
    }, '*');
    
    // Check for mynetwork div
    document.getElementById('mynetwork')
    
    // List all event listeners on mynetwork
    getEventListeners(document.getElementById('mynetwork'))
    ```
    
    ### Common Issues:
    - **No mynetwork div**: Canvas hasn't loaded yet
    - **No visNetwork object**: PyVis network not initialized
    - **postMessage fails**: iframe communication blocked
    - **No event listeners**: JavaScript files not loaded
    """)