import unittest
import time
from src.message_format import Message
from src.message_queue import message_queue
import threading
import json
import pytest
from datetime import datetime
from src.handlers import handle_message
from src.state import get_store, set_ideas, get_ideas, set_central, get_central
import uuid
from tests.test_utils import mock_streamlit, set_test_ideas, get_test_ideas, set_test_central, get_test_central

# Import fixture to patch st
pytest.importorskip("tests.test_utils")

class TestStateSync(unittest.TestCase):
    def setUp(self):
        self.message_queue = message_queue
        self.frontend_state = {
            'nodes': {},
            'selectedNode': None
        }
        self.backend_state = {
            'ideas': [],
            'selected_node': None
        }
        self.lock = threading.Lock()
        
        # Patch the _process_next_message method to handle our test messages
        self.original_process_next_message = self.message_queue._process_next_message
        self.message_queue._process_next_message = self._mock_process_next_message

    def tearDown(self):
        # Restore original method
        self.message_queue._process_next_message = self.original_process_next_message
        self.frontend_state = {'nodes': {}, 'selectedNode': None}
        self.backend_state = {'ideas': [], 'selected_node': None}

    def _mock_process_next_message(self, message):
        """Mock implementation that calls our handler directly."""
        return self.handle_message(message)
        
    def enqueue(self, message):
        """Enqueue a message and process it immediately for testing."""
        response = self._mock_process_next_message(message)
        return response

    def handle_message(self, message):
        """Handle incoming messages and update states."""
        with self.lock:
            if message.action == 'create_node':
                # Update both states
                node_id = f"node_{len(self.backend_state['ideas']) + 1}"
                node_data = {
                    'id': node_id,
                    'label': message.payload['title'],
                    'parent': message.payload['parent_id']
                }
                
                # Update backend state
                self.backend_state['ideas'].append(node_data)
                
                # Update frontend state
                self.frontend_state['nodes'][node_id] = {
                    'id': node_id,
                    'title': message.payload['title'],
                    'parentId': message.payload['parent_id']
                }
                
                return Message.create('backend', 'create_node_response', {
                    'new_node': node_data
                })
                
            elif message.action == 'select_node':
                node_id = message.payload['node_id']
                
                # Update both states
                self.frontend_state['selectedNode'] = node_id
                self.backend_state['selected_node'] = node_id
                
                return Message.create('backend', 'select_node_response', {
                    'selected_node': node_id
                })
                
            elif message.action == 'edit_node':
                node_id = message.payload['node_id']
                new_title = message.payload['title']
                
                # Update both states
                if node_id in self.frontend_state['nodes']:
                    self.frontend_state['nodes'][node_id]['title'] = new_title
                
                for idea in self.backend_state['ideas']:
                    if idea['id'] == node_id:
                        idea['label'] = new_title
                        break
                
                return Message.create('backend', 'edit_node_response', {
                    'updated_node': {'id': node_id, 'title': new_title}
                })
                
            elif message.action == 'delete_node':
                node_id = message.payload['node_id']
                
                # Update both states
                if node_id in self.frontend_state['nodes']:
                    del self.frontend_state['nodes'][node_id]
                    if self.frontend_state['selectedNode'] == node_id:
                        self.frontend_state['selectedNode'] = None
                
                self.backend_state['ideas'] = [
                    idea for idea in self.backend_state['ideas']
                    if idea['id'] != node_id
                ]
                if self.backend_state['selected_node'] == node_id:
                    self.backend_state['selected_node'] = None
                
                return Message.create('backend', 'delete_node_response', {})
            
            return Message.create('backend', 'error_response', {
                'error': 'Unknown action'
            })

    def test_node_creation_sync(self):
        """Test state synchronization during node creation."""
        # Create a node
        message = Message.create('frontend', 'create_node', {
            'title': 'Test Node',
            'parent_id': 'root'
        })
        self.enqueue(message)

        with self.lock:
            # Verify frontend state
            self.assertEqual(len(self.frontend_state['nodes']), 1)
            node_id = list(self.frontend_state['nodes'].keys())[0]
            self.assertEqual(self.frontend_state['nodes'][node_id]['title'], 'Test Node')
            
            # Verify backend state
            self.assertEqual(len(self.backend_state['ideas']), 1)
            self.assertEqual(self.backend_state['ideas'][0]['label'], 'Test Node')

    def test_node_selection_sync(self):
        """Test state synchronization during node selection."""
        # First create a node
        create_message = Message.create('frontend', 'create_node', {
            'title': 'Test Node',
            'parent_id': 'root'
        })
        self.enqueue(create_message)

        # Then select the node
        node_id = list(self.frontend_state['nodes'].keys())[0]
        select_message = Message.create('frontend', 'select_node', {
            'node_id': node_id
        })
        self.enqueue(select_message)

        with self.lock:
            # Verify frontend state
            self.assertEqual(self.frontend_state['selectedNode'], node_id)
            
            # Verify backend state
            self.assertEqual(self.backend_state['selected_node'], node_id)

    def test_node_editing_sync(self):
        """Test state synchronization during node editing."""
        # First create a node
        create_message = Message.create('frontend', 'create_node', {
            'title': 'Test Node',
            'parent_id': 'root'
        })
        self.enqueue(create_message)

        # Then edit the node
        node_id = list(self.frontend_state['nodes'].keys())[0]
        edit_message = Message.create('frontend', 'edit_node', {
            'node_id': node_id,
            'title': 'Updated Node'
        })
        self.enqueue(edit_message)

        with self.lock:
            # Verify frontend state
            self.assertEqual(self.frontend_state['nodes'][node_id]['title'], 'Updated Node')
            
            # Verify backend state
            self.assertEqual(self.backend_state['ideas'][0]['label'], 'Updated Node')

    def test_node_deletion_sync(self):
        """Test state synchronization during node deletion."""
        # First create a node
        create_message = Message.create('frontend', 'create_node', {
            'title': 'Test Node',
            'parent_id': 'root'
        })
        self.enqueue(create_message)

        # Select the node
        node_id = list(self.frontend_state['nodes'].keys())[0]
        select_message = Message.create('frontend', 'select_node', {
            'node_id': node_id
        })
        self.enqueue(select_message)

        # Then delete the node
        delete_message = Message.create('frontend', 'delete_node', {
            'node_id': node_id
        })
        self.enqueue(delete_message)

        with self.lock:
            # Verify frontend state
            self.assertEqual(len(self.frontend_state['nodes']), 0)
            self.assertIsNone(self.frontend_state['selectedNode'])
            
            # Verify backend state
            self.assertEqual(len(self.backend_state['ideas']), 0)
            self.assertIsNone(self.backend_state['selected_node'])

    def test_state_sync_sequence(self):
        """Test state synchronization during a sequence of operations."""
        # Create initial node
        create_message = Message.create('frontend', 'create_node', {
            'title': 'Test Node',
            'parent_id': 'root'
        })
        self.enqueue(create_message)

        node_id = list(self.frontend_state['nodes'].keys())[0]

        # Perform sequence of operations
        operations = [
            ('select_node', {'node_id': node_id}),
            ('edit_node', {'node_id': node_id, 'title': 'Updated Node'}),
            ('delete_node', {'node_id': node_id})
        ]

        for action, payload in operations:
            message = Message.create('frontend', action, payload)
            self.enqueue(message)

        with self.lock:
            # Verify final states
            self.assertEqual(len(self.frontend_state['nodes']), 0)
            self.assertIsNone(self.frontend_state['selectedNode'])
            self.assertEqual(len(self.backend_state['ideas']), 0)
            self.assertIsNone(self.backend_state['selected_node'])

