"""
Unit tests for the event system foundation.
"""

import pytest
import asyncio
import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch
from concurrent.futures import ThreadPoolExecutor

from src.infrastructure.event_system import (
    Event, EventType, EventPriority, EventMetadata,
    EventBus, EventSubscription, EventMiddleware,
    LoggingMiddleware, ValidationMiddleware, MetricsMiddleware,
    EventPersistence, get_event_bus, publish_event,
    subscribe_to_events, event_handler
)


class TestEventMetadata:
    """Test cases for EventMetadata."""
    
    def test_metadata_creation(self):
        """Test creating event metadata."""
        metadata = EventMetadata(
            user_id="user123",
            session_id="session456",
            source_component="test_component"
        )
        
        assert metadata.user_id == "user123"
        assert metadata.session_id == "session456"
        assert metadata.source_component == "test_component"
        assert len(metadata.correlation_id) == 8
        assert isinstance(metadata.tags, set)
        assert isinstance(metadata.custom_data, dict)
    
    def test_metadata_to_dict(self):
        """Test converting metadata to dictionary."""
        metadata = EventMetadata(
            user_id="user123",
            tags={"tag1", "tag2"},
            custom_data={"key": "value"}
        )
        
        result = metadata.to_dict()
        
        assert result["user_id"] == "user123"
        assert set(result["tags"]) == {"tag1", "tag2"}
        assert result["custom_data"]["key"] == "value"
        assert "correlation_id" in result


class TestEvent:
    """Test cases for Event class."""
    
    def test_event_creation(self):
        """Test creating an event."""
        metadata = EventMetadata(user_id="user123")
        event = Event(
            event_type=EventType.NODE_CREATED,
            data={"node_id": 1, "title": "Test Node"},
            metadata=metadata,
            priority=EventPriority.HIGH
        )
        
        assert event.event_type == EventType.NODE_CREATED
        assert event.data["node_id"] == 1
        assert event.metadata.user_id == "user123"
        assert event.priority == EventPriority.HIGH
        assert isinstance(event.timestamp, datetime)
        assert len(event.event_id) > 0
    
    def test_event_to_dict(self):
        """Test converting event to dictionary."""
        event = Event(
            event_type=EventType.NODE_UPDATED,
            data={"node_id": 2}
        )
        
        result = event.to_dict()
        
        assert result["event_type"] == "node.updated"
        assert result["data"]["node_id"] == 2
        assert "event_id" in result
        assert "timestamp" in result
        assert "metadata" in result
        assert "priority" in result
    
    def test_event_from_dict(self):
        """Test creating event from dictionary."""
        event_dict = {
            "event_id": "test-id",
            "event_type": "node.created",
            "data": {"node_id": 3},
            "metadata": {
                "correlation_id": "corr123",
                "user_id": "user456"
            },
            "priority": 10,
            "timestamp": "2023-01-01T12:00:00"
        }
        
        event = Event.from_dict(event_dict)
        
        assert event.event_id == "test-id"
        assert event.event_type == EventType.NODE_CREATED
        assert event.data["node_id"] == 3
        assert event.metadata.correlation_id == "corr123"
        assert event.metadata.user_id == "user456"
        assert event.priority == EventPriority.HIGH
    
    def test_event_fluent_interface(self):
        """Test event fluent interface methods."""
        event = Event(event_type=EventType.NODE_CREATED)
        
        result = (event
                 .add_tag("important")
                 .add_tag("test")
                 .set_source("test_component")
                 .set_user_context("user789", "session123"))
        
        assert result is event  # Fluent interface returns self
        assert "important" in event.metadata.tags
        assert "test" in event.metadata.tags
        assert event.metadata.source_component == "test_component"
        assert event.metadata.user_id == "user789"
        assert event.metadata.session_id == "session123"


