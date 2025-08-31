"""
Unit tests for UI communication system.
"""

import pytest
import time
import threading
from datetime import datetime, timedelta
from typing import Optional, List
from unittest.mock import Mock, patch

from src.infrastructure.ui_communication import (
    UIMessage, CommunicationChannel, MessagePriority, MessageHandler,
    UICommunicationBus, get_ui_communication_bus, send_ui_message
)
from src.infrastructure.ui_adapters import (
    StreamlitSessionAdapter, WebSocketSimulatorAdapter, DirectUpdateAdapter,
    CompositeUIAdapter, UIMessageHandler
)
from src.infrastructure.event_system import Event, EventType


class MockMessageHandler(MessageHandler):
    """Mock message handler for unit tests."""
    
    def __init__(self, channels: Optional[List[CommunicationChannel]] = None):
        super().__init__(channels)
        self.handled_messages = []
        self.should_fail = False
    
    def handle(self, message: UIMessage) -> Optional[UIMessage]:
        """Handle the message and optionally return a response."""
        if self.should_fail:
            raise Exception("Handler intentionally failed")
        
        self.handled_messages.append(message)
        return None


class TestUIMessage:
    """Test cases for UIMessage."""
    
    def test_message_creation(self):
        """Test creating a UI message."""
        message = UIMessage(
            channel=CommunicationChannel.NODE_DATA,
            message_type="node_created",
            data={'node_id': 1, 'title': 'Test Node'},
            priority=MessagePriority.HIGH
        )
        
        assert message.channel == CommunicationChannel.NODE_DATA
        assert message.message_type == "node_created"
        assert message.data['node_id'] == 1
        assert message.priority == MessagePriority.HIGH
        assert message.message_id is not None
        assert isinstance(message.timestamp, datetime)
    
    def test_message_to_dict(self):
        """Test converting message to dictionary."""
        message = UIMessage(
            channel=CommunicationChannel.UI_STATE,
            message_type="selection_changed",
            data={'selected_nodes': [1, 2, 3]},
            source_component="node_selector"
        )
        
        result = message.to_dict()
        
        assert result['channel'] == 'ui_state'
        assert result['message_type'] == 'selection_changed'
        assert result['data']['selected_nodes'] == [1, 2, 3]
        assert result['source_component'] == 'node_selector'
        assert 'message_id' in result
        assert 'timestamp' in result
    
    def test_message_from_dict(self):
        """Test creating message from dictionary."""
        data = {
            'message_id': 'test-123',
            'channel': 'system_status',
            'message_type': 'error',
            'data': {'error_code': 'DB_ERROR'},
            'priority': 20,
            'timestamp': '2023-01-01T12:00:00',
            'source_component': 'database'
        }
        
        message = UIMessage.from_dict(data)
        
        assert message.message_id == 'test-123'
        assert message.channel == CommunicationChannel.SYSTEM_STATUS
        assert message.message_type == 'error'
        assert message.data['error_code'] == 'DB_ERROR'
        assert message.priority == MessagePriority.CRITICAL
        assert message.source_component == 'database'


class MockMessageHandler(MessageHandler):
    """Test message handler implementation."""
    
    def __init__(self, channels=None):
        super().__init__(channels)
        self.channels = channels or [CommunicationChannel.UI_STATE]
        self.handled_messages = []
        self.should_fail = False
    
    def can_handle(self, message):
        return message.channel in self.channels
    
    def handle(self, message):
        """Handle the message and optionally return a response."""
        if self.should_fail:
            raise ValueError("Handler configured to fail")
        
        self.handled_messages.append(message)
        return None
    
    def handle_message(self, message):
        # This method is for compatibility but doesn't add to handled_messages
        # since handle() already does that
        if self.should_fail:
            raise ValueError("Handler configured to fail")
        
        return True