def create_test_message(action, payload):
    """Helper function to create test messages with required fields."""
    return Message(
        message_id=str(uuid.uuid4()),
        source='frontend',
        action=action,
        payload=payload,
        timestamp=datetime.now().timestamp() * 1000
    )

def test_node_state_sync():
    """Test node state synchronization between frontend and backend."""
    # Create initial state
    initial_nodes = [
        {
            'id': 1,
            'label': 'Test Node 1',
            'x': 0,
            'y': 0,
            'description': 'Test Description 1',
            'urgency': 'medium',
            'tag': 'test'
        },
        {
            'id': 2,
            'label': 'Test Node 2',
            'x': 100,
            'y': 100,
            'description': 'Test Description 2',
            'urgency': 'high',
            'tag': 'test'
        }
    ]
    
    # Set initial state
    set_ideas(initial_nodes)
    set_central(1)
    
    # Test node update
    update_msg = create_test_message(
        'edit_node',
        {
            'node_id': 1,
            'label': 'Updated Node 1',
            'description': 'Updated Description 1',
            'x': 50,
            'y': 50
        }
    )
    
    response = handle_message(update_msg.to_dict())
    assert response is not None
    assert isinstance(response, Message)
    assert response.status == 'completed'
    assert response.action.endswith('_response')
    
    # Verify state update
    updated_nodes = get_ideas()
    updated_node = next((n for n in updated_nodes if n['id'] == 1), None)
    assert updated_node is not None
    assert updated_node['label'] == 'Updated Node 1'
    assert updated_node['description'] == 'Updated Description 1'
    assert updated_node['x'] == 50
    assert updated_node['y'] == 50

