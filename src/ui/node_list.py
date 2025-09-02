"""Node List component for the Enhanced Mind Map application."""

import streamlit as st
from src.integration.service_adapter import get_service_adapter

def render_node_list():
    """
    Render the Node List section with filtering and action buttons for each node.
    """
    adapter = get_service_adapter()
    ideas = adapter.get_ideas()
    if not ideas:
        return
        
    # Add custom CSS for better button alignment
    st.markdown("""
    <style>
    div[data-testid="column"] > div > div > div > div > div[data-testid="stButton"] > button {
        width: 100%;
        padding: 0px 5px;
        display: flex;
        justify-content: center;
    }
    </style>
    """, unsafe_allow_html=True)
    
    with st.sidebar.expander("✏️ Node List"):
        # Add search bar inside Node List
        node_search = st.text_input("🔍 Filter nodes", key="node_list_search")
        
        # Filter nodes based on search
        filtered_ideas = ideas
        if node_search:
            filtered_ideas = [
                node for node in ideas 
                if node_search.lower() in node.get('label', 'Untitled Node').lower() or 
                (node.get('description') and node_search.lower() in node['description'].lower()) or
                (node.get('tag') and node_search.lower() in node['tag'].lower())
            ]
            
            if not filtered_ideas:
                st.info(f"No nodes match '{node_search}'")
        
        # Display count of filtered nodes
        if node_search and filtered_ideas:
            st.caption(f"Showing {len(filtered_ideas)} of {len(ideas)} nodes")
        
        # List the filtered nodes
        for node in filtered_ideas:
            # Skip any malformed nodes without an ID
            if 'id' not in node:
                continue
                
            # More balanced column widths for better alignment
            col1, col2, col3, col4 = st.columns([2.5, 1, 1, 1])
            label_display = node.get('label', 'Untitled Node')
            if node.get('tag'):
                label_display = f"[{node['tag']}] {label_display}"
            col1.write(label_display)
            
            # Use smaller emoji icons for better alignment with proper classes
            if col2.button("🎯", key=f"center_{node['id']}", help="Center this node"):
                st.session_state['center_node'] = node['id']
                st.rerun()
            
            if col3.button("✏️", key=f"edit_{node['id']}", help="Edit this node"):
                st.session_state['edit_node'] = node['id']
                st.rerun()
            
            if col4.button("🗑️", key=f"delete_{node['id']}", help="Delete this node"):
                st.session_state['delete_node'] = node['id']
                st.rerun()

def handle_node_list_actions():
    """
    Handle button actions from the node list (center, edit, delete).
    
    Note: The actual handling is now done in main_new.py using the service adapter.
    This function is kept for backward compatibility but the logic has been moved.
    """
    # The actual handling is now done in main_new.py handle_ui_actions()
    # using the service adapter for proper architecture integration
    pass 