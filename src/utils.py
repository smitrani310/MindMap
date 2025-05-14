# Utility functions for MindMap
import streamlit as st
from src.themes import URGENCY_SIZE, TAGS, THEMES, PRIMARY_NODE_BORDER, RGBA_ALPHA
import functools
import logging
import colorsys
import re
from typing import Union, List, Dict, Any, Optional, Set, Tuple

# Cache for memoization
_size_cache = {}

def clear_size_cache():
    """Clear the size calculation cache"""
    global _size_cache
    _size_cache = {}

def collect_descendants(node_id, ideas, descendants=None):
    """Recursively collect all descendants of a node.
    
    Args:
        node_id: ID of the starting node
        ideas: List of all nodes
        descendants: Optional set to collect descendant IDs (used for recursion)
        
    Returns:
        Set of node IDs including the starting node and all descendants
    """
    if descendants is None:
        descendants = set()
    
    descendants.add(node_id)
    
    # Find all children of this node
    children = [n for n in ideas if 'id' in n and n.get('parent') == node_id]
    
    # Recursively add descendants
    for child in children:
        if child['id'] not in descendants:  # Avoid cycles
            collect_descendants(child['id'], ideas, descendants)
    
    return descendants

def compare_node_ids(id1: Any, id2: Any) -> bool:
    """Safely compare node IDs of potentially different types.
    
    Args:
        id1: First node ID to compare
        id2: Second node ID to compare
        
    Returns:
        True if the IDs represent the same node, False otherwise
    """
    # Try direct comparison first
    if id1 == id2:
        return True
    
    # Convert both to strings and compare
    if str(id1) == str(id2):
        return True
    
    # Try to convert both to integers and compare
    try:
        int_id1 = int(id1)
        int_id2 = int(id2)
        return int_id1 == int_id2
    except (ValueError, TypeError):
        pass
    
    # IDs are not equivalent
    return False

def find_node_by_id(ideas: List[Dict[str, Any]], node_id: Any) -> Optional[Dict[str, Any]]:
    """Find a node by its ID with flexible type handling.
    
    Args:
        ideas: List of all nodes
        node_id: ID to search for (can be string, int, etc.)
        
    Returns:
        The node dictionary if found, or None if not found
    """
    for node in ideas:
        if 'id' in node and compare_node_ids(node['id'], node_id):
            return node
    return None

def canvas_to_node_coordinates(canvas_x: Union[int, float], canvas_y: Union[int, float], 
                               canvas_width: Union[int, float], canvas_height: Union[int, float]) -> Tuple[float, float]:
    """Convert canvas coordinates to node coordinates.
    
    Canvas center maps to (0,0) in node coordinates.
    
    Args:
        canvas_x: X coordinate on canvas
        canvas_y: Y coordinate on canvas
        canvas_width: Width of the canvas
        canvas_height: Height of the canvas
        
    Returns:
        Tuple of (node_x, node_y)
    """
    node_x = float(canvas_x) - float(canvas_width)/2
    node_y = float(canvas_y) - float(canvas_height)/2
    return node_x, node_y
    
def node_to_canvas_coordinates(node_x: Union[int, float], node_y: Union[int, float], 
                               canvas_width: Union[int, float], canvas_height: Union[int, float]) -> Tuple[float, float]:
    """Convert node coordinates to canvas coordinates.
    
    Node position (0,0) maps to canvas center.
    
    Args:
        node_x: X coordinate in node space
        node_y: Y coordinate in node space
        canvas_width: Width of the canvas
        canvas_height: Height of the canvas
        
    Returns:
        Tuple of (canvas_x, canvas_y)
    """
    canvas_x = float(node_x) + float(canvas_width)/2
    canvas_y = float(node_y) + float(canvas_height)/2
    return canvas_x, canvas_y

