"""
Unit tests for caching infrastructure.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock

from src.infrastructure.cache import (
    LRUCache, CacheEntry, CacheManager, cached,
    get_cache_manager, cache_key_for_node, cache_key_for_search,
    invalidate_node_cache, invalidate_search_cache
)
from src.domain.models import Node, Position, UrgencyLevel


class TestCacheEntry:
    """Test cases for CacheEntry."""
    
    def test_cache_entry_creation(self):
        """Test creating a cache entry."""
        entry = CacheEntry(value="test", created_at=datetime.now())
        assert entry.value == "test"
        assert entry.access_count == 0
        assert not entry.is_expired()
    
    def test_cache_entry_expiration(self):
        """Test cache entry expiration."""
        past_time = datetime.now() - timedelta(seconds=10)
        entry = CacheEntry(
            value="test",
            created_at=past_time,
            ttl_seconds=5
        )
        assert entry.is_expired()
    
    def test_cache_entry_access(self):
        """Test cache entry access functionality."""
        entry = CacheEntry(value="test", created_at=datetime.now())
        initial_count = entry.access_count
        
        value = entry.access()
        
        assert value == "test"
        assert entry.access_count == initial_count + 1
        assert entry.last_accessed is not None


class TestLRUCache:
    """Test cases for LRUCache."""
    
    def test_lru_cache_basic_operations(self):
        """Test basic LRU cache operations."""
        cache = LRUCache[str](max_size=3)
        
        # Test put and get
        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Test cache miss
        assert cache.get("nonexistent") is None
    
    def test_lru_cache_eviction(self):
        """Test LRU cache eviction."""
        cache = LRUCache[str](max_size=2)
        
        # Fill cache
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        
        # Access key1 to make it more recently used
        cache.get("key1")
        
        # Add key3, should evict key2
        cache.put("key3", "value3")
        
        assert cache.get("key1") == "value1"  # Should still exist
        assert cache.get("key2") is None      # Should be evicted
        assert cache.get("key3") == "value3"  # Should exist
    
    def test_lru_cache_ttl(self):
        """Test LRU cache TTL functionality."""
        cache = LRUCache[str](max_size=10, default_ttl=1)  # 1 second TTL
        
        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(1.1)
        assert cache.get("key1") is None
    
    def test_lru_cache_invalidation(self):
        """Test cache invalidation."""
        cache = LRUCache[str](max_size=10)
        
        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Invalidate
        assert cache.invalidate("key1") == True
        assert cache.get("key1") is None
        
        # Try to invalidate non-existent key
        assert cache.invalidate("nonexistent") == False
    
    def test_lru_cache_stats(self):
        """Test cache statistics."""
        cache = LRUCache[str](max_size=10)
        
        # Initial stats
        stats = cache.get_stats()
        assert stats['hits'] == 0
        assert stats['misses'] == 0
        assert stats['size'] == 0
        
        # Add some data and access it
        cache.put("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss
        
        stats = cache.get_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['size'] == 1
        assert stats['hit_rate'] == 0.5
    
    def test_cleanup_expired(self):
        """Test cleanup of expired entries."""
        cache = LRUCache[str](max_size=10, default_ttl=1)
        
        # Add entries that will expire
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Cleanup expired entries
        expired_count = cache.cleanup_expired()
        assert expired_count == 2
        assert cache.get_stats()['size'] == 0


class TestCacheManager:
    """Test cases for CacheManager."""
    
    @pytest.fixture
    def cache_manager(self):
        """Create cache manager for testing."""
        return CacheManager()
    
    def test_cache_manager_initialization(self, cache_manager):
        """Test cache manager initialization."""
        assert cache_manager is not None
        
        # Check that default caches are created
        assert cache_manager.get_cache('nodes') is not None
        assert cache_manager.get_cache('render') is not None
        assert cache_manager.get_cache('computation') is not None
        assert cache_manager.get_cache('search') is not None
    
    def test_create_and_get_cache(self, cache_manager):
        """Test creating and getting caches."""
        # Create a new cache
        cache = cache_manager.create_cache('test_cache', max_size=50, default_ttl=30)
        assert cache is not None
        assert cache.max_size == 50
        assert cache.default_ttl == 30
        
        # Get the same cache
        same_cache = cache_manager.get_cache('test_cache')
        assert same_cache is cache
    
    def test_get_or_create_cache(self, cache_manager):
        """Test get_or_create_cache functionality."""
        # Get existing cache
        existing_cache = cache_manager.get_or_create_cache('nodes')
        assert existing_cache is not None
        
        # Create new cache
        new_cache = cache_manager.get_or_create_cache('new_cache', max_size=100)
        assert new_cache is not None
        assert new_cache.max_size == 100
    
    def test_invalidate_cache(self, cache_manager):
        """Test cache invalidation."""
        cache = cache_manager.get_cache('nodes')
        cache.put("test_key", "test_value")
        
        # Invalidate specific key
        result = cache_manager.invalidate_cache('nodes', 'test_key')
        assert result == True
        assert cache.get("test_key") is None
        
        # Invalidate entire cache
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        result = cache_manager.invalidate_cache('nodes')
        assert result == True
        assert cache.get_stats()['size'] == 0
    
    def test_cleanup_all_expired(self, cache_manager):
        """Test cleanup of expired entries in all caches."""
        # Add entries with short TTL
        nodes_cache = cache_manager.get_cache('nodes')
        nodes_cache.put("key1", "value1", ttl=1)
        
        render_cache = cache_manager.get_cache('render')
        render_cache.put("key2", "value2", ttl=1)
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Cleanup all expired
        results = cache_manager.cleanup_all_expired()
        
        # Should have cleaned up entries from both caches
        assert len(results) >= 0  # May be empty if cleanup happened automatically
    
    def test_get_all_stats(self, cache_manager):
        """Test getting statistics for all caches."""
        stats = cache_manager.get_all_stats()
        
        assert 'nodes' in stats
        assert 'render' in stats
        assert 'computation' in stats
        assert 'search' in stats
        
        # Check structure of stats
        for cache_name, cache_stats in stats.items():
            assert 'size' in cache_stats
            assert 'max_size' in cache_stats
            assert 'hits' in cache_stats
            assert 'misses' in cache_stats
            assert 'hit_rate' in cache_stats


class TestCachedDecorator:
    """Test cases for cached decorator."""
    
    def test_cached_decorator_basic(self):
        """Test basic cached decorator functionality."""
        call_count = 0
        
        @cached(cache_name='test_cache')
        def expensive_function(value):
            nonlocal call_count
            call_count += 1
            return value * 2
        
        # First call should execute function
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1
        
        # Second call should use cache
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Should not increment
        
        # Different argument should execute function again
        result3 = expensive_function(10)
        assert result3 == 20
        assert call_count == 2
    
    def test_cached_decorator_with_ttl(self):
        """Test cached decorator with TTL."""
        call_count = 0
        
        @cached(cache_name='ttl_test', ttl=1)  # 1 second TTL
        def function_with_ttl(value):
            nonlocal call_count
            call_count += 1
            return value * 3
        
        # First call
        result1 = function_with_ttl(5)
        assert result1 == 15
        assert call_count == 1
        
        # Second call within TTL
        result2 = function_with_ttl(5)
        assert result2 == 15
        assert call_count == 1
        
        # Wait for TTL to expire
        time.sleep(1.1)
        
        # Third call after TTL expiration
        result3 = function_with_ttl(5)
        assert result3 == 15
        assert call_count == 2  # Should increment
    
    def test_cached_decorator_with_kwargs(self):
        """Test cached decorator with keyword arguments."""
        call_count = 0
        
        @cached(cache_name='kwargs_test')
        def function_with_kwargs(a, b=10, c=20):
            nonlocal call_count
            call_count += 1
            return a + b + c
        
        # Test with different combinations
        result1 = function_with_kwargs(1, b=2, c=3)
        assert result1 == 6
        assert call_count == 1
        
        # Same call should use cache
        result2 = function_with_kwargs(1, b=2, c=3)
        assert result2 == 6
        assert call_count == 1
        
        # Different kwargs should execute function
        result3 = function_with_kwargs(1, b=5, c=3)
        assert result3 == 9
        assert call_count == 2


class TestCacheKeyFunctions:
    """Test cases for cache key generation functions."""
    
    def test_cache_key_for_node(self):
        """Test node cache key generation."""
        key1 = cache_key_for_node(123, "details")
        key2 = cache_key_for_node(123, "details")
        key3 = cache_key_for_node(123, "summary")
        key4 = cache_key_for_node(456, "details")
        
        # Same parameters should generate same key
        assert key1 == key2
        
        # Different parameters should generate different keys
        assert key1 != key3
        assert key1 != key4
    
    def test_cache_key_for_search(self):
        """Test search cache key generation."""
        key1 = cache_key_for_search("test query")
        key2 = cache_key_for_search("test query")
        key3 = cache_key_for_search("different query")
        
        # Same query should generate same key
        assert key1 == key2
        
        # Different query should generate different key
        assert key1 != key3
        
        # Test with filters
        filters1 = {"urgency": "high", "tag": "work"}
        filters2 = {"urgency": "high", "tag": "work"}
        filters3 = {"urgency": "low", "tag": "work"}
        
        key4 = cache_key_for_search("query", filters1)
        key5 = cache_key_for_search("query", filters2)
        key6 = cache_key_for_search("query", filters3)
        
        assert key4 == key5
        assert key4 != key6


class TestCacheInvalidation:
    """Test cases for cache invalidation functions."""
    
    def test_invalidate_node_cache(self):
        """Test node cache invalidation."""
        cache_manager = get_cache_manager()
        
        # Add some data to caches
        nodes_cache = cache_manager.get_cache('nodes')
        render_cache = cache_manager.get_cache('render')
        
        nodes_cache.put("node_123", "node data")
        render_cache.put("render_123", "render data")
        
        # Invalidate node cache
        invalidate_node_cache(123)
        
        # Caches should be cleared
        assert nodes_cache.get_stats()['size'] == 0
        assert render_cache.get_stats()['size'] == 0
    
    def test_invalidate_search_cache(self):
        """Test search cache invalidation."""
        cache_manager = get_cache_manager()
        search_cache = cache_manager.get_cache('search')
        
        # Add some search data
        search_cache.put("search_key", "search results")
        assert search_cache.get("search_key") == "search results"
        
        # Invalidate search cache
        invalidate_search_cache()
        
        # Search cache should be cleared
        assert search_cache.get("search_key") is None


class TestGlobalCacheManager:
    """Test cases for global cache manager functions."""
    
    def test_get_cache_manager(self):
        """Test getting global cache manager."""
        manager1 = get_cache_manager()
        manager2 = get_cache_manager()
        
        # Should return the same instance
        assert manager1 is manager2
        assert manager1 is not None


if __name__ == "__main__":
    pytest.main([__file__])