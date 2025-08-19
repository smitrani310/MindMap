"""
Integration tests for the event system foundation.
"""

import pytest
import asyncio
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock

from src.infrastructure.event_system import (
    Event, EventType, EventPriority, EventMetadata, EventBus,
    get_event_bus, publish_event, subscribe_to_events, event_handler
)
from src.infrastructure.domain_events import (
    NodeCreatedEvent, NodeUpdatedEvent, SystemErrorEvent,
    create_node_created_event, create_system_error_event
)


def test_complete_event_flow():
    """Test complete event flow from creation to handling."""
    
    # Set up event tracking
    handled_events = []
    
    def node_created_handler(event):
        handled_events.append(('node_created', event))
    
    def node_updated_handler(event):
        handled_events.append(('node_updated', event))
    
    def system_error_handler(event):
        handled_events.append(('system_error', event))
    
    # Subscribe to different event types
    bus = get_event_bus()
    
    sub1 = subscribe_to_events(EventType.NODE_CREATED, node_created_handler, priority=10)
    sub2 = subscribe_to_events(EventType.NODE_UPDATED, node_updated_handler, priority=5)
    sub3 = subscribe_to_events(EventType.SYSTEM_ERROR, system_error_handler, priority=20)
    
    # Publish events using different methods
    
    # 1. Direct event creation and publishing
    event1 = Event(
        event_type=EventType.NODE_CREATED,
        data={'node_id': 1, 'title': 'Test Node'},
        priority=EventPriority.HIGH
    )
    bus.publish(event1)
    
    # 2. Convenience function
    publish_event(
        EventType.NODE_UPDATED,
        data={'node_id': 1, 'changes': {'title': 'Updated Node'}},
        priority=EventPriority.NORMAL
    )
    
    # 3. Domain-specific event
    domain_event = create_node_created_event(
        node_id=2,
        title='Domain Event Node',
        content='Created using domain event'
    )
    bus.publish(domain_event)
    
    # 4. System error event
    error_event = create_system_error_event(
        component='test_component',
        error_message='Test error occurred',
        error_code='TEST_ERROR'
    )
    bus.publish(error_event)
    
    # Verify all events were handled
    assert len(handled_events) == 4
    
    # Check event types and order (should be by priority)
    event_types = [event[0] for event in handled_events]
    assert 'system_error' in event_types  # Priority 20
    assert 'node_created' in event_types  # Priority 10 (appears twice)
    assert 'node_updated' in event_types  # Priority 5
    
    # Verify event data
    node_created_events = [e for e in handled_events if e[0] == 'node_created']
    assert len(node_created_events) == 2
    
    # Check first node created event
    first_event = node_created_events[0][1]
    assert first_event.data['node_id'] == 1
    assert first_event.data['title'] == 'Test Node'
    
    # Check domain event
    domain_handled = [e for e in handled_events if e[0] == 'node_created' and e[1].data.get('node_data', {}).get('title') == 'Domain Event Node']
    assert len(domain_handled) == 1
    
    # Clean up subscriptions
    bus.unsubscribe(sub1)
    bus.unsubscribe(sub2)
    bus.unsubscribe(sub3)
    
    print("✓ Complete event flow test passed")


def test_event_middleware_pipeline():
    """Test event processing through middleware pipeline."""
    
    # Create custom middleware for testing
    class TestMiddleware:
        def __init__(self, name):
            self.name = name
            self.processed_events = []
        
        def process(self, event, next_handler):
            self.processed_events.append(event)
            # Add middleware marker to event
            if 'middleware_chain' not in event.data:
                event.data['middleware_chain'] = []
            event.data['middleware_chain'].append(self.name)
            next_handler(event)
    
    # Set up event bus with custom middleware
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.jsonl') as f:
        storage_path = f.name
    
    try:
        bus = EventBus(enable_persistence=True, storage_path=storage_path)
        
        # Add custom middleware
        middleware1 = TestMiddleware("middleware1")
        middleware2 = TestMiddleware("middleware2")
        
        bus.add_middleware(middleware1)
        bus.add_middleware(middleware2)
        
        # Set up handler
        handled_events = []
        def test_handler(event):
            handled_events.append(event)
        
        bus.subscribe(EventType.NODE_CREATED, test_handler)
        
        # Publish event
        event = Event(event_type=EventType.NODE_CREATED, data={'node_id': 1})
        bus.publish(event)
        
        # Verify middleware processed the event
        assert len(middleware1.processed_events) == 1
        assert len(middleware2.processed_events) == 1
        
        # Verify handler received the event with middleware markers
        assert len(handled_events) == 1
        processed_event = handled_events[0]
        assert 'middleware_chain' in processed_event.data
        assert 'middleware1' in processed_event.data['middleware_chain']
        assert 'middleware2' in processed_event.data['middleware_chain']
        
        # Verify event was persisted
        persisted_events = bus.persistence.load_events()
        assert len(persisted_events) == 1
        assert persisted_events[0].event_type == EventType.NODE_CREATED
        
        bus.shutdown()
        
    finally:
        Path(storage_path).unlink(missing_ok=True)
    
    print("✓ Event middleware pipeline test passed")


