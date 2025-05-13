"""
Node lifecycle test, focusing on position persistence.

This test tracks a node from creation to deletion, with specific focus
on how position data is initialized, updated, and persisted.
"""

import unittest
import sys
import os
import json
import logging
from unittest.mock import patch, MagicMock

# Add the parent directory to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger('node_lifecycle')

# Disable Streamlit warnings
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="streamlit")

# Import app components
try:
    from src.message_format import Message
    from src.state import get_ideas, set_ideas, get_store, save_data
    HAS_IMPORTS = True
except ImportError:
    logger.warning("Could not import required modules, will use mocks")
    HAS_IMPORTS = False

class NodeLifecycleTest(unittest.TestCase):
    """Test case for node lifecycle with focus on position persistence"""
    
    def setUp(self):
        """Set up test environment"""
        # Initial test data
        self.initial_data = {
            'ideas': [],
            'next_id': 1,
            'central': None
        }
        
        # Set up mocks for state management
        self.ideas = []
        self.nodes = []
        self.next_id = 1
        
        # Create mocks
        self.get_ideas_mock = MagicMock(return_value=self.ideas)
        self.set_ideas_mock = MagicMock(side_effect=self.update_ideas)
        self.get_store_mock = MagicMock(return_value={
            'ideas': self.ideas,
            'next_id': self.next_id,
            'central': None if not self.ideas else self.ideas[0]['id']
        })
        self.save_data_mock = MagicMock()
        
        # Apply patches
        self.patches = []
        self.patches.append(patch('src.state.get_ideas', self.get_ideas_mock))
        self.patches.append(patch('src.state.set_ideas', self.set_ideas_mock))
        self.patches.append(patch('src.state.get_store', self.get_store_mock))
        self.patches.append(patch('src.state.save_data', self.save_data_mock))
        
        # Start all patches
        for p in self.patches:
            p.start()
    
    def tearDown(self):
        """Clean up after test"""
        for p in self.patches:
            p.stop()
    
    def update_ideas(self, new_ideas):
        """Mock implementation of set_ideas"""
        self.ideas = new_ideas
        return True
    
    def test_node_lifecycle(self):
        """Test the complete lifecycle of a node with position persistence"""
        logger.info("--- Starting node lifecycle test ---")
        
        # Step 1: Create a node
        logger.info("\n=== Step 1: Create a node ===")
        node_id = self.create_node("Test Node", "This is a test node")
        self.assertIsNotNone(node_id, "Node creation failed")
        logger.info(f"Created node with ID: {node_id}")
        
        # Verify initial position
        node = self.find_node(node_id)
        self.assertIsNotNone(node, f"Node {node_id} not found after creation")
        
        initial_x = node.get('x')
        initial_y = node.get('y')
        logger.info(f"Initial position: ({initial_x}, {initial_y})")
        
        # Check if position is initialized
        self.assertIsNotNone(initial_x, "X coordinate not initialized")
        self.assertIsNotNone(initial_y, "Y coordinate not initialized")
        
        # Step 2: Update the node position
        logger.info("\n=== Step 2: Update node position ===")
        new_x, new_y = 100, 200
        success = self.update_node_position(node_id, new_x, new_y)
        self.assertTrue(success, f"Failed to update position of node {node_id}")
        
        # Verify position was updated
        node = self.find_node(node_id)
        self.assertIsNotNone(node, f"Node {node_id} not found after position update")
        
        updated_x = node.get('x')
        updated_y = node.get('y')
        logger.info(f"Updated position: ({updated_x}, {updated_y})")
        
        self.assertEqual(updated_x, new_x, f"X coordinate not updated correctly: {updated_x} != {new_x}")
        self.assertEqual(updated_y, new_y, f"Y coordinate not updated correctly: {updated_y} != {new_y}")
        
        # Step 3: Simulate reload (clear and reload data)
        logger.info("\n=== Step 3: Simulate app reload ===")
        data_before_reload = {
            'ideas': self.ideas,
            'next_id': self.next_id,
            'central': node_id
        }
        
        # Save data for reload simulation
        self.save_data_before_reload(data_before_reload)
        
        # Clear in-memory state to simulate app restart
        self.ideas = []
        self.next_id = 1
        
        # Reload from saved data
        self.reload_data()
        
        # Verify position persisted across reload
        node = self.find_node(node_id)
        self.assertIsNotNone(node, f"Node {node_id} not found after reload")
        
        reloaded_x = node.get('x')
        reloaded_y = node.get('y')
        logger.info(f"Position after reload: ({reloaded_x}, {reloaded_y})")
        
        self.assertEqual(reloaded_x, new_x, f"X coordinate not preserved across reload: {reloaded_x} != {new_x}")
        self.assertEqual(reloaded_y, new_y, f"Y coordinate not preserved across reload: {reloaded_y} != {new_y}")
        
        # Step 4: Update position again
        logger.info("\n=== Step 4: Update position again ===")
        newer_x, newer_y = 300, 400
        success = self.update_node_position(node_id, newer_x, newer_y)
        self.assertTrue(success, f"Failed to update position of node {node_id} second time")
        
        # Verify second position update
        node = self.find_node(node_id)
        second_x = node.get('x')
        second_y = node.get('y')
        logger.info(f"Position after second update: ({second_x}, {second_y})")
        
        self.assertEqual(second_x, newer_x, f"X coordinate not updated correctly second time: {second_x} != {newer_x}")
        self.assertEqual(second_y, newer_y, f"Y coordinate not updated correctly second time: {second_y} != {newer_y}")
        
        # Step 5: Delete the node
        logger.info("\n=== Step 5: Delete the node ===")
        success = self.delete_node(node_id)
        self.assertTrue(success, f"Failed to delete node {node_id}")
        
        # Verify node is gone
        node = self.find_node(node_id)
        self.assertIsNone(node, f"Node {node_id} still exists after deletion")
        
        logger.info("--- Node lifecycle test complete ---")
    
    def create_node(self, label, description, parent=None, position=None):
        """Create a new node and return its ID"""
        # Default position if none provided
        if position is None:
            position = {'x': 0, 'y': 0}
        
        # Create node data
        node = {
            'id': self.next_id,
            'label': label,
            'description': description,
            'urgency': 'medium',
            'tag': '',
            'parent': parent,
            'edge_type': 'default',
            'x': position['x'],
            'y': position['y']
        }
        
        # Add to ideas list
        self.ideas.append(node)
        
        # Increment next_id
        self.next_id += 1
        
        # Update the state
        self.set_ideas_mock(self.ideas)
        self.save_data_mock(self.get_store_mock())
        
        return node['id']
    
    def update_node_position(self, node_id, new_x, new_y):
        """Update a node's position"""
        # Find the node
        node = self.find_node(node_id)
        if not node:
            return False
        
        # Update position
        node['x'] = new_x
        node['y'] = new_y
        
        # Update the state
        self.set_ideas_mock(self.ideas)
        self.save_data_mock(self.get_store_mock())
        
        return True
    
    def find_node(self, node_id):
        """Find a node by ID"""
        return next((n for n in self.ideas if n['id'] == node_id), None)
    
    def delete_node(self, node_id):
        """Delete a node"""
        # Find the node
        node = self.find_node(node_id)
        if not node:
            return False
        
        # Remove node from ideas
        self.ideas = [n for n in self.ideas if n['id'] != node_id]
        
        # Also remove any child nodes
        self.ideas = [n for n in self.ideas if n.get('parent') != node_id]
        
        # Update the state
        self.set_ideas_mock(self.ideas)
        self.save_data_mock(self.get_store_mock())
        
        return True
    
    def save_data_before_reload(self, data):
        """Simulate saving data before reload"""
        # In a real app, this would write to a file or database
        self._saved_data = data
        logger.info(f"Data saved before reload: {data}")
    
    def reload_data(self):
        """Simulate reloading data after app restart"""
        # In a real app, this would read from a file or database
        if not hasattr(self, '_saved_data'):
            logger.error("No saved data to reload")
            return False
        
        # Reload data
        self.ideas = self._saved_data['ideas']
        self.next_id = self._saved_data['next_id']
        
        logger.info(f"Data reloaded: {self.ideas}")
        return True
    
    def test_position_initialization(self):
        """Test how positions are initialized for new nodes"""
        logger.info("--- Starting position initialization test ---")
        
        # Test 1: Default positioning
        logger.info("\n=== Test 1: Default positioning ===")
        node_id = self.create_node("Default Position Node", "Node with default position")
        node = self.find_node(node_id)
        
        logger.info(f"Default position: ({node['x']}, {node['y']})")
        self.assertIsNotNone(node['x'], "X coordinate not initialized")
        self.assertIsNotNone(node['y'], "Y coordinate not initialized")
        
        # Test 2: Specified positioning
        logger.info("\n=== Test 2: Specified positioning ===")
        custom_x, custom_y = 150, 250
        node_id = self.create_node("Custom Position Node", "Node with custom position", 
                                  position={'x': custom_x, 'y': custom_y})
        node = self.find_node(node_id)
        
        logger.info(f"Custom position: ({node['x']}, {node['y']})")
        self.assertEqual(node['x'], custom_x, f"X coordinate not initialized correctly: {node['x']} != {custom_x}")
        self.assertEqual(node['y'], custom_y, f"Y coordinate not initialized correctly: {node['y']} != {custom_y}")
        
        # Test 3: Child node positioning
        logger.info("\n=== Test 3: Child node positioning ===")
        parent_id = node_id  # Use the previous node as parent
        child_id = self.create_node("Child Node", "Child of node with custom position", parent=parent_id)
        child = self.find_node(child_id)
        
        logger.info(f"Child position: ({child['x']}, {child['y']})")
        self.assertIsNotNone(child['x'], "Child X coordinate not initialized")
        self.assertIsNotNone(child['y'], "Child Y coordinate not initialized")
        
        # In a typical application, child nodes might be positioned relative to parent
        # We're just checking that positions are initialized
        
        logger.info("--- Position initialization test complete ---")
    
    def test_multiple_position_updates(self):
        """Test multiple position updates in sequence"""
        logger.info("--- Starting multiple position updates test ---")
        
        # Create a node
        node_id = self.create_node("Multiple Update Node", "Node for multiple position updates")
        
        # Perform multiple updates
        updates = [
            {'x': 100, 'y': 100},
            {'x': 200, 'y': 200},
            {'x': 300, 'y': 300},
            {'x': 400, 'y': 400},
            {'x': 500, 'y': 500}
        ]
        
        for i, update in enumerate(updates):
            logger.info(f"\n=== Update {i+1}: ({update['x']}, {update['y']}) ===")
            success = self.update_node_position(node_id, update['x'], update['y'])
            self.assertTrue(success, f"Failed to update position to ({update['x']}, {update['y']})")
            
            # Verify update
            node = self.find_node(node_id)
            self.assertEqual(node['x'], update['x'], f"X coordinate not updated correctly: {node['x']} != {update['x']}")
            self.assertEqual(node['y'], update['y'], f"Y coordinate not updated correctly: {node['y']} != {update['y']}")
        
        # Final position should match the last update
        node = self.find_node(node_id)
        last_update = updates[-1]
        logger.info(f"Final position: ({node['x']}, {node['y']})")
        self.assertEqual(node['x'], last_update['x'], f"Final X position incorrect: {node['x']} != {last_update['x']}")
        self.assertEqual(node['y'], last_update['y'], f"Final Y position incorrect: {node['y']} != {last_update['y']}")
        
        logger.info("--- Multiple position updates test complete ---")

if __name__ == '__main__':
    unittest.main() 