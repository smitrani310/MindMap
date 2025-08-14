"""
Integration tests for the event system working with services and caching.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch

from src.application.services import MindMapService, NodeCreateRequest, NodeUpdateRequest
from src.application.event_handlers import setup_default_event_handlers, get_ui_event_handler, get_cache_event_handler
from src.infrastructure.repositories import JsonMindMapRepository
from src.infrastructure.config import AppConfig
from src.infrastructure.events import EventType, get_event_bus, publish_event, subscribe_to_event
from src.domain.models import Position, UrgencyLevel


class TestEventSystemIntegration:
    """Test cases for event system integration."""
    
    @pytest.fixture
    def temp_data_file(self):
        """Create a temporary data file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"nodes": [], "metadata": {"version": "1.0", "created_at": "2024-01-01T00:00:00", "last_modified": "2024-01-01T00:00:00"}}')
            temp_file = f.name
        
        yield temp_file
        
        # Cleanup
        if os.path.exists(temp_file):
            os.unlink(temp_file)
    
    @pytest.fixture
    def config(self, temp_data_file):
        """Create test configuration."""
        return AppConfig(
            data_file=temp_data_file,
            cache_size=100
        )
    
    @pytest.fixture
    def service(self, config):
        """Create service with event system integration."""
        repository = JsonMindMapRepository(config)
        service = MindMapService(repository, config)
        
        # Set up event handlers
        setup_default_event_handlers()
        
        return service
    
    def test_node_creation_publishes_events(self, service):
        """Test that creating a node publishes appropriate events."""
        event_bus = get_event_bus()
        
        # Subscribe to node created events
        received_events = []
        def event_subscriber(event):
            received_events.append(event)
        
        event_bus.subscribe(EventType.NODE_CREATED, event_subscriber)
        
        # Create a node
        request = NodeCreateRequest(
            label="Test Node",
            position=Position(x=100, y=200),
            urgency=UrgencyLevel.HIGH,
            tag="test"
        )
        
        result = service.create_node(request)
        assert result.is_ok()
        
        # Check that event was published
        assert len(received_events) == 1
        event = received_events[0]
        assert event.type == EventType.NODE_CREATED
        assert event.source == "MindMapService"
        assert event.data['node_id'] == result.data.id
        assert event.data['label'] == "Test Node"
        assert event.data['urgency'] == UrgencyLevel.HIGH.value
        assert event.data['tag'] == "test"
    
    def test_node_update_publishes_events(self, service):
        """Test that updating a node publishes appropriate events."""
        event_bus = get_event_bus()
        
        # Create a node first
        create_request = NodeCreateRequest(
            label="Original Node",
            position=Position(x=100, y=200),
            urgency=UrgencyLevel.MEDIUM
        )
        create_result = service.create_node(create_request)
        assert create_result.is_ok()
        node_id = create_result.data.id
        
        # Subscribe to node updated events
        received_events = []
        def event_subscriber(event):
            received_events.append(event)
        
        event_bus.subscribe(EventType.NODE_UPDATED, event_subscriber)
        
        # Update the node
        update_request = NodeUpdateRequest(
            label="Updated Node",
            urgency=UrgencyLevel.HIGH
        )
        
        result = service.update_node(node_id, update_request)
        assert result.is_ok()
        
        # Check that event was published
        assert len(received_events) == 1
        event = received_events[0]
        assert event.type == EventType.NODE_UPDATED
        assert event.source == "MindMapService"
        assert event.data['node_id'] == node_id
        assert event.data['label'] == "Updated Node"
        assert event.data['urgency'] == UrgencyLevel.HIGH.value
        assert 'label' in event.data['updated_fields']
        assert 'urgency' in event.data['updated_fields']
    
    def test_node_deletion_publishes_events(self, service):
        """Test that deleting a node publishes appropriate events."""
        event_bus = get_event_bus()
        
        # Create a node first
        create_request = NodeCreateRequest(
            label="Node to Delete",
            position=Position(x=100, y=200)
        )
        create_result = service.create_node(create_request)
        assert create_result.is_ok()
        node_id = create_result.data.id
        
        # Subscribe to node deleted events
        received_events = []
        def event_subscriber(event):
            received_events.append(event)
        
        event_bus.subscribe(EventType.NODE_DELETED, event_subscriber)
        
        # Delete the node
        result = service.delete_node(node_id)
        assert result.is_ok()
        
        # Check that event was published
        assert len(received_events) == 1
        event = received_events[0]
        assert event.type == EventType.NODE_DELETED
        assert event.source == "MindMapService"
        assert event.data['node_id'] == node_id
        assert event.data['label'] == "Node to Delete"
        assert event.data['deleted_count'] == 1
    
    def test_event_handlers_process_node_events(self, service):
        """Test that event handlers properly process node events."""
        event_bus = get_event_bus()
        
        # Get the cache event handler to check its stats
        cache_handler = get_cache_event_handler()
        assert cache_handler is not None
        
        initial_stats = cache_handler.get_cache_stats()
        
        # Create a node (should trigger cache invalidation events)
        request = NodeCreateRequest(
            label="Handler Test Node",
            position=Position(x=100, y=200)
        )
        
        result = service.create_node(request)
        assert result.is_ok()
        
        # Check that cache invalidation events were processed
        # (The NodeEventHandler should have published cache invalidation events)
        final_stats = cache_handler.get_cache_stats()
        assert final_stats['invalidations'] > initial_stats['invalidations']
    
    def test_ui_event_handler_tracks_selections(self, service):
        """Test that UI event handler tracks node selections."""
        event_bus = get_event_bus()
        ui_handler = get_ui_event_handler()
        assert ui_handler is not None
        
        # Initially no nodes selected
        assert len(ui_handler.get_selected_nodes()) == 0
        
        # Publish node selection events
        publish_event(
            EventType.UI_NODE_SELECTED,
            source="ui_test",
            data={'node_id': 123}
        )
        
        publish_event(
            EventType.UI_NODE_SELECTED,
            source="ui_test",
            data={'node_id': 456}
        )
        
        # Check that selections were tracked
        selected = ui_handler.get_selected_nodes()
        assert len(selected) == 2
        assert 123 in selected
        assert 456 in selected
        
        # Deselect one node
        publish_event(
            EventType.UI_NODE_DESELECTED,
            source="ui_test",
            data={'node_id': 123}
        )
        
        # Check updated selections
        selected = ui_handler.get_selected_nodes()
        assert len(selected) == 1
        assert 123 not in selected
        assert 456 in selected
    
    def test_system_events_are_handled(self, service):
        """Test that system events are properly handled."""
        event_bus = get_event_bus()
        
        # Publish a system error event
        publish_event(
            EventType.SYSTEM_ERROR,
            source="test_system",
            data={
                'message': 'Test error occurred',
                'error_type': 'TestError'
            }
        )
        
        # Publish a system info event
        publish_event(
            EventType.SYSTEM_INFO,
            source="test_system",
            data={
                'message': 'System information'
            }
        )
        
        # Events should be processed by SystemEventHandler
        # (We can't easily verify the logging, but we can check that no exceptions were raised)
        
        # Publish mindmap loaded event
        publish_event(
            EventType.MINDMAP_LOADED,
            source="repository",
            data={
                'node_count': 10,
                'file_path': '/test/path.json'
            }
        )
        
        # This should trigger cache invalidation
        # The test passes if no exceptions are raised
    
    def test_event_persistence_and_replay(self, service):
        """Test event persistence and replay functionality."""
        event_bus = get_event_bus()
        
        # Create some nodes to generate events
        for i in range(3):
            request = NodeCreateRequest(
                label=f"Persistence Test Node {i}",
                position=Position(x=i*100, y=i*100)
            )
            result = service.create_node(request)
            assert result.is_ok()
        
        # Check that events were persisted
        if event_bus.persistence:
            stored_events = event_bus.persistence.get_events(event_type=EventType.NODE_CREATED)
            assert len(stored_events) >= 3
            
            # Check event replay functionality
            replay_count = event_bus.replay_events(event_type=EventType.NODE_CREATED)
            assert replay_count >= 3
    
    def test_event_middleware_processing(self, service):
        """Test that event middleware processes events correctly."""
        event_bus = get_event_bus()
        
        # Get performance middleware stats before
        performance_middleware = None
        for middleware in event_bus.middleware:
            if hasattr(middleware, 'get_stats'):
                performance_middleware = middleware
                break
        
        assert performance_middleware is not None
        initial_stats = performance_middleware.get_stats()
        
        # Create a node to generate events
        request = NodeCreateRequest(
            label="Middleware Test Node",
            position=Position(x=100, y=200)
        )
        
        result = service.create_node(request)
        assert result.is_ok()
        
        # Check that performance middleware tracked the event
        final_stats = performance_middleware.get_stats()
        
        # Should have stats for NODE_CREATED events
        assert EventType.NODE_CREATED.value in final_stats
        node_created_stats = final_stats[EventType.NODE_CREATED.value]
        assert node_created_stats['count'] > 0
        assert node_created_stats['avg_ms'] >= 0
    
    def test_event_bus_statistics(self, service):
        """Test event bus statistics collection."""
        event_bus = get_event_bus()
        
        # Get initial stats
        initial_stats = event_bus.get_stats()
        
        # Create a node to generate events
        request = NodeCreateRequest(
            label="Stats Test Node",
            position=Position(x=100, y=200)
        )
        
        result = service.create_node(request)
        assert result.is_ok()
        
        # Get final stats
        final_stats = event_bus.get_stats()
        
        # Check that stats are comprehensive
        assert 'handlers' in final_stats
        assert 'handler_count' in final_stats
        assert 'middleware_count' in final_stats
        assert 'subscriber_counts' in final_stats
        assert 'total_subscribers' in final_stats
        assert 'persistence' in final_stats
        assert 'performance' in final_stats
        
        # Should have default handlers
        assert final_stats['handler_count'] >= 4  # Node, UI, System, Cache handlers
        assert final_stats['middleware_count'] >= 2  # Logging, Performance middleware
        
        # Persistence stats should show events
        persistence_stats = final_stats['persistence']
        assert persistence_stats['total_events'] > 0
        assert EventType.NODE_CREATED.value in persistence_stats['event_type_counts']
    
    def test_custom_event_subscription(self, service):
        """Test custom event subscription and handling."""
        event_bus = get_event_bus()
        
        # Custom event handler
        custom_events = []
        def custom_handler(event):
            custom_events.append(event)
        
        # Subscribe to multiple event types
        event_bus.subscribe(EventType.NODE_CREATED, custom_handler)
        event_bus.subscribe(EventType.NODE_UPDATED, custom_handler)
        event_bus.subscribe(EventType.NODE_DELETED, custom_handler)
        
        # Create, update, and delete a node
        create_request = NodeCreateRequest(
            label="Custom Handler Test",
            position=Position(x=100, y=200)
        )
        create_result = service.create_node(create_request)
        assert create_result.is_ok()
        node_id = create_result.data.id
        
        update_request = NodeUpdateRequest(label="Updated Label")
        update_result = service.update_node(node_id, update_request)
        assert update_result.is_ok()
        
        delete_result = service.delete_node(node_id)
        assert delete_result.is_ok()
        
        # Check that all events were received
        assert len(custom_events) == 3
        
        event_types = [event.type for event in custom_events]
        assert EventType.NODE_CREATED in event_types
        assert EventType.NODE_UPDATED in event_types
        assert EventType.NODE_DELETED in event_types
        
        # All events should be from MindMapService
        sources = [event.source for event in custom_events]
        assert all(source == "MindMapService" for source in sources)


if __name__ == "__main__":
    pytest.main([__file__])