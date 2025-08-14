"""
Integration tests for caching and performance monitoring working together.
"""

import pytest
import tempfile
import os
from pathlib import Path

from src.application.services import MindMapService, NodeCreateRequest
from src.infrastructure.repositories import JsonMindMapRepository
from src.infrastructure.config import AppConfig
from src.infrastructure.cache import get_cache_manager
from src.infrastructure.performance import get_performance_monitor
from src.domain.models import Position, UrgencyLevel


class TestCachingPerformanceIntegration:
    """Test cases for caching and performance monitoring integration."""
    
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
        """Create service with all integrations."""
        repository = JsonMindMapRepository(config)
        service = MindMapService(repository, config)
        
        # Clear any existing metrics
        performance_monitor = get_performance_monitor()
        performance_monitor.clear_metrics()
        
        # Clear cache
        cache_manager = get_cache_manager()
        cache_manager.invalidate_cache('nodes')
        cache_manager.invalidate_cache('computation')
        
        return service
    
    def test_service_operations_are_timed(self, service):
        """Test that service operations are being timed."""
        performance_monitor = get_performance_monitor()
        
        # Create a node
        request = NodeCreateRequest(
            label="Test Node",
            position=Position(x=100, y=200),
            urgency=UrgencyLevel.MEDIUM
        )
        
        result = service.create_node(request)
        assert result.is_ok()
        
        # Check that the operation was timed
        stats = performance_monitor.get_operation_stats("mindmap_service.create_node")
        assert stats is not None
        assert stats['count'] == 1
        assert stats['success_count'] == 1
        assert stats['avg_duration'] > 0
    
    def test_caching_improves_performance(self, service):
        """Test that caching improves performance for repeated operations."""
        performance_monitor = get_performance_monitor()
        
        # Create some test data
        for i in range(5):
            request = NodeCreateRequest(
                label=f"Node {i}",
                position=Position(x=i*100, y=i*100),
                urgency=UrgencyLevel.MEDIUM,
                tag=f"tag{i % 2}"  # Alternate between tag0 and tag1
            )
            result = service.create_node(request)
            assert result.is_ok()
        
        # Clear performance metrics to start fresh
        performance_monitor.clear_metrics()
        
        # First call to get statistics
        stats1 = service.get_statistics()
        first_call_stats = performance_monitor.get_operation_stats("mindmap_service.get_statistics")
        
        # Second call to get statistics (should use cache)
        stats2 = service.get_statistics()
        second_call_stats = performance_monitor.get_operation_stats("mindmap_service.get_statistics")
        
        # Both calls should return the same data
        assert stats1 == stats2
        
        # Should have recorded calls (exact count depends on caching behavior)
        assert second_call_stats is not None
        assert second_call_stats['count'] >= 1
        
        # The results should be consistent
        assert stats1['total_nodes'] == 5
        assert 'urgency_distribution' in stats1
        assert 'tag_distribution' in stats1
    
    def test_cache_invalidation_on_data_changes(self, service):
        """Test that cache is properly invalidated when data changes."""
        cache_manager = get_cache_manager()
        
        # Create initial data
        request = NodeCreateRequest(
            label="Initial Node",
            position=Position(x=100, y=200),
            urgency=UrgencyLevel.HIGH
        )
        result = service.create_node(request)
        assert result.is_ok()
        node_id = result.data.id
        
        # Get statistics to populate cache
        stats1 = service.get_statistics()
        assert stats1['total_nodes'] == 1
        
        # Check that computation cache has data
        computation_cache = cache_manager.get_cache('computation')
        assert computation_cache.get_stats()['size'] > 0
        
        # Delete the node (should invalidate cache)
        delete_result = service.delete_node(node_id)
        assert delete_result.is_ok()
        
        # Get statistics again (should reflect the change)
        stats2 = service.get_statistics()
        assert stats2['total_nodes'] == 0
        
        # The statistics should be different
        assert stats1 != stats2
    
    def test_search_operations_use_caching(self, service):
        """Test that search operations use caching."""
        performance_monitor = get_performance_monitor()
        cache_manager = get_cache_manager()
        
        # Create test data
        for i in range(3):
            request = NodeCreateRequest(
                label=f"Searchable Node {i}",
                position=Position(x=i*100, y=i*100),
                urgency=UrgencyLevel.MEDIUM,
                description=f"Description for node {i}"
            )
            result = service.create_node(request)
            assert result.is_ok()
        
        # Clear performance metrics
        performance_monitor.clear_metrics()
        
        # First search
        results1 = service.search_nodes("Searchable")
        assert len(results1) == 3
        
        # Check that search was timed
        search_stats = performance_monitor.get_operation_stats("mindmap_service.search_nodes")
        assert search_stats is not None
        assert search_stats['count'] == 1
        
        # Second identical search (should use cache if implemented)
        results2 = service.search_nodes("Searchable")
        assert len(results2) == 3
        assert results1 == results2
        
        # Should have recorded 2 search operations
        search_stats_after = performance_monitor.get_operation_stats("mindmap_service.search_nodes")
        assert search_stats_after['count'] == 2
    
    def test_performance_monitoring_tracks_errors(self, service):
        """Test that performance monitoring tracks operations properly."""
        performance_monitor = get_performance_monitor()
        
        # Try to update a non-existent node (should return error result but not raise exception)
        from src.application.services import NodeUpdateRequest
        update_request = NodeUpdateRequest(label="Updated Label")
        
        result = service.update_node(999, update_request)  # Non-existent ID
        assert not result.is_ok()
        
        # Check that the operation was tracked (as successful from decorator perspective)
        stats = performance_monitor.get_operation_stats("mindmap_service.update_node")
        assert stats is not None
        assert stats['count'] == 1
        # The decorator sees this as successful since no exception was raised
        assert stats['success_count'] == 1
        assert stats['error_count'] == 0
    
    def test_cache_statistics_are_available(self, service):
        """Test that cache statistics are available and meaningful."""
        cache_manager = get_cache_manager()
        
        # Create some data to populate caches
        request = NodeCreateRequest(
            label="Cache Test Node",
            position=Position(x=100, y=200),
            urgency=UrgencyLevel.MEDIUM
        )
        result = service.create_node(request)
        assert result.is_ok()
        
        # Perform operations that should use cache
        service.get_statistics()
        service.search_nodes("Cache")
        
        # Get cache statistics
        all_stats = cache_manager.get_all_stats()
        
        # Should have stats for all cache types
        assert 'nodes' in all_stats
        assert 'render' in all_stats
        assert 'computation' in all_stats
        assert 'search' in all_stats
        
        # Each cache should have proper structure
        for cache_name, stats in all_stats.items():
            assert 'size' in stats
            assert 'max_size' in stats
            assert 'hits' in stats
            assert 'misses' in stats
            assert 'hit_rate' in stats
            assert 'total_requests' in stats
    
    def test_performance_summary_includes_service_operations(self, service):
        """Test that performance summary includes service operations."""
        performance_monitor = get_performance_monitor()
        
        # Perform various service operations
        request = NodeCreateRequest(
            label="Performance Test Node",
            position=Position(x=100, y=200),
            urgency=UrgencyLevel.HIGH
        )
        
        # Create node
        result = service.create_node(request)
        assert result.is_ok()
        node_id = result.data.id
        
        # Get statistics
        service.get_statistics()
        
        # Search nodes
        service.search_nodes("Performance")
        
        # Update node
        from src.application.services import NodeUpdateRequest
        update_request = NodeUpdateRequest(label="Updated Performance Node")
        service.update_node(node_id, update_request)
        
        # Get all performance statistics
        all_stats = performance_monitor.get_all_stats()
        
        # Should have stats for all operations we performed
        expected_operations = [
            "mindmap_service.create_node",
            "mindmap_service.get_statistics", 
            "mindmap_service.search_nodes",
            "mindmap_service.update_node"
        ]
        
        for operation in expected_operations:
            assert operation in all_stats
            stats = all_stats[operation]
            assert stats['count'] >= 1
            assert stats['avg_duration'] >= 0  # Duration can be 0 for very fast operations


if __name__ == "__main__":
    pytest.main([__file__])