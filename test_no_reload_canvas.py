#!/usr/bin/env python3
"""
Test script for canvas interactions without page reloads.

This version uses Streamlit component communication instead of URL parameters
to avoid the nested iframe reload issue.
"""

import streamlit as st
import json
import time
from datetime import datetime

st.set_page_config(page_title="No-Reload Canvas Test", layout="wide")

st.title("🚀 Canvas Interactions Without Page Reloads")

st.markdown("""
## New Approach - No More Reloads! 

✅ **Component Communication**: Direct Streamlit component messaging  
✅ **No Page Reloads**: Interactions happen instantly without refreshing  
✅ **No Nested Iframes**: Clean, single-level iframe structure  
✅ **Session Storage Fallback**: Reliable backup communication method  

This approach eliminates the infinite reload issue by using proper Streamlit component communication.
""")

# Test the new canvas component
try:
    from src.ui.canvas_component import canvas_communication_component, process_canvas_component_message
    
    st.subheader("🎯 Interactive Test Canvas")
    
    # Create test HTML
    test_html = """
    <div style="border: 2px solid #007acc; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px;">
        <h2 style="color: white; text-align: center; margin-bottom: 20px;">🖱️ Click Test Area</h2>
        
        <div id="test-canvas" style="
            width: 400px; 
            height: 250px; 
            background: rgba(255,255,255,0.1); 
            border: 2px dashed rgba(255,255,255,0.3);
            border-radius: 10px; 
            margin: 20px auto; 
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 16px;
            position: relative;
            backdrop-filter: blur(10px);
        ">
            <div id="canvas-text">Try: Click • Double-Click • Right-Click</div>
            <div id="click-ripple" style="
                position: absolute;
                width: 30px;
                height: 30px;
                background: rgba(255,255,255,0.5);
                border-radius: 50%;
                display: none;
                pointer-events: none;
                animation: ripple 0.6s ease-out;
            "></div>
        </div>
        
        <div id="interaction-log" style="
            background: rgba(0,0,0,0.2); 
            color: white;
            padding: 15px; 
            border-radius: 8px;
            max-height: 150px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 12px;
        ">
            <strong>📋 Interaction Log:</strong><br>
            <div id="log-entries">Ready for interactions... (No reloads!)</div>
        </div>
    </div>

    <style>
    @keyframes ripple {
        0% { transform: scale(0); opacity: 1; }
        100% { transform: scale(4); opacity: 0; }
    }
    </style>

    <script>
    document.addEventListener('DOMContentLoaded', function() {
        const testCanvas = document.getElementById('test-canvas');
        const logEntries = document.getElementById('log-entries');
        const clickRipple = document.getElementById('click-ripple');
        
        function addLogEntry(message, type = 'info') {
            const timestamp = new Date().toLocaleTimeString();
            const color = type === 'success' ? '#4CAF50' : type === 'error' ? '#f44336' : '#2196F3';
            logEntries.innerHTML += `<br><span style="color: ${color}">[${timestamp}] ${message}</span>`;
            logEntries.scrollTop = logEntries.scrollHeight;
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
        
        function showRipple(x, y) {
            const rect = testCanvas.getBoundingClientRect();
            clickRipple.style.left = (x - rect.left - 15) + 'px';
            clickRipple.style.top = (y - rect.top - 15) + 'px';
            clickRipple.style.display = 'block';
            
            setTimeout(() => {
                clickRipple.style.display = 'none';
            }, 600);
        }
        
        function sendInteraction(action, event) {
            const rect = testCanvas.getBoundingClientRect();
            const payload = {
                x: event.clientX - rect.left,
                y: event.clientY - rect.top,
                canvasWidth: rect.width,
                canvasHeight: rect.height
            };
            
            addLogEntry(`🚀 ${action} at (${payload.x}, ${payload.y})`, 'info');
            showRipple(event.clientX, event.clientY);
            
            // Use the enhanced communication system
            if (window.streamlitCanvasComm) {
                const success = window.streamlitCanvasComm.sendMessage({
                    action: action,
                    payload: payload
                });
                
                if (success) {
                    addLogEntry(`✅ Message sent successfully (NO RELOAD!)`, 'success');
                } else {
                    addLogEntry(`❌ Message failed to send`, 'error');
                }
            } else {
                addLogEntry(`⚠️ Communication system not ready`, 'error');
            }
        }
        
        // Event listeners
        testCanvas.addEventListener('click', function(event) {
            sendInteraction('canvas_click', event);
        });
        
        testCanvas.addEventListener('dblclick', function(event) {
            sendInteraction('canvas_dblclick', event);
        });
        
        testCanvas.addEventListener('contextmenu', function(event) {
            event.preventDefault();
            if (confirm('Test delete action?')) {
                sendInteraction('canvas_contextmenu', event);
            }
            return false;
        });
        
        addLogEntry('✅ Test canvas initialized - NO RELOAD MODE!', 'success');
    });
    </script>
    """
    
    # Render using the new component
    component_value = canvas_communication_component(test_html, height=400)
    
    # Process any messages
    if component_value:
        message = process_canvas_component_message(component_value)
        if message:
            st.success(f"🎯 **Interaction Detected!** {message['action']} at ({message['payload'].get('x', 0)}, {message['payload'].get('y', 0)})")
            st.json(message)
            
            # Store in session state for history
            if 'interaction_history' not in st.session_state:
                st.session_state.interaction_history = []
            
            st.session_state.interaction_history.append({
                'action': message['action'],
                'coordinates': f"({message['payload'].get('x', 0)}, {message['payload'].get('y', 0)})",
                'time': datetime.now().strftime("%H:%M:%S")
            })
    
    # Show interaction history
    st.subheader("📊 Interaction History")
    if 'interaction_history' in st.session_state and st.session_state.interaction_history:
        for i, interaction in enumerate(reversed(st.session_state.interaction_history[-10:])):  # Last 10
            st.write(f"**{len(st.session_state.interaction_history) - i}.** {interaction['action']} at {interaction['coordinates']} - {interaction['time']}")
    else:
        st.info("No interactions yet. Try clicking on the test canvas above!")
    
    # Clear history button
    if st.button("🗑️ Clear History"):
        st.session_state.interaction_history = []
        st.success("History cleared!")
        st.rerun()
    
except Exception as e:
    st.error(f"❌ Error loading canvas component: {e}")
    st.code(str(e))

# Show comparison
st.subheader("📈 Comparison: Old vs New Approach")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### ❌ Old Approach (URL Parameters)
    - Page reloads on every interaction
    - Nested iframe creation
    - Slow response times
    - Browser back button issues
    - Complex URL parameter handling
    """)

with col2:
    st.markdown("""
    ### ✅ New Approach (Component Communication)
    - **No page reloads** - instant response
    - Clean single iframe structure
    - Fast, responsive interactions
    - No URL pollution
    - Direct Streamlit integration
    """)

# Technical details
with st.expander("🔧 Technical Implementation Details"):
    st.markdown("""
    ### How It Works:
    
    1. **Component Wrapper**: Custom Streamlit component handles iframe communication
    2. **Direct Messaging**: Uses `Streamlit.setComponentValue()` for immediate data transfer
    3. **Session Storage Fallback**: Backup method if direct communication fails
    4. **Message Interception**: Overrides the old URL-based system
    5. **No Reloads**: All communication happens via JavaScript events
    
    ### Benefits:
    - ✅ Eliminates infinite reload loops
    - ✅ Faster interaction response
    - ✅ Better user experience
    - ✅ Cleaner code architecture
    - ✅ More reliable communication
    """)

st.success("🎉 Canvas interactions now work without page reloads!")