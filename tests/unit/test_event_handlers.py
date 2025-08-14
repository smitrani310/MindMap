"""
Unit tests for event handlers.
"""

import pytest
from unittest.mock import Mock, patch

from src.application.event_handlers import (
    NodeEventHandler, UIEventHandler, SystemEventHandler, CacheEventHandler,
    setup_default_event_handlers, get_ui_event_handler, get_cache_event_handler
)
from src.infrastructure.events import Event, EventType, get_event_bus


class TestNodeEventHandler:
    """Test cases for NodeEventHandler."""
    
    @pytest.fixture
    def handler(self):
        """Create node event handler for testing."""
        return NodeEventHandler()
    
    def test_handler_name(self, handler):
        """Test handler name."""
        assert handler.name == "NodeEventHandler"
    
    def test_can_handle(self, handler):
        """Test can_handle method."""
        # Should handle node events
        assert handler.can_handle(Event(type=EventType.NODE_CREATED, source="test"))
        assert handler.can_handle(Event(type=EventType.NODE_UPDATED, source="test"))
        assert handler.can_handle(Event(type=EventType.NODE_DELETED, source="test"))
        assert handler.can_handle(Event(type=EventType.NODE_MOVED, source="test"))
        
        # Should not handle other events
        assert not handler.can_handle(Event(type=EventType.SYSTEM_INFO, source="test"))
        assert not handler.can_handle(Event(type=EventType.UI_ZOOM_CHANGED, source="test"))
    
    @patch('src.application.event_handlers.invalidate_search_cache')
    @patch('src.application.event_handlers.get_event_bus')
    def test_handle_node_created(self, mock_get_bus, mock_invalidate_search, handler):
        """Test handling node created event."""
        mock_bus = Mock()
        mock_get_bus.return_value = mock_bus
        
        event = Event(
            type=EventType.NODE_CREATED,
            source="test",
            data={'node_id': 123, 'label': 'Test Node'}
        )
        
        handler.handle(event)
        
        # Check that search cache was invalidated
        mock_invalidate_search.assert_called_once()
        
        # Check that cache invalidation event was published
        mock_bus.publish.assert_called_once()
        published_event = mock_bus.publish.call_args[0][0]
        assert published_event.type == EventType.CACHE_INVALIDATED
        assert published_event.data['cache_type'] == 'search'
        assert published_event.data['reason'] == 'node_created'
        assert published_event.data['node_id'] == 123
    
    @patch('src.application.event_handlers.invalidate_node_cache')
    @patch('src.application.event_handlers.invalidate_search_cache')
    @patch('src.application.event_handlers.get_event_bus')
    def test_handle_node_updated(self, mock_get_bus, mock_invalidate_search, mock_invalidate_node, handler):
        """Test handling node updated event."""
        mock_bus = Mock()
        mock_get_bus.return_value = mock_bus
        
        event = Event(
            type=EventType.NODE_UPDATED,
            source="test",
            data={'node_id': 456, 'updated_fields': ['label', 'position']}
        )
        
        handler.handle(event)
        
        # Check that caches were invalidated
        mock_invalidate_node.assert_called_once_with(456)
        mock_invalidate_search.assert_called_once()
        
        # Check that cache invalidation event was published
        mock_bus.publish.assert_called_once()
        published_event = mock_bus.publish.call_args[0][0]
        assert published_event.type == EventType.CACHE_INVALIDATED
        assert published_event.data['cache_type'] == 'node'
        assert published_event.data['reason'] == 'node_updated'
    
    @patch('src.application.event_handlers.invalidate_node_cache')
    @patch('src.application.event_handlers.invalidate_search_cache')
    @patch('src.application.event_handlers.get_event_bus')
    def test_handle_node_deleted(self, mock_get_bus, mock_invalidate_search, mock_invalidate_node, handler):
        """Test handling node deleted event."""
        mock_bus = Mock()
        mock_get_bus.return_value = mock_bus
        
        event = Event(
            type=EventType.NODE_DELETED,
            source="test",
            data={'node_id': 789, 'deleted_count': 3}
        )
        
        handler.handle(event)
        
        # Check that caches were invalidated
        mock_invalidate_node.assert_called_once_with(789)
        mock_invalidate_search.assert_called_once()
        
        # Check that cache invalidation event was published
        mock_bus.publish.assert_called_once()
        published_event = mock_bus.publish.call_args[0][0]
        assert published_event.type == EventType.CACHE_INVALIDATED
        assert published_event.data['cache_type'] == 'all'
        assert published_event.data['reason'] == 'node_deleted'
    
    def test_handle_missing_node_id(self, handler):
        """Test handling event with missing node_id."""
        event = Event(
            type=EventType.NODE_CREATED,
            source="test",
            data={}  # Missing node_id
        )
        
        # Should not raise exception, just log warning
        handler.handle(event)


