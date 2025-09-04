#!/usr/bin/env python3
"""
Test script for the reliable canvas communication system.

This script demonstrates the new reliable communication methods:
1. URL parameter updates with auto-refresh
2. LocalStorage backup
3. Multiple fallback methods
"""

import streamlit as st
import json
import time
from datetime import datetime

st.set_page_config(page_title="Reliable Canvas Communication Test", layout="wide")

st.title("🔧 Reliable Canvas Communication Test")

st.markdown("""
## New Communication System Features:

✅ **Multiple Fallback Methods:**
- URL parameter updates with page refresh
- LocalStorage backup storage
- Message queuing system
- Automatic retry mechanisms

✅ **Enhanced Reliability:**
- Message deduplication
- Automatic cleanup of old messages
- Comprehensive error handling
- Debug information and monitoring

✅ **Better User Experience:**
- Immediate visual feedback
- Consistent interaction behavior
- Reduced message loss
- Clear error reporting
""")

# Initialize the reliable communication system
try:
    from src.ui.reliable_canvas_communication import get_canvas_communicator
    communicator = get_canvas_communicator()
    
    st.success("✅ Reliable communication system loaded successfully!")
    
    # Process any pending messages
    message_processed = communicator.process_canvas_messages()
    if message_processed:
        st.success("🎯 Canvas message processed!")
        st.balloons()
    
    # Show debug information
    communicator.render_debug_info()
    
except Exception as e:
    st.error(f"❌ Error loading communication system: {e}")
    st.code(str(e))

# Test canvas with reliable communication
st.subheader("🎯 Test Canvas with Reliable Communication")

# Create test HTML with the reliable communication system
test_html = f"""
<div style="border: 2px solid #007acc; padding: 20px; background: #f8f9fa; border-radius: 8px;">
    <h3>🖱️ Interactive Test Area</h3>
    <div id="test-canvas" style="
        width: 300px; 
        height: 200px; 
        background: linear-gradient(45deg, #007acc, #00bcd4); 
        border-radius: 10px; 
        margin: 20px auto; 
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        font-size: 18px;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
        position: relative;
        overflow: hidden;
    ">
        <div id="canvas-text">Click, Double-Click, or Right-Click Me!</div>
        <div id="click-indicator" style="
            position: absolute;
            width: 20px;
            height: 20px;
            background: rgba(255,255,255,0.8);
            border-radius: 50%;
            display: none;
            pointer-events: none;
        "></div>
    </div>
    
    <div id="message-log" style="
        background: white; 
        border: 1px solid #ddd; 
        padding: 15px; 
        border-radius: 5px;
        max-height: 200px;
        overflow-y: auto;
        font-family: monospace;
        font-size: 12px;
    ">
        <strong>📋 Message Log:</strong><br>
        <div id="log-content">Ready for interactions...</div>
    </div>
</div>

{communicator.get_enhanced_javascript()}

<script>
// Additional test-specific functionality
document.addEventListener('DOMContentLoaded', function() {{
    const testCanvas = document.getElementById('test-canvas');
    const logContent = document.getElementById('log-content');
    const clickIndicator = document.getElementById('click-indicator');
    
    function addLogEntry(message) {{
        const timestamp = new Date().toLocaleTimeString();
        logContent.innerHTML += '<br>[' + timestamp + '] ' + message;
        logContent.scrollTop = logContent.scrollHeight;
        console.log('[TEST] ' + message);
    }}
    
    function showClickIndicator(x, y) {{
        const rect = testCanvas.getBoundingClientRect();
        clickIndicator.style.left = (x - rect.left - 10) + 'px';
        clickIndicator.style.top = (y - rect.top - 10) + 'px';
        clickIndicator.style.display = 'block';
        
        setTimeout(function() {{
            clickIndicator.style.display = 'none';
        }}, 500);
    }}
    
    // Override the reliable communication to add test logging
    const originalSendMessage = window.reliableCanvasCommunication.sendMessage;
    window.reliableCanvasCommunication.sendMessage = function(action, payload) {{
        addLogEntry('🚀 Sending ' + action + ' with payload: ' + JSON.stringify(payload));
        return originalSendMessage.call(this, action, payload);
    }};
    
    // Add test-specific event handlers
    testCanvas.addEventListener('click', function(event) {{
        showClickIndicator(event.clientX, event.clientY);
        addLogEntry('🖱️ Click detected on test canvas');
    }});
    
    testCanvas.addEventListener('dblclick', function(event) {{
        showClickIndicator(event.clientX, event.clientY);
        addLogEntry('🖱️🖱️ Double-click detected on test canvas');
    }});
    
    testCanvas.addEventListener('contextmenu', function(event) {{
        showClickIndicator(event.clientX, event.clientY);
        addLogEntry('🖱️➡️ Right-click detected on test canvas');
    }});
    
    addLogEntry('✅ Test canvas initialized with reliable communication');
}});
</script>
"""