class TestEventSubscription:
    """Test cases for EventSubscription."""
    
    def test_subscription_creation(self):
        """Test creating an event subscription."""
        handler = Mock()
        event_types = {EventType.NODE_CREATED, EventType.NODE_UPDATED}
        
        subscription = EventSubscription(
            handler=handler,
            event_types=event_types,
            subscription_id="sub123",
            priority=5,
            tags={"important"}
        )
        
        assert subscription.handler == handler
        assert subscription.event_types == event_types
        assert subscription.subscription_id == "sub123"
        assert subscription.priority == 5
        assert subscription.tags == {"important"}
        assert subscription.call_count == 0
    
    def test_subscription_matches_event_type(self):
        """Test subscription matching by event type."""
        handler = Mock()
        subscription = EventSubscription(
            handler=handler,
            event_types={EventType.NODE_CREATED},
            subscription_id="sub123"
        )
        
        matching_event = Event(event_type=EventType.NODE_CREATED)
        non_matching_event = Event(event_type=EventType.NODE_UPDATED)
        
        assert subscription.matches(matching_event) is True
        assert subscription.matches(non_matching_event) is False
    
    def test_subscription_matches_tags(self):
        """Test subscription matching by tags."""
        handler = Mock()
        subscription = EventSubscription(
            handler=handler,
            event_types={EventType.NODE_CREATED},
            subscription_id="sub123",
            tags={"important"}
        )
        
        matching_event = Event(event_type=EventType.NODE_CREATED)
        matching_event.add_tag("important")
        
        non_matching_event = Event(event_type=EventType.NODE_CREATED)
        non_matching_event.add_tag("normal")
        
        assert subscription.matches(matching_event) is True
        assert subscription.matches(non_matching_event) is False
    
    def test_subscription_matches_condition(self):
        """Test subscription matching by custom condition."""
        handler = Mock()
        condition = lambda event: event.data.get("priority", 0) > 5
        
        subscription = EventSubscription(
            handler=handler,
            event_types={EventType.NODE_CREATED},
            subscription_id="sub123",
            condition=condition
        )
        
        matching_event = Event(
            event_type=EventType.NODE_CREATED,
            data={"priority": 10}
        )
        non_matching_event = Event(
            event_type=EventType.NODE_CREATED,
            data={"priority": 3}
        )
        
        assert subscription.matches(matching_event) is True
        assert subscription.matches(non_matching_event) is False
    
    def test_subscription_call_handler(self):
        """Test calling subscription handler."""
        handler = Mock()
        subscription = EventSubscription(
            handler=handler,
            event_types={EventType.NODE_CREATED},
            subscription_id="sub123"
        )
        
        event = Event(event_type=EventType.NODE_CREATED)
        subscription.call_handler(event)
        
        handler.assert_called_once_with(event)
        assert subscription.call_count == 1
        assert subscription.last_called is not None


class TestEventMiddleware:
    """Test cases for event middleware."""
    
    def test_logging_middleware(self):
        """Test logging middleware."""
        logger = Mock()
        middleware = LoggingMiddleware(logger)
        next_handler = Mock()
        
        event = Event(event_type=EventType.NODE_CREATED)
        middleware.process(event, next_handler)
        
        logger.info.assert_called_once()
        next_handler.assert_called_once_with(event)
    
    def test_validation_middleware(self):
        """Test validation middleware."""
        validator = Mock(return_value=True)
        middleware = ValidationMiddleware({EventType.NODE_CREATED: validator})
        next_handler = Mock()
        
        event = Event(event_type=EventType.NODE_CREATED)
        middleware.process(event, next_handler)
        
        validator.assert_called_once_with(event)
        next_handler.assert_called_once_with(event)
    
    def test_validation_middleware_failure(self):
        """Test validation middleware with validation failure."""
        validator = Mock(return_value=False)
        middleware = ValidationMiddleware({EventType.NODE_CREATED: validator})
        next_handler = Mock()
        
        event = Event(event_type=EventType.NODE_CREATED)
        
        with pytest.raises(ValueError, match="Event validation failed"):
            middleware.process(event, next_handler)
        
        validator.assert_called_once_with(event)
        next_handler.assert_not_called()
    
    def test_metrics_middleware(self):
        """Test metrics middleware."""
        middleware = MetricsMiddleware()
        next_handler = Mock()
        
        event = Event(event_type=EventType.NODE_CREATED)
        middleware.process(event, next_handler)
        
        next_handler.assert_called_once_with(event)
        
        metrics = middleware.get_metrics()
        assert metrics["event_counts"]["node.created"] == 1
        assert "processing_times" in metrics
        assert "node.created" in metrics["processing_times"]


