"""Node Edit Modal component for the Enhanced Mind Map application."""

import streamlit as st
from src.integration.service_adapter import get_service_adapter
from src.utils import get_theme, is_circular
from src.themes import TAGS

def render_node_edit_modal():
    """
    Render the node edit modal when a node is selected for editing.
    """
    adapter = get_service_adapter()
    
    if 'edit_node' in st.session_state and st.session_state['edit_node'] is not None:
        node_id = st.session_state['edit_node']
        node = adapter.find_node_by_id(node_id)

        if node:
            with st.form(key=f"edit_node_{node_id}"):
                st.subheader(f"Edit Node: {node.get('label', 'Untitled Node')}")
                new_label = st.text_input("Label", value=node.get('label', 'Untitled Node'))
                new_description = st.text_area("Description", value=node.get('description', ''), height=150)
                col1, col2 = st.columns(2)
                new_urgency = col1.selectbox("Urgency",
                                            list(get_theme()['urgency_colors'].keys()),
                                            index=list(get_theme()['urgency_colors'].keys()).index(node.get('urgency', 'low')))
                
                # Get all tags, including custom ones
                if 'store' in st.session_state:
                    settings = st.session_state['store'].get('settings', {})
                    custom_tags = settings.get('custom_tags', [])
                else:
                    custom_tags = []
                all_available_tags = [''] + list(TAGS.keys()) + custom_tags
                
                # Find the index of the current tag or default to empty
                current_tag = node.get('tag', '')
                tag_index = 0
                if current_tag in all_available_tags:
                    tag_index = all_available_tags.index(current_tag)
                
                new_tag = col2.selectbox("Tag",
                                        all_available_tags,
                                        index=tag_index)

                if node['parent'] is not None:
                    parent_node = adapter.find_node_by_id(node['parent'])
                    if parent_node:
                        current_parent = parent_node.get('label', 'Untitled Node')
                    else:
                        current_parent = ""
                    new_parent = st.text_input("Parent label (blank → no parent)", value=current_parent)
                    new_edge_type = st.selectbox("Connection Type",
                                                list(get_theme()['edge_colors'].keys()),
                                                index=list(get_theme()['edge_colors'].keys()).index(node.get('edge_type', 'default')) 
                                                    if node.get('edge_type', 'default') in get_theme()['edge_colors'] 
                                                    else 0)
                else:
                    new_parent = st.text_input("Parent label (blank → no parent)")
                    new_edge_type = st.selectbox("Connection Type", list(get_theme()['edge_colors'].keys()))

                # Form buttons - ensure we have submit buttons
                col1, col2 = st.columns(2)
                submitted = col1.form_submit_button("Save Changes")
                cancelled = col2.form_submit_button("Cancel")
                
                # Handle form submission logic after the form
                if submitted:
                    # Create update data
                    update_data = {
                        'label': new_label,
                        'description': new_description,
                        'urgency': new_urgency,
                        'tag': new_tag
                    }

                    # Handle parent relationship
                    if new_parent.strip():
                        ideas = adapter.get_ideas()
                        new_pid = next((i['id'] for i in ideas if i['label'].strip() == new_parent.strip()), None)
                        if new_pid is not None and new_pid != node['id']:  # Prevent self-reference
                            if not is_circular(node['id'], new_pid, ideas):
                                update_data['parent'] = new_pid
                                update_data['edge_type'] = new_edge_type
                            else:
                                st.warning("Cannot create circular parent-child relationships")
                        elif new_pid == node['id']:
                            st.warning("Cannot set a node as its own parent.")
                    else:
                        update_data['parent'] = None
                        update_data['edge_type'] = 'default'

                    # Update the node using the service adapter
                    success = adapter.update_node(node['id'], update_data)
                    if success:
                        st.success(f"Successfully updated node: {new_label}")
                        st.session_state['edit_node'] = None
                        st.rerun()
                    else:
                        st.error("Failed to update node. Please try again.")

                if cancelled:
                    st.session_state['edit_node'] = None
                    st.rerun() 