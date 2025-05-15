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
from src.utils import hex_to_rgb, get_theme, recalc_size, get_edge_color, get_urgency_color, get_tag_color, collect_descendants, find_node_by_id, find_closest_node
from src.themes import THEMES, TAGS, URGENCY_SIZE
from src.handlers import handle_message, handle_exception, is_circular
from src.message_queue import message_queue, MessageQueue, Message
from src.message_format import Message, validate_message, create_response_message
from src.logging_setup import get_logger
from src.node_utils import validate_node, update_node_position
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
from src.ui.canvas_toggle import render_canvas_toggle

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
    
    # Add canvas expansion toggle
    canvas_height = render_canvas_toggle()

    # Build PyVis Network
    theme = get_theme()
    
    # Create network with transparent background for seamless integration
    net = Network(
        height=canvas_height, 
        width="100%", 
        directed=True, 
        bgcolor=theme['background'],
        font_color=theme.get('text_color', '#333333'),
        select_menu=False,  # Remove the default right-click menu
        filter_menu=False,  # Remove the filter menu
        cdn_resources='local'  # Use local resources for better loading
    )

    # Configure physics using centralized settings
    net.barnes_hut(
        gravity=NETWORK_CONFIG['gravity'],
        central_gravity=NETWORK_CONFIG['central_gravity'],
        spring_length=NETWORK_CONFIG['spring_length'],
        spring_strength=get_store().get('settings', {}).get('spring_strength', DEFAULT_SETTINGS['spring_strength']),
        damping=NETWORK_CONFIG['damping'],
        overlap=NETWORK_CONFIG['overlap']
    )

    # Add nodes and edges to the network
    id_set = {n['id'] for n in get_ideas() if 'id' in n}
    
    # Get central node
    central_id = get_central()
    logger.info(f"Creating nodes with central node ID: {central_id}")
    
    for n in get_ideas():
        # Skip nodes without an id
        if 'id' not in n:
            continue
            
        recalc_size(n)

        # Get the color mode from settings
        color_mode = get_store().get('settings', {}).get('color_mode', 'urgency')
        
        # Log node and coloring details
        node_id = n.get('id')
        node_tag = n.get('tag', '')
        node_urgency = n.get('urgency', 'medium')
        logger.debug(f"Coloring node {node_id} with tag='{node_tag}', urgency='{node_urgency}', mode='{color_mode}'")
        
        # Set color based on tag or urgency depending on color mode
        if color_mode == 'tag' and n.get('tag'):
            # Use tag color if available
            color_hex = get_tag_color(n['tag'])
            logger.debug(f"Node {node_id}: Using tag color {color_hex} for tag '{n['tag']}'")
        else:
            # Fall back to urgency color
            color_hex = get_urgency_color(n.get('urgency', 'medium'))
            logger.debug(f"Node {node_id}: Using urgency color {color_hex} for '{n.get('urgency', 'medium')}'")

        r, g, b = hex_to_rgb(color_hex)
        bg, bd = f"rgba({r},{g},{b},{RGBA_ALPHA})", f"rgba({r},{g},{b},1)"

        # Apply the size multiplier to make urgency differences more noticeable
        base_size = n.get('size', 20)  # Default size of 20 if not set
        size_multiplier = get_store().get('settings', {}).get('size_multiplier', DEFAULT_SETTINGS['size_multiplier'])
        if n.get('urgency') == 'high':
            base_size = base_size * size_multiplier
        elif n.get('urgency') == 'low':
            base_size = base_size / size_multiplier
            
        size_px = base_size * (1.5 if n['id'] == central_id else 1)
        
        # Apply special highlighting for central node
        is_central = n['id'] == central_id
        if is_central:
            bd = "#FF5722"  # Bright orange border
            border_width = 3  # Thicker border
            logger.info(f"Applying special highlighting to central node {n['id']}")
        else:
            border_width = 1

        # Prepare node title with description for hover text
        title = n['label']
        if n.get('tag'):
            title = f"[{n['tag']}] {title}"
        if n.get('description'):
            title += f"\n\n{n['description']}"

        kwargs = {
            'label': n['label'],
            'title': title,
            'size': size_px,
            'color': {'background': bg, 'border': bd},
            'borderWidth': border_width,
            'shape': 'circle',
            'fixed': {'x': False, 'y': False}
        }

        if n['x'] is not None and n['y'] is not None:
            kwargs.update(x=n['x'], y=n['y'])

        net.add_node(n['id'], **kwargs)

    # Add edges between nodes
    for n in get_ideas():
        # Skip nodes without an id
        if 'id' not in n:
            continue
            
        pid = n.get('parent')
        if pid in id_set:
            edge_type = n.get('edge_type', 'default')
            # Make sure the edge type is valid for the current theme
            if edge_type not in get_theme()['edge_colors']:
                edge_type = 'default'  # Fallback to default if not in theme
            edge_color = get_edge_color(edge_type)
            edge_length = get_store().get('settings', {}).get('edge_length', DEFAULT_SETTINGS['edge_length'])
            net.add_edge(pid, n['id'], arrows='to', color=edge_color, title=edge_type, length=edge_length)

    # Generate PyVis HTML with modified network code to ensure accessibility
    html_content = net.generate_html()

    # Create simplified HTML with direct network object access
    modified_html = html_content.replace(
        'var network = new vis.Network(',
        'window.visNetwork = new vis.Network('
    )
    
    # Add additional hook to ensure network is accessible globally
    modified_html = modified_html.replace(
        '</script>',
        '''
        // Add hook to ensure visNetwork is available
        if (typeof network !== 'undefined' && !window.visNetwork) {
            console.log('Setting window.visNetwork from local network variable');
            window.visNetwork = network;
        }
        
        // Debug that will run after network creation
        setTimeout(function() {
            console.log('Network object availability check:');
            console.log('- window.visNetwork available:', window.visNetwork !== undefined);
            if (!window.visNetwork) {
                console.log('Searching for network in canvases...');
                var networkDiv = document.getElementById('mynetwork');
                if (networkDiv) {
                    var canvases = networkDiv.querySelectorAll('canvas');
                    for (var i = 0; i < canvases.length; i++) {
                        if (canvases[i].network) {
                            console.log('Found network object in canvas');
                            window.visNetwork = canvases[i].network;
                            break;
                        }
                    }
                }
            }
        }, 1000);
        </script>'''
    )

    # Add direct event listeners to guarantee they are attached
    # Load the JavaScript files from the extracted modules instead of inline code
    js_files = [
        'src/js/message_relay.js',
        'src/js/position_tracking.js',
        'src/js/network_events.js'
    ]
    
    # Read the JS files and combine them into a single script element
    js_files_content = ""
    for js_file in js_files:
        try:
            with open(js_file, 'r') as f:
                js_files_content += f.read() + "\n\n"
        except Exception as e:
            logger.error(f"Error loading JS file {js_file}: {str(e)}")
    
    direct_js = f"""
    <script>
    {js_files_content}
    </script>
    """

    # Add the direct JS right before the closing </body> tag
    modified_html = modified_html.replace('</body>', direct_js + '</body>')

    # Get network positions for all nodes
    node_positions = {}
    for n in get_ideas():
        if 'id' in n and 'x' in n and 'y' in n and n['x'] is not None and n['y'] is not None:
            node_id = n['id']
            x = n['x']
            y = n['y']
            # Skip (0,0) positions that might be default
            if float(x) != 0.0 or float(y) != 0.0:
                node_positions[node_id] = {'x': float(x), 'y': float(y)}
    
    # Insert the position data into the JavaScript
    position_data_js = f"""
    <script>
    // Initialize position data from server
    window.serverNodePositions = {json.dumps(node_positions)};
    
    console.log('📊 Loaded position data for', Object.keys(window.serverNodePositions).length, 'nodes from server');
    </script>
    """
    
    # Add position data initialization to the HTML
    modified_html += position_data_js
    
    # Include our custom utils.js file to fix the Streamlit namespace error
    with open("src/utils.js", "r") as f:
        utils_js = f.read()
        utils_js_html = f"""
        <script type="text/javascript">
        // Immediately define Streamlit namespace to prevent errors
        if (typeof window.Streamlit === 'undefined') {{
            window.Streamlit = {{ 
                setComponentValue: function() {{ console.log('Streamlit mock: setComponentValue called'); }},
                setComponentReady: function() {{ console.log('Streamlit mock: setComponentReady called'); }},
                receiveMessageFromPython: function() {{ console.log('Streamlit mock: receiveMessageFromPython called'); }}
            }};
            console.log('Created Streamlit namespace mock to prevent errors');
        }}
        </script>
        <script type="text/javascript">
        {utils_js}
        </script>
        """
    
    # Add utils.js to the HTML
    modified_html += utils_js_html

    # Render the modified HTML
    components.html(
        modified_html, 
        height=int(canvas_height.replace("px", "")), 
        scrolling=False
    )

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
    action = st.query_params.get('action', None)
    payload_str = st.query_params.get('payload', None)
    
    # Initialize message debug in session state if not present
    if 'message_debug' not in st.session_state:
        st.session_state.message_debug = []
    
    # Add current message to debug log immediately if present
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

    # Remove message stats columns
    # Remove communication diagnostics expander
    # Remove debug message log expander
    # Remove the two buttons

    if action:
        try:
            # Parse the payload
            if payload_str:
                payload = json.loads(payload_str)
                
                # Log successful payload parsing
                logger.debug(f"Payload parsed successfully: {payload}")
                
                # Handle different action types
                if action.startswith('canvas_'):
                    # Handle canvas coordinate-based messages
                    logger.info(f"Processing canvas interaction: {action}")
                    
                    # For click/dblclick actions, find the nearest node
                    if action in ['canvas_click', 'canvas_dblclick', 'canvas_contextmenu']:
                        if 'x' in payload and 'y' in payload:
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
                                            new_central = next((n['id'] for n in get_ideas() if 'id' not in n or n['id'] not in to_remove), None)
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
                    
                    # Store message info in session state to confirm processing 
                    st.session_state.last_processed_message = {
                        'action': action,
                        'payload': payload,
                        'time': current_time
                    }
                    
                    # Force a rerun to update the UI after processing
                    st.rerun()
                    
                elif action == 'pos':
                    # Handle node position update
                    logger.info(f"💥 POSITION UPDATE MESSAGE RECEIVED: {payload}")
                    
                    if 'id' in payload and 'x' in payload and 'y' in payload:
                        node_id = payload['id']
                        x = payload['x']
                        y = payload['y']
                        
                        logger.info(f"⭐ POSITION DEBUG: Processing update for node {node_id} to ({x}, {y}) of types (x: {type(x).__name__}, y: {type(y).__name__})")
                        
                        # Use the centralized position update service
                        try:
                            from src.node_utils import update_node_position_service
                            from src.history import save_state_to_history
                            
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
                                st.rerun()
                            else:
                                logger.warning(f"❌ POSITION UPDATE FAILED: {result['message']}")
                        except Exception as e:
                            logger.error(f"❌ Error updating position: {str(e)}")
                            logger.error(traceback.format_exc())
                    else:
                        logger.error(f"❌ Invalid position update payload: {payload}")
                else:
                    # Handle other action types
                    logger.info(f"Processing regular action: {action}")
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            logger.error(traceback.format_exc())

    # Add debug API for position tracking
    # This is now integrated in the position_tracking.js file loaded above
    # No need for additional JavaScript here

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