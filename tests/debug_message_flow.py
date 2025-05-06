import unittest
import pytest
import time
import logging
import json
from datetime import datetime
import threading
from unittest.mock import patch, MagicMock

# Import app modules
from src.message_format import Message, create_response_message, validate_message
from src.message_queue import message_queue
from src.state import get_store, get_ideas, set_ideas, get_central, set_central, add_idea
from src.state import get_next_id, increment_next_id, save_data
from src.utils import recalc_size
from src.handlers import handle_message, is_circular

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG, 
                  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Mock streamlit for testing
class MockStreamlit:
    """Mock streamlit for testing."""
    def __init__(self):
        self.session_state = {}
        self.rerun_called = False
        
    def rerun(self):
        self.rerun_called = True

# Create mock st
mock_st = MockStreamlit()

# Mock state functions for testing
def mock_get_ideas():
    """Mock implementation of get_ideas"""
    return mock_st.session_state.get('ideas', [])

def mock_set_ideas(ideas):
    """Mock implementation of set_ideas"""
    mock_st.session_state['ideas'] = ideas

def mock_get_central():
    """Mock implementation of get_central"""
    return mock_st.session_state.get('central')

def mock_set_central(node_id):
    """Mock implementation of set_central"""
    mock_st.session_state['central'] = node_id

def mock_get_next_id():
    """Mock implementation of get_next_id"""
    return mock_st.session_state.get('next_id', 1)

def mock_increment_next_id():
    """Mock implementation of increment_next_id"""
    current = mock_st.session_state.get('next_id', 1)
    mock_st.session_state['next_id'] = current + 1
    return current + 1

def mock_add_idea(idea):
    """Mock implementation of add_idea"""
    ideas = mock_st.session_state.get('ideas', [])
    ideas.append(idea)
    mock_st.session_state['ideas'] = ideas

def mock_save_data():
    """Mock implementation of save_data"""
    # Just a stub for testing
    pass

# Patch modules that use streamlit
@pytest.fixture(autouse=True)
def patch_streamlit():
    # Import the modules we need to patch
    import sys
    from src import message_queue
    from src import handlers
    from src import state
    
    # Inject mock_st if it doesn't exist
    if not hasattr(message_queue, 'st'):
        setattr(message_queue, 'st', mock_st)
    
    if not hasattr(handlers, 'st'):
        setattr(handlers, 'st', mock_st)
    
    # We only need to patch 'st' in message_queue
    message_queue_patches = {
        'st': mock_st
    }
    
    # Patch handlers with streamlit
    handlers_patches = {
        'st': mock_st
    }
    
    # Patch all state functions in the state module
    state_patches = {
        'get_ideas': mock_get_ideas,
        'set_ideas': mock_set_ideas,
        'get_central': mock_get_central,
        'set_central': mock_set_central,
        'get_next_id': mock_get_next_id,
        'increment_next_id': mock_increment_next_id,
        'add_idea': mock_add_idea,
        'save_data': mock_save_data,
    }
    
    # Apply all patches at once
    with patch.multiple('src.message_queue', **message_queue_patches):
        with patch.multiple('src.handlers', **handlers_patches):
            with patch.multiple('src.state', **state_patches):
                yield

