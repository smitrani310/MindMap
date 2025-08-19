"""
Comprehensive integration tests for the complete event system.

This test suite validates the entire event system including:
- Event publishing and subscription
- Event handler execution
- Event middleware functionality  
- Event persistence and replay
"""

import pytest
import asyncio
import tempfile
import time
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock

from src.infrastructure.event_system import (
    Event, EventType, EventPriority, EventBus, get_event_bus,
    publish_event, subscribe_to_events, event_handler
)
from src.infrastructure.domain_events import (
    NodeCreatedEvent, NodeUpdatedEvent, SystemErrorEvent,
    create_node_created_event, create_system_error_event
)
from src.application.event_handlers import (
    NodeEventHandler, UIEventHandler, SystemEventHandler,
    setup_default_handlers, get_handler_registry
)


def test_complete_event_publishing_and_subscription():
    """Test comprehensive event publishing and subscription scenarios."""
    
    print("Testing event publishing and subscription...")
    
    bus = EventBus(enable_persistence=False)
    subscription_results = {}
    
    # Test different subscription patterns
    
    # 1. Single event type subscription
    def single_event_handler(event):
        subscription_results.setdefault('single', []).append(event)
    
    sub1 = bus.subscribe(EventType.NODE_CREATED, single_event_handler)
    
    # 2. Multiple event type subscription
    def multi_event_handler(event):
        subscription_results.setdefault('multi', []).append(event)
    
    sub2 = bus.subscribe(
        [EventType.NODE_CREATED, EventType.NODE_UPDATED, EventType.NODE_DELETED],
        multi_event_handler
    )
    
    # 3. Priority-based subscription
    def high_priority_handler(event):
        subscription_results.setdefault('high_priority', []).append(event)
    
    def low_priority_handler(event):
        subscription_results.setdefault('low_priority', []).append(event)
    
    sub3 = bus.subscribe(EventType.NODE_CREATED, high_priority_handler, priority=10)
    sub4 = bus.subscribe(EventType.NODE_CREATED, low_priority_handler, priority=1)
    
    # 4. Tag-based subscription
    def tagged_handler(event):
        subscription_results.setdefault('tagged', []).append(event)
    
    sub5 = bus.subscribe(EventType.NODE_CREATED, tagged_handler, tags={'important'})
    
    # 5. Conditional subscription
    def conditional_handler(event):
        subscription_results.setdefault('conditional', []).append(event)
    
    sub6 = bus.subscribe(
        EventType.NODE_CREATED,
        conditional_handler,
        condition=lambda e: e.data.get('node_data', {}).get('priority', 0) > 5
    )
    
    # Publish test events
    
    # Event 1: Basic node creation
    event1 = create_node_created_event(node_id=1, title="Basic Node")
    bus.publish(event1)
    
    # Event 2: Tagged node creation
    event2 = create_node_created_event(node_id=2, title="Important Node")
    event2.add_tag('important')
    bus.publish(event2)
    
    # Event 3: High priority node creation
    event3 = Event(
        event_type=EventType.NODE_CREATED,
        data={
            'node_id': 3,
            'node_data': {'title': 'High Priority Node', 'priority': 10}
        }
    )
    bus.publish(event3)
    
    # Event 4: Node update (should only trigger multi handler)
    event4 = Event(
        event_type=EventType.NODE_UPDATED,
        data={'node_id': 1, 'node_data': {'changes': {'title': 'Updated Node'}}}
    )
    bus.publish(event4)
    
    # Verify subscription results
    
    # Single event handler should get all NODE_CREATED events
    assert len(subscription_results['single']) == 3
    
    # Multi event handler should get all events
    assert len(subscription_results['multi']) == 4
    
    # Priority handlers should get NODE_CREATED events
    assert len(subscription_results['high_priority']) == 3
    assert len(subscription_results['low_priority']) == 3
    
    # Tagged handler should only get tagged event
    assert len(subscription_results['tagged']) == 1
    assert subscription_results['tagged'][0] == event2
    
    # Conditional handler should only get high priority event
    assert len(subscription_results['conditional']) == 1
    assert subscription_results['conditional'][0] == event3
    
    # Clean up
    for sub_id in [sub1, sub2, sub3, sub4, sub5, sub6]:
        bus.unsubscribe(sub_id)
    
    bus.shutdown()
    
    print("✓ Event publishing and subscription test passed")