class TestUIEventHandler:
    """Test cases for UIEventHandler."""
    
    @pytest.fixture
    def handler(self):
        """Create UI event handler for testing."""
        return UIEventHandler()
    
    def test_handler_name(self, handler):
        """Test handler name."""
        assert handler.name == "UIEventHandler"
    
    def test_can_handle(self, handler):
        """Test can_handle method."""
        # Should handle UI events
        assert handler.can_handle(Event(type=EventType.UI_NODE_SELECTED, source="test"))
        assert handler.can_handle(Event(type=EventType.UI_NODE_DESELECTED, source="test"))
        assert handler.can_handle(Event(type=EventType.UI_ZOOM_CHANGED, source="test"))
        assert handler.can_handle(Event(type=EventType.UI_PAN_CHANGED, source="test"))
        
        # Should not handle other events
        assert not handler.can_handle(Event(type=EventType.NODE_CREATED, source="test"))
        assert not handler.can_handle(Event(type=EventType.SYSTEM_INFO, source="test"))
    
    def test_node_selection(self, handler):
        """Test node selection and deselection."""
        # Initially no nodes selected
        assert len(handler.get_selected_nodes()) == 0
        
        # Select a node
        select_event = Event(
            type=EventType.UI_NODE_SELECTED,
            source="ui",
            data={'node_id': 123}
        )
        handler.handle(select_event)
        
        selected = handler.get_selected_nodes()
        assert len(selected) == 1
        assert 123 in selected
        
        # Select another node
        select_event2 = Event(
            type=EventType.UI_NODE_SELECTED,
            source="ui",
            data={'node_id': 456}
        )
        handler.handle(select_event2)
        
        selected = handler.get_selected_nodes()
        assert len(selected) == 2
        assert 123 in selected
        assert 456 in selected
        
        # Deselect a node
        deselect_event = Event(
            type=EventType.UI_NODE_DESELECTED,
            source="ui",
            data={'node_id': 123}
        )
        handler.handle(deselect_event)
        
        selected = handler.get_selected_nodes()
        assert len(selected) == 1
        assert 123 not in selected
        assert 456 in selected
    
    @patch('src.application.event_handlers.get_cache_manager')
    def test_zoom_changed_invalidates_cache(self, mock_get_cache_manager, handler):
        """Test that zoom change invalidates render cache."""
        mock_cache_manager = Mock()
        mock_get_cache_manager.return_value = mock_cache_manager
        
        zoom_event = Event(
            type=EventType.UI_ZOOM_CHANGED,
            source="ui",
            data={'zoom_level': 1.5}
        )
        
        handler.handle(zoom_event)
        
        # Check that render cache was invalidated
        mock_cache_manager.invalidate_cache.assert_called_once_with('render')
    
    @patch('src.application.event_handlers.get_cache_manager')
    def test_pan_changed_invalidates_cache(self, mock_get_cache_manager, handler):
        """Test that pan change invalidates render cache."""
        mock_cache_manager = Mock()
        mock_get_cache_manager.return_value = mock_cache_manager
        
        pan_event = Event(
            type=EventType.UI_PAN_CHANGED,
            source="ui",
            data={'pan_x': 100, 'pan_y': 200}
        )
        
        handler.handle(pan_event)
        
        # Check that render cache was invalidated
        mock_cache_manager.invalidate_cache.assert_called_once_with('render')


