# Utility functions for MindMap
from src.themes import URGENCY_SIZE, TAGS, THEMES, PRIMARY_NODE_BORDER, RGBA_ALPHA

def hex_to_rgb(h):
    return tuple(int(h.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

def get_theme():
    from src.state import get_current_theme
    return THEMES[get_current_theme()]

def recalc_size(node):
    node['size'] = URGENCY_SIZE.get(node.get('urgency', 'low'), 120)

def get_edge_color(edge_type):
    return get_theme()['edge_colors'].get(edge_type, get_theme()['edge_colors']['default'])

def get_urgency_color(urgency):
    return get_theme()['urgency_colors'].get(urgency, get_theme()['urgency_colors']['low'])

def get_tag_color(tag):
    return TAGS.get(tag, '#808080') 