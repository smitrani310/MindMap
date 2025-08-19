"""
Unit tests for event handlers.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.application.event_handlers import (
    BaseEventHandler, NodeEventHandler, UIEventHandler, SystemEventHandler,
    EventHandlerRegistry, get_handler_registry, setup_default_handlers
)
from src.infrastructure.event_system import Event, EventType, EventBus, get_event_bus
from src.infrastructure.domain_events import NodeCreatedEvent, SystemErrorEvent


class TestBaseEventHandler:
    """Test cases for BaseEventHandler."""
    
    def test_base_handler_abstract_methods(self):
        """Test that BaseEventHandler is abstract."""
        with pytest.raises(TypeError):
            BaseEventHandler("test")
    
    def test_handler_wrapper_functionality(self):
        """Test the event handling wrapper functionality."""
        
        class TestHandler(BaseEventHandler):
            def __init__(self):
                super().__init__("TestHandler")
                self.handled_events = []
            
            def get_handled_event_types(self):
                return {EventType.NODE_CREATED}
            
            def handle_event(self, event):
                self.handled_events.append(event)
        
        handler = TestHandler()
        event = Event(event_type=EventType.NODE_CREATED, data={'node_id': 1})
        
        handler._handle_event_wrapper(event)
        
        assert len(handler.handled_events) == 1
        assert handler.handled_events_count == 1
        assert handler.last_handled_at is not None
        assert handler.error_count == 0
    
    def test_handler_error_handling(self):
        """Test error handling in event wrapper."""
        
        class FailingHandler(BaseEventHandler):
            def get_handled_event_types(self):
                return {EventType.NODE_CREATED}
            
            def handle_event(self, event):
                raise ValueError("Handler failed")
        
        handler = FailingHandler("FailingHandler")
        event = Event(event_type=EventType.NODE_CREATED)
        
        with pytest.raises(ValueError):
            handler._handle_event_wrapper(event)
        
        assert handler.error_count == 1
        assert handler.handled_events_count == 0


class TestNodeEventHandler:
    """Test cases for NodeEventHandler."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.handler = NodeEventHandler()
    
    def test_handled_event_types(self):
        """Test that handler returns correct event types."""
        event_types = self.handler.get_handled_event_types()
        
        expected_types = {
            EventType.NODE_CREATED,
            EventType.NODE_UPDATED,
            EventType.NODE_DELETED,
            EventType.NODE_MOVED,
            EventType.NODE_PARENT_CHANGED
        }
        
        assert event_types == expected_types
    
    def test_event_priorities(self):
        """Test event priority mapping."""
        assert self.handler.get_priority_for_event_type(EventType.NODE_CREATED) == 10
        assert self.handler.get_priority_for_event_type(EventType.NODE_DELETED) == 10
        assert self.handler.get_priority_for_event_type(EventType.NODE_UPDATED) == 5
        assert self.handler.get_priority_for_event_type(EventType.NODE_MOVED) == 3
    
    def test_handle_node_created(self):
        """Test handling node created events."""
        event = Event(
            event_type=EventType.NODE_CREATED,
            data={
                'node_id': 1,
                'node_data': {
                    'title': 'Test Node',
                    'content': 'Test content',
                    'parent_id': None,
                    'position': {'x': 100, 'y': 200}
                }
            }
        )
        
        self.handler.handle_event(event)
        
        # Verify node was added to cache
        assert 1 in self.handler.node_cache
        node = self.handler.node_cache[1]
        assert node['title'] == 'Test Node'
        assert node['content'] == 'Test content'
        assert node['position'] == {'x': 100, 'y': 200}
        assert self.handler.node_creation_count == 1
    
    def test_handle_node_created_with_parent(self):
        """Test handling node creation with parent relationship."""
        # Create parent node first
        parent_event = Event(
            event_type=EventType.NODE_CREATED,
            data={
                'node_id': 1,
                'node_data': {'title': 'Parent Node'}
            }
        )
        self.handler.handle_event(parent_event)
        
        # Create child node
        child_event = Event(
            event_type=EventType.NODE_CREATED,
            data={
                'node_id': 2,
                'node_data': {
                    'title': 'Child Node',
                    'parent_id': 1
                }
            }
        )
        self.handler.handle_event(child_event)
        
        # Verify relationship was established
        assert 1 in self.handler.node_relationships
        assert 2 in self.handler.node_relationships[1]
        assert self.handler.node_cache[2]['parent_id'] == 1
    
    def test_handle_node_updated(self):
        """Test handling node updated events."""
        # First create a node
        create_event = Event(
            event_type=EventType.NODE_CREATED,
            data={
                'node_id': 1,
                'node_data': {
                    'title': 'Original Title',
                    'content': 'Original content'
                }
            }
        )
        self.handler.handle_event(create_event)
        
        # Then update it
        update_event = Event(
            event_type=EventType.NODE_UPDATED,
            data={
                'node_id': 1,
                'node_data': {
                    'changes': {'title': 'Updated Title'},
                    'old_values': {'title': 'Original Title'}
                }
            }
        )
        self.handler.handle_event(update_event)
        
        # Verify node was updated
        assert self.handler.node_cache[1]['title'] == 'Updated Title'
        assert self.handler.node_update_count == 1
    
    def test_handle_node_deleted(self):
        """Test handling node deleted events."""
        # First create a node
        create_event = Event(
            event_type=EventType.NODE_CREATED,
            data={
                'node_id': 1,
                'node_data': {'title': 'Test Node'}
            }
        )
        self.handler.handle_event(create_event)
        
        # Then delete it
        delete_event = Event(
            event_type=EventType.NODE_DELETED,
            data={
                'node_id': 1,
                'node_data': {
                    'deleted_node_data': {'title': 'Test Node'},
                    'cascade_deleted': []
                }
            }
        )
        self.handler.handle_event(delete_event)
        
        # Verify node was removed
        assert 1 not in self.handler.node_cache
        assert self.handler.node_deletion_count == 1
    
    def test_handle_node_moved(self):
        """Test handling node moved events."""
        # Create a node first
        create_event = Event(
            event_type=EventType.NODE_CREATED,
            data={
                'node_id': 1,
                'node_data': {
                    'title': 'Test Node',
                    'position': {'x': 0, 'y': 0}
                }
            }
        )
        self.handler.handle_event(create_event)
        
        # Move the node
        move_event = Event(
            event_type=EventType.NODE_MOVED,
            data={
                'node_id': 1,
                'node_data': {
                    'old_position': {'x': 0, 'y': 0},
                    'new_position': {'x': 100, 'y': 150}
                }
            }
        )
        self.handler.handle_event(move_event)
        
        # Verify position was updated
        assert self.handler.node_cache[1]['position'] == {'x': 100, 'y': 150}
    
    def test_handle_parent_change(self):
        """Test handling parent relationship changes."""
        # Create nodes
        for i in range(1, 4):
            event = Event(
                event_type=EventType.NODE_CREATED,
                data={
                    'node_id': i,
                    'node_data': {'title': f'Node {i}'}
                }
            )
            self.handler.handle_event(event)
        
        # Set initial parent relationship (2 -> 1)
        self.handler._handle_parent_change(2, None, 1)
        assert 2 in self.handler.node_relationships[1]
        
        # Change parent relationship (2 -> 3)
        self.handler._handle_parent_change(2, 1, 3)
        assert 2 not in self.handler.node_relationships[1]
        assert 2 in self.handler.node_relationships[3]
    
    def test_get_node_stats(self):
        """Test getting node statistics."""
        # Create some nodes
        for i in range(1, 4):
            event = Event(
                event_type=EventType.NODE_CREATED,
                data={
                    'node_id': i,
                    'node_data': {
                        'title': f'Node {i}',
                        'parent_id': 1 if i > 1 else None
                    }
                }
            )
            self.handler.handle_event(event)
        
        stats = self.handler.get_node_stats()
        
        assert stats['total_nodes'] == 3
        assert stats['nodes_created'] == 3
        assert stats['nodes_updated'] == 0
        assert stats['nodes_deleted'] == 0
        assert stats['orphan_nodes'] == 1  # Node 1 has no parent