class TestUICommunicationBus:
    """Test cases for UICommunicationBus."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.bus = UICommunicationBus()
        self.bus.start()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        self.bus.stop()
    
    def test_bus_start_stop(self):
        """Test starting and stopping the communication bus."""
        bus = UICommunicationBus()
        
        assert not bus._running
        
        bus.start()
        assert bus._running
        assert bus._worker_thread is not None
        
        bus.stop()
        assert not bus._running
    
    def test_send_message(self):
        """Test sending a message."""
        message = UIMessage(
            channel=CommunicationChannel.NODE_DATA,
            message_type="test_message",
            data={'test': 'data'}
        )
        
        result = self.bus.send_message(message)
        
        assert result is True
        assert self.bus.delivery_stats['messages_sent'] == 1
        assert len(self.bus.message_history) == 1
        assert self.bus.message_history[0] == message
    
    def test_register_handler(self):
        """Test registering a message handler."""
        handler = MockMessageHandler()
        
        self.bus.register_handler("test_handler", handler)
        
        assert "test_handler" in self.bus.message_handlers
        assert self.bus.message_handlers["test_handler"] == handler
    
    def test_message_processing(self):
        """Test message processing with handlers."""
        handler = MockMessageHandler([CommunicationChannel.NODE_DATA])
        self.bus.register_handler("test_handler", handler)
        
        message = UIMessage(
            channel=CommunicationChannel.NODE_DATA,
            message_type="test_message",
            data={'node_id': 1}
        )
        
        self.bus.send_message(message)
        
        # Wait for processing
        time.sleep(0.1)
        
        assert len(handler.handled_messages) == 1
        assert handler.handled_messages[0] == message
        assert self.bus.delivery_stats['messages_delivered'] == 1
    
    def test_message_retry(self):
        """Test message retry on handler failure."""
        handler = MockMessageHandler([CommunicationChannel.NODE_DATA])
        handler.should_fail = True
        self.bus.register_handler("failing_handler", handler)
        
        message = UIMessage(
            channel=CommunicationChannel.NODE_DATA,
            message_type="test_message",
            data={'node_id': 1},
            max_retries=2
        )
        
        self.bus.send_message(message)
        
        # Wait for processing and retries
        time.sleep(0.5)
        
        # Message should have been retried
        assert message.retry_count > 0
        assert self.bus.delivery_stats['messages_failed'] > 0
    
    def test_acknowledge_message(self):
        """Test message acknowledgment."""
        message = UIMessage(
            channel=CommunicationChannel.UI_STATE,
            message_type="test_message",
            requires_acknowledgment=True
        )
        
        # Simulate pending acknowledgment
        self.bus.pending_acknowledgments[message.message_id] = message
        
        result = self.bus.acknowledge_message(message.message_id)
        
        assert result is True
        assert message.message_id not in self.bus.pending_acknowledgments
        assert self.bus.delivery_stats['acknowledgments_received'] == 1
    
    def test_message_history(self):
        """Test message history functionality."""
        messages = []
        for i in range(5):
            message = UIMessage(
                channel=CommunicationChannel.NODE_DATA,
                message_type=f"message_{i}",
                data={'index': i}
            )
            messages.append(message)
            self.bus.send_message(message)
        
        # Get all history
        history = self.bus.get_message_history()
        assert len(history) == 5
        
        # Get limited history
        limited_history = self.bus.get_message_history(limit=3)
        assert len(limited_history) == 3
        
        # Get filtered history
        filtered_history = self.bus.get_message_history(
            channel=CommunicationChannel.NODE_DATA
        )
        assert len(filtered_history) == 5
        assert all(m.channel == CommunicationChannel.NODE_DATA for m in filtered_history)
    
    def test_replay_messages(self):
        """Test message replay functionality."""
        # Send some messages
        for i in range(3):
            message = UIMessage(
                channel=CommunicationChannel.UI_STATE,
                message_type=f"original_message_{i}",
                data={'index': i}
            )
            self.bus.send_message(message)
        
        # Replay messages
        replayed_count = self.bus.replay_messages(
            channel=CommunicationChannel.UI_STATE
        )
        
        assert replayed_count == 3
        
        # Check that replay messages were sent
        replay_messages = [
            m for m in self.bus.message_history 
            if m.message_type.startswith('replay_')
        ]
        assert len(replay_messages) == 3
    
    def test_delivery_stats(self):
        """Test delivery statistics."""
        handler = MockMessageHandler([CommunicationChannel.NODE_DATA])
        self.bus.register_handler("test_handler", handler)
        
        # Send successful message
        message1 = UIMessage(
            channel=CommunicationChannel.NODE_DATA,
            message_type="success_message"
        )
        self.bus.send_message(message1)
        
        # Send message with no handler
        message2 = UIMessage(
            channel=CommunicationChannel.NOTIFICATIONS,
            message_type="no_handler_message"
        )
        self.bus.send_message(message2)
        
        # Wait for processing
        time.sleep(0.1)
        
        stats = self.bus.get_delivery_stats()
        
        assert stats['messages_sent'] == 2
        assert stats['messages_delivered'] >= 1
        assert stats['messages_failed'] >= 1
        assert stats['registered_handlers'] == 1


class TestStreamlitSessionAdapter:
    """Test cases for StreamlitSessionAdapter."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = StreamlitSessionAdapter()
        
        # Create a mock session that behaves like a dict
        self.mock_session = Mock()
        self.mock_session.__contains__ = Mock(return_value=False)  # For 'in' operator
        self.mock_session.ui_messages = []
        self.mock_session.nodes_updated = False
        
        # Make get() method return ui_messages when key is 'ui_messages'
        def mock_get(key, default=None):
            if key == 'ui_messages':
                return self.mock_session.ui_messages
            return default
        
        self.mock_session.get = Mock(side_effect=mock_get)
        
        self.adapter.set_session_state(self.mock_session)
    
    def test_send_to_ui(self):
        """Test sending message to UI via session state."""
        message = UIMessage(
            channel=CommunicationChannel.NODE_DATA,
            message_type="node_update",
            data={'node_id': 1}
        )
        
        result = self.adapter.send_to_ui(message)
        
        assert result is True
        assert hasattr(self.mock_session, 'ui_messages')
        assert len(self.mock_session.ui_messages) == 1
        assert self.mock_session.nodes_updated is True
    
    def test_is_available(self):
        """Test availability check."""
        assert self.adapter.is_available() is True
        
        # Test without session state
        adapter_no_session = StreamlitSessionAdapter()
        assert adapter_no_session.is_available() is False
    
    def test_get_messages(self):
        """Test getting messages from session state."""
        # Set up messages in session
        self.mock_session.ui_messages = [
            {
                'channel': 'node_data',
                'message_type': 'node_created',
                'data': {'node_id': 1}
            },
            {
                'channel': 'ui_state',
                'message_type': 'selection_changed',
                'data': {'selected': [1]}
            }
        ]
        
        # Get all messages
        all_messages = self.adapter.get_messages()
        assert len(all_messages) == 2
        
        # Get filtered messages
        node_messages = self.adapter.get_messages(CommunicationChannel.NODE_DATA)
        assert len(node_messages) == 1
        assert node_messages[0]['message_type'] == 'node_created'
    
    def test_clear_messages(self):
        """Test clearing messages from session state."""
        # Set up messages
        self.mock_session.ui_messages = [
            {'channel': 'node_data', 'message_type': 'test1'},
            {'channel': 'ui_state', 'message_type': 'test2'}
        ]
        
        # Clear specific channel
        self.adapter.clear_messages(CommunicationChannel.NODE_DATA)
        assert len(self.mock_session.ui_messages) == 1
        assert self.mock_session.ui_messages[0]['channel'] == 'ui_state'
        
        # Clear all messages
        self.adapter.clear_messages()
        assert len(self.mock_session.ui_messages) == 0


