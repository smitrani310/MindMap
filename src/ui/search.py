"""Search component for the Enhanced Mind Map application."""

import streamlit as st
import logging
from src.integration.service_adapter import get_service_adapter

logger = logging.getLogger(__name__)

def render_search():
    """
    Render the search and replace functionality in the sidebar.
    """
    adapter = get_service_adapter()
    
    search_col1, search_col2 = st.sidebar.columns([3, 1])
    search_q = search_col1.text_input("🔍 Search nodes")
    search_replace = search_col2.checkbox("Replace")

    if search_replace and search_q:
        replace_q = st.sidebar.text_input("Replace with")
        if st.sidebar.button("Replace All"):
            ideas = adapter.get_ideas()
            if ideas:
                count = 0
                updated_nodes = []
                
                for node in ideas:
                    node_updated = False
                    updated_node = node.copy()
                    
                    # Check and replace in label
                    if search_q.lower() in node.get('label', 'Untitled Node').lower():
                        updated_node['label'] = node.get('label', 'Untitled Node').replace(search_q, replace_q)
                        node_updated = True
                        count += 1
                    
                    # Check and replace in description
                    if 'description' in node and search_q.lower() in node['description'].lower():
                        updated_node['description'] = node['description'].replace(search_q, replace_q)
                        node_updated = True
                        count += 1
                    
                    if node_updated:
                        updated_nodes.append(updated_node)
                
                # Apply updates using service adapter
                if updated_nodes:
                    # Note: This is a bulk operation that would need to be implemented
                    # For now, we'll show the count but note that individual updates would be needed
                    st.sidebar.success(f"Found {count} instances to replace")
                    st.sidebar.warning("Bulk replace not yet implemented with new architecture")
                    logger.info(f"Search and replace: '{search_q}' to '{replace_q}' - {count} instances found")
                else:
                    st.sidebar.info("No matches found")
                    
                if count > 0:
                    st.rerun() 