st.components.v1.html(test_html, height=400)

# Show current URL parameters
st.subheader("📨 Current URL Parameters")
params = dict(st.query_params)
if params:
    st.json(params)
    
    # Show if we have canvas messages
    if any(key.startswith('canvas_') for key in params.keys()):
        st.success("🎯 Canvas message detected in URL!")
        
        # Extract canvas message details
        action = params.get('canvas_action')
        payload_str = params.get('canvas_payload')
        message_id = params.get('canvas_message_id')
        
        if action and payload_str:
            st.markdown(f"**Action:** `{action}`")
            st.markdown(f"**Message ID:** `{message_id}`")
            
            try:
                payload = json.loads(payload_str)
                st.markdown("**Payload:**")
                st.json(payload)
            except:
                st.error("Invalid payload JSON")
else:
    st.info("No URL parameters - try interacting with the test canvas above")

# Manual testing section
st.subheader("🧪 Manual Testing")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🖱️ Simulate Click"):
        # Simulate a canvas click by setting URL parameters
        st.query_params.update({
            'canvas_action': 'canvas_click',
            'canvas_payload': json.dumps({
                'x': 150, 'y': 100, 
                'canvasWidth': 300, 'canvasHeight': 200
            }),
            'canvas_message_id': str(int(time.time())),
            'canvas_timestamp': str(int(time.time() * 1000))
        })
        st.rerun()

with col2:
    if st.button("🖱️🖱️ Simulate Double-Click"):
        st.query_params.update({
            'canvas_action': 'canvas_dblclick',
            'canvas_payload': json.dumps({
                'x': 150, 'y': 100, 
                'canvasWidth': 300, 'canvasHeight': 200
            }),
            'canvas_message_id': str(int(time.time())),
            'canvas_timestamp': str(int(time.time() * 1000))
        })
        st.rerun()

with col3:
    if st.button("🗑️ Clear Parameters"):
        st.query_params.clear()
        st.success("Parameters cleared!")
        st.rerun()

# Instructions
with st.expander("📖 How to Test", expanded=True):
    st.markdown("""
    ### Testing Steps:
    
    1. **Interact with the test canvas above:**
       - Single click anywhere on the blue gradient area
       - Double-click to test double-click handling
       - Right-click to test context menu handling
    
    2. **Watch for:**
       - Messages appearing in the log area
       - URL parameters updating automatically
       - Page refreshing to process messages
       - Success notifications appearing
    
    3. **Check the debug panel** in the sidebar for:
       - Message processing statistics
       - Recent message history
       - Manual test buttons
    
    4. **Use manual test buttons** to simulate interactions without clicking
    
    ### What Should Happen:
    - ✅ Click → Page refreshes → Success message appears
    - ✅ Double-click → Page refreshes → Edit action triggered
    - ✅ Right-click → Confirmation dialog → Delete action triggered
    - ✅ All interactions logged and processed reliably
    """)

# Show system status
st.subheader("📊 System Status")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Communication System", "✅ Active")

with col2:
    try:
        from src.ui.network_visualization import render_network_visualization
        st.metric("Network Visualization", "✅ Available")
    except:
        st.metric("Network Visualization", "❌ Error")

with col3:
    try:
        from src.integration.service_adapter import get_service_adapter
        adapter = get_service_adapter()
        ideas = adapter.get_ideas()
        st.metric("Nodes Available", len(ideas))
    except:
        st.metric("Nodes Available", "❌ Error")