"""Header component for the Enhanced Mind Map application."""

import streamlit as st
from src.state import get_current_theme

def render_header():
    """
    Render the application header, including the title and theme-specific styling.
    """
    # Apply theme to page
    current_theme = get_current_theme()
    if current_theme == 'dark':
        st.markdown("""
        <style>
        .stApp {
            background-color: #2E3440;
            color: #D8DEE9;
        }
        .stSidebar {
            background-color: #3B4252;
        }
        /* Remove canvas frame */
        iframe {
            border: none !important;
            box-shadow: none !important;
            background-color: transparent !important;
        }
        </style>
        """, unsafe_allow_html=True)
    else:
        # For light theme, only remove the frame but keep the theme
        st.markdown("""
        <style>
        /* Remove canvas frame */
        iframe {
            border: none !important;
            box-shadow: none !important;
            background-color: transparent !important;
        }
        </style>
        """, unsafe_allow_html=True)

    st.title("🧠 Enhanced Mind Map") 