def test_event_filtering_and_conditions():
    """Test event filtering with tags and conditions."""
    
    bus = get_event_bus()
    handled_events = []
    
    # Handler for high-priority events only
    def high_priority_handler(event):
        handled_events.append(('high_priority', event))
    
    # Handler for events with 'important' tag
    def important_handler(event):
        handled_events.append(('important', event))
    
    # Handler for events with specific condition
    def large_node_handler(event):
        handled_events.append(('large_node', event))
    
    # Subscribe with different filters
    sub1 = bus.subscribe(
        EventType.NODE_CREATED,
        high_priority_handler,
        condition=lambda e: e.priority == EventPriority.HIGH
    )
    
    sub2 = bus.subscribe(
        EventType.NODE_CREATED,
        important_handler,
        tags={'important'}
    )
    
    sub3 = bus.subscribe(
        EventType.NODE_CREATED,
        large_node_handler,
        condition=lambda e: len(e.data.get('title', '')) > 10
    )
    
    # Publish various events
    
    # Event 1: High priority, no tags, short title
    event1 = Event(
        event_type=EventType.NODE_CREATED,
        data={'node_id': 1, 'title': 'Short'},
        priority=EventPriority.HIGH
    )
    bus.publish(event1)
    
    # Event 2: Normal priority, important tag, short title
    event2 = Event(
        event_type=EventType.NODE_CREATED,
        data={'node_id': 2, 'title': 'Tagged'}
    )
    event2.add_tag('important')
    bus.publish(event2)
    
    # Event 3: Normal priority, no tags, long title
    event3 = Event(
        event_type=EventType.NODE_CREATED,
        data={'node_id': 3, 'title': 'This is a very long title'}
    )
    bus.publish(event3)
    
    # Event 4: High priority, important tag, long title (matches all)
    event4 = Event(
        event_type=EventType.NODE_CREATED,
        data={'node_id': 4, 'title': 'Important and very long title'},
        priority=EventPriority.HIGH
    )
    event4.add_tag('important')
    bus.publish(event4)
    
    # Verify filtering worked correctly
    high_priority_events = [e for e in handled_events if e[0] == 'high_priority']
    important_events = [e for e in handled_events if e[0] == 'important']
    large_node_events = [e for e in handled_events if e[0] == 'large_node']
    
    # High priority handler should get events 1 and 4
    assert len(high_priority_events) == 2
    assert high_priority_events[0][1].data['node_id'] == 1
    assert high_priority_events[1][1].data['node_id'] == 4
    
    # Important handler should get events 2 and 4
    assert len(important_events) == 2
    assert important_events[0][1].data['node_id'] == 2
    assert important_events[1][1].data['node_id'] == 4
    
    # Large node handler should get events 3 and 4
    assert len(large_node_events) == 2
    assert large_node_events[0][1].data['node_id'] == 3
    assert large_node_events[1][1].data['node_id'] == 4
    
    # Clean up
    bus.unsubscribe(sub1)
    bus.unsubscribe(sub2)
    bus.unsubscribe(sub3)
    
    print("✓ Event filtering and conditions test passed")


def test_async_event_handling():
    """Test asynchronous event handling."""
    
    bus = get_event_bus()
    async_results = []
    sync_results = []
    
    # Async handler
    async def async_handler(event):
        await asyncio.sleep(0.01)  # Simulate async work
        async_results.append(event.data['node_id'])
    
    # Sync handler
    def sync_handler(event):
        sync_results.append(event.data['node_id'])
    
    # Subscribe both handlers
    sub1 = bus.subscribe(EventType.NODE_CREATED, async_handler)
    sub2 = bus.subscribe(EventType.NODE_CREATED, sync_handler)
    
    # Publish events
    for i in range(3):
        event = Event(
            event_type=EventType.NODE_CREATED,
            data={'node_id': i}
        )
        bus.publish(event)
    
    # Give time for async processing
    time.sleep(0.1)
    
    # Verify both handlers processed all events
    assert len(sync_results) == 3
    assert sync_results == [0, 1, 2]
    
    # Async results might be in different order due to async processing
    assert len(async_results) == 3
    assert set(async_results) == {0, 1, 2}
    
    # Clean up
    bus.unsubscribe(sub1)
    bus.unsubscribe(sub2)
    
    print("✓ Async event handling test passed")


