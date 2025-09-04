"""
Integration tests for UI components with the new service layer.

This module tests that UI components correctly integrate with the service adapter
and that the new architecture works seamlessly with existing UI code.
"""

import pytest
import streamlit as st
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

from src.integration.service_adapter import ServiceAdapter, get_service_adapter, init_service_adapter
from src.domain.models import Node, Position, UrgencyLevel, EdgeType
from src.infrastructure.config import AppConfig


class TestUIServiceIntegration:
    """Test UI integration with the service layer."""
    
    @pytest.fixture
    def temp_config(self):
        """Create a temporary configuration for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = AppConfig(
                data_file=os.path.join(temp_dir, "test_data.json"),
                backup_dir=os.path.join(temp_dir, "backups"),
                log_dir=os.path.join(temp_dir, "logs")
            )
            yield config
    
    @pytest.fixture
    def service_adapter(self, temp_config):
        """Create a service adapter for testing."""
        with patch('src.integration.service_adapter.ConfigFactory.create_config', return_value=temp_config):
            adapter = ServiceAdapter()
            yield adapter
    
    def test_service_adapter_initialization(self, service_adapter):
        """Test that the service adapter initializes correctly."""
        assert service_adapter is not None
        assert service_adapter.service is not None
        assert service_adapter.repository is not None
        assert service_adapter.config is not None
    
    def test_get_ideas_empty(self, service_adapter):
        """Test getting ideas when no nodes exist."""
        ideas = service_adapter.get_ideas()
        assert ideas == []
    
    def test_add_idea_integration(self, service_adapter):
        """Test adding an idea through the service adapter."""
        node_data = {
            'label': 'Test Node',
            'description': 'Test Description',
            'urgency': 'high',
            'tag': 'test',
            'x': 100.0,
            'y': 200.0,
            'parent': None,
            'edge_type': 'default'
        }
        
        success = service_adapter.add_idea(node_data)
        assert success is True
        
        ideas = service_adapter.get_ideas()
        assert len(ideas) == 1
        
        added_node = ideas[0]
        assert added_node['label'] == 'Test Node'
        assert added_node['description'] == 'Test Description'
        assert added_node['urgency'] == 'high'
        assert added_node['tag'] == 'test'
        assert added_node['x'] == 100.0
        assert added_node['y'] == 200.0
        assert added_node['parent'] is None
        assert added_node['edge_type'] == 'default'
    
    def test_central_node_operations(self, service_adapter):
        """Test central node operations through the service adapter."""
        # Initially no central node
        assert service_adapter.get_central() is None
        
        # Add a node
        node_data = {
            'label': 'Central Node',
            'description': 'This will be central',
            'urgency': 'medium',
            'tag': '',
            'x': 0.0,
            'y': 0.0,
            'parent': None,
            'edge_type': 'default'
        }
        
        success = service_adapter.add_idea(node_data)
        assert success is True
        
        ideas = service_adapter.get_ideas()
        node_id = ideas[0]['id']
        
        # Set as central
        success = service_adapter.set_central(node_id)
        assert success is True
        
        # Verify it's central
        central_id = service_adapter.get_central()
        assert central_id == node_id
    
    def test_node_search_integration(self, service_adapter):
        """Test node search through the service adapter."""
        # Add multiple nodes
        nodes_data = [
            {'label': 'Important Task', 'description': 'Very important', 'urgency': 'high', 'tag': 'work', 'x': 0, 'y': 0},
            {'label': 'Personal Note', 'description': 'Personal stuff', 'urgency': 'low', 'tag': 'personal', 'x': 100, 'y': 100},
            {'label': 'Research Topic', 'description': 'Important research', 'urgency': 'medium', 'tag': 'research', 'x': 200, 'y': 200}
        ]
        
        for node_data in nodes_data:
            success = service_adapter.add_idea(node_data)
            assert success is True
        
        # Search for nodes
        results = service_adapter.search_nodes('important')
        assert len(results) == 2  # Should find "Important Task" and "Research Topic"
        
        labels = [node['label'] for node in results]
        assert 'Important Task' in labels
        assert 'Research Topic' in labels
    
    def test_statistics_integration(self, service_adapter):
        """Test statistics through the service adapter."""
        # Initially empty
        stats = service_adapter.get_statistics()
        assert stats['total_nodes'] == 0
        
        # Add some nodes
        nodes_data = [
            {'label': 'High Priority', 'urgency': 'high', 'tag': 'work', 'x': 0, 'y': 0},
            {'label': 'Medium Priority', 'urgency': 'medium', 'tag': 'work', 'x': 100, 'y': 100},
            {'label': 'Low Priority', 'urgency': 'low', 'tag': 'personal', 'x': 200, 'y': 200}
        ]
        
        for node_data in nodes_data:
            success = service_adapter.add_idea(node_data)
            assert success is True
        
        # Check updated statistics
        stats = service_adapter.get_statistics()
        assert stats['total_nodes'] == 3
        assert stats['urgency_distribution']['high'] == 1
        assert stats['urgency_distribution']['medium'] == 1
        assert stats['urgency_distribution']['low'] == 1
        assert stats['tag_distribution']['work'] == 2
        assert stats['tag_distribution']['personal'] == 1
    
    def test_settings_integration(self, service_adapter):
        """Test settings operations through the service adapter."""
        # Get default settings
        settings = service_adapter.get_settings()
        assert 'color_mode' in settings
        assert 'edge_length' in settings
        
        # Update settings
        new_settings = settings.copy()
        new_settings['color_mode'] = 'tag'
        new_settings['edge_length'] = 150
        
        success = service_adapter.update_settings(new_settings)
        assert success is True
        
        # Verify settings were updated
        updated_settings = service_adapter.get_settings()
        assert updated_settings['color_mode'] == 'tag'
        assert updated_settings['edge_length'] == 150
    
    def test_backup_restore_integration(self, service_adapter):
        """Test backup and restore operations through the service adapter."""
        # Add some data
        node_data = {
            'label': 'Test Node for Backup',
            'description': 'This node will be backed up',
            'urgency': 'medium',
            'tag': 'test',
            'x': 50.0,
            'y': 75.0
        }
        
        success = service_adapter.add_idea(node_data)
        assert success is True
        
        # Create backup
        backup_path = service_adapter.create_backup()
        assert backup_path is not None
        assert isinstance(backup_path, str)
        
        # List backups
        backups = service_adapter.list_backups()
        assert len(backups) >= 1
        
        # Verify backup info structure
        backup_info = backups[0]
        assert 'path' in backup_info
        assert 'filename' in backup_info
        assert 'created_at' in backup_info
        assert 'size' in backup_info
    
    def test_node_update_integration(self, service_adapter):
        """Test node updates through the service adapter."""
        # Add a node
        node_data = {
            'label': 'Original Label',
            'description': 'Original Description',
            'urgency': 'low',
            'tag': 'original',
            'x': 0.0,
            'y': 0.0
        }
        
        success = service_adapter.add_idea(node_data)
        assert success is True
        
        ideas = service_adapter.get_ideas()
        node_id = ideas[0]['id']
        
        # Update the node
        updates = {
            'label': 'Updated Label',
            'description': 'Updated Description',
            'urgency': 'high',
            'tag': 'updated',
            'x': 100.0,
            'y': 200.0
        }
        
        success = service_adapter.update_node(node_id, updates)
        assert success is True
        
        # Verify updates
        updated_node = service_adapter.find_node_by_id(node_id)
        assert updated_node is not None
        assert updated_node['label'] == 'Updated Label'
        assert updated_node['description'] == 'Updated Description'
        assert updated_node['urgency'] == 'high'
        assert updated_node['tag'] == 'updated'
        assert updated_node['x'] == 100.0
        assert updated_node['y'] == 200.0
    
    def test_node_deletion_integration(self, service_adapter):
        """Test node deletion through the service adapter."""
        # Add parent and child nodes
        parent_data = {
            'label': 'Parent Node',
            'description': 'This is the parent',
            'urgency': 'medium',
            'tag': 'parent',
            'x': 0.0,
            'y': 0.0
        }
        
        success = service_adapter.add_idea(parent_data)
        assert success is True
        
        ideas = service_adapter.get_ideas()
        parent_id = ideas[0]['id']
        
        child_data = {
            'label': 'Child Node',
            'description': 'This is the child',
            'urgency': 'low',
            'tag': 'child',
            'x': 100.0,
            'y': 100.0,
            'parent': parent_id
        }
        
        success = service_adapter.add_idea(child_data)
        assert success is True
        
        # Verify we have 2 nodes
        ideas = service_adapter.get_ideas()
        assert len(ideas) == 2
        
        # Delete parent (should also delete child)
        success = service_adapter.delete_node(parent_id)
        assert success is True
        
        # Verify both nodes are deleted
        ideas = service_adapter.get_ideas()
        assert len(ideas) == 0
    
    def test_format_conversion(self, service_adapter):
        """Test that format conversion between old and new formats works correctly."""
        # Test with complex node data
        node_data = {
            'label': 'Complex Node',
            'description': 'A node with all properties',
            'urgency': 'high',
            'tag': 'complex',
            'x': 123.45,
            'y': 678.90,
            'parent': None,
            'edge_type': 'strong'
        }
        
        success = service_adapter.add_idea(node_data)
        assert success is True
        
        ideas = service_adapter.get_ideas()
        retrieved_node = ideas[0]
        
        # Verify all properties are preserved
        assert retrieved_node['label'] == node_data['label']
        assert retrieved_node['description'] == node_data['description']
        assert retrieved_node['urgency'] == node_data['urgency']
        assert retrieved_node['tag'] == node_data['tag']
        assert retrieved_node['x'] == node_data['x']
        assert retrieved_node['y'] == node_data['y']
        assert retrieved_node['parent'] == node_data['parent']
        assert retrieved_node['edge_type'] == node_data['edge_type']
        
        # Verify additional properties are added
        assert 'id' in retrieved_node
        assert 'size' in retrieved_node
        assert 'color' in retrieved_node
        assert 'created_at' in retrieved_node
        assert 'updated_at' in retrieved_node


class TestUIComponentIntegration:
    """Test specific UI component integration scenarios."""
    
    @pytest.fixture
    def mock_streamlit(self):
        """Mock Streamlit session state."""
        with patch('streamlit.session_state', {}) as mock_state:
            yield mock_state
    
    @pytest.fixture
    def service_adapter(self, mock_streamlit):
        """Create a service adapter with mocked Streamlit."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = AppConfig(
                data_file=os.path.join(temp_dir, "test_data.json"),
                backup_dir=os.path.join(temp_dir, "backups"),
                log_dir=os.path.join(temp_dir, "logs")
            )
            
            with patch('src.integration.service_adapter.ConfigFactory.create_config', return_value=config):
                adapter = ServiceAdapter()
                yield adapter
    
    def test_network_visualization_integration(self, service_adapter, mock_streamlit):
        """Test that network visualization works with the service adapter."""
        # Add some test nodes
        nodes_data = [
            {'label': 'Central Node', 'urgency': 'high', 'tag': 'center', 'x': 0, 'y': 0},
            {'label': 'Child Node 1', 'urgency': 'medium', 'tag': 'child', 'x': 100, 'y': 100, 'parent': None},
            {'label': 'Child Node 2', 'urgency': 'low', 'tag': 'child', 'x': -100, 'y': -100, 'parent': None}
        ]
        
        for node_data in nodes_data:
            success = service_adapter.add_idea(node_data)
            assert success is True
        
        # Set central node
        ideas = service_adapter.get_ideas()
        central_id = ideas[0]['id']
        success = service_adapter.set_central(central_id)
        assert success is True
        
        # Test that we can get the data needed for visualization
        ideas = service_adapter.get_ideas()
        central_id = service_adapter.get_central()
        settings = service_adapter.get_settings()
        
        assert len(ideas) == 3
        assert central_id is not None
        assert 'color_mode' in settings
        assert 'edge_length' in settings
        assert 'size_multiplier' in settings
    
    def test_add_bubble_integration(self, service_adapter, mock_streamlit):
        """Test that add bubble functionality works with the service adapter."""
        # Simulate adding a node through the UI
        initial_count = len(service_adapter.get_ideas())
        
        node_data = {
            'label': 'New Bubble',
            'description': 'Added through UI',
            'urgency': 'medium',
            'tag': 'ui-test',
            'x': 50,
            'y': 75,
            'parent': None,
            'edge_type': 'default'
        }
        
        success = service_adapter.add_idea(node_data)
        assert success is True
        
        # Verify the node was added
        ideas = service_adapter.get_ideas()
        assert len(ideas) == initial_count + 1
        
        new_node = ideas[-1]  # Last added node
        assert new_node['label'] == 'New Bubble'
        assert new_node['description'] == 'Added through UI'
        assert new_node['urgency'] == 'medium'
        assert new_node['tag'] == 'ui-test'
    
    def test_node_details_integration(self, service_adapter, mock_streamlit):
        """Test that node details functionality works with the service adapter."""
        # Add a node with full details
        node_data = {
            'label': 'Detailed Node',
            'description': 'This node has lots of details for testing',
            'urgency': 'high',
            'tag': 'detailed',
            'x': 200,
            'y': 300,
            'parent': None,
            'edge_type': 'strong'
        }
        
        success = service_adapter.add_idea(node_data)
        assert success is True
        
        ideas = service_adapter.get_ideas()
        node_id = ideas[0]['id']
        
        # Set as central node
        success = service_adapter.set_central(node_id)
        assert success is True
        
        # Test retrieving node details
        central_id = service_adapter.get_central()
        assert central_id == node_id
        
        node_details = service_adapter.find_node_by_id(central_id)
        assert node_details is not None
        assert node_details['label'] == 'Detailed Node'
        assert node_details['description'] == 'This node has lots of details for testing'
        assert node_details['urgency'] == 'high'
        assert node_details['tag'] == 'detailed'
        
        # Test color mode toggle
        settings = service_adapter.get_settings()
        original_mode = settings.get('color_mode', 'urgency')
        
        new_settings = settings.copy()
        new_settings['color_mode'] = 'tag' if original_mode == 'urgency' else 'urgency'
        
        success = service_adapter.update_settings(new_settings)
        assert success is True
        
        updated_settings = service_adapter.get_settings()
        assert updated_settings['color_mode'] != original_mode


if __name__ == "__main__":
    pytest.main([__file__])