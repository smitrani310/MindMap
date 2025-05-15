"""Canvas expansion toggle component for the Enhanced Mind Map application."""

import streamlit as st
from src.state import get_store, save_data
from src.config import CANVAS_DIMENSIONS

def render_canvas_toggle():
    """
    Render the canvas expansion toggle button and handle the expansion state.
    
    Returns:
        int: The current canvas height based on expansion state
    """
    # Add canvas expansion toggle
    canvas_expanded = st.session_state.get('canvas_expanded', False)
    expand_button = st.button(
        "🔍 Expand Canvas" if not canvas_expanded else "🔍 Collapse Canvas", 
        key="canvas_expand_toggle_btn"
    )
    
    if expand_button:
        # Toggle canvas expansion
        canvas_expanded = not canvas_expanded
        # Update both session state and store
        st.session_state['canvas_expanded'] = canvas_expanded
        get_store()['settings']['canvas_expanded'] = canvas_expanded
        save_data(get_store())
        st.rerun()

    # Set canvas height based on expansion state
    canvas_height = CANVAS_DIMENSIONS['expanded' if canvas_expanded else 'normal']
    
    return canvas_height 