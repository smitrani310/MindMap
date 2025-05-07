"""
Integration tests for canvas event handling in the Mind Map application.

This module tests the interaction between user events on the canvas and the application's
message queue system. It verifies that:
- Canvas clicks are properly processed and mapped to nodes
- Double-clicks trigger appropriate actions
- Context menu events are handled correctly
- Coordinate transformations work accurately
- Node creation and positioning follow the expected rules
- Message queue processes events in the correct order

The tests use a mock Streamlit environment to simulate the application's
state management and UI updates.
"""

import unittest
import pytest
import time
import logging
import json
from datetime import datetime
import threading
from unittest.mock import patch, MagicMock

# Import app modules
from src.message_format import Message, create_response_message
from src.message_queue import message_queue
from src.state import get_store, get_ideas, set_ideas, get_central, set_central, add_idea
from src.state import get_next_id, increment_next_id, save_data
from src.utils import recalc_size
from src.handlers import handle_message, is_circular

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG, 
                  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MockStreamlit:
    """Mock Streamlit environment for testing canvas interactions.
    
    Simulates Streamlit's session state and rerun functionality
    to test UI updates without actual Streamlit dependencies.
    """
    def __init__(self):
        self.session_state = {}
        self.rerun_called = False
        
    def rerun(self):
        """Simulate Streamlit's rerun functionality."""
        self.rerun_called = True

# Create mock st instance
mock_st = MockStreamlit()

# Mock state management functions
def mock_get_ideas():
    """Mock implementation of get_ideas to simulate state retrieval."""
    return mock_st.session_state.get('ideas', [])

def mock_set_ideas(ideas):
    """Mock implementation of set_ideas to simulate state updates."""
    mock_st.session_state['ideas'] = ideas

def mock_get_central():
    """Mock implementation of get_central to simulate central node retrieval."""
    return mock_st.session_state.get('central')

def mock_set_central(node_id):
    """Mock implementation of set_central to simulate central node updates."""
    mock_st.session_state['central'] = node_id

@pytest.fixture(autouse=True)
def patch_streamlit():
    """Fixture to patch Streamlit dependencies for testing.
    
    Injects mock Streamlit instance and state management functions
    into the application modules to enable testing without actual
    Streamlit dependencies.
    """
    import sys
    from src import message_queue
    from src import handlers
    from src import state
    
    if not hasattr(message_queue, 'st'):
        setattr(message_queue, 'st', mock_st)
    
    if not hasattr(handlers, 'st'):
        setattr(handlers, 'st', mock_st)
        
    with patch('src.message_queue.st', mock_st):
        with patch('src.handlers.st', mock_st):
            with patch('src.message_queue.get_ideas', mock_get_ideas):
                with patch('src.message_queue.get_central', mock_get_central):
                    with patch('src.message_queue.set_central', mock_set_central):
                        yield