class TestEventPersistence:
    """Test cases for event persistence."""
    
    def test_persist_and_load_events(self):
        """Test persisting and loading events."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.jsonl') as f:
            storage_path = f.name
        
        try:
            persistence = EventPersistence(storage_path)
            
            # Create and persist events
            event1 = Event(event_type=EventType.NODE_CREATED, data={"node_id": 1})
            event2 = Event(event_type=EventType.NODE_UPDATED, data={"node_id": 2})
            
            persistence.persist_event(event1)
            persistence.persist_event(event2)
            
            # Load events
            loaded_events = persistence.load_events()
            
            assert len(loaded_events) == 2
            assert loaded_events[0].event_type == EventType.NODE_CREATED
            assert loaded_events[1].event_type == EventType.NODE_UPDATED
            
        finally:
            Path(storage_path).unlink(missing_ok=True)
    
    def test_load_events_with_filter(self):
        """Test loading events with event type filter."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.jsonl') as f:
            storage_path = f.name
        
        try:
            persistence = EventPersistence(storage_path)
            
            # Create and persist events
            event1 = Event(event_type=EventType.NODE_CREATED, data={"node_id": 1})
            event2 = Event(event_type=EventType.NODE_UPDATED, data={"node_id": 2})
            event3 = Event(event_type=EventType.NODE_CREATED, data={"node_id": 3})
            
            persistence.persist_event(event1)
            persistence.persist_event(event2)
            persistence.persist_event(event3)
            
            # Load only NODE_CREATED events
            loaded_events = persistence.load_events(event_type=EventType.NODE_CREATED)
            
            assert len(loaded_events) == 2
            assert all(e.event_type == EventType.NODE_CREATED for e in loaded_events)
            
        finally:
            Path(storage_path).unlink(missing_ok=True)
    
    def test_load_events_with_limit(self):
        """Test loading events with limit."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.jsonl') as f:
            storage_path = f.name
        
        try:
            persistence = EventPersistence(storage_path)
            
            # Create and persist multiple events
            for i in range(5):
                event = Event(event_type=EventType.NODE_CREATED, data={"node_id": i})
                persistence.persist_event(event)
            
            # Load with limit
            loaded_events = persistence.load_events(limit=3)
            
            assert len(loaded_events) == 3
            
        finally:
            Path(storage_path).unlink(missing_ok=True)
    
    def test_clear_events(self):
        """Test clearing persisted events."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.jsonl') as f:
            storage_path = f.name
        
        try:
            persistence = EventPersistence(storage_path)
            
            # Persist an event
            event = Event(event_type=EventType.NODE_CREATED)
            persistence.persist_event(event)
            
            # Verify event exists
            loaded_events = persistence.load_events()
            assert len(loaded_events) == 1
            
            # Clear events
            persistence.clear_events()
            
            # Verify events are cleared
            loaded_events = persistence.load_events()
            assert len(loaded_events) == 0
            
        finally:
            Path(storage_path).unlink(missing_ok=True)