class TestUIEventHandler:
    """Test cases for UIEventHandler."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.handler = UIEventHandler()
    
    def test_handled_event_types(self):
        """Test that handler returns correct event types."""
        event_types = self.handler.get_handled_event_types()
        
        expected_types = {
            EventType.UI_NODE_SELECTED,
            EventType.UI_NODE_DESELECTED,
            EventType.UI_ZOOM_CHANGED,
            EventType.UI_VIEW_CHANGED,
            EventType.UI_FILTER_APPLIED
        }
        
        assert event_types == expected_types
    
    def test_handle_node_selected_single(self):
        """Test handling single node selection."""
        event = Event(
            event_type=EventType.UI_NODE_SELECTED,
            data={
                'component': 'node_selector',
                'action': 'selection_changed',
                'ui_data': {
                    'node_id': 1,
                    'selected': True,
                    'selection_mode': 'single'
                }
            }
        )
        
        self.handler.handle_event(event)
        
        # Verify node was selected
        assert 1 in self.handler.selected_nodes
        assert len(self.handler.selected_nodes) == 1
        assert self.handler.ui_interaction_count == 1
        assert len(self.handler.selection_history) == 1
    
    def test_handle_node_selected_multi(self):
        """Test handling multi-node selection."""
        # Select first node
        event1 = Event(
            event_type=EventType.UI_NODE_SELECTED,
            data={
                'ui_data': {
                    'node_id': 1,
                    'selected': True,
                    'selection_mode': 'multi'
                }
            }
        )
        self.handler.handle_event(event1)
        
        # Select second node
        event2 = Event(
            event_type=EventType.UI_NODE_SELECTED,
            data={
                'ui_data': {
                    'node_id': 2,
                    'selected': True,
                    'selection_mode': 'multi'
                }
            }
        )
        self.handler.handle_event(event2)
        
        # Verify both nodes are selected
        assert 1 in self.handler.selected_nodes
        assert 2 in self.handler.selected_nodes
        assert len(self.handler.selected_nodes) == 2
    
    def test_handle_node_deselected(self):
        """Test handling node deselection."""
        # First select a node
        select_event = Event(
            event_type=EventType.UI_NODE_SELECTED,
            data={
                'ui_data': {
                    'node_id': 1,
                    'selected': True,
                    'selection_mode': 'single'
                }
            }
        )
        self.handler.handle_event(select_event)
        
        # Then deselect it
        deselect_event = Event(
            event_type=EventType.UI_NODE_DESELECTED,
            data={
                'ui_data': {
                    'node_id': 1,
                    'selected': False
                }
            }
        )
        self.handler.handle_event(deselect_event)
        
        # Verify node was deselected
        assert 1 not in self.handler.selected_nodes
        assert len(self.handler.selected_nodes) == 0
    
    def test_handle_zoom_changed(self):
        """Test handling zoom change events."""
        event = Event(
            event_type=EventType.UI_ZOOM_CHANGED,
            data={
                'ui_data': {
                    'zoom_level': 1.5
                }
            }
        )
        
        self.handler.handle_event(event)
        
        # Verify zoom level was updated
        assert self.handler.current_zoom_level == 1.5
        assert self.handler.ui_interaction_count == 1
    
    def test_handle_view_changed(self):
        """Test handling view change events."""
        event = Event(
            event_type=EventType.UI_VIEW_CHANGED,
            data={
                'ui_data': {
                    'center_position': {'x': 100, 'y': 200},
                    'zoom_level': 2.0
                }
            }
        )
        
        self.handler.handle_event(event)
        
        # Verify view was updated
        assert self.handler.current_center_position == {'x': 100, 'y': 200}
        assert self.handler.current_zoom_level == 2.0
    
    def test_handle_filter_applied(self):
        """Test handling filter application."""
        event = Event(
            event_type=EventType.UI_FILTER_APPLIED,
            data={
                'ui_data': {
                    'filter_type': 'urgency',
                    'filter_value': 'high',
                    'active': True
                }
            }
        )
        
        self.handler.handle_event(event)
        
        # Verify filter was applied
        assert 'urgency' in self.handler.active_filters
        assert self.handler.active_filters['urgency'] == 'high'
    
    def test_get_ui_stats(self):
        """Test getting UI statistics."""
        # Select some nodes
        for i in range(1, 3):
            event = Event(
                event_type=EventType.UI_NODE_SELECTED,
                data={
                    'ui_data': {
                        'node_id': i,
                        'selected': True,
                        'selection_mode': 'multi'
                    }
                }
            )
            self.handler.handle_event(event)
        
        stats = self.handler.get_ui_stats()
        
        assert stats['selected_nodes_count'] == 2
        assert set(stats['selected_nodes']) == {1, 2}
        assert stats['ui_interactions'] == 2


class TestSystemEventHandler:
    """Test cases for SystemEventHandler."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.handler = SystemEventHandler()
    
    def test_handled_event_types(self):
        """Test that handler returns correct event types."""
        event_types = self.handler.get_handled_event_types()
        
        expected_types = {
            EventType.SYSTEM_STARTUP,
            EventType.SYSTEM_SHUTDOWN,
            EventType.SYSTEM_ERROR,
            EventType.SYSTEM_WARNING,
            EventType.PERFORMANCE_SLOW_OPERATION,
            EventType.PERFORMANCE_THRESHOLD_EXCEEDED,
            EventType.DATA_LOADED,
            EventType.DATA_SAVED,
            EventType.CACHE_HIT,
            EventType.CACHE_MISS,
            EventType.CACHE_INVALIDATED
        }
        
        assert event_types == expected_types
    
    def test_handle_system_startup(self):
        """Test handling system startup events."""
        event = Event(
            event_type=EventType.SYSTEM_STARTUP,
            data={
                'system_component': 'main',
                'message': 'System starting up',
                'system_data': {
                    'version': '1.0.0'
                }
            }
        )
        
        self.handler.handle_event(event)
        
        # Verify system status was updated
        assert self.handler.system_status == 'running'
        assert self.handler.system_start_time is not None
    
    def test_handle_system_shutdown(self):
        """Test handling system shutdown events."""
        # First start the system
        startup_event = Event(
            event_type=EventType.SYSTEM_STARTUP,
            data={'system_component': 'main', 'message': 'Starting'}
        )
        self.handler.handle_event(startup_event)
        
        # Then shut it down
        shutdown_event = Event(
            event_type=EventType.SYSTEM_SHUTDOWN,
            data={
                'system_component': 'main',
                'message': 'System shutting down',
                'system_data': {
                    'reason': 'user_request'
                }
            }
        )
        self.handler.handle_event(shutdown_event)
        
        # Verify system status was updated
        assert self.handler.system_status == 'stopped'
    
    def test_handle_system_error(self):
        """Test handling system error events."""
        event = Event(
            event_type=EventType.SYSTEM_ERROR,
            data={
                'system_component': 'database',
                'message': 'Connection failed',
                'system_data': {
                    'error_code': 'DB_CONNECTION_ERROR'
                }
            }
        )
        
        self.handler.handle_event(event)
        
        # Verify error was tracked
        assert self.handler.error_count_by_component['database'] == 1
        assert self.handler.last_error_time is not None
    
    def test_handle_system_warning(self):
        """Test handling system warning events."""
        event = Event(
            event_type=EventType.SYSTEM_WARNING,
            data={
                'system_component': 'cache',
                'message': 'Cache nearly full'
            }
        )
        
        self.handler.handle_event(event)
        
        # Verify warning was tracked
        assert self.handler.warning_count_by_component['cache'] == 1
    
    def test_handle_slow_operation(self):
        """Test handling slow operation events."""
        event = Event(
            event_type=EventType.PERFORMANCE_SLOW_OPERATION,
            data={
                'operation_name': 'database_query',
                'duration_ms': 2500.0,
                'threshold_ms': 1000.0,
                'performance_data': {
                    'component': 'database'
                }
            }
        )
        
        self.handler.handle_event(event)
        
        # Verify performance issue was recorded
        assert len(self.handler.performance_issues) == 1
        issue = self.handler.performance_issues[0]
        assert issue['operation_name'] == 'database_query'
        assert issue['duration_ms'] == 2500.0
    
    def test_handle_data_events(self):
        """Test handling data load/save events."""
        load_event = Event(
            event_type=EventType.DATA_LOADED,
            data={
                'data_source': 'mindmap.json',
                'operation': 'load',
                'data_info': {
                    'record_count': 150,
                    'load_duration_ms': 250.0
                }
            }
        )
        
        save_event = Event(
            event_type=EventType.DATA_SAVED,
            data={
                'data_source': 'mindmap.json',
                'operation': 'save',
                'data_info': {
                    'record_count': 155,
                    'save_duration_ms': 180.0,
                    'backup_created': True
                }
            }
        )
        
        self.handler.handle_event(load_event)
        self.handler.handle_event(save_event)
        
        # Events should be handled without errors
        # (Specific assertions would depend on implementation details)
    
    def test_get_system_stats(self):
        """Test getting system statistics."""
        # Generate some events
        startup_event = Event(
            event_type=EventType.SYSTEM_STARTUP,
            data={'system_component': 'main', 'message': 'Starting'}
        )
        self.handler.handle_event(startup_event)
        
        error_event = Event(
            event_type=EventType.SYSTEM_ERROR,
            data={
                'system_component': 'database',
                'message': 'Error occurred'
            }
        )
        self.handler.handle_event(error_event)
        
        stats = self.handler.get_system_stats()
        
        assert stats['system_status'] == 'running'
        assert stats['total_errors'] == 1
        assert stats['errors_by_component']['database'] == 1
        assert stats['uptime_seconds'] is not None


