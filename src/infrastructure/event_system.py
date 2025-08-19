"""
Modern event system foundation for the Enhanced Mind Map application.

This module provides a comprehensive event-driven architecture with:
- Strongly typed events
- Event bus with subscription management
- Middleware pipeline for event processing
- Event persistence for audit trails
- Async/sync event handling support
"""

import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Union, Type, Set
from concurrent.futures import ThreadPoolExecutor
import json
import threading
from pathlib import Path


class EventType(str, Enum):
    """Standard event types for the mind map application."""
    
    # Node events
    NODE_CREATED = "node.created"
    NODE_UPDATED = "node.updated"
    NODE_DELETED = "node.deleted"
    NODE_MOVED = "node.moved"
    NODE_PARENT_CHANGED = "node.parent_changed"
    
    # UI events
    UI_NODE_SELECTED = "ui.node_selected"
    UI_NODE_DESELECTED = "ui.node_deselected"
    UI_ZOOM_CHANGED = "ui.zoom_changed"
    UI_VIEW_CHANGED = "ui.view_changed"
    UI_FILTER_APPLIED = "ui.filter_applied"
    
    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"
    
    # Data events
    DATA_LOADED = "data.loaded"
    DATA_SAVED = "data.saved"
    DATA_BACKUP_CREATED = "data.backup_created"
    DATA_RESTORED = "data.restored"
    
    # Cache events
    CACHE_HIT = "cache.hit"
    CACHE_MISS = "cache.miss"
    CACHE_INVALIDATED = "cache.invalidated"
    CACHE_CLEARED = "cache.cleared"
    
    # Performance events
    PERFORMANCE_SLOW_OPERATION = "performance.slow_operation"
    PERFORMANCE_THRESHOLD_EXCEEDED = "performance.threshold_exceeded"
    
    # User events
    USER_ACTION = "user.action"
    USER_SESSION_STARTED = "user.session_started"
    USER_SESSION_ENDED = "user.session_ended"


class EventPriority(int, Enum):
    """Event priority levels for processing order."""
    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


@dataclass
class EventMetadata:
    """Metadata associated with an event."""
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    source_component: Optional[str] = None
    tags: Set[str] = field(default_factory=set)
    custom_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            'correlation_id': self.correlation_id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'request_id': self.request_id,
            'source_component': self.source_component,
            'tags': list(self.tags),
            'custom_data': self.custom_data
        }


@dataclass
class Event:
    """Base event class with comprehensive metadata and typing."""
    
    event_type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: EventMetadata = field(default_factory=EventMetadata)
    priority: EventPriority = EventPriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.now)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'data': self.data,
            'metadata': self.metadata.to_dict(),
            'priority': self.priority.value,
            'timestamp': self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create event from dictionary."""
        metadata_dict = data.get('metadata', {})
        metadata = EventMetadata(
            correlation_id=metadata_dict.get('correlation_id', str(uuid.uuid4())[:8]),
            user_id=metadata_dict.get('user_id'),
            session_id=metadata_dict.get('session_id'),
            request_id=metadata_dict.get('request_id'),
            source_component=metadata_dict.get('source_component'),
            tags=set(metadata_dict.get('tags', [])),
            custom_data=metadata_dict.get('custom_data', {})
        )
        
        return cls(
            event_id=data.get('event_id', str(uuid.uuid4())),
            event_type=EventType(data['event_type']),
            data=data.get('data', {}),
            metadata=metadata,
            priority=EventPriority(data.get('priority', EventPriority.NORMAL.value)),
            timestamp=datetime.fromisoformat(data['timestamp']) if 'timestamp' in data else datetime.now()
        )
    
    def add_tag(self, tag: str) -> 'Event':
        """Add a tag to the event metadata."""
        self.metadata.tags.add(tag)
        return self
    
    def set_source(self, component: str) -> 'Event':
        """Set the source component for the event."""
        self.metadata.source_component = component
        return self
    
    def set_user_context(self, user_id: str, session_id: Optional[str] = None) -> 'Event':
        """Set user context for the event."""
        self.metadata.user_id = user_id
        if session_id:
            self.metadata.session_id = session_id
        return self


# Event handler type definitions
EventHandler = Callable[[Event], None]
AsyncEventHandler = Callable[[Event], asyncio.Future]
EventHandlerUnion = Union[EventHandler, AsyncEventHandler]


class EventMiddleware(ABC):
    """Abstract base class for event middleware."""
    
    @abstractmethod
    def process(self, event: Event, next_handler: Callable[[Event], None]) -> None:
        """Process the event and call the next handler in the pipeline."""
        pass


class LoggingMiddleware(EventMiddleware):
    """Middleware that logs all events."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def process(self, event: Event, next_handler: Callable[[Event], None]) -> None:
        """Log the event and continue processing."""
        self.logger.info(
            f"Event processed: {event.event_type.value}",
            extra={
                'event_id': event.event_id,
                'event_type': event.event_type.value,
                'correlation_id': event.metadata.correlation_id,
                'source_component': event.metadata.source_component,
                'priority': event.priority.value,
                'data_keys': list(event.data.keys())
            }
        )
        next_handler(event)


