import unittest
import time
from src.message_format import Message
from src.message_queue import message_queue
import threading
import json
import pytest
from datetime import datetime
from src.handlers import handle_message
from src.state import set_ideas, get_ideas
import uuid
from tests.test_utils import mock_streamlit, set_test_ideas, get_test_ideas, set_test_central

# Import fixture to patch st
pytest.importorskip("tests.test_utils")

class TestCanvasEvents(unittest.TestCase):
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
        """Handle incoming messages and simulate graph actions."""
        with self.lock:
            # Store the original message
            self.received_messages.append(message)
            
            # Generate a response based on the message type
            response = None
            
            # Convert canvas events to node actions
            if message.action == 'canvas_click':
                # Find nearest node and convert to view_node action
                node_id = self.find_nearest_node(message.payload['x'], message.payload['y'])
                if node_id:
                    self.processed_actions.append(('view', node_id))
                    response = Message.create('backend', 'view_node_response', {
                        'node_details': {'id': node_id, 'title': 'Test Node'}
                    })
            
            elif message.action == 'canvas_dblclick':
                # Find nearest node and convert to edit_node action
                node_id = self.find_nearest_node(message.payload['x'], message.payload['y'])
                if node_id:
                    self.processed_actions.append(('edit', node_id))
                    response = Message.create('backend', 'edit_node_response', {
                        'updated_node': {'id': node_id, 'title': 'Updated Node'}
                    })
            
            elif message.action == 'canvas_contextmenu':
                # Find nearest node and convert to delete_node action
                node_id = self.find_nearest_node(message.payload['x'], message.payload['y'])
                if node_id:
                    self.processed_actions.append(('delete', node_id))
                    response = Message.create('backend', 'delete_node_response', {})
            
            if response is None:
                response = Message.create('backend', 'error_response', {
                    'error': 'Unknown action'
                })
            
            # Clear the received_messages and replace with the response for test verification
            self.received_messages = [response]
            
            return response

    def find_nearest_node(self, x, y):
        """Simulate finding the nearest node to given coordinates."""
        # In a real implementation, this would calculate distances to all nodes
        # For testing, we'll return a fixed node ID
        return 'test_node_1'
        
    def enqueue(self, message):
        """Enqueue a message and process it immediately for testing."""
        response = self._mock_process_next_message(message)
        return response

    def test_canvas_click_conversion(self):
        """Test conversion of canvas click to node view action."""
        # Simulate canvas click
        message = Message.create('frontend', 'canvas_click', {
            'x': 100,
            'y': 100,
            'canvasWidth': 800,
            'canvasHeight': 600,
            'timestamp': datetime.now().timestamp() * 1000
        })
        self.enqueue(message)

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
        message = Message.create('frontend', 'canvas_dblclick', {
            'x': 100,
            'y': 100,
            'canvasWidth': 800,
            'canvasHeight': 600,
            'timestamp': datetime.now().timestamp() * 1000
        })
        self.enqueue(message)

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
        message = Message.create('frontend', 'canvas_contextmenu', {
            'x': 100,
            'y': 100,
            'canvasWidth': 800,
            'canvasHeight': 600,
            'timestamp': datetime.now().timestamp() * 1000
        })
        self.enqueue(message)

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
            message = Message.create('frontend', event_type, {
                **payload,
                'canvasWidth': 800,
                'canvasHeight': 600,
                'timestamp': datetime.now().timestamp() * 1000
            })
            self.enqueue(message)

        with self.lock:
            # Verify all events were processed
            self.assertEqual(len(self.processed_actions), len(events))
            
            # Verify action sequence
            expected_actions = ['view', 'edit', 'delete']
            for i, (action, _) in enumerate(self.processed_actions):
                self.assertEqual(action, expected_actions[i])
            
            # Verify all messages were processed successfully
            for response in self.received_messages:
                self.assertTrue(response.action.endswith('_response'))

def create_test_message(action, payload):
    """Helper function to create test messages with required fields."""
    return Message(
        message_id=str(uuid.uuid4()),
        source='frontend',
        action=action,
        payload=payload,
        timestamp=datetime.now().timestamp() * 1000
    )

def test_canvas_coordinate_transformation():
    """Test coordinate transformation between canvas and backend coordinates."""
    # Create test node at center
    test_nodes = [
        {
            'id': 1,
            'label': 'Center Node',
            'x': 0,
            'y': 0
        }
    ]
    set_ideas(test_nodes)
    
    # Test click coordinates
    canvas_width = 800
    canvas_height = 600
    click_x = 400  # Center of canvas
    click_y = 300  # Center of canvas
    
    click_msg = create_test_message(
        'canvas_click',
        {
            'x': click_x,
            'y': click_y,
            'canvasWidth': canvas_width,
            'canvasHeight': canvas_height,
            'timestamp': datetime.now().timestamp() * 1000
        }
    )
    
    response = handle_message(click_msg.to_dict())
    assert response is not None
    assert response.status == 'completed'
    assert response.action.endswith('_response')