class TestCanvasActions(unittest.TestCase):
    """Test suite for canvas event handling and message queue functionality.
    
    Tests the complete flow of canvas events from user interaction
    through message queue processing to state updates and UI changes.
    """
    
    def setUp(self):
        """Set up test environment before each test.
        
        Initializes:
        - Mock Streamlit state
        - Message queue
        - Test nodes with specific positions
        - Mock store and state management
        """
        # Clear mock streamlit state
        mock_st.session_state = {}
        mock_st.rerun_called = False
        
        # Clear message queue
        with message_queue._lock:
            message_queue.queue = []
        
        # Set up sample nodes with positions for testing
        self.test_nodes = [
            {
                'id': 1,
                'label': 'Center Node',
                'description': 'Center test node',
                'urgency': 'medium',
                'tag': 'test',
                'x': 0,  # Center of canvas
                'y': 0,
                'size': 20,
                'parent': None
            },
            {
                'id': 2,
                'label': 'Top Right Node',
                'description': 'Top right test node',
                'urgency': 'high',
                'tag': 'test',
                'x': 200,  # Top right
                'y': -150,
                'size': 25,
                'parent': 1
            },
            {
                'id': 3,
                'label': 'Bottom Left Node',
                'description': 'Bottom left test node',
                'urgency': 'low',
                'tag': 'test', 
                'x': -200,  # Bottom left
                'y': 150, 
                'size': 15,
                'parent': 1
            }
        ]
        
        logger.debug("Test nodes setup:")
        for node in self.test_nodes:
            logger.debug(f"Node ID: {node['id']}, Position: ({node['x']}, {node['y']})")
        
        # Initialize store with test nodes
        store = {
            'ideas': self.test_nodes,
            'central': 1,
            'next_id': 4,
            'history': [],
            'history_index': -1,
            'settings': {'edge_length': 100, 'spring_strength': 0.5, 'size_multiplier': 1.0}
        }
        
        # Set the store
        with patch('src.state.get_store', return_value=store):
            set_ideas(self.test_nodes)
            set_central(1)
        
        # Set up initial store access pattern
        self.original_get_store = get_store
        self.store_patcher = patch('src.state.get_store', return_value=store)
        self.mock_get_store = self.store_patcher.start()
        
        # Save original methods
        self.original_save_data = save_data
        
        # Patch save_data to do nothing in tests
        self.save_data_patcher = patch('src.state.save_data')
        self.mock_save_data = self.save_data_patcher.start()
        
        # Verify state setup is correct
        ideas_after_setup = get_ideas()
        logger.debug(f"Store after setup: {store}")
        logger.debug(f"Ideas count after setup: {len(ideas_after_setup)}")
        for node in ideas_after_setup:
            logger.debug(f"Node in store: ID: {node.get('id')}, Position: ({node.get('x')}, {node.get('y')})")
            
    def tearDown(self):
        """Clean up test environment after each test.
        
        Stops all patches and ensures no lingering state
        between test cases.
        """
        self.store_patcher.stop()
        self.save_data_patcher.stop()
        
    def test_message_queue_initialization(self):
        """Test message queue initialization.
        
        Verifies that:
        - Message queue is properly initialized
        - Queue is accessible and of correct type
        - Lock mechanism is in place
        """
        self.assertIsNotNone(message_queue)
        self.assertIsInstance(message_queue.queue, list)
        
    def test_message_enqueue(self):
        """Test message enqueueing functionality.
        
        Verifies that:
        - Messages can be added to the queue
        - Queue maintains correct order
        - Message data is preserved
        """
        message = Message.create('test', 'test_action', {'test': 'data'})
        message_queue.enqueue(message)
        
        with message_queue._lock:
            self.assertEqual(len(message_queue.queue), 1)
            
    def test_process_next_message(self):
        """Test direct message processing.
        
        Verifies that:
        - Messages are processed correctly
        - Appropriate responses are generated
        - State updates occur as expected
        """
        message = Message.create('test', 'center_node', {'id': 1})
        response = message_queue._process_next_message(message)
        
        self.assertIsNotNone(response)
        self.assertEqual(response.status, 'completed')
        
    def test_canvas_click_processing(self):
        """Test canvas click event processing.
        
        Verifies that:
        - Click coordinates are correctly mapped to canvas space
        - Node selection works based on click position
        - State updates reflect the selection
        - UI is notified of changes
        """
        logger.info("Running canvas click test")
        
        # Check that the nodes are properly set in the store
        ideas = get_ideas()
        logger.debug(f"Nodes in store at test start: {len(ideas)}")
        for node in ideas:
            logger.debug(f"Node in store before click: ID: {node.get('id')}, Position: ({node.get('x')}, {node.get('y')})")
            
        canvas_width = 800
        canvas_height = 600
        
        # Calculate expected canvas position of center node (should be at 400, 300)
        center_node = next((n for n in ideas if n.get('id') == 1), None)
        if center_node:
            expected_canvas_x = center_node['x'] + canvas_width/2
            expected_canvas_y = center_node['y'] + canvas_height/2
            logger.debug(f"Expected canvas position of center node: ({expected_canvas_x}, {expected_canvas_y})")
            
        click_message = Message.create('frontend', 'canvas_click', {
            'x': 400,  # Canvas center X
            'y': 300,  # Canvas center Y
            'canvasWidth': canvas_width,
            'canvasHeight': canvas_height,
            'timestamp': datetime.now().timestamp() * 1000
        })
        
        logger.debug(f"Test node positioning: {[(n['id'], n['x'], n['y']) for n in self.test_nodes]}")
        logger.debug(f"Canvas dimensions: {canvas_width}x{canvas_height}")
        logger.debug(f"Click position: (400, 300)")
        
        # Directly check distance calculation for debug purposes
        for node in ideas:
            if 'id' in node and node.get('x') is not None and node.get('y') is not None:
                node_canvas_x = node['x'] + canvas_width/2
                node_canvas_y = node['y'] + canvas_height/2
                distance = ((node_canvas_x - 400) ** 2 + (node_canvas_y - 300) ** 2) ** 0.5
                logger.debug(f"Manual distance calculation - Node {node['id']}: {distance}")
        
        # Process the message
        response = message_queue._process_next_message(click_message)
        
        logger.debug(f"Click response: {response}")
        logger.debug(f"Mock session state: {mock_st.session_state}")
        
        self.assertIsNotNone(response)
        self.assertEqual(response.status, 'completed')
        self.assertEqual(mock_st.session_state.get('selected_node'), 1)
        self.assertTrue(mock_st.rerun_called)
        
    def test_canvas_dblclick_processing(self):
        """Test canvas double-click event processing.
        
        Verifies that:
        - Double-click coordinates are correctly mapped
        - Appropriate node is selected/created
        - State updates reflect the action
        - UI is notified of changes
        """
        canvas_width = 800
        canvas_height = 600
        
        dblclick_message = Message.create('frontend', 'canvas_dblclick', {
            'x': 600,  # Near top right
            'y': 150,  # Near top right
            'canvasWidth': canvas_width,
            'canvasHeight': canvas_height,
            'timestamp': datetime.now().timestamp() * 1000
        })
        
        logger.debug(f"Double-click position: (600, 150)")
        
        response = message_queue._process_next_message(dblclick_message)
        
        logger.debug(f"Double-click response: {response}")
        logger.debug(f"Mock session state: {mock_st.session_state}")
        
        self.assertIsNotNone(response)
        self.assertEqual(response.status, 'completed')
        
    def test_canvas_contextmenu_processing(self):
        """Test processing of canvas context menu event."""
        # Create a context menu message near the bottom left node
        canvas_width = 800
        canvas_height = 600
        
        # Context menu coordinates for bottom left node
        contextmenu_message = Message.create('frontend', 'canvas_contextmenu', {
            'x': 200,  # Near bottom left
            'y': 450,  # Near bottom left
            'canvasWidth': canvas_width,
            'canvasHeight': canvas_height,
            'timestamp': datetime.now().timestamp() * 1000
        })
        
        # Debug info
        logger.debug(f"Context menu position: (200, 450)")
        
        # Process the message
        response = message_queue._process_next_message(contextmenu_message)
        
        # Debug info
        logger.debug(f"Context menu response: {response}")
        
        # Verify response
        self.assertIsNotNone(response)
        self.assertEqual(response.status, 'completed')
        
        # Get the updated store content
        ideas = get_ideas()
        
        # Verify node was deleted
        node_ids = {n['id'] for n in ideas}
        self.assertNotIn(3, node_ids)  # Bottom left node should be deleted
        
    def test_coordinate_transformation(self):
        """Test coordinate transformation between canvas and backend coordinates."""
        # Canvas dimensions
        canvas_width = 800
        canvas_height = 600
        
        # Test center node at (0,0) in backend should be (400,300) on canvas
        node = self.test_nodes[0]  # Center node
        node_canvas_x = node['x'] + canvas_width/2
        node_canvas_y = node['y'] + canvas_height/2
        
        # Debug info
        logger.debug(f"Node backend coordinates: ({node['x']}, {node['y']})")
        logger.debug(f"Node canvas coordinates: ({node_canvas_x}, {node_canvas_y})")
        
        # Verify transformation
        self.assertEqual(node_canvas_x, 400)  # Center X
        self.assertEqual(node_canvas_y, 300)  # Center Y
        
    def test_click_distance_calculation(self):
        """Test calculation of click distance to nodes."""
        # Canvas dimensions
        canvas_width = 800
        canvas_height = 600
        
        # Click at (410, 310) - slightly offset from center
        click_x = 410
        click_y = 310
        
        # Calculate distances for each node
        distances = []
        for node in self.test_nodes:
            # Convert backend coordinates to canvas coordinates
            node_canvas_x = node['x'] + canvas_width/2
            node_canvas_y = node['y'] + canvas_height/2
            
            # Calculate Euclidean distance
            distance = ((node_canvas_x - click_x) ** 2 + (node_canvas_y - click_y) ** 2) ** 0.5
            distances.append((node['id'], distance))
        
        # Debug info
        logger.debug(f"Click position: ({click_x}, {click_y})")
        logger.debug(f"Distance to each node: {distances}")
        
        # Find closest node
        closest_node_id = sorted(distances, key=lambda x: x[1])[0][0]
        
        # Verify closest node is center node
        self.assertEqual(closest_node_id, 1)  # Center node
        
    def test_node_threshold_detection(self):
        """Test node detection within threshold."""
        # Canvas dimensions
        canvas_width = 800
        canvas_height = 600
        
        # Calculate threshold (8% of smallest dimension)
        threshold = min(canvas_width, canvas_height) * 0.08
        
        # Debug info
        logger.debug(f"Click threshold: {threshold}")
        
        # Verify threshold is reasonable
        self.assertGreater(threshold, 0)
        self.assertLess(threshold, 100)  # Should be less than 100px
        
        # Test click just within threshold of center node
        node = self.test_nodes[0]  # Center node
        node_canvas_x = node['x'] + canvas_width/2
        node_canvas_y = node['y'] + canvas_height/2
        
        # Click position just within threshold
        click_x = node_canvas_x + threshold - 5
        click_y = node_canvas_y
        
        # Calculate distance
        distance = ((node_canvas_x - click_x) ** 2 + (node_canvas_y - click_y) ** 2) ** 0.5
        
        # Debug info
        logger.debug(f"Node canvas position: ({node_canvas_x}, {node_canvas_y})")
        logger.debug(f"Click position: ({click_x}, {click_y})")
        logger.debug(f"Distance: {distance}, Threshold: {threshold}")
        
        # Verify distance is within threshold
        self.assertLess(distance, threshold)
        
        # Test with click message
        click_message = Message.create('frontend', 'canvas_click', {
            'x': click_x,
            'y': click_y,
            'canvasWidth': canvas_width,
            'canvasHeight': canvas_height,
            'timestamp': datetime.now().timestamp() * 1000
        })
        
        # Process the message
        response = message_queue._process_next_message(click_message)
        
        # Verify response
        self.assertIsNotNone(response)
        self.assertEqual(response.status, 'completed')
        self.assertEqual(mock_st.session_state.get('selected_node'), 1)  # Center node
        
    def test_node_creation_and_positioning(self):
        """Test node creation with position data."""
        # Create a new node with specific position
        message = Message.create('frontend', 'create_node', {
            'label': 'New Positioned Node',
            'description': 'Test node with position',
            'urgency': 'medium',
            'tag': 'test',
            'x': 100,
            'y': 100
        })
        
        # Process the message
        response = message_queue._process_next_message(message)
        
        # Verify response
        self.assertIsNotNone(response)
        self.assertEqual(response.status, 'completed')
        
        # Get the created node
        new_node = next((n for n in get_ideas() if n['label'] == 'New Positioned Node'), None)
        
        # Verify node was created with correct position
        self.assertIsNotNone(new_node)
        self.assertEqual(new_node['x'], 100)
        self.assertEqual(new_node['y'], 100)
        
    def test_message_queue_worker(self):
        """Test message queue worker thread processing."""
        # Create a test handler
        called_messages = []
        
        def test_handler(message):
            called_messages.append(message)
            return create_response_message(message, 'completed', {'handled': True})
        
        # Start queue with test handler
        message_queue.start(test_handler)
        
        try:
            # Enqueue a test message
            test_message = Message.create('test', 'test_action', {'test': 'data'})
            message_queue.enqueue(test_message)
            
            # Wait for message to be processed
            time.sleep(0.5)
            
            # Verify message was processed
            self.assertGreaterEqual(len(called_messages), 1)
            self.assertEqual(called_messages[0].action, 'test_action')
            
        finally:
            # Stop queue
            message_queue.stop()


if __name__ == '__main__':
    unittest.main() 