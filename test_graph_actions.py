import unittest
from src.message_format import Message, create_response_message
from src.message_queue import message_queue
import time
import threading
import json

class TestGraphActions(unittest.TestCase):
    def setUp(self):
        self.message_queue = message_queue
        self.received_messages = []
        self.response_messages = []  # Store response messages separately
        self.processed_actions = []
        self.lock = threading.Lock()
        self.message_queue.start(lambda msg: self.handle_message(msg))
        time.sleep(0.1)  # Give the queue time to start

    def tearDown(self):
        self.message_queue.stop()
        time.sleep(0.1)  # Give the queue time to stop
        self.received_messages = []
        self.response_messages = []
        self.processed_actions = []

    def handle_message(self, message):
        """Handle incoming messages and simulate graph actions."""
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
        """Test viewing node details."""
        # Send view node request
        message = Message.create('graph', 'view_node', {'node_id': 'test_node_1'})
        self.message_queue.enqueue(message)
        time.sleep(0.2)

        with self.lock:
            self.assertEqual(len(self.processed_actions), 1)
            action, node_id = self.processed_actions[0]
            self.assertEqual(action, 'view')
            self.assertEqual(node_id, 'test_node_1')
            
            # Verify response message
            self.assertEqual(len(self.response_messages), 1)
            response = self.response_messages[0]
            self.assertEqual(response.status, 'completed')
            self.assertIn('node_details', response.payload)

    def test_node_editing(self):
        """Test editing node details."""
        # Send edit node request
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
            
            # Verify response message
            self.assertEqual(len(self.response_messages), 1)
            response = self.response_messages[0]
            self.assertEqual(response.status, 'completed')
            self.assertEqual(response.payload['updated_node']['title'], 'Updated Title')

    def test_node_deletion(self):
        """Test deleting a node."""
        # Send delete node request
        message = Message.create('graph', 'delete_node', {'node_id': 'test_node_1'})
        self.message_queue.enqueue(message)
        time.sleep(0.2)

        with self.lock:
            self.assertEqual(len(self.processed_actions), 1)
            action, node_id = self.processed_actions[0]
            self.assertEqual(action, 'delete')
            self.assertEqual(node_id, 'test_node_1')
            
            # Verify response message
            self.assertEqual(len(self.response_messages), 1)
            response = self.response_messages[0]
            self.assertEqual(response.status, 'completed')

    def test_node_movement(self):
        """Test moving a node."""
        # Send move node request
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
            
            # Verify response message
            self.assertEqual(len(self.response_messages), 1)
            response = self.response_messages[0]
            self.assertEqual(response.status, 'completed')
            self.assertEqual(response.payload['new_position'], position)

    def test_node_creation(self):
        """Test creating a new node."""
        # Send create node request
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
            
            # Verify response message
            self.assertEqual(len(self.response_messages), 1)
            response = self.response_messages[0]
            self.assertEqual(response.status, 'completed')
            self.assertEqual(response.payload['new_node']['title'], 'New Node')

    def test_action_sequence(self):
        """Test a sequence of actions to verify system continuity."""
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