"""UI Communication system for the Enhanced Mind Map application."""

import json
import logging
import threading
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Union
from enum import Enum
from dataclasses import dataclass, asdict
from queue import Queue, Empty
import asyncio
from concurrent.futures import ThreadPoolExecutor


class CommunicationChannel(Enum):
    """Communication channels for UI messages."""
    NODE_DATA = "node_data"
    UI_STATE = "ui_state"
    SYSTEM_STATUS = "system_status"
    NOTIFICATIONS = "notifications"
    EVENTS = "events"
    USER_ACTIONS = "user_actions"


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = 1
    NORMAL = 10
    CRITICAL = 20
    HIGH = 30
    URGENT = 40


@dataclass
class UIMessage:
    """Represents a message in the UI communication system."""
    channel: CommunicationChannel
    message_type: str
    data: Optional[Dict[str, Any]] = None
    priority: MessagePriority = MessagePriority.NORMAL
    message_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    source_component: Optional[str] = None
    requires_acknowledgment: bool = False
    max_retries: int = 3
    retry_count: int = 0
    
    def __post_init__(self):
        if self.message_id is None:
            self.message_id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.data is None:
            self.data = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        result = {
            'message_id': self.message_id,
            'channel': self.channel.value,
            'message_type': self.message_type,
            'data': self.data,
            'priority': self.priority.value,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'source_component': self.source_component,
            'requires_acknowledgment': self.requires_acknowledgment,
            'max_retries': self.max_retries,
            'retry_count': self.retry_count
        }
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UIMessage':
        """Create message from dictionary."""
        data = data.copy()
        data['channel'] = CommunicationChannel(data['channel'])
        data['priority'] = MessagePriority(data['priority'])
        if data.get('timestamp'):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)
    
    def to_json(self) -> str:
        """Convert message to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'UIMessage':
        """Create message from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


class MessageHandler(ABC):
    """Abstract base class for UI message handlers."""
    
    def __init__(self, channels: Optional[List[CommunicationChannel]] = None):
        self.channels = channels or []
        self.handled_messages = []
        self.should_fail = False
    
    def can_handle(self, message: UIMessage) -> bool:
        """Check if this handler can process the message."""
        if not self.channels:
            return True
        return message.channel in self.channels
    
    @abstractmethod
    def handle(self, message: UIMessage) -> Optional[UIMessage]:
        """Handle the message and optionally return a response."""
        pass
    
    def get_priority(self) -> int:
        """Get handler priority (higher numbers = higher priority)."""
        return 10


