import unittest
import time
from src.message_format import Message
from src.message_queue import message_queue
import threading
import json

class TestCanvasEvents(unittest.TestCase):
    def setUp(self):
        self.message_queue = message_queue
        self.received_messages = []
        self.processed_actions = []
        self.lock = threading.Lock()
        self.message_queue.start(lambda msg: self.handle_message(msg))
        time.sleep(0.1)  # Give the queue time to start

    def tearDown(self):
        self.message_queue.stop()
        time.sleep(0.1)  # Give the queue time to stop
        self.received_messages = []
        self.processed_actions = []

    def handle_message(self, message):
        """Handle incoming messages and simulate graph actions."""
        with self.lock:
            self.received_messages.append(message)
            
            # Convert canvas events to node actions
            if message.action == 'canvas_click':
                # Find nearest node and convert to view_node action
                node_id = self.find_nearest_node(message.payload['x'], message.payload['y'])
                if node_id:
                    self.processed_actions.append(('view', node_id))
                    return Message.create('backend', 'view_node_response', {
                        'node_details': {'id': node_id, 'title': 'Test Node'}
                    })
            
            elif message.action == 'canvas_dblclick':
                # Find nearest node and convert to edit_node action
                node_id = self.find_nearest_node(message.payload['x'], message.payload['y'])
                if node_id:
                    self.processed_actions.append(('edit', node_id))
                    return Message.create('backend', 'edit_node_response', {
                        'updated_node': {'id': node_id, 'title': 'Updated Node'}
                    })
            
            elif message.action == 'canvas_contextmenu':
                # Find nearest node and convert to delete_node action
                node_id = self.find_nearest_node(message.payload['x'], message.payload['y'])
                if node_id:
                    self.processed_actions.append(('delete', node_id))
                    return Message.create('backend', 'delete_node_response', {})
            
            return Message.create('backend', 'error_response', {
                'error': 'Unknown action'
            })

    def find_nearest_node(self, x, y):
        """Simulate finding the nearest node to given coordinates."""
        # In a real implementation, this would calculate distances to all nodes
        # For testing, we'll return a fixed node ID
        return 'test_node_1'

    def test_canvas_click_conversion(self):
        """Test conversion of canvas click to node view action."""
        # Simulate canvas click
        message = Message.create('canvas', 'canvas_click', {
            'x': 100,
            'y': 100,
            'canvasWidth': 800,
            'canvasHeight': 600
        })
        self.message_queue.enqueue(message)
        time.sleep(0.2)

        with self.lock:
            self.assertEqual(len(self.processed_actions), 1)
            action, node_id = self.processed_actions[0]
            self.assertEqual(action, 'view')
            self.assertEqual(node_id, 'test_node_1')
            
            # Verify response message
            self.assertEqual(len(self.received_messages), 1)
            response = self.received_messages[0]
            self.assertEqual(response.action, 'view_node_response')
            self.assertIn('node_details', response.payload)

    def test_canvas_dblclick_conversion(self):
        """Test conversion of canvas double-click to node edit action."""
        # Simulate canvas double-click
        message = Message.create('canvas', 'canvas_dblclick', {
            'x': 100,
            'y': 100,
            'canvasWidth': 800,
            'canvasHeight': 600
        })
        self.message_queue.enqueue(message)
        time.sleep(0.2)

        with self.lock:
            self.assertEqual(len(self.processed_actions), 1)
            action, node_id = self.processed_actions[0]
            self.assertEqual(action, 'edit')
            self.assertEqual(node_id, 'test_node_1')
            
            # Verify response message
            self.assertEqual(len(self.received_messages), 1)
            response = self.received_messages[0]
            self.assertEqual(response.action, 'edit_node_response')
            self.assertIn('updated_node', response.payload)

    def test_canvas_contextmenu_conversion(self):
        """Test conversion of canvas context menu to node delete action."""
        # Simulate canvas context menu
        message = Message.create('canvas', 'canvas_contextmenu', {
            'x': 100,
            'y': 100,
            'canvasWidth': 800,
            'canvasHeight': 600
        })
        self.message_queue.enqueue(message)
        time.sleep(0.2)

        with self.lock:
            self.assertEqual(len(self.processed_actions), 1)
            action, node_id = self.processed_actions[0]
            self.assertEqual(action, 'delete')
            self.assertEqual(node_id, 'test_node_1')
            
            # Verify response message
            self.assertEqual(len(self.received_messages), 1)
            response = self.received_messages[0]
            self.assertEqual(response.action, 'delete_node_response')

    def test_canvas_event_sequence(self):
        """Test a sequence of canvas events to verify proper conversion."""
        events = [
            ('canvas_click', {'x': 100, 'y': 100}),
            ('canvas_dblclick', {'x': 150, 'y': 150}),
            ('canvas_contextmenu', {'x': 200, 'y': 200})
        ]

        # Execute events in sequence
        for event_type, payload in events:
            message = Message.create('canvas', event_type, {
                **payload,
                'canvasWidth': 800,
                'canvasHeight': 600
            })
            self.message_queue.enqueue(message)
            time.sleep(0.2)

        with self.lock:
            # Verify all events were processed
            self.assertEqual(len(self.processed_actions), len(events))
            
            # Verify action sequence
            expected_actions = ['view', 'edit', 'delete']
            for i, (action, _) in enumerate(self.processed_actions):
                self.assertEqual(action, expected_actions[i])
            
            # Verify all messages were processed successfully
            for response in self.received_messages:
                self.assertIn('_response', response.action)

if __name__ == '__main__':
    unittest.main() 