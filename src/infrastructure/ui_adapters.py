"""
UI adapters for different communication mechanisms.

This module provides adapters for different UI communication methods,
including Streamlit session state, WebSocket simulation, and direct updates.
"""

import json
import logging
import threading
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime

from src.infrastructure.ui_communication import (
    UIMessage, MessageHandler, CommunicationChannel, MessagePriority
)


class UIAdapter(ABC):
    """Abstract base class for UI adapters."""
    
    @abstractmethod
    def send_to_ui(self, message: UIMessage) -> bool:
        """Send message to the UI."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this adapter is available."""
        pass


class StreamlitSessionAdapter(UIAdapter):
    """Adapter for Streamlit session state communication."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._session_state = None
        self._lock = threading.Lock()
    
    def set_session_state(self, session_state) -> None:
        """Set the Streamlit session state object."""
        with self._lock:
            self._session_state = session_state
    
    def send_to_ui(self, message: UIMessage) -> bool:
        """Send message to UI via Streamlit session state."""
        if not self.is_available():
            return False
        
        try:
            with self._lock:
                # Initialize message queue in session state if needed
                if 'ui_messages' not in self._session_state:
                    self._session_state.ui_messages = []
                
                # Add message to queue
                self._session_state.ui_messages.append(message.to_dict())
                
                # Keep only last 100 messages
                if len(self._session_state.ui_messages) > 100:
                    self._session_state.ui_messages = self._session_state.ui_messages[-100:]
                
                # Set update flags based on channel
                if message.channel == CommunicationChannel.NODE_DATA:
                    self._session_state.nodes_updated = True
                elif message.channel == CommunicationChannel.UI_STATE:
                    self._session_state.ui_state_updated = True
                elif message.channel == CommunicationChannel.SYSTEM_STATUS:
                    self._session_state.system_status_updated = True
                
                self.logger.debug(f"Message sent to Streamlit session: {message.message_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to send message to Streamlit session: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if Streamlit session state is available."""
        return self._session_state is not None
    
    def get_messages(self, channel: Optional[CommunicationChannel] = None) -> List[Dict[str, Any]]:
        """Get messages from session state."""
        if not self.is_available():
            return []
        
        try:
            with self._lock:
                messages = self._session_state.get('ui_messages', [])
                
                if channel:
                    messages = [m for m in messages if m.get('channel') == channel.value]
                
                return messages
                
        except Exception as e:
            self.logger.error(f"Failed to get messages from session: {e}")
            return []
    
    def clear_messages(self, channel: Optional[CommunicationChannel] = None) -> None:
        """Clear messages from session state."""
        if not self.is_available():
            return
        
        try:
            with self._lock:
                if channel:
                    # Remove messages for specific channel
                    messages = self._session_state.get('ui_messages', [])
                    self._session_state.ui_messages = [
                        m for m in messages if m.get('channel') != channel.value
                    ]
                else:
                    # Clear all messages
                    self._session_state.ui_messages = []
                
        except Exception as e:
            self.logger.error(f"Failed to clear messages from session: {e}")


class WebSocketSimulatorAdapter(UIAdapter):
    """Adapter that simulates WebSocket communication for testing."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.connected_clients: Dict[str, Callable[[UIMessage], None]] = {}
        self.message_buffer: List[UIMessage] = []
        self._lock = threading.Lock()
    
    def connect_client(self, client_id: str, callback: Callable[[UIMessage], None]) -> None:
        """Connect a client with a callback function."""
        with self._lock:
            self.connected_clients[client_id] = callback
            self.logger.info(f"WebSocket client connected: {client_id}")
    
    def disconnect_client(self, client_id: str) -> None:
        """Disconnect a client."""
        with self._lock:
            if client_id in self.connected_clients:
                del self.connected_clients[client_id]
                self.logger.info(f"WebSocket client disconnected: {client_id}")
    
    def send_to_ui(self, message: UIMessage) -> bool:
        """Send message to all connected clients."""
        if not self.is_available():
            # Buffer message if no clients connected
            with self._lock:
                self.message_buffer.append(message)
                # Keep only last 50 buffered messages
                if len(self.message_buffer) > 50:
                    self.message_buffer = self.message_buffer[-50:]
            return True
        
        success_count = 0
        failed_clients = []
        
        with self._lock:
            for client_id, callback in self.connected_clients.items():
                try:
                    callback(message)
                    success_count += 1
                except Exception as e:
                    self.logger.error(f"Failed to send to client {client_id}: {e}")
                    failed_clients.append(client_id)
            
            # Remove failed clients
            for client_id in failed_clients:
                del self.connected_clients[client_id]
        
        return success_count > 0
    
    def is_available(self) -> bool:
        """Check if any clients are connected."""
        with self._lock:
            return len(self.connected_clients) > 0
    
    def get_buffered_messages(self) -> List[UIMessage]:
        """Get buffered messages."""
        with self._lock:
            return self.message_buffer.copy()
    
    def clear_buffer(self) -> None:
        """Clear message buffer."""
        with self._lock:
            self.message_buffer.clear()


class DirectUpdateAdapter(UIAdapter):
    """Adapter for direct UI updates (for testing and development)."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.update_callbacks: Dict[CommunicationChannel, List[Callable[[UIMessage], None]]] = {}
        self.last_messages: Dict[CommunicationChannel, UIMessage] = {}
        self._lock = threading.Lock()
    
    def register_callback(self, channel: CommunicationChannel, callback: Callable[[UIMessage], None]) -> None:
        """Register a callback for a specific channel."""
        with self._lock:
            if channel not in self.update_callbacks:
                self.update_callbacks[channel] = []
            self.update_callbacks[channel].append(callback)
            self.logger.info(f"Registered callback for channel: {channel.value}")
    
    def unregister_callback(self, channel: CommunicationChannel, callback: Callable[[UIMessage], None]) -> bool:
        """Unregister a callback."""
        with self._lock:
            if channel in self.update_callbacks:
                try:
                    self.update_callbacks[channel].remove(callback)
                    self.logger.info(f"Unregistered callback for channel: {channel.value}")
                    return True
                except ValueError:
                    pass
            return False
    
    def send_to_ui(self, message: UIMessage) -> bool:
        """Send message via direct callbacks."""
        with self._lock:
            self.last_messages[message.channel] = message
            
            callbacks = self.update_callbacks.get(message.channel, [])
            if not callbacks:
                self.logger.debug(f"No callbacks registered for channel: {message.channel.value}")
                return True  # Not an error, just no listeners
            
            success_count = 0
            failed_callbacks = []
            
            for callback in callbacks:
                try:
                    callback(message)
                    success_count += 1
                except Exception as e:
                    self.logger.error(f"Callback failed for channel {message.channel.value}: {e}")
                    failed_callbacks.append(callback)
            
            # Remove failed callbacks
            for callback in failed_callbacks:
                self.update_callbacks[message.channel].remove(callback)
            
            return success_count > 0
    
    def is_available(self) -> bool:
        """Direct updates are always available."""
        return True
    
    def get_last_message(self, channel: CommunicationChannel) -> Optional[UIMessage]:
        """Get the last message for a channel."""
        with self._lock:
            return self.last_messages.get(channel)