class TestWebSocketSimulatorAdapter:
    """Test cases for WebSocketSimulatorAdapter."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = WebSocketSimulatorAdapter()
    
    def test_connect_disconnect_client(self):
        """Test client connection and disconnection."""
        callback = Mock()
        
        # Connect client
        self.adapter.connect_client("client1", callback)
        assert "client1" in self.adapter.connected_clients
        assert self.adapter.is_available() is True
        
        # Disconnect client
        self.adapter.disconnect_client("client1")
        assert "client1" not in self.adapter.connected_clients
        assert self.adapter.is_available() is False
    
    def test_send_to_ui_with_clients(self):
        """Test sending message to connected clients."""
        callback1 = Mock()
        callback2 = Mock()
        
        self.adapter.connect_client("client1", callback1)
        self.adapter.connect_client("client2", callback2)
        
        message = UIMessage(
            channel=CommunicationChannel.UI_STATE,
            message_type="test_message"
        )
        
        result = self.adapter.send_to_ui(message)
        
        assert result is True
        callback1.assert_called_once_with(message)
        callback2.assert_called_once_with(message)
    
    def test_send_to_ui_without_clients(self):
        """Test sending message without connected clients (buffering)."""
        message = UIMessage(
            channel=CommunicationChannel.NODE_DATA,
            message_type="buffered_message"
        )
        
        result = self.adapter.send_to_ui(message)
        
        assert result is True
        buffered_messages = self.adapter.get_buffered_messages()
        assert len(buffered_messages) == 1
        assert buffered_messages[0] == message
    
    def test_failed_client_removal(self):
        """Test removal of failed clients."""
        failing_callback = Mock(side_effect=Exception("Client failed"))
        working_callback = Mock()
        
        self.adapter.connect_client("failing_client", failing_callback)
        self.adapter.connect_client("working_client", working_callback)
        
        message = UIMessage(
            channel=CommunicationChannel.SYSTEM_STATUS,
            message_type="test_message"
        )
        
        result = self.adapter.send_to_ui(message)
        
        # Should still succeed with working client
        assert result is True
        # Failed client should be removed
        assert "failing_client" not in self.adapter.connected_clients
        assert "working_client" in self.adapter.connected_clients


class TestDirectUpdateAdapter:
    """Test cases for DirectUpdateAdapter."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = DirectUpdateAdapter()
    
    def test_register_callback(self):
        """Test registering callbacks."""
        callback = Mock()
        
        self.adapter.register_callback(CommunicationChannel.NODE_DATA, callback)
        
        assert CommunicationChannel.NODE_DATA in self.adapter.update_callbacks
        assert callback in self.adapter.update_callbacks[CommunicationChannel.NODE_DATA]
    
    def test_send_to_ui(self):
        """Test sending message via direct callbacks."""
        callback = Mock()
        self.adapter.register_callback(CommunicationChannel.UI_STATE, callback)
        
        message = UIMessage(
            channel=CommunicationChannel.UI_STATE,
            message_type="direct_update"
        )
        
        result = self.adapter.send_to_ui(message)
        
        assert result is True
        callback.assert_called_once_with(message)
        
        # Check last message tracking
        last_message = self.adapter.get_last_message(CommunicationChannel.UI_STATE)
        assert last_message == message
    
    def test_is_available(self):
        """Test availability (always true for direct adapter)."""
        assert self.adapter.is_available() is True
    
    def test_unregister_callback(self):
        """Test unregistering callbacks."""
        callback = Mock()
        self.adapter.register_callback(CommunicationChannel.NODE_DATA, callback)
        
        result = self.adapter.unregister_callback(CommunicationChannel.NODE_DATA, callback)
        
        assert result is True
        assert callback not in self.adapter.update_callbacks[CommunicationChannel.NODE_DATA]


