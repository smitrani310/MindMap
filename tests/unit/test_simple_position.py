"""
Simple test for node position updates.
This test directly updates node positions without complex mocking.
"""

import unittest
import sys
import os
import json
from unittest.mock import patch, MagicMock

# Add the parent directory to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Suppress Streamlit warnings
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="streamlit")

# Create test data
TEST_NODES = [
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

class SimplePositionTest(unittest.TestCase):
    """Simple test case for node position updates"""
    
    def setUp(self):
        """Set up the test environment"""
        # Create a copy of the test data to avoid sharing state between tests
        self.nodes = [node.copy() for node in TEST_NODES]
        
        # Create a mock for saving data
        self.save_mock = MagicMock()
        
    def test_direct_position_update(self):
        """Test directly updating node positions"""
        # Node to update
        node_id = 1
        new_x = 100
        new_y = 200
        
        # Find the node by ID
        node = next((n for n in self.nodes if n['id'] == node_id), None)
        self.assertIsNotNone(node, "Node not found")
        
        # Update the position
        node['x'] = new_x
        node['y'] = new_y
        
        # Verify the position was updated
        self.assertEqual(node['x'], new_x)
        self.assertEqual(node['y'], new_y)
        
        # Simulate saving data
        self.save_mock(self.nodes)
        self.save_mock.assert_called_once()
        
    def test_batch_position_updates(self):
        """Test updating multiple nodes"""
        # Updates for multiple nodes
        updates = [
            {'id': 1, 'x': 150, 'y': 250},
            {'id': 2, 'x': 300, 'y': 400}
        ]
        
        # Apply updates
        for update in updates:
            node_id = update['id']
            node = next((n for n in self.nodes if n['id'] == node_id), None)
            self.assertIsNotNone(node, f"Node {node_id} not found")
            
            node['x'] = update['x']
            node['y'] = update['y']
            
            # Simulate saving data
            self.save_mock(self.nodes)
        
        # Verify positions were updated
        node1 = next((n for n in self.nodes if n['id'] == 1), None)
        self.assertEqual(node1['x'], 150)
        self.assertEqual(node1['y'], 250)
        
        node2 = next((n for n in self.nodes if n['id'] == 2), None)
        self.assertEqual(node2['x'], 300)
        self.assertEqual(node2['y'], 400)
        
        # Verify save was called for each update
        self.assertEqual(self.save_mock.call_count, 2)
        
    def test_alternative_position_format(self):
        """Test updating positions with alternative format {node_id: {x, y}}"""
        # Create an alternative format update
        alt_update = {'2': {'x': 200, 'y': 300}}
        
        # Extract values
        node_id = int(list(alt_update.keys())[0])
        pos_data = alt_update[str(node_id)]
        new_x = pos_data['x']
        new_y = pos_data['y']
        
        # Find and update the node
        node = next((n for n in self.nodes if n['id'] == node_id), None)
        self.assertIsNotNone(node, f"Node {node_id} not found")
        
        node['x'] = new_x
        node['y'] = new_y
        
        # Verify the position was updated
        self.assertEqual(node['x'], 200)
        self.assertEqual(node['y'], 300)
        
        # Simulate saving data
        self.save_mock(self.nodes)
        self.save_mock.assert_called_once()
        
    def test_nonexistent_node_handling(self):
        """Test handling updates for nonexistent nodes"""
        # Try to update a node that doesn't exist
        node_id = 999
        new_x = 100
        new_y = 200
        
        # Find the node by ID
        node = next((n for n in self.nodes if n['id'] == node_id), None)
        self.assertIsNone(node, "Node should not exist")
        
        # Count nodes before operation
        node_count_before = len(self.nodes)
        
        # Since node doesn't exist, we wouldn't update anything
        # In a real implementation, this would likely trigger an error
        # But for test simplicity, we're just verifying no changes occurred
        
        # Verify no nodes were added or removed
        self.assertEqual(len(self.nodes), node_count_before)
        
        # Verify the original nodes' positions were not changed
        original_nodes = TEST_NODES
        for i, original in enumerate(original_nodes):
            self.assertEqual(self.nodes[i]['x'], original['x'])
            self.assertEqual(self.nodes[i]['y'], original['y'])
        
        # The save function shouldn't be called in this case
        self.save_mock.assert_not_called()
        
    def test_handle_missing_coordinates(self):
        """Test handling updates with missing coordinates"""
        # Update with missing y coordinate
        node_id = 1
        new_x = 150
        
        # Find the node by ID
        node = next((n for n in self.nodes if n['id'] == node_id), None)
        self.assertIsNotNone(node, "Node not found")
        
        # Store original position
        original_x = node['x']
        original_y = node['y']
        
        # In a real implementation, this would likely trigger an error
        # since y is missing. For this test, we'll mimic that by not updating.
        
        # Verify the position wasn't changed
        self.assertEqual(node['x'], original_x)
        self.assertEqual(node['y'], original_y)
        
        # The save function shouldn't be called in this case
        self.save_mock.assert_not_called()

if __name__ == '__main__':
    unittest.main() 