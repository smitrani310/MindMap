import unittest
import time
from src.message_format import Message
from src.message_queue import message_queue
import threading
import json

class TestMessageFlow(unittest.TestCase):
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
        """Handle incoming messages and track actions."""
        with self.lock:
            self.received_messages.append(message)
            
            # Map canvas events to node actions
            if message.action == 'canvas_click':
                # Simulate finding nearest node
                node_id = self.find_nearest_node(message.payload['x'], message.payload['y'])
                if node_id:
                    self.processed_actions.append(('view_node', node_id))
                    return Message.create('backend', 'view_node_response', {
                        'node_id': node_id
                    })
                    
            elif message.action == 'canvas_dblclick':
                node_id = self.find_nearest_node(message.payload['x'], message.payload['y'])
                if node_id:
                    self.processed_actions.append(('edit_node', node_id))
                    return Message.create('backend', 'edit_node_response', {
                        'node_id': node_id
                    })
                    
            elif message.action == 'canvas_contextmenu':
                node_id = self.find_nearest_node(message.payload['x'], message.payload['y'])
                if node_id:
                    self.processed_actions.append(('delete_node', node_id))
                    return Message.create('backend', 'delete_node_response', {
                        'node_id': node_id
                    })
            
            return Message.create('backend', 'error_response', {
                'error': 'Unknown action'
            })

    def find_nearest_node(self, x, y):
        """Simulate finding the nearest node to given coordinates."""
        # For testing, return a fixed node ID
        return "node_1"

    def test_canvas_click_flow(self):
        """Test the flow from canvas click to node view action."""
        # Simulate canvas click
        message = Message.create('frontend', 'canvas_click', {
            'x': 100,
            'y': 100,
            'canvasWidth': 800,
            'canvasHeight': 600,
            'timestamp': int(time.time() * 1000)
        })
        self.message_queue.enqueue(message)
        time.sleep(0.2)

        with self.lock:
            # Verify message was received
            self.assertEqual(len(self.received_messages), 1)
            self.assertEqual(self.received_messages[0].action, 'canvas_click')
            
            # Verify action was processed
            self.assertEqual(len(self.processed_actions), 1)
            self.assertEqual(self.processed_actions[0], ('view_node', 'node_1'))

    def test_canvas_dblclick_flow(self):
        """Test the flow from canvas double-click to node edit action."""
        # Simulate canvas double-click
        message = Message.create('frontend', 'canvas_dblclick', {
            'x': 100,
            'y': 100,
            'canvasWidth': 800,
            'canvasHeight': 600,
            'timestamp': int(time.time() * 1000)
        })
        self.message_queue.enqueue(message)
        time.sleep(0.2)

        with self.lock:
            # Verify message was received
            self.assertEqual(len(self.received_messages), 1)
            self.assertEqual(self.received_messages[0].action, 'canvas_dblclick')
            
            # Verify action was processed
            self.assertEqual(len(self.processed_actions), 1)
            self.assertEqual(self.processed_actions[0], ('edit_node', 'node_1'))

    def test_canvas_contextmenu_flow(self):
        """Test the flow from canvas context menu to node delete action."""
        # Simulate canvas context menu
        message = Message.create('frontend', 'canvas_contextmenu', {
            'x': 100,
            'y': 100,
            'canvasWidth': 800,
            'canvasHeight': 600,
            'timestamp': int(time.time() * 1000)
        })
        self.message_queue.enqueue(message)
        time.sleep(0.2)

        with self.lock:
            # Verify message was received
            self.assertEqual(len(self.received_messages), 1)
            self.assertEqual(self.received_messages[0].action, 'canvas_contextmenu')
            
            # Verify action was processed
            self.assertEqual(len(self.processed_actions), 1)
            self.assertEqual(self.processed_actions[0], ('delete_node', 'node_1'))

    def test_message_flow_sequence(self):
        """Test a sequence of canvas events and their corresponding actions."""
        # Simulate a sequence of events
        events = [
            ('canvas_click', {'x': 100, 'y': 100}),
            ('canvas_dblclick', {'x': 150, 'y': 150}),
            ('canvas_contextmenu', {'x': 200, 'y': 200})
        ]

        for action, payload in events:
            payload.update({
                'canvasWidth': 800,
                'canvasHeight': 600,
                'timestamp': int(time.time() * 1000)
            })
            message = Message.create('frontend', action, payload)
            self.message_queue.enqueue(message)
            time.sleep(0.2)

        with self.lock:
            # Verify all messages were received
            self.assertEqual(len(self.received_messages), 3)
            
            # Verify all actions were processed in order
            expected_actions = [
                ('view_node', 'node_1'),
                ('edit_node', 'node_1'),
                ('delete_node', 'node_1')
            ]
            self.assertEqual(self.processed_actions, expected_actions)

if __name__ == '__main__':
    unittest.main() 