#!/usr/bin/env python3
"""
Simple Network Test

Test if the network visualization is working at all.
"""

import streamlit as st
from pyvis.network import Network
import tempfile
import os

st.set_page_config(page_title="Simple Network Test", layout="wide")

st.title("🔧 Simple Network Test")

st.markdown("""
This test creates a minimal network to see if PyVis and vis-network are working.
""")

# Create a simple network
net = Network(height="400px", width="100%", bgcolor="#222222", font_color="white")

# Add some test nodes
net.add_node(1, label="Node 1", color="red")
net.add_node(2, label="Node 2", color="blue")
net.add_node(3, label="Node 3", color="green")

# Add some edges
net.add_edge(1, 2)
net.add_edge(2, 3)
net.add_edge(3, 1)

# Generate HTML
try:
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        net.save_graph(f.name)
        
        # Read the HTML content
        with open(f.name, 'r') as html_file:
            html_content = html_file.read()
        
        # Clean up (skip on Windows due to file locking)
        try:
            os.unlink(f.name)
        except PermissionError:
            pass  # File will be cleaned up by system later
        
        st.success("✅ Network HTML generated successfully")
        
        # Show the network
        st.components.v1.html(html_content, height=450)
        
        # Show some debug info
        with st.expander("🔍 Debug Info"):
            st.write("**HTML Length:**", len(html_content))
            st.write("**Contains vis-network:**", "vis-network" in html_content or "vis.js" in html_content)
            st.write("**Contains vis.Network:**", "vis.Network" in html_content)
            
            # Show first 1000 characters of HTML
            st.code(html_content[:1000] + "..." if len(html_content) > 1000 else html_content)
        
except Exception as e:
    st.error(f"❌ Error creating network: {e}")
    import traceback
    st.code(traceback.format_exc())

st.markdown("""
**Expected behavior:**
- ✅ Network should display with 3 colored nodes
- ✅ Nodes should be connected in a triangle
- ✅ Network should be interactive (draggable, zoomable)

**If this doesn't work:**
- The issue is with PyVis or vis-network library loading
- Check if vis-network CDN is accessible
- Check browser console for JavaScript errors
""")