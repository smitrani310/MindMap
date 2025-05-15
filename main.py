"""streamlit_mindmap_app.py – v5.4 Enhanced Mind Map with Improved Structure
Added features:
- Centralized configuration
- Separated JavaScript handlers
- Improved error handling
- Better code organization

Original features:
- Tags/categories for nodes with color coding
- Node descriptions/notes
- Different connection types
- Undo/redo functionality
- Custom themes
- Keyboard shortcuts
- Search and replace
"""

import json
import textwrap
import datetime
import traceback
import os
import logging
import colorsys
from typing import List, Dict, Optional, Tuple, Set
from copy import deepcopy
import atexit
import platform
import re
import sys
import time
import uuid
from collections import Counter

import streamlit as st
from pyvis.network import Network
import streamlit.components.v1 as components

# Import configuration and modules
from src.config import (
    DATA_FILE, DEFAULT_SETTINGS, NETWORK_CONFIG,
    CANVAS_DIMENSIONS, PRIMARY_NODE_BORDER, RGBA_ALPHA,
    ERROR_MESSAGES
)
from src.state import (
    get_store, get_ideas, get_central, get_next_id, increment_next_id, get_current_theme,
    set_ideas, add_idea, set_central, set_current_theme, save_data, load_data
)
from src.history import save_state_to_history, can_undo, can_redo, perform_undo, perform_redo
from src.utils import (
    hex_to_rgb, get_theme, recalc_size, get_edge_color, get_urgency_color, 
    get_tag_color, collect_descendants, find_node_by_id, find_closest_node, is_circular,
    handle_exception
)
from src.themes import THEMES, TAGS, URGENCY_SIZE
from src.handlers import handle_message
from src.message_queue import message_queue, MessageQueue, Message
from src.message_format import Message, validate_message, create_response_message
from src.logging_setup import get_logger
from src.node_utils import validate_node, update_node_position
from src.message_handler import process_message_params, process_action
from src.ui.header import render_header
from src.ui.sidebar import render_sidebar
from src.ui.search import render_search
from src.ui.import_export import render_import_export
from src.ui.add_bubble import render_add_bubble_form
from src.ui.undo_redo import render_undo_redo
from src.ui.shortcuts import render_shortcuts
from src.ui.logs import render_logs_section
from src.ui.node_list import render_node_list, handle_node_list_actions
from src.ui.node_edit import render_node_edit_modal
from src.ui.tutorial import render_tutorial_prompt
from src.ui.node_details import render_node_details
from src.ui.canvas import render_canvas

# Configure logging
import os
import datetime

# Create logs directory if it doesn't exist
logs_dir = "logs"
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Log rotation - keep only the last 20 log files
def rotate_logs(max_logs=20):
    if os.path.exists(logs_dir):
        log_files = sorted([f for f in os.listdir(logs_dir) if f.endswith('.log')])
        if len(log_files) > max_logs:
            # Remove oldest logs
            for old_log in log_files[:-max_logs]:
                try:
                    os.remove(os.path.join(logs_dir, old_log))
                    print(f"Removed old log file: {old_log}")
                except Exception as e:
                    print(f"Error removing log file {old_log}: {str(e)}")

# Perform log rotation
rotate_logs()

# Initialize logging
def initialize_logging():
    # Check if logger is already initialized
    if hasattr(initialize_logging, 'logger') and initialize_logging.logger is not None:
        return initialize_logging.logger, initialize_logging.log_filename
    
    # Generate a unique log filename with timestamp
    current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(logs_dir, f"mindmap_session_{current_time}.log")
    
    # Set up file handler
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

    # Set up console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers = []  # Remove any existing handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Get logger for this module
    logger = logging.getLogger(__name__)
    logger.info(f"Starting new session. Logging to: {log_filename}")
    
    # Store logger and filename in function attributes
    initialize_logging.logger = logger
    initialize_logging.log_filename = log_filename
    
    return logger, log_filename

# Initialize logger globally
logger, current_log_filename = initialize_logging()

# Add a function to create a new log file
def create_new_log():
    global logger, current_log_filename
    
    # Close existing file handlers
    for handler in logging.getLogger().handlers[:]:
        handler.close()
        logging.getLogger().removeHandler(handler)
    
    # Clear the stored logger
    initialize_logging.logger = None
    initialize_logging.log_filename = None
    
    # Initialize new logging
    logger, current_log_filename = initialize_logging()
    return current_log_filename

# Initialize session state with persisted data
if 'store' not in st.session_state:
    persisted_data = load_data()
    logger.info("Loading persisted data for new session")
    if persisted_data:
        st.session_state['store'] = persisted_data
        logger.info(f"Loaded data with {len(persisted_data.get('ideas', []))} nodes")
        # Update session state with canvas expansion setting if available
        if 'canvas_expanded' in persisted_data.get('settings', {}):
            st.session_state['canvas_expanded'] = persisted_data['settings']['canvas_expanded']
    else:
        logger.info("No persisted data found, initializing empty store")
        st.session_state['store'] = {
            'ideas': [],
            'central': None,
            'next_id': 0,
            'history': [],
            'history_index': -1,
            'current_theme': 'default',
            'settings': DEFAULT_SETTINGS.copy()
        }
    
    # Initialize settings in session state for easy access
    if 'settings' not in get_store():
        get_store()['settings'] = DEFAULT_SETTINGS.copy()
        logger.info("Initialized default settings")

