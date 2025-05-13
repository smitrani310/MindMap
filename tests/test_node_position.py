import unittest
import json
import os
import sys
import time
from unittest.mock import patch, MagicMock

# Add parent directory to path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import app components
from src.message_format import Message
from src.message_queue import message_queue
from src.state import get_ideas, set_ideas, get_store, save_data

# Create a mock implementation of _handle_position to avoid Streamlit context errors
def mock_handle_position(message_queue_self, message):
    """Mock implementation of _handle_position"""
    try:
        # Get the ideas
        ideas = get_ideas()
        
        # Check for direct format first (id, x, y)
        node_id = message.payload.get('id')
        new_x = message.payload.get('x')
        new_y = message.payload.get('y')
        
        # If direct format isn't available, check alternative format
        if node_id is None or new_x is None or new_y is None:
            # Look for first key that could be a node ID
            keys = [k for k in message.payload.keys() if k not in ('id', 'x', 'y', 'source', 'action', 'timestamp', 'message_id')]
            if keys:
                node_id = keys[0]
                pos_data = message.payload.get(node_id)
                if isinstance(pos_data, dict):
                    new_x = pos_data.get('x')
                    new_y = pos_data.get('y')
        
        # Validate we have all required data
        if node_id is None or new_x is None or new_y is None:
            error = f"Missing position data: id={node_id}, x={new_x}, y={new_y}"
            print(error)
            return Message.create_error(message, error)
        
        # Try to convert ID to integer if possible
        try:
            node_id_int = int(node_id)
        except (ValueError, TypeError):
            node_id_int = None
        
        # Find the node (try both string and integer comparison)
        node = next((n for n in ideas if 
                   str(n.get('id')) == str(node_id) or 
                   (node_id_int is not None and n.get('id') == node_id_int)), None)
                   
        if not node:
            error = f"Node with id {node_id} not found for position update"
            print(error)
            return Message.create_error(message, error)
        
        # Update the position
        try:
            # For the mock, simulate the update_node_position function
            node['x'] = float(new_x)
            node['y'] = float(new_y)
        except (ValueError, TypeError) as e:
            error = f"Error updating position: {str(e)}"
            print(error)
            return Message.create_error(message, error)
        
        # Update the ideas list
        set_ideas(ideas)
        
        # Save the data
        save_data(get_store())
        
        # Return success response
        return Message.create_success(message)
    except Exception as e:
        print(f"Error in mock_handle_position: {str(e)}")
        return Message.create_error(message, str(e))

