"""
Event handlers for the Mind Map application.

This module contains handlers for various canvas and node events including:
- Canvas click events
- Canvas double-click events 
- Canvas context menu events
- Node position updates
"""

import logging
import datetime
import traceback

from src.state import (
    get_store, get_ideas, get_central, 
    set_ideas, set_central, save_data
)
from src.history import save_state_to_history
from src.utils import find_closest_node, collect_descendants
from src.node_utils import update_node_position_service

# Get logger
logger = logging.getLogger(__name__)

def handle_canvas_click(payload, action):
    """
    Handle canvas click, double-click, and context-menu actions.
    
    Args:
        payload (dict): The message payload containing coordinates
        action (str): The action type (canvas_click, canvas_dblclick, canvas_contextmenu)
    
    Returns:
        bool: True if action was successful, False otherwise
    """
    import streamlit as st
    
    if 'x' not in payload or 'y' not in payload:
        logger.warning(f"Missing coordinates in {action} payload")
        return False
    
    # Process the coordinates
    click_x = payload.get('x', 0)
    click_y = payload.get('y', 0)
    canvas_width = payload.get('canvasWidth', 800)
    canvas_height = payload.get('canvasHeight', 600)
    
    # Store the coordinates in session state
    st.session_state.last_click_coords = {
        'x': click_x,
        'y': click_y,
        'canvasWidth': canvas_width,
        'canvasHeight': canvas_height,
        'timestamp': payload.get('timestamp', datetime.datetime.now().timestamp() * 1000)
    }
    
    logger.info(f"Canvas {action} at coordinates: ({click_x}, {click_y})")
    
    # Get all nodes with stored positions
    ideas = get_ideas()
    nodes_with_pos = [n for n in ideas if n.get('x') is not None and n.get('y') is not None]
    
    # Debug logging
    logger.info(f"Total nodes: {len(ideas)}, Nodes with positions: {len(nodes_with_pos)}")
    
    canvas_action_successful = False
    
    if nodes_with_pos:
        # Use utility function to find the closest node
        closest_node, min_distance, click_threshold = find_closest_node(
            nodes_with_pos, click_x, click_y, canvas_width, canvas_height
        )
        
        if closest_node:
            logger.info(f"Closest node: {closest_node['id']} ({closest_node.get('label', 'Untitled Node')}) at distance {min_distance:.2f}, threshold: {click_threshold:.2f}")
        
        if closest_node and min_distance < click_threshold:
            node_id = closest_node['id']
            logger.info(f"Node {node_id} is within threshold - processing {action}")
            
            # Handle different actions
            if action == 'canvas_click':
                # Regular click - select and center the node
                st.session_state.selected_node = node_id
                st.session_state.show_node_details = True
                set_central(node_id)
                save_data(get_store())
                logger.info(f"Selected and centered node {node_id}")
                canvas_action_successful = True
            
            elif action == 'canvas_dblclick':
                # Double-click - edit the node
                st.session_state['edit_node'] = node_id
                logger.info(f"Opening edit modal for node {node_id}")
                canvas_action_successful = True
            
            elif action == 'canvas_contextmenu':
                # Right-click - delete the node (and its descendants)
                logger.info(f"Deleting node {node_id}")
                
                # Save state before deletion
                save_state_to_history()
                
                # Remove node and its descendants using utility function
                to_remove = collect_descendants(node_id, get_ideas())
                
                set_ideas([n for n in get_ideas() if 'id' not in n or n['id'] not in to_remove])
                
                # Update central node if needed
                if get_central() in to_remove:
                    new_central = next((n['id'] for n in get_ideas() if 'id' in n and n['id'] not in to_remove), None)
                    set_central(new_central)
                
                save_data(get_store())
                logger.info(f"Deleted node {node_id} and {len(to_remove)-1} descendants")
                canvas_action_successful = True
        else:
            if closest_node:
                logger.warning(f"No node found near click coordinates (closest: {closest_node.get('label', 'Untitled Node')} at distance: {min_distance:.2f}, threshold: {click_threshold:.2f})")
            else:
                logger.warning(f"No nodes found near click coordinates")
    
    # Show warning message if action failed
    if not canvas_action_successful and action != 'canvas_click':
        logger.error(f"Canvas action {action} failed at coordinates ({click_x:.1f}, {click_y:.1f})")
    
    return canvas_action_successful

def handle_position_update(payload):
    """
    Handle position update message.
    
    Args:
        payload (dict): The message payload with id, x, y coordinates
    
    Returns:
        bool: True if position update was successful, False otherwise
    """
    logger.info(f"💥 POSITION UPDATE MESSAGE RECEIVED: {payload}")
    
    if 'id' not in payload or 'x' not in payload or 'y' not in payload:
        logger.error(f"❌ Invalid position update payload: {payload}")
        return False
    
    node_id = payload['id']
    x = payload['x']
    y = payload['y']
    
    logger.info(f"⭐ POSITION DEBUG: Processing update for node {node_id} to ({x}, {y}) of types (x: {type(x).__name__}, y: {type(y).__name__})")
    
    # Use the centralized position update service
    try:
        result = update_node_position_service(
            node_id=node_id, 
            x=x, 
            y=y, 
            get_ideas_func=get_ideas,
            set_ideas_func=set_ideas,
            save_state_func=save_state_to_history,
            save_data_func=save_data,
            get_store_func=get_store
        )
        
        if result['success']:
            logger.info(f"💾 POSITION UPDATE SUCCESS: {result['message']}")
            return True
        else:
            logger.warning(f"❌ POSITION UPDATE FAILED: {result['message']}")
            return False
    except Exception as e:
        logger.error(f"❌ Error updating position: {str(e)}")
        logger.error(traceback.format_exc())
        return False 