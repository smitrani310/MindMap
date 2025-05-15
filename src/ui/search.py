"""Search component for the Enhanced Mind Map application."""

import streamlit as st
import logging
from src.state import get_ideas, get_store, save_data
from src.history import save_state_to_history

logger = logging.getLogger(__name__)

def render_search():
    """
    Render the search and replace functionality in the sidebar.
    """
    search_col1, search_col2 = st.sidebar.columns([3, 1])
    search_q = search_col1.text_input("🔍 Search nodes")
    search_replace = search_col2.checkbox("Replace")

    if search_replace and search_q:
        replace_q = st.sidebar.text_input("Replace with")
        if st.sidebar.button("Replace All"):
            ideas = get_ideas()
            if ideas:
                save_state_to_history()
                count = 0
                for node in ideas:
                    if search_q.lower() in node.get('label', 'Untitled Node').lower():
                        node['label'] = node.get('label', 'Untitled Node').replace(search_q, replace_q)
                        count += 1
                    if 'description' in node and search_q.lower() in node['description'].lower():
                        node['description'] = node['description'].replace(search_q, replace_q)
                        count += 1
                st.sidebar.success(f"Replaced {count} instances")
                logger.info(f"Search and replace: '{search_q}' to '{replace_q}' - {count} instances replaced")
                if count > 0:
                    save_data(get_store())
                    st.rerun() 