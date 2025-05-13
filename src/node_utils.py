"""Utilities for node validation and manipulation."""
import logging
import math

logger = logging.getLogger(__name__)

def validate_node(node, get_next_id_func, increment_next_id_func):
    """Validate and fix node structure to ensure all required fields are present.
    
    Args:
        node: Node dictionary to validate
        get_next_id_func: Function to get the next available node ID
        increment_next_id_func: Function to increment the next ID counter
        
    Returns:
        Validated and fixed node dictionary
    """
    # Ensure node is a dictionary
    if not isinstance(node, dict):
        # Create a minimal valid node if the input is invalid
        return {
            'id': get_next_id_func(),
            'label': 'Fixed Node',
            'parent': None,
            'description': '',
            'urgency': 'medium',
            'tag': '',
            'edge_type': 'default',
            'x': 0.0,
            'y': 0.0
        }
    
    # Check and add required fields if missing
    if 'id' not in node:
        node['id'] = get_next_id_func()
        increment_next_id_func()
        
    node.setdefault('label', 'Untitled Node')
    node.setdefault('parent', None)
    node.setdefault('description', '')
    node.setdefault('urgency', 'medium')
    node.setdefault('tag', '')
    node.setdefault('edge_type', 'default')
    
    # Log existing position values for debugging
    if 'x' in node or 'y' in node:
        logger.debug(f"Node {node.get('id')} existing position: x={node.get('x')}, y={node.get('y')}")
    
    # Ensure x and y are numbers, not None or strings
    # If values exist but are invalid, preserve them by converting to float
    if 'x' not in node or node['x'] is None:
        node['x'] = 0.0
    else:
        try:
            node['x'] = float(node['x'])
        except (ValueError, TypeError):
            logger.warning(f"Invalid x value for node {node.get('id')}: {node['x']}, defaulting to 0.0")
            node['x'] = 0.0
    
    if 'y' not in node or node['y'] is None:
        node['y'] = 0.0
    else:
        try:
            node['y'] = float(node['y'])
        except (ValueError, TypeError):
            logger.warning(f"Invalid y value for node {node.get('id')}: {node['y']}, defaulting to 0.0")
            node['y'] = 0.0
    
    # Log the updated position values
    logger.debug(f"Node {node.get('id')} validated position: x={node['x']}, y={node['y']}")
    
    # Ensure the id is an integer
    if not isinstance(node['id'], int):
        try:
            node['id'] = int(node['id'])
        except (ValueError, TypeError):
            # If conversion fails, assign a new valid ID
            node['id'] = get_next_id_func()
            increment_next_id_func()
    
    # Ensure parent is handled correctly - either None or an integer
    if node['parent'] is not None:
        try:
            node['parent'] = int(node['parent'])
        except (ValueError, TypeError):
            # If parent can't be converted to int, set to None
            node['parent'] = None
    
    return node

def update_node_position(node, x, y):
    """Update a node's position with proper type handling.
    
    Args:
        node: Node dictionary to update
        x: New x coordinate
        y: New y coordinate
        
    Returns:
        Updated node dictionary
    """
    if not isinstance(node, dict):
        logger.error("Cannot update position for invalid node")
        return node
    
    try:
        # Store original values for logging
        orig_x = node.get('x')
        orig_y = node.get('y')
        
        # Log the input values
        logger.info(f"🔍 Position update received - Node: {node.get('id', 'unknown')}, New pos: ({x}, {y}), Types: x={type(x).__name__}, y={type(y).__name__}")
        
        # Convert to float and update
        node['x'] = float(x)
        node['y'] = float(y)
        
        # Log with more detail
        logger.info(f"📝 Position updated for node {node.get('id', 'unknown')}: ({orig_x}, {orig_y}) -> ({node['x']}, {node['y']})")
        
        # Check for NaN values (important validation)
        if math.isnan(node['x']) or math.isnan(node['y']):
            logger.warning(f"NaN coordinates detected for node {node.get('id', 'unknown')}, resetting to origin")
            node['x'] = 0.0
            node['y'] = 0.0
            
        # Also check for zero coordinates - might indicate an issue
        if node['x'] == 0.0 and node['y'] == 0.0:
            logger.warning(f"⚠️ Zero coordinates (0, 0) detected after update for node {node.get('id', 'unknown')}. This might indicate a position is not being saved correctly.")
            
    except (ValueError, TypeError) as e:
        logger.error(f"Error updating position for node {node.get('id', 'unknown')}: {str(e)}")
        # Set default values if conversion fails
        node['x'] = 0.0
        node['y'] = 0.0
    
    return node 