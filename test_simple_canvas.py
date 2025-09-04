#!/usr/bin/env python3
"""
Simple Canvas Interaction Test

This test uses the most basic approach possible:
- Simple JavaScript event handling
- Session storage for data transfer
- Basic Streamlit session state
- No complex communication layers
"""

import streamlit as st
import json
from datetime import datetime

st.set_page_config(page_title="Simple Canvas Test", layout="wide")

st.title("🎯 Simple Canvas Interaction Test")

st.markdown("""
## Simplified Approach

This test uses the most straightforward method possible:

✅ **Simple JavaScript**: Basic event listeners on canvas  
✅ **Session Storage**: Simple data transfer mechanism  
✅ **Visual Feedback**: Status indicator shows interactions  
✅ **No Complex Layers**: Direct, minimal implementation  

**Instructions:**
1. Click anywhere on the test area below
2. Watch the status indicator in the top-right
3. Check the interaction log below
""")

# Simple test HTML
test_html = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { margin: 0; padding: 0; font-family: Arial, sans-serif; }
        #test-area {
            width: 100%;
            height: 400px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 24px;
            font-weight: bold;
            cursor: pointer;
            position: relative;
        }
        #status {
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: normal;
        }
        .click-ripple {
            position: absolute;
            width: 20px;
            height: 20px;
            background: rgba(255,255,255,0.6);
            border-radius: 50%;
            pointer-events: none;
            animation: ripple 0.6s ease-out;
        }
        @keyframes ripple {
            0% { transform: scale(0); opacity: 1; }
            100% { transform: scale(4); opacity: 0; }
        }
    </style>
</head>
<body>
    <div id="test-area">
        <div>Click Anywhere to Test</div>
        <div id="status">Ready...</div>
    </div>

    <script>
    let interactionCount = 0;
    
    function showStatus(message) {
        const status = document.getElementById('status');
        status.textContent = message;
        console.log('[TEST] ' + message);
        
        setTimeout(() => {
            status.textContent = 'Ready...';
        }, 2000);
    }
    
    function createRipple(x, y) {
        const ripple = document.createElement('div');
        ripple.className = 'click-ripple';
        ripple.style.left = (x - 10) + 'px';
        ripple.style.top = (y - 10) + 'px';
        
        document.getElementById('test-area').appendChild(ripple);
        
        setTimeout(() => {
            ripple.remove();
        }, 600);
    }
    
    function handleInteraction(event, actionType) {
        interactionCount++;
        
        const rect = event.target.getBoundingClientRect();
        const x = Math.round(event.clientX - rect.left);
        const y = Math.round(event.clientY - rect.top);
        
        // Create visual feedback
        createRipple(x, y);
        showStatus(`${actionType} #${interactionCount} at (${x}, ${y})`);
        
        // Store interaction data
        const interaction = {
            action: actionType,
            x: x,
            y: y,
            canvasWidth: Math.round(rect.width),
            canvasHeight: Math.round(rect.height),
            timestamp: Date.now(),
            count: interactionCount
        };
        
        try {
            // Store in session storage
            sessionStorage.setItem('simple_canvas_interaction', JSON.stringify(interaction));
            sessionStorage.setItem('simple_canvas_trigger', Date.now().toString());
            
            // Also try to communicate with parent
            if (window.parent && window.parent !== window) {
                window.parent.postMessage({
                    type: 'simple_canvas_interaction',
                    data: interaction
                }, '*');
            }
            
            console.log('Interaction stored:', interaction);
            
        } catch (e) {
            console.error('Failed to store interaction:', e);
            showStatus('Error: ' + e.message);
        }
    }
    
    // Set up event listeners
    document.addEventListener('DOMContentLoaded', function() {
        const testArea = document.getElementById('test-area');
        
        testArea.addEventListener('click', function(event) {
            handleInteraction(event, 'click');
        });
        
        testArea.addEventListener('dblclick', function(event) {
            event.preventDefault();
            handleInteraction(event, 'dblclick');
        });
        
        testArea.addEventListener('contextmenu', function(event) {
            event.preventDefault();
            handleInteraction(event, 'rightclick');
            return false;
        });
        
        showStatus('Test ready!');
        console.log('Simple canvas test initialized');
    });
    </script>
</body>
</html>
"""

# Render the test HTML
st.components.v1.html(test_html, height=420)

# Check for interactions
if 'simple_interaction_history' not in st.session_state:
    st.session_state.simple_interaction_history = []

# Simple interaction detection (this would be enhanced in the real implementation)
st.subheader("📊 Interaction Detection")

# Manual test buttons for demonstration
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🖱️ Simulate Click"):
        interaction = {
            'action': 'click',
            'x': 200,
            'y': 150,
            'timestamp': datetime.now().strftime("%H:%M:%S"),
            'source': 'manual'
        }
        st.session_state.simple_interaction_history.append(interaction)
        st.success("✅ Click interaction simulated!")
        st.rerun()

with col2:
    if st.button("🖱️🖱️ Simulate Double-Click"):
        interaction = {
            'action': 'dblclick',
            'x': 300,
            'y': 200,
            'timestamp': datetime.now().strftime("%H:%M:%S"),
            'source': 'manual'
        }
        st.session_state.simple_interaction_history.append(interaction)
        st.success("✅ Double-click interaction simulated!")
        st.rerun()

with col3:
    if st.button("🗑️ Clear History"):
        st.session_state.simple_interaction_history = []
        st.success("History cleared!")
        st.rerun()

# Show interaction history
if st.session_state.simple_interaction_history:
    st.subheader("📋 Interaction History")
    for i, interaction in enumerate(reversed(st.session_state.simple_interaction_history[-10:])):
        st.write(f"**{len(st.session_state.simple_interaction_history) - i}.** "
                f"{interaction['action']} at ({interaction.get('x', 0)}, {interaction.get('y', 0)}) "
                f"- {interaction['timestamp']} ({interaction.get('source', 'unknown')})")
else:
    st.info("No interactions recorded yet. Try clicking on the test area above!")

# Technical details
with st.expander("🔧 How This Works"):
    st.markdown("""
    ### Simple Implementation:
    
    1. **JavaScript Event Listeners**: Direct event handling on the test area
    2. **Session Storage**: Store interaction data in browser storage
    3. **Visual Feedback**: Immediate ripple effect and status updates
    4. **Streamlit Integration**: Manual buttons demonstrate the concept
    
    ### Benefits:
    - ✅ No complex communication layers
    - ✅ Immediate visual feedback
    - ✅ Simple debugging and testing
    - ✅ Easy to understand and maintain
    
    ### Next Steps:
    - Integrate with actual mind map canvas
    - Add automatic detection of session storage changes
    - Connect to node selection and editing functions
    """)

st.success("🎉 Simple canvas interaction test ready!")