class TestCompositeUIAdapter:
    """Test cases for CompositeUIAdapter."""
    
    def test_send_to_ui_first_available(self):
        """Test sending message using first available adapter."""
        adapter1 = Mock(spec=StreamlitSessionAdapter)
        adapter1.is_available.return_value = False
        
        adapter2 = Mock(spec=DirectUpdateAdapter)
        adapter2.is_available.return_value = True
        adapter2.send_to_ui.return_value = True
        
        composite = CompositeUIAdapter([adapter1, adapter2])
        
        message = UIMessage(
            channel=CommunicationChannel.UI_STATE,
            message_type="test"
        )
        
        result = composite.send_to_ui(message)
        
        assert result is True
        adapter1.is_available.assert_called_once()
        adapter1.send_to_ui.assert_not_called()
        adapter2.send_to_ui.assert_called_once_with(message)
    
    def test_is_available(self):
        """Test availability check for composite adapter."""
        adapter1 = Mock()
        adapter1.is_available.return_value = False
        
        adapter2 = Mock()
        adapter2.is_available.return_value = True
        
        composite = CompositeUIAdapter([adapter1, adapter2])
        
        assert composite.is_available() is True
        
        # Test when no adapters are available
        adapter2.is_available.return_value = False
        assert composite.is_available() is False