class TestEventHandlerRegistry:
    """Test cases for EventHandlerRegistry."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.registry = EventHandlerRegistry()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        self.registry.shutdown_all_handlers()
    
    def test_register_handler(self):
        """Test registering an event handler."""
        handler = NodeEventHandler()
        
        self.registry.register_handler(handler)
        
        assert handler.name in self.registry.handlers
        assert len(handler.subscription_ids) > 0
    
    def test_unregister_handler(self):
        """Test unregistering an event handler."""
        handler = NodeEventHandler()
        self.registry.register_handler(handler)
        
        result = self.registry.unregister_handler(handler.name)
        
        assert result is True
        assert handler.name not in self.registry.handlers
        assert len(handler.subscription_ids) == 0
    
    def test_get_handler(self):
        """Test getting a registered handler."""
        handler = NodeEventHandler()
        self.registry.register_handler(handler)
        
        retrieved_handler = self.registry.get_handler(handler.name)
        
        assert retrieved_handler is handler
    
    def test_get_all_handlers(self):
        """Test getting all registered handlers."""
        handler1 = NodeEventHandler()
        handler2 = UIEventHandler()
        
        self.registry.register_handler(handler1)
        self.registry.register_handler(handler2)
        
        all_handlers = self.registry.get_all_handlers()
        
        assert len(all_handlers) == 2
        assert handler1.name in all_handlers
        assert handler2.name in all_handlers
    
    def test_get_registry_stats(self):
        """Test getting registry statistics."""
        handler = NodeEventHandler()
        self.registry.register_handler(handler)
        
        stats = self.registry.get_registry_stats()
        
        assert stats['total_handlers'] == 1
        assert handler.name in stats['handler_names']
        assert handler.name in stats['handler_stats']
    
    def test_shutdown_all_handlers(self):
        """Test shutting down all handlers."""
        handler1 = NodeEventHandler()
        handler2 = UIEventHandler()
        
        self.registry.register_handler(handler1)
        self.registry.register_handler(handler2)
        
        self.registry.shutdown_all_handlers()
        
        assert len(self.registry.handlers) == 0


class TestGlobalFunctions:
    """Test cases for global functions."""
    
    def test_get_handler_registry_singleton(self):
        """Test that get_handler_registry returns singleton."""
        registry1 = get_handler_registry()
        registry2 = get_handler_registry()
        
        assert registry1 is registry2
    
    @patch('src.application.event_handlers.get_handler_registry')
    def test_setup_default_handlers(self, mock_get_registry):
        """Test setting up default handlers."""
        mock_registry = Mock()
        mock_get_registry.return_value = mock_registry
        
        setup_default_handlers()
        
        # Should register 3 default handlers
        assert mock_registry.register_handler.call_count == 3
        
        # Check that the right handler types were registered
        registered_handlers = [
            call[0][0] for call in mock_registry.register_handler.call_args_list
        ]
        
        handler_types = [type(handler).__name__ for handler in registered_handlers]
        assert 'NodeEventHandler' in handler_types
        assert 'UIEventHandler' in handler_types
        assert 'SystemEventHandler' in handler_types


if __name__ == "__main__":
    pytest.main([__file__])