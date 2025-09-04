#!/usr/bin/env python3
"""
Debug Canvas Loading

This script helps debug why the canvas isn't loading properly.
We'll start with the most basic approach and build up.
"""

import streamlit as st
import logging

st.set_page_config(page_title="Debug Canvas Loading", layout="wide")

st.title("🔍 Debug Canvas Loading")

st.markdown("""
Let's debug why the canvas isn't loading properly by testing different approaches:
""")

# Test 1: Basic HTML component
st.subheader("Test 1: Basic HTML Component")

basic_html = """
<div style="width: 100%; height: 200px; background: #007acc; color: white; display: flex; align-items: center; justify-content: center; font-size: 20px;">
    Basic HTML Test - If you see this, HTML components work
</div>
"""

try:
    st.components.v1.html(basic_html, height=220)
    st.success("✅ Basic HTML component loaded successfully")
except Exception as e:
    st.error(f"❌ Basic HTML component failed: {e}")

# Test 2: HTML with JavaScript
st.subheader("Test 2: HTML with JavaScript")

js_html = """
<div id="js-test" style="width: 100%; height: 200px; background: #28a745; color: white; display: flex; align-items: center; justify-content: center; font-size: 20px;">
    JavaScript Test - Click me!
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
    const div = document.getElementById('js-test');
    div.addEventListener('click', function() {
        div.innerHTML = 'JavaScript Works! ✅';
        div.style.background = '#ffc107';
        div.style.color = '#000';
    });
    console.log('JavaScript test ready');
});
</script>
"""

try:
    st.components.v1.html(js_html, height=220)
    st.success("✅ HTML with JavaScript loaded successfully")
except Exception as e:
    st.error(f"❌ HTML with JavaScript failed: {e}")

# Test 3: Try to load the actual mind map
st.subheader("Test 3: Mind Map Network")

try:
    from src.ui.network_visualization import render_network_visualization
    st.write("Attempting to render network visualization...")
    render_network_visualization("400px")
    st.success("✅ Network visualization loaded successfully")
except Exception as e:
    st.error(f"❌ Network visualization failed: {e}")
    st.code(str(e))
    
    # Show more details
    import traceback
    st.code(traceback.format_exc())

# Test 4: Check if PyVis works
st.subheader("Test 4: PyVis Network Test")

try:
    from pyvis.network import Network
    
    # Create a simple test network
    net = Network(height="300px", width="100%", bgcolor="#f0f0f0")
    
    # Add some test nodes
    net.add_node(1, label="Node 1", color="#ff6b6b")
    net.add_node(2, label="Node 2", color="#4ecdc4")
    net.add_node(3, label="Node 3", color="#45b7d1")
    
    # Add edges
    net.add_edge(1, 2)
    net.add_edge(2, 3)
    
    # Generate HTML
    html_content = net.generate_html()
    
    # Display it
    st.components.v1.html(html_content, height=320)
    st.success("✅ PyVis network test successful")
    
except Exception as e:
    st.error(f"❌ PyVis network test failed: {e}")
    st.code(str(e))

# Test 5: Check service adapter
st.subheader("Test 5: Service Adapter Test")

try:
    from src.integration.service_adapter import get_service_adapter
    adapter = get_service_adapter()
    ideas = adapter.get_ideas()
    
    st.write(f"Found {len(ideas)} nodes in the mind map:")
    for idea in ideas[:3]:  # Show first 3
        st.write(f"- **{idea.get('label', 'Untitled')}** at ({idea.get('x', 0)}, {idea.get('y', 0)})")
    
    st.success("✅ Service adapter working correctly")
    
except Exception as e:
    st.error(f"❌ Service adapter failed: {e}")
    st.code(str(e))

# Test 6: Manual network creation
st.subheader("Test 6: Manual Network Creation")

try:
    from pyvis.network import Network
    from src.integration.service_adapter import get_service_adapter
    
    # Get data
    adapter = get_service_adapter()
    ideas = adapter.get_ideas()
    
    if ideas:
        # Create network
        net = Network(height="400px", width="100%", bgcolor="#ffffff")
        
        # Add nodes
        for idea in ideas:
            net.add_node(
                idea['id'], 
                label=idea.get('label', 'Untitled'),
                color="#4ecdc4",
                size=20
            )
        
        # Add edges
        for idea in ideas:
            if idea.get('parent') and idea['parent'] in [n['id'] for n in ideas]:
                net.add_edge(idea['parent'], idea['id'])
        
        # Generate and display
        html_content = net.generate_html()
        st.components.v1.html(html_content, height=420)
        st.success("✅ Manual network creation successful")
    else:
        st.warning("⚠️ No nodes found in mind map data")
        
except Exception as e:
    st.error(f"❌ Manual network creation failed: {e}")
    st.code(str(e))

# Diagnostic information
st.subheader("🔧 Diagnostic Information")

col1, col2 = st.columns(2)

with col1:
    st.write("**Python Environment:**")
    try:
        import sys
        st.write(f"- Python version: {sys.version}")
        
        import streamlit
        st.write(f"- Streamlit version: {streamlit.__version__}")
        
        import pyvis
        st.write(f"- PyVis version: {pyvis.__version__}")
        
    except Exception as e:
        st.write(f"Error getting versions: {e}")

with col2:
    st.write("**File System:**")
    try:
        import os
        st.write(f"- Current directory: {os.getcwd()}")
        
        # Check if key files exist
        key_files = [
            "src/ui/network_visualization.py",
            "src/integration/service_adapter.py",
            "mindmap_data.json"
        ]
        
        for file in key_files:
            exists = os.path.exists(file)
            st.write(f"- {file}: {'✅' if exists else '❌'}")
            
    except Exception as e:
        st.write(f"Error checking files: {e}")

# Instructions
st.subheader("📋 What to Check")

st.markdown("""
**If tests are failing:**

1. **Test 1 fails**: Basic Streamlit components not working
2. **Test 2 fails**: JavaScript execution blocked
3. **Test 3 fails**: Network visualization has issues
4. **Test 4 fails**: PyVis library problems
5. **Test 5 fails**: Service adapter or data issues
6. **Test 6 fails**: Data loading or network creation issues

**Next steps based on results:**
- If all tests pass: Canvas interactions should work
- If PyVis tests fail: Check PyVis installation
- If service adapter fails: Check data file and imports
- If JavaScript fails: Check browser security settings
""")

st.info("👆 Run through these tests to identify where the canvas loading is failing")