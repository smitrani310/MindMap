import unittest
import time
from src.message_format import Message
from src.message_queue import message_queue
import threading
import json

class TestStateSync(unittest.TestCase):
    def setUp(self):
        self.message_queue = message_queue
        self.frontend_state = {
            'nodes': {},
            'selectedNode': None
        }
        self.backend_state = {
            'ideas': [],
            'selected_node': None
        }
        self.lock = threading.Lock()
        self.message_queue.start(lambda msg: self.handle_message(msg))
        time.sleep(0.1)  # Give the queue time to start

    def tearDown(self):
        self.message_queue.stop()
        time.sleep(0.1)  # Give the queue time to stop
        self.frontend_state = {'nodes': {}, 'selectedNode': None}
        self.backend_state = {'ideas': [], 'selected_node': None}

    def handle_message(self, message):
        """Handle incoming messages and update states."""
        with self.lock:
            if message.action == 'create_node':
                # Update both states
                node_id = f"node_{len(self.backend_state['ideas']) + 1}"
                node_data = {
                    'id': node_id,
                    'label': message.payload['title'],
                    'parent': message.payload['parent_id']
                }
                
                # Update backend state
                self.backend_state['ideas'].append(node_data)
                
                # Update frontend state
                self.frontend_state['nodes'][node_id] = {
                    'id': node_id,
                    'title': message.payload['title'],
                    'parentId': message.payload['parent_id']
                }
                
                return Message.create('backend', 'create_node_response', {
                    'new_node': node_data
                })
                
            elif message.action == 'select_node':
                node_id = message.payload['node_id']
                
                # Update both states
                self.frontend_state['selectedNode'] = node_id
                self.backend_state['selected_node'] = node_id
                
                return Message.create('backend', 'select_node_response', {
                    'selected_node': node_id
                })
                
            elif message.action == 'edit_node':
                node_id = message.payload['node_id']
                new_title = message.payload['title']
                
                # Update both states
                if node_id in self.frontend_state['nodes']:
                    self.frontend_state['nodes'][node_id]['title'] = new_title
                
                for idea in self.backend_state['ideas']:
                    if idea['id'] == node_id:
                        idea['label'] = new_title
                        break
                
                return Message.create('backend', 'edit_node_response', {
                    'updated_node': {'id': node_id, 'title': new_title}
                })
                
            elif message.action == 'delete_node':
                node_id = message.payload['node_id']
                
                # Update both states
                if node_id in self.frontend_state['nodes']:
                    del self.frontend_state['nodes'][node_id]
                    if self.frontend_state['selectedNode'] == node_id:
                        self.frontend_state['selectedNode'] = None
                
                self.backend_state['ideas'] = [
                    idea for idea in self.backend_state['ideas']
                    if idea['id'] != node_id
                ]
                if self.backend_state['selected_node'] == node_id:
                    self.backend_state['selected_node'] = None
                
                return Message.create('backend', 'delete_node_response', {})
            
            return Message.create('backend', 'error_response', {
                'error': 'Unknown action'
            })

    def test_node_creation_sync(self):
        """Test state synchronization during node creation."""
        # Create a node
        message = Message.create('frontend', 'create_node', {
            'title': 'Test Node',
            'parent_id': 'root'
        })
        self.message_queue.enqueue(message)
        time.sleep(0.2)

        with self.lock:
            # Verify frontend state
            self.assertEqual(len(self.frontend_state['nodes']), 1)
            node_id = list(self.frontend_state['nodes'].keys())[0]
            self.assertEqual(self.frontend_state['nodes'][node_id]['title'], 'Test Node')
            
            # Verify backend state
            self.assertEqual(len(self.backend_state['ideas']), 1)
            self.assertEqual(self.backend_state['ideas'][0]['label'], 'Test Node')

    def test_node_selection_sync(self):
        """Test state synchronization during node selection."""
        # First create a node
        create_message = Message.create('frontend', 'create_node', {
            'title': 'Test Node',
            'parent_id': 'root'
        })
        self.message_queue.enqueue(create_message)
        time.sleep(0.2)

        # Then select the node
        node_id = list(self.frontend_state['nodes'].keys())[0]
        select_message = Message.create('frontend', 'select_node', {
            'node_id': node_id
        })
        self.message_queue.enqueue(select_message)
        time.sleep(0.2)

        with self.lock:
            # Verify frontend state
            self.assertEqual(self.frontend_state['selectedNode'], node_id)
            
            # Verify backend state
            self.assertEqual(self.backend_state['selected_node'], node_id)

    def test_node_editing_sync(self):
        """Test state synchronization during node editing."""
        # First create a node
        create_message = Message.create('frontend', 'create_node', {
            'title': 'Test Node',
            'parent_id': 'root'
        })
        self.message_queue.enqueue(create_message)
        time.sleep(0.2)

        # Then edit the node
        node_id = list(self.frontend_state['nodes'].keys())[0]
        edit_message = Message.create('frontend', 'edit_node', {
            'node_id': node_id,
            'title': 'Updated Node'
        })
        self.message_queue.enqueue(edit_message)
        time.sleep(0.2)

        with self.lock:
            # Verify frontend state
            self.assertEqual(self.frontend_state['nodes'][node_id]['title'], 'Updated Node')
            
            # Verify backend state
            self.assertEqual(self.backend_state['ideas'][0]['label'], 'Updated Node')

    def test_node_deletion_sync(self):
        """Test state synchronization during node deletion."""
        # First create a node
        create_message = Message.create('frontend', 'create_node', {
            'title': 'Test Node',
            'parent_id': 'root'
        })
        self.message_queue.enqueue(create_message)
        time.sleep(0.2)

        # Select the node
        node_id = list(self.frontend_state['nodes'].keys())[0]
        select_message = Message.create('frontend', 'select_node', {
            'node_id': node_id
        })
        self.message_queue.enqueue(select_message)
        time.sleep(0.2)

        # Then delete the node
        delete_message = Message.create('frontend', 'delete_node', {
            'node_id': node_id
        })
        self.message_queue.enqueue(delete_message)
        time.sleep(0.2)

        with self.lock:
            # Verify frontend state
            self.assertEqual(len(self.frontend_state['nodes']), 0)
            self.assertIsNone(self.frontend_state['selectedNode'])
            
            # Verify backend state
            self.assertEqual(len(self.backend_state['ideas']), 0)
            self.assertIsNone(self.backend_state['selected_node'])

    def test_state_sync_sequence(self):
        """Test state synchronization during a sequence of operations."""
        # Create initial node
        create_message = Message.create('frontend', 'create_node', {
            'title': 'Test Node',
            'parent_id': 'root'
        })
        self.message_queue.enqueue(create_message)
        time.sleep(0.2)

        node_id = list(self.frontend_state['nodes'].keys())[0]

        # Perform sequence of operations
        operations = [
            ('select_node', {'node_id': node_id}),
            ('edit_node', {'node_id': node_id, 'title': 'Updated Node'}),
            ('delete_node', {'node_id': node_id})
        ]

        for action, payload in operations:
            message = Message.create('frontend', action, payload)
            self.message_queue.enqueue(message)
            time.sleep(0.2)

        with self.lock:
            # Verify final states
            self.assertEqual(len(self.frontend_state['nodes']), 0)
            self.assertIsNone(self.frontend_state['selectedNode'])
            self.assertEqual(len(self.backend_state['ideas']), 0)
            self.assertIsNone(self.backend_state['selected_node'])

if __name__ == '__main__':
    unittest.main() 