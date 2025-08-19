"""
Integration tests for event handlers working with the event system.
"""

import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock

from src.infrastructure.event_system import (
    Event, EventType, EventBus, get_event_bus, publish_event
)
from src.infrastructure.domain_events import (
    NodeCreatedEvent, NodeUpdatedEvent, SystemErrorEvent,
    create_node_created_event, create_system_error_event
)
from src.application.event_handlers import (
    NodeEventHandler, UIEventHandler, SystemEventHandler,
    EventHandlerRegistry, setup_default_handlers
)


def test_complete_event_handler_integration():
    """Test complete integration of event handlers with event system."""
    
    # Set up event bus and handlers
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.jsonl') as f:
        storage_path = f.name
    
    try:
        bus = EventBus(enable_persistence=True, storage_path=storage_path)
        registry = EventHandlerRegistry(bus)
        
        # Register handlers
        node_handler = NodeEventHandler()
        ui_handler = UIEventHandler()
        system_handler = SystemEventHandler()
        
        registry.register_handler(node_handler)
        registry.register_handler(ui_handler)
        registry.register_handler(system_handler)
        
        # Test node operations
        
        # 1. Create nodes
        node1_event = create_node_created_event(
            node_id=1,
            title="Root Node",
            content="This is the root node",
            parent_id=None,
            position={'x': 0, 'y': 0}
        )
        bus.publish(node1_event)
        
        node2_event = create_node_created_event(
            node_id=2,
            title="Child Node",
            content="This is a child node",
            parent_id=1,
            position={'x': 100, 'y': 100}
        )
        bus.publish(node2_event)
        
        # 2. Update a node
        update_event = Event(
            event_type=EventType.NODE_UPDATED,
            data={
                'node_id': 1,
                'node_data': {
                    'changes': {'title': 'Updated Root Node'},
                    'old_values': {'title': 'Root Node'}
                }
            }
        )
        bus.publish(update_event)
        
        # 3. UI interactions
        selection_event = Event(
            event_type=EventType.UI_NODE_SELECTED,
            data={
                'ui_data': {
                    'node_id': 1,
                    'selected': True,
                    'selection_mode': 'single'
                }
            }
        )
        bus.publish(selection_event)
        
        zoom_event = Event(
            event_type=EventType.UI_ZOOM_CHANGED,
            data={
                'ui_data': {
                    'zoom_level': 1.5
                }
            }
        )
        bus.publish(zoom_event)
        
        # 4. System events
        startup_event = Event(
            event_type=EventType.SYSTEM_STARTUP,
            data={
                'system_component': 'main',
                'message': 'System started',
                'system_data': {'version': '1.0.0'}
            }
        )
        bus.publish(startup_event)
        
        error_event = create_system_error_event(
            component='database',
            error_message='Connection timeout',
            error_code='DB_TIMEOUT'
        )
        bus.publish(error_event)
        
        # Verify handlers processed events correctly
        
        # Node handler verification
        assert len(node_handler.node_cache) == 2
        assert node_handler.node_cache[1]['title'] == 'Updated Root Node'
        assert node_handler.node_cache[2]['parent_id'] == 1
        assert 2 in node_handler.node_relationships[1]
        assert node_handler.node_creation_count == 2
        assert node_handler.node_update_count == 1
        
        # UI handler verification
        assert 1 in ui_handler.selected_nodes
        assert ui_handler.current_zoom_level == 1.5
        assert ui_handler.ui_interaction_count == 2
        
        # System handler verification
        assert system_handler.system_status == 'running'
        assert system_handler.error_count_by_component['database'] == 1
        assert system_handler.system_start_time is not None
        
        # Verify event persistence
        persisted_events = bus.persistence.load_events()
        assert len(persisted_events) == 7  # All events should be persisted
        
        # Verify handler statistics
        node_stats = node_handler.get_stats()
        assert node_stats['handled_events_count'] == 3  # 2 creates + 1 update
        assert node_stats['error_count'] == 0
        
        ui_stats = ui_handler.get_stats()
        assert ui_stats['handled_events_count'] == 2  # 1 selection + 1 zoom
        
        system_stats = system_handler.get_stats()
        assert system_stats['handled_events_count'] == 2  # 1 startup + 1 error
        
        # Verify registry statistics
        registry_stats = registry.get_registry_stats()
        assert registry_stats['total_handlers'] == 3
        assert 'NodeEventHandler' in registry_stats['handler_names']
        assert 'UIEventHandler' in registry_stats['handler_names']
        assert 'SystemEventHandler' in registry_stats['handler_names']
        
        # Clean up
        registry.shutdown_all_handlers()
        bus.shutdown()
        
    finally:
        Path(storage_path).unlink(missing_ok=True)
    
    print("✓ Complete event handler integration test passed")