class CompositeUIAdapter(UIAdapter):
    """Composite adapter that tries multiple adapters in order."""
    
    def __init__(self, adapters: List[UIAdapter]):
        self.adapters = adapters
        self.logger = logging.getLogger(__name__)
    
    def send_to_ui(self, message: UIMessage) -> bool:
        """Send message using the first available adapter."""
        for adapter in self.adapters:
            if adapter.is_available():
                try:
                    if adapter.send_to_ui(message):
                        self.logger.debug(f"Message sent via {type(adapter).__name__}: {message.message_id}")
                        return True
                except Exception as e:
                    self.logger.warning(f"Adapter {type(adapter).__name__} failed: {e}")
                    continue
        
        self.logger.error(f"All adapters failed for message: {message.message_id}")
        return False
    
    def is_available(self) -> bool:
        """Check if any adapter is available."""
        return any(adapter.is_available() for adapter in self.adapters)


class UIMessageHandler(MessageHandler):
    """Message handler that uses UI adapters."""
    
    def __init__(self, adapter: UIAdapter, channels: Optional[List[CommunicationChannel]] = None):
        self.adapter = adapter
        self.channels = set(channels) if channels else set(CommunicationChannel)
        self.logger = logging.getLogger(__name__)
        self.handled_count = 0
        self.failed_count = 0
    
    def can_handle(self, message: UIMessage) -> bool:
        """Check if this handler can process the message."""
        return message.channel in self.channels and self.adapter.is_available()
    
    def handle_message(self, message: UIMessage) -> bool:
        """Handle the message using the UI adapter."""
        try:
            if self.adapter.send_to_ui(message):
                self.handled_count += 1
                return True
            else:
                self.failed_count += 1
                return False
        except Exception as e:
            self.logger.error(f"Failed to handle message {message.message_id}: {e}")
            self.failed_count += 1
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get handler statistics."""
        return {
            'handled_count': self.handled_count,
            'failed_count': self.failed_count,
            'channels': [ch.value for ch in self.channels],
            'adapter_type': type(self.adapter).__name__,
            'adapter_available': self.adapter.is_available()
        }


# Convenience functions for creating common UI messages
def send_node_update(node_id: int, update_type: str, data: Dict[str, Any]) -> str:
    """Send a node update message."""
    from src.infrastructure.ui_communication import send_ui_message
    
    return send_ui_message(
        channel=CommunicationChannel.NODE_DATA,
        message_type=f"node_{update_type}",
        data={
            'node_id': node_id,
            'update_type': update_type,
            **data
        },
        priority=MessagePriority.HIGH
    )


def send_ui_state_update(component: str, state_data: Dict[str, Any]) -> str:
    """Send a UI state update message."""
    from src.infrastructure.ui_communication import send_ui_message
    
    return send_ui_message(
        channel=CommunicationChannel.UI_STATE,
        message_type="state_update",
        data={
            'component': component,
            'state': state_data
        },
        priority=MessagePriority.NORMAL,
        target_component=component
    )


def send_system_notification(message: str, level: str = "info", component: str = "system") -> str:
    """Send a system notification message."""
    from src.infrastructure.ui_communication import send_ui_message
    
    return send_ui_message(
        channel=CommunicationChannel.NOTIFICATIONS,
        message_type="notification",
        data={
            'message': message,
            'level': level,
            'component': component,
            'timestamp': datetime.now().isoformat()
        },
        priority=MessagePriority.HIGH if level == "error" else MessagePriority.NORMAL
    )


def send_user_action_response(action: str, success: bool, data: Optional[Dict[str, Any]] = None) -> str:
    """Send a user action response message."""
    from src.infrastructure.ui_communication import send_ui_message
    
    return send_ui_message(
        channel=CommunicationChannel.USER_ACTIONS,
        message_type="action_response",
        data={
            'action': action,
            'success': success,
            'data': data or {},
            'timestamp': datetime.now().isoformat()
        },
        priority=MessagePriority.HIGH
    )