"""
Canvas module for the Mind Map application.

This module centralizes all canvas-related functionality including:
- Canvas rendering and visualization
- Canvas expansion/collapse toggle
- Canvas utilities and coordinate handling
- Integration with network visualization
"""

import logging
import streamlit as st
from typing import Dict, Any, Optional, Tuple

from src.state import get_store, save_data, get_ideas, set_ideas
from src.history import save_state_to_history
from src.config import CANVAS_DIMENSIONS
from src.utils import find_closest_node, extract_canvas_coordinates, standard_response
from src.ui.network_visualization import render_network_visualization

# Get logger
logger = logging.getLogger(__name__)

def render_canvas():
    """
    Render the entire canvas including toggle controls and visualization.
    
    This is the main entry point for canvas rendering in the application.
    """
    # Add canvas expansion toggle
    canvas_height = render_canvas_toggle()
    
    # Render the network visualization
    render_network_visualization(canvas_height)
    
    return canvas_height

def render_canvas_toggle():
    """
    Render the canvas expansion toggle button and handle the expansion state.
    
    Returns:
        str: The current canvas height based on expansion state (e.g., "600px")
    """
    # Add canvas expansion toggle
    canvas_expanded = st.session_state.get('canvas_expanded', False)
    expand_button = st.button(
        "🔍 Expand Canvas" if not canvas_expanded else "🔍 Collapse Canvas", 
        key="canvas_expand_toggle_btn"
    )
    
    if expand_button:
        # Toggle canvas expansion
        canvas_expanded = not canvas_expanded
        # Update both session state and store
        st.session_state['canvas_expanded'] = canvas_expanded
        get_store()['settings']['canvas_expanded'] = canvas_expanded
        save_data(get_store())
        st.rerun()

    # Set canvas height based on expansion state
    canvas_height = CANVAS_DIMENSIONS['expanded' if canvas_expanded else 'normal']
    
    return canvas_height

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

def get_canvas_dimensions() -> Tuple[int, int]:
    """
    Get the default canvas dimensions.
    
    Returns:
        Tuple[int, int]: Width and height of the canvas
    """
    return (800, 600)  # Default canvas dimensions

def calculate_node_canvas_position(node: Dict[str, Any]) -> Tuple[float, float]:
    """
    Calculate the position of a node on the canvas.
    
    Args:
        node: The node object
        
    Returns:
        Tuple[float, float]: The x, y coordinates on the canvas
    """
    canvas_width, canvas_height = get_canvas_dimensions()
    
    # Convert from network coordinates to canvas coordinates
    node_canvas_x = node.get('x', 0) + canvas_width/2
    node_canvas_y = node.get('y', 0) + canvas_height/2
    
    return (node_canvas_x, node_canvas_y)

def calculate_click_threshold() -> float:
    """
    Calculate the threshold distance for considering a click on a node.
    
    Returns:
        float: The click threshold distance
    """
    canvas_width, canvas_height = get_canvas_dimensions()
    return min(canvas_width, canvas_height) * 0.08  # 8% of the smaller dimension 