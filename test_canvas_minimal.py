#!/usr/bin/env python3
"""
Minimal Canvas Test

Test the canvas rendering in isolation.
"""

import streamlit as st
import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

st.set_page_config(page_title="Minimal Canvas Test", layout="wide")

st.title("🔧 Minimal Canvas Test")

st.markdown("""
This test checks if the canvas rendering works in isolation.
""")

try:
    # Initialize the application first
    from src.application.app_lifecycle import get_lifecycle_manager
    
    st.write("🔄 Initializing application...")
    manager = get_lifecycle_manager()
    success = manager.initialize()
    
    if success:
        st.success("✅ Application initialized successfully")
        
        # Try to render the canvas
        st.write("🔄 Rendering canvas...")
        
        from src.ui.canvas import render_canvas
        render_canvas()
        
        st.success("✅ Canvas rendered successfully")
        
    else:
        st.error("❌ Failed to initialize application")
        
except Exception as e:
    st.error(f"❌ Error: {e}")
    import traceback
    st.code(traceback.format_exc())

st.markdown("""
**Expected behavior:**
- ✅ Application should initialize
- ✅ Canvas should render with network visualization
- ✅ Nodes should be visible in the network

**If this doesn't work:**
- Check the error details above
- Verify that all dependencies are installed
- Check if the data file exists and has nodes
""")