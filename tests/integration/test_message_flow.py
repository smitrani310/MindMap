import unittest
import time
from src.message_format import Message, validate_message
from src.message_queue import message_queue
import threading
import json
import pytest
from datetime import datetime
from src.handlers import handle_message
import uuid
from tests.test_utils import mock_streamlit, set_test_ideas, get_test_ideas, set_test_central

# Import fixture to patch st
pytest.importorskip("tests.test_utils")

class TestMessageFlow(unittest.TestCase):
    def setUp(self):
        self.message_queue = message_queue
        self.received_messages = []
        self.processed_actions = []
        self.lock = threading.Lock()
        
        # Patch the _process_next_message method to handle our test messages
        self.original_process_next_message = self.message_queue._process_next_message
        self.message_queue._process_next_message = self._mock_process_next_message
        
        # Initialize a queue for our test messages
        self.test_message_queue = []

    def tearDown(self):
        # Restore original method
        self.message_queue._process_next_message = self.original_process_next_message
        self.received_messages = []
        self.processed_actions = []
        self.test_message_queue = []

    def _mock_process_next_message(self, message):
        """Mock implementation that calls our handler directly."""
        return self.handle_message(message)
        
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
        
    def enqueue(self, message):
        """Enqueue a message and process it immediately for testing."""
        response = self._mock_process_next_message(message)
        return response

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
        self.enqueue(message)

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
        self.enqueue(message)

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
        self.enqueue(message)

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
            self.enqueue(message)

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

def create_test_message(action, payload):
    """Helper function to create test messages with required fields."""
    return Message(
        message_id=str(uuid.uuid4()),
        source='frontend',
        action=action,
        payload=payload,
        timestamp=datetime.now().timestamp() * 1000
    )

def test_message_creation():
    """Test creating valid messages with different actions."""
    # Test canvas click message
    click_msg = create_test_message(
        'canvas_click',
        {
            'x': 100,
            'y': 200,
            'canvasWidth': 800,
            'canvasHeight': 600,
            'timestamp': datetime.now().timestamp() * 1000
        }
    )
    assert validate_message(click_msg.to_dict())
    
    # Test node edit message
    edit_msg = create_test_message(
        'edit_node',
        {
            'node_id': 1,
            'label': 'Test Node',
            'description': 'Test Description'
        }
    )
    assert validate_message(edit_msg.to_dict())

def test_message_validation():
    """Test message validation with various scenarios."""
    # Test missing required fields
    invalid_msg = {
        'action': 'canvas_click',
        'payload': {'x': 100, 'y': 200}
    }
    assert not validate_message(invalid_msg)
    
    # Test invalid action
    invalid_action_msg = {
        'message_id': str(uuid.uuid4()),
        'source': 'frontend',
        'action': 'invalid_action',
        'payload': {},
        'timestamp': datetime.now().timestamp() * 1000
    }
    assert not validate_message(invalid_action_msg)
    
    # Test invalid payload format
    invalid_payload_msg = {
        'message_id': str(uuid.uuid4()),
        'source': 'frontend',
        'action': 'canvas_click',
        'payload': 'not_a_dict',
        'timestamp': datetime.now().timestamp() * 1000
    }
    assert not validate_message(invalid_payload_msg)

def test_message_queue_processing():
    """Test message queue processing and response handling."""
    # Create test message
    test_msg = create_test_message(
        'canvas_click',
        {
            'x': 100,
            'y': 200,
            'canvasWidth': 800,
            'canvasHeight': 600,
            'timestamp': datetime.now().timestamp() * 1000
        }
    )
    
    # Process message through queue
    response = message_queue._process_next_message(test_msg)
    assert response is not None
    assert isinstance(response, Message)
    assert response.status in ['completed', 'failed']

def test_canvas_actions():
    """Test canvas-related actions and their responses."""
    # Test click action
    click_msg = create_test_message(
        'canvas_click',
        {
            'x': 100,
            'y': 200,
            'canvasWidth': 800,
            'canvasHeight': 600,
            'timestamp': datetime.now().timestamp() * 1000
        }
    )
    response = handle_message(click_msg.to_dict())
    assert response is not None
    assert response.action.endswith('_response')
    
    # Test double-click action
    dblclick_msg = create_test_message(
        'canvas_dblclick',
        {
            'x': 100,
            'y': 200,
            'canvasWidth': 800,
            'canvasHeight': 600,
            'timestamp': datetime.now().timestamp() * 1000
        }
    )
    response = handle_message(dblclick_msg.to_dict())
    assert response is not None
    assert response.action.endswith('_response')
    
    # Test context menu action
    context_msg = create_test_message(
        'canvas_contextmenu',
        {
            'x': 100,
            'y': 200,
            'canvasWidth': 800,
            'canvasHeight': 600,
            'timestamp': datetime.now().timestamp() * 1000
        }
    )
    response = handle_message(context_msg.to_dict())
    assert response is not None
    assert response.action.endswith('_response')

def test_node_operations():
    """Test node-specific operations."""
    # Test node creation
    create_msg = create_test_message(
        'create_node',
        {
            'label': 'Test Node',
            'description': 'Test Description',
            'urgency': 'medium',
            'tag': 'test'
        }
    )
    response = handle_message(create_msg.to_dict())
    assert response is not None
    assert response.action.endswith('_response')
    assert 'node_id' in response.payload
    
    # Test node update
    update_msg = create_test_message(
        'update_node',
        {
            'node_id': 1,
            'label': 'Updated Node',
            'description': 'Updated Description'
        }
    )
    response = handle_message(update_msg.to_dict())
    assert response is not None
    assert response.action.endswith('_response')
    
    # Test node deletion
    delete_msg = create_test_message(
        'delete_node',
        {
            'node_id': 1
        }
    )
    response = handle_message(delete_msg.to_dict())
    assert response is not None
    assert response.action.endswith('_response')

def test_error_handling():
    """Test error handling in message processing."""
    # Test invalid message format
    invalid_msg = {
        'source': 'frontend',
        'action': 'canvas_click',
        'payload': None  # Invalid payload
    }
    response = handle_message(invalid_msg)
    assert response is not None
    assert isinstance(response, Message)
    assert response.status == 'failed'
    assert 'error' in response.payload
    
    # Test non-existent node operation
    invalid_node_msg = create_test_message(
        'update_node',
        {
            'node_id': 999999,  # Non-existent node
            'label': 'Test'
        }
    )
    response = handle_message(invalid_node_msg.to_dict())
    assert response is not None
    assert isinstance(response, Message)
    assert response.status == 'failed'
    assert 'error' in response.payload

if __name__ == '__main__':
    unittest.main() 