def test_event_handler_execution_comprehensive():
    """Test comprehensive event handler execution scenarios."""
    
    print("Testing event handler execution...")
    
    bus = EventBus(enable_persistence=False)
    
    # Set up handlers
    node_handler = NodeEventHandler()
    ui_handler = UIEventHandler()
    system_handler = SystemEventHandler()
    
    # Register handlers
    node_handler.register(bus)
    ui_handler.register(bus)
    system_handler.register(bus)
    
    # Test node handler execution
    
    # Create nodes with relationships
    parent_event = create_node_created_event(
        node_id=1,
        title="Parent Node",
        content="This is a parent node"
    )
    bus.publish(parent_event)
    
    child_event = create_node_created_event(
        node_id=2,
        title="Child Node",
        content="This is a child node",
        parent_id=1
    )
    bus.publish(child_event)
    
    # Update a node
    update_event = Event(
        event_type=EventType.NODE_UPDATED,
        data={
            'node_id': 1,
            'node_data': {
                'changes': {'title': 'Updated Parent Node'},
                'old_values': {'title': 'Parent Node'}
            }
        }
    )
    bus.publish(update_event)
    
    # Move a node
    move_event = Event(
        event_type=EventType.NODE_MOVED,
        data={
            'node_id': 2,
            'node_data': {
                'old_position': {'x': 0, 'y': 0},
                'new_position': {'x': 100, 'y': 150}
            }
        }
    )
    bus.publish(move_event)
    
    # Delete a node
    delete_event = Event(
        event_type=EventType.NODE_DELETED,
        data={
            'node_id': 2,
            'node_data': {
                'deleted_node_data': {'title': 'Child Node', 'parent_id': 1},
                'cascade_deleted': []
            }
        }
    )
    bus.publish(delete_event)
    
    # Verify node handler execution
    assert len(node_handler.node_cache) == 1  # Only parent remains
    assert node_handler.node_cache[1]['title'] == 'Updated Parent Node'
    assert node_handler.node_creation_count == 2
    assert node_handler.node_update_count == 1
    assert node_handler.node_deletion_count == 1
    
    # Test UI handler execution
    
    # Node selection
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
    
    # View change
    view_event = Event(
        event_type=EventType.UI_VIEW_CHANGED,
        data={
            'ui_data': {
                'zoom_level': 2.0,
                'center_position': {'x': 200, 'y': 300}
            }
        }
    )
    bus.publish(view_event)
    
    # Filter application
    filter_event = Event(
        event_type=EventType.UI_FILTER_APPLIED,
        data={
            'ui_data': {
                'filter_type': 'urgency',
                'filter_value': 'high',
                'active': True
            }
        }
    )
    bus.publish(filter_event)
    
    # Verify UI handler execution
    assert 1 in ui_handler.selected_nodes
    assert ui_handler.current_zoom_level == 2.0
    assert ui_handler.current_center_position == {'x': 200, 'y': 300}
    assert 'urgency' in ui_handler.active_filters
    assert ui_handler.active_filters['urgency'] == 'high'
    
    # Test system handler execution
    
    # System startup
    startup_event = Event(
        event_type=EventType.SYSTEM_STARTUP,
        data={
            'system_component': 'main',
            'message': 'System started',
            'system_data': {'version': '2.0.0'}
        }
    )
    bus.publish(startup_event)
    
    # System error
    error_event = create_system_error_event(
        component='database',
        error_message='Connection timeout',
        error_code='DB_TIMEOUT'
    )
    bus.publish(error_event)
    
    # Performance issue
    perf_event = Event(
        event_type=EventType.PERFORMANCE_SLOW_OPERATION,
        data={
            'operation_name': 'slow_query',
            'duration_ms': 3000.0,
            'threshold_ms': 1000.0,
            'performance_data': {'component': 'database'}
        }
    )
    bus.publish(perf_event)
    
    # Verify system handler execution
    assert system_handler.system_status == 'running'
    assert system_handler.error_count_by_component['database'] == 1
    assert len(system_handler.performance_issues) == 1
    
    # Get comprehensive statistics
    node_stats = node_handler.get_stats()
    ui_stats = ui_handler.get_stats()
    system_stats = system_handler.get_stats()
    
    assert node_stats['handled_events_count'] == 5  # 2 creates + 1 update + 1 move + 1 delete
    assert ui_stats['handled_events_count'] == 3    # 1 selection + 1 view + 1 filter
    assert system_stats['handled_events_count'] == 3  # 1 startup + 1 error + 1 perf
    
    # Clean up
    node_handler.unregister(bus)
    ui_handler.unregister(bus)
    system_handler.unregister(bus)
    bus.shutdown()
    
    print("✓ Event handler execution test passed")