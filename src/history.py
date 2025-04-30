"""History management for undo/redo functionality."""

from typing import List, Dict, Any
from copy import deepcopy
import streamlit as st

# Maximum number of states to keep in history
MAX_HISTORY_SIZE = 50

def get_history() -> List[Dict[str, Any]]:
    """Get the history stack from session state."""
    return st.session_state.get('store', {}).get('history', [])

def get_history_index() -> int:
    """Get the current history index from session state."""
    return st.session_state.get('store', {}).get('history_index', -1)

def set_history(history: List[Dict[str, Any]]) -> None:
    """Set the history stack in session state."""
    st.session_state['store']['history'] = history

def set_history_index(index: int) -> None:
    """Set the current history index in session state."""
    st.session_state['store']['history_index'] = index

def save_state_to_history() -> None:
    """Save the current state to history."""
    store = st.session_state.get('store', {})
    history = store.get('history', [])
    history_index = store.get('history_index', -1)
    
    # Remove any states after the current index
    if history_index < len(history) - 1:
        history = history[:history_index + 1]
    
    # Save current state with all required fields
    current_state = {
        'ideas': deepcopy(store.get('ideas', [])),
        'central': store.get('central'),
        'next_id': store.get('next_id', 0),
        'settings': deepcopy(store.get('settings', {}))
    }
    
    history.append(current_state)
    
    # Limit history size to prevent memory issues
    if len(history) > MAX_HISTORY_SIZE:
        history = history[-MAX_HISTORY_SIZE:]
        
    set_history(history)
    set_history_index(len(history) - 1)

def can_undo() -> bool:
    """Check if undo is possible."""
    return get_history_index() > 0

def can_redo() -> bool:
    """Check if redo is possible."""
    history = get_history()
    return get_history_index() < len(history) - 1

def perform_undo() -> bool:
    """Perform undo operation."""
    if not can_undo():
        return False
    
    history = get_history()
    history_index = get_history_index()
    
    # Get the previous state
    previous_state = history[history_index - 1]
    
    # Update current state with proper default values
    store = st.session_state['store']
    store['ideas'] = deepcopy(previous_state.get('ideas', []))
    store['central'] = previous_state.get('central')
    store['next_id'] = previous_state.get('next_id', 0)  # Default to 0 if not present
    store['settings'] = deepcopy(previous_state.get('settings', {}))
    
    # Update history index
    set_history_index(history_index - 1)
    
    return True

def perform_redo() -> bool:
    """Perform redo operation."""
    if not can_redo():
        return False
    
    history = get_history()
    history_index = get_history_index()
    
    # Get the next state
    next_state = history[history_index + 1]
    
    # Update current state with proper default values
    store = st.session_state['store']
    store['ideas'] = deepcopy(next_state.get('ideas', []))
    store['central'] = next_state.get('central')
    store['next_id'] = next_state.get('next_id', 0)  # Default to 0 if not present
    store['settings'] = deepcopy(next_state.get('settings', {}))
    
    # Update history index
    set_history_index(history_index + 1)
    
    return True 