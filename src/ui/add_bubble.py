"""Add Bubble form component for the Enhanced Mind Map application."""

import streamlit as st
from src.state import get_store, get_ideas, get_central, get_next_id, increment_next_id, add_idea, save_data
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
        settings = get_store().get('settings', {})
        custom_tags = settings.get('custom_tags', [])
        all_available_tags = [''] + list(TAGS.keys()) + custom_tags
        
        # Display the tags dropdown
        tag = col2.selectbox("Tag", all_available_tags)
        
        parent_label = st.text_input("Parent label (blank → current center)")
        edge_type = st.selectbox("Connection Type", list(get_theme()['edge_colors'].keys()))

        if st.form_submit_button("Add") and label:
            pid = None
            if parent_label.strip():
                pid = next((i['id'] for i in get_ideas() if i['label'].strip() == parent_label.strip()), None)
                if pid is None:
                    st.warning("Parent not found; adding as top-level")
            elif get_central() is not None:
                pid = get_central()

            new_node = {
                'id': get_next_id(),
                'label': label.strip(),
                'description': description,
                'urgency': urgency,
                'tag': tag,
                'parent': pid,
                'edge_type': edge_type if pid is not None else 'default',
                'x': None,
                'y': None
            }
            recalc_size(new_node)
            add_idea(new_node)
            increment_next_id()
            save_data(get_store())
            st.rerun() 