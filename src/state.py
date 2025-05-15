# State management helpers for MindMap

import streamlit as st
import json
import os
import logging
import hashlib
from src.config import DATA_FILE, ERROR_MESSAGES

logger = logging.getLogger(__name__)

# Cache for data hashing to prevent redundant saves
_last_save_hash = None

def get_store():
    """Get the store from session state."""
    if 'store' not in st.session_state:
        st.session_state['store'] = {'ideas': [], 'central': None, 'next_id': 0}
    return st.session_state['store']

def get_ideas():
    """Get all ideas from the store."""
    return get_store().get('ideas', [])

def get_central():
    """Get the central node ID from the store."""
    return get_store().get('central')

def get_next_id():
    """Get the next ID from the store."""
    return get_store().get('next_id', 0)

def increment_next_id():
    """Increment the next ID in the store."""
    get_store()['next_id'] = get_next_id() + 1

def get_current_theme():
    """Get the current theme from the store."""
    return get_store().get('current_theme', 'default')

def set_ideas(ideas_list):
    """Set the ideas in the store."""
    # Import utility function
    from src.node_utils import validate_node
    
    # Validate each node in the list
    validated_ideas = [validate_node(node, get_next_id, increment_next_id) for node in ideas_list]
    
    # Update the store with validated nodes
    get_store()['ideas'] = validated_ideas
    
    # Make sure changes are persisted to the data file
    save_data(get_store())

def add_idea(node):
    """Add an idea to the store."""
    store = get_store()
    if 'ideas' not in store:
        store['ideas'] = []
    
    # Import utility function
    from src.node_utils import validate_node
    
    # Validate the node before adding
    validated_node = validate_node(node, get_next_id, increment_next_id)
    store['ideas'].append(validated_node)
    save_data(store)  # Save state changes automatically

def set_central(mid):
    """Set the central node ID in the store."""
    get_store()['central'] = mid

def set_current_theme(theme_name):
    """Set the current theme in the store."""
    get_store()['current_theme'] = theme_name

def update_idea(node_id, updates):
    """Update an idea in the store."""
    store = get_store()
    ideas = store.get('ideas', [])
    for node in ideas:
        if node['id'] == node_id:
            node.update(updates)
            break
    store['ideas'] = ideas
    save_data(store)  # Save state changes automatically

def save_data(data):
    """Save app data to file."""
    try:
        # Log what we're about to save
        ideas = data.get('ideas', [])
        logger.debug(f"Saving data with {len(ideas)} nodes")
        
        # Validate positions for all nodes before saving
        for node in ideas:
            # Check if node has position data
            if 'x' not in node or 'y' not in node or node['x'] is None or node['y'] is None:
                logger.warning(f"Node {node.get('id', 'unknown')} missing position data, initializing to (0,0)")
                node['x'] = 0.0
                node['y'] = 0.0
            
            # Ensure positions are float (not strings or other types)
            try:
                node['x'] = float(node['x'])
                node['y'] = float(node['y'])
            except (ValueError, TypeError):
                logger.warning(f"Invalid position values for node {node.get('id', 'unknown')}, resetting to (0,0)")
                node['x'] = 0.0
                node['y'] = 0.0
        
        # Log position data for debugging
        position_data = {node.get('id'): (node.get('x'), node.get('y')) for node in ideas if 'id' in node}
        logger.debug(f"Node positions before saving: {position_data}")
        
        # Serialize the data to JSON
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        logger.debug("Save complete")
        return True
    except Exception as e:
        logger.error(f"Error saving data: {str(e)}")
        return False

def load_data():
    """Load data from JSON file if it exists"""
    global _last_save_hash
    
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                
                # Update the hash cache
                data_str = json.dumps(data, sort_keys=True)
                _last_save_hash = hashlib.md5(data_str.encode()).hexdigest()
                
                return data
        logger.info("Data file not found, using default settings")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in data file: {str(e)}")
        st.error(ERROR_MESSAGES['invalid_json'])
        return None
    except PermissionError as e:
        logger.error(f"Permission error accessing data file: {str(e)}")
        st.error(ERROR_MESSAGES['permission_error'])
        return None
    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")
        st.error(ERROR_MESSAGES['load_data'].format(error=str(e)))
        return None 