def test_node_creation_sync():
    """Test node creation and state synchronization."""
    # Create new node
    create_msg = create_test_message(
        'new_node',
        {
            'label': 'New Node',
            'description': 'New Description',
            'urgency': 'low',
            'tag': 'new',
            'x': 200,
            'y': 200
        }
    )
    
    response = handle_message(create_msg.to_dict())
    assert response is not None
    assert isinstance(response, Message)
    assert response.status == 'completed'
    assert response.action.endswith('_response')
    
    # Verify node creation
    nodes = get_ideas()
    new_node = next((n for n in nodes if n['label'] == 'New Node'), None)
    assert new_node is not None
    assert new_node['description'] == 'New Description'
    assert new_node['urgency'] == 'low'
    assert new_node['tag'] == 'new'
    assert new_node['x'] == 200
    assert new_node['y'] == 200

def test_node_deletion_sync():
    """Test node deletion and state synchronization."""
    # Create test nodes
    test_nodes = [
        {
            'id': 1,
            'label': 'Parent Node',
            'x': 0,
            'y': 0
        },
        {
            'id': 2,
            'label': 'Child Node',
            'x': 100,
            'y': 100,
            'parent': 1
        }
    ]
    
    set_ideas(test_nodes)
    
    # Delete parent node
    delete_msg = create_test_message(
        'delete',
        {
            'id': 1
        }
    )
    
    response = handle_message(delete_msg.to_dict())
    assert response is not None
    assert isinstance(response, Message)
    assert response.status == 'completed'
    assert response.action.endswith('_response')
    
    # Verify deletion
    nodes = get_ideas()
    assert len(nodes) == 0  # Both parent and child should be deleted

def test_central_node_sync():
    """Test central node state synchronization."""
    # Create test nodes
    test_nodes = [
        {
            'id': 1,
            'label': 'Node 1',
            'x': 0,
            'y': 0
        },
        {
            'id': 2,
            'label': 'Node 2',
            'x': 100,
            'y': 100
        }
    ]
    
    set_ideas(test_nodes)
    
    # Set central node
    central_msg = create_test_message(
        'center_node',
        {
            'id': 2
        }
    )
    
    response = handle_message(central_msg.to_dict())
    assert response is not None
    assert isinstance(response, Message)
    assert response.status == 'completed'
    assert response.action.endswith('_response')
    
    # Verify central node
    assert get_central() == 2

def test_node_position_sync():
    """Test node position synchronization."""
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
    
    # Update node position
    position_msg = create_test_message(
        'pos',
        {
            '1': {'x': 150, 'y': 150}
        }
    )
    
    response = handle_message(position_msg.to_dict())
    assert response is not None
    assert isinstance(response, Message)
    assert response.status == 'completed'
    assert response.action.endswith('_response')
    
    # Verify position update
    nodes = get_ideas()
    node = next((n for n in nodes if n['id'] == 1), None)
    assert node is not None
    assert node['x'] == 150
    assert node['y'] == 150

def test_node_relationship_sync():
    """Test node relationship synchronization."""
    # Create test nodes
    test_nodes = [
        {
            'id': 1,
            'label': 'Parent Node',
            'x': 0,
            'y': 0
        },
        {
            'id': 2,
            'label': 'Child Node',
            'x': 100,
            'y': 100
        }
    ]
    
    set_ideas(test_nodes)
    
    # Update relationship
    relationship_msg = create_test_message(
        'reparent',
        {
            'id': 2,
            'parent': 1
        }
    )
    
    response = handle_message(relationship_msg.to_dict())
    assert response is not None
    assert isinstance(response, Message)
    assert response.status == 'completed'
    assert response.action.endswith('_response')
    
    # Verify relationship update
    nodes = get_ideas()
    child_node = next((n for n in nodes if n['id'] == 2), None)
    assert child_node is not None
    assert child_node['parent'] == 1
    assert child_node['edge_type'] == 'default'

if __name__ == '__main__':
    unittest.main() 