# ---------------- Main App ----------------
try:
    st.set_page_config(page_title="Enhanced Mind Map", layout="wide")

    # Add a script to restore messages from browser cookies if needed
    message_recovery_js = """
    <script>
    // Script to help with message recovery on page load
    console.log('Message recovery script loaded');
    
    function injectMessageToSessionState() {
        // Check for URL parameters first
        const urlParams = new URLSearchParams(window.location.search);
        const action = urlParams.get('action');
        const payload = urlParams.get('payload');
        
        if (action && payload) {
            console.log('Found message in URL parameters, will be recorded');
            return;
        }
        
        // Look for message in cookie
        try {
            const cookies = document.cookie.split(';');
            for (let cookie of cookies) {
                cookie = cookie.trim();
                if (cookie.startsWith('last_message=')) {
                    const msgStr = decodeURIComponent(cookie.substring('last_message='.length));
                    const message = JSON.parse(msgStr);
                    console.log('Found message in cookie:', message);
                    
                    // Add to URL parameters and refresh
                    const params = new URLSearchParams();
                    params.set('action', message.action);
                    params.set('payload', message.payload);
                    const newUrl = window.location.pathname + '?' + params.toString();
                    
                    console.log('Redirecting to inject message:', newUrl);
                    // Use timeout to ensure the page has time to initialize
                    setTimeout(function() {
                        window.location.href = newUrl;
                    }, 100);
                    
                    return;
                }
            }
        } catch (e) {
            console.error('Error recovering message from cookie:', e);
        }
    }
    
    // Run recovery on page load if there's no action parameter
    if (!window.location.search.includes('action=')) {
        console.log('No action in URL, checking for stored messages');
        setTimeout(injectMessageToSessionState, 500);
    }
    </script>
    """
    
    # Insert the message recovery script
    st.components.v1.html(message_recovery_js, height=0)

    # Render the application header
    render_header()

    # Render sidebar with settings
    render_sidebar()

    # Render canvas (includes toggle and visualization)
    render_canvas()

    # Render search functionality
    render_search()

    # Render import/export functionality
    render_import_export()

    # Add Bubble Form
    render_add_bubble_form()

    # Undo/Redo buttons
    render_undo_redo()

    # Keyboard Shortcuts Info
    render_shortcuts()

    # Logs section
    render_logs_section()

    # Edit / Center List
    render_node_list()
    handle_node_list_actions()

    # Handle button actions from session state
    if 'center_node' in st.session_state:
        node_id = st.session_state.pop('center_node')
        if node_id in {n['id'] for n in get_ideas() if 'id' in n}:
            set_central(node_id)
            st.rerun()

    if 'delete_node' in st.session_state:
        node_id = st.session_state.pop('delete_node')
        if node_id in {n['id'] for n in get_ideas() if 'id' in n}:
            save_state_to_history()
            
            # Use the utility function to collect descendants
            to_remove = collect_descendants(node_id, get_ideas())

            set_ideas([n for n in get_ideas() if 'id' not in n or n['id'] not in to_remove])
            if get_central() in to_remove:
                set_central(None)
            if st.session_state.get('selected_node') in to_remove:
                st.session_state['selected_node'] = None
            st.rerun()

    # Node Edit Modal
    render_node_edit_modal()

    # Tutorial Prompt When Empty
    render_tutorial_prompt()

    # Node Details Section
    render_node_details()

    # Process any messages from JavaScript
    action, payload_str, current_time = process_message_params()

    # Process the action if there is one
    if action:
        try:
            # Process the action using the refactored module
            rerun_needed = process_action(action, payload_str, current_time)
            
            # Force a rerun to update the UI if needed
            if rerun_needed:
                st.rerun()
                
        except Exception as e:
            logger.error(f"Error processing action: {str(e)}")
            logger.error(traceback.format_exc())
            st.error(f"Error processing action: {str(e)}")

    # Remove message stats columns
    # Remove communication diagnostics expander
    # Remove debug message log expander
    # Remove the two buttons

except Exception as e:
    logger.error(f"Unhandled exception: {str(e)}")
    logger.error(traceback.format_exc())
    handle_exception(e)

def handle_message_with_queue(message: Message) -> None:
    """Handle a message using the message queue."""
    try:
        # Process the message
        response = handle_message(message.to_dict())
        
        # Send response back to frontend
        if response:
            response_message = Message.from_dict(response)
            # Store in session state
            st.session_state['last_response'] = response_message.to_json()
            
            # Send response back to frontend via postMessage
            js_code = f"""
            <script>
                window.parent.postMessage({response_message.to_json()}, '*');
            </script>
            """
            st.components.v1.html(js_code, height=0)
            
            st.rerun()
            
    except Exception as e:
        logger.error(f"Error handling message: {str(e)}")
        response = create_response_message(message, 'failed', str(e))
        st.session_state['last_response'] = response.to_json()
        
        # Send error response back to frontend
        js_code = f"""
        <script>
            window.parent.postMessage({response.to_json()}, '*');
        </script>
        """
        st.components.v1.html(js_code, height=0)
        
        st.rerun()

# Initialize message queue
message_queue.start(handle_message_with_queue)

# Handle reinitialization if needed (this happens after importing JSON files)
if st.session_state.get('reinitialize_message_queue', False):
    # Clear the flag
    del st.session_state['reinitialize_message_queue']
    
    # Stop and restart the message queue to ensure it works with new data
    logger.info("Reinitializing message queue after JSON import")
    message_queue.stop()
    time.sleep(0.3)  # Allow time for the thread to fully stop
    
    # Verify the queue is stopped
    logger.info(f"Message queue stopped: thread is {message_queue._worker_thread}")
    
    # Restart the queue
    message_queue.start(handle_message_with_queue)
    logger.info("Message queue reinitialized after import")

# Add cleanup on app shutdown
def cleanup():
    """Clean up resources when the app is shutting down."""
    message_queue.stop()

# Register cleanup
atexit.register(cleanup)