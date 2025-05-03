# Utility functions for MindMap
import streamlit as st
from src.themes import URGENCY_SIZE, TAGS, THEMES, PRIMARY_NODE_BORDER, RGBA_ALPHA
import functools
import logging
import colorsys
import re

# Cache for memoization
_size_cache = {}

def clear_size_cache():
    """Clear the size calculation cache"""
    global _size_cache
    _size_cache = {}

def hex_to_rgb(color_str):
    """Convert hex or HSL color to RGB."""
    logger = logging.getLogger(__name__)
    
    # Handle HSL format
    hsl_match = re.match(r'hsl\((\d+),\s*(\d+)%,\s*(\d+)%\)', color_str)
    if hsl_match:
        h, s, l = [int(x) for x in hsl_match.groups()]
        logger.debug(f"Converting HSL color: {color_str}")
        h /= 360
        s /= 100
        l /= 100
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        return (int(r*255), int(g*255), int(b*255))
    
    # Handle hex format
    try:
        hex_color = color_str.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    except ValueError as e:
        logger.error(f"Invalid color format: {color_str}")
        # Return a default gray color when conversion fails
        return (128, 128, 128)

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
    """Get color for tag, including custom tags."""
    from src.state import get_store
    
    # Skip processing for empty tags
    if not tag:
        return '#808080'  # Default gray
    
    logger = logging.getLogger(__name__)
    
    # Check custom colors first
    custom_colors = get_store().get('settings', {}).get('custom_colors', {}).get('tags', {})
    if tag in custom_colors:
        color = custom_colors[tag]
        logger.debug(f"Using custom color for tag '{tag}': {color}")
        return color
    
    # Check builtin tags from TAGS dictionary
    if tag in TAGS:
        color = TAGS[tag].get('color', '#808080')
        logger.debug(f"Using builtin color for tag '{tag}': {color}")
        return color
    
    # For a custom tag without a saved color, generate one based on the tag name
    hash_value = sum(ord(c) for c in tag)
    hue = hash_value % 360
    
    # Convert HSL to hex directly instead of returning HSL string
    h, s, l = hue/360.0, 0.7, 0.6
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    hex_color = "#{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(b*255))
    
    logger.debug(f"Generated hex color for tag '{tag}': {hex_color}")
    return hex_color 