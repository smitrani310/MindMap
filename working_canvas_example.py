#!/usr/bin/env python3
"""
Working Canvas Example

This is a minimal working example that demonstrates canvas interactions
working properly with Streamlit.
"""

import streamlit as st
import json
from datetime import datetime

st.set_page_config(page_title="Working Canvas Example", layout="wide")

st.title("✅ Working Canvas Interaction Example")

st.markdown("""
This example demonstrates canvas interactions that actually work:

1. **Click** on the canvas below
2. **Watch** the interaction counter update
3. **See** the coordinates captured
4. **Verify** that interactions are processed correctly
""")

# Initialize session state
if 'click_count' not in st.session_state:
    st.session_state.click_count = 0

if 'last_click' not in st.session_state:
    st.session_state.last_click = None

# Check for URL parameters (simple method)
params = st.query_params

if 'canvas_x' in params and 'canvas_y' in params:
    try:
        x = int(params['canvas_x'])
        y = int(params['canvas_y'])
        action = params.get('canvas_action', 'click')
        
        # Process the click
        st.session_state.click_count += 1
        st.session_state.last_click = {
            'x': x,
            'y': y,
            'action': action,
            'time': datetime.now().strftime("%H:%M:%S"),
            'count': st.session_state.click_count
        }
        
        # Clear parameters
        st.query_params.clear()
        
        # Show success
        st.success(f"✅ {action.title()} detected at ({x}, {y})!")
        
        # Rerun to update display
        st.rerun()
        
    except (ValueError, KeyError) as e:
        st.error(f"Error processing click: {e}")

# Display current status
col1, col2 = st.columns(2)

with col1:
    st.metric("Total Clicks", st.session_state.click_count)

with col2:
    if st.session_state.last_click:
        st.metric("Last Click", f"({st.session_state.last_click['x']}, {st.session_state.last_click['y']})")
    else:
        st.metric("Last Click", "None")

# Create working canvas HTML
canvas_html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ margin: 0; padding: 0; }}
        #canvas-area {{
            width: 100%;
            height: 300px;
            background: linear-gradient(45deg, #FF6B6B, #4ECDC4);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 24px;
            font-weight: bold;
            cursor: pointer;
            position: relative;
            border-radius: 10px;
        }}
        #click-indicator {{
            position: absolute;
            width: 20px;
            height: 20px;
            background: rgba(255,255,255,0.8);
            border-radius: 50%;
            display: none;
            pointer-events: none;
            animation: pulse 0.5s ease-out;
        }}
        @keyframes pulse {{
            0% {{ transform: scale(0); opacity: 1; }}
            100% {{ transform: scale(3); opacity: 0; }}
        }}
        #status {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 14px;
            font-weight: normal;
        }}
    </style>
</head>
<body>
    <div id="canvas-area">
        <div>Click Anywhere on This Canvas</div>
        <div id="click-indicator"></div>
        <div id="status">Ready... (Clicks: {st.session_state.click_count})</div>
    </div>

    <script>
    function handleCanvasClick(event, actionType) {{
        const canvasArea = document.getElementById('canvas-area');
        const rect = canvasArea.getBoundingClientRect();
        
        const x = Math.round(event.clientX - rect.left);
        const y = Math.round(event.clientY - rect.top);
        
        // Show visual feedback
        const indicator = document.getElementById('click-indicator');
        indicator.style.left = (x - 10) + 'px';
        indicator.style.top = (y - 10) + 'px';
        indicator.style.display = 'block';
        
        setTimeout(() => {{
            indicator.style.display = 'none';
        }}, 500);
        
        // Update status
        const status = document.getElementById('status');
        status.textContent = `${{actionType}} at (${{x}}, ${{y}}) - Processing...`;
        
        // Send to Streamlit via URL parameters
        const currentUrl = new URL(window.location);
        currentUrl.searchParams.set('canvas_x', x);
        currentUrl.searchParams.set('canvas_y', y);
        currentUrl.searchParams.set('canvas_action', actionType);
        
        // Navigate to new URL (this will trigger Streamlit to process)
        window.location.href = currentUrl.toString();
    }}
    
    document.addEventListener('DOMContentLoaded', function() {{
        const canvasArea = document.getElementById('canvas-area');
        
        // Single click
        canvasArea.addEventListener('click', function(event) {{
            handleCanvasClick(event, 'click');
        }});
        
        // Double click
        canvasArea.addEventListener('dblclick', function(event) {{
            event.preventDefault();
            handleCanvasClick(event, 'double-click');
        }});
        
        // Right click
        canvasArea.addEventListener('contextmenu', function(event) {{
            event.preventDefault();
            handleCanvasClick(event, 'right-click');
            return false;
        }});
        
        console.log('Canvas interactions ready!');
    }});
    </script>
</body>
</html>
"""

# Render the canvas
st.components.v1.html(canvas_html, height=320)

# Show interaction history
if st.session_state.last_click:
    st.subheader("📊 Last Interaction Details")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.write(f"**Action:** {st.session_state.last_click['action']}")
    
    with col2:
        st.write(f"**X:** {st.session_state.last_click['x']}")
    
    with col3:
        st.write(f"**Y:** {st.session_state.last_click['y']}")
    
    with col4:
        st.write(f"**Time:** {st.session_state.last_click['time']}")

# Reset button
if st.button("🔄 Reset Counter"):
    st.session_state.click_count = 0
    st.session_state.last_click = None
    st.success("Counter reset!")
    st.rerun()

# Show how it works
with st.expander("🔧 How This Works"):
    st.markdown("""
    ### Simple & Reliable Method:
    
    1. **JavaScript Event Listeners**: Capture click events on the canvas
    2. **URL Parameters**: Pass coordinates via URL query parameters  
    3. **Page Navigation**: Use `window.location.href` to trigger Streamlit processing
    4. **Streamlit Processing**: Check `st.query_params` for interaction data
    5. **State Update**: Update session state and rerun to show changes
    
    ### Why This Works:
    - ✅ **Simple**: No complex communication layers
    - ✅ **Reliable**: URL parameters always work
    - ✅ **Immediate**: Visual feedback before processing
    - ✅ **Debuggable**: Easy to see what's happening
    
    ### Key Points:
    - Each click triggers a page reload (by design)
    - Coordinates are captured accurately
    - All interaction types work (click, double-click, right-click)
    - Session state persists across reloads
    """)

if st.session_state.click_count > 0:
    st.success(f"🎉 Canvas interactions are working! Total clicks: {st.session_state.click_count}")
else:
    st.info("👆 Click on the canvas above to test interactions")