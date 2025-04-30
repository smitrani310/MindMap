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
    return st.session_state.get('store', {'ideas': [], 'central': None, 'next_id': 0})

def get_ideas():
    """Get ideas from the store."""
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

def set_ideas(ideas):
    """Set the ideas in the store."""
    get_store()['ideas'] = ideas

def add_idea(node):
    """Add an idea to the store."""
    get_store()['ideas'].append(node)

def set_central(mid):
    """Set the central node ID in the store."""
    get_store()['central'] = mid

def set_current_theme(theme_name):
    """Set the current theme in the store."""
    get_store()['current_theme'] = theme_name

def save_data(data):
    """Save data to JSON file, with caching to prevent redundant writes"""
    global _last_save_hash
    
    try:
        # Create a hash of the data to check if it has changed
        data_str = json.dumps(data, sort_keys=True)
        current_hash = hashlib.md5(data_str.encode()).hexdigest()
        
        # Only save if the data has changed
        if current_hash != _last_save_hash:
            with open(DATA_FILE, 'w') as f:
                json.dump(data, f)
            _last_save_hash = current_hash
            logger.info("Data saved successfully")
        else:
            logger.debug("Skipping save - data unchanged")
    except PermissionError as e:
        logger.error(f"Permission error saving data file: {str(e)}")
        st.error(ERROR_MESSAGES['permission_error'])
    except Exception as e:
        logger.error(f"Error saving data: {str(e)}")
        st.error(ERROR_MESSAGES['save_data'].format(error=str(e)))

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