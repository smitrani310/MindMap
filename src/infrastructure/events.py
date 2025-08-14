"""
Event system infrastructure for the Enhanced Mind Map application.

This module provides a modern event-driven architecture with event bus,
handlers, middleware, and persistence capabilities.
"""

import logging
import threading
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Type, Union
from enum import Enum
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Standard event types for the mind map application."""
    
    # Node events
    NODE_CREATED = "node.created"
    NODE_UPDATED = "node.updated"
    NODE_DELETED = "node.deleted"
    NODE_MOVED = "node.moved"
    
    # Mind map events
    MINDMAP_LOADED = "mindmap.loaded"
    MINDMAP_SAVED = "mindmap.saved"
    MINDMAP_CLEARED = "mindmap.cleared"
    
    # UI events
    UI_NODE_SELECTED = "ui.node.selected"
    UI_NODE_DESELECTED = "ui.node.deselected"
    UI_ZOOM_CHANGED = "ui.zoom.changed"
    UI_PAN_CHANGED = "ui.pan.changed"
    
    # System events
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"
    SYSTEM_INFO = "system.info"
    
    # Cache events
    CACHE_HIT = "cache.hit"
    CACHE_MISS = "cache.miss"
    CACHE_INVALIDATED = "cache.invalidated"


@dataclass
class Event:
    """Represents an event in the system."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType = EventType.SYSTEM_INFO
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "unknown"
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation."""
        return {
            'id': self.id,
            'type': self.type.value,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'data': self.data,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create event from dictionary representation."""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            type=EventType(data.get('type', EventType.SYSTEM_INFO.value)),
            timestamp=datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat())),
            source=data.get('source', 'unknown'),
            data=data.get('data', {}),
            metadata=data.get('metadata', {})
        )


class EventHandler(ABC):
    """Abstract base class for event handlers."""
    
    @abstractmethod
    def can_handle(self, event: Event) -> bool:
        """Check if this handler can process the given event."""
        pass
    
    @abstractmethod
    def handle(self, event: Event) -> None:
        """Handle the given event."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the handler name."""
        pass


class EventMiddleware(ABC):
    """Abstract base class for event middleware."""
    
    @abstractmethod
    def process(self, event: Event, next_handler: Callable[[Event], None]) -> None:
        """Process the event and call the next handler in the chain."""
        pass


class LoggingMiddleware(EventMiddleware):
    """Middleware that logs all events."""
    
    def __init__(self, log_level: int = logging.INFO):
        self.log_level = log_level
        self.logger = logging.getLogger(f"{__name__}.LoggingMiddleware")
    
    def process(self, event: Event, next_handler: Callable[[Event], None]) -> None:
        """Log the event and continue processing."""
        self.logger.log(
            self.log_level,
            f"Event {event.type.value} from {event.source}: {event.data}"
        )
        next_handler(event)


class PerformanceMiddleware(EventMiddleware):
    """Middleware that tracks event processing performance."""
    
    def __init__(self):
        self.processing_times: Dict[str, List[float]] = defaultdict(list)
        self.lock = threading.RLock()
    
    def process(self, event: Event, next_handler: Callable[[Event], None]) -> None:
        """Track processing time and continue."""
        import time
        
        start_time = time.time()
        try:
            next_handler(event)
        finally:
            duration = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            with self.lock:
                self.processing_times[event.type.value].append(duration)
                # Keep only last 100 measurements
                if len(self.processing_times[event.type.value]) > 100:
                    self.processing_times[event.type.value].pop(0)
    
    def get_stats(self) -> Dict[str, Dict[str, float]]:
        """Get performance statistics for event processing."""
        stats = {}
        
        with self.lock:
            for event_type, times in self.processing_times.items():
                if times:
                    stats[event_type] = {
                        'count': len(times),
                        'avg_ms': sum(times) / len(times),
                        'min_ms': min(times),
                        'max_ms': max(times),
                        'total_ms': sum(times)
                    }
        
        return stats


