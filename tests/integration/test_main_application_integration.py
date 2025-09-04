"""
Integration tests for the main application with refactored architecture.

This module tests the complete application flow including lifecycle management,
UI integration, and service layer coordination.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
import streamlit as st

from src.application.app_lifecycle import ApplicationLifecycleManager, get_lifecycle_manager
from src.integration.service_adapter import ServiceAdapter
from src.infrastructure.config import AppConfig


class TestMainApplicationIntegration:
    """Test the main application integration with the new architecture."""
    
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
    def mock_streamlit(self):
        """Mock Streamlit session state and functions."""
        with patch('streamlit.session_state', {}) as mock_state, \
             patch('streamlit.set_page_config') as mock_config, \
             patch('streamlit.success') as mock_success, \
             patch('streamlit.error') as mock_error, \
             patch('streamlit.rerun') as mock_rerun:
            
            yield {
                'session_state': mock_state,
                'set_page_config': mock_config,
                'success': mock_success,
                'error': mock_error,
                'rerun': mock_rerun
            }
    
    @pytest.fixture
    def lifecycle_manager(self, temp_config, mock_streamlit):
        """Create a lifecycle manager for testing."""
        with patch('src.integration.service_adapter.ConfigFactory.create_config', return_value=temp_config), \
             patch('src.integration.service_adapter.RepositoryFactory.create_repository') as mock_repo_factory:
            
            # Use a fresh in-memory repository for each test to ensure isolation
            from src.infrastructure.repositories import InMemoryMindMapRepository
            mock_repo_factory.return_value = InMemoryMindMapRepository()
            
            # Reset global singletons to ensure test isolation
            import src.integration.service_adapter
            import src.application.app_lifecycle
            src.integration.service_adapter._service_adapter = None
            src.application.app_lifecycle._lifecycle_manager = None
            
            manager = ApplicationLifecycleManager()
            yield manager
    
    def test_lifecycle_manager_initialization(self, lifecycle_manager, mock_streamlit):
        """Test that the lifecycle manager initializes correctly."""
        success = lifecycle_manager.initialize()
        
        assert success is True
        assert lifecycle_manager.initialized is True
        assert lifecycle_manager.adapter is not None
        assert lifecycle_manager.performance_monitor is not None
        assert lifecycle_manager.cache_manager is not None
        
        # Verify Streamlit configuration was called
        mock_streamlit['set_page_config'].assert_called_once()
    
    def test_session_state_setup(self, lifecycle_manager, mock_streamlit):
        """Test that session state is properly set up."""
        lifecycle_manager.initialize()
        
        # Check that required session state variables are set
        session_state = mock_streamlit['session_state']
        assert 'app_lifecycle' in session_state
        assert 'adapter' in session_state
        assert 'selected_node' in session_state
        assert 'ui_state' in session_state
        
        # Verify ui_state structure
        ui_state = session_state['ui_state']
        assert 'show_tutorial' in ui_state
        assert 'show_logs' in ui_state
        assert 'canvas_height' in ui_state
    
    def test_legacy_compatibility_update(self, lifecycle_manager, mock_streamlit):
        """Test that legacy compatibility state is properly updated."""
        lifecycle_manager.initialize()
        
        # Add some test data
        adapter = lifecycle_manager.get_adapter()
        node_data = {
            'label': 'Test Node',
            'description': 'Test Description',
            'urgency': 'high',
            'tag': 'test',
            'x': 100.0,
            'y': 200.0
        }
        adapter.add_idea(node_data)
        
        # Update legacy compatibility
        lifecycle_manager.update_legacy_compatibility()
        
        # Check that store is properly updated
        session_state = mock_streamlit['session_state']
        assert 'store' in session_state
        
        store = session_state['store']
        assert 'ideas' in store
        assert 'central' in store
        assert 'next_id' in store
        assert 'settings' in store
        
        # Verify data integrity
        assert len(store['ideas']) == 1
        assert store['ideas'][0]['label'] == 'Test Node'
    
    def test_ui_action_processing_center_node(self, lifecycle_manager, mock_streamlit):
        """Test processing center node UI action."""
        lifecycle_manager.initialize()
        
        # Add a test node
        adapter = lifecycle_manager.get_adapter()
        node_data = {
            'label': 'Center Node',
            'urgency': 'medium',
            'x': 0.0,
            'y': 0.0
        }
        adapter.add_idea(node_data)
        
        ideas = adapter.get_ideas()
        node_id = ideas[0]['id']
        
        # Set up center node action in session state
        session_state = mock_streamlit['session_state']
        session_state['center_node'] = node_id
        
        # Process UI actions
        lifecycle_manager.process_ui_actions()
        
        # Verify the node was centered
        central_id = adapter.get_central()
        assert central_id == node_id
        
        # Verify success message was shown
        mock_streamlit['success'].assert_called()
        mock_streamlit['rerun'].assert_called()
        
        # Verify action was removed from session state
        assert 'center_node' not in session_state
    
    def test_ui_action_processing_delete_node(self, lifecycle_manager, mock_streamlit):
        """Test processing delete node UI action."""
        lifecycle_manager.initialize()
        
        # Add test nodes (parent and child)
        adapter = lifecycle_manager.get_adapter()
        parent_data = {
            'label': 'Parent Node',
            'urgency': 'medium',
            'x': 0.0,
            'y': 0.0
        }
        adapter.add_idea(parent_data)
        
        ideas = adapter.get_ideas()
        parent_id = ideas[0]['id']
        
        child_data = {
            'label': 'Child Node',
            'urgency': 'low',
            'x': 100.0,
            'y': 100.0,
            'parent': parent_id
        }
        adapter.add_idea(child_data)
        
        # Set up delete node action in session state
        session_state = mock_streamlit['session_state']
        session_state['delete_node'] = parent_id
        session_state['selected_node'] = parent_id  # Simulate selected node
        
        # Process UI actions
        lifecycle_manager.process_ui_actions()
        
        # Verify nodes were deleted
        ideas = adapter.get_ideas()
        assert len(ideas) == 0
        
        # Verify selected node was cleared
        assert session_state.get('selected_node') is None
        
        # Verify success message was shown
        mock_streamlit['success'].assert_called()
        mock_streamlit['rerun'].assert_called()
        
        # Verify action was removed from session state
        assert 'delete_node' not in session_state
    
    def test_bulk_import_operation(self, lifecycle_manager, mock_streamlit):
        """Test bulk import operation through UI actions."""
        lifecycle_manager.initialize()
        
        # Prepare import data
        import_data = [
            {
                'id': 1,
                'label': 'Imported Node 1',
                'description': 'First imported node',
                'urgency': 'high',
                'tag': 'import',
                'x': 0.0,
                'y': 0.0,
                'parent': None,
                'edge_type': 'default'
            },
            {
                'id': 2,
                'label': 'Imported Node 2',
                'description': 'Second imported node',
                'urgency': 'medium',
                'tag': 'import',
                'x': 100.0,
                'y': 100.0,
                'parent': 1,
                'edge_type': 'strong'
            }
        ]
        
        # Set up bulk import action in session state
        session_state = mock_streamlit['session_state']
        session_state['bulk_operation'] = {
            'type': 'import',
            'data': import_data
        }
        
        # Process UI actions
        lifecycle_manager.process_ui_actions()
        
        # Verify nodes were imported
        adapter = lifecycle_manager.get_adapter()
        ideas = adapter.get_ideas()
        assert len(ideas) == 2
        
        # Verify success message was shown
        mock_streamlit['success'].assert_called()
        mock_streamlit['rerun'].assert_called()
        
        # Verify action was removed from session state
        assert 'bulk_operation' not in session_state
    
    def test_bulk_export_operation(self, lifecycle_manager, mock_streamlit):
        """Test bulk export operation through UI actions."""
        lifecycle_manager.initialize()
        
        # Add some test data
        adapter = lifecycle_manager.get_adapter()
        nodes_data = [
            {'label': 'Export Node 1', 'urgency': 'high', 'x': 0, 'y': 0},
            {'label': 'Export Node 2', 'urgency': 'medium', 'x': 100, 'y': 100}
        ]
        
        for node_data in nodes_data:
            adapter.add_idea(node_data)
        
        # Set up bulk export action in session state
        session_state = mock_streamlit['session_state']
        session_state['bulk_operation'] = {
            'type': 'export'
        }
        
        # Process UI actions
        lifecycle_manager.process_ui_actions()
        
        # Verify export data was prepared
        assert 'export_data' in session_state
        export_data = session_state['export_data']
        assert len(export_data) == 2
        
        # Verify success message was shown
        mock_streamlit['success'].assert_called()
        
        # Verify action was removed from session state
        assert 'bulk_operation' not in session_state
    
    def test_error_handling(self, lifecycle_manager, mock_streamlit):
        """Test error handling in the lifecycle manager."""
        lifecycle_manager.initialize()
        
        # Create an error scenario by trying to center a non-existent node
        session_state = mock_streamlit['session_state']
        session_state['center_node'] = 99999  # Non-existent node ID
        
        # Process UI actions (should handle error gracefully)
        lifecycle_manager.process_ui_actions()
        
        # Verify error was handled (no exception raised)
        # The specific error handling depends on the service adapter implementation
        assert 'center_node' not in session_state  # Action should be removed
    
    def test_statistics_collection(self, lifecycle_manager, mock_streamlit):
        """Test statistics collection through the lifecycle manager."""
        lifecycle_manager.initialize()
        
        # Add some test data
        adapter = lifecycle_manager.get_adapter()
        nodes_data = [
            {'label': 'High Priority', 'urgency': 'high', 'tag': 'work', 'x': 0, 'y': 0},
            {'label': 'Medium Priority', 'urgency': 'medium', 'tag': 'work', 'x': 100, 'y': 100},
            {'label': 'Low Priority', 'urgency': 'low', 'tag': 'personal', 'x': 200, 'y': 200}
        ]
        
        for node_data in nodes_data:
            adapter.add_idea(node_data)
        
        # Get statistics
        stats = lifecycle_manager.get_statistics()
        
        # Verify basic statistics
        assert 'total_nodes' in stats
        assert stats['total_nodes'] == 3
        
        assert 'urgency_distribution' in stats
        urgency_dist = stats['urgency_distribution']
        assert urgency_dist['high'] == 1
        assert urgency_dist['medium'] == 1
        assert urgency_dist['low'] == 1
        
        assert 'tag_distribution' in stats
        tag_dist = stats['tag_distribution']
        assert tag_dist['work'] == 2
        assert tag_dist['personal'] == 1
        
        # Verify additional statistics are included
        assert 'performance' in stats
        assert 'cache_stats' in stats
    
    def test_cleanup(self, lifecycle_manager, mock_streamlit):
        """Test application cleanup."""
        lifecycle_manager.initialize()
        
        # Perform cleanup
        lifecycle_manager.cleanup()
        
        # Verify cleanup was performed (no exceptions raised)
        # The specific cleanup behavior depends on the implementation
        assert True  # If we get here, cleanup didn't raise an exception


class TestGlobalLifecycleManager:
    """Test the global lifecycle manager functions."""
    
    def test_get_lifecycle_manager_singleton(self):
        """Test that get_lifecycle_manager returns a singleton."""
        manager1 = get_lifecycle_manager()
        manager2 = get_lifecycle_manager()
        
        assert manager1 is manager2
        assert isinstance(manager1, ApplicationLifecycleManager)
    
    @patch('src.application.app_lifecycle.ApplicationLifecycleManager.initialize')
    def test_initialize_application_function(self, mock_initialize):
        """Test the initialize_application function."""
        from src.application.app_lifecycle import initialize_application
        
        mock_initialize.return_value = True
        
        result = initialize_application()
        
        assert result is True
        mock_initialize.assert_called_once()
    
    @patch('src.application.app_lifecycle.ApplicationLifecycleManager.get_adapter')
    def test_get_application_adapter_function(self, mock_get_adapter):
        """Test the get_application_adapter function."""
        from src.application.app_lifecycle import get_application_adapter
        
        mock_adapter = Mock(spec=ServiceAdapter)
        mock_get_adapter.return_value = mock_adapter
        
        result = get_application_adapter()
        
        assert result is mock_adapter
        mock_get_adapter.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])