def test_event_handler_priority_ordering():
    """Test that event handlers are called in priority order."""
    
    bus = EventBus(enable_persistence=False)
    call_order = []
    
    # Create handlers with different priorities and unique names
    class HighPriorityHandler(NodeEventHandler):
        def __init__(self):
            super().__init__()
            self.name = "HighPriorityNodeHandler"
        
        def handle_event(self, event):
            call_order.append('high')
            super().handle_event(event)
    
    class LowPriorityHandler(NodeEventHandler):
        def __init__(self):
            super().__init__()
            self.name = "LowPriorityNodeHandler"
        
        def get_priority_for_event_type(self, event_type):
            return 1  # Lower priority
        
        def handle_event(self, event):
            call_order.append('low')
            super().handle_event(event)
    
    # Register handlers directly with the bus to control priority
    high_handler = HighPriorityHandler()
    low_handler = LowPriorityHandler()
    
    # Subscribe directly with specific priorities
    bus.subscribe(
        EventType.NODE_CREATED,
        high_handler._handle_event_wrapper,
        priority=10
    )
    
    bus.subscribe(
        EventType.NODE_CREATED,
        low_handler._handle_event_wrapper,
        priority=1
    )
    
    # Publish event
    event = Event(
        event_type=EventType.NODE_CREATED,
        data={
            'node_id': 1,
            'node_data': {'title': 'Test Node'}
        }
    )
    bus.publish(event)
    
    # Verify call order (high priority first)
    assert call_order == ['high', 'low']
    
    # Clean up
    bus.shutdown()
    
    print("✓ Event handler priority ordering test passed")


def test_event_handler_error_resilience():
    """Test that event handlers are resilient to errors in other handlers."""
    
    bus = EventBus(enable_persistence=False)
    
    # Create handlers, one that fails
    class FailingHandler(NodeEventHandler):
        def __init__(self):
            super().__init__()
            self.name = "FailingNodeHandler"
        
        def handle_event(self, event):
            raise ValueError("Handler failed")
    
    class WorkingHandler(NodeEventHandler):
        def __init__(self):
            super().__init__()
            self.name = "WorkingNodeHandler"
            self.events_handled = []
        
        def handle_event(self, event):
            self.events_handled.append(event)
            super().handle_event(event)
    
    # Register handlers
    failing_handler = FailingHandler()
    working_handler = WorkingHandler()
    
    registry = EventHandlerRegistry(bus)
    registry.register_handler(failing_handler)
    registry.register_handler(working_handler)
    
    # Publish event
    event = Event(
        event_type=EventType.NODE_CREATED,
        data={
            'node_id': 1,
            'node_data': {'title': 'Test Node'}
        }
    )
    bus.publish(event)
    
    # Verify working handler still processed the event
    assert len(working_handler.events_handled) == 1
    assert working_handler.events_handled[0] == event
    
    # Verify failing handler recorded the error
    assert failing_handler.error_count == 1
    
    # Clean up
    registry.shutdown_all_handlers()
    bus.shutdown()
    
    print("✓ Event handler error resilience test passed")


def test_event_handler_filtering():
    """Test event handler filtering with tags and conditions."""
    
    bus = EventBus(enable_persistence=False)
    
    # Create handler that only processes important events
    class ImportantNodeHandler(NodeEventHandler):
        def __init__(self):
            super().__init__()
            self.name = "ImportantNodeHandler"
            self.processed_events = []
        
        def handle_event(self, event):
            self.processed_events.append(event)
            super().handle_event(event)
    
    handler = ImportantNodeHandler()
    
    # Register with tag filter
    subscription_id = bus.subscribe(
        EventType.NODE_CREATED,
        handler._handle_event_wrapper,
        tags={'important'}
    )
    
    # Publish events with and without important tag
    important_event = Event(
        event_type=EventType.NODE_CREATED,
        data={
            'node_id': 1,
            'node_data': {'title': 'Important Node'}
        }
    )
    important_event.add_tag('important')
    
    normal_event = Event(
        event_type=EventType.NODE_CREATED,
        data={
            'node_id': 2,
            'node_data': {'title': 'Normal Node'}
        }
    )
    normal_event.add_tag('normal')
    
    bus.publish(important_event)
    bus.publish(normal_event)
    
    # Verify only important event was processed
    assert len(handler.processed_events) == 1
    assert handler.processed_events[0] == important_event
    
    # Clean up
    bus.unsubscribe(subscription_id)
    bus.shutdown()
    
    print("✓ Event handler filtering test passed")


