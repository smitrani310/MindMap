"""
Debug script for position update flow.

This script traces the complete flow of position updates from frontend to backend,
with detailed logging at each step to identify where positions might be lost.
"""

import sys
import os
import json
import logging
import time
from unittest.mock import patch, MagicMock

# Add the parent directory to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger('debug_position')

# Disable Streamlit warnings
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="streamlit")

# Import app components
from src.message_format import Message
try:
    from src.message_queue import message_queue
    from src.handlers import handle_message
    from src.state import get_ideas, set_ideas, get_store, save_data
    HAS_QUEUE = True
except ImportError:
    logger.warning("Couldn't import message_queue, will use mocks instead")
    HAS_QUEUE = False

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
        'y': 0
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

class PositionFlowDebugger:
    """Class to debug position update flow"""
    
    def __init__(self):
        """Initialize the debugger"""
        self.nodes = [node.copy() for node in TEST_NODES]
        self.setup_mocks()
        
    def setup_mocks(self):
        """Set up mocks for state management"""
        # Mock for state management
        self.ideas_getter_mock = MagicMock(return_value=self.nodes)
        self.ideas_setter_mock = MagicMock()
        self.store_getter_mock = MagicMock(return_value={
            'ideas': self.nodes,
            'next_id': 3,
            'central': 1
        })
        self.save_data_mock = MagicMock()
        
        # Apply patches
        self.patches = []
        self.patches.append(patch('src.state.get_ideas', self.ideas_getter_mock))
        self.patches.append(patch('src.state.set_ideas', self.ideas_setter_mock))
        self.patches.append(patch('src.state.get_store', self.store_getter_mock))
        self.patches.append(patch('src.state.save_data', self.save_data_mock))
        
        # Start all patches
        for p in self.patches:
            p.start()
    
    def teardown_mocks(self):
        """Tear down mocks"""
        for p in self.patches:
            p.stop()
    
    def simulate_frontend_drag(self, node_id, new_x, new_y):
        """Simulate a frontend drag operation"""
        logger.info(f"[FRONTEND] Dragging node {node_id} to position ({new_x}, {new_y})")
        
        # Create a drag event object similar to what vis.js would produce
        drag_event = {
            'nodes': [str(node_id)]
        }
        
        # Mock what the dragEnd handler would do
        logger.debug(f"[FRONTEND] dragEnd event fired with: {drag_event}")
        
        # Get node position from vis.js (mocked)
        node_positions = self._mock_vis_get_positions([str(node_id)])
        node_position = node_positions[str(node_id)]
        
        # In our test, override the mocked position with our test values
        node_position['x'] = new_x
        node_position['y'] = new_y
        
        logger.debug(f"[FRONTEND] Node position from vis.js: {node_position}")
        
        # Create the position message
        message_payload = {
            'id': node_id,
            'x': node_position['x'],
            'y': node_position['y']
        }
        
        logger.info(f"[FRONTEND] Sending position message: {message_payload}")
        
        # In the real app, this would be sent through Streamlit's component_value
        # Here we'll directly call our backend simulation
        self.simulate_backend_message_handling(message_payload)
    
    def _mock_vis_get_positions(self, node_ids):
        """Mock the vis.js getPositions method"""
        result = {}
        for node_id in node_ids:
            # In real app, this would return the actual position from the vis.js network
            result[node_id] = {'x': 100, 'y': 200}  # Default mock values
        return result
    
    def simulate_backend_message_handling(self, message_payload):
        """Simulate backend handling of a position message"""
        logger.info(f"[BACKEND] Received position message: {message_payload}")
        
        # This simulates what happens in main.py when a message is received
        # First, a Message object is created
        message = Message.create('frontend', 'pos', message_payload)
        logger.debug(f"[BACKEND] Created Message object: {message.to_dict()}")
        
        # Check if we can use the actual message queue or need to mock it
        if HAS_QUEUE:
            logger.info("[BACKEND] Using actual message_queue for processing")
            # Process with the message queue
            try:
                response = message_queue._handle_position(message)
                logger.info(f"[BACKEND] Response: {response.to_dict()}")
            except Exception as e:
                logger.error(f"[BACKEND] Error in message_queue._handle_position: {e}")
                # Fall back to direct processing
                self.process_position_directly(message_payload)
        else:
            logger.info("[BACKEND] Using direct position processing (mock)")
            # Process directly
            self.process_position_directly(message_payload)
    
    def process_position_directly(self, payload):
        """Process position update directly, bypassing the message queue"""
        logger.info(f"[BACKEND] Direct position processing: {payload}")
        
        # Extract position data
        node_id = payload.get('id')
        new_x = payload.get('x')
        new_y = payload.get('y')
        
        # Validate data
        if not (node_id and new_x is not None and new_y is not None):
            logger.error(f"[BACKEND] Missing position data: id={node_id}, x={new_x}, y={new_y}")
            return
        
        # Get current ideas
        ideas = self.ideas_getter_mock()
        logger.debug(f"[BACKEND] Current ideas before update: {ideas}")
        
        # Find the node
        updated = False
        for node in ideas:
            if 'id' in node and str(node['id']) == str(node_id):
                logger.info(f"[BACKEND] Found node {node_id}, updating position: {new_x}, {new_y}")
                
                # Log previous position
                prev_x = node.get('x')
                prev_y = node.get('y')
                logger.debug(f"[BACKEND] Previous position: ({prev_x}, {prev_y})")
                
                # Update position
                node['x'] = new_x
                node['y'] = new_y
                updated = True
                break
        
        if not updated:
            logger.error(f"[BACKEND] Node {node_id} not found!")
            return
        
        # Update ideas
        logger.debug(f"[BACKEND] Setting ideas with updated positions")
        self.ideas_setter_mock(ideas)
        
        # Save data
        logger.debug(f"[BACKEND] Saving data")
        self.save_data_mock(self.store_getter_mock())
        
        # Verify the update worked
        self.verify_update(node_id, new_x, new_y)
    
    def verify_update(self, node_id, expected_x, expected_y):
        """Verify that the position update was successful"""
        # In a real app, this would read from the data store
        # Here we're reading directly from our mocked data
        ideas = self.ideas_getter_mock()
        node = next((n for n in ideas if str(n['id']) == str(node_id)), None)
        
        if not node:
            logger.error(f"[VERIFY] Node {node_id} not found when verifying!")
            return False
        
        actual_x = node.get('x')
        actual_y = node.get('y')
        
        if actual_x == expected_x and actual_y == expected_y:
            logger.info(f"[VERIFY] Success! Position updated to ({actual_x}, {actual_y})")
            return True
        else:
            logger.error(f"[VERIFY] Failed! Expected ({expected_x}, {expected_y}), but got ({actual_x}, {actual_y})")
            return False
    
    def check_all_code_paths(self):
        """Run a series of tests to check all code paths in position handling"""
        logger.info("--- Starting position update flow debug ---")
        
        # Test 1: Standard position update
        logger.info("\n=== Test 1: Standard position update ===")
        self.simulate_frontend_drag(1, 100, 200)
        
        # Test 2: Alternative format
        logger.info("\n=== Test 2: Alternative position format ===")
        # Create position message in alternative format
        alt_message = {'2': {'x': 150, 'y': 250}}
        self.simulate_backend_message_handling(alt_message)
        
        # Test 3: Position update via main.py flow
        logger.info("\n=== Test 3: Direct position update (main.py flow) ===")
        self.simulate_main_py_flow(1, 300, 400)
        
        # Test 4: Check direct DOM-to-backend flow
        logger.info("\n=== Test 4: DOM direct to backend flow ===")
        self.simulate_dom_to_backend_flow(2, 500, 600)
        
        logger.info("--- Position update flow debug complete ---")
    
    def simulate_main_py_flow(self, node_id, new_x, new_y):
        """Simulate how main.py directly handles position updates"""
        logger.info(f"[MAIN.PY] Processing position update: id={node_id}, x={new_x}, y={new_y}")
        
        # Get ideas
        ideas = self.ideas_getter_mock()
        logger.debug(f"[MAIN.PY] Current ideas before update: {ideas}")
        
        # Find and update node
        updated = False
        for node in ideas:
            if 'id' in node and str(node['id']) == str(node_id):
                logger.info(f"[MAIN.PY] Found node {node_id}, updating position: {new_x}, {new_y}")
                
                # Log previous position
                prev_x = node.get('x')
                prev_y = node.get('y')
                logger.debug(f"[MAIN.PY] Previous position: ({prev_x}, {prev_y})")
                
                # Update position
                node['x'] = new_x
                node['y'] = new_y
                updated = True
                break
        
        if not updated:
            logger.error(f"[MAIN.PY] Node {node_id} not found!")
            return
        
        # Update ideas
        logger.debug(f"[MAIN.PY] Setting ideas with updated positions")
        self.ideas_setter_mock(ideas)
        
        # Save data
        logger.debug(f"[MAIN.PY] Saving data")
        self.save_data_mock(self.store_getter_mock())
        
        # Verify the update worked
        self.verify_update(node_id, new_x, new_y)
    
    def simulate_dom_to_backend_flow(self, node_id, new_x, new_y):
        """Simulate direct DOM-to-backend flow, as it would happen in production"""
        logger.info(f"[DOM] Drag node {node_id} to position ({new_x}, {new_y})")
        
        # In real app, this would be the JavaScript function that gets called on dragEnd
        js_code = f"""
        function onDragEnd(params) {{
            if (params.nodes && params.nodes.length > 0) {{
                const nodeId = params.nodes[0];
                const nodePosition = window.visNetwork.getPositions([nodeId])[nodeId];
                console.log('Node dragged:', nodeId, 'to position:', nodePosition);
                
                // Send position update
                sendMessage('pos', {{
                    id: nodeId,
                    x: nodePosition.x,
                    y: nodePosition.y
                }});
            }}
        }}
        """
        logger.debug(f"[DOM] JavaScript code: {js_code}")
        
        # Mock the params that would be passed to the dragEnd handler
        params = {'nodes': [str(node_id)]}
        logger.debug(f"[DOM] Drag event params: {params}")
        
        # Mock the position that would be returned by vis.js
        positions = {str(node_id): {'x': new_x, 'y': new_y}}
        logger.debug(f"[DOM] Positions from vis.js: {positions}")
        
        # Create the message that would be sent to the backend
        message_payload = {
            'id': node_id,
            'x': new_x,
            'y': new_y
        }
        logger.info(f"[DOM] Sending position message: {message_payload}")
        
        # Simulate backend handling
        self.simulate_backend_message_handling(message_payload)
    
    def run(self):
        """Run the debugger"""
        try:
            self.check_all_code_paths()
        finally:
            self.teardown_mocks()

if __name__ == "__main__":
    debugger = PositionFlowDebugger()
    debugger.run() 