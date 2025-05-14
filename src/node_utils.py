"""Utilities for node validation and manipulation."""
import logging
import math
from typing import Dict, Any, Optional, Union, List
import streamlit as st
from src.utils import handle_error

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
    logger = logging.getLogger(__name__)
    
    # Ensure node is a dictionary
    if not isinstance(node, dict):
        logger.warning(f"Invalid node type: {type(node).__name__}, creating empty node")
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
    
    # Create a copy to avoid modifying the original
    validated = node.copy()
    original_id = validated.get('id')
    
    # Check and add required fields if missing
    if 'id' not in validated:
        logger.info("Node missing ID, assigning new ID")
        validated['id'] = get_next_id_func()
        increment_next_id_func()
    
    # Validate required string fields
    for field in ['label', 'description', 'urgency', 'tag', 'edge_type']:
        if field not in validated:
            logger.debug(f"Node {validated.get('id')} missing '{field}', setting default")
            validated[field] = '' if field in ['description', 'tag'] else \
                               'medium' if field == 'urgency' else \
                               'default' if field == 'edge_type' else \
                               'Untitled Node'
        elif validated[field] is None:
            logger.debug(f"Node {validated.get('id')} has None for '{field}', setting default")
            validated[field] = '' if field in ['description', 'tag'] else \
                               'medium' if field == 'urgency' else \
                               'default' if field == 'edge_type' else \
                               'Untitled Node'
    
    # Ensure label is not empty
    if not validated['label'].strip():
        logger.debug(f"Node {validated.get('id')} has empty label, setting default")
        validated['label'] = 'Untitled Node'
    
    # Ensure parent is properly handled
    if 'parent' not in validated:
        logger.debug(f"Node {validated.get('id')} missing 'parent', setting to None")
        validated['parent'] = None
    
    # Log existing position values for debugging
    if 'x' in validated or 'y' in validated:
        logger.debug(f"Node {validated.get('id')} existing position: x={validated.get('x')}, y={validated.get('y')}")
    
    # Validate and fix position coordinates
    for coord in ['x', 'y']:
        if coord not in validated or validated[coord] is None:
            logger.debug(f"Node {validated.get('id')} missing '{coord}', setting to 0.0")
            validated[coord] = 0.0
        else:
            try:
                validated[coord] = float(validated[coord])
                # Check for NaN or infinite values
                if math.isnan(validated[coord]) or math.isinf(validated[coord]):
                    logger.warning(f"Node {validated.get('id')} has invalid {coord} value: {validated[coord]}, setting to 0.0")
                    validated[coord] = 0.0
            except (ValueError, TypeError):
                logger.warning(f"Invalid {coord} value for node {validated.get('id')}: {validated[coord]}, setting to 0.0")
                validated[coord] = 0.0
    
    # Log the updated position values
    logger.debug(f"Node {validated.get('id')} validated position: x={validated['x']}, y={validated['y']}")
    
    # Ensure the id is an integer
    if not isinstance(validated['id'], int):
        try:
            logger.debug(f"Converting ID from {type(validated['id']).__name__} to int: {validated['id']}")
            validated['id'] = int(validated['id'])
        except (ValueError, TypeError):
            # If conversion fails, assign a new valid ID
            old_id = validated['id']
            validated['id'] = get_next_id_func()
            increment_next_id_func()
            logger.warning(f"Could not convert node ID '{old_id}' to integer, assigned new ID: {validated['id']}")
    
    # Ensure parent is handled correctly - either None or an integer
    if validated['parent'] is not None:
        try:
            validated['parent'] = int(validated['parent'])
        except (ValueError, TypeError):
            # If parent can't be converted to int, set to None
            logger.warning(f"Could not convert parent ID '{validated['parent']}' to integer for node {validated['id']}, setting parent to None")
            validated['parent'] = None
    
    # Log changes made during validation
    if original_id != validated['id']:
        logger.info(f"Node ID changed during validation: {original_id} → {validated['id']}")
    
    return validated

