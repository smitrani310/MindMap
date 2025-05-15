"""Node List component for the Enhanced Mind Map application."""

import streamlit as st
from src.state import get_ideas, set_ideas, get_central, set_central, save_data
from src.history import save_state_to_history
from src.utils import collect_descendants, find_node_by_id

def render_node_list():
    """
    Render the Node List section with filtering and action buttons for each node.
    """
    ideas = get_ideas()
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
            if col2.button("🎯", key=f"center_{node['id']}", help="Center this node", 
                          on_click=lambda id=node['id']: st.session_state.update({'center_node': id})):
                pass
            
            if col3.button("✏️", key=f"edit_{node['id']}", help="Edit this node",
                          on_click=lambda id=node['id']: st.session_state.update({'edit_node': id})):
                pass
            
            if col4.button("🗑️", key=f"delete_{node['id']}", help="Delete this node",
                          on_click=lambda id=node['id']: st.session_state.update({'delete_node': id})):
                pass

def handle_node_list_actions():
    """
    Handle button actions from the node list (center, edit, delete).
    """
    ideas = get_ideas()
    
    # Handle center node action
    if 'center_node' in st.session_state:
        node_id = st.session_state.pop('center_node')
        if node_id in {n['id'] for n in ideas if 'id' in n}:
            set_central(node_id)
            st.rerun()

    # Handle delete node action
    if 'delete_node' in st.session_state:
        node_id = st.session_state.pop('delete_node')
        if node_id in {n['id'] for n in ideas if 'id' in n}:
            save_state_to_history()
            
            # Use the utility function to collect descendants
            to_remove = collect_descendants(node_id, ideas)

            set_ideas([n for n in ideas if 'id' not in n or n['id'] not in to_remove])
            if get_central() in to_remove:
                set_central(None)
            if st.session_state.get('selected_node') in to_remove:
                st.session_state['selected_node'] = None
            st.rerun() 