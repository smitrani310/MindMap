# Position update utilities for MindMap application
import logging
from typing import Dict, Any, List, Optional, Callable, Union, Tuple

from src.utils import find_node_by_id, handle_error

logger = logging.getLogger(__name__)

def process_position_update(
    node_id: Union[str, int],
    x: Union[float, int],
    y: Union[float, int],
    get_ideas_func: Callable,
    set_ideas_func: Callable,
    save_state_func: Callable,
    save_data_func: Callable,
    get_store_func: Callable
) -> Dict[str, Any]:
    """Process a single node position update.
    
    Args:
        node_id: The ID of the node to update
        x: The new X coordinate
        y: The new Y coordinate
        get_ideas_func: Function to get all nodes
        set_ideas_func: Function to update nodes
        save_state_func: Function to save state for undo
        save_data_func: Function to persist changes
        get_store_func: Function to get the data store
        
    Returns:
        Dictionary with success status and message
    """
    try:
        ideas = get_ideas_func()
        
        # Try to convert node_id to int if possible
        try:
            node_id = int(node_id)
        except (ValueError, TypeError):
            # Keep as is if conversion fails
            pass
            
        # Find the node
        node = find_node_by_id(ideas, node_id)
        
        if not node:
            logger.warning(f"Position update failed - node not found: {node_id}")
            return {
                'success': False,
                'message': f"Node not found: {node_id}"
            }
            
        # Save state for undo
        save_state_func()
            
        # Update the position
        try:
            x_float = float(x)
            y_float = float(y)
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid position coordinates for node {node_id}: x={x}, y={y}")
            return {
                'success': False,
                'message': f"Invalid coordinates: {str(e)}"
            }
            
        # Update the node
        node['x'] = x_float
        node['y'] = y_float
        
        # Save changes
        set_ideas_func(ideas)
        save_data_func(get_store_func())
        
        return {
            'success': True,
            'message': f"Position updated for node {node_id}"
        }
        
    except Exception as e:
        error_msg = handle_error(e, logger, f"Error updating position for node {node_id}")
        return {
            'success': False,
            'message': error_msg
        }

def process_bulk_position_updates(
    position_data: Dict[str, Any],
    get_ideas_func: Callable,
    set_ideas_func: Callable,
    save_state_func: Callable,
    save_data_func: Callable,
    get_store_func: Callable
) -> Dict[str, Any]:
    """Process bulk position updates for multiple nodes.
    
    Args:
        position_data: Dictionary mapping node IDs to position updates
        get_ideas_func: Function to get all nodes
        set_ideas_func: Function to update nodes
        save_state_func: Function to save state for undo
        save_data_func: Function to persist changes
        get_store_func: Function to get the data store
        
    Returns:
        Dictionary with success status, message, and results
    """
    # Store individual results
    results = []
    position_updated = False
    
    # Skip known message metadata keys
    skipped_keys = {'source', 'action', 'timestamp', 'message_id'}
    
    # Save state once for all updates
    save_state_func()
    
    # Process each key in the data
    for node_id, data in position_data.items():
        # Skip non-position data
        if node_id in skipped_keys:
            continue
            
        # Check if this is a valid position update
        if not isinstance(data, dict) or 'x' not in data or 'y' not in data:
            continue
            
        result = process_position_update(
            node_id=node_id,
            x=data['x'],
            y=data['y'],
            get_ideas_func=get_ideas_func,
            set_ideas_func=set_ideas_func,
            # Pass None for save_state_func to avoid multiple history entries
            save_state_func=lambda: None,
            save_data_func=save_data_func,
            get_store_func=get_store_func
        )
        
        results.append(result)
        if result['success']:
            position_updated = True
    
    # After all updates, save data once
    if position_updated:
        save_data_func(get_store_func())
        
    # Create summary result
    if position_updated:
        return {
            'success': True,
            'message': f"Updated {sum(1 for r in results if r['success'])} node positions",
            'results': results
        }
    else:
        error_messages = [r['message'] for r in results if not r['success']]
        return {
            'success': False,
            'message': "No positions were updated" if not error_messages else error_messages[0],
            'results': results
        }

def handle_position_message(
    message: Any,
    get_ideas_func: Callable,
    set_ideas_func: Callable,
    save_state_func: Callable,
    save_data_func: Callable,
    get_store_func: Callable
) -> Dict[str, Any]:
    """Handle position update messages in different formats.
    
    Supports both direct format (id, x, y) and bulk format (multiple nodes).
    
    Args:
        message: The message with position data
        get_ideas_func: Function to get all nodes
        set_ideas_func: Function to update nodes
        save_state_func: Function to save state for undo
        save_data_func: Function to persist changes
        get_store_func: Function to get the data store
        
    Returns:
        Dictionary with success status, message, and results
    """
    try:
        payload = message.payload
        
        # Check for direct format (id, x, y)
        if all(k in payload for k in ('id', 'x', 'y')):
            return process_position_update(
                node_id=payload['id'],
                x=payload['x'],
                y=payload['y'],
                get_ideas_func=get_ideas_func,
                set_ideas_func=set_ideas_func,
                save_state_func=save_state_func,
                save_data_func=save_data_func,
                get_store_func=get_store_func
            )
        else:
            # Bulk format - multiple nodes
            return process_bulk_position_updates(
                position_data=payload,
                get_ideas_func=get_ideas_func,
                set_ideas_func=set_ideas_func,
                save_state_func=save_state_func,
                save_data_func=save_data_func,
                get_store_func=get_store_func
            )
    except Exception as e:
        error_msg = handle_error(e, logger, "Error processing position update message")
        return {
            'success': False,
            'message': error_msg
        } 