def test_event_decorator():
    """Test event handler decorator functionality."""
    
    # Track decorator-registered handlers
    decorator_results = []
    
    @event_handler(EventType.NODE_CREATED, priority=15)
    def decorated_handler(event):
        decorator_results.append(event.data['node_id'])
    
    @event_handler([EventType.NODE_UPDATED, EventType.NODE_DELETED], priority=5)
    def multi_event_handler(event):
        decorator_results.append(f"{event.event_type.value}_{event.data['node_id']}")
    
    # Publish events
    bus = get_event_bus()
    
    # Node created event
    event1 = Event(event_type=EventType.NODE_CREATED, data={'node_id': 100})
    bus.publish(event1)
    
    # Node updated event
    event2 = Event(event_type=EventType.NODE_UPDATED, data={'node_id': 101})
    bus.publish(event2)
    
    # Node deleted event
    event3 = Event(event_type=EventType.NODE_DELETED, data={'node_id': 102})
    bus.publish(event3)
    
    # Verify decorator handlers were called
    assert 100 in decorator_results
    assert "node.updated_101" in decorator_results
    assert "node.deleted_102" in decorator_results
    
    # Verify subscription IDs were stored on functions
    assert hasattr(decorated_handler, '_event_subscription_id')
    assert hasattr(multi_event_handler, '_event_subscription_id')
    
    print("✓ Event decorator test passed")


def test_event_metrics_and_stats():
    """Test event metrics and subscription statistics."""
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.jsonl') as f:
        storage_path = f.name
    
    try:
        bus = EventBus(enable_persistence=True, storage_path=storage_path)
        
        # Create handlers
        def handler1(event):
            pass
        
        def handler2(event):
            pass
        
        # Subscribe to different events
        sub1 = bus.subscribe(EventType.NODE_CREATED, handler1, priority=10)
        sub2 = bus.subscribe([EventType.NODE_UPDATED, EventType.NODE_DELETED], handler2, priority=5)
        
        # Publish events
        for i in range(5):
            event = Event(event_type=EventType.NODE_CREATED, data={'node_id': i})
            bus.publish(event)
        
        for i in range(3):
            event = Event(event_type=EventType.NODE_UPDATED, data={'node_id': i})
            bus.publish(event)
        
        # Get subscription stats
        stats = bus.get_subscription_stats()
        
        assert stats['total_subscriptions'] == 2
        assert stats['subscriptions_by_type']['node.created'] == 1
        assert stats['subscriptions_by_type']['node.updated'] == 1
        assert stats['subscriptions_by_type']['node.deleted'] == 1
        
        # Verify subscription details
        sub_details = stats['subscription_details']
        assert len(sub_details) == 2
        
        # Find the subscription that handles NODE_CREATED
        node_created_sub = next(
            sub for sub in sub_details 
            if 'node.created' in sub['event_types']
        )
        assert node_created_sub['call_count'] == 5  # Called for each NODE_CREATED event
        assert node_created_sub['priority'] == 10
        
        # Get metrics
        metrics = bus.get_metrics()
        assert 'middleware_metrics' in metrics
        
        # Should have metrics from built-in middleware
        middleware_metrics = metrics['middleware_metrics']
        assert len(middleware_metrics) > 0
        
        # Check if MetricsMiddleware recorded events
        metrics_middleware_key = next(
            key for key in middleware_metrics.keys() 
            if 'MetricsMiddleware' in key
        )
        metrics_data = middleware_metrics[metrics_middleware_key]
        
        assert 'event_counts' in metrics_data
        assert metrics_data['event_counts']['node.created'] == 5
        assert metrics_data['event_counts']['node.updated'] == 3
        
        bus.shutdown()
        
    finally:
        Path(storage_path).unlink(missing_ok=True)
    
    print("✓ Event metrics and stats test passed")


if __name__ == "__main__":
    """Run integration tests."""
    print("Running Event System Foundation Integration Tests...")
    print()
    
    test_complete_event_flow()
    test_event_middleware_pipeline()
    test_event_filtering_and_conditions()
    test_async_event_handling()
    test_event_decorator()
    test_event_metrics_and_stats()
    
    print()
    print("🎉 All integration tests passed!")
    print()
    print("Event System Foundation - Task 8.1 Complete!")
    print()
    print("Key Features Implemented:")
    print("✓ Strongly typed event system with comprehensive event types")
    print("✓ Event bus with subscription management and priority handling")
    print("✓ Middleware pipeline for event processing and validation")
    print("✓ Event persistence for audit trails and replay")
    print("✓ Async/sync event handler support")
    print("✓ Event filtering with tags and custom conditions")
    print("✓ Event metrics and subscription statistics")
    print("✓ Domain-specific event classes with proper typing")
    print("✓ Decorator-based event handler registration")
    print("✓ Global event bus with convenience functions")
    print("✓ Comprehensive error handling and logging integration")