class TestUIMessageHandler:
    """Test cases for UIMessageHandler."""
    
    def test_can_handle(self):
        """Test message handling capability check."""
        adapter = Mock()
        adapter.is_available.return_value = True
        
        handler = UIMessageHandler(
            adapter, 
            channels=[CommunicationChannel.NODE_DATA]
        )
        
        # Should handle NODE_DATA messages
        node_message = UIMessage(channel=CommunicationChannel.NODE_DATA, message_type="test")
        assert handler.can_handle(node_message) is True
        
        # Should not handle UI_STATE messages
        ui_message = UIMessage(channel=CommunicationChannel.UI_STATE, message_type="test")
        assert handler.can_handle(ui_message) is False
        
        # Should not handle when adapter unavailable
        adapter.is_available.return_value = False
        assert handler.can_handle(node_message) is False
    
    def test_handle_message(self):
        """Test message handling."""
        adapter = Mock()
        adapter.send_to_ui.return_value = True
        
        handler = UIMessageHandler(adapter)
        
        message = UIMessage(channel=CommunicationChannel.UI_STATE, message_type="test")
        
        result = handler.handle_message(message)
        
        assert result is True
        adapter.send_to_ui.assert_called_once_with(message)
        assert handler.handled_count == 1
        assert handler.failed_count == 0
    
    def test_get_stats(self):
        """Test getting handler statistics."""
        adapter = Mock()
        adapter.is_available.return_value = True
        
        handler = UIMessageHandler(
            adapter,
            channels=[CommunicationChannel.NODE_DATA, CommunicationChannel.UI_STATE]
        )
        
        stats = handler.get_stats()
        
        assert stats['handled_count'] == 0
        assert stats['failed_count'] == 0
        assert len(stats['channels']) == 2
        assert 'node_data' in stats['channels']
        assert 'ui_state' in stats['channels']
        assert stats['adapter_available'] is True


class TestGlobalFunctions:
    """Test cases for global functions."""
    
    def test_get_ui_communication_bus_singleton(self):
        """Test that get_ui_communication_bus returns singleton."""
        bus1 = get_ui_communication_bus()
        bus2 = get_ui_communication_bus()
        
        assert bus1 is bus2
    
    def test_send_ui_message_convenience(self):
        """Test send_ui_message convenience function."""
        message_id = send_ui_message(
            channel=CommunicationChannel.NODE_DATA,
            message_type="test_message",
            data={'test': 'data'},
            priority=MessagePriority.HIGH
        )
        
        assert message_id is not None
        assert len(message_id) > 0
        
        # Verify message was sent
        bus = get_ui_communication_bus()
        assert bus.delivery_stats['messages_sent'] > 0


if __name__ == "__main__":
    pytest.main([__file__])