class TestSystemEventHandler:
    """Test cases for SystemEventHandler."""
    
    @pytest.fixture
    def handler(self):
        """Create system event handler for testing."""
        return SystemEventHandler()
    
    def test_handler_name(self, handler):
        """Test handler name."""
        assert handler.name == "SystemEventHandler"
    
    def test_can_handle(self, handler):
        """Test can_handle method."""
        # Should handle system events
        assert handler.can_handle(Event(type=EventType.SYSTEM_ERROR, source="test"))
        assert handler.can_handle(Event(type=EventType.SYSTEM_WARNING, source="test"))
        assert handler.can_handle(Event(type=EventType.SYSTEM_INFO, source="test"))
        assert handler.can_handle(Event(type=EventType.MINDMAP_LOADED, source="test"))
        assert handler.can_handle(Event(type=EventType.MINDMAP_SAVED, source="test"))
        assert handler.can_handle(Event(type=EventType.MINDMAP_CLEARED, source="test"))
        
        # Should not handle other events
        assert not handler.can_handle(Event(type=EventType.NODE_CREATED, source="test"))
        assert not handler.can_handle(Event(type=EventType.UI_ZOOM_CHANGED, source="test"))
    
    def test_handle_system_error(self, handler):
        """Test handling system error event."""
        # Mock the performance monitor directly on the handler
        mock_monitor = Mock()
        handler.performance_monitor = mock_monitor
        
        error_event = Event(
            type=EventType.SYSTEM_ERROR,
            source="test_service",
            data={
                'message': 'Test error message',
                'error_type': 'ValidationError'
            }
        )
        
        handler.handle(error_event)
        
        # Check that error was recorded in performance monitor
        mock_monitor.record_metric.assert_called_once_with(
            operation="system_error.ValidationError",
            duration_ms=0,
            success=False,
            error='Test error message'
        )
    
    @patch('src.application.event_handlers.get_cache_manager')
    def test_handle_mindmap_loaded(self, mock_get_cache_manager, handler):
        """Test handling mindmap loaded event."""
        mock_cache_manager = Mock()
        mock_get_cache_manager.return_value = mock_cache_manager
        
        loaded_event = Event(
            type=EventType.MINDMAP_LOADED,
            source="repository",
            data={
                'node_count': 50,
                'file_path': '/path/to/file.json'
            }
        )
        
        handler.handle(loaded_event)
        
        # Check that all caches were invalidated
        expected_calls = [
            ('nodes',),
            ('render',),
            ('computation',),
            ('search',)
        ]
        
        actual_calls = [call[0] for call in mock_cache_manager.invalidate_cache.call_args_list]
        for expected_call in expected_calls:
            assert expected_call in actual_calls
    
    @patch('src.application.event_handlers.get_cache_manager')
    def test_handle_mindmap_cleared(self, mock_get_cache_manager, handler):
        """Test handling mindmap cleared event."""
        mock_cache_manager = Mock()
        mock_get_cache_manager.return_value = mock_cache_manager
        
        cleared_event = Event(
            type=EventType.MINDMAP_CLEARED,
            source="service"
        )
        
        handler.handle(cleared_event)
        
        # Check that all caches were invalidated
        expected_calls = [
            ('nodes',),
            ('render',),
            ('computation',),
            ('search',)
        ]
        
        actual_calls = [call[0] for call in mock_cache_manager.invalidate_cache.call_args_list]
        for expected_call in expected_calls:
            assert expected_call in actual_calls