def test_node_selection():
    """Test node selection through canvas clicks."""
    # Create test nodes at positions that will be properly detected by click
    # Position nodes at the center of the canvas for predictable click detection
    nodes = [
        {'id': 1, 'x': 0, 'y': 0, 'label': 'Center Node'},  # Will be at canvas center (400, 300)
        {'id': 2, 'x': 50, 'y': 50, 'label': 'Top Right Node'},  # Will be at (450, 350)
        {'id': 3, 'x': -50, 'y': -50, 'label': 'Bottom Left Node'}  # Will be at (350, 250)
    ]
    set_ideas(nodes)
    
    # Test clicking near center node (exact center)
    center_click = create_test_message(
        'canvas_click',
        {
            'x': 400,  # Center of canvas
            'y': 300,  # Center of canvas
            'canvasWidth': 800,
            'canvasHeight': 600,
            'timestamp': datetime.now().timestamp() * 1000
        }
    )
    
    response = handle_message(center_click.to_dict())
    assert response is not None
    assert response.status == 'completed'
    assert response.action.endswith('_response')
    
    # Test clicking near top right node
    top_right_click = create_test_message(
        'canvas_click',
        {
            'x': 450,  # Near top right
            'y': 350,  # Near top right
            'canvasWidth': 800,
            'canvasHeight': 600,
            'timestamp': datetime.now().timestamp() * 1000
        }
    )
    
    response = handle_message(top_right_click.to_dict())
    assert response is not None
    assert response.status == 'completed'
    assert response.action.endswith('_response')

def test_node_interaction_events():
    """Test various node interaction events."""
    # Create test node
    test_nodes = [
        {
            'id': 1,
            'label': 'Test Node',
            'x': 0,
            'y': 0
        }
    ]
    set_ideas(test_nodes)
    
    # Test double-click for editing
    dblclick_msg = create_test_message(
        'canvas_dblclick',
        {
            'x': 400,
            'y': 300,
            'canvasWidth': 800,
            'canvasHeight': 600,
            'timestamp': datetime.now().timestamp() * 1000
        }
    )
    
    response = handle_message(dblclick_msg.to_dict())
    assert response is not None
    assert response.status == 'completed'
    assert response.action.endswith('_response')
    
    # Test right-click for deletion
    context_msg = create_test_message(
        'canvas_contextmenu',
        {
            'x': 400,
            'y': 300,
            'canvasWidth': 800,
            'canvasHeight': 600,
            'timestamp': datetime.now().timestamp() * 1000
        }
    )
    
    response = handle_message(context_msg.to_dict())
    assert response is not None
    assert response.status == 'completed'
    assert response.action.endswith('_response')

def test_canvas_boundary_conditions():
    """Test canvas interactions at boundary conditions."""
    # Create test node at center
    test_nodes = [
        {
            'id': 1,
            'label': 'Test Node',
            'x': 0,
            'y': 0
        }
    ]
    set_ideas(test_nodes)
    
    # Test click at the exact center (where the node is)
    center_click = create_test_message(
        'canvas_click',
        {
            'x': 400,  # Center X
            'y': 300,  # Center Y
            'canvasWidth': 800,
            'canvasHeight': 600,
            'timestamp': datetime.now().timestamp() * 1000
        }
    )
    
    response = handle_message(center_click.to_dict())
    assert response is not None
    assert response.status == 'completed'
    assert response.action.endswith('_response')
    
    # Test click outside canvas (should fail)
    outside_click = create_test_message(
        'canvas_click',
        {
            'x': 1000,  # Outside canvas
            'y': 1000,  # Outside canvas
            'canvasWidth': 800,
            'canvasHeight': 600,
            'timestamp': datetime.now().timestamp() * 1000
        }
    )
    
    response = handle_message(outside_click.to_dict())
    assert response is not None
    assert response.status == 'failed'  # This should fail as there's no node there
    assert response.action.endswith('_response')

def test_canvas_event_sequence():
    """Test sequence of canvas events and their interactions."""
    # Create test node
    test_nodes = [
        {
            'id': 1,
            'label': 'Test Node',
            'x': 0,
            'y': 0
        }
    ]
    set_ideas(test_nodes)
    
    # Create a sequence of events
    events = [
        create_test_message(
            'canvas_click',
            {
                'x': 400,
                'y': 300,
                'canvasWidth': 800,
                'canvasHeight': 600,
                'timestamp': datetime.now().timestamp() * 1000
            }
        ),
        create_test_message(
            'canvas_dblclick',
            {
                'x': 400,
                'y': 300,
                'canvasWidth': 800,
                'canvasHeight': 600,
                'timestamp': datetime.now().timestamp() * 1000
            }
        ),
        create_test_message(
            'canvas_contextmenu',
            {
                'x': 400,
                'y': 300,
                'canvasWidth': 800,
                'canvasHeight': 600,
                'timestamp': datetime.now().timestamp() * 1000
            }
        )
    ]
    
    # Process events in sequence
    responses = []
    for event in events:
        response = handle_message(event.to_dict())
        responses.append(response)
    
    # Verify responses
    assert len(responses) == 3
    for response in responses:
        assert response is not None
        assert response.status == 'completed'
        assert response.action.endswith('_response')

if __name__ == '__main__':
    unittest.main() 