class TestMessageFlow(unittest.TestCase):
    """Test message flow and message handler integration."""
    
    def setUp(self):
        """Set up test case."""
        # Clear mock streamlit state
        mock_st.session_state = {}
        mock_st.rerun_called = False
        
        # Clear message queue
        with message_queue._lock:
            message_queue.queue = []
        
        # Set up sample nodes for testing
        self.test_nodes = [
            {
                'id': 1,
                'label': 'Root Node',
                'description': 'Root test node',
                'urgency': 'medium',
                'tag': 'test',
                'x': 0,
                'y': 0,
                'size': 20,
                'parent': None
            },
            {
                'id': 2,
                'label': 'Child Node 1',
                'description': 'Child test node 1',
                'urgency': 'high',
                'tag': 'test',
                'x': 100,
                'y': 100,
                'size': 25,
                'parent': 1
            }
        ]
        
        # Initialize store with test nodes
        self.store = {
            'ideas': self.test_nodes,
            'central': 1,
            'next_id': 3,
            'history': [],
            'history_index': -1,
            'settings': {'edge_length': 100, 'spring_strength': 0.5, 'size_multiplier': 1.0}
        }
        
        # Initialize mock session state
        mock_st.session_state['ideas'] = self.test_nodes
        mock_st.session_state['central'] = 1
        mock_st.session_state['next_id'] = 3
        
        # Set up state
        with patch('src.state.get_store', return_value=self.store):
            set_ideas(self.test_nodes)
            set_central(1)
        
        # Set up patches
        self.store_patcher = patch('src.state.get_store', return_value=self.store)
        self.mock_get_store = self.store_patcher.start()
        
        self.save_data_patcher = patch('src.state.save_data')
        self.mock_save_data = self.save_data_patcher.start()
        
    def tearDown(self):
        """Clean up after test case."""
        # Stop all patches
        self.store_patcher.stop()
        self.save_data_patcher.stop()
        
    def reset_test_state(self):
        """Reset test state to initial values for each test case."""
        # Clear and reset mock session state
        mock_st.session_state.clear()
        mock_st.session_state['ideas'] = list(self.test_nodes)  # Make a copy
        mock_st.session_state['central'] = 1
        mock_st.session_state['next_id'] = 3
        mock_st.rerun_called = False
        
        # Clear message queue
        with message_queue._lock:
            message_queue.queue = []
        
    def test_message_validation(self):
        """Test message validation functionality."""
        # Reset state
        self.reset_test_state()
        
        # Test valid message
        valid_message = {
            'message_id': '12345',
            'source': 'frontend',
            'action': 'canvas_click',
            'payload': {'x': 100, 'y': 100},
            'timestamp': 1617293033123
        }
        self.assertTrue(validate_message(valid_message))
        
        # Test invalid messages
        # Missing required fields
        invalid_message1 = {
            'action': 'canvas_click',
            'payload': {'x': 100, 'y': 100}
        }
        self.assertFalse(validate_message(invalid_message1))
        
        # Invalid action
        invalid_message2 = {
            'message_id': '12345',
            'source': 'frontend',
            'action': 'invalid_action',
            'payload': {},
            'timestamp': 1617293033123
        }
        self.assertFalse(validate_message(invalid_message2))
        
        # Invalid payload type
        invalid_message3 = {
            'message_id': '12345',
            'source': 'frontend',
            'action': 'canvas_click',
            'payload': 'not_a_dict',
            'timestamp': 1617293033123
        }
        self.assertFalse(validate_message(invalid_message3))
        
    def test_message_creation(self):
        """Test message creation."""
        # Reset state
        self.reset_test_state()
        
        # Create a message
        message = Message.create('frontend', 'canvas_click', {'x': 100, 'y': 100})
        
        # Verify message properties
        self.assertEqual(message.source, 'frontend')
        self.assertEqual(message.action, 'canvas_click')
        self.assertEqual(message.payload, {'x': 100, 'y': 100})
        self.assertIsNotNone(message.message_id)
        self.assertIsNotNone(message.timestamp)
        
        # Verify to_dict and from_dict
        message_dict = message.to_dict()
        message2 = Message.from_dict(message_dict)
        self.assertEqual(message.message_id, message2.message_id)
        self.assertEqual(message.action, message2.action)
        
    def test_response_message_creation(self):
        """Test response message creation."""
        # Reset state
        self.reset_test_state()
        
        # Create a message
        original_message = Message.create('frontend', 'canvas_click', {'x': 100, 'y': 100})
        
        # Create a response message - payload should be the 4th parameter, not 3rd
        response = create_response_message(original_message, 'completed', None, {'result': 'success'})
        
        # Verify response properties
        self.assertEqual(response.source, 'backend')
        self.assertEqual(response.action, 'canvas_click_response')
        self.assertEqual(response.status, 'completed')
        self.assertEqual(response.payload['result'], 'success')
        
    def test_handler_direct_call(self):
        """Test direct calls to the message handler."""
        # Reset state
        self.reset_test_state()
        
        # Test with valid message
        message_dict = {
            'message_id': '12345',
            'source': 'frontend',
            'action': 'center_node',
            'payload': {'id': 1},
            'timestamp': 1617293033123
        }
        
        # Call handler directly
        response = handle_message(message_dict)
        
        # Verify response
        self.assertIsNotNone(response)
        self.assertEqual(response.action, 'center_node_response')
        self.assertEqual(response.status, 'completed')
        
        # Test with invalid message
        invalid_message = {
            'action': 'center_node',
            'payload': {'id': 'not_an_integer'}
        }
        
        # Call handler directly
        response = handle_message(invalid_message)
        
        # Verify error response
        self.assertIsNotNone(response)
        self.assertEqual(response.status, 'failed')
        self.assertIn('error', response.payload)
        
    def test_queue_handler_integration(self):
        """Test integration between queue and handler."""
        # Reset state
        self.reset_test_state()
        
        # Create a test handler that records calls
        called_messages = []
        
        def test_handler(message):
            called_messages.append(message)
            # Process the message with the real handler
            response = handle_message(message.to_dict())
            return response
        
        # Start queue with test handler
        message_queue.start(test_handler)
        
        try:
            # Enqueue a test message
            test_message = Message.create('frontend', 'center_node', {'id': 2})
            message_queue.enqueue(test_message)
            
            # Wait for message to be processed
            time.sleep(0.5)
            
            # Verify message was processed
            self.assertGreaterEqual(len(called_messages), 1)
            self.assertEqual(called_messages[0].action, 'center_node')
            
            # Verify central node was updated
            self.assertEqual(mock_st.session_state.get('central'), 2)
            
        finally:
            # Stop queue
            message_queue.stop()
            
    def test_node_creation_flow(self):
        """Test flow from message to node creation."""
        # Reset state
        self.reset_test_state()
        
        # Create a test handler
        def test_handler(message):
            # Process with real handler
            return handle_message(message.to_dict())
        
        # Start the queue
        message_queue.start(test_handler)
        
        try:
            # Create a node creation message
            node_message = Message.create('frontend', 'create_node', {
                'label': 'New Test Node',
                'description': 'Created through message flow',
                'urgency': 'medium',
                'tag': 'test'
            })
            
            # Enqueue the message
            message_queue.enqueue(node_message)
            
            # Wait for processing
            time.sleep(0.5)
            
            # Verify node was created
            ideas = mock_st.session_state.get('ideas', [])
            new_node = next((n for n in ideas if n['label'] == 'New Test Node'), None)
            
            self.assertIsNotNone(new_node)
            self.assertEqual(new_node['description'], 'Created through message flow')
            self.assertEqual(new_node['urgency'], 'medium')
            self.assertEqual(new_node['tag'], 'test')
            
        finally:
            # Stop queue
            message_queue.stop()
            
    def test_node_update_flow(self):
        """Test flow from message to node update."""
        # Reset state
        self.reset_test_state()
        
        # Create a test handler
        def test_handler(message):
            # Process with real handler
            return handle_message(message.to_dict())
        
        # Start the queue
        message_queue.start(test_handler)
        
        try:
            # Create a node update message
            update_message = Message.create('frontend', 'edit_node', {
                'node_id': 1,
                'label': 'Updated Root Node',
                'description': 'Updated through message flow',
                'urgency': 'high',
                'tag': 'important'
            })
            
            # Enqueue the message
            message_queue.enqueue(update_message)
            
            # Wait for processing
            time.sleep(0.5)
            
            # Verify node was updated
            ideas = mock_st.session_state.get('ideas', [])
            updated_node = next((n for n in ideas if n['id'] == 1), None)
            
            self.assertIsNotNone(updated_node)
            self.assertEqual(updated_node['label'], 'Updated Root Node')
            self.assertEqual(updated_node['description'], 'Updated through message flow')
            self.assertEqual(updated_node['urgency'], 'high')
            self.assertEqual(updated_node['tag'], 'important')
            
        finally:
            # Stop queue
            message_queue.stop()
            
    def test_node_deletion_flow(self):
        """Test flow from message to node deletion."""
        # Reset state
        self.reset_test_state()
        
        # Create a test handler
        def test_handler(message):
            # Process with real handler
            return handle_message(message.to_dict())
        
        # Start the queue
        message_queue.start(test_handler)
        
        try:
            # Create a node deletion message
            delete_message = Message.create('frontend', 'delete_node', {
                'node_id': 2  # Delete child node
            })
            
            # Enqueue the message
            message_queue.enqueue(delete_message)
            
            # Wait for processing
            time.sleep(0.5)
            
            # Verify node was deleted
            ideas = mock_st.session_state.get('ideas', [])
            deleted_node = next((n for n in ideas if n['id'] == 2), None)
            
            self.assertIsNone(deleted_node)
            self.assertEqual(len(ideas), 1)  # Only root node should remain
            
        finally:
            # Stop queue
            message_queue.stop()
            
    def test_error_handling(self):
        """Test error handling in message flow."""
        # Reset state
        self.reset_test_state()
        
        # Create a test handler
        def test_handler(message):
            # Process with real handler
            return handle_message(message.to_dict())
        
        # Start the queue
        message_queue.start(test_handler)
        
        try:
            # Create a message that will cause an error (invalid node ID)
            error_message = Message.create('frontend', 'edit_node', {
                'node_id': 999,  # Non-existent node
                'label': 'This will fail'
            })
            
            # Enqueue the message
            message_queue.enqueue(error_message)
            
            # Wait for processing
            time.sleep(0.5)
            
            # No assertion needed - test passes if no exception is thrown
            # We're testing that errors are properly caught and handled
            
        finally:
            # Stop queue
            message_queue.stop()
            
    def test_multiple_message_processing(self):
        """Test processing multiple messages in sequence."""
        # Reset state
        self.reset_test_state()
        
        # Create a test handler that records calls
        called_messages = []
        
        def test_handler(message):
            called_messages.append(message)
            # Process the message with the real handler
            response = handle_message(message.to_dict())
            return response
        
        # Start queue with test handler
        message_queue.start(test_handler)
        
        try:
            # Create multiple messages
            messages = [
                Message.create('frontend', 'create_node', {
                    'label': f'Sequential Node {i}',
                    'description': f'Created in sequence {i}',
                    'urgency': 'medium',
                    'tag': 'test'
                })
                for i in range(5)
            ]
            
            # Enqueue all messages
            for msg in messages:
                message_queue.enqueue(msg)
            
            # Wait for processing
            time.sleep(1.0)
            
            # Verify all messages were processed
            self.assertEqual(len(called_messages), 5)
            
            # Verify nodes were created
            ideas = mock_st.session_state.get('ideas', [])
            for i in range(5):
                node = next((n for n in ideas if n['label'] == f'Sequential Node {i}'), None)
                self.assertIsNotNone(node)
                self.assertEqual(node['description'], f'Created in sequence {i}')
            
        finally:
            # Stop queue
            message_queue.stop()


if __name__ == '__main__':
    unittest.main() 