class EventPersistence:
    """Handles persistence of events for debugging and replay."""
    
    def __init__(self, max_events: int = 10000):
        self.max_events = max_events
        self.events: deque = deque(maxlen=max_events)
        self.lock = threading.RLock()
    
    def store_event(self, event: Event) -> None:
        """Store an event for later retrieval."""
        with self.lock:
            self.events.append(event)
    
    def get_events(self, 
                   event_type: Optional[EventType] = None,
                   source: Optional[str] = None,
                   since: Optional[datetime] = None,
                   limit: Optional[int] = None) -> List[Event]:
        """Retrieve events based on filters."""
        with self.lock:
            filtered_events = []
            
            for event in self.events:
                # Apply filters
                if event_type and event.type != event_type:
                    continue
                if source and event.source != source:
                    continue
                if since and event.timestamp < since:
                    continue
                
                filtered_events.append(event)
                
                # Apply limit
                if limit and len(filtered_events) >= limit:
                    break
            
            return filtered_events
    
    def clear_events(self) -> None:
        """Clear all stored events."""
        with self.lock:
            self.events.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about stored events."""
        with self.lock:
            event_counts = defaultdict(int)
            source_counts = defaultdict(int)
            
            for event in self.events:
                event_counts[event.type.value] += 1
                source_counts[event.source] += 1
            
            return {
                'total_events': len(self.events),
                'max_events': self.max_events,
                'event_type_counts': dict(event_counts),
                'source_counts': dict(source_counts),
                'oldest_event': self.events[0].timestamp.isoformat() if self.events else None,
                'newest_event': self.events[-1].timestamp.isoformat() if self.events else None
            }


class EventBus:
    """Central event bus for publishing and subscribing to events."""
    
    def __init__(self, enable_persistence: bool = True):
        self.handlers: List[EventHandler] = []
        self.middleware: List[EventMiddleware] = []
        self.subscribers: Dict[EventType, List[Callable[[Event], None]]] = defaultdict(list)
        self.persistence = EventPersistence() if enable_persistence else None
        self.lock = threading.RLock()
        self.logger = logging.getLogger(f"{__name__}.EventBus")
        
        # Add default middleware
        self.add_middleware(LoggingMiddleware(logging.DEBUG))
        self.add_middleware(PerformanceMiddleware())
    
    def add_handler(self, handler: EventHandler) -> None:
        """Add an event handler to the bus."""
        with self.lock:
            self.handlers.append(handler)
            self.logger.info(f"Added event handler: {handler.name}")
    
    def remove_handler(self, handler: EventHandler) -> bool:
        """Remove an event handler from the bus."""
        with self.lock:
            if handler in self.handlers:
                self.handlers.remove(handler)
                self.logger.info(f"Removed event handler: {handler.name}")
                return True
            return False
    
    def add_middleware(self, middleware: EventMiddleware) -> None:
        """Add middleware to the event processing pipeline."""
        with self.lock:
            self.middleware.append(middleware)
            self.logger.info(f"Added event middleware: {middleware.__class__.__name__}")
    
    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """Subscribe to events of a specific type."""
        with self.lock:
            self.subscribers[event_type].append(callback)
            self.logger.info(f"Added subscriber for {event_type.value}")
    
    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> bool:
        """Unsubscribe from events of a specific type."""
        with self.lock:
            if callback in self.subscribers[event_type]:
                self.subscribers[event_type].remove(callback)
                self.logger.info(f"Removed subscriber for {event_type.value}")
                return True
            return False
    
    def publish(self, event: Event) -> None:
        """Publish an event to all interested handlers and subscribers."""
        with self.lock:
            # Store event for persistence if enabled
            if self.persistence:
                self.persistence.store_event(event)
            
            # Process through middleware chain
            self._process_with_middleware(event, 0)
    
    def _process_with_middleware(self, event: Event, middleware_index: int) -> None:
        """Process event through middleware chain."""
        if middleware_index >= len(self.middleware):
            # End of middleware chain, process the event
            self._process_event(event)
            return
        
        # Get current middleware and process
        current_middleware = self.middleware[middleware_index]
        next_handler = lambda e: self._process_with_middleware(e, middleware_index + 1)
        
        try:
            current_middleware.process(event, next_handler)
        except Exception as e:
            self.logger.error(f"Error in middleware {current_middleware.__class__.__name__}: {e}")
            # Continue with next middleware
            self._process_with_middleware(event, middleware_index + 1)
    
    def _process_event(self, event: Event) -> None:
        """Process the event with handlers and subscribers."""
        # Process with registered handlers
        for handler in self.handlers:
            try:
                if handler.can_handle(event):
                    handler.handle(event)
            except Exception as e:
                self.logger.error(f"Error in handler {handler.name}: {e}")
        
        # Process with subscribers
        for callback in self.subscribers[event.type]:
            try:
                callback(event)
            except Exception as e:
                self.logger.error(f"Error in subscriber callback: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the event bus."""
        with self.lock:
            handler_names = [h.name for h in self.handlers]
            subscriber_counts = {et.value: len(callbacks) for et, callbacks in self.subscribers.items()}
            
            stats = {
                'handlers': handler_names,
                'handler_count': len(self.handlers),
                'middleware_count': len(self.middleware),
                'subscriber_counts': subscriber_counts,
                'total_subscribers': sum(subscriber_counts.values())
            }
            
            # Add persistence stats if available
            if self.persistence:
                stats['persistence'] = self.persistence.get_stats()
            
            # Add performance stats from middleware
            for middleware in self.middleware:
                if isinstance(middleware, PerformanceMiddleware):
                    stats['performance'] = middleware.get_stats()
                    break
            
            return stats
    
    def replay_events(self, 
                     event_type: Optional[EventType] = None,
                     source: Optional[str] = None,
                     since: Optional[datetime] = None) -> int:
        """Replay stored events matching the criteria."""
        if not self.persistence:
            self.logger.warning("Event persistence is not enabled, cannot replay events")
            return 0
        
        events_to_replay = self.persistence.get_events(event_type, source, since)
        
        self.logger.info(f"Replaying {len(events_to_replay)} events")
        
        for event in events_to_replay:
            # Create a new event with updated timestamp to avoid confusion
            replay_event = Event(
                id=str(uuid.uuid4()),
                type=event.type,
                timestamp=datetime.now(),
                source=f"replay:{event.source}",
                data=event.data.copy(),
                metadata={**event.metadata, 'original_id': event.id, 'replayed': True}
            )
            
            self._process_event(replay_event)  # Skip middleware for replay
        
        return len(events_to_replay)


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def publish_event(event_type: EventType, source: str, data: Dict[str, Any] = None, metadata: Dict[str, Any] = None) -> None:
    """Convenience function to publish an event."""
    event = Event(
        type=event_type,
        source=source,
        data=data or {},
        metadata=metadata or {}
    )
    get_event_bus().publish(event)


def subscribe_to_event(event_type: EventType, callback: Callable[[Event], None]) -> None:
    """Convenience function to subscribe to an event type."""
    get_event_bus().subscribe(event_type, callback)


def create_node_event(node_id: int, action: str, source: str, node_data: Dict[str, Any] = None) -> Event:
    """Create a node-related event."""
    event_type_map = {
        'created': EventType.NODE_CREATED,
        'updated': EventType.NODE_UPDATED,
        'deleted': EventType.NODE_DELETED,
        'moved': EventType.NODE_MOVED
    }
    
    event_type = event_type_map.get(action, EventType.SYSTEM_INFO)
    
    return Event(
        type=event_type,
        source=source,
        data={
            'node_id': node_id,
            'action': action,
            **(node_data or {})
        },
        metadata={
            'category': 'node_operation'
        }
    )