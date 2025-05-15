"""Node Details component for the Enhanced Mind Map application."""

import streamlit as st
import logging
from src.state import get_central, get_ideas, get_store, set_central, save_data
from src.utils import find_node_by_id

logger = logging.getLogger(__name__)

def render_node_details():
    """
    Render the node details section for the selected or central node.
    """
    # Node details section for both central and selected nodes
    # Use only the central node approach
    display_node = None
    
    if get_central() is not None:
        central_id = get_central()
        logger.info(f"Using central node ID: {central_id}")
        display_node = find_node_by_id(get_ideas(), central_id)
        logger.info(f"Found node for central ID: {display_node is not None}")
    
    # Fallback: If no central node, pick the first node if available
    if display_node is None and get_ideas():
        # Find first node with a valid ID
        display_node = next((n for n in get_ideas() if 'id' in n), None)
        if display_node:
            selected_node_temp = display_node['id']
            logger.info(f"No central node, using fallback node ID: {selected_node_temp}")
            # Set as central node
            set_central(selected_node_temp)

    # Debug output for ideas
    logger.info(f"Total nodes in ideas: {len(get_ideas())}")
    if not get_ideas():
        logger.warning("No ideas/nodes found in the store")
    
    # Display color mode legend
    color_mode = get_store().get('settings', {}).get('color_mode', 'urgency')
    col1, col2 = st.columns([3, 1])
    with col1:
        if color_mode == 'urgency':
            st.write("🎨 **Color Mode:** Urgency-based")
        else:
            st.write("🎨 **Color Mode:** Tag-based")
    with col2:
        # Quick toggle button
        if st.button("Toggle Color Mode", key="node_details_toggle_color_mode_btn"):
            settings = get_store().get('settings', {})
            new_mode = 'tag' if color_mode == 'urgency' else 'urgency'
            settings['color_mode'] = new_mode
            save_data(get_store())
            st.rerun()

    if display_node:
        logger.info(f"Displaying node: {display_node['id']} - {display_node.get('label', 'Untitled Node')}")
        # Display node with a clean style, matching the center button approach
        st.subheader(f"📌 Selected: {display_node.get('label', 'Untitled Node')}")

        # Display node details
        if display_node.get('tag'):
            st.write(f"**Tag:** {display_node['tag']}")

        st.write(f"**Urgency:** {display_node.get('urgency', 'medium')}")

        if display_node.get('description'):
            st.markdown("**Description:**")
            st.markdown(display_node['description'])
        else:
            st.markdown("**Description:** *No description available*")

        # Display children
        children = [n for n in get_ideas() if n.get('parent') == display_node['id']]
        if children:
            st.markdown("**Connected Ideas:**")
            for child in children:
                st.markdown(f"- {child['label']} ({child.get('edge_type', 'default')} connection)")
        else:
            st.markdown("**Connected Ideas:** *None*")
    else:
        # If we still don't have a node to display, show a message
        logger.warning("No node available to display")
        st.warning("No node selected. Click on a node in the canvas to view its details.") 