def test_cross_handler_communication():
    """Test communication between different event handlers."""
    
    bus = EventBus(enable_persistence=False)
    
    # Create handlers that communicate via events
    class NodeHandler(NodeEventHandler):
        def __init__(self, bus):
            super().__init__()
            self.name = "CommunicatingNodeHandler"
            self.bus = bus
        
        def handle_event(self, event):
            super().handle_event(event)
            
            # When a node is created, publish a UI selection event
            if event.event_type == EventType.NODE_CREATED:
                selection_event = Event(
                    event_type=EventType.UI_NODE_SELECTED,
                    data={
                        'ui_data': {
                            'node_id': event.data['node_id'],
                            'selected': True,
                            'selection_mode': 'single'
                        }
                    }
                )
                self.bus.publish(selection_event)
    
    class UIHandler(UIEventHandler):
        def __init__(self, bus):
            super().__init__()
            self.name = "CommunicatingUIHandler"
            self.bus = bus
            self.auto_selections = []
        
        def handle_event(self, event):
            if event.event_type == EventType.UI_NODE_SELECTED:
                # Track auto-selections
                if event.data.get('ui_data', {}).get('selection_mode') == 'single':
                    self.auto_selections.append(event.data['ui_data']['node_id'])
            
            super().handle_event(event)
    
    # Register handlers
    node_handler = NodeHandler(bus)
    ui_handler = UIHandler(bus)
    
    registry = EventHandlerRegistry(bus)
    registry.register_handler(node_handler)
    registry.register_handler(ui_handler)
    
    # Create a node
    create_event = Event(
        event_type=EventType.NODE_CREATED,
        data={
            'node_id': 1,
            'node_data': {'title': 'Auto-Select Node'}
        }
    )
    bus.publish(create_event)
    
    # Verify cross-handler communication worked
    assert 1 in ui_handler.selected_nodes
    assert 1 in ui_handler.auto_selections
    
    # Clean up
    registry.shutdown_all_handlers()
    bus.shutdown()
    
    print("✓ Cross-handler communication test passed")


def test_handler_performance_monitoring():
    """Test performance monitoring of event handlers."""
    
    bus = EventBus(enable_persistence=False)
    
    # Create a slow handler
    class SlowHandler(NodeEventHandler):
        def __init__(self):
            super().__init__()
            self.name = "SlowNodeHandler"
        
        def handle_event(self, event):
            time.sleep(0.01)  # Simulate slow processing
            super().handle_event(event)
    
    handler = SlowHandler()
    registry = EventHandlerRegistry(bus)
    registry.register_handler(handler)
    
    # Process multiple events
    for i in range(5):
        event = Event(
            event_type=EventType.NODE_CREATED,
            data={
                'node_id': i,
                'node_data': {'title': f'Node {i}'}
            }
        )
        bus.publish(event)
    
    # Get metrics
    metrics = bus.get_metrics()
    
    # Verify metrics were collected
    assert 'middleware_metrics' in metrics
    
    # Find metrics middleware
    metrics_middleware = None
    for key, value in metrics['middleware_metrics'].items():
        if 'MetricsMiddleware' in key:
            metrics_middleware = value
            break
    
    assert metrics_middleware is not None
    assert 'event_counts' in metrics_middleware
    assert metrics_middleware['event_counts']['node.created'] == 5
    
    # Clean up
    registry.shutdown_all_handlers()
    bus.shutdown()
    
    print("✓ Handler performance monitoring test passed")


def test_setup_default_handlers_integration():
    """Test setting up default handlers and their integration."""
    
    # Set up default handlers
    setup_default_handlers()
    
    # Get the global registry
    from src.application.event_handlers import get_handler_registry
    registry = get_handler_registry()
    
    # Verify default handlers were registered
    handlers = registry.get_all_handlers()
    assert len(handlers) >= 3
    
    handler_names = list(handlers.keys())
    assert 'NodeEventHandler' in handler_names
    assert 'UIEventHandler' in handler_names
    assert 'SystemEventHandler' in handler_names
    
    # Test that handlers are working
    bus = get_event_bus()
    
    # Publish a test event
    event = Event(
        event_type=EventType.NODE_CREATED,
        data={
            'node_id': 999,
            'node_data': {'title': 'Default Handler Test'}
        }
    )
    bus.publish(event)
    
    # Verify node handler processed the event
    node_handler = handlers['NodeEventHandler']
    assert 999 in node_handler.node_cache
    assert node_handler.node_cache[999]['title'] == 'Default Handler Test'
    
    # Clean up
    registry.shutdown_all_handlers()
    
    print("✓ Setup default handlers integration test passed")


if __name__ == "__main__":
    """Run integration tests."""
    print("Running Event Handlers Integration Tests...")
    print()
    
    test_complete_event_handler_integration()
    test_event_handler_priority_ordering()
    test_event_handler_error_resilience()
    test_event_handler_filtering()
    test_cross_handler_communication()
    test_handler_performance_monitoring()
    test_setup_default_handlers_integration()
    
    print()
    print("🎉 All integration tests passed!")
    print()
    print("Event Handlers - Task 8.2 Complete!")
    print()
    print("Key Features Implemented:")
    print("✓ NodeEventHandler for comprehensive node lifecycle management")
    print("✓ UIEventHandler for user interface state management")
    print("✓ SystemEventHandler for system monitoring and error tracking")
    print("✓ EventHandlerRegistry for centralized handler management")
    print("✓ Priority-based event processing")
    print("✓ Error resilience and isolation between handlers")
    print("✓ Event filtering with tags and custom conditions")
    print("✓ Cross-handler communication via event publishing")
    print("✓ Performance monitoring and metrics collection")
    print("✓ Comprehensive statistics and reporting")
    print("✓ Easy setup with default handler configuration")