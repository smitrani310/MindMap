"""Configuration settings for the Enhanced Mind Map application."""

# File paths
DATA_FILE = "mindmap_data.json"

# Default settings
DEFAULT_SETTINGS = {
    'edge_length': 100,
    'spring_strength': 0.5,
    'size_multiplier': 1.0,
    'canvas_expanded': False
}

# Network configuration
NETWORK_CONFIG = {
    'gravity': -2000,
    'central_gravity': 0.3,
    'spring_length': 50,
    'damping': 0.09,
    'overlap': 0
}

# Canvas dimensions
CANVAS_DIMENSIONS = {
    'normal': "650px",
    'expanded': "1000px"
}

# UI constants
PRIMARY_NODE_BORDER = 2
RGBA_ALPHA = 0.7

# Error messages
ERROR_MESSAGES = {
    'load_data': "Error loading data: {error}",
    'save_data': "Error saving data: {error}",
    'invalid_json': "Invalid JSON format",
    'file_not_found': "Data file not found",
    'permission_error': "Permission denied accessing data file"
} 