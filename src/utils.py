# Utility functions for MindMap
import streamlit as st
from src.themes import URGENCY_SIZE, TAGS, THEMES, PRIMARY_NODE_BORDER, RGBA_ALPHA
import functools

# Cache for memoization
_size_cache = {}

def clear_size_cache():
    """Clear the size calculation cache"""
    global _size_cache
    _size_cache = {}

def hex_to_rgb(hex_color):
    """Convert hex color to RGB."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def get_theme(theme_name=None):
    """Get theme settings."""
    from src.state import get_current_theme
    theme_name = theme_name or get_current_theme()
    return THEMES.get(theme_name, THEMES['default'])

def recalc_size(node):
    """Calculate node size based on label length and urgency, with memoization."""
    if 'size' not in node:
        # Create a cache key from label and urgency
        label = node.get('label', '')
        urgency = node.get('urgency', 'medium')
        cache_key = f"{label}:{urgency}"
        
        # Check cache first
        if cache_key in _size_cache:
            node['size'] = _size_cache[cache_key]
        else:
            # Calculate if not in cache
            label_length = len(label)
            size = URGENCY_SIZE.get(urgency, 15) * (0.8 + min(1.0, label_length / 30.0))
            node['size'] = size
            
            # Cache the result
            _size_cache[cache_key] = size
            
            # Limit cache size to prevent memory issues
            if len(_size_cache) > 1000:
                clear_size_cache()

def get_edge_color(edge_type):
    """Get color for edge type with fallback for unknown types."""
    theme = get_theme()
    
    # Check if the edge_type exists in the theme
    if edge_type in theme.get('edge_colors', {}):
        return theme['edge_colors'][edge_type]
    
    # If edge_type isn't in this theme, try default edge type
    if 'default' in theme.get('edge_colors', {}):
        return theme['edge_colors']['default']
        
    # Ultimate fallback - gray
    return '#aaaaaa'

def get_urgency_color(urgency):
    """Get color for urgency level."""
    from src.state import get_store
    custom_colors = get_store().get('settings', {}).get('custom_colors', {}).get('urgency', {})
    if urgency in custom_colors:
        return custom_colors[urgency]
    return get_theme()['urgency_colors'].get(urgency, '#808080')

def get_tag_color(tag):
    """Get color for tag."""
    from src.state import get_store
    custom_colors = get_store().get('settings', {}).get('custom_colors', {}).get('tags', {})
    if tag in custom_colors:
        return custom_colors[tag]
    return TAGS.get(tag, {}).get('color', '#808080') 