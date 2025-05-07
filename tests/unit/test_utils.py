import sys
from unittest.mock import MagicMock
import pytest
from typing import Dict, Any, Optional

# Mock session state
class MockSessionState(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize with default values needed for tests
        self['store'] = {
            'ideas': [],
            'next_id': 1,
            'central': None
        }
        self['history'] = []
        self['history_index'] = -1
        
    def __getattr__(self, key):
        if key in self:
            return self[key]
        return None

# Create a mock Streamlit module
class MockStreamlit:
    def __init__(self):
        self.session_state = MockSessionState()
        
    def error(self, text):
        # Just log errors during tests
        print(f"ST ERROR: {text}")
        
    def rerun(self):
        # No-op in tests
        pass
        
    def exception(self, e):
        # Just log exceptions during tests
        print(f"ST EXCEPTION: {e}")

# Create the mock instance
mock_st = MockStreamlit()

# Mock implementations of state functions
def _patch_state_functions(monkeypatch):
    """Patch state functions to use our mock session state."""
    from src import state
    
    # Patch get_ideas
    def mock_get_ideas():
        return mock_st.session_state['store']['ideas']
    monkeypatch.setattr(state, 'get_ideas', mock_get_ideas)
    
    # Patch set_ideas
    def mock_set_ideas(ideas):
        mock_st.session_state['store']['ideas'] = ideas
    monkeypatch.setattr(state, 'set_ideas', mock_set_ideas)
    
    # Patch get_central
    def mock_get_central():
        return mock_st.session_state['store']['central']
    monkeypatch.setattr(state, 'get_central', mock_get_central)
    
    # Patch set_central
    def mock_set_central(node_id):
        mock_st.session_state['store']['central'] = node_id
    monkeypatch.setattr(state, 'set_central', mock_set_central)
    
    # Patch get_next_id
    def mock_get_next_id():
        return mock_st.session_state['store']['next_id']
    monkeypatch.setattr(state, 'get_next_id', mock_get_next_id)
    
    # Patch increment_next_id
    def mock_increment_next_id():
        mock_st.session_state['store']['next_id'] += 1
    monkeypatch.setattr(state, 'increment_next_id', mock_increment_next_id)
    
    # Patch add_idea
    def mock_add_idea(idea):
        mock_st.session_state['store']['ideas'].append(idea)
    monkeypatch.setattr(state, 'add_idea', mock_add_idea)
    
    # Patch get_store
    def mock_get_store():
        return mock_st.session_state['store']
    monkeypatch.setattr(state, 'get_store', mock_get_store)
    
    # Patch save_data (no-op in tests)
    def mock_save_data(store):
        pass
    monkeypatch.setattr(state, 'save_data', mock_save_data)

# Mock implementations of history functions
def _patch_history_functions(monkeypatch):
    """Patch history functions to use our mock session state."""
    from src import history
    
    # Patch save_state_to_history
    def mock_save_state_to_history():
        # Just append current ideas to history in tests
        current_ideas = mock_st.session_state['store']['ideas'].copy()
        mock_st.session_state['history'].append(current_ideas)
        mock_st.session_state['history_index'] = len(mock_st.session_state['history']) - 1
    monkeypatch.setattr(history, 'save_state_to_history', mock_save_state_to_history)
    
    # Patch perform_undo
    def mock_perform_undo():
        if not mock_st.session_state['history'] or mock_st.session_state['history_index'] <= 0:
            return False
            
        mock_st.session_state['history_index'] -= 1
        prev_state = mock_st.session_state['history'][mock_st.session_state['history_index']]
        mock_st.session_state['store']['ideas'] = prev_state.copy()
        return True
    monkeypatch.setattr(history, 'perform_undo', mock_perform_undo)
    
    # Patch perform_redo
    def mock_perform_redo():
        if (not mock_st.session_state['history'] or 
                mock_st.session_state['history_index'] >= len(mock_st.session_state['history']) - 1):
            return False
            
        mock_st.session_state['history_index'] += 1
        next_state = mock_st.session_state['history'][mock_st.session_state['history_index']]
        mock_st.session_state['store']['ideas'] = next_state.copy()
        return True
    monkeypatch.setattr(history, 'perform_redo', mock_perform_redo)

# Setup pytest fixture to patch Streamlit
@pytest.fixture(autouse=True)
def mock_streamlit(monkeypatch):
    """Automatically patch streamlit for all tests."""
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

# Test helpers
def set_test_ideas(ideas):
    """Set ideas in the mock session state."""
    mock_st.session_state['store']['ideas'] = ideas
    
def get_test_ideas():
    """Get ideas from the mock session state."""
    return mock_st.session_state['store']['ideas']
    
def set_test_central(node_id):
    """Set central node in the mock session state."""
    mock_st.session_state['store']['central'] = node_id
    
def get_test_central():
    """Get central node from the mock session state."""
    return mock_st.session_state['store']['central'] 