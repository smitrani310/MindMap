"""Add Bubble form component for the Enhanced Mind Map application."""

import streamlit as st
from src.integration.service_adapter import get_service_adapter
from src.utils import recalc_size, get_theme
from src.themes import TAGS

def render_add_bubble_form():
    """
    Render the Add Bubble form in the sidebar, allowing users to add new nodes to the mind map.
    """
    with st.sidebar.form("add_bubble_form"):
        st.header("➕ Add Bubble")
        label = st.text_input("Label")
        description = st.text_area("Description (optional)", height=100)
        col1, col2 = st.columns(2)
        urgency = col1.selectbox("Urgency", list(get_theme()['urgency_colors'].keys()))
        
        # Get all tags, including custom ones
        adapter = get_service_adapter()
        if 'store' in st.session_state:
            settings = st.session_state['store'].get('settings', {})
            custom_tags = settings.get('custom_tags', [])
        else:
            custom_tags = []
        all_available_tags = [''] + list(TAGS.keys()) + custom_tags
        
        # Display the tags dropdown
        tag = col2.selectbox("Tag", all_available_tags)
        
        parent_label = st.text_input("Parent label (blank → current center)")
        edge_type = st.selectbox("Connection Type", list(get_theme()['edge_colors'].keys()))

        if st.form_submit_button("Add") and label:
            try:
                pid = None
                if parent_label.strip():
                    # Search for parent by label using the service adapter
                    ideas = adapter.get_ideas()
                    pid = next((i['id'] for i in ideas if i['label'].strip() == parent_label.strip()), None)
                    if pid is None:
                        st.warning("Parent not found; adding as top-level")
                elif adapter.get_central() is not None:
                    pid = adapter.get_central()

                # Generate random position for new nodes to avoid overlap
                import random
                random_x = random.randint(-200, 200)
                random_y = random.randint(-200, 200)
                
                new_node = {
                    'label': label.strip(),
                    'description': description,
                    'urgency': urgency,
                    'tag': tag,
                    'parent': pid,
                    'edge_type': edge_type if pid is not None else 'default',
                    'x': random_x,  # Random position to avoid overlap
                    'y': random_y
                }
                
                # Add the node using the service adapter
                success = adapter.add_idea(new_node)
                
                if success:
                    # If this is the first node and no central node is set, make it central
                    if adapter.get_central() is None:
                        ideas = adapter.get_ideas()
                        if len(ideas) == 1:  # This is the first node
                            first_node_id = ideas[0]['id']
                            adapter.set_central(first_node_id)
                            st.info(f"Set '{label}' as the central node!")
                    
                    st.success(f"Added '{label}' successfully!")
                    st.rerun()
                else:
                    st.error("Failed to add node. Please try again.")
                    
            except Exception as e:
                st.error(f"Error adding node: {str(e)}")
                import logging
                logging.getLogger(__name__).error(f"Error in add_bubble_form: {str(e)}") 