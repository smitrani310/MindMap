"""
Unit tests for event system infrastructure.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.infrastructure.events import (
    Event, EventType, EventHandler, EventMiddleware, EventBus, EventPersistence,
    LoggingMiddleware, PerformanceMiddleware, get_event_bus, publish_event,
    subscribe_to_event, create_node_event
)


class TestEvent:
    """Test cases for Event class."""
    
    def test_event_creation(self):
        """Test creating an event."""
        event = Event(
            type=EventType.NODE_CREATED,
            source="test",
            data={"node_id": 123},
            metadata={"test": True}
        )
        
        assert event.type == EventType.NODE_CREATED
        assert event.source == "test"
        assert event.data["node_id"] == 123
        assert event.metadata["test"] == True
        assert event.id is not None
        assert isinstance(event.timestamp, datetime)
    
    def test_event_to_dict(self):
        """Test converting event to dictionary."""
        event = Event(
            type=EventType.NODE_UPDATED,
            source="service",
            data={"key": "value"}
        )
        
        event_dict = event.to_dict()
        
        assert event_dict["type"] == EventType.NODE_UPDATED.value
        assert event_dict["source"] == "service"
        assert event_dict["data"]["key"] == "value"
        assert "id" in event_dict
        assert "timestamp" in event_dict
    
    def test_event_from_dict(self):
        """Test creating event from dictionary."""
        event_dict = {
            "id": "test-id",
            "type": EventType.NODE_DELETED.value,
            "timestamp": "2024-01-01T12:00:00",
            "source": "test_source",
            "data": {"test": "data"},
            "metadata": {"meta": "data"}
        }
        
        event = Event.from_dict(event_dict)
        
        assert event.id == "test-id"
        assert event.type == EventType.NODE_DELETED
        assert event.source == "test_source"
        assert event.data["test"] == "data"
        assert event.metadata["meta"] == "data"


class MockEventHandler(EventHandler):
    """Mock event handler for testing."""
    
    def __init__(self, name: str, can_handle_types: list = None):
        self._name = name
        self.can_handle_types = can_handle_types or []
        self.handled_events = []
    
    @property
    def name(self) -> str:
        return self._name
    
    def can_handle(self, event: Event) -> bool:
        return event.type in self.can_handle_types
    
    def handle(self, event: Event) -> None:
        self.handled_events.append(event)


class MockMiddleware(EventMiddleware):
    """Mock middleware for testing."""
    
    def __init__(self):
        self.processed_events = []
    
    def process(self, event: Event, next_handler) -> None:
        self.processed_events.append(event)
        next_handler(event)


class TestEventBus:
    """Test cases for EventBus."""
    
    @pytest.fixture
    def event_bus(self):
        """Create a fresh event bus for testing."""
        return EventBus(enable_persistence=True)
    
    def test_event_bus_initialization(self, event_bus):
        """Test event bus initialization."""
        assert event_bus is not None
        assert event_bus.persistence is not None
        assert len(event_bus.middleware) >= 2  # Default middleware
        assert len(event_bus.handlers) == 0
    
    def test_add_remove_handler(self, event_bus):
        """Test adding and removing event handlers."""
        handler = MockEventHandler("test_handler", [EventType.NODE_CREATED])
        
        # Add handler
        event_bus.add_handler(handler)
        assert handler in event_bus.handlers
        
        # Remove handler
        result = event_bus.remove_handler(handler)
        assert result == True
        assert handler not in event_bus.handlers
        
        # Try to remove non-existent handler
        result = event_bus.remove_handler(handler)
        assert result == False
    
    def test_add_middleware(self, event_bus):
        """Test adding middleware."""
        middleware = MockMiddleware()
        initial_count = len(event_bus.middleware)
        
        event_bus.add_middleware(middleware)
        assert len(event_bus.middleware) == initial_count + 1
        assert middleware in event_bus.middleware
    
    def test_subscribe_unsubscribe(self, event_bus):
        """Test subscribing and unsubscribing to events."""
        callback_calls = []
        
        def test_callback(event):
            callback_calls.append(event)
        
        # Subscribe
        event_bus.subscribe(EventType.NODE_CREATED, test_callback)
        assert test_callback in event_bus.subscribers[EventType.NODE_CREATED]
        
        # Publish event
        event = Event(type=EventType.NODE_CREATED, source="test")
        event_bus.publish(event)
        
        # Check callback was called
        assert len(callback_calls) == 1
        assert callback_calls[0] == event
        
        # Unsubscribe
        result = event_bus.unsubscribe(EventType.NODE_CREATED, test_callback)
        assert result == True
        assert test_callback not in event_bus.subscribers[EventType.NODE_CREATED]
    
    def test_publish_event_to_handlers(self, event_bus):
        """Test publishing events to handlers."""
        handler1 = MockEventHandler("handler1", [EventType.NODE_CREATED])
        handler2 = MockEventHandler("handler2", [EventType.NODE_UPDATED])
        handler3 = MockEventHandler("handler3", [EventType.NODE_CREATED, EventType.NODE_UPDATED])
        
        event_bus.add_handler(handler1)
        event_bus.add_handler(handler2)
        event_bus.add_handler(handler3)
        
        # Publish NODE_CREATED event
        event1 = Event(type=EventType.NODE_CREATED, source="test")
        event_bus.publish(event1)
        
        # Check which handlers received the event
        assert len(handler1.handled_events) == 1
        assert len(handler2.handled_events) == 0
        assert len(handler3.handled_events) == 1
        
        # Publish NODE_UPDATED event
        event2 = Event(type=EventType.NODE_UPDATED, source="test")
        event_bus.publish(event2)
        
        # Check handlers again
        assert len(handler1.handled_events) == 1  # Still 1
        assert len(handler2.handled_events) == 1  # Now 1
        assert len(handler3.handled_events) == 2  # Now 2
    
    def test_middleware_processing(self, event_bus):
        """Test middleware processing."""
        middleware = MockMiddleware()
        event_bus.add_middleware(middleware)
        
        handler = MockEventHandler("test_handler", [EventType.NODE_CREATED])
        event_bus.add_handler(handler)
        
        event = Event(type=EventType.NODE_CREATED, source="test")
        event_bus.publish(event)
        
        # Check middleware processed the event
        assert len(middleware.processed_events) == 1
        assert middleware.processed_events[0] == event
        
        # Check handler also received the event
        assert len(handler.handled_events) == 1
    
    def test_event_persistence(self, event_bus):
        """Test event persistence."""
        event1 = Event(type=EventType.NODE_CREATED, source="test1")
        event2 = Event(type=EventType.NODE_UPDATED, source="test2")
        
        event_bus.publish(event1)
        event_bus.publish(event2)
        
        # Check events were persisted
        stored_events = event_bus.persistence.get_events()
        assert len(stored_events) == 2
        assert stored_events[0].type == EventType.NODE_CREATED
        assert stored_events[1].type == EventType.NODE_UPDATED
    
    def test_get_stats(self, event_bus):
        """Test getting event bus statistics."""
        handler = MockEventHandler("test_handler", [EventType.NODE_CREATED])
        event_bus.add_handler(handler)
        
        callback = lambda e: None
        event_bus.subscribe(EventType.NODE_UPDATED, callback)
        
        stats = event_bus.get_stats()
        
        assert 'handlers' in stats
        assert 'handler_count' in stats
        assert 'middleware_count' in stats
        assert 'subscriber_counts' in stats
        assert 'total_subscribers' in stats
        assert 'persistence' in stats
        
        assert stats['handler_count'] == 1
        assert stats['total_subscribers'] == 1
        assert EventType.NODE_UPDATED.value in stats['subscriber_counts']


class TestEventPersistence:
    """Test cases for EventPersistence."""
    
    @pytest.fixture
    def persistence(self):
        """Create event persistence for testing."""
        return EventPersistence(max_events=100)
    
    def test_store_and_retrieve_events(self, persistence):
        """Test storing and retrieving events."""
        event1 = Event(type=EventType.NODE_CREATED, source="test1")
        event2 = Event(type=EventType.NODE_UPDATED, source="test2")
        
        persistence.store_event(event1)
        persistence.store_event(event2)
        
        events = persistence.get_events()
        assert len(events) == 2
        assert events[0] == event1
        assert events[1] == event2
    
    def test_filter_events_by_type(self, persistence):
        """Test filtering events by type."""
        event1 = Event(type=EventType.NODE_CREATED, source="test")
        event2 = Event(type=EventType.NODE_UPDATED, source="test")
        event3 = Event(type=EventType.NODE_CREATED, source="test")
        
        persistence.store_event(event1)
        persistence.store_event(event2)
        persistence.store_event(event3)
        
        created_events = persistence.get_events(event_type=EventType.NODE_CREATED)
        assert len(created_events) == 2
        assert all(e.type == EventType.NODE_CREATED for e in created_events)
    
    def test_filter_events_by_source(self, persistence):
        """Test filtering events by source."""
        event1 = Event(type=EventType.NODE_CREATED, source="source1")
        event2 = Event(type=EventType.NODE_CREATED, source="source2")
        event3 = Event(type=EventType.NODE_CREATED, source="source1")
        
        persistence.store_event(event1)
        persistence.store_event(event2)
        persistence.store_event(event3)
        
        source1_events = persistence.get_events(source="source1")
        assert len(source1_events) == 2
        assert all(e.source == "source1" for e in source1_events)
    
    def test_filter_events_by_time(self, persistence):
        """Test filtering events by time."""
        past_time = datetime.now() - timedelta(hours=1)
        
        event1 = Event(type=EventType.NODE_CREATED, source="test", timestamp=past_time)
        event2 = Event(type=EventType.NODE_CREATED, source="test")  # Current time
        
        persistence.store_event(event1)
        persistence.store_event(event2)
        
        recent_events = persistence.get_events(since=datetime.now() - timedelta(minutes=30))
        assert len(recent_events) == 1
        assert recent_events[0] == event2
    
    def test_limit_events(self, persistence):
        """Test limiting number of returned events."""
        for i in range(10):
            event = Event(type=EventType.NODE_CREATED, source=f"test{i}")
            persistence.store_event(event)
        
        limited_events = persistence.get_events(limit=5)
        assert len(limited_events) == 5
    
    def test_max_events_limit(self):
        """Test maximum events limit."""
        persistence = EventPersistence(max_events=3)
        
        for i in range(5):
            event = Event(type=EventType.NODE_CREATED, source=f"test{i}")
            persistence.store_event(event)
        
        events = persistence.get_events()
        assert len(events) == 3  # Should only keep last 3
        assert events[0].source == "test2"  # First stored should be test2
        assert events[2].source == "test4"  # Last stored should be test4


class TestMiddleware:
    """Test cases for middleware classes."""
    
    def test_logging_middleware(self):
        """Test logging middleware."""
        with patch('src.infrastructure.events.logging.getLogger') as mock_logger:
            mock_log_instance = Mock()
            mock_logger.return_value = mock_log_instance
            
            middleware = LoggingMiddleware()
            event = Event(type=EventType.NODE_CREATED, source="test", data={"key": "value"})
            
            next_called = False
            def next_handler(e):
                nonlocal next_called
                next_called = True
            
            middleware.process(event, next_handler)
            
            # Check that logging was called
            mock_log_instance.log.assert_called_once()
            assert next_called
    
    def test_performance_middleware(self):
        """Test performance middleware."""
        middleware = PerformanceMiddleware()
        event = Event(type=EventType.NODE_CREATED, source="test")
        
        next_called = False
        def next_handler(e):
            nonlocal next_called
            next_called = True
            time.sleep(0.01)  # Small delay
        
        middleware.process(event, next_handler)
        
        # Check that performance was tracked
        stats = middleware.get_stats()
        assert EventType.NODE_CREATED.value in stats
        assert stats[EventType.NODE_CREATED.value]['count'] == 1
        assert stats[EventType.NODE_CREATED.value]['avg_ms'] > 0
        assert next_called


class TestConvenienceFunctions:
    """Test cases for convenience functions."""
    
    def test_publish_event(self):
        """Test publish_event convenience function."""
        with patch('src.infrastructure.events.get_event_bus') as mock_get_bus:
            mock_bus = Mock()
            mock_get_bus.return_value = mock_bus
            
            publish_event(
                EventType.NODE_CREATED,
                source="test",
                data={"key": "value"},
                metadata={"meta": "data"}
            )
            
            # Check that publish was called on the bus
            mock_bus.publish.assert_called_once()
            
            # Check the event that was published
            published_event = mock_bus.publish.call_args[0][0]
            assert published_event.type == EventType.NODE_CREATED
            assert published_event.source == "test"
            assert published_event.data["key"] == "value"
            assert published_event.metadata["meta"] == "data"
    
    def test_subscribe_to_event(self):
        """Test subscribe_to_event convenience function."""
        with patch('src.infrastructure.events.get_event_bus') as mock_get_bus:
            mock_bus = Mock()
            mock_get_bus.return_value = mock_bus
            
            callback = lambda e: None
            subscribe_to_event(EventType.NODE_UPDATED, callback)
            
            # Check that subscribe was called on the bus
            mock_bus.subscribe.assert_called_once_with(EventType.NODE_UPDATED, callback)
    
    def test_create_node_event(self):
        """Test create_node_event convenience function."""
        event = create_node_event(
            node_id=123,
            action="created",
            source="test_service",
            node_data={"label": "Test Node"}
        )
        
        assert event.type == EventType.NODE_CREATED
        assert event.source == "test_service"
        assert event.data["node_id"] == 123
        assert event.data["action"] == "created"
        assert event.data["label"] == "Test Node"
        assert event.metadata["category"] == "node_operation"


class TestGlobalEventBus:
    """Test cases for global event bus functions."""
    
    def test_get_event_bus_singleton(self):
        """Test that get_event_bus returns singleton."""
        bus1 = get_event_bus()
        bus2 = get_event_bus()
        
        assert bus1 is bus2
        assert bus1 is not None


if __name__ == "__main__":
    pytest.main([__file__])