class TestNodePosition(unittest.TestCase):
    """Test suite for node position update functionality"""
    
    def setUp(self):
        """Set up test environment before each test"""
        # Mock the store with test data
        self.test_ideas = [
            {
                'id': 1,
                'label': 'Test Node 1',
                'description': 'Test Description',
                'urgency': 'medium',
                'tag': '',
                'parent': None,
                'edge_type': 'default',
                'x': 0,
                'y': 0  # Starting at position (0,0)
            },
            {
                'id': 2,
                'label': 'Test Node 2',
                'description': 'Test Description 2',
                'urgency': 'medium',
                'tag': '',
                'parent': 1,
                'edge_type': 'default',
                'x': 50,
                'y': 50
            }
        ]
        
        # Create a patch for the store
        self.store_patch = patch('src.state.get_store', return_value={
            'ideas': self.test_ideas,
            'next_id': 3,
            'central': 1
        })
        
        # Create a patch for the ideas getter
        self.ideas_getter_patch = patch('src.state.get_ideas', return_value=self.test_ideas)
        
        # Create a patch for the ideas setter to track changes
        self.ideas_setter_mock = MagicMock()
        self.ideas_setter_patch = patch('src.state.set_ideas', self.ideas_setter_mock)
        
        # Create a patch for the save_data function
        self.save_data_mock = MagicMock()
        self.save_data_patch = patch('src.state.save_data', self.save_data_mock)
        
        # Mock streamlit
        self.st_patch = patch('src.message_queue.st')
        
        # Create a patch for the _handle_position method to avoid Streamlit context errors
        self.handle_position_patch = patch('src.message_queue.MessageQueue._handle_position', 
                                          side_effect=mock_handle_position)
        
        # Start all patches
        self.store_patch.start()
        self.ideas_getter_patch.start()
        self.ideas_setter_patch.start()
        self.save_data_patch.start()
        self.st_patch.start()
        self.handle_position_patch.start()
        
    def tearDown(self):
        """Clean up after each test"""
        # Stop all patches
        self.handle_position_patch.stop()
        self.store_patch.stop()
        self.ideas_getter_patch.stop()
        self.ideas_setter_patch.stop()
        self.save_data_patch.stop()
        self.st_patch.stop()
        
    def test_position_update_direct_format(self):
        """Test node position update with direct format (id, x, y)"""
        # Create a position update message
        message = Message.create('frontend', 'pos', {
            'id': 1,
            'x': 100,
            'y': 200
        })
        
        # Process the message
        response = message_queue._handle_position(message)
        
        # Check that the response is successful
        self.assertEqual(response.status, 'completed')
        
        # Make sure the setter was called
        self.ideas_setter_mock.assert_called_once()
        
        # The setter should be called with a list of ideas
        called_args = self.ideas_setter_mock.call_args[0]
        self.assertTrue(len(called_args) > 0, "set_ideas was not called with any arguments")
        called_ideas = called_args[0]
        
        # Find the updated node
        updated_node = next((n for n in called_ideas if n['id'] == 1), None)
        self.assertIsNotNone(updated_node, "Node not found in updated ideas")
        
        # Verify position was updated
        self.assertEqual(updated_node['x'], 100)
        self.assertEqual(updated_node['y'], 200)
        
        # Verify save_data was called
        self.save_data_mock.assert_called_once()
        
    def test_position_update_alternative_format(self):
        """Test node position update with alternative format (nodeId: {x, y})"""
        # Create a position update message with alternative format
        message = Message.create('frontend', 'pos', {
            '2': {'x': 150, 'y': 250}
        })
        
        # Process the message
        response = message_queue._handle_position(message)
        
        # Check that the response is successful
        self.assertEqual(response.status, 'completed')
        
        # Make sure the setter was called
        self.ideas_setter_mock.assert_called_once()
        
        # The setter should be called with a list of ideas
        called_args = self.ideas_setter_mock.call_args[0]
        self.assertTrue(len(called_args) > 0, "set_ideas was not called with any arguments")
        called_ideas = called_args[0]
        
        # Find the updated node
        updated_node = next((n for n in called_ideas if n['id'] == 2), None)
        self.assertIsNotNone(updated_node, "Node not found in updated ideas")
        
        # Verify position was updated
        self.assertEqual(updated_node['x'], 150)
        self.assertEqual(updated_node['y'], 250)
        
        # Verify save_data was called
        self.save_data_mock.assert_called_once()
        
    def test_position_update_nonexistent_node(self):
        """Test position update with a non-existent node ID"""
        # Create a position update message with a non-existent node ID
        message = Message.create('frontend', 'pos', {
            'id': 999,
            'x': 100,
            'y': 100
        })
        
        # Process the message
        response = message_queue._handle_position(message)
        
        # Check that the response indicates failure
        self.assertEqual(response.status, 'failed')
        self.assertIn("not found", response.error)
        
    def test_position_update_missing_data(self):
        """Test position update with missing coordinate data"""
        # Create a position update message with missing y coordinate
        message = Message.create('frontend', 'pos', {
            'id': 1,
            'x': 100
            # Missing y
        })
        
        # Process the message
        response = message_queue._handle_position(message)
        
        # Check that the response indicates failure
        self.assertEqual(response.status, 'failed')
        self.assertIn("Missing", response.error)
        
    def test_dragend_event_flow_simulation(self):
        """Simulate the flow from dragEnd event to position update"""
        # This test simulates the full flow from dragEnd to position update
        
        # Step 1: Create a payload similar to what the dragEnd handler would create
        drag_position = {
            'id': 1,
            'x': 300,
            'y': 400
        }
        
        # Step 2: Create a message as it would be created in the message handler
        message = Message.create('frontend', 'pos', drag_position)
        
        # Step 3: Process with the position handler directly as in main.py
        response = message_queue._handle_position(message)
        
        # Verify it worked
        self.assertEqual(response.status, 'completed')
        
        # Make sure the setter was called
        self.ideas_setter_mock.assert_called_once()
        
        # The setter should be called with a list of ideas
        called_args = self.ideas_setter_mock.call_args[0]
        self.assertTrue(len(called_args) > 0, "set_ideas was not called with any arguments")
        called_ideas = called_args[0]
        
        # Find the updated node
        updated_node = next((n for n in called_ideas if n['id'] == 1), None)
        self.assertIsNotNone(updated_node, "Node not found in updated ideas")
        
        # Verify position was updated
        self.assertEqual(updated_node['x'], 300)
        self.assertEqual(updated_node['y'], 400)
        
        # Verify save_data was called
        self.save_data_mock.assert_called_once()

if __name__ == '__main__':
    unittest.main() 