class UICommunicationBus:
    """Central message bus for UI communication."""
    
    def __init__(self):
        self.message_handlers: Dict[str, MessageHandler] = {}
        self.message_history: List[UIMessage] = []
        self.pending_acknowledgments: Dict[str, UIMessage] = {}
        self.delivery_stats = {
            'messages_sent': 0,
            'messages_delivered': 0,
            'messages_failed': 0,
            'acknowledgments_received': 0
        }
        self.logger = logging.getLogger(__name__)
        self._lock = threading.RLock()
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self.message_queue: Queue = Queue()
    
    def start(self) -> None:
        """Start the message processing worker."""
        if self._running:
            return
        
        self._running = True
        self._worker_thread = threading.Thread(target=self._process_messages, daemon=True)
        self._worker_thread.start()
        self.logger.info("UI communication bus started")
    
    def stop(self) -> None:
        """Stop the message processing worker."""
        self._running = False
        
        if self._worker_thread:
            self._worker_thread.join(timeout=5.0)
        
        self.logger.info("UI communication bus stopped")
    
    def send_message(self, message: UIMessage) -> bool:
        """Send a message through the bus."""
        try:
            with self._lock:
                self.message_history.append(message)
                self.delivery_stats['messages_sent'] += 1
                
                # Handle acknowledgment requirement
                if message.requires_acknowledgment:
                    self.pending_acknowledgments[message.message_id] = message
            
            if self._running:
                self.message_queue.put(message, timeout=1.0)
            else:
                # Process immediately if not running (for testing)
                self._handle_message(message)
            
            self.logger.debug(f"Sent message: {message.message_type} (ID: {message.message_id})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            with self._lock:
                self.delivery_stats['messages_failed'] += 1
            return False
    
    def register_handler(self, name: str, handler: MessageHandler) -> None:
        """Register a message handler."""
        with self._lock:
            self.message_handlers[name] = handler
        self.logger.info(f"Registered UI message handler: {name}")
    
    def unregister_handler(self, name: str) -> None:
        """Unregister a message handler."""
        with self._lock:
            if name in self.message_handlers:
                del self.message_handlers[name]
        self.logger.info(f"Unregistered UI message handler: {name}")
    
    def acknowledge_message(self, message_id: str) -> bool:
        """Acknowledge receipt of a message."""
        with self._lock:
            if message_id in self.pending_acknowledgments:
                del self.pending_acknowledgments[message_id]
                self.delivery_stats['acknowledgments_received'] += 1
                self.logger.debug(f"Acknowledged message: {message_id}")
                return True
            return False
    
    def get_message_history(self, channel: Optional[CommunicationChannel] = None, 
                          limit: Optional[int] = None) -> List[UIMessage]:
        """Get message history, optionally filtered by channel."""
        with self._lock:
            history = self.message_history
            
            if channel:
                history = [msg for msg in history if msg.channel == channel]
            
            if limit:
                history = history[-limit:]
            
            return history.copy()
    
    def replay_messages(self, channel: Optional[CommunicationChannel] = None,
                       since: Optional[datetime] = None) -> int:
        """Replay messages from history."""
        messages_to_replay = self.get_message_history(channel)
        
        if since:
            messages_to_replay = [
                msg for msg in messages_to_replay 
                if msg.timestamp and msg.timestamp >= since
            ]
        
        replayed_count = 0
        for original_message in messages_to_replay:
            # Create a replay message
            replay_message = UIMessage(
                channel=original_message.channel,
                message_type=f"replay_{original_message.message_type}",
                data=original_message.data,
                priority=original_message.priority,
                source_component="replay_system"
            )
            
            if self.send_message(replay_message):
                replayed_count += 1
        
        return replayed_count
    
    def get_delivery_stats(self) -> Dict[str, Any]:
        """Get delivery statistics."""
        with self._lock:
            stats = self.delivery_stats.copy()
            stats['registered_handlers'] = len(self.message_handlers)
            stats['pending_acknowledgments'] = len(self.pending_acknowledgments)
            stats['message_history_size'] = len(self.message_history)
            return stats
    
    def _process_messages(self) -> None:
        """Process messages in the queue."""
        while self._running:
            try:
                message = self.message_queue.get(timeout=0.1)
                self._handle_message(message)
                
            except Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error processing message: {e}", exc_info=True)
                with self._lock:
                    self.delivery_stats['messages_failed'] += 1
    
    def _handle_message(self, message: UIMessage) -> bool:
        """Handle a single message."""
        try:
            self.logger.debug(f"Processing message: {message.message_type} (ID: {message.message_id})")
            
            # Find appropriate handlers
            handlers_found = False
            for name, handler in self.message_handlers.items():
                if handler.can_handle(message):
                    handlers_found = True
                    try:
                        if handler.should_fail:
                            raise Exception("Handler configured to fail")
                        
                        # Call the handler's handle method
                        response = handler.handle(message)
                        
                        with self._lock:
                            self.delivery_stats['messages_delivered'] += 1
                        
                        if response:
                            self.send_message(response)
                            
                    except Exception as e:
                        self.logger.error(f"Handler {name} failed: {e}")
                        with self._lock:
                            self.delivery_stats['messages_failed'] += 1
                        
                        # Handle retry logic
                        if message.retry_count < message.max_retries:
                            message.retry_count += 1
                            self.logger.info(f"Retrying message {message.message_id}, attempt {message.retry_count}")
                            time.sleep(0.1 * message.retry_count)  # Exponential backoff
                            self.message_queue.put(message)
            
            if not handlers_found:
                self.logger.warning(f"No handler found for message: {message.message_type}")
                with self._lock:
                    self.delivery_stats['messages_failed'] += 1
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error handling message {message.message_id}: {e}", exc_info=True)
            with self._lock:
                self.delivery_stats['messages_failed'] += 1
            return False


# Global communication bus instance
_communication_bus: Optional[UICommunicationBus] = None


def get_ui_communication_bus() -> UICommunicationBus:
    """Get the global UI communication bus."""
    global _communication_bus
    if _communication_bus is None:
        _communication_bus = UICommunicationBus()
    return _communication_bus


def send_ui_message(
    channel: CommunicationChannel,
    message_type: str,
    data: Optional[Dict[str, Any]] = None,
    priority: MessagePriority = MessagePriority.NORMAL,
    source_component: Optional[str] = None,
    requires_acknowledgment: bool = False
) -> str:
    """Send a UI message through the communication bus."""
    message = UIMessage(
        channel=channel,
        message_type=message_type,
        data=data,
        priority=priority,
        source_component=source_component,
        requires_acknowledgment=requires_acknowledgment
    )
    
    bus = get_ui_communication_bus()
    bus.send_message(message)
    return message.message_id


def start_ui_communication() -> None:
    """Start the UI communication system."""
    bus = get_ui_communication_bus()
    bus.start()


def stop_ui_communication() -> None:
    """Stop the UI communication system."""
    bus = get_ui_communication_bus()
    bus.stop()


# Utility functions for common UI operations
def notify_node_created(node_id: str, node_data: Dict[str, Any]) -> str:
    """Send notification about node creation."""
    return send_ui_message(
        CommunicationChannel.NODE_DATA,
        "node_created",
        {'node_id': node_id, 'node_data': node_data},
        MessagePriority.NORMAL
    )


def notify_node_updated(node_id: str, changes: Dict[str, Any]) -> str:
    """Send notification about node update."""
    return send_ui_message(
        CommunicationChannel.NODE_DATA,
        "node_updated",
        {'node_id': node_id, 'changes': changes},
        MessagePriority.NORMAL
    )


def notify_node_deleted(node_id: str) -> str:
    """Send notification about node deletion."""
    return send_ui_message(
        CommunicationChannel.NODE_DATA,
        "node_deleted",
        {'node_id': node_id},
        MessagePriority.NORMAL
    )


def notify_error(error_message: str, error_details: Optional[Dict[str, Any]] = None) -> str:
    """Send error notification."""
    return send_ui_message(
        CommunicationChannel.SYSTEM_STATUS,
        "error_occurred",
        {'message': error_message, 'details': error_details or {}},
        MessagePriority.URGENT
    )


def request_ui_refresh(component: Optional[str] = None) -> str:
    """Request UI refresh."""
    return send_ui_message(
        CommunicationChannel.UI_STATE,
        "refresh_ui",
        {'component': component},
        MessagePriority.HIGH
    )


def update_ui_status(status: str, details: Optional[Dict[str, Any]] = None) -> str:
    """Update UI status."""
    return send_ui_message(
        CommunicationChannel.SYSTEM_STATUS,
        "status_update",
        {'status': status, 'details': details or {}},
        MessagePriority.NORMAL
    )
