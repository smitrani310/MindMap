"""
Integration tests for the service adapter.

These tests verify that the service adapter correctly bridges the old and new architectures.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from src.integration.service_adapter import ServiceAdapter, get_service_adapter
from src.domain.models import Node, Position, UrgencyLevel, EdgeType
from src.infrastructure.config import AppConfig


class TestServiceAdapter:
    """Test cases for the ServiceAdapter integration layer."""
    
    @pytest.fixture
    def temp_config(self):
        """Create a temporary configuration for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            config = AppConfig(
                data_file=str(temp_path / "test_adapter.json"),
                backup_dir=str(temp_path / "backups"),
                log_dir=str(temp_path / "logs"),
                environment="testing"
            )
            
            yield config
    
    @pytest.fixture
    def adapter(self, temp_config):
        """Create a service adapter for testing."""
        with patch('src.integration.service_adapter.ConfigFactory.create_config', return_value=temp_config):
            adapter = ServiceAdapter()
            return adapter
    
    def test_adapter_initialization(self, adapter):
        """Test that the adapter initializes correctly."""
        assert adapter.config is not None
        assert adapter.repository is not None
        assert adapter.service is not None
    
    def test_backward_compatibility_get_ideas(self, adapter):
        """Test getting ideas in old format."""
        # Add a node using the new service
        service = adapter.get_service()
        from src.application.services import NodeCreateRequest
        
        request = NodeCreateRequest(
            label="Test Node",
            description="Test Description",
            position=Position(10, 20),
            urgency=UrgencyLevel.HIGH,
            tag="test"
        )
        
        result = service.create_node(request)
        assert result.is_ok()
        
        # Get ideas in old format
        ideas = adapter.get_ideas()
        assert len(ideas) == 1
        
        idea = ideas[0]
        assert idea['label'] == "Test Node"
        assert idea['description'] == "Test Description"
        assert idea['x'] == 10
        assert idea['y'] == 20
        assert idea['urgency'] == "high"
        assert idea['tag'] == "test"
        assert 'id' in idea
    
    def test_backward_compatibility_add_idea(self, adapter):
        """Test adding ideas using old format."""
        old_format_node = {
            'label': 'Old Format Node',
            'description': 'Added using old format',
            'x': 100,
            'y': 200,
            'urgency': 'medium',
            'tag': 'legacy',
            'parent': None,
            'edge_type': 'default'
        }
        
        success = adapter.add_idea(old_format_node)
        assert success
        
        # Verify the node was added correctly
        ideas = adapter.get_ideas()
        assert len(ideas) == 1
        
        added_node = ideas[0]
        assert added_node['label'] == 'Old Format Node'
        assert added_node['description'] == 'Added using old format'
        assert added_node['x'] == 100
        assert added_node['y'] == 200
        assert added_node['urgency'] == 'medium'
        assert added_node['tag'] == 'legacy'
    
    def test_central_node_management(self, adapter):
        """Test central node management through adapter."""
        # Initially no central node
        assert adapter.get_central() is None
        
        # Add a node
        old_format_node = {
            'label': 'Central Node',
            'x': 0,
            'y': 0,
            'urgency': 'high',
            'tag': 'central'
        }
        
        success = adapter.add_idea(old_format_node)
        assert success
        
        # Get the node ID
        ideas = adapter.get_ideas()
        node_id = ideas[0]['id']
        
        # Set as central
        success = adapter.set_central(node_id)
        assert success
        
        # Verify it's set as central
        central_id = adapter.get_central()
        assert central_id == node_id
        
        # Clear central node
        success = adapter.set_central(None)
        assert success
        assert adapter.get_central() is None
    
    def test_node_position_update(self, adapter):
        """Test updating node positions through adapter."""
        # Add a node
        old_format_node = {
            'label': 'Movable Node',
            'x': 50,
            'y': 50,
        }
        
        success = adapter.add_idea(old_format_node)
        assert success
        
        # Get the node ID
        ideas = adapter.get_ideas()
        node_id = ideas[0]['id']
        
        # Update position
        success = adapter.update_node_position(node_id, 150, 250)
        assert success
        
        # Verify position was updated
        updated_ideas = adapter.get_ideas()
        updated_node = updated_ideas[0]
        assert updated_node['x'] == 150
        assert updated_node['y'] == 250
    
    def test_node_deletion(self, adapter):
        """Test node deletion through adapter."""
        # Add a parent node
        parent_node = {
            'label': 'Parent Node',
            'x': 0,
            'y': 0,
        }
        
        success = adapter.add_idea(parent_node)
        assert success
        
        # Get parent ID
        ideas = adapter.get_ideas()
        parent_id = ideas[0]['id']
        
        # Add a child node
        child_node = {
            'label': 'Child Node',
            'x': 100,
            'y': 100,
            'parent': parent_id,
        }
        
        success = adapter.add_idea(child_node)
        assert success
        
        # Verify we have 2 nodes
        ideas = adapter.get_ideas()
        assert len(ideas) == 2
        
        # Delete parent (should delete child too)
        success = adapter.delete_node(parent_id)
        assert success
        
        # Verify both nodes are deleted
        ideas = adapter.get_ideas()
        assert len(ideas) == 0
    
    def test_node_search(self, adapter):
        """Test node search functionality."""
        # Add some test nodes
        nodes = [
            {'label': 'JavaScript Tutorial', 'description': 'Learn JS basics'},
            {'label': 'Python Guide', 'description': 'Advanced Python'},
            {'label': 'Web Development', 'description': 'HTML, CSS, JavaScript'},
        ]
        
        for node in nodes:
            success = adapter.add_idea(node)
            assert success
        
        # Search for JavaScript
        results = adapter.search_nodes('JavaScript')
        assert len(results) == 2  # Should find "JavaScript Tutorial" and "Web Development"
        
        # Search for Python
        results = adapter.search_nodes('Python')
        assert len(results) == 1  # Should find "Python Guide"
        
        # Search for non-existent term
        results = adapter.search_nodes('NonExistent')
        assert len(results) == 0
    
    def test_statistics(self, adapter):
        """Test statistics functionality."""
        # Initially empty
        stats = adapter.get_statistics()
        assert stats['total_nodes'] == 0
        
        # Add some nodes with different properties
        nodes = [
            {'label': 'High Priority', 'urgency': 'high', 'tag': 'work'},
            {'label': 'Medium Priority', 'urgency': 'medium', 'tag': 'work'},
            {'label': 'Personal Task', 'urgency': 'low', 'tag': 'personal'},
        ]
        
        for node in nodes:
            success = adapter.add_idea(node)
            assert success
        
        # Check updated statistics
        stats = adapter.get_statistics()
        assert stats['total_nodes'] == 3
        assert stats['urgency_distribution']['high'] == 1
        assert stats['urgency_distribution']['medium'] == 1
        assert stats['urgency_distribution']['low'] == 1
        assert stats['tag_distribution']['work'] == 2
        assert stats['tag_distribution']['personal'] == 1
    
    def test_backup_and_restore(self, adapter):
        """Test backup and restore functionality."""
        # Add a test node
        test_node = {
            'label': 'Backup Test Node',
            'description': 'This should be backed up',
            'urgency': 'high',
        }
        
        success = adapter.add_idea(test_node)
        assert success
        
        # Create backup
        backup_path = adapter.create_backup()
        assert backup_path is not None
        assert Path(backup_path).exists()
        
        # List backups
        backups = adapter.list_backups()
        assert len(backups) >= 1
        
        # Modify data
        modify_node = {
            'label': 'Modified Node',
            'description': 'This is modified data',
        }
        
        success = adapter.add_idea(modify_node)
        assert success
        
        # Verify we have 2 nodes
        ideas = adapter.get_ideas()
        assert len(ideas) == 2
        
        # Restore from backup
        success = adapter.restore_backup(backup_path)
        assert success
        
        # Verify we're back to 1 node
        ideas = adapter.get_ideas()
        assert len(ideas) == 1
        assert ideas[0]['label'] == 'Backup Test Node'
    
    def test_find_node_by_id(self, adapter):
        """Test finding nodes by ID."""
        # Add a test node
        test_node = {
            'label': 'Findable Node',
            'description': 'Can be found by ID',
        }
        
        success = adapter.add_idea(test_node)
        assert success
        
        # Get the node ID
        ideas = adapter.get_ideas()
        node_id = ideas[0]['id']
        
        # Find by ID
        found_node = adapter.find_node_by_id(node_id)
        assert found_node is not None
        assert found_node['label'] == 'Findable Node'
        assert found_node['description'] == 'Can be found by ID'
        
        # Try to find non-existent node
        not_found = adapter.find_node_by_id(999)
        assert not_found is None
    
    def test_format_conversion(self, adapter):
        """Test conversion between old and new formats."""
        # Test old format to create request conversion
        old_format = {
            'label': 'Conversion Test',
            'description': 'Testing format conversion',
            'x': 123.45,
            'y': 678.90,
            'urgency': 'high',
            'tag': 'test',
            'parent': None,
            'edge_type': 'strong'
        }
        
        request = adapter._old_format_to_create_request(old_format)
        assert request.label == 'Conversion Test'
        assert request.description == 'Testing format conversion'
        assert request.position.x == 123.45
        assert request.position.y == 678.90
        assert request.urgency == UrgencyLevel.HIGH
        assert request.tag == 'test'
        assert request.parent_id is None
        assert request.edge_type == EdgeType.STRONG
    
    def test_error_handling(self, adapter):
        """Test error handling in adapter methods."""
        # Test adding invalid node
        invalid_node = {
            'label': '',  # Empty label should cause validation error
        }
        
        success = adapter.add_idea(invalid_node)
        assert not success  # Should fail due to validation
        
        # Test updating non-existent node position
        success = adapter.update_node_position(999, 100, 100)
        assert not success  # Should fail because node doesn't exist
        
        # Test deleting non-existent node
        success = adapter.delete_node(999)
        assert not success  # Should fail because node doesn't exist
        
        # Test setting non-existent central node
        success = adapter.set_central(999)
        assert not success  # Should fail because node doesn't exist


class TestServiceAdapterGlobalFunctions:
    """Test the global service adapter functions."""
    
    def test_get_service_adapter_singleton(self):
        """Test that get_service_adapter returns the same instance."""
        adapter1 = get_service_adapter()
        adapter2 = get_service_adapter()
        
        assert adapter1 is adapter2  # Should be the same instance
    
    @patch('streamlit.session_state', {})
    def test_init_service_adapter(self):
        """Test service adapter initialization."""
        from src.integration.service_adapter import init_service_adapter
        import streamlit as st
        
        adapter = init_service_adapter()
        assert adapter is not None
        assert st.session_state['service_adapter'] is adapter