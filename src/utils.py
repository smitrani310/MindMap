# Utility functions for MindMap
import streamlit as st
from src.themes import URGENCY_SIZE, TAGS, THEMES, PRIMARY_NODE_BORDER, RGBA_ALPHA

def hex_to_rgb(hex_color):
    """Convert hex color to RGB."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def get_theme():
    """Get the theme from settings."""
    from src.state import get_current_theme
    theme_name = get_current_theme()
    return THEMES.get(theme_name, THEMES['default'])

def recalc_size(node):
    """Calculate node size based on label length and urgency."""
    if 'size' not in node:
        label_length = len(node.get('label', ''))
        node['size'] = URGENCY_SIZE.get(node.get('urgency', 'medium'), 15) * (0.8 + min(1.0, label_length / 30.0))

def get_edge_color(edge_type):
    """Get color for edge type."""
    theme = get_theme()
    return theme['edge_colors'].get(edge_type, '#999999')

def get_urgency_color(urgency_level):
    """Get color for urgency level from settings."""
    from src.state import get_store
    
    store = get_store()
    custom_colors = store.get('settings', {}).get('custom_colors', {})
    
    # First check if there's a custom color set
    if 'urgency' in custom_colors and urgency_level in custom_colors['urgency']:
        return custom_colors['urgency'][urgency_level]
    
    # Fallback to theme colors
    theme = get_theme()
    return theme['urgency_colors'].get(urgency_level, '#cccccc')

def get_tag_color(tag):
    """Get color for tag from settings."""
    from src.state import get_store
    
    store = get_store()
    custom_colors = store.get('settings', {}).get('custom_colors', {})
    
    # First check if there's a custom color set
    if 'tags' in custom_colors and tag in custom_colors['tags']:
        return custom_colors['tags'][tag]
    
    # Fallback to default tag colors
    return TAGS.get(tag, {}).get('color', '#cccccc') 