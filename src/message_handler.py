"""
Message handler module for the Mind Map application.

This module handles processing of messages between the JavaScript frontend
and the Python backend, including:
- URL parameter processing
- Canvas click event handling
- Position updates
- General message actions
"""

import json
import datetime
import logging
import traceback
import streamlit as st

from src.state import get_store
from src.events import handle_canvas_click, handle_position_update

# Get logger
logger = logging.getLogger(__name__)

def setup_message_state():
    """Initialize message-related session state variables."""
    # Initialize message debug in session state if not present
    if 'message_debug' not in st.session_state:
        st.session_state.message_debug = []

def process_message_params():
    """
    Process URL parameters to extract and handle messages.
    
    Returns:
        tuple: (action, payload_str, current_time) if a message is found,
               (None, None, None) otherwise
    """
    # Get parameters from URL
    action = st.query_params.get('action', None)
    payload_str = st.query_params.get('payload', None)
    
    # Initialize message state
    setup_message_state()
    
    # Add current message to debug log if present
    if action and payload_str:
        # Get current time for the message
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        
        # Create the message record
        new_message = {
            'action': action,
            'payload': payload_str,
            'time': current_time
        }
        
        # Add to the log
        st.session_state.message_debug.append(new_message)
        
        # Limit log size
        if len(st.session_state.message_debug) > 50:
            st.session_state.message_debug = st.session_state.message_debug[-50:]
        
        # Log to console/file
        logger.info(f"Received message: action={action}, payload={payload_str}")
        
        # Add a prominent notification banner
        st.success(f"🔔 Message received: **{action}** at {current_time}")
        
        return action, payload_str, current_time
    
    return None, None, None

def process_action(action, payload_str, current_time):
    """
    Process an action based on its type and payload.
    
    Args:
        action (str): The action type
        payload_str (str): The JSON payload as a string
        current_time (str): The timestamp when the message was received
    
    Returns:
        bool: True if a UI rerun is needed, False otherwise
    """
    if not action:
        return False
    
    try:
        # Parse the payload
        if not payload_str:
            payload = {}
        else:
            payload = json.loads(payload_str)
            
        # Log successful payload parsing
        logger.debug(f"Payload parsed successfully: {payload}")
        
        # Handle different action types
        rerun_needed = False
        
        if action.startswith('canvas_'):
            # Handle canvas coordinate-based messages
            logger.info(f"Processing canvas interaction: {action}")
            
            # For click/dblclick actions, find the nearest node
            if action in ['canvas_click', 'canvas_dblclick', 'canvas_contextmenu']:
                canvas_action_successful = handle_canvas_click(payload, action)
                
                # Store message info in session state to confirm processing 
                st.session_state.last_processed_message = {
                    'action': action,
                    'payload': payload,
                    'time': current_time
                }
                
                rerun_needed = True
        
        elif action == 'pos':
            # Handle node position update
            position_update_successful = handle_position_update(payload)
            rerun_needed = position_update_successful
        
        else:
            # Handle other action types
            logger.info(f"Processing regular action: {action}")
        
        return rerun_needed
    
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        logger.error(traceback.format_exc())
        return False 