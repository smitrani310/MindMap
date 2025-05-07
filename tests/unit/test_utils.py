import sys
from unittest.mock import MagicMock
import pytest
from typing import Dict, Any, Optional

class MockSessionState(dict):
    """Mock implementation of Streamlit's session state.
    
    Provides a dictionary-like object that mimics Streamlit's session state
    functionality for testing purposes. Initializes with default values
    needed for the Mind Map application tests.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize with default values needed for tests
        self['store'] = {
            'ideas': [],      # List of mind map nodes
            'next_id': 1,     # Next available node ID
            'central': None   # ID of central node
        }
        self['history'] = []          # State history for undo/redo
        self['history_index'] = -1    # Current position in history
        
    def __getattr__(self, key):
        """Provide attribute-style access to dictionary items."""
        if key in self:
            return self[key]
        return None

class MockStreamlit:
    """Mock implementation of the Streamlit module.
    
    Provides minimal implementations of Streamlit functions needed for testing.
    Focuses on session state management and error handling capabilities.
    """
    def __init__(self):
        self.session_state = MockSessionState()
        
    def error(self, text):
        """Mock Streamlit's error display."""
        print(f"ST ERROR: {text}")
        
    def rerun(self):
        """Mock Streamlit's page rerun functionality."""
        pass
        
    def exception(self, e):
        """Mock Streamlit's exception display."""
        print(f"ST EXCEPTION: {e}")

# Create the mock instance
mock_st = MockStreamlit()

def _patch_state_functions(monkeypatch):
    """Patch state management functions for testing.
    
    Replaces the actual state management functions with mock implementations
    that use our MockSessionState instead of Streamlit's session state.
    
    Args:
        monkeypatch: pytest's monkeypatch fixture for replacing functions
    """
    from src import state
    
    # Patch get_ideas: Retrieve the list of mind map nodes
    def mock_get_ideas():
        return mock_st.session_state['store']['ideas']
    monkeypatch.setattr(state, 'get_ideas', mock_get_ideas)
    
    # Patch set_ideas: Update the list of mind map nodes
    def mock_set_ideas(ideas):
        mock_st.session_state['store']['ideas'] = ideas
    monkeypatch.setattr(state, 'set_ideas', mock_set_ideas)
    
    # Patch get_central: Get the ID of the central node
    def mock_get_central():
        return mock_st.session_state['store']['central']
    monkeypatch.setattr(state, 'get_central', mock_get_central)
    
    # Patch set_central: Set the central node ID
    def mock_set_central(node_id):
        mock_st.session_state['store']['central'] = node_id
    monkeypatch.setattr(state, 'set_central', mock_set_central)
    
    # Patch get_next_id: Get the next available node ID
    def mock_get_next_id():
        return mock_st.session_state['store']['next_id']
    monkeypatch.setattr(state, 'get_next_id', mock_get_next_id)
    
    # Patch increment_next_id: Increment the next available node ID
    def mock_increment_next_id():
        mock_st.session_state['store']['next_id'] += 1
    monkeypatch.setattr(state, 'increment_next_id', mock_increment_next_id)
    
    # Patch add_idea: Add a new node to the mind map
    def mock_add_idea(idea):
        mock_st.session_state['store']['ideas'].append(idea)
    monkeypatch.setattr(state, 'add_idea', mock_add_idea)
    
    # Patch get_store: Get the entire state store
    def mock_get_store():
        return mock_st.session_state['store']
    monkeypatch.setattr(state, 'get_store', mock_get_store)
    
    # Patch save_data: Mock data persistence
    def mock_save_data(store):
        pass  # No-op in tests
    monkeypatch.setattr(state, 'save_data', mock_save_data)

def _patch_history_functions(monkeypatch):
    """Patch history management functions for testing.
    
    Replaces the actual history tracking functions with mock implementations
    that use our MockSessionState for undo/redo functionality.
    
    Args:
        monkeypatch: pytest's monkeypatch fixture for replacing functions
    """
    from src import history
    
    # Patch save_state_to_history: Save current state to history
    def mock_save_state_to_history():
        current_ideas = mock_st.session_state['store']['ideas'].copy()
        mock_st.session_state['history'].append(current_ideas)
        mock_st.session_state['history_index'] = len(mock_st.session_state['history']) - 1
    monkeypatch.setattr(history, 'save_state_to_history', mock_save_state_to_history)
    
    # Patch perform_undo: Restore previous state
    def mock_perform_undo():
        if not mock_st.session_state['history'] or mock_st.session_state['history_index'] <= 0:
            return False
            
        mock_st.session_state['history_index'] -= 1
        prev_state = mock_st.session_state['history'][mock_st.session_state['history_index']]
        mock_st.session_state['store']['ideas'] = prev_state.copy()
        return True
    monkeypatch.setattr(history, 'perform_undo', mock_perform_undo)
    
    # Patch perform_redo: Restore next state
    def mock_perform_redo():
        if (not mock_st.session_state['history'] or 
                mock_st.session_state['history_index'] >= len(mock_st.session_state['history']) - 1):
            return False
            
        mock_st.session_state['history_index'] += 1
        next_state = mock_st.session_state['history'][mock_st.session_state['history_index']]
        mock_st.session_state['store']['ideas'] = next_state.copy()
        return True
    monkeypatch.setattr(history, 'perform_redo', mock_perform_redo)

@pytest.fixture(autouse=True)
def mock_streamlit(monkeypatch):
    """Pytest fixture to automatically patch Streamlit for all tests.
    
    This fixture:
    1. Replaces the real Streamlit module with our mock
    2. Resets session state before each test
    3. Patches all modules that directly use Streamlit
    4. Sets up state and history management mocks
    
    Args:
        monkeypatch: pytest's monkeypatch fixture
    
    Returns:
        MockStreamlit: The mock Streamlit instance
    """
    # Add the mock to sys.modules
    monkeypatch.setitem(sys.modules, 'streamlit', mock_st)
    
    # Reset session state for each test
    mock_st.session_state = MockSessionState()
    
    # Patch modules that directly use streamlit
    from src import handlers
    monkeypatch.setattr(handlers, 'st', mock_st)
    
    try:
        from src import state
        monkeypatch.setattr(state, 'st', mock_st)
        _patch_state_functions(monkeypatch)
    except (ImportError, AttributeError) as e:
        print(f"Error patching state: {e}")
        
    try:
        from src import history
        monkeypatch.setattr(history, 'st', mock_st)
        _patch_history_functions(monkeypatch)
    except (ImportError, AttributeError) as e:
        print(f"Error patching history: {e}")
    
    return mock_st

# Test Helper Functions
def set_test_ideas(ideas):
    """Set the current mind map nodes for testing.
    
    Args:
        ideas: List of node dictionaries to set as current ideas
    """
    mock_st.session_state['store']['ideas'] = ideas
    
def get_test_ideas():
    """Get the current mind map nodes.
    
    Returns:
        List of current node dictionaries
    """
    return mock_st.session_state['store']['ideas']
    
def set_test_central(node_id):
    """Set the central node for testing.
    
    Args:
        node_id: ID of the node to set as central
    """
    mock_st.session_state['store']['central'] = node_id
    
def get_test_central():
    """Get the current central node ID.
    
    Returns:
        ID of the current central node
    """
    return mock_st.session_state['store']['central'] 