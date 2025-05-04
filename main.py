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
from src.utils import hex_to_rgb, get_theme, recalc_size, get_edge_color, get_urgency_color, get_tag_color
from src.themes import THEMES, TAGS, URGENCY_SIZE
from src.handlers import handle_message, handle_exception, is_circular

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
                    if search_q.lower() in node['label'].lower():
                        node['label'] = node['label'].replace(search_q, replace_q)
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
                    label_map = {item['label'].strip().lower(): item['id'] for item in data}
                    for item in data:
                        item.setdefault('x', None)
                        item.setdefault('y', None)
                        item.setdefault('description', '')
                        item.setdefault('tag', '')
                        item.setdefault('edge_type', 'default')
                        p = item.get('parent')
                        if isinstance(p, str):
                            item['parent'] = label_map.get(p.strip().lower())
                        recalc_size(item)
                    set_ideas(data)
                    get_store()['next_id'] = max((i['id'] for i in data), default=-1) + 1
                    set_central(next((i['id'] for i in data if i.get('is_central')), None))
                    save_data(get_store())
                    logger.info(f"Successfully imported {len(data)} nodes from {uploaded.name}")
                    st.success("Imported bubbles from JSON")
            except Exception as e:
                handle_exception(e)
                logger.error(f"Import error: {str(e)}")

        ideas = get_ideas()
        if ideas:
            export = [item.copy() for item in ideas]
            for item in export:
                item['is_central'] = (item['id'] == get_central())
                
            # Create filename with timestamp
            export_filename = f"mindmap_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            st.download_button(
                "💾 Export JSON",
                data=json.dumps(export, indent=2),
                file_name=export_filename,
                mime="application/json",
                on_click=lambda: logger.info(f"Exported {len(export)} nodes to {export_filename}")
            )

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
                with open(os.path.join(logs_dir, current_log), 'r') as f:
                    log_content = f.read()
                st.text_area("Log Content", log_content, height=300)
            
            # Download current log
            with open(os.path.join(logs_dir, current_log), 'r') as f:
                st.download_button(
                    "💾 Download Current Log",
                    f.read(),
                    file_name=current_log,
                    mime="text/plain"
                )
            
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
                        with open(os.path.join(logs_dir, selected_log), 'r') as f:
                            log_content = f.read()
                        st.text_area("Previous Log Content", log_content, height=300)
                    
                    # Download selected log
                    with open(os.path.join(logs_dir, selected_log), 'r') as f:
                        st.download_button(
                            "💾 Download Selected Log",
                            f.read(),
                            file_name=selected_log,
                            mime="text/plain"
                        )
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
                    if node_search.lower() in node['label'].lower() or 
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
                # More balanced column widths for better alignment
                col1, col2, col3, col4 = st.columns([2.5, 1, 1, 1])
                label_display = node['label']
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
        if node_id in {n['id'] for n in ideas}:
            set_central(node_id)
            st.rerun()

    if 'delete_node' in st.session_state:
        node_id = st.session_state.pop('delete_node')
        if node_id in {n['id'] for n in ideas}:
            save_state_to_history()
            to_remove = set()

            def collect_descendants(node_id):
                to_remove.add(node_id)
                for child in [n for n in ideas if n.get('parent') == node_id]:
                    collect_descendants(child['id'])

            collect_descendants(node_id)
            set_ideas([n for n in ideas if n['id'] not in to_remove])
            if get_central() in to_remove:
                set_central(None)
            if st.session_state.get('selected_node') in to_remove:
                st.session_state['selected_node'] = None
            st.rerun()

    # Node Edit Modal
    if 'edit_node' in st.session_state and st.session_state['edit_node'] is not None:
        node_id = st.session_state['edit_node']
        node = next((n for n in ideas if n['id'] == node_id), None)

        if node:
            with st.form(key=f"edit_node_{node_id}"):
                st.subheader(f"Edit Node: {node['label']}")
                new_label = st.text_input("Label", value=node['label'])
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
                    parent_node = next((n for n in ideas if n['id'] == node['parent']), None)
                    if parent_node:
                        current_parent = parent_node['label']
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
    id_set = {n['id'] for n in ideas}
    
    # Get central node
    central_id = get_central()
    logger.info(f"Creating nodes with central node ID: {central_id}")
    
    for n in ideas:
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
            color_hex = get_urgency_color(n['urgency'])
            logger.debug(f"Node {node_id}: Using urgency color {color_hex} for '{n['urgency']}'")

        r, g, b = hex_to_rgb(color_hex)
        bg, bd = f"rgba({r},{g},{b},{RGBA_ALPHA})", f"rgba({r},{g},{b},1)"

        # Apply the size multiplier to make urgency differences more noticeable
        base_size = n['size']
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

    # Add direct event listeners to guarantee they are attached
    direct_js = """
    <script>
    // Debug overlay
    var debugDiv = document.createElement('div');
    debugDiv.id = 'js-debug';
    debugDiv.style.position = 'absolute';
    debugDiv.style.top = '10px';
    debugDiv.style.left = '10px';
    debugDiv.style.backgroundColor = 'rgba(255,255,255,0.8)';
    debugDiv.style.padding = '5px';
    debugDiv.style.borderRadius = '5px';
    debugDiv.style.fontSize = '12px';
    debugDiv.style.zIndex = '1000';
    debugDiv.style.maxWidth = '300px';
    debugDiv.style.maxHeight = '200px';
    debugDiv.style.overflow = 'auto';
    debugDiv.innerHTML = 'JavaScript debugging...';
    document.body.appendChild(debugDiv);

    function debugLog(message) {
        var entry = document.createElement('div');
        entry.textContent = new Date().toLocaleTimeString() + ': ' + message;
        debugDiv.appendChild(entry);
        
        // Keep only last 10 messages
        while (debugDiv.childNodes.length > 10) {
            debugDiv.removeChild(debugDiv.firstChild);
        }
        console.log(message); // Also log to console
    }

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
    debugLog('Hidden form created for communication');

    // Communication helper for sending messages to Streamlit
    function simpleSendMessage(action, payload) {
        try {
            debugLog('Sending message: ' + action);
            
            // Method 1: Try direct navigation with top window
            try {
                debugLog('Trying direct top window navigation for: ' + action);
                var params = new URLSearchParams();
                params.set('action', action);
                params.set('payload', JSON.stringify(payload));
                var fullUrl = window.location.pathname + '?' + params.toString();
                
                // Use parent location to navigate
                window.parent.location.href = fullUrl;
                
                debugLog('Navigated parent window to: ' + fullUrl);
                return; // Exit early if successful
            } catch(e) {
                debugLog('Parent window navigation failed: ' + e.message);
            }
            
            // If parent navigation fails, try postMessage
            try {
                window.parent.postMessage({
                    source: 'network_canvas',
                    action: action,
                    payload: payload
                }, '*');
                debugLog('Message sent via postMessage');
            } catch(e) {
                debugLog('ERROR: All methods failed - ' + e.message);
            }
        } catch(e) {
            debugLog('CRITICAL ERROR in simpleSendMessage: ' + e.message);
        }
    }

    // Add a simplified click handler
    document.addEventListener('DOMContentLoaded', function() {
        debugLog('Setting up direct canvas click handler');
        
        // Find the canvas container
        var networkDiv = document.getElementById('mynetwork');
        if (!networkDiv) {
            debugLog('ERROR: mynetwork div not found');
            return;
        }
        
        // Add the global click handler
        networkDiv.addEventListener('click', function(event) {
            // Get coordinates relative to the container
            var rect = networkDiv.getBoundingClientRect();
            var relX = event.clientX - rect.left;
            var relY = event.clientY - rect.top;
            
            debugLog(`Canvas clicked at: (${relX}, ${relY})`);
            
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
            
            debugLog(`Canvas double-clicked at: (${relX}, ${relY})`);
            
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
            
            debugLog(`Canvas right-clicked at: (${relX}, ${relY})`);
            
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
        
        debugLog('Direct canvas handlers set up successfully');
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
    
    if action:
        logger.info(f"Query parameters received: action={action}, payload={payload_str}")
        try:
            # Parse the payload
            if payload_str:
                payload = json.loads(payload_str)
            else:
                payload = {}
            
            # Create message data structure
            message = {
                'type': action,
                'payload': payload
            }
            logger.info(f"Processing message: {message}")
            
            # Log the current state before processing
            logger.debug(f"Current state before processing: {len(get_ideas())}")
            
            # Handle JavaScript logs
            if action == 'log':
                log_data = payload
                log_level = log_data.get('level', 'info').lower()
                log_message = log_data.get('message', '')
                log_data = log_data.get('data')
                
                if log_level == 'error':
                    logger.error(f"JS: {log_message}", extra={'js_data': log_data})
                elif log_level == 'warning':
                    logger.warning(f"JS: {log_message}", extra={'js_data': log_data})
                elif log_level == 'debug':
                    logger.debug(f"JS: {log_message}", extra={'js_data': log_data})
                else:
                    logger.info(f"JS: {log_message}", extra={'js_data': log_data})

            # Handle canvas click, double-click, and right-click events
            elif action in ['canvas_click', 'canvas_dblclick', 'canvas_contextmenu']:
                # Extract coordinates and canvas dimensions
                click_x = payload.get('x', 0)
                click_y = payload.get('y', 0)
                canvas_width = payload.get('canvasWidth', 800)
                canvas_height = payload.get('canvasHeight', 600)
                
                logger.info(f"Canvas {action} at coordinates: ({click_x}, {click_y})")
                
                # Get all nodes with stored positions
                ideas = get_ideas()
                nodes_with_pos = [n for n in ideas if n.get('x') is not None and n.get('y') is not None]
                
                canvas_action_successful = False
                
                if nodes_with_pos:
                    # Find the closest node by Euclidean distance
                    closest_node = None
                    min_distance = float('inf')
                    
                    for node in nodes_with_pos:
                        node_x = node.get('x', 0)
                        node_y = node.get('y', 0)
                        
                        # Scale the coordinates to match the canvas
                        # This is a rough approximation - might need adjusting
                        node_canvas_x = (node_x + 0.5) * canvas_width
                        node_canvas_y = (node_y + 0.5) * canvas_height
                        
                        # Calculate Euclidean distance
                        distance = ((node_canvas_x - click_x) ** 2 + (node_canvas_y - click_y) ** 2) ** 0.5
                        
                        if distance < min_distance:
                            min_distance = distance
                            closest_node = node
                    
                    # Use a threshold based on the canvas size
                    click_threshold = min(canvas_width, canvas_height) * 0.1  # 10% of the smallest dimension
                    
                    if closest_node and min_distance < click_threshold:
                        node_id = closest_node['id']
                        logger.info(f"Found closest node: {node_id} at distance {min_distance:.2f} (threshold: {click_threshold:.2f})")
                        
                        # Handle different actions
                        if action == 'canvas_click':
                            # Regular click - select and center the node
                            st.session_state.selected_node = node_id
                            st.session_state.show_node_details = True
                            st.session_state.center_node_id = node_id
                            set_central(node_id)
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
                            
                            # Remove node and its descendants
                            to_remove = set()
                            
                            def collect_descendants(nid):
                                to_remove.add(nid)
                                for child in [n for n in ideas if n.get('parent') == nid]:
                                    collect_descendants(child['id'])
                            
                            collect_descendants(node_id)
                            set_ideas([n for n in ideas if n['id'] not in to_remove])
                            
                            if get_central() in to_remove:
                                new_central = next((n['id'] for n in ideas if n['id'] not in to_remove), None)
                                set_central(new_central)
                            
                            logger.info(f"Deleted node {node_id} and {len(to_remove)-1} descendants")
                            canvas_action_successful = True
                    else:
                        logger.warning(f"No node found near click coordinates (closest distance: {min_distance:.2f}, threshold: {click_threshold:.2f})")
                else:
                    logger.warning("No nodes with position data found")
                
                # Show warning message if action failed
                if not canvas_action_successful:
                    st.warning(f"No node found near click position ({click_x:.1f}, {click_y:.1f}). Try clicking closer to a node.")
            
            # Process legacy message types (for backward compatibility)
            elif action == 'select_node':
                node_id = payload.get('id')
                if node_id is not None:
                    node_id = int(node_id)  # Convert to int if needed
                    logger.info(f"Node selected: {node_id}")
                    st.session_state.selected_node = node_id
                    st.session_state.show_node_details = True
                    st.session_state.center_node_id = node_id
            elif action == 'center_node':
                node_id = payload.get('id')
                if node_id is not None:
                    node_id = int(node_id)  # Convert to int if needed
                    logger.info(f"Centering node: {node_id}")
                    st.session_state.center_node_id = node_id
                    set_central(node_id)  # Update the central node
            elif action == 'edit_modal':
                node_id = payload.get('id')
                if node_id is not None:
                    node_id = int(node_id)  # Convert to int if needed
                    logger.info(f"Opening edit modal for node: {node_id}")
                    st.session_state['edit_node'] = node_id
            elif action == 'delete':
                node_id = payload.get('id')
                if node_id is not None:
                    node_id = int(node_id)  # Convert to int if needed
                    logger.info(f"Deleting node: {node_id}")
                    ideas = get_ideas()
                    # Save state before deletion
                    save_state_to_history()
                    # Remove node and its descendants
                    to_remove = set()
                    
                    def collect_descendants(nid):
                        to_remove.add(nid)
                        for child in [n for n in ideas if n.get('parent') == nid]:
                            collect_descendants(child['id'])
                    
                    collect_descendants(node_id)
                    set_ideas([n for n in ideas if n['id'] not in to_remove])
                    if get_central() in to_remove:
                        set_central(None)
            elif action == 'pos':
                logger.info(f"Updating node positions: {payload}")
                for node_id_str, pos in payload.items():
                    try:
                        node_id = int(node_id_str)
                        ideas = get_ideas()
                        for node in ideas:
                            if node['id'] == node_id:
                                node['x'] = pos['x']
                                node['y'] = pos['y']
                                break
                    except (ValueError, KeyError):
                        logger.error(f"Error processing position for node ID {node_id_str}")
            else:
                logger.warning(f"Unknown action type: {action}")
            
            # Log success and save data
            logger.info("Message processed successfully")
            save_data(get_store())
            
            # Clear query parameters after processing
            st.experimental_set_query_params()
            
            # Force a rerun to update the UI immediately
            st.rerun()
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            st.error(f"Error processing message: {str(e)}")
    else:
        logger.debug("No message to process")

    # Node details section for both central and selected nodes
    # Use only the central node approach
    display_node = None
    
    if get_central() is not None:
        central_id = get_central()
        logger.info(f"Using central node ID: {central_id}")
        display_node = next((n for n in ideas if n['id'] == central_id), None)
        logger.info(f"Found node for central ID: {display_node is not None}")
    
    # Fallback: If no central node, pick the first node if available
    if display_node is None and ideas:
        display_node = ideas[0]
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
        logger.info(f"Displaying node: {display_node['id']} - {display_node['label']}")
        # Display node with a clean style, matching the center button approach
        st.subheader(f"📌 Selected: {display_node['label']}")

        # Add buttons for the selected node in a row
        edit_col, delete_col = st.columns(2)
        
        # Edit button
        if edit_col.button("✏️ Edit Selected Node", help="Edit this node's properties"):
            node_id = display_node['id']
            logger.info(f"Opening edit modal for node {node_id} via direct button click")
            st.session_state['edit_node'] = node_id
            st.rerun()
        
        # Delete button
        if delete_col.button("🗑️ Delete Selected Node", type="primary", help="Delete this node and all its descendants"):
            node_id = display_node['id']
            logger.info(f"Deleting node {node_id} via direct button click")
            
            # Save state before deletion
            save_state_to_history()
            
            # Get all nodes
            ideas = get_ideas()
            
            # Remove node and its descendants
            to_remove = set()
            
            def collect_descendants(nid):
                to_remove.add(nid)
                for child in [n for n in ideas if n.get('parent') == nid]:
                    collect_descendants(child['id'])
            
            collect_descendants(node_id)
            set_ideas([n for n in ideas if n['id'] not in to_remove])
            
            # Update central node if needed
            if get_central() in to_remove:
                new_central = next((n['id'] for n in ideas if n['id'] not in to_remove), None)
                set_central(new_central)
            
            logger.info(f"Deleted node {node_id} and {len(to_remove)-1} descendants")
            save_data(get_store())
            st.rerun()

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
    // Log that this parent window script is loaded
    console.log('Parent window message handler initialized');

    // Listen for messages from the iframe
    window.addEventListener('message', function(event) {
        console.log('Parent window received message:', event.data);
        
        // Check if message is from our network canvas
        if (event.data && event.data.source === 'network_canvas') {
            try {
                // Get the action and payload
                var action = event.data.action;
                var payload = event.data.payload;
                
                console.log('Processing message from canvas:', action, payload);
                
                // Display processing information in the page for visibility
                var debugInfo = document.createElement('div');
                debugInfo.style.position = 'fixed';
                debugInfo.style.top = '10px';
                debugInfo.style.right = '10px';
                debugInfo.style.backgroundColor = 'rgba(255, 255, 0, 0.8)';
                debugInfo.style.padding = '10px';
                debugInfo.style.borderRadius = '5px';
                debugInfo.style.zIndex = '9999';
                debugInfo.innerHTML = 'Processing: ' + action + ' at ' + new Date().toLocaleTimeString();
                document.body.appendChild(debugInfo);
                
                // Remove the debug info after 3 seconds
                setTimeout(function() {
                    document.body.removeChild(debugInfo);
                }, 3000);
                
                // Use window.location to navigate with query parameters
                // This is the most reliable way to communicate with Streamlit
                var params = new URLSearchParams();
                params.set('action', action);
                params.set('payload', JSON.stringify(payload));
                
                // Create the URL with the base path and parameters
                var newUrl = window.location.pathname + '?' + params.toString();
                
                // Navigate to the URL with parameters
                console.log('Navigating to:', newUrl);
                window.location.href = newUrl;
            } catch (error) {
                console.error('Error processing message from canvas:', error);
                
                // Display error in the page for visibility
                var errorInfo = document.createElement('div');
                errorInfo.style.position = 'fixed';
                errorInfo.style.top = '10px';
                errorInfo.style.right = '10px';
                errorInfo.style.backgroundColor = 'rgba(255, 0, 0, 0.8)';
                errorInfo.style.color = 'white';
                errorInfo.style.padding = '10px';
                errorInfo.style.borderRadius = '5px';
                errorInfo.style.zIndex = '9999';
                errorInfo.innerHTML = 'Error: ' + error.message;
                document.body.appendChild(errorInfo);
                
                // Remove the error info after 5 seconds
                setTimeout(function() {
                    document.body.removeChild(errorInfo);
                }, 5000);
            }
        }
    });

    // For testing, you can use this function to manually trigger a message
    window.sendTestMessage = function(action, payload) {
        console.log('Sending test message:', action, payload);
        var params = new URLSearchParams();
        params.set('action', action);
        params.set('payload', JSON.stringify(payload));
        
        var newUrl = window.location.pathname + '?' + params.toString();
        window.location.href = newUrl;
    };
    
    // Log that this parent window script has completed initialization
    console.log('Parent window message handler setup complete');
    </script>
    """

    # Add the Streamlit JS to the page
    st.components.v1.html(streamlit_js, height=0)

    # Add an option in the debug tools to switch to direct click mode
    with st.expander("Debug Tools", expanded=True):
        st.write("These tools help diagnose canvas communication issues")
        
        # Enable direct click mode
        if 'direct_click_mode' not in st.session_state:
            st.session_state.direct_click_mode = True
        
        st.session_state.direct_click_mode = st.checkbox(
            "Enable Direct Click Mode (recommended)", 
            value=st.session_state.direct_click_mode,
            help="When enabled, clicks are processed using a simple coordinate-based approach instead of network events"
        )
        
        # Display last message information
        st.write("### Communication Status")
        if 'last_action' not in st.session_state:
            st.session_state.last_action = None
            st.session_state.last_payload = None
            st.session_state.last_message_time = None
        
        if action:
            # Update last message info
            st.session_state.last_action = action
            st.session_state.last_payload = payload_str
            st.session_state.last_message_time = datetime.datetime.now().strftime("%H:%M:%S")
        
        # Display status information
        status_col1, status_col2 = st.columns(2)
        
        with status_col1:
            st.write("**Last Action:**")
            st.code(st.session_state.last_action or "None")
            
            st.write("**Time Received:**")
            st.code(st.session_state.last_message_time or "None")
        
        with status_col2:
            st.write("**Last Payload:**")
            st.code(st.session_state.last_payload or "None", language="json")
        
        # Add a button to clear query parameters
        if st.button("Clear URL Parameters"):
            st.experimental_set_query_params()
            st.success("URL parameters cleared")
            st.rerun()
        
        # Node test section
        st.write("### Node Testing")
        col1, col2 = st.columns(2)
        with col1:
            node_id_for_test = st.number_input("Node ID for test", value=1, min_value=0)
        
        with col2:
            test_action = st.selectbox("Test action", ["select_node", "center_node", "edit_modal", "delete"])
        
        if st.button("Send Test Message"):
            # Use session_state to simulate a message
            if test_action == "select_node" or test_action == "center_node":
                st.session_state.selected_node = node_id_for_test
                st.session_state.show_node_details = True
                st.session_state.center_node_id = node_id_for_test
                set_central(node_id_for_test)
            elif test_action == "edit_modal":
                st.session_state['edit_node'] = node_id_for_test
            elif test_action == "delete":
                ideas = get_ideas()
                node = next((n for n in ideas if n['id'] == node_id_for_test), None)
                if node:
                    # Save state before deletion
                    save_state_to_history()
                    # Remove node and its descendants
                    to_remove = set()
                    
                    def collect_descendants(nid):
                        to_remove.add(nid)
                        for child in [n for n in ideas if n.get('parent') == nid]:
                            collect_descendants(child['id'])
                    
                    collect_descendants(node_id_for_test)
                    set_ideas([n for n in ideas if n['id'] not in to_remove])
                    if get_central() in to_remove:
                        set_central(None)
            
            # Log the test action
            logger.info(f"Test message sent via debug button: {test_action}, node ID: {node_id_for_test}")
            st.success(f"Test message sent: {test_action}, node ID: {node_id_for_test}")
            st.rerun()

    # Add a local storage-based message passing as a fallback method
    direct_js += """
    <script>
    // Add local storage message passing as an additional fallback
    // This helps with certain cross-origin scenarios where other methods fail
    
    // Listen for local storage changes
    window.addEventListener('storage', function(event) {
        if (event.key === 'mindmap_message' && event.newValue) {
            try {
                var message = JSON.parse(event.newValue);
                debugLog('Received message from localStorage: ' + message.action);
                
                // Clear the storage immediately to prevent duplicate handling
                localStorage.removeItem('mindmap_message');
                
                // Process the message locally
                if (typeof simpleSendMessage === 'function') {
                    simpleSendMessage(message.action, message.payload);
                } else {
                    debugLog('ERROR: simpleSendMessage function not available');
                }
            } catch (e) {
                console.error('Error processing localStorage message:', e);
            }
        }
    });
    
    // Add a localStorage communication method
    window.sendViaLocalStorage = function(action, payload) {
        try {
            var message = {
                action: action,
                payload: payload,
                timestamp: new Date().getTime()
            };
            
            // Store the message
            localStorage.setItem('mindmap_message', JSON.stringify(message));
            
            // Trigger storage event in other windows/frames
            // This is needed because storage events only fire in other windows/frames
            localStorage.setItem('mindmap_trigger', Date.now());
            localStorage.removeItem('mindmap_trigger');
            
            return true;
        } catch (e) {
            console.error('Error sending via localStorage:', e);
            return false;
        }
    };
    </script>
    """

except Exception as e:
    logger.error(f"Unhandled exception: {str(e)}")
    logger.error(traceback.format_exc())
    handle_exception(e)