def update_node_position(node, x, y):
    """Update a node's position with proper type handling.
    
    Args:
        node: Node dictionary to update
        x: New x coordinate
        y: New y coordinate
        
    Returns:
        Updated node dictionary
    """
    logger = logging.getLogger(__name__)
    
    # Validate input data
    if not isinstance(node, dict):
        logger.error(f"Cannot update position: Invalid node type {type(node).__name__}, expected dict")
        return node
    
    if 'id' not in node:
        logger.error("Cannot update position: Node missing required 'id' field")
        return node
    
    node_id = node.get('id', 'unknown')
    
    try:
        # Store original values for logging and recovery
        orig_x = node.get('x')
        orig_y = node.get('y')
        
        # Validate coordinate inputs
        if x is None or y is None:
            logger.error(f"Cannot update position for node {node_id}: Coordinates cannot be None")
            return node
            
        # Convert to float with validation
        try:
            float_x = float(x)
            float_y = float(y)
        except (ValueError, TypeError) as e:
            logger.error(f"Cannot update position for node {node_id}: Invalid coordinate format: {str(e)}")
            return node
            
        # Check for invalid values
        if math.isnan(float_x) or math.isnan(float_y) or math.isinf(float_x) or math.isinf(float_y):
            logger.error(f"Cannot update position for node {node_id}: Invalid coordinate values: x={x}, y={y}")
            return node
        
        # Log the input values
        logger.info(f"🔍 Position update received - Node: {node_id}, New pos: ({float_x}, {float_y})")
        
        # Update the position
        node['x'] = float_x
        node['y'] = float_y
        
        # Log with more detail
        logger.info(f"📝 Position updated for node {node_id}: ({orig_x}, {orig_y}) -> ({node['x']}, {node['y']})")
        
        # Also check for zero coordinates - might indicate an issue
        if node['x'] == 0.0 and node['y'] == 0.0:
            logger.warning(f"⚠️ Zero coordinates (0, 0) detected after update for node {node_id}. This might indicate a position is not being saved correctly.")
            
    except Exception as e:
        error_msg = handle_error(e, logger, f"Error updating position for node {node_id}")
        # Restore original values if available
        if orig_x is not None and orig_y is not None:
            node['x'] = orig_x
            node['y'] = orig_y
            logger.info(f"Restored original position ({orig_x}, {orig_y}) for node {node_id} after error")
    
    return node

def update_node_position_service(node_id: Any, x: Any, y: Any, get_ideas_func, set_ideas_func, save_state_func, save_data_func, get_store_func) -> Dict[str, Any]:
    """Centralized service for updating node positions.
    
    This function handles all the steps needed to properly update a node's position:
    1. Find the node by ID with proper type handling
    2. Update the position with validation
    3. Save the state for undo capability
    4. Save the updated data
    
    Args:
        node_id: ID of the node to update
        x: New x coordinate
        y: New y coordinate
        get_ideas_func: Function to get all ideas/nodes
        set_ideas_func: Function to set all ideas/nodes
        save_state_func: Function to save state to history
        save_data_func: Function to save data to persistent storage
        get_store_func: Function to get the application state store
        
    Returns:
        Dictionary with success status and message
    """
    logger.info(f"Position service: Updating node {node_id} to position ({x}, {y})")
    
    # Input validation
    try:
        # Validate coordinates
        if x is None or y is None:
            return {
                'success': False,
                'message': f"Missing coordinates: x={x}, y={y}"
            }
            
        # Try converting to float - will raise exception if invalid
        float_x = float(x)
        float_y = float(y)
        
        # Check for NaN values
        if math.isnan(float_x) or math.isnan(float_y) or math.isinf(float_x) or math.isinf(float_y):
            return {
                'success': False,
                'message': f"Invalid coordinate values: x={x}, y={y}"
            }
    except (ValueError, TypeError) as e:
        logger.error(f"Position service: Invalid coordinate format: {str(e)}")
        return {
            'success': False,
            'message': f"Invalid coordinate format: {str(e)}"
        }
    
    # Get all ideas
    try:
        ideas = get_ideas_func()
        if ideas is None:
            logger.error("Position service: get_ideas_func returned None")
            return {
                'success': False,
                'message': "Could not retrieve nodes from storage"
            }
    except Exception as e:
        error_msg = handle_error(e, logger, "Position service: Error getting ideas")
        return {
            'success': False,
            'message': f"Error retrieving nodes: {str(e)}"
        }
    
    # Find the node
    from src.utils import find_node_by_id, validate_node_exists
    success, node, error_msg = validate_node_exists(node_id, ideas, 'position update')
    
    if not success:
        logger.warning(error_msg)
        return {
            'success': False,
            'message': f"Node with id {node_id} not found"
        }
    
    # Update the position
    old_x, old_y = node.get('x'), node.get('y')
    update_node_position(node, float_x, float_y)
    
    try:
        # Save state for undo capability
        save_state_func()
        
        # Save the updated data
        set_ideas_func(ideas)
        save_data_func(get_store_func())
        
        logger.info(f"Position service: Successfully updated node {node_id} from ({old_x}, {old_y}) to ({node['x']}, {node['y']})")
        
        return {
            'success': True,
            'message': f"Successfully updated position for node {node_id}",
            'node': node
        }
    except Exception as e:
        error_msg = handle_error(e, logger, "Position service: Error saving position update")
        return {
            'success': False,
            'message': error_msg
        } 