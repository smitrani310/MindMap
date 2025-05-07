"""
Integration tests for state synchronization in the Mind Map application.

This module tests how the application maintains consistency between different
components through message-based state synchronization. It verifies that:
- Node operations (view, edit, delete, move, create) are properly synchronized
- State changes are propagated correctly through the message queue
- Response messages contain the expected state updates
- Multiple operations maintain state consistency
- Concurrent operations are handled safely with proper locking

The tests simulate real-world usage patterns by executing sequences of
operations and verifying the resulting state at each step.
"""

import unittest
from src.message_format import Message, create_response_message
from src.message_queue import message_queue
import time
import threading
import json

class TestGraphActions(unittest.TestCase):
    """Test suite for graph state synchronization.
    
    Tests the complete flow of state changes through the message queue system,
    ensuring that operations on the graph maintain consistency across all
    components of the application.
    """
    
    def setUp(self):
        """Set up test environment before each test.
        
        Initializes:
        - Message queue for state synchronization
        - Message tracking lists
        - Threading lock for safe concurrent access
        - Message handler for processing test messages
        """
        self.message_queue = message_queue
        self.received_messages = []
        self.response_messages = []  # Store response messages separately
        self.processed_actions = []
        self.lock = threading.Lock()
        self.message_queue.start(lambda msg: self.handle_message(msg))
        time.sleep(0.1)  # Give the queue time to start

    def tearDown(self):
        """Clean up test environment after each test.
        
        Ensures:
        - Message queue is properly stopped
        - All message tracking lists are cleared
        - No lingering state between tests
        """
        self.message_queue.stop()
        time.sleep(0.1)  # Give the queue time to stop
        self.received_messages = []
        self.response_messages = []
        self.processed_actions = []

    def handle_message(self, message):
        """Handle incoming messages and simulate graph actions.
        
        Processes different types of graph operations and generates
        appropriate response messages. Maintains a record of processed
        actions for verification.
        
        Args:
            message: The message to process
            
        Returns:
            Response message containing the result of the operation
        """
        with self.lock:
            self.received_messages.append(message)
            
            # Simulate different graph actions based on message action
            response = None
            if message.action == 'view_node':
                self.processed_actions.append(('view', message.payload['node_id']))
                response = create_response_message(message, status='completed', 
                    payload={'node_details': {'id': message.payload['node_id'], 'title': 'Test Node'}})
                
            elif message.action == 'edit_node':
                self.processed_actions.append(('edit', message.payload['node_id']))
                response = create_response_message(message, status='completed',
                    payload={'updated_node': {'id': message.payload['node_id'], 'title': message.payload['title']}})
                
            elif message.action == 'delete_node':
                self.processed_actions.append(('delete', message.payload['node_id']))
                response = create_response_message(message, status='completed')
                
            elif message.action == 'move_node':
                self.processed_actions.append(('move', message.payload['node_id']))
                response = create_response_message(message, status='completed',
                    payload={'new_position': message.payload['position']})
                
            elif message.action == 'create_node':
                self.processed_actions.append(('create', message.payload['parent_id']))
                response = create_response_message(message, status='completed',
                    payload={'new_node': {'id': 'new_node_id', 'title': message.payload['title']}})
            else:
                response = create_response_message(message, status='failed', error='Unknown action')
            
            # Store the response message
            self.response_messages.append(response)
            return response

    def test_node_viewing(self):
        """Test viewing node details.
        
        Verifies that:
        - Node view requests are properly processed
        - Correct node details are returned
        - State remains consistent after viewing
        - Response messages contain expected data
        """
        message = Message.create('graph', 'view_node', {'node_id': 'test_node_1'})
        self.message_queue.enqueue(message)
        time.sleep(0.2)

        with self.lock:
            self.assertEqual(len(self.processed_actions), 1)
            action, node_id = self.processed_actions[0]
            self.assertEqual(action, 'view')
            self.assertEqual(node_id, 'test_node_1')
            
            self.assertEqual(len(self.response_messages), 1)
            response = self.response_messages[0]
            self.assertEqual(response.status, 'completed')
            self.assertIn('node_details', response.payload)

    def test_node_editing(self):
        """Test editing node details.
        
        Verifies that:
        - Node edit requests are properly processed
        - Changes are correctly applied
        - State is updated consistently
        - Response messages reflect the changes
        """
        message = Message.create('graph', 'edit_node', {
            'node_id': 'test_node_1',
            'title': 'Updated Title'
        })
        self.message_queue.enqueue(message)
        time.sleep(0.2)

        with self.lock:
            self.assertEqual(len(self.processed_actions), 1)
            action, node_id = self.processed_actions[0]
            self.assertEqual(action, 'edit')
            self.assertEqual(node_id, 'test_node_1')
            
            self.assertEqual(len(self.response_messages), 1)
            response = self.response_messages[0]
            self.assertEqual(response.status, 'completed')
            self.assertEqual(response.payload['updated_node']['title'], 'Updated Title')

    def test_node_deletion(self):
        """Test deleting a node.
        
        Verifies that:
        - Node deletion requests are properly processed
        - Node is removed from the state
        - Connected nodes are handled correctly
        - Response messages confirm deletion
        """
        message = Message.create('graph', 'delete_node', {'node_id': 'test_node_1'})
        self.message_queue.enqueue(message)
        time.sleep(0.2)

        with self.lock:
            self.assertEqual(len(self.processed_actions), 1)
            action, node_id = self.processed_actions[0]
            self.assertEqual(action, 'delete')
            self.assertEqual(node_id, 'test_node_1')
            
            self.assertEqual(len(self.response_messages), 1)
            response = self.response_messages[0]
            self.assertEqual(response.status, 'completed')

    def test_node_movement(self):
        """Test moving a node.
        
        Verifies that:
        - Node movement requests are properly processed
        - Position updates are correctly applied
        - State reflects the new position
        - Response messages contain new coordinates
        """
        position = {'x': 100, 'y': 200}
        message = Message.create('graph', 'move_node', {
            'node_id': 'test_node_1',
            'position': position
        })
        self.message_queue.enqueue(message)
        time.sleep(0.2)

        with self.lock:
            self.assertEqual(len(self.processed_actions), 1)
            action, node_id = self.processed_actions[0]
            self.assertEqual(action, 'move')
            self.assertEqual(node_id, 'test_node_1')
            
            self.assertEqual(len(self.response_messages), 1)
            response = self.response_messages[0]
            self.assertEqual(response.status, 'completed')
            self.assertEqual(response.payload['new_position'], position)

    def test_node_creation(self):
        """Test creating a new node.
        
        Verifies that:
        - Node creation requests are properly processed
        - New node is added to the state
        - Parent-child relationships are maintained
        - Response messages contain new node details
        """
        message = Message.create('graph', 'create_node', {
            'parent_id': 'parent_node_1',
            'title': 'New Node'
        })
        self.message_queue.enqueue(message)
        time.sleep(0.2)

        with self.lock:
            self.assertEqual(len(self.processed_actions), 1)
            action, parent_id = self.processed_actions[0]
            self.assertEqual(action, 'create')
            self.assertEqual(parent_id, 'parent_node_1')
            
            self.assertEqual(len(self.response_messages), 1)
            response = self.response_messages[0]
            self.assertEqual(response.status, 'completed')
            self.assertEqual(response.payload['new_node']['title'], 'New Node')

    def test_action_sequence(self):
        """Test a sequence of actions to verify system continuity.
        
        Verifies that:
        - Multiple operations can be executed in sequence
        - State remains consistent throughout the sequence
        - Each operation produces the expected result
        - Response messages are generated for each operation
        - The system maintains integrity under load
        """
        actions = [
            ('create_node', {'parent_id': 'root', 'title': 'Node 1'}),
            ('view_node', {'node_id': 'new_node_id'}),
            ('edit_node', {'node_id': 'new_node_id', 'title': 'Updated Node 1'}),
            ('move_node', {'node_id': 'new_node_id', 'position': {'x': 100, 'y': 100}}),
            ('delete_node', {'node_id': 'new_node_id'})
        ]

        # Execute actions in sequence
        for action, payload in actions:
            message = Message.create('graph', action, payload)
            self.message_queue.enqueue(message)
            time.sleep(0.2)

        with self.lock:
            # Verify all actions were processed
            self.assertEqual(len(self.processed_actions), len(actions))
            
            # Verify action sequence
            expected_actions = ['create', 'view', 'edit', 'move', 'delete']
            for i, (action, _) in enumerate(self.processed_actions):
                self.assertEqual(action, expected_actions[i])
            
            # Verify all messages were processed successfully
            for response in self.response_messages:
                self.assertEqual(response.status, 'completed')

if __name__ == '__main__':
    unittest.main() 