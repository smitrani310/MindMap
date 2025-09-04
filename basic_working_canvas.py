#!/usr/bin/env python3
"""
Basic Working Canvas

This creates the most basic working canvas with mind map nodes.
No complex interactions - just get the canvas displaying first.
"""

import streamlit as st
from pyvis.network import Network

st.set_page_config(page_title="Basic Working Canvas", layout="wide")

st.title("🎯 Basic Working Canvas")

st.markdown("Let's start with the most basic canvas that actually displays:")

# Create a simple network
try:
    # Initialize network
    net = Network(
        height="500px", 
        width="100%", 
        bgcolor="#ffffff",
        font_color="#333333"
    )
    
    # Try to get real data
    try:
        from src.integration.service_adapter import get_service_adapter
        adapter = get_service_adapter()
        ideas = adapter.get_ideas()
        
        if ideas:
            st.success(f"✅ Found {len(ideas)} nodes in mind map data")
            
            # Add real nodes
            for idea in ideas:
                net.add_node(
                    idea['id'],
                    label=idea.get('label', f"Node {idea['id']}"),
                    color="#4ecdc4",
                    size=25,
                    title=idea.get('description', idea.get('label', ''))
                )
            
            # Add edges
            for idea in ideas:
                parent_id = idea.get('parent')
                if parent_id and parent_id in [n['id'] for n in ideas]:
                    net.add_edge(parent_id, idea['id'], color="#cccccc")
        else:
            st.warning("No nodes found, creating sample data")
            raise Exception("No data")
            
    except Exception as e:
        st.warning(f"Could not load real data ({e}), using sample data")
        
        # Create sample nodes
        sample_nodes = [
            {"id": 1, "label": "Central Idea", "color": "#ff6b6b"},
            {"id": 2, "label": "Branch 1", "color": "#4ecdc4"},
            {"id": 3, "label": "Branch 2", "color": "#45b7d1"},
            {"id": 4, "label": "Sub-idea 1", "color": "#96ceb4"},
            {"id": 5, "label": "Sub-idea 2", "color": "#feca57"}
        ]
        
        for node in sample_nodes:
            net.add_node(node["id"], label=node["label"], color=node["color"], size=25)
        
        # Add sample edges
        net.add_edge(1, 2)
        net.add_edge(1, 3)
        net.add_edge(2, 4)
        net.add_edge(3, 5)
    
    # Configure physics
    net.barnes_hut(
        gravity=-80000,
        central_gravity=0.3,
        spring_length=100,
        spring_strength=0.05,
        damping=0.09,
        overlap=0
    )
    
    # Generate HTML
    html_content = net.generate_html()
    
    # Display the network
    st.components.v1.html(html_content, height=520)
    
    st.success("✅ Basic canvas loaded successfully!")
    
    # Show the HTML content for debugging
    with st.expander("🔧 Debug: View Generated HTML"):
        st.code(html_content[:1000] + "..." if len(html_content) > 1000 else html_content, language="html")

except Exception as e:
    st.error(f"❌ Failed to create basic canvas: {e}")
    
    import traceback
    st.code(traceback.format_exc())

# Instructions
st.markdown("""
## 📋 What This Tests:

1. **PyVis Network Creation**: Can we create a basic network?
2. **Data Loading**: Can we load mind map data?
3. **HTML Generation**: Can PyVis generate HTML?
4. **Streamlit Display**: Can Streamlit display the HTML component?

If this works, we can add interactions step by step.
If this fails, we need to fix the basic canvas first.
""")

# Show system info
with st.expander("🔧 System Information"):
    try:
        import sys
        import pyvis
        import streamlit as st_version
        
        st.write(f"**Python:** {sys.version}")
        st.write(f"**Streamlit:** {st_version.__version__}")
        st.write(f"**PyVis:** {pyvis.__version__}")
        
        # Check if we can import our modules
        try:
            from src.integration.service_adapter import get_service_adapter
            st.write("**Service Adapter:** ✅ Available")
        except Exception as e:
            st.write(f"**Service Adapter:** ❌ {e}")
        
    except Exception as e:
        st.write(f"Error getting system info: {e}")

st.info("👆 If you can see a network with nodes and edges above, the basic canvas is working!")