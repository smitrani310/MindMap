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

    # Apply theme to page
    current_theme = get_current_theme()
    if current_theme == 'dark':
        st.markdown("""
        <style>
        .stApp {
            background-color: #2E3440;
            color: #D8DEE9;
        }
        .stSidebar {
            background-color: #3B4252;
        }
        /* Remove canvas frame */
        iframe {
            border: none !important;
            box-shadow: none !important;
            background-color: transparent !important;
        }
        </style>
        """, unsafe_allow_html=True)
    else:
        # For light theme, only remove the frame but keep the theme
        st.markdown("""
        <style>
        /* Remove canvas frame */
        iframe {
            border: none !important;
            box-shadow: none !important;
            background-color: transparent !important;
        }
        </style>
        """, unsafe_allow_html=True)

    st.title("🧠 Enhanced Mind Map")

    # Sidebar Theme Selection
    with st.sidebar.expander("Settings", expanded=False):
        selected_theme = st.selectbox(
            "Select Theme",
            options=list(THEMES.keys()),
            index=list(THEMES.keys()).index(get_current_theme())
        )
        
        # Get settings with defaults
        settings = get_store().get('settings', {})
        default_edge_length = settings.get('edge_length', DEFAULT_SETTINGS['edge_length'])
        default_spring_strength = settings.get('spring_strength', DEFAULT_SETTINGS['spring_strength'])
        default_size_multiplier = settings.get('size_multiplier', DEFAULT_SETTINGS['size_multiplier'])
        
        # Add connection length slider
        edge_length = st.slider(
            "Connection Length", 
            min_value=50, 
            max_value=300, 
            value=default_edge_length,
            step=10,
            help="Adjust the length of connections between nodes"
        )
        
        # Add spring strength slider
        spring_strength = st.slider(
            "Connection Strength",
            min_value=0.1,
            max_value=1.0,
            value=default_spring_strength,
            step=0.1,
            help="Adjust how strongly connected nodes pull together (higher = tighter grouping)"
        )
        
        # Add size multiplier for urgency differences
        size_multiplier = st.slider(
            "Urgency Size Impact",
            min_value=1.0,
            max_value=3.0,
            value=default_size_multiplier,
            step=0.2,
            help="Enhance the size difference between urgency levels (higher = more pronounced difference)"
        )
        
        # Get custom colors or use defaults
        custom_colors = settings.get('custom_colors', DEFAULT_SETTINGS['custom_colors'])
        
        # Custom Tags Management
        st.markdown("### Tag Management")
        
        # Get existing custom tags
        custom_tags = settings.get('custom_tags', [])
        
        # Input for adding new custom tags
        new_tag_col1, new_tag_col2 = st.columns([3, 1])
        new_tag = new_tag_col1.text_input("New Custom Tag", key="new_custom_tag")
        
        add_tag_clicked = new_tag_col2.button("Add Tag")
        if add_tag_clicked and new_tag and new_tag not in custom_tags and new_tag not in TAGS:
            # Generate a color for the new tag
            hash_value = sum(ord(c) for c in new_tag)
            hue = hash_value % 360
            
            # Convert HSL to hex for the color picker
            h, s, l = hue/360.0, 0.7, 0.6  # convert to 0-1 range
            r, g, b = colorsys.hls_to_rgb(h, l, s)
            hex_color = "#{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(b*255))
            
            # Add the tag to custom tags list
            custom_tags.append(new_tag)
            
            # Add the tag color to custom colors
            if 'tags' not in custom_colors:
                custom_colors['tags'] = {}
            custom_colors['tags'][new_tag] = hex_color
            
            # Save changes
            settings['custom_tags'] = custom_tags
            settings['custom_colors'] = custom_colors
            get_store()['settings'] = settings
            
            # Log the color assignment for debugging
            logger.info(f"Added new tag '{new_tag}' with color {hex_color}")
            
            save_data(get_store())
            st.rerun()
            
        # Display custom tags for removal and color editing
        if custom_tags:
            st.markdown("**Custom Tags:**")
            
            # For each custom tag, show name, color picker and delete button
            for i, tag in enumerate(custom_tags):
                col1, col2, col3 = st.columns([2, 2, 1])
                
                # Tag name
                col1.write(f"• {tag}")
                
                # Color picker
                current_color = custom_colors.get('tags', {}).get(tag, "#808080")
                new_color = col2.color_picker(
                    "Color", 
                    current_color, 
                    key=f"color_picker_{tag}_{i}",
                    label_visibility="collapsed"
                )
                
                # Update color if changed
                if new_color != current_color:
                    if 'tags' not in custom_colors:
                        custom_colors['tags'] = {}
                    custom_colors['tags'][tag] = new_color
                    settings['custom_colors'] = custom_colors
                    get_store()['settings'] = settings
                    save_data(get_store())
                
                # Delete button
                if col3.button("🗑️", key=f"remove_tag_{i}", help=f"Remove {tag}"):
                    custom_tags.remove(tag)
                    if tag in custom_colors.get('tags', {}):
                        del custom_colors['tags'][tag]
                    
                    settings['custom_tags'] = custom_tags
                    settings['custom_colors'] = custom_colors
                    get_store()['settings'] = settings
                    save_data(get_store())
                    st.rerun()
        else:
            st.info("No custom tags yet. Add one above.")
        
        # Color customization section
        st.markdown("### Color Customization")
        
        # Add color mode toggle
        color_mode = settings.get('color_mode', DEFAULT_SETTINGS['color_mode'])
        new_color_mode = st.radio(
            "Node Color Mode",
            options=["Urgency", "Tag"],
            index=0 if color_mode == 'urgency' else 1,
            horizontal=True,
            help="Choose whether to color nodes based on urgency level or tag"
        )
        # Convert display name to config value
        new_color_mode = new_color_mode.lower()
        
        # Add explanation of current mode
        if new_color_mode == 'urgency':
            st.info("Nodes are colored by urgency level (high, medium, low).")
        else:
            st.info("Nodes are colored by their assigned tag. Nodes without tags will use urgency colors.")
        
        # Color tabs for urgency and tags
        active_tab = 0 if new_color_mode == 'urgency' else 1
        color_tab1, color_tab2 = st.tabs(["Urgency Colors", "Tag Colors"])
        
        # Urgency color pickers
        with color_tab1:
            urgency_colors = custom_colors.get('urgency', DEFAULT_SETTINGS['custom_colors']['urgency'])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                high_color = st.color_picker(
                    "High Urgency", 
                    urgency_colors.get('high', DEFAULT_SETTINGS['custom_colors']['urgency']['high']),
                    help="Color for high urgency nodes"
                )
            with col2:
                medium_color = st.color_picker(
                    "Medium Urgency", 
                    urgency_colors.get('medium', DEFAULT_SETTINGS['custom_colors']['urgency']['medium']),
                    help="Color for medium urgency nodes"
                )
            with col3:
                low_color = st.color_picker(
                    "Low Urgency", 
                    urgency_colors.get('low', DEFAULT_SETTINGS['custom_colors']['urgency']['low']),
                    help="Color for low urgency nodes"
                )
            
            # Update urgency colors if changed
            if (high_color != urgency_colors.get('high') or 
                medium_color != urgency_colors.get('medium') or 
                low_color != urgency_colors.get('low')):
                custom_colors['urgency'] = {
                    'high': high_color,
                    'medium': medium_color,
                    'low': low_color
                }
        
        # Tag color pickers
        with color_tab2:
            tag_colors = custom_colors.get('tags', DEFAULT_SETTINGS['custom_colors']['tags'])
            
            # Get all tags (built-in only)
            builtin_tags = list(TAGS.keys())
            
            st.markdown("#### Built-in Tags")
            
            # Create 2 columns for built-in tag colors
            tag_col1, tag_col2 = st.columns(2)
            
            half_length = len(builtin_tags) // 2 + len(builtin_tags) % 2
            
            # First column of built-in tags
            with tag_col1:
                for tag in builtin_tags[:half_length]:
                    tag_color = st.color_picker(
                        f"{tag.capitalize()}", 
                        tag_colors.get(tag, TAGS[tag]['color']),
                        help=f"Color for {tag} tag"
                    )
                    # Update if changed
                    if tag_color != tag_colors.get(tag):
                        tag_colors[tag] = tag_color
            
            # Second column of built-in tags
            with tag_col2:
                for tag in builtin_tags[half_length:]:
                    tag_color = st.color_picker(
                        f"{tag.capitalize()}", 
                        tag_colors.get(tag, TAGS[tag]['color']),
                        help=f"Color for {tag} tag"
                    )
                    # Update if changed
                    if tag_color != tag_colors.get(tag):
                        tag_colors[tag] = tag_color
            
            # Note about custom tags
            st.info("Custom tag colors can be changed in the Tag Management section above.")
            
            # Update tag colors
            custom_colors['tags'] = tag_colors
        
        # Save all settings if changed
        settings_changed = (
            edge_length != default_edge_length or 
            spring_strength != default_spring_strength or 
            size_multiplier != default_size_multiplier or
            custom_colors != settings.get('custom_colors', {}) or
            custom_tags != settings.get('custom_tags', []) or
            new_color_mode != color_mode
        )
        
        if settings_changed:
            # Update the store with new settings
            get_store()['settings'] = {
                'edge_length': edge_length,
                'spring_strength': spring_strength,
                'size_multiplier': size_multiplier,
                'canvas_expanded': settings.get('canvas_expanded', False),
                'color_mode': new_color_mode,
                'custom_tags': custom_tags,
                'custom_colors': custom_colors
            }
            save_data(get_store())
        
        if selected_theme != get_current_theme():
            set_current_theme(selected_theme)
            logger.info(f"Theme changed to: {selected_theme}")
            st.rerun()

    # Sidebar Search
    search_col1, search_col2 = st.sidebar.columns([3, 1])
    search_q = search_col1.text_input("🔍 Search nodes")
    search_replace = search_col2.checkbox("Replace")

    if search_replace and search_q:
        replace_q = st.sidebar.text_input("Replace with")
        if st.sidebar.button("Replace All"):
            ideas = get_ideas()
            if ideas:
                save_state_to_history()
                count = 0
                for node in ideas:
                    if search_q.lower() in node.get('label', 'Untitled Node').lower():
                        node['label'] = node.get('label', 'Untitled Node').replace(search_q, replace_q)
                        count += 1
                    if 'description' in node and search_q.lower() in node['description'].lower():
                        node['description'] = node['description'].replace(search_q, replace_q)
                        count += 1
                st.sidebar.success(f"Replaced {count} instances")
                logger.info(f"Search and replace: '{search_q}' to '{replace_q}' - {count} instances replaced")
                if count > 0:
                    save_data(get_store())
                    st.rerun()

    # Import / Export JSON
    with st.sidebar.expander("📂 Import / Export"):
        uploaded = st.file_uploader("Import JSON", type="json")
        if uploaded:
            try:
                data = json.load(uploaded)
                if not isinstance(data, list):
                    st.error("JSON must be a list")
                    logger.error(f"Import failed: JSON not a list. Filename: {uploaded.name}")
                else:
                    save_state_to_history()  # Save current state before import
                    
                    # First pass: validate all nodes and ensure they have IDs
                    validated_data = [validate_node(item, get_next_id, increment_next_id) for item in data]
                    
                    # Second pass: create a label_map with valid nodes
                    label_map = {item.get('label', '').strip().lower(): item.get('id') 
                                for item in validated_data 
                                if item.get('label') and item.get('id') is not None}
                    
                    # Third pass: handle parent relationships
                    for item in validated_data:
                        p = item.get('parent')
                        if isinstance(p, str):
                            item['parent'] = label_map.get(p.strip().lower())
                        recalc_size(item)
                    
                    set_ideas(validated_data)
                    
                    # Safely calculate next_id by filtering out items without an id
                    valid_ids = [i.get('id') for i in validated_data if i.get('id') is not None]
                    get_store()['next_id'] = max(valid_ids, default=-1) + 1
                    
                    # Set central node safely
                    set_central(next((i.get('id') for i in validated_data if i.get('is_central') and i.get('id') is not None), None))
                    save_data(get_store())
                    
                    # Set a flag to reinitialize the message queue after import
                    st.session_state['reinitialize_message_queue'] = True
                    logger.info(f"Setting reinitialize_message_queue flag after import of {len(validated_data)} nodes")
                    
                    logger.info(f"Successfully imported {len(validated_data)} nodes from {uploaded.name}")
                    st.success("Imported bubbles from JSON")
            except Exception as e:
                handle_exception(e)
                logger.error(f"Import error: {str(e)}")

        ideas = get_ideas()
        if ideas:
            export = [item.copy() for item in ideas]
            
            # Log the positions before export
            position_info = []
            for item in export:
                # Use get() method with a default of None to safely access the id
                item['is_central'] = (item.get('id') == get_central())
                
                # Ensure position values are float and show original values for debugging
                orig_x = item.get('x')
                orig_y = item.get('y')
                
                # Validate position data exists
                if 'x' not in item or 'y' not in item or item['x'] is None or item['y'] is None:
                    logger.warning(f"Missing position data in export for node {item.get('id')}, initializing to (0,0)")
                    item['x'] = 0.0
                    item['y'] = 0.0
                
                # Convert to float to ensure proper JSON serialization
                try:
                    item['x'] = float(item['x'])
                    item['y'] = float(item['y'])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid position values in export for node {item.get('id')}, resetting to (0,0)")
                    item['x'] = 0.0
                    item['y'] = 0.0
                
                # Check for changes in value
                if orig_x != item['x'] or orig_y != item['y']:
                    logger.warning(f"Position values changed during export: Node {item.get('id')} from ({orig_x}, {orig_y}) to ({item['x']}, {item['y']})")
                
                # Track position info for logging
                position_info.append(f"Node {item.get('id')} ({item.get('label')}): ({item['x']}, {item['y']})")
            
            # Log the position data for debugging
            logger.info(f"Exporting {len(export)} nodes with positions:")
            for pos in position_info:
                logger.info(f"  {pos}")
                
            # Create filename with timestamp
            export_filename = f"mindmap_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            try:
                # Create JSON data
                json_data = json.dumps(export, indent=2)
                
                st.download_button(
                    "💾 Export JSON",
                    data=json_data,
                    file_name=export_filename,
                    mime="application/json",
                    key="export_json_button",
                    on_click=lambda: logger.info(f"Exported {len(export)} nodes to {export_filename}")
                )
            except Exception as e:
                logger.error(f"Error preparing JSON export: {str(e)}")
                st.error(f"Error exporting JSON: {str(e)}")

    # Add Bubble Form
    with st.sidebar.form("add_bubble_form"):
        st.header("➕ Add Bubble")
        label = st.text_input("Label")
        description = st.text_area("Description (optional)", height=100)
        col1, col2 = st.columns(2)
        urgency = col1.selectbox("Urgency", list(get_theme()['urgency_colors'].keys()))
        
        # Get all tags, including custom ones
        settings = get_store().get('settings', {})
        custom_tags = settings.get('custom_tags', [])
        all_available_tags = [''] + list(TAGS.keys()) + custom_tags
        
        # Display the tags dropdown
        tag = col2.selectbox("Tag", all_available_tags)
        
        parent_label = st.text_input("Parent label (blank → current center)")
        edge_type = st.selectbox("Connection Type", list(get_theme()['edge_colors'].keys()))

        if st.form_submit_button("Add") and label:
            pid = None
            if parent_label.strip():
                pid = next((i['id'] for i in get_ideas() if i['label'].strip() == parent_label.strip()), None)
                if pid is None:
                    st.warning("Parent not found; adding as top-level")
            elif get_central() is not None:
                pid = get_central()

            new_node = {
                'id': get_next_id(),
                'label': label.strip(),
                'description': description,
                'urgency': urgency,
                'tag': tag,
                'parent': pid,
                'edge_type': edge_type if pid is not None else 'default',
                'x': None,
                'y': None
            }
            recalc_size(new_node)
            add_idea(new_node)
            increment_next_id()
            save_data(get_store())
            st.rerun()

    # Undo/Redo buttons
    undo_col, redo_col = st.sidebar.columns(2)
    if undo_col.button("↩️ Undo", disabled=not can_undo()):
        if perform_undo():
            save_data(get_store())
            st.rerun()  # Force a complete rerun to update the network

    if redo_col.button("↪️ Redo", disabled=not can_redo()):
        if perform_redo():
            save_data(get_store())
            st.rerun()  # Force a complete rerun to update the network

    # Keyboard Shortcuts Info
    with st.sidebar.expander("⌨️ Keyboard Shortcuts"):
        st.markdown("""
        - **Double-click**: Edit node
        - **Right-click**: Delete node
        - **Drag**: Move node
        - **Drag near another**: Change parent
        - **Ctrl+Z**: Undo (when focused on canvas)
        - **Ctrl+Y**: Redo (when focused on canvas)
        - **Ctrl+N**: New node (when focused on canvas)
        """)
    
    # Logs section
    with st.sidebar.expander("📊 Logs"):
        st.write("**Current Session Log:**")
        
        # Get list of log files
        log_files = []
        if os.path.exists(logs_dir):
            log_files = sorted([f for f in os.listdir(logs_dir) if f.endswith('.log')], reverse=True)
        
        if log_files:
            # Show current log file
            current_log = log_files[0]
            st.caption(f"Current: {current_log}")
            
            # Add button to create new log
            if st.button("Create New Log"):
                new_log = create_new_log()
                st.success(f"Created new log file: {new_log}")
                st.rerun()
            
            # Option to view the current log
            if st.button("View Current Log"):
                try:
                    with open(os.path.join(logs_dir, current_log), 'r') as f:
                        log_content = f.read()
                    st.text_area("Log Content", log_content, height=300)
                except Exception as e:
                    st.error(f"Error reading log file: {str(e)}")
            
            # Download current log
            try:
                with open(os.path.join(logs_dir, current_log), 'r') as f:
                    log_content = f.read()
                    st.download_button(
                        "💾 Download Current Log",
                        log_content,
                        file_name=current_log,
                        mime="text/plain",
                        key="download_current_log"
                    )
            except Exception as e:
                st.error(f"Error preparing log for download: {str(e)}")
            
            # Previous logs dropdown
            if len(log_files) > 1:
                st.write("**Previous Session Logs:**")
                selected_log = st.selectbox(
                    "Select log file",
                    options=log_files[1:],
                    format_func=lambda x: f"{x.replace('mindmap_session_', '').replace('.log', '')}"
                )
                
                if selected_log:
                    # View selected log
                    if st.button("View Selected Log"):
                        try:
                            with open(os.path.join(logs_dir, selected_log), 'r') as f:
                                log_content = f.read()
                            st.text_area("Previous Log Content", log_content, height=300)
                        except Exception as e:
                            st.error(f"Error reading selected log: {str(e)}")
                    
                    # Download selected log
                    try:
                        with open(os.path.join(logs_dir, selected_log), 'r') as f:
                            log_content = f.read()
                            st.download_button(
                                "💾 Download Selected Log",
                                log_content,
                                file_name=selected_log,
                                mime="text/plain",
                                key="download_selected_log"
                            )
                    except Exception as e:
                        st.error(f"Error preparing selected log for download: {str(e)}")
        else:
            st.info("No log files found.")

    # Edit / Center List
    ideas = get_ideas()
    if ideas:
        # Add custom CSS for better button alignment
        st.markdown("""
        <style>
        div[data-testid="column"] > div > div > div > div > div[data-testid="stButton"] > button {
            width: 100%;
            padding: 0px 5px;
            display: flex;
            justify-content: center;
        }
        </style>
        """, unsafe_allow_html=True)
        
        with st.sidebar.expander("✏️ Node List"):
            # Add search bar inside Node List
            node_search = st.text_input("🔍 Filter nodes", key="node_list_search")
            
            # Filter nodes based on search
            filtered_ideas = ideas
            if node_search:
                filtered_ideas = [
                    node for node in ideas 
                    if node_search.lower() in node.get('label', 'Untitled Node').lower() or 
                    (node.get('description') and node_search.lower() in node['description'].lower()) or
                    (node.get('tag') and node_search.lower() in node['tag'].lower())
                ]
                
                if not filtered_ideas:
                    st.info(f"No nodes match '{node_search}'")
            
            # Display count of filtered nodes
            if node_search and filtered_ideas:
                st.caption(f"Showing {len(filtered_ideas)} of {len(ideas)} nodes")
            
            # List the filtered nodes
            for node in filtered_ideas:
                # Skip any malformed nodes without an ID
                if 'id' not in node:
                    continue
                    
                # More balanced column widths for better alignment
                col1, col2, col3, col4 = st.columns([2.5, 1, 1, 1])
                label_display = node.get('label', 'Untitled Node')
                if node.get('tag'):
                    label_display = f"[{node['tag']}] {label_display}"
                col1.write(label_display)
                
                # Use smaller emoji icons for better alignment with proper classes
                if col2.button("🎯", key=f"center_{node['id']}", help="Center this node", 
                              on_click=lambda id=node['id']: st.session_state.update({'center_node': id})):
                    pass
                
                if col3.button("✏️", key=f"edit_{node['id']}", help="Edit this node",
                              on_click=lambda id=node['id']: st.session_state.update({'edit_node': id})):
                    pass
                
                if col4.button("🗑️", key=f"delete_{node['id']}", help="Delete this node",
                              on_click=lambda id=node['id']: st.session_state.update({'delete_node': id})):
                    pass

    # Handle button actions from session state
    if 'center_node' in st.session_state:
        node_id = st.session_state.pop('center_node')
        if node_id in {n['id'] for n in ideas if 'id' in n}:
            set_central(node_id)
            st.rerun()

    if 'delete_node' in st.session_state:
        node_id = st.session_state.pop('delete_node')
        if node_id in {n['id'] for n in ideas if 'id' in n}:
            save_state_to_history()
            
            # Use the utility function to collect descendants
            to_remove = collect_descendants(node_id, ideas)

            set_ideas([n for n in ideas if 'id' not in n or n['id'] not in to_remove])
            if get_central() in to_remove:
                set_central(None)
            if st.session_state.get('selected_node') in to_remove:
                st.session_state['selected_node'] = None
            st.rerun()

    # Node Edit Modal
    if 'edit_node' in st.session_state and st.session_state['edit_node'] is not None:
        node_id = st.session_state['edit_node']
        node = find_node_by_id(ideas, node_id)

        if node:
            with st.form(key=f"edit_node_{node_id}"):
                st.subheader(f"Edit Node: {node.get('label', 'Untitled Node')}")
                new_label = st.text_input("Label", value=node.get('label', 'Untitled Node'))
                new_description = st.text_area("Description", value=node.get('description', ''), height=150)
                col1, col2 = st.columns(2)
                new_urgency = col1.selectbox("Urgency",
                                            list(get_theme()['urgency_colors'].keys()),
                                            index=list(get_theme()['urgency_colors'].keys()).index(node.get('urgency', 'low')))
                
                # Get all tags, including custom ones
                settings = get_store().get('settings', {})
                custom_tags = settings.get('custom_tags', [])
                all_available_tags = [''] + list(TAGS.keys()) + custom_tags
                
                # Find the index of the current tag or default to empty
                current_tag = node.get('tag', '')
                tag_index = 0
                if current_tag in all_available_tags:
                    tag_index = all_available_tags.index(current_tag)
                
                new_tag = col2.selectbox("Tag",
                                        all_available_tags,
                                        index=tag_index)

                if node['parent'] is not None:
                    parent_node = find_node_by_id(ideas, node['parent'])
                    if parent_node:
                        current_parent = parent_node.get('label', 'Untitled Node')
                    else:
                        current_parent = ""
                    new_parent = st.text_input("Parent label (blank → no parent)", value=current_parent)
                    new_edge_type = st.selectbox("Connection Type",
                                                list(get_theme()['edge_colors'].keys()),
                                                index=list(get_theme()['edge_colors'].keys()).index(node.get('edge_type', 'default')) 
                                                    if node.get('edge_type', 'default') in get_theme()['edge_colors'] 
                                                    else 0)
                else:
                    new_parent = st.text_input("Parent label (blank → no parent)")
                    new_edge_type = st.selectbox("Connection Type", list(get_theme()['edge_colors'].keys()))

                # Form buttons - ensure we have submit buttons
                col1, col2 = st.columns(2)
                submitted = col1.form_submit_button("Save Changes")
                cancelled = col2.form_submit_button("Cancel")
                
                # Handle form submission logic after the form
                if submitted:
                    save_state_to_history()
                    node['label'] = new_label
                    node['description'] = new_description
                    node['urgency'] = new_urgency
                    node['tag'] = new_tag
                    recalc_size(node)

                    # Update parent if needed
                    if new_parent.strip():
                        new_pid = next((i['id'] for i in get_ideas() if i['label'].strip() == new_parent.strip()), None)
                        if new_pid is not None and new_pid != node['id']:  # Prevent self-reference
                            if not is_circular(node['id'], new_pid, ideas):
                                node['parent'] = new_pid
                                node['edge_type'] = new_edge_type
                            else:
                                st.warning("Cannot create circular parent-child relationships")
                        elif new_pid == node['id']:
                            st.warning("Cannot set a node as its own parent.")
                    else:
                        node['parent'] = None
                        node['edge_type'] = 'default'

                    save_data(get_store())
                    st.session_state['edit_node'] = None
                    st.rerun()

                if cancelled:
                    st.session_state['edit_node'] = None
                    st.rerun()

    # Tutorial Prompt When Empty
    if not ideas:
        st.info("Your map is empty! Use the Add Bubble form on the left to get started.")
        with st.expander("Quick Tutorial"):
            st.markdown("""
            ### Getting Started with Enhanced Mind Map

            1. **Add your first bubble** using the form on the left sidebar
            2. **Organize your ideas** by creating parent-child relationships
            3. **Use tags** to categorize different types of nodes
            4. **Set urgency levels** to visually prioritize important ideas
            5. **Add descriptions** to provide more context for each node
            6. **Customize connection types** to show different relationships
            7. **Use the theme selector** to change the visual appearance

            **Interactive Features:**
            - Double-click a node to edit it
            - Right-click a node to delete it
            - Drag nodes to reposition them
            - Drag a node close to another to change its parent
            - Use undo/redo buttons to reverse changes
            """)
        st.stop()

    # Add canvas expansion toggle
    canvas_expanded = st.session_state.get('canvas_expanded', False)
    expand_button = st.button("🔍 Expand Canvas" if not canvas_expanded else "🔍 Collapse Canvas")
    
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

    # Build PyVis Network
    theme = get_theme()
    canvas_height = CANVAS_DIMENSIONS['expanded' if st.session_state.get('canvas_expanded', False) else 'normal']
    
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
        spring_strength=spring_strength,
        damping=NETWORK_CONFIG['damping'],
        overlap=NETWORK_CONFIG['overlap']
    )

    # Add nodes and edges to the network
    id_set = {n['id'] for n in ideas if 'id' in n}
    
    # Get central node
    central_id = get_central()
    logger.info(f"Creating nodes with central node ID: {central_id}")
    
    for n in ideas:
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
    for n in ideas:
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
                            console.log('Found network in canvas, setting as window.visNetwork');
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
    direct_js = """
    <script>
    // Create a hidden form for direct form submissions
    var hiddenForm = document.createElement('form');
    hiddenForm.id = 'hidden-message-form';
    hiddenForm.method = 'GET';
    hiddenForm.target = '_top'; // Target the top window
    hiddenForm.style.display = 'none';

    // Add input fields
    var actionInput = document.createElement('input');
    actionInput.type = 'hidden';
    actionInput.id = 'hidden-action-input';
    actionInput.name = 'action';

    var payloadInput = document.createElement('input');
    payloadInput.type = 'hidden';
    payloadInput.id = 'hidden-payload-input';
    payloadInput.name = 'payload';

    // Add submit button
    var submitButton = document.createElement('button');
    submitButton.type = 'submit';
    submitButton.id = 'hidden-submit-button';
    submitButton.style.display = 'none';

    // Assemble the form
    hiddenForm.appendChild(actionInput);
    hiddenForm.appendChild(payloadInput);
    hiddenForm.appendChild(submitButton);

    // Add form to document
    document.body.appendChild(hiddenForm);
    
    // Store node positions from the server
    window.serverNodePositions = {}; 
    
    // Function to explicitly ensure positions from server data are applied to nodes
    function ensureNodePositionsApplied() {
        if (window.visNetwork && window.serverNodePositions) {
            console.log('🔧 Explicitly applying stored positions to network');
            
            try {
                if (typeof applyStoredPositions === 'function') {
                    // Use the dedicated function if available
                    applyStoredPositions(window.visNetwork, window.serverNodePositions);
                } else {
                    // Manual fallback
                    console.log('📝 Using manual position application');
                    const nodeIds = Object.keys(window.serverNodePositions);
                    console.log(`Applying positions to ${nodeIds.length} nodes`);
                    
                    let appliedCount = 0;
                    nodeIds.forEach(nodeId => {
                        const pos = window.serverNodePositions[nodeId];
                        if (pos && pos.x !== undefined && pos.y !== undefined) {
                            try {
                                const x = parseFloat(pos.x);
                                const y = parseFloat(pos.y);
                                
                                if (!isNaN(x) && !isNaN(y)) {
                                    window.visNetwork.moveNode(nodeId, x, y);
                                    appliedCount++;
                                }
                            } catch (e) {
                                console.error(`Error applying position to node ${nodeId}:`, e);
                            }
                        }
                    });
                    
                    console.log(`Manually applied ${appliedCount} node positions`);
                }
                
                // Force network to redraw
                if (window.visNetwork.redraw) {
                    window.visNetwork.redraw();
                }
                
                console.log('✅ Node positions applied successfully');
                return true;
            } catch (error) {
                console.error('❌ Error applying node positions:', error);
                return false;
            }
        } else {
            console.warn('⚠️ Cannot apply positions: network or positions not available');
            return false;
        }
    }

    // Attach drag end event handler to the vis.js network
    function setupDragEndHandler() {
        if (window.visNetwork) {
            console.log('Adding dragEnd event listener to visNetwork');
            
            // Add the dragEnd event to track node position changes
            window.visNetwork.on('dragEnd', function(params) {
                if (params.nodes && params.nodes.length > 0) {
                    const nodeId = params.nodes[0];
                    const nodePosition = window.visNetwork.getPositions([nodeId])[nodeId];
                    
                    console.log('Node dragged:', nodeId, 'to position:', nodePosition);
                    
                    // Update stored positions
                    if (!window.serverNodePositions) window.serverNodePositions = {};
                    window.serverNodePositions[nodeId] = { 
                        x: nodePosition.x, 
                        y: nodePosition.y 
                    };
                    
                    // Add more detailed logging
                    console.log('Sending position update with payload:', {
                        id: nodeId,
                        x: nodePosition.x,
                        y: nodePosition.y
                    });
                    
                    // Send position update to backend
                    simpleSendMessage('pos', {
                        id: nodeId,
                        x: nodePosition.x,
                        y: nodePosition.y
                    });
                }
            });
            
            console.log('dragEnd event handler attached successfully');
            return true;
        } else {
            console.error('visNetwork not available when trying to attach dragEnd handler');
            return false;
        }
    }

    // Try to set up the handler with retry logic
    var dragEndSetupAttempts = 0;
    var maxDragEndSetupAttempts = 20; // More attempts with longer total wait time
    
    function attemptDragEndSetup() {
        dragEndSetupAttempts++;
        console.log(`Attempt ${dragEndSetupAttempts}/${maxDragEndSetupAttempts} to set up dragEnd handler`);
        
        if (setupDragEndHandler()) {
            console.log('Successfully set up dragEnd handler');
        } else if (dragEndSetupAttempts < maxDragEndSetupAttempts) {
            // Try again after a delay, with increasing wait time
            var delay = 300 + (dragEndSetupAttempts * 100); // Gradually increase delay
            console.log(`Will retry in ${delay}ms...`);
            setTimeout(attemptDragEndSetup, delay);
        } else {
            console.error('Failed to set up dragEnd handler after maximum attempts');
        }
    }
    
    // Start trying to set up the handler
    document.addEventListener('DOMContentLoaded', function() {
        // Initial delay to give network time to initialize
        setTimeout(attemptDragEndSetup, 1000);
        
        // Also watch for the network object to become available
        var networkWatcher = setInterval(function() {
            if (window.visNetwork) {
                clearInterval(networkWatcher);
                console.log('Network detected by watcher, attempting to attach dragEnd handler');
                setupDragEndHandler();
            }
        }, 300);
    });

    // Also add mutation observer to detect when network is added to DOM
    var networkObserver = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes && mutation.addedNodes.length > 0) {
                for (var i = 0; i < mutation.addedNodes.length; i++) {
                    var node = mutation.addedNodes[i];
                    // Check if the added node is the network container or contains it
                    if (node.id === 'mynetwork' || (node.querySelector && node.querySelector('#mynetwork'))) {
                        console.log('Network container detected in DOM via MutationObserver');
                        // Check if we can access the network
                        setTimeout(function() {
                            // Try to detect network after the container is added
                            if (window.visNetwork) {
                                console.log('Network object available after container detection');
                                setupDragEndHandler();
                            } else {
                                // Try to find the network object in other ways
                                var networkDiv = document.getElementById('mynetwork');
                                if (networkDiv) {
                                    console.log('Found network div, looking for network object');
                                    var canvases = networkDiv.querySelectorAll('canvas');
                                    if (canvases.length > 0) {
                                        for (var j = 0; j < canvases.length; j++) {
                                            if (canvases[j].network) {
                                                console.log('Found network object in canvas');
                                                window.visNetwork = canvases[j].network;
                                                setupDragEndHandler();
                                                break;
                                            }
                                        }
                                    }
                                }
                            }
                        }, 500);
                    }
                }
            }
        });
    });
    
    // Start observing document body for changes
    networkObserver.observe(document.body, {
        childList: true,
        subtree: true
    });

    // Create global helper for direct parent-frame communication using pure postMessage
    window.directParentCommunication = {
        sendMessage: function(action, payload) {
            try {
                console.log('POSTMESSAGE: Sending message to parent: ' + action);
                
                // Create the message object
                var message = {
                    source: 'network_canvas',
                    action: action,
                    payload: payload,
                    timestamp: Date.now()
                };
                
                // Send to parent directly - this works even in sandboxed iframes
                window.parent.postMessage(message, '*');
                console.log('POSTMESSAGE: Message sent to parent');
                return true;
            } catch(e) {
                console.error('POSTMESSAGE: Communication failed: ' + e.message);
                return false;
            }
        }
    };

    // Communication helper for sending messages to Streamlit
    function simpleSendMessage(action, payload) {
        try {
            // Package the message with source identifier
            var message = {
                source: 'network_canvas',
                action: action,
                payload: payload,
                timestamp: Date.now()
            };
            
            // Track if any communication method succeeds
            var communicationSucceeded = false;
            
            // Try direct parent communication first (most reliable)
            try {
                const directResult = window.directParentCommunication.sendMessage(action, payload);
                if (directResult) {
                    communicationSucceeded = true;
                    return; // Exit early if successful
                }
            } catch(e) {
                console.error('Direct parent communication failed: ' + e.message);
            }
            
            // Method 1: Send via postMessage (main method)
            try {
                // Try multiple targets (sometimes frames can be nested)
                const targets = [window.parent, window.top, window];
                
                for (let i = 0; i < targets.length; i++) {
                    try {
                        const target = targets[i];
                        if (target && target !== window) {
                            target.postMessage(message, '*');
                            communicationSucceeded = true;
                            break;
                        }
                    } catch (e) {
                        console.error(`Failed to send to target ${i}: ${e.message}`);
                    }
                }
                
                if (!communicationSucceeded) {
                    // Try standard window.parent as last resort
                    window.parent.postMessage(message, '*');
                    communicationSucceeded = true;
                }
            } catch(e) {
                console.error('All postMessage attempts failed: ' + e.message);
            }
            
            // Method 2: Direct URL parameter modification if postMessage failed
            if (!communicationSucceeded) {
                try {
                    var params = new URLSearchParams(window.location.search);
                    params.set('action', action);
                    
                    // Make sure to preserve all payload fields for coordinate calculations
                    if (payload) {
                        // Include canvas dimensions with click coordinates
                        if (payload.x !== undefined && payload.y !== undefined) {
                            var networkDiv = document.getElementById('mynetwork');
                            if (networkDiv) {
                                var rect = networkDiv.getBoundingClientRect();
                                payload.canvasWidth = rect.width;
                                payload.canvasHeight = rect.height;
                            }
                        }
                    }
                    
                    params.set('payload', JSON.stringify(payload));
                    var newUrl = window.top.location.pathname + '?' + params.toString();
                    window.top.location.href = newUrl;
                    communicationSucceeded = true;
                    return; // Success, so return early
                } catch(e) {
                    console.error('URL parameter method failed: ' + e.message);
                }
            }
            
            // Method 3: Try localStorage if available and previous methods failed
            if (!communicationSucceeded && window.localStorage) {
                try {
                    localStorage.setItem('mindmap_message', JSON.stringify(message));
                    localStorage.setItem('mindmap_trigger_reload', Date.now().toString());
                    communicationSucceeded = true;
                } catch(e) {
                    console.error('localStorage method failed: ' + e.message);
                }
            }
            
            // Method 4: Form submission as last resort
            if (!communicationSucceeded) {
                try {
                    var form = document.getElementById('hidden-message-form');
                    var actionInput = document.getElementById('hidden-action-input');
                    var payloadInput = document.getElementById('hidden-payload-input');
                    
                    if (form && actionInput && payloadInput) {
                        actionInput.value = action;
                        payloadInput.value = JSON.stringify(payload);
                        form.submit();
                        communicationSucceeded = true;
                    }
                } catch(e) {
                    console.error('Form submission method failed: ' + e.message);
                }
            }
        } catch(e) {
            console.error('CRITICAL ERROR in simpleSendMessage: ' + e.message);
        }
    }

    // Add a simplified click handler
    document.addEventListener('DOMContentLoaded', function() {
        // Find the canvas container
        var networkDiv = document.getElementById('mynetwork');
        if (!networkDiv) {
            console.error('ERROR: mynetwork div not found');
            return;
        }
        
        // Add the global click handler
        networkDiv.addEventListener('click', function(event) {
            // Get coordinates relative to the container
            var rect = networkDiv.getBoundingClientRect();
            var relX = event.clientX - rect.left;
            var relY = event.clientY - rect.top;
            
            // Send the click event with coordinates
            simpleSendMessage('canvas_click', {
                x: relX,
                y: relY,
                canvasWidth: rect.width,
                canvasHeight: rect.height,
                timestamp: new Date().getTime()
            });
        });
        
        // Add double-click handler for editing
        networkDiv.addEventListener('dblclick', function(event) {
            // Get coordinates relative to the container
            var rect = networkDiv.getBoundingClientRect();
            var relX = event.clientX - rect.left;
            var relY = event.clientY - rect.top;
            
            // Send the double-click event
            simpleSendMessage('canvas_dblclick', {
                x: relX,
                y: relY,
                canvasWidth: rect.width,
                canvasHeight: rect.height,
                timestamp: new Date().getTime()
            });
            
            // Prevent default browser double-click behavior
            event.preventDefault();
        });
        
        // Add context menu handler for deleting
        networkDiv.addEventListener('contextmenu', function(event) {
            // Prevent default browser context menu
            event.preventDefault();
            
            // Get coordinates relative to the container
            var rect = networkDiv.getBoundingClientRect();
            var relX = event.clientX - rect.left;
            var relY = event.clientY - rect.top;
            
            // Confirm deletion
            if (confirm('Delete this bubble?')) {
                // Send the right-click event
                simpleSendMessage('canvas_contextmenu', {
                    x: relX,
                    y: relY,
                    canvasWidth: rect.width,
                    canvasHeight: rect.height,
                    timestamp: new Date().getTime()
                });
            }
            
            return false;
        });
    });
    </script>
    """

    # Add the direct JS right before the closing </body> tag
    modified_html = modified_html.replace('</body>', direct_js + '</body>')

    # Render the modified HTML
    components.html(
        modified_html, 
        height=int(canvas_height.replace("px", "")), 
        scrolling=False
    )

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
                                        to_remove = collect_descendants(node_id, ideas)
                                        
                                        set_ideas([n for n in ideas if 'id' not in n or n['id'] not in to_remove])
                                        
                                        # Update central node if needed
                                        if get_central() in to_remove:
                                            new_central = next((n['id'] for n in ideas if 'id' not in n or n['id'] not in to_remove), None)
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

    # Node details section for both central and selected nodes
    # Use only the central node approach
    display_node = None
    
    if get_central() is not None:
        central_id = get_central()
        logger.info(f"Using central node ID: {central_id}")
        display_node = find_node_by_id(ideas, central_id)
        logger.info(f"Found node for central ID: {display_node is not None}")
    
    # Fallback: If no central node, pick the first node if available
    if display_node is None and ideas:
        # Find first node with a valid ID
        display_node = next((n for n in ideas if 'id' in n), None)
        if display_node:
            selected_node_temp = display_node['id']
            logger.info(f"No central node, using fallback node ID: {selected_node_temp}")
            # Set as central node
            set_central(selected_node_temp)

    # Debug output for ideas
    logger.info(f"Total nodes in ideas: {len(ideas)}")
    if not ideas:
        logger.warning("No ideas/nodes found in the store")
    
    # Display color mode legend
    color_mode = get_store().get('settings', {}).get('color_mode', 'urgency')
    col1, col2 = st.columns([3, 1])
    with col1:
        if color_mode == 'urgency':
            st.write("🎨 **Color Mode:** Urgency-based")
        else:
            st.write("🎨 **Color Mode:** Tag-based")
    with col2:
        # Quick toggle button
        if st.button("Toggle Color Mode"):
            settings = get_store().get('settings', {})
            new_mode = 'tag' if color_mode == 'urgency' else 'urgency'
            settings['color_mode'] = new_mode
            save_data(get_store())
            st.rerun()

    if display_node:
        logger.info(f"Displaying node: {display_node['id']} - {display_node.get('label', 'Untitled Node')}")
        # Display node with a clean style, matching the center button approach
        st.subheader(f"📌 Selected: {display_node.get('label', 'Untitled Node')}")

        # Display node details
        if display_node.get('tag'):
            st.write(f"**Tag:** {display_node['tag']}")

        st.write(f"**Urgency:** {display_node.get('urgency', 'medium')}")

        if display_node.get('description'):
            st.markdown("**Description:**")
            st.markdown(display_node['description'])
        else:
            st.markdown("**Description:** *No description available*")

        # Display children
        children = [n for n in ideas if n.get('parent') == display_node['id']]
        if children:
            st.markdown("**Connected Ideas:**")
            for child in children:
                st.markdown(f"- {child['label']} ({child.get('edge_type', 'default')} connection)")
        else:
            st.markdown("**Connected Ideas:** *None*")
    else:
        # If we still don't have a node to display, show a message
        logger.warning("No node available to display")
        st.warning("No node selected. Click on a node in the canvas to view its details.")

    # Add JavaScript to handle postMessage from iframe - using Streamlit's session state
    streamlit_js = """
    <script>
    // Wait for DOM to be fully loaded before running
    document.addEventListener('DOMContentLoaded', function() {
        // Log that this parent window script is loaded
        console.log('Parent window message handler initialized');

        try {
            // Create a visible debug element
            var parentDebugDiv = document.createElement('div');
            parentDebugDiv.id = 'parent-debug';
            parentDebugDiv.style.position = 'fixed';
            parentDebugDiv.style.bottom = '10px';
            parentDebugDiv.style.right = '10px';
            parentDebugDiv.style.backgroundColor = 'rgba(0,0,0,0.7)';
            parentDebugDiv.style.color = 'white';
            parentDebugDiv.style.padding = '10px';
            parentDebugDiv.style.borderRadius = '5px';
            parentDebugDiv.style.fontSize = '12px';
            parentDebugDiv.style.zIndex = '10000';
            parentDebugDiv.style.maxWidth = '300px';
            parentDebugDiv.style.maxHeight = '200px';
            parentDebugDiv.style.overflow = 'auto';
            parentDebugDiv.innerHTML = 'Parent window handler active...';
            
            // Safe DOM insertion
            if (document.body) {
                document.body.appendChild(parentDebugDiv);
                console.log('Debug overlay created successfully');
            } else {
                console.error('Cannot find document.body!');
            }

            function parentDebugLog(message) {
                console.log(message);
                if (parentDebugDiv) {
                    var entry = document.createElement('div');
                    entry.textContent = new Date().toLocaleTimeString() + ': ' + message;
                    parentDebugDiv.appendChild(entry);
                    
                    // Keep only last 10 messages
                    while (parentDebugDiv.childNodes.length > 10) {
                        parentDebugDiv.removeChild(parentDebugDiv.firstChild);
                    }
                } else {
                    console.log('Debug message (no div):', message);
                }
            }

            // Helper to process a message no matter how it was received
            function processMessage(action, payload) {
                try {
                    if (!action) {
                        parentDebugLog('No action provided');
                        return;
                    }
                    
                    parentDebugLog('Processing message: ' + action);
                    
                    // Store in session or local storage as backup
                    try {
                        localStorage.setItem('last_message_action', action);
                        localStorage.setItem('last_message_payload', JSON.stringify(payload));
                        localStorage.setItem('last_message_time', new Date().toISOString());
                    } catch (e) {
                        parentDebugLog('Failed to store in localStorage: ' + e.message);
                    }
                    
                    // Set URL parameters
                    var params = new URLSearchParams(window.location.search);
                    params.set('action', action);
                    params.set('payload', JSON.stringify(payload));
                    
                    // Update URL without navigation
                    try {
                        window.history.pushState({}, '', window.location.pathname + '?' + params.toString());
                        parentDebugLog('URL updated with parameters');
                    } catch (e) {
                        parentDebugLog('Failed to update URL: ' + e.message);
                    }
                    
                    // Force a page reload to process the message
                    parentDebugLog('Reloading page to process message');
                    setTimeout(function() {
                        location.reload();
                    }, 100);
                } catch (e) {
                    parentDebugLog('Error processing message: ' + e.message);
                    console.error(e);
                }
            }

            // Listen for messages from the iframe
            window.addEventListener('message', function(event) {
                console.log('Received message event', event);
                parentDebugLog('Received message: ' + JSON.stringify(event.data).substring(0, 50) + '...');
                
                // Check if message has the right format
                if (event.data) {
                    try {
                        let action, payload;
                        
                        // Try multiple known formats
                        if (event.data.source === 'network_canvas' && event.data.action) {
                            // Standard format
                            action = event.data.action;
                            payload = event.data.payload;
                            parentDebugLog('Recognized standard format message');
                        } else if (event.data.action) {
                            // Alternative format
                            action = event.data.action;
                            payload = event.data.payload;
                            parentDebugLog('Recognized alternative format message');
                        } else if (typeof event.data === 'object') {
                            // Try to infer format
                            if (event.data.type && event.data.payload) {
                                action = event.data.type;
                                payload = event.data.payload;
                                parentDebugLog('Inferred message format from type/payload');
                            } else if (event.data.canvas_click || event.data.canvas_dblclick || event.data.canvas_contextmenu) {
                                // Event-named format
                                const keys = Object.keys(event.data);
                                for (const key of keys) {
                                    if (key.startsWith('canvas_')) {
                                        action = key;
                                        payload = event.data[key];
                                        break;
                                    }
                                }
                                parentDebugLog('Inferred message from event-named keys');
                            }
                        }
                        
                        if (action) {
                            processMessage(action, payload);
                        } else {
                            parentDebugLog('Could not determine message format: ' + JSON.stringify(event.data).substring(0, 100));
                        }
                    } catch (error) {
                        parentDebugLog('ERROR in message processing: ' + error.message);
                        console.error(error);
                    }
                } else {
                    parentDebugLog('Empty message received');
                }
            });
            
            parentDebugLog('Parent handler initialized successfully');
        } catch (setupError) {
            console.error('Critical error in parent handler setup:', setupError);
        }
    });
    </script>
    """

    # Add the Streamlit JS to the page
    st.components.v1.html(streamlit_js, height=0)

    # Include our custom utils.js file to fix the Streamlit namespace error
    with open("src/utils.js", "r") as f:
        utils_js = f.read()
        st.components.v1.html(
            f"""
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
            """, 
            height=0
        )

    # Add debug API for position tracking
    js_debug_code = """
    <script>
    window.positionDebug = {
        trackNodes: {},
        
        // Start tracking a node's position
        trackNode: function(nodeId) {
            if (!nodeId) return;
            
            this.trackNodes[nodeId] = {
                id: nodeId,
                lastPosition: null,
                history: []
            };
            
            console.log(`🔍 Started tracking position for node ${nodeId}`);
            return true;
        },
        
        // Update a tracked node's position (called automatically by the tracking interval)
        updateNodePosition: function(nodeId) {
            if (!this.trackNodes[nodeId] || !window.visNetwork) return;
            
            try {
                const positions = window.visNetwork.getPositions([nodeId]);
                const position = positions[nodeId];
                
                if (!position) return;
                
                // Store position
                const tracker = this.trackNodes[nodeId];
                
                // Only record if position has changed
                if (!tracker.lastPosition || 
                    tracker.lastPosition.x !== position.x || 
                    tracker.lastPosition.y !== position.y) {
                    
                    // Add to history
                    tracker.history.push({
                        timestamp: Date.now(),
                        x: position.x,
                        y: position.y,
                        source: 'auto_check'
                    });
                    
                    // Update last position
                    tracker.lastPosition = { x: position.x, y: position.y };
                    
                    console.log(`🔍 Node ${nodeId} position updated to (${position.x}, ${position.y})`);
                }
            } catch (e) {
                console.error(`Error tracking node ${nodeId} position:`, e);
            }
        },
        
        // Record position update event from dragEnd
        recordDragEvent: function(nodeId, x, y) {
            if (!this.trackNodes[nodeId]) {
                this.trackNode(nodeId);
            }
            
            const tracker = this.trackNodes[nodeId];
            tracker.lastPosition = { x: x, y: y };
            tracker.history.push({
                timestamp: Date.now(),
                x: x,
                y: y,
                source: 'drag_end'
            });
            
            console.log(`🔍 Node ${nodeId} dragged to (${x}, ${y})`);
        },
        
        // Get debugging info
        getDebugInfo: function(nodeId) {
            if (!nodeId) {
                return this.trackNodes;
            }
            
            return this.trackNodes[nodeId] || null;
        },
        
        // Get current position from vis.js
        getCurrentPosition: function(nodeId) {
            if (!window.visNetwork) return null;
            
            try {
                const positions = window.visNetwork.getPositions([nodeId]);
                return positions[nodeId];
            } catch (e) {
                console.error(`Error getting position for node ${nodeId}:`, e);
                return null;
            }
        },
        
        // Run a diagnostic test for node position persistence
        testPositionPersistence: function(nodeId) {
            if (!nodeId || !window.visNetwork) {
                console.error("Cannot test: Missing nodeId or visNetwork");
                return {success: false, error: "Missing nodeId or visNetwork"};
            }
            
            try {
                // Get current position
                const currentPos = this.getCurrentPosition(nodeId);
                if (!currentPos) {
                    return {success: false, error: "Node not found in network"};
                }
                
                console.log(`Current position of node ${nodeId}: (${currentPos.x}, ${currentPos.y})`);
                
                // Modify position slightly
                const newX = currentPos.x + 50;
                const newY = currentPos.y + 50;
                
                // Update position via network
                window.visNetwork.moveNode(nodeId, newX, newY);
                console.log(`Moved node ${nodeId} to (${newX}, ${newY})`);
                
                // Manually trigger position update
                const result = window.directParentCommunication.sendMessage('pos', {
                    id: nodeId,
                    x: newX,
                    y: newY
                });
                
                // Show update result
                console.log(`Position update sent: ${result ? "SUCCESS" : "FAILED"}`);
                
                // Store test data
                const testData = {
                    nodeId: nodeId,
                    originalPosition: currentPos,
                    newPosition: {x: newX, y: newY},
                    updateSent: result,
                    timestamp: new Date().toISOString()
                };
                
                // Store test data in localStorage for verification after reload
                try {
                    localStorage.setItem('position_test_data', JSON.stringify(testData));
                } catch(e) {
                    console.error("Could not save test data:", e);
                }
                
                return {
                    success: true,
                    message: "Position update test completed. Reload page to verify persistence.",
                    testData: testData
                };
            } catch(e) {
                console.error("Position persistence test failed:", e);
                return {success: false, error: e.message};
            }
        },
        
        // Verify persistence after page reload
        verifyPersistence: function() {
            try {
                // Get stored test data
                const testDataStr = localStorage.getItem('position_test_data');
                if (!testDataStr) {
                    return {success: false, message: "No test data found. Run testPositionPersistence first."};
                }
                
                const testData = JSON.parse(testDataStr);
                const nodeId = testData.nodeId;
                
                // Get current position after reload
                if (!window.visNetwork) {
                    return {success: false, message: "Network not available yet. Try again in a moment."};
                }
                
                const currentPos = this.getCurrentPosition(nodeId);
                if (!currentPos) {
                    return {success: false, message: "Node not found after reload"};
                }
                
                // Check if position was maintained
                const expectedX = testData.newPosition.x;
                const expectedY = testData.newPosition.y;
                const currentX = currentPos.x;
                const currentY = currentPos.y;
                
                // Calculate difference (allowing small floating point variations)
                const xDiff = Math.abs(expectedX - currentX);
                const yDiff = Math.abs(expectedY - currentY);
                
                const success = xDiff < 1 && yDiff < 1;
                
                if (success) {
                    console.log(`✅ POSITION PERSISTENCE TEST PASSED! Node ${nodeId} maintained position (${currentX}, ${currentY})`);
                } else {
                    console.error(`❌ POSITION PERSISTENCE TEST FAILED! 
                        Expected: (${expectedX}, ${expectedY})
                        Actual: (${currentX}, ${currentY})
                        Diff: (${xDiff}, ${yDiff})`);
                }
                
                return {
                    success: success,
                    message: success ? "Position successfully maintained!" : "Position not maintained correctly",
                    expected: testData.newPosition,
                    actual: currentPos,
                    diff: {x: xDiff, y: yDiff}
                };
            } catch(e) {
                console.error("Verification failed:", e);
                return {success: false, error: e.message};
            }
        }
    };
    
    // Start automatic position tracking
    setInterval(function() {
        if (window.visNetwork) {
            for (const nodeId in window.positionDebug.trackNodes) {
                window.positionDebug.updateNodePosition(nodeId);
            }
        }
    }, 2000);
    
    // Enhance dragEnd handler to record position events
    if (window.visNetwork) {
        try {
            const origDragEnd = window.visNetwork.eventHandlers['dragEnd'];
            if (origDragEnd) {
                window.visNetwork.off('dragEnd');
                window.visNetwork.on('dragEnd', function(params) {
                    // Call original handler
                    origDragEnd(params);
                    
                    // Record for debugging
                    if (params.nodes && params.nodes.length > 0) {
                        const nodeId = params.nodes[0];
                        const positions = window.visNetwork.getPositions([nodeId]);
                        if (positions && positions[nodeId]) {
                            window.positionDebug.recordDragEvent(
                                nodeId, 
                                positions[nodeId].x, 
                                positions[nodeId].y
                            );
                        }
                    }
                });
                console.log('Enhanced dragEnd handler for position debugging');
            }
        } catch (e) {
            console.error('Error enhancing dragEnd handler:', e);
        }
    }
    </script>
    """
    
    # Render the debug JavaScript
    st.components.v1.html(js_debug_code, height=0)

    # Get network positions for all nodes - add this before the network creation
    node_positions = {}
    for n in ideas:
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
    
    // Debug position data
    if (Object.keys(window.serverNodePositions).length > 0) {{
        console.log('📌 Some position samples:');
        
        // Log first 3 positions as samples
        let count = 0;
        for (const nodeId in window.serverNodePositions) {{
            if (count < 3) {{
                console.log(`Node ${{nodeId}}: (${{window.serverNodePositions[nodeId].x}}, ${{window.serverNodePositions[nodeId].y}})`);
                count++;
            }} else {{
                break;
            }}
        }}
    }}
    </script>
    """
    
    # Add position data initialization to the HTML
    modified_html += position_data_js
    
    # Add code to call ensureNodePositionsApplied
    position_apply_js = """
    <script>
    // Call the position application function when the network is ready
    var positionApplicationAttempts = 0;
    var maxPositionApplicationAttempts = 15;
    
    function attemptPositionApplication() {
        positionApplicationAttempts++;
        console.log(`🔄 Attempt ${positionApplicationAttempts}/${maxPositionApplicationAttempts} to apply node positions`);
        
        if (window.visNetwork && window.serverNodePositions) {
            if (typeof ensureNodePositionsApplied === 'function') {
                const result = ensureNodePositionsApplied();
                if (result) {
                    console.log('✅ Successfully applied node positions on attempt', positionApplicationAttempts);
                    return;
                }
            } else {
                console.warn('⚠️ ensureNodePositionsApplied function not available');
            }
        }
        
        if (positionApplicationAttempts < maxPositionApplicationAttempts) {
            // Try again after delay
            setTimeout(attemptPositionApplication, 500);
        } else {
            console.error('❌ Failed to apply positions after max attempts');
        }
    }
    
    // Start attempts after a short delay to ensure network is initialized
    setTimeout(function() {
        attemptPositionApplication();
    }, 1000);
    
    // Also setup periodic check in case network is recreated
    setInterval(function() {
        if (window.visNetwork && window.serverNodePositions && 
            Object.keys(window.serverNodePositions).length > 0) {
            console.log('⏰ Periodic position application check');
            if (typeof ensureNodePositionsApplied === 'function') {
                ensureNodePositionsApplied();
            }
        }
    }, 5000);
    </script>
    """
    
    # Add position application to the HTML
    modified_html += position_apply_js

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