def find_closest_node(ideas: List[Dict[str, Any]], click_x: Union[int, float], click_y: Union[int, float],
                      canvas_width: Union[int, float], canvas_height: Union[int, float]) -> Tuple[Optional[Dict[str, Any]], float, float]:
    """Find the closest node to the given click coordinates.
    
    Args:
        ideas: List of all nodes
        click_x: X coordinate on the canvas
        click_y: Y coordinate on the canvas
        canvas_width: Width of the canvas 
        canvas_height: Height of the canvas
        
    Returns:
        Tuple of (closest_node, min_distance, click_threshold) where:
        - closest_node: The node closest to the click coordinates, or None if no nodes found
        - min_distance: The distance to the closest node
        - click_threshold: The calculated threshold for considering a click "on" a node
    """
    logger = logging.getLogger(__name__)
    
    # Find the nearest node
    closest_node = None
    min_distance = float('inf')
    
    # Filter nodes with valid positions
    nodes_with_pos = [n for n in ideas if n.get('x') is not None and n.get('y') is not None]
    
    for node in nodes_with_pos:
        # Scale coordinates to match canvas
        node_x = node.get('x', 0)
        node_y = node.get('y', 0)
        
        node_canvas_x, node_canvas_y = node_to_canvas_coordinates(node_x, node_y, canvas_width, canvas_height)
        
        # Calculate Euclidean distance
        distance = ((node_canvas_x - click_x) ** 2 + (node_canvas_y - click_y) ** 2) ** 0.5
        
        logger.debug(f"Node {node.get('id')} distance from click: {distance:.2f}")
        
        if distance < min_distance:
            min_distance = distance
            closest_node = node
    
    # Calculate threshold based on canvas dimensions and node size
    base_threshold = min(canvas_width, canvas_height) * 0.08  # 8% of the smallest dimension
    node_size = closest_node.get('size', 20) if closest_node else 20
    click_threshold = base_threshold + node_size
    
    if closest_node:
        logger.debug(f"Closest node: {closest_node.get('id')} at distance {min_distance:.2f}, threshold: {click_threshold:.2f}")
    
    return closest_node, min_distance, click_threshold

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

def handle_error(e: Exception, logger: Optional[logging.Logger] = None, 
                message: Optional[str] = None, log_traceback: bool = True) -> str:
    """Standardized error handling utility.
    
    Provides a consistent way to handle exceptions across the application
    with proper logging and optional traceback.
    
    Args:
        e: The exception to handle
        logger: Optional logger instance. If not provided, creates a new one.
        message: Optional custom message prefix. If not provided, uses a default.
        log_traceback: Whether to log the full traceback. Default is True.
        
    Returns:
        Error message string suitable for user-facing error messages.
    """
    # Get logger if not provided
    if logger is None:
        logger = logging.getLogger(__name__)
    
    # Format the error message
    if message:
        error_msg = f"{message}: {str(e)}"
    else:
        error_msg = f"An error occurred: {str(e)}"
    
    # Log the error
    logger.error(error_msg)
    logger.error(f"Error type: {type(e).__name__}")
    
    # Log traceback if requested
    if log_traceback:
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    
    return error_msg 

def validate_node_exists(node_id: Any, ideas: List[Dict[str, Any]], action_name: str = "operation") -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """Validate that a node with the given ID exists.
    
    A common pattern in handlers for validating node existence before performing actions.
    
    Args:
        node_id: ID of the node to validate
        ideas: List of all nodes
        action_name: Name of the action being performed (for error message)
        
    Returns:
        Tuple of (success, node, error_message) where:
        - success: True if node exists, False otherwise
        - node: The node if found, None otherwise
        - error_message: Error message if node doesn't exist, None otherwise
    """
    node = find_node_by_id(ideas, node_id)
    
    if node:
        return True, node, None
    
    error_message = f"{action_name.capitalize()} request for nonexistent node: {node_id}"
    return False, None, error_message 

