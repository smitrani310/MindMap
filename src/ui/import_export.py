"""Import/Export component for the Enhanced Mind Map application."""

import streamlit as st
import json
import datetime
import logging
from src.state import get_ideas, get_store, set_ideas, set_central, get_central, get_next_id, increment_next_id, save_data
from src.utils import recalc_size, find_node_by_id
from src.history import save_state_to_history
from src.handlers import handle_exception

logger = logging.getLogger(__name__)

def render_import_export():
    """
    Render the import/export functionality in the sidebar.
    """
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

def validate_node(item, get_next_id_func, increment_next_id_func):
    """
    Validate a node and ensure it has all required properties.
    """
    if not isinstance(item, dict):
        return {}
    
    # Create a copy to avoid modifying the original
    node = item.copy()
    
    # Ensure node has an ID
    if 'id' not in node or node['id'] is None:
        node['id'] = get_next_id_func()
        increment_next_id_func()
    
    # Set defaults for other properties if missing
    if 'label' not in node or not node['label']:
        node['label'] = 'Untitled Node'
    
    if 'urgency' not in node:
        node['urgency'] = 'medium'
    
    if 'tag' not in node:
        node['tag'] = ''
    
    if 'description' not in node:
        node['description'] = ''
    
    if 'edge_type' not in node:
        node['edge_type'] = 'default'
    
    # Initialize position to None if missing
    if 'x' not in node or node['x'] is None:
        node['x'] = None
    
    if 'y' not in node or node['y'] is None:
        node['y'] = None
    
    return node 