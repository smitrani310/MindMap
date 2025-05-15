"""Keyboard shortcuts component for the Enhanced Mind Map application."""

import streamlit as st

def render_shortcuts():
    """
    Render the keyboard shortcuts information in the sidebar.
    """
    with st.sidebar.expander("⌨️ Keyboard Shortcuts"):
        st.markdown("""
        - **Double-click**: Edit node
        - **Right-click**: Delete node
        - **Drag**: Move node
        - **Drag near another**: Change parent
        - **Ctrl+Z**: Undo (when focused on canvas)
        - **Ctrl+Y**: Redo (when focused on canvas)
        - **Ctrl+N**: New node (when focused on canvas)
        """) 