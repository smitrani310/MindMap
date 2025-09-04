#!/usr/bin/env python3
"""
Network Visualization Test

Test the network visualization in isolation.
"""

import streamlit as st
import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

st.title("🔧 Network Visualization Test")

st.markdown("""
This test checks if the network visualization works with real data.
""")

# Initialize service adapter first
st.subheader("1. Initialize Service Adapter")
try:
    from src.integration.service_adapter import init_service_adapter
    adapter = init_service_adapter()
    ideas = adapter.get_ideas()
    central = adapter.get_central()
    
    st.success(f"✅ Service adapter initialized: {len(ideas)} ideas, central node: {central}")
    
    # Show the ideas
    with st.expander("📊 Ideas Data"):
        for idea in ideas:
            st.write(f"- **{idea.get('label', 'Untitled')}** (ID: {idea.get('id')}) at ({idea.get('x', 0)}, {idea.get('y', 0)})")
    
except Exception as e:
    st.error(f"❌ Service adapter error: {e}")
    import traceback
    st.code(traceback.format_exc())
    st.stop()

# Test network visualization
st.subheader("2. Test Network Visualization")
try:
    from src.ui.network_visualization import render_network_visualization
    
    st.write("🔄 Rendering network visualization...")
    render_network_visualization("600px")
    
    st.success("✅ Network visualization rendered")
    
except Exception as e:
    st.error(f"❌ Network visualization error: {e}")
    import traceback
    st.code(traceback.format_exc())

st.markdown("""
**Expected behavior:**
- ✅ Service adapter should load 5 ideas
- ✅ Network visualization should render with nodes visible
- ✅ Nodes should be interactive (clickable, draggable)

**If network doesn't show nodes:**
- Check browser console for JavaScript errors
- Verify that PyVis is generating proper HTML
- Check if vis-network library is loading correctly
""")