class TestCacheEventHandler:
    """Test cases for CacheEventHandler."""
    
    @pytest.fixture
    def handler(self):
        """Create cache event handler for testing."""
        return CacheEventHandler()
    
    def test_handler_name(self, handler):
        """Test handler name."""
        assert handler.name == "CacheEventHandler"
    
    def test_can_handle(self, handler):
        """Test can_handle method."""
        # Should handle cache events
        assert handler.can_handle(Event(type=EventType.CACHE_HIT, source="test"))
        assert handler.can_handle(Event(type=EventType.CACHE_MISS, source="test"))
        assert handler.can_handle(Event(type=EventType.CACHE_INVALIDATED, source="test"))
        
        # Should not handle other events
        assert not handler.can_handle(Event(type=EventType.NODE_CREATED, source="test"))
        assert not handler.can_handle(Event(type=EventType.SYSTEM_INFO, source="test"))
    
    def test_cache_event_tracking(self, handler):
        """Test tracking cache events."""
        # Initially no stats
        stats = handler.get_cache_stats()
        assert stats['hits'] == 0
        assert stats['misses'] == 0
        assert stats['invalidations'] == 0
        
        # Handle cache hit
        hit_event = Event(
            type=EventType.CACHE_HIT,
            source="cache",
            data={'cache_type': 'nodes', 'cache_key': 'node_123'}
        )
        handler.handle(hit_event)
        
        stats = handler.get_cache_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 0
        assert stats['invalidations'] == 0
        
        # Handle cache miss
        miss_event = Event(
            type=EventType.CACHE_MISS,
            source="cache",
            data={'cache_type': 'render', 'cache_key': 'render_456'}
        )
        handler.handle(miss_event)
        
        stats = handler.get_cache_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['invalidations'] == 0
        
        # Handle cache invalidation
        invalidation_event = Event(
            type=EventType.CACHE_INVALIDATED,
            source="service",
            data={'cache_type': 'all', 'reason': 'data_changed'}
        )
        handler.handle(invalidation_event)
        
        stats = handler.get_cache_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['invalidations'] == 1


class TestEventHandlerSetup:
    """Test cases for event handler setup functions."""
    
    @patch('src.application.event_handlers.get_event_bus')
    def test_setup_default_event_handlers(self, mock_get_bus):
        """Test setting up default event handlers."""
        mock_bus = Mock()
        mock_get_bus.return_value = mock_bus
        
        setup_default_event_handlers()
        
        # Check that handlers were added to the bus
        assert mock_bus.add_handler.call_count == 4
        
        # Check the types of handlers that were added
        handler_types = [type(call[0][0]).__name__ for call in mock_bus.add_handler.call_args_list]
        assert 'NodeEventHandler' in handler_types
        assert 'UIEventHandler' in handler_types
        assert 'SystemEventHandler' in handler_types
        assert 'CacheEventHandler' in handler_types
    
    def test_get_ui_event_handler(self):
        """Test getting UI event handler."""
        # Create a mock event bus with handlers
        mock_bus = Mock()
        ui_handler = UIEventHandler()
        other_handler = NodeEventHandler()
        mock_bus.handlers = [other_handler, ui_handler]
        
        with patch('src.application.event_handlers.get_event_bus', return_value=mock_bus):
            result = get_ui_event_handler()
            assert result is ui_handler
    
    def test_get_ui_event_handler_not_found(self):
        """Test getting UI event handler when not found."""
        mock_bus = Mock()
        mock_bus.handlers = [NodeEventHandler()]  # No UI handler
        
        with patch('src.application.event_handlers.get_event_bus', return_value=mock_bus):
            result = get_ui_event_handler()
            assert result is None
    
    def test_get_cache_event_handler(self):
        """Test getting cache event handler."""
        mock_bus = Mock()
        cache_handler = CacheEventHandler()
        other_handler = SystemEventHandler()
        mock_bus.handlers = [other_handler, cache_handler]
        
        with patch('src.application.event_handlers.get_event_bus', return_value=mock_bus):
            result = get_cache_event_handler()
            assert result is cache_handler
    
    def test_get_cache_event_handler_not_found(self):
        """Test getting cache event handler when not found."""
        mock_bus = Mock()
        mock_bus.handlers = [NodeEventHandler()]  # No cache handler
        
        with patch('src.application.event_handlers.get_event_bus', return_value=mock_bus):
            result = get_cache_event_handler()
            assert result is None


if __name__ == "__main__":
    pytest.main([__file__])