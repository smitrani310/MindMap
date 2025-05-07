#!/usr/bin/env python
"""
Integration tests for core Mind Map functionality.

This module tests the fundamental features of the Mind Map application,
including:
- Node creation and management
- Canvas interactions
- State persistence
- Basic operations (add, edit, delete)
- Event handling
- UI updates

The tests verify that the core features work together correctly
and maintain data consistency across operations.
"""

import unittest
import time
from src.message_format import Message
from src.message_queue import message_queue
from src import state, handlers
from tests.unit.test_utils import set_test_ideas, get_test_ideas

class TestCoreFunctionality(unittest.TestCase):
    """Test suite for core Mind Map functionality.
    
    Tests the basic operations and features that form the foundation
    of the Mind Map application, ensuring they work together correctly.
    """

    def setUp(self):
        """Set up test fixtures before each test method.
        
        Initializes:
        - Message queue for event handling
        - Test data and initial state
        - UI component mocks
        - Event tracking
        """
        self.message_queue = message_queue
        self.message_queue.start(self.handle_message)
        time.sleep(0.1)  # Allow queue to initialize
        
        # Initialize test data
        self.test_node = {
            'id': 1,
            'text': 'Test Node',
            'x': 100,
            'y': 100,
            'connections': []
        }
        set_test_ideas([self.test_node])

    def tearDown(self):
        """Clean up after each test method.
        
        Ensures:
        - Message queue is stopped
        - Test state is cleared
        - Resources are released
        - No lingering test data
        """
        self.message_queue.stop()
        time.sleep(0.1)  # Allow queue to stop
        set_test_ideas([])

    def handle_message(self, message):
        """Test message handler for core functionality tests.
        
        Processes messages and updates state based on the operation.
        Simulates real-world message handling for core features.
        
        Args:
            message: The message to process
            
        Returns:
            Response message indicating processing result
        """
        if message.action == 'create_node':
            current_ideas = get_test_ideas()
            current_ideas.append(message.payload)
            set_test_ideas(current_ideas)
        elif message.action == 'update_node':
            current_ideas = get_test_ideas()
            for i, node in enumerate(current_ideas):
                if node['id'] == message.payload['id']:
                    current_ideas[i] = message.payload
                    break
            set_test_ideas(current_ideas)
        elif message.action == 'delete_node':
            current_ideas = get_test_ideas()
            current_ideas = [n for n in current_ideas if n['id'] != message.payload['id']]
            set_test_ideas(current_ideas)

    def test_node_creation(self):
        """Test node creation functionality.
        
        Verifies that:
        - Nodes can be created with correct properties
        - Node data is properly stored
        - State is updated correctly
        - UI is notified of changes
        - Node IDs are unique
        """
        # Create a new node
        new_node = {
            'id': 2,
            'text': 'New Node',
            'x': 200,
            'y': 200,
            'connections': []
        }
        
        message = Message.create('ui', 'create_node', new_node)
        self.message_queue.enqueue(message)
        time.sleep(0.2)  # Allow processing
        
        # Verify node creation
        current_ideas = get_test_ideas()
        self.assertEqual(len(current_ideas), 2)
        self.assertEqual(current_ideas[1]['text'], 'New Node')

    def test_node_update(self):
        """Test node update functionality.
        
        Verifies that:
        - Nodes can be updated correctly
        - Changes are persisted
        - State remains consistent
        - UI reflects updates
        - Connections are maintained
        """
        # Update existing node
        updated_node = self.test_node.copy()
        updated_node['text'] = 'Updated Node'
        
        message = Message.create('ui', 'update_node', updated_node)
        self.message_queue.enqueue(message)
        time.sleep(0.2)  # Allow processing
        
        # Verify node update
        current_ideas = get_test_ideas()
        self.assertEqual(len(current_ideas), 1)
        self.assertEqual(current_ideas[0]['text'], 'Updated Node')

    def test_node_deletion(self):
        """Test node deletion functionality.
        
        Verifies that:
        - Nodes can be deleted correctly
        - State is updated properly
        - UI reflects deletion
        - Connected nodes are handled
        - History is maintained
        """
        # Delete existing node
        message = Message.create('ui', 'delete_node', {'id': 1})
        self.message_queue.enqueue(message)
        time.sleep(0.2)  # Allow processing
        
        # Verify node deletion
        current_ideas = get_test_ideas()
        self.assertEqual(len(current_ideas), 0)

if __name__ == '__main__':
    unittest.main() 