# Canvas utilities for MindMap application
import logging
import streamlit as st
from typing import Dict, Any, List, Tuple, Optional, Union

from src.utils import (
    find_closest_node, 
    extract_canvas_coordinates, 
    validate_node_exists,
    standard_response
)
from src.state import get_ideas, set_ideas, get_store, save_data
from src.history import save_state_to_history

logger = logging.getLogger(__name__)

def handle_canvas_interaction(
    message: Any,
    interaction_type: str,
    on_node_found_callback: Optional[callable] = None
) -> Dict[str, Any]:
    """
    Generic handler for canvas interactions (click, double-click, context menu).
    
    Args:
        message: The message containing canvas coordinates
        interaction_type: Type of interaction ('click', 'dblclick', 'contextmenu')
        on_node_found_callback: Optional callback function to execute when a node is found
        
    Returns:
        Standard response with success/failure status
    """
    try:
        ideas = get_ideas()
        
        # Extract and validate canvas coordinates
        success, error_msg, coords = extract_canvas_coordinates(message.payload)
        if not success:
            logger.warning(error_msg)
            return standard_response(message, False, error_msg)
        
        # Use utility function to find the closest node
        closest_node, min_distance, click_threshold = find_closest_node(
            ideas, 
            coords['x'], 
            coords['y'], 
            coords['canvasWidth'], 
            coords['canvasHeight']
        )
        
        if closest_node and min_distance <= click_threshold:
            logger.debug(f"Node {closest_node['id']} found at distance {min_distance:.2f} for {interaction_type}")
            
            # If callback provided, execute it
            if on_node_found_callback:
                return on_node_found_callback(closest_node, message)
                
            # Default actions for common interaction types
            if interaction_type == 'click':
                st.session_state['selected_node'] = closest_node['id']
                st.rerun()
                return standard_response(message, True)
            elif interaction_type == 'dblclick':
                st.session_state['edit_node'] = closest_node['id']
                st.rerun()
                return standard_response(message, True)
            elif interaction_type == 'contextmenu':
                # Delete the node
                save_state_to_history()
                ideas.remove(closest_node)
                set_ideas(ideas)
                save_data(get_store())
                st.rerun()
                return standard_response(message, True)
                
            # For other interactions, just return success
            return standard_response(message, True)
        else:
            error_msg = f'No node found near {interaction_type} coordinates'
            logger.warning(f"{error_msg} (closest: {closest_node['label'] if closest_node else 'None'} at distance: {min_distance:.2f}, threshold: {click_threshold:.2f})")
            return standard_response(message, False, error_msg)
            
    except Exception as e:
        from src.utils import handle_error
        error_msg = handle_error(e, logger, f"Error processing canvas {interaction_type}")
        return standard_response(message, False, error_msg) 