def validate_payload(payload: Dict[str, Any], required_fields: List[str] = None, field_types: Dict[str, type] = None) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """Validate message payload against required fields and types.
    
    A utility function for standardizing input validation across handlers.
    
    Args:
        payload: The payload dictionary to validate
        required_fields: List of field names that must be present
        field_types: Dictionary mapping field names to their expected types
        
    Returns:
        Tuple of (is_valid, error_message, validated_payload) where:
        - is_valid: True if validation passed, False otherwise
        - error_message: Error message if validation failed, None otherwise
        - validated_payload: The validated payload (may include type conversions)
    """
    logger = logging.getLogger(__name__)
    
    # Create a copy of the payload for validation
    validated = payload.copy() if payload else {}
    
    # Check for required fields
    if required_fields:
        for field in required_fields:
            if field not in validated:
                error_msg = f"Missing required field: {field}"
                logger.warning(error_msg)
                return False, error_msg, validated
    
    # Check field types if specified
    if field_types:
        for field, expected_type in field_types.items():
            # Skip fields that aren't present (they're handled by required_fields check)
            if field not in validated:
                continue
                
            # Skip None values unless the field is required
            if validated[field] is None:
                if required_fields and field in required_fields:
                    error_msg = f"Field '{field}' is required and cannot be None"
                    logger.warning(error_msg)
                    return False, error_msg, validated
                continue
            
            # Check if field value matches expected type
            if not isinstance(validated[field], expected_type):
                # Try to convert some common types
                try:
                    if expected_type is int:
                        validated[field] = int(validated[field])
                    elif expected_type is float:
                        validated[field] = float(validated[field])
                    elif expected_type is str:
                        validated[field] = str(validated[field])
                    elif expected_type is bool:
                        # Handle common string representations of bool
                        if isinstance(validated[field], str):
                            if validated[field].lower() in ('true', 'yes', '1', 'y'):
                                validated[field] = True
                            elif validated[field].lower() in ('false', 'no', '0', 'n'):
                                validated[field] = False
                            else:
                                raise ValueError(f"Cannot convert '{validated[field]}' to bool")
                        else:
                            validated[field] = bool(validated[field])
                    else:
                        # For other types, we can't do automatic conversion
                        error_msg = f"Field '{field}' has incorrect type: expected {expected_type.__name__}, got {type(validated[field]).__name__}"
                        logger.warning(error_msg)
                        return False, error_msg, validated
                except (ValueError, TypeError) as e:
                    error_msg = f"Cannot convert field '{field}' to {expected_type.__name__}: {str(e)}"
                    logger.warning(error_msg)
                    return False, error_msg, validated
    
    return True, None, validated 

def extract_canvas_coordinates(payload: Dict[str, Any]) -> Tuple[bool, Optional[str], Dict[str, float]]:
    """Extract and validate canvas coordinates from a message payload.
    
    Args:
        payload: The message payload containing coordinate data
        
    Returns:
        Tuple of (success, error_message, coordinates) where:
        - success: True if coordinates were valid, False otherwise
        - error_message: Error message if validation failed, None otherwise
        - coordinates: Dictionary containing x, y, canvasWidth, canvasHeight
    """
    logger = logging.getLogger(__name__)
    
    # Define required fields and types
    required_fields = ['x', 'y']
    field_types = {
        'x': float,
        'y': float,
        'canvasWidth': float,
        'canvasHeight': float
    }
    
    # Use the payload validation utility
    is_valid, error_msg, validated_payload = validate_payload(
        payload,
        required_fields=required_fields,
        field_types=field_types
    )
    
    if not is_valid:
        return False, error_msg, {}
    
    # Set default canvas dimensions if not provided
    if 'canvasWidth' not in validated_payload:
        validated_payload['canvasWidth'] = 800.0
        logger.debug("Canvas width not provided, using default (800)")
    
    if 'canvasHeight' not in validated_payload:
        validated_payload['canvasHeight'] = 600.0
        logger.debug("Canvas height not provided, using default (600)")
    
    # Extract only the coordinate-related fields
    coordinates = {
        'x': validated_payload['x'],
        'y': validated_payload['y'],
        'canvasWidth': validated_payload['canvasWidth'],
        'canvasHeight': validated_payload['canvasHeight']
    }
    
    logger.debug(f"Extracted canvas coordinates: ({coordinates['x']}, {coordinates['y']}) on {coordinates['canvasWidth']}x{coordinates['canvasHeight']} canvas")
    
    return True, None, coordinates 

def standard_response(message: Any, success: bool, error_message: Optional[str] = None, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a standardized response format.
    
    Args:
        message: The original message to respond to
        success: Whether the operation was successful
        error_message: Error message if operation failed
        data: Optional data to include in the response
        
    Returns:
        A standardized response dictionary ready to be sent
    """
    from src.message_format import create_response_message
    
    # Prepare the response data
    status = 'completed' if success else 'failed'
    
    # For errors, use error_message as payload
    if not success and error_message:
        return create_response_message(message, status, error_message)
    
    # For success with data, include data as payload
    if success and data:
        return create_response_message(message, status, None, data)
    
    # For simple success without data
    return create_response_message(message, status) 