class ValidationMiddleware(EventMiddleware):
    """Middleware that validates events before processing."""
    
    def __init__(self, validators: Optional[Dict[EventType, Callable[[Event], bool]]] = None):
        self.validators = validators or {}
    
    def process(self, event: Event, next_handler: Callable[[Event], None]) -> None:
        """Validate the event and continue processing if valid."""
        validator = self.validators.get(event.event_type)
        if validator and not validator(event):
            raise ValueError(f"Event validation failed for {event.event_type.value}")
        
        next_handler(event)
    
    def add_validator(self, event_type: EventType, validator: Callable[[Event], bool]) -> None:
        """Add a validator for a specific event type."""
        self.validators[event_type] = validator


class MetricsMiddleware(EventMiddleware):
    """Middleware that collects event metrics."""
    
    def __init__(self):
        self.event_counts: Dict[str, int] = {}
        self.processing_times: Dict[str, List[float]] = {}
        self._lock = threading.Lock()
    
    def process(self, event: Event, next_handler: Callable[[Event], None]) -> None:
        """Collect metrics and continue processing."""
        start_time = datetime.now()
        
        # Update event count
        with self._lock:
            event_type = event.event_type.value
            self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
        
        try:
            next_handler(event)
        finally:
            # Record processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            with self._lock:
                if event_type not in self.processing_times:
                    self.processing_times[event_type] = []
                self.processing_times[event_type].append(processing_time)
                
                # Keep only last 100 measurements
                if len(self.processing_times[event_type]) > 100:
                    self.processing_times[event_type] = self.processing_times[event_type][-100:]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics."""
        with self._lock:
            metrics = {
                'event_counts': self.event_counts.copy(),
                'processing_times': {}
            }
            
            for event_type, times in self.processing_times.items():
                if times:
                    metrics['processing_times'][event_type] = {
                        'count': len(times),
                        'avg_ms': sum(times) / len(times),
                        'min_ms': min(times),
                        'max_ms': max(times)
                    }
            
            return metrics


class EventPersistence:
    """Event persistence system for audit trails."""
    
    def __init__(self, storage_path: str = "events.jsonl"):
        self.storage_path = Path(storage_path)
        self._lock = threading.Lock()
        
        # Ensure storage directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
    
    def persist_event(self, event: Event) -> None:
        """Persist an event to storage."""
        with self._lock:
            with open(self.storage_path, 'a', encoding='utf-8') as f:
                json.dump(event.to_dict(), f, ensure_ascii=False)
                f.write('\n')
    
    def load_events(self, limit: Optional[int] = None, event_type: Optional[EventType] = None) -> List[Event]:
        """Load events from storage."""
        events = []
        
        if not self.storage_path.exists():
            return events
        
        with open(self.storage_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                
                try:
                    event_data = json.loads(line)
                    event = Event.from_dict(event_data)
                    
                    if event_type is None or event.event_type == event_type:
                        events.append(event)
                        
                        if limit and len(events) >= limit:
                            break
                            
                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    logging.getLogger(__name__).warning(f"Failed to parse event: {e}")
                    continue
        
        return events
    
    def clear_events(self) -> None:
        """Clear all persisted events."""
        with self._lock:
            if self.storage_path.exists():
                self.storage_path.unlink()


class EventSubscription:
    """Represents a subscription to events."""
    
    def __init__(
        self,
        handler: EventHandlerUnion,
        event_types: Set[EventType],
        subscription_id: str,
        priority: int = 0,
        tags: Optional[Set[str]] = None,
        condition: Optional[Callable[[Event], bool]] = None
    ):
        self.handler = handler
        self.event_types = event_types
        self.subscription_id = subscription_id
        self.priority = priority
        self.tags = tags or set()
        self.condition = condition
        self.created_at = datetime.now()
        self.call_count = 0
        self.last_called = None
    
    def matches(self, event: Event) -> bool:
        """Check if this subscription matches the given event."""
        # Check event type
        if event.event_type not in self.event_types:
            return False
        
        # Check tags if specified
        if self.tags and not self.tags.intersection(event.metadata.tags):
            return False
        
        # Check custom condition if specified
        if self.condition and not self.condition(event):
            return False
        
        return True
    
    def call_handler(self, event: Event) -> None:
        """Call the event handler."""
        self.call_count += 1
        self.last_called = datetime.now()
        
        if asyncio.iscoroutinefunction(self.handler):
            # Handle async handlers
            loop = None
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            if loop.is_running():
                # If loop is already running, schedule the coroutine
                asyncio.create_task(self.handler(event))
            else:
                # Run the coroutine
                loop.run_until_complete(self.handler(event))
        else:
            # Handle sync handlers
            self.handler(event)


class EventBus:
    """Central event bus for managing event subscriptions and publishing."""
    
    def __init__(self, enable_persistence: bool = True, storage_path: str = "events.jsonl"):
        self.subscriptions: Dict[str, EventSubscription] = {}
        self.middleware: List[EventMiddleware] = []
        self.persistence = EventPersistence(storage_path) if enable_persistence else None
        self.logger = logging.getLogger(__name__)
        self._lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="EventBus")
        
        # Add default middleware
        self.add_middleware(LoggingMiddleware(self.logger))
        self.add_middleware(MetricsMiddleware())
    
    def add_middleware(self, middleware: EventMiddleware) -> None:
        """Add middleware to the processing pipeline."""
        with self._lock:
            self.middleware.append(middleware)
    
    def subscribe(
        self,
        event_types: Union[EventType, List[EventType], Set[EventType]],
        handler: EventHandlerUnion,
        subscription_id: Optional[str] = None,
        priority: int = 0,
        tags: Optional[Set[str]] = None,
        condition: Optional[Callable[[Event], bool]] = None
    ) -> str:
        """Subscribe to events."""
        if isinstance(event_types, EventType):
            event_types = {event_types}
        elif isinstance(event_types, list):
            event_types = set(event_types)
        
        subscription_id = subscription_id or str(uuid.uuid4())
        
        subscription = EventSubscription(
            handler=handler,
            event_types=event_types,
            subscription_id=subscription_id,
            priority=priority,
            tags=tags,
            condition=condition
        )
        
        with self._lock:
            self.subscriptions[subscription_id] = subscription
        
        self.logger.info(
            f"Subscribed to events: {[et.value for et in event_types]}",
            extra={
                'subscription_id': subscription_id,
                'event_types': [et.value for et in event_types],
                'priority': priority,
                'tags': list(tags) if tags else []
            }
        )
        
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events."""
        with self._lock:
            if subscription_id in self.subscriptions:
                del self.subscriptions[subscription_id]
                self.logger.info(f"Unsubscribed: {subscription_id}")
                return True
            return False
    
    def publish(self, event: Event, async_processing: bool = False) -> None:
        """Publish an event to all matching subscribers."""
        # Persist event if enabled
        if self.persistence:
            try:
                self.persistence.persist_event(event)
            except Exception as e:
                self.logger.error(f"Failed to persist event {event.event_id}: {e}")
        
        # Process event through middleware and deliver to subscribers
        if async_processing:
            self.executor.submit(self._process_event, event)
        else:
            self._process_event(event)
    
    def _process_event(self, event: Event) -> None:
        """Process event through middleware pipeline and deliver to subscribers."""
        try:
            # Build middleware chain
            def deliver_to_subscribers(evt: Event) -> None:
                self._deliver_to_subscribers(evt)
            
            # Create middleware chain
            handler = deliver_to_subscribers
            for middleware in reversed(self.middleware):
                current_handler = handler
                handler = lambda evt, mw=middleware, next_h=current_handler: mw.process(evt, next_h)
            
            # Execute the chain
            handler(event)
            
        except Exception as e:
            self.logger.error(
                f"Error processing event {event.event_id}: {e}",
                extra={
                    'event_id': event.event_id,
                    'event_type': event.event_type.value,
                    'error': str(e)
                },
                exc_info=True
            )
    
    def _deliver_to_subscribers(self, event: Event) -> None:
        """Deliver event to matching subscribers."""
        matching_subscriptions = []
        
        with self._lock:
            for subscription in self.subscriptions.values():
                if subscription.matches(event):
                    matching_subscriptions.append(subscription)
        
        # Sort by priority (higher priority first)
        matching_subscriptions.sort(key=lambda s: s.priority, reverse=True)
        
        # Deliver to subscribers
        for subscription in matching_subscriptions:
            try:
                subscription.call_handler(event)
            except Exception as e:
                self.logger.error(
                    f"Error in event handler {subscription.subscription_id}: {e}",
                    extra={
                        'subscription_id': subscription.subscription_id,
                        'event_id': event.event_id,
                        'event_type': event.event_type.value,
                        'error': str(e)
                    },
                    exc_info=True
                )
    
    def get_subscription_stats(self) -> Dict[str, Any]:
        """Get statistics about subscriptions."""
        with self._lock:
            stats = {
                'total_subscriptions': len(self.subscriptions),
                'subscriptions_by_type': {},
                'subscription_details': []
            }
            
            for subscription in self.subscriptions.values():
                for event_type in subscription.event_types:
                    type_name = event_type.value
                    if type_name not in stats['subscriptions_by_type']:
                        stats['subscriptions_by_type'][type_name] = 0
                    stats['subscriptions_by_type'][type_name] += 1
                
                stats['subscription_details'].append({
                    'subscription_id': subscription.subscription_id,
                    'event_types': [et.value for et in subscription.event_types],
                    'priority': subscription.priority,
                    'call_count': subscription.call_count,
                    'last_called': subscription.last_called.isoformat() if subscription.last_called else None,
                    'created_at': subscription.created_at.isoformat()
                })
            
            return stats
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get event processing metrics."""
        metrics = {'middleware_metrics': {}}
        
        for i, middleware in enumerate(self.middleware):
            if hasattr(middleware, 'get_metrics'):
                metrics['middleware_metrics'][f'{type(middleware).__name__}_{i}'] = middleware.get_metrics()
        
        return metrics
    
    def shutdown(self) -> None:
        """Shutdown the event bus."""
        self.logger.info("Shutting down event bus")
        self.executor.shutdown(wait=True)
        
        with self._lock:
            self.subscriptions.clear()


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def publish_event(
    event_type: EventType,
    data: Optional[Dict[str, Any]] = None,
    metadata: Optional[EventMetadata] = None,
    priority: EventPriority = EventPriority.NORMAL,
    async_processing: bool = False
) -> str:
    """Convenience function to publish an event."""
    event = Event(
        event_type=event_type,
        data=data or {},
        metadata=metadata or EventMetadata(),
        priority=priority
    )
    
    get_event_bus().publish(event, async_processing=async_processing)
    return event.event_id


def subscribe_to_events(
    event_types: Union[EventType, List[EventType]],
    handler: EventHandlerUnion,
    **kwargs
) -> str:
    """Convenience function to subscribe to events."""
    return get_event_bus().subscribe(event_types, handler, **kwargs)


def unsubscribe_from_events(subscription_id: str) -> bool:
    """Convenience function to unsubscribe from events."""
    return get_event_bus().unsubscribe(subscription_id)


# Decorator for event handlers
def event_handler(
    event_types: Union[EventType, List[EventType]],
    priority: int = 0,
    tags: Optional[Set[str]] = None,
    condition: Optional[Callable[[Event], bool]] = None
):
    """Decorator to register a function as an event handler."""
    def decorator(func: EventHandlerUnion) -> EventHandlerUnion:
        subscription_id = subscribe_to_events(
            event_types=event_types,
            handler=func,
            priority=priority,
            tags=tags,
            condition=condition
        )
        
        # Store subscription ID on the function for later unsubscription
        func._event_subscription_id = subscription_id
        return func
    
    return decorator