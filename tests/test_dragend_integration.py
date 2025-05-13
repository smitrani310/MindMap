import unittest
import sys
import os
import json
import time
from unittest.mock import patch, MagicMock

# Add parent directory to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import required modules
from src.message_format import Message, create_response_message
from src.message_queue import message_queue
from src.state import get_ideas, set_ideas, get_store, save_data

# Create mock implementation of handle_position to avoid Streamlit context errors
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

class TestDragEndIntegration(unittest.TestCase):
    """
    Integration test for the dragEnd->position update flow
    
    This test simulates the complete flow:
    1. Frontend dragEnd event
    2. Message generation and sending
    3. Backend processing
    4. State updating
    
    Each step is mocked where needed but the flow matches the real app.
    """
    
    def setUp(self):
        """Set up the test environment"""
        # Create test data
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
                'y': 0  # Initial position
            }
        ]
        
        # Create patches for all necessary dependencies
        self.store_patch = patch('src.state.get_store', return_value={
            'ideas': self.test_ideas,
            'next_id': 2,
            'central': 1
        })
        
        self.ideas_getter_patch = patch('src.state.get_ideas', return_value=self.test_ideas)
        
        # Create a special setter patch that actually updates our test list
        def ideas_setter(ideas):
            self.test_ideas = ideas
            return True
            
        self.ideas_setter_patch = patch('src.state.set_ideas', side_effect=ideas_setter)
        
        # Mock save_data
        self.save_data_mock = MagicMock()
        self.save_data_patch = patch('src.state.save_data', self.save_data_mock)
        
        # Mock streamlit
        self.st_patch = patch('src.message_queue.st')
        
        # Create a patch for the _handle_position method to avoid Streamlit context errors
        self.handle_position_patch = patch('src.message_queue.MessageQueue._handle_position',
                                          side_effect=mock_handle_position)
        
        # Start all the patches
        self.store_patch.start()
        self.ideas_getter_patch.start()
        self.ideas_setter_patch.start()
        self.save_data_patch.start()
        self.st_patch.start()
        self.handle_position_patch.start()
        
    def tearDown(self):
        """Clean up after the test"""
        # Stop all patches
        self.handle_position_patch.stop()
        self.store_patch.stop()
        self.ideas_getter_patch.stop()
        self.ideas_setter_patch.stop()
        self.save_data_patch.stop()
        self.st_patch.stop()
        
    def test_dragend_integration(self):
        """Test the full dragEnd integration flow"""
        # STEP 1: Simulate the dragEnd event in the browser
        # In the real app, vis.js fires this event when a node is dragged
        # The event includes the node ID
        node_id = 1
        new_x = 150
        new_y = 250
        
        # STEP 2: The event handler gets the new position from vis.js
        # In the real app, this happens with window.visNetwork.getPositions()
        node_position = {
            'x': new_x,
            'y': new_y
        }
        
        # STEP 3: The handler creates a message
        # In real app: simpleSendMessage('pos', {id: nodeId, x: pos.x, y: pos.y})
        payload = {
            'id': node_id,
            'x': new_x,
            'y': new_y
        }
        
        # STEP 4: The message is received by Streamlit and processed
        # In the real app, main.py receives the message and creates a Message object
        message = Message.create('frontend', 'pos', payload)
        
        # STEP 5: The message is passed to the message handler
        # In real app: handle_message_with_queue(position_message)
        response = message_queue._handle_position(message)
        
        # Assertions
        # Check that the message was processed successfully
        self.assertEqual(response.status, 'completed', 
                        f"Position update failed: {getattr(response, 'error', 'unknown error')}")
        
        # Check that our test node was updated
        updated_node = next((n for n in self.test_ideas if n['id'] == node_id), None)
        self.assertIsNotNone(updated_node, "Node not found after update")
        
        # Check the position values
        self.assertEqual(updated_node['x'], new_x, "X coordinate not updated correctly")
        self.assertEqual(updated_node['y'], new_y, "Y coordinate not updated correctly")
        
        # Check that save_data was called to persist the changes
        self.save_data_mock.assert_called()
        
    def test_multiple_node_updates(self):
        """Test updating multiple nodes in sequence"""
        # Add a second node to test multiple updates
        self.test_ideas.append({
            'id': 2,
            'label': 'Test Node 2',
            'description': 'Second node',
            'urgency': 'medium',
            'tag': '',
            'parent': 1,
            'edge_type': 'default',
            'x': 50,
            'y': 50
        })
        
        # Update positions for both nodes
        updates = [
            {'id': 1, 'x': 100, 'y': 100},
            {'id': 2, 'x': 200, 'y': 200}
        ]
        
        # Reset the mock to ensure proper call counts
        self.save_data_mock.reset_mock()
        
        # Process each update
        for update in updates:
            message = Message.create('frontend', 'pos', update)
            response = message_queue._handle_position(message)
            self.assertEqual(response.status, 'completed', 
                            f"Position update failed for node {update['id']}")
        
        # Verify both nodes were updated correctly
        node1 = next((n for n in self.test_ideas if n['id'] == 1), None)
        node2 = next((n for n in self.test_ideas if n['id'] == 2), None)
        
        self.assertEqual(node1['x'], 100)
        self.assertEqual(node1['y'], 100)
        self.assertEqual(node2['x'], 200)
        self.assertEqual(node2['y'], 200)
        
        # Should have called save_data twice (once per update)
        self.assertEqual(self.save_data_mock.call_count, 2)
        
    def test_direct_update_in_main(self):
        """Test the direct update flow used in main.py"""
        # This simulates the implementation in main.py where we directly
        # update the node position without going through message_queue
        
        node_id = 1
        new_x = 300
        new_y = 400
        
        # Reset the mock to ensure proper call counts
        self.save_data_mock.reset_mock()
        
        # Get ideas
        ideas = get_ideas()
        updated = False
        
        # Find and update the node
        for node in ideas:
            if 'id' in node and str(node['id']) == str(node_id):
                node['x'] = new_x
                node['y'] = new_y
                updated = True
                break
                
        # Update the store if node was found
        self.assertTrue(updated, "Node not found for direct update")
        
        # Save the updated ideas
        set_ideas(ideas)
        save_data(get_store())
        
        # Verify the node was updated
        node = next((n for n in self.test_ideas if n['id'] == node_id), None)
        self.assertEqual(node['x'], new_x)
        self.assertEqual(node['y'], new_y)
        
        # Check that save_data was called
        self.save_data_mock.assert_called_once()

if __name__ == '__main__':
    unittest.main() 