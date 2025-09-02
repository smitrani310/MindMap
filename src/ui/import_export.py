"""Import/Export component for the Enhanced Mind Map application."""

import streamlit as st
import json
import datetime
import logging
from src.integration.service_adapter import get_service_adapter
from src.utils import handle_exception

logger = logging.getLogger(__name__)

def render_import_export():
    """
    Render the import/export functionality in the sidebar.
    """
    adapter = get_service_adapter()
    
    with st.sidebar.expander("📂 Import / Export"):
        uploaded = st.file_uploader("Import JSON", type="json")
        if uploaded:
            try:
                data = json.load(uploaded)
                if not isinstance(data, list):
                    st.error("JSON must be a list")
                    logger.error(f"Import failed: JSON not a list. Filename: {uploaded.name}")
                else:
                    # Validate and process the data
                    validated_data = []
                    for item in data:
                        validated_item = validate_node(item)
                        if validated_item:
                            validated_data.append(validated_item)
                    
                    # Handle parent relationships by label
                    label_map = {item.get('label', '').strip().lower(): item.get('id') 
                                for item in validated_data 
                                if item.get('label') and item.get('id') is not None}
                    
                    for item in validated_data:
                        p = item.get('parent')
                        if isinstance(p, str):
                            item['parent'] = label_map.get(p.strip().lower())
                    
                    # Import using service adapter
                    if adapter.set_ideas(validated_data):
                        # Set central node if specified
                        central_node = next((i for i in validated_data if i.get('is_central')), None)
                        if central_node and central_node.get('id'):
                            adapter.set_central(central_node['id'])
                        
                        logger.info(f"Successfully imported {len(validated_data)} nodes from {uploaded.name}")
                        st.success(f"Imported {len(validated_data)} bubbles from JSON")
                        st.rerun()
                    else:
                        st.error("Failed to import data")
                        
            except Exception as e:
                handle_exception(e)
                logger.error(f"Import error: {str(e)}")

        ideas = adapter.get_ideas()
        if ideas:
            export = []
            central_id = adapter.get_central()
            
            # Prepare export data
            for item in ideas:
                export_item = item.copy()
                export_item['is_central'] = (item.get('id') == central_id)
                
                # Ensure position values are properly formatted
                if 'x' not in export_item or 'y' not in export_item or export_item['x'] is None or export_item['y'] is None:
                    logger.warning(f"Missing position data in export for node {item.get('id')}, initializing to (0,0)")
                    export_item['x'] = 0.0
                    export_item['y'] = 0.0
                
                # Convert to float to ensure proper JSON serialization
                try:
                    export_item['x'] = float(export_item['x'])
                    export_item['y'] = float(export_item['y'])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid position values in export for node {item.get('id')}, resetting to (0,0)")
                    export_item['x'] = 0.0
                    export_item['y'] = 0.0
                
                export.append(export_item)
            
            # Log the position data for debugging
            logger.info(f"Exporting {len(export)} nodes with positions:")
            for item in export:
                logger.info(f"  Node {item.get('id')} ({item.get('label')}): ({item['x']}, {item['y']})")
                
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

def validate_node(item):
    """
    Validate a node and ensure it has all required properties.
    """
    if not isinstance(item, dict):
        return None
    
    # Create a copy to avoid modifying the original
    node = item.copy()
    
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
    
    # Initialize position to 0 if missing
    if 'x' not in node or node['x'] is None:
        node['x'] = 0.0
    
    if 'y' not in node or node['y'] is None:
        node['y'] = 0.0
    
    return node 