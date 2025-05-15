"""Undo/Redo component for the Enhanced Mind Map application."""

import streamlit as st
from src.state import get_store, save_data
from src.history import can_undo, can_redo, perform_undo, perform_redo

def render_undo_redo():
    """
    Render undo and redo buttons in the sidebar.
    """
    undo_col, redo_col = st.sidebar.columns(2)
    if undo_col.button("↩️ Undo", disabled=not can_undo()):
        if perform_undo():
            save_data(get_store())
            st.rerun()  # Force a complete rerun to update the network

    if redo_col.button("↪️ Redo", disabled=not can_redo()):
        if perform_redo():
            save_data(get_store())
            st.rerun()  # Force a complete rerun to update the network 