class TestEventBus:
    """Test cases for EventBus."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.jsonl') as f:
            self.storage_path = f.name
        self.event_bus = EventBus(enable_persistence=True, storage_path=self.storage_path)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        self.event_bus.shutdown()
        Path(self.storage_path).unlink(missing_ok=True)
    
    def test_subscribe_and_publish(self):
        """Test basic subscribe and publish functionality."""
        handler = Mock()
        
        # Subscribe to events
        subscription_id = self.event_bus.subscribe(EventType.NODE_CREATED, handler)
        
        # Publish event
        event = Event(event_type=EventType.NODE_CREATED, data={"node_id": 1})
        self.event_bus.publish(event)
        
        # Verify handler was called
        handler.assert_called_once_with(event)
        
        # Verify subscription exists
        assert subscription_id in self.event_bus.subscriptions
    
    def test_subscribe_multiple_event_types(self):
        """Test subscribing to multiple event types."""
        handler = Mock()
        
        # Subscribe to multiple event types
        event_types = [EventType.NODE_CREATED, EventType.NODE_UPDATED]
        subscription_id = self.event_bus.subscribe(event_types, handler)
        
        # Publish events of different types
        event1 = Event(event_type=EventType.NODE_CREATED)
        event2 = Event(event_type=EventType.NODE_UPDATED)
        event3 = Event(event_type=EventType.NODE_DELETED)  # Not subscribed
        
        self.event_bus.publish(event1)
        self.event_bus.publish(event2)
        self.event_bus.publish(event3)
        
        # Verify handler was called for subscribed events only
        assert handler.call_count == 2
        handler.assert_any_call(event1)
        handler.assert_any_call(event2)
    
    def test_unsubscribe(self):
        """Test unsubscribing from events."""
        handler = Mock()
        
        # Subscribe and then unsubscribe
        subscription_id = self.event_bus.subscribe(EventType.NODE_CREATED, handler)
        assert self.event_bus.unsubscribe(subscription_id) is True
        
        # Publish event after unsubscribing
        event = Event(event_type=EventType.NODE_CREATED)
        self.event_bus.publish(event)
        
        # Verify handler was not called
        handler.assert_not_called()
        
        # Verify subscription is removed
        assert subscription_id not in self.event_bus.subscriptions
    
    def test_subscription_priority(self):
        """Test subscription priority ordering."""
        call_order = []
        
        def handler1(event):
            call_order.append("handler1")
        
        def handler2(event):
            call_order.append("handler2")
        
        def handler3(event):
            call_order.append("handler3")
        
        # Subscribe with different priorities
        self.event_bus.subscribe(EventType.NODE_CREATED, handler1, priority=1)
        self.event_bus.subscribe(EventType.NODE_CREATED, handler2, priority=10)
        self.event_bus.subscribe(EventType.NODE_CREATED, handler3, priority=5)
        
        # Publish event
        event = Event(event_type=EventType.NODE_CREATED)
        self.event_bus.publish(event)
        
        # Verify handlers were called in priority order (highest first)
        assert call_order == ["handler2", "handler3", "handler1"]
    
    def test_subscription_with_tags(self):
        """Test subscription with tag filtering."""
        handler = Mock()
        
        # Subscribe with tag filter
        self.event_bus.subscribe(
            EventType.NODE_CREATED,
            handler,
            tags={"important"}
        )
        
        # Publish events with and without matching tags
        event1 = Event(event_type=EventType.NODE_CREATED)
        event1.add_tag("important")
        
        event2 = Event(event_type=EventType.NODE_CREATED)
        event2.add_tag("normal")
        
        self.event_bus.publish(event1)
        self.event_bus.publish(event2)
        
        # Verify handler was called only for matching event
        handler.assert_called_once_with(event1)
    
    def test_subscription_with_condition(self):
        """Test subscription with custom condition."""
        handler = Mock()
        condition = lambda event: event.data.get("priority", 0) > 5
        
        # Subscribe with condition
        self.event_bus.subscribe(
            EventType.NODE_CREATED,
            handler,
            condition=condition
        )
        
        # Publish events that match and don't match condition
        event1 = Event(event_type=EventType.NODE_CREATED, data={"priority": 10})
        event2 = Event(event_type=EventType.NODE_CREATED, data={"priority": 3})
        
        self.event_bus.publish(event1)
        self.event_bus.publish(event2)
        
        # Verify handler was called only for matching event
        handler.assert_called_once_with(event1)
    
    def test_async_handler(self):
        """Test async event handler."""
        async def async_handler(event):
            # Simulate async work
            await asyncio.sleep(0.01)
            async_handler.called = True
        
        async_handler.called = False
        
        # Subscribe async handler
        self.event_bus.subscribe(EventType.NODE_CREATED, async_handler)
        
        # Publish event
        event = Event(event_type=EventType.NODE_CREATED)
        self.event_bus.publish(event)
        
        # Give some time for async processing
        import time
        time.sleep(0.1)
        
        # Verify async handler was called
        assert async_handler.called is True
    
    def test_middleware_processing(self):
        """Test middleware processing pipeline."""
        # Create custom middleware
        class TestMiddleware(EventMiddleware):
            def __init__(self):
                self.processed_events = []
            
            def process(self, event, next_handler):
                self.processed_events.append(event)
                next_handler(event)
        
        test_middleware = TestMiddleware()
        self.event_bus.add_middleware(test_middleware)
        
        handler = Mock()
        self.event_bus.subscribe(EventType.NODE_CREATED, handler)
        
        # Publish event
        event = Event(event_type=EventType.NODE_CREATED)
        self.event_bus.publish(event)
        
        # Verify middleware processed the event
        assert len(test_middleware.processed_events) == 1
        assert test_middleware.processed_events[0] == event
        
        # Verify handler was still called
        handler.assert_called_once_with(event)
    
    def test_error_handling_in_handler(self):
        """Test error handling when event handler fails."""
        def failing_handler(event):
            raise ValueError("Handler failed")
        
        def working_handler(event):
            working_handler.called = True
        
        working_handler.called = False
        
        # Subscribe both handlers
        self.event_bus.subscribe(EventType.NODE_CREATED, failing_handler)
        self.event_bus.subscribe(EventType.NODE_CREATED, working_handler)
        
        # Publish event
        event = Event(event_type=EventType.NODE_CREATED)
        self.event_bus.publish(event)
        
        # Verify working handler was still called despite failing handler
        assert working_handler.called is True
    
    def test_get_subscription_stats(self):
        """Test getting subscription statistics."""
        handler1 = Mock()
        handler2 = Mock()
        
        # Create subscriptions
        self.event_bus.subscribe(EventType.NODE_CREATED, handler1)
        self.event_bus.subscribe([EventType.NODE_UPDATED, EventType.NODE_DELETED], handler2)
        
        # Get stats
        stats = self.event_bus.get_subscription_stats()
        
        assert stats["total_subscriptions"] == 2
        assert stats["subscriptions_by_type"]["node.created"] == 1
        assert stats["subscriptions_by_type"]["node.updated"] == 1
        assert stats["subscriptions_by_type"]["node.deleted"] == 1
        assert len(stats["subscription_details"]) == 2
    
    def test_get_metrics(self):
        """Test getting event processing metrics."""
        handler = Mock()
        self.event_bus.subscribe(EventType.NODE_CREATED, handler)
        
        # Publish some events
        for i in range(3):
            event = Event(event_type=EventType.NODE_CREATED, data={"node_id": i})
            self.event_bus.publish(event)
        
        # Get metrics
        metrics = self.event_bus.get_metrics()
        
        assert "middleware_metrics" in metrics
        # Should have metrics from MetricsMiddleware
        assert any("MetricsMiddleware" in key for key in metrics["middleware_metrics"].keys())


class TestGlobalEventBus:
    """Test cases for global event bus functions."""
    
    def test_get_event_bus_singleton(self):
        """Test that get_event_bus returns singleton."""
        bus1 = get_event_bus()
        bus2 = get_event_bus()
        
        assert bus1 is bus2
    
    def test_publish_event_convenience(self):
        """Test publish_event convenience function."""
        handler = Mock()
        
        # Subscribe using global bus
        subscribe_to_events(EventType.NODE_CREATED, handler)
        
        # Publish using convenience function
        event_id = publish_event(
            EventType.NODE_CREATED,
            data={"node_id": 1},
            priority=EventPriority.HIGH
        )
        
        # Verify handler was called
        handler.assert_called_once()
        called_event = handler.call_args[0][0]
        assert called_event.event_id == event_id
        assert called_event.data["node_id"] == 1
        assert called_event.priority == EventPriority.HIGH
    
    def test_event_handler_decorator(self):
        """Test event_handler decorator."""
        @event_handler(EventType.NODE_CREATED, priority=5)
        def test_handler(event):
            test_handler.called = True
            test_handler.event = event
        
        test_handler.called = False
        test_handler.event = None
        
        # Publish event
        event = Event(event_type=EventType.NODE_CREATED)
        get_event_bus().publish(event)
        
        # Verify handler was called
        assert test_handler.called is True
        assert test_handler.event == event
        
        # Verify subscription ID was stored
        assert hasattr(test_handler, '_event_subscription_id')


if __name__ == "__main__":
    pytest.main([__file__])