"""
Unit tests for caching system.
"""

import pytest
import time
from unittest.mock import patch

from src.infrastructure.cache import (
    CacheEntry, LRUCache, CacheManager, get_cache_manager,
    cached, cache_key_for_node, cache_key_for_search,
    invalidate_node_cache, invalidate_search_cache
)


class TestCacheEntry:
    """Test cases for CacheEntry."""
    
    def test_cache_entry_creation(self):
        """Test creating a cache entry."""
        from datetime import datetime
        
        entry = CacheEntry(value="test_value", created_at=datetime.now())
        
        assert entry.value == "test_value"
        assert entry.access_count == 0
        assert entry.last_accessed is None
        assert entry.ttl_seconds is None
    
    def test_cache_entry_with_ttl(self):
        """Test cache entry with TTL."""
        from datetime import datetime
        
        entry = CacheEntry(
            value="test_value", 
            created_at=datetime.now(),
            ttl_seconds=60
        )
        
        assert not entry.is_expired()
        
        # Test with old creation time
        old_time = datetime.now().replace(year=2020)
        old_entry = CacheEntry(
            value="old_value",
            created_at=old_time,
            ttl_seconds=60
        )
        
        assert old_entry.is_expired()
    
    def test_cache_entry_access(self):
        """Test accessing cache entry."""
        from datetime import datetime
        
        entry = CacheEntry(value="test_value", created_at=datetime.now())
        
        assert entry.access_count == 0
        assert entry.last_accessed is None
        
        value = entry.access()
        
        assert value == "test_value"
        assert entry.access_count == 1
        assert entry.last_accessed is not None


class TestLRUCache:
    """Test cases for LRUCache."""
    
    def test_cache_initialization(self):
        """Test cache initialization."""
        cache = LRUCache(max_size=100, default_ttl=300)
        
        assert cache.max_size == 100
        assert cache.default_ttl == 300
        assert len(cache._cache) == 0
    
    def test_put_and_get(self):
        """Test putting and getting values."""
        cache = LRUCache(max_size=10)
        
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("nonexistent") is None
    
    def test_cache_with_ttl(self):
        """Test cache with TTL expiration."""
        cache = LRUCache(max_size=10, default_ttl=1)  # 1 second TTL
        
        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(1.1)
        assert cache.get("key1") is None
    
    def test_cache_override_ttl(self):
        """Test overriding default TTL."""
        cache = LRUCache(max_size=10, default_ttl=1)
        
        cache.put("key1", "value1", ttl=None)  # No expiration
        cache.put("key2", "value2", ttl=2)     # 2 second TTL
        
        time.sleep(1.1)
        
        assert cache.get("key1") == "value1"  # Should not expire
        assert cache.get("key2") == "value2"  # Should not expire yet
        
        time.sleep(1.1)
        
        assert cache.get("key1") == "value1"  # Still should not expire
        assert cache.get("key2") is None      # Should expire now
    
    def test_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = LRUCache(max_size=3)
        
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")
        
        # Access key1 to make it recently used
        cache.get("key1")
        
        # Add key4, should evict key2 (least recently used)
        cache.put("key4", "value4")
        
        assert cache.get("key1") == "value1"  # Should still exist
        assert cache.get("key2") is None      # Should be evicted
        assert cache.get("key3") == "value3"  # Should still exist
        assert cache.get("key4") == "value4"  # Should exist
    
    def test_invalidate(self):
        """Test cache invalidation."""
        cache = LRUCache(max_size=10)
        
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        
        assert cache.get("key1") == "value1"
        
        # Invalidate key1
        result = cache.invalidate("key1")
        assert result is True
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        
        # Try to invalidate non-existent key
        result = cache.invalidate("nonexistent")
        assert result is False
    
    def test_clear(self):
        """Test clearing the cache."""
        cache = LRUCache(max_size=10)
        
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        
        assert len(cache._cache) == 2
        
        cache.clear()
        
        assert len(cache._cache) == 0
        assert cache.get("key1") is None
        assert cache.get("key2") is None
    
    def test_get_stats(self):
        """Test getting cache statistics."""
        cache = LRUCache(max_size=10)
        
        # Initially empty
        stats = cache.get_stats()
        assert stats['size'] == 0
        assert stats['hits'] == 0
        assert stats['misses'] == 0
        assert stats['hit_rate'] == 0
        
        # Add some data and access it
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        
        cache.get("key1")  # Hit
        cache.get("key1")  # Hit
        cache.get("nonexistent")  # Miss
        
        stats = cache.get_stats()
        assert stats['size'] == 2
        assert stats['hits'] == 2
        assert stats['misses'] == 1
        assert stats['hit_rate'] == 2/3
    
    def test_cleanup_expired(self):
        """Test cleaning up expired entries."""
        cache = LRUCache(max_size=10)
        
        cache.put("key1", "value1", ttl=1)  # Will expire
        cache.put("key2", "value2")         # Won't expire
        
        time.sleep(1.1)
        
        expired_count = cache.cleanup_expired()
        
        assert expired_count == 1
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"


class TestCacheManager:
    """Test cases for CacheManager."""
    
    def test_cache_manager_initialization(self):
        """Test cache manager initialization."""
        manager = CacheManager()
        
        # Should create default caches
        assert manager.get_cache('nodes') is not None
        assert manager.get_cache('render') is not None
        assert manager.get_cache('computation') is not None
        assert manager.get_cache('search') is not None
    
    def test_create_cache(self):
        """Test creating a new cache."""
        manager = CacheManager()
        
        cache = manager.create_cache('test_cache', max_size=50, default_ttl=120)
        
        assert cache is not None
        assert cache.max_size == 50
        assert cache.default_ttl == 120
        assert manager.get_cache('test_cache') is cache
    
    def test_get_or_create_cache(self):
        """Test getting or creating a cache."""
        manager = CacheManager()
        
        # Get existing cache
        existing_cache = manager.get_or_create_cache('nodes')
        assert existing_cache is not None
        
        # Create new cache
        new_cache = manager.get_or_create_cache('new_cache', max_size=25)
        assert new_cache is not None
        assert new_cache.max_size == 25
        
        # Get the same cache again
        same_cache = manager.get_or_create_cache('new_cache')
        assert same_cache is new_cache
    
    def test_invalidate_cache(self):
        """Test cache invalidation."""
        manager = CacheManager()
        
        cache = manager.get_cache('nodes')
        cache.put('test_key', 'test_value')
        
        assert cache.get('test_key') == 'test_value'
        
        # Invalidate specific key
        result = manager.invalidate_cache('nodes', 'test_key')
        assert result is True
        assert cache.get('test_key') is None
        
        # Add data back and invalidate entire cache
        cache.put('test_key', 'test_value')
        cache.put('test_key2', 'test_value2')
        
        result = manager.invalidate_cache('nodes')
        assert result is True
        assert cache.get('test_key') is None
        assert cache.get('test_key2') is None
    
    def test_cleanup_all_expired(self):
        """Test cleaning up expired entries in all caches."""
        manager = CacheManager()
        
        # Add expired entries to multiple caches
        nodes_cache = manager.get_cache('nodes')
        search_cache = manager.get_cache('search')
        
        nodes_cache.put('expired1', 'value1', ttl=1)
        search_cache.put('expired2', 'value2', ttl=1)
        
        time.sleep(1.1)
        
        results = manager.cleanup_all_expired()
        
        # Should report expired entries from both caches
        assert 'nodes' in results or 'search' in results
    
    def test_get_all_stats(self):
        """Test getting statistics for all caches."""
        manager = CacheManager()
        
        # Add some data to caches
        nodes_cache = manager.get_cache('nodes')
        nodes_cache.put('key1', 'value1')
        nodes_cache.get('key1')  # Generate a hit
        
        stats = manager.get_all_stats()
        
        assert 'nodes' in stats
        assert stats['nodes']['size'] == 1
        assert stats['nodes']['hits'] == 1


class TestCachedDecorator:
    """Test cases for the @cached decorator."""
    
    def test_cached_decorator(self):
        """Test cached decorator functionality."""
        call_count = 0
        
        @cached(cache_name='test_cache', ttl=60)
        def expensive_function(x, y):
            nonlocal call_count
            call_count += 1
            return x + y
        
        # First call should execute the function
        result1 = expensive_function(1, 2)
        assert result1 == 3
        assert call_count == 1
        
        # Second call with same arguments should use cache
        result2 = expensive_function(1, 2)
        assert result2 == 3
        assert call_count == 1  # Should not increment
        
        # Call with different arguments should execute the function
        result3 = expensive_function(2, 3)
        assert result3 == 5
        assert call_count == 2
    
    def test_cached_decorator_with_custom_key_func(self):
        """Test cached decorator with custom key function."""
        call_count = 0
        
        def custom_key_func(x, y):
            return f"custom_{x}_{y}"
        
        @cached(cache_name='test_cache', key_func=custom_key_func)
        def test_function(x, y):
            nonlocal call_count
            call_count += 1
            return x * y
        
        result1 = test_function(2, 3)
        assert result1 == 6
        assert call_count == 1
        
        result2 = test_function(2, 3)
        assert result2 == 6
        assert call_count == 1  # Should use cache


class TestCacheUtilities:
    """Test cases for cache utility functions."""
    
    def test_cache_key_for_node(self):
        """Test generating cache keys for nodes."""
        key1 = cache_key_for_node(123)
        key2 = cache_key_for_node(123, 'update')
        key3 = cache_key_for_node(456)
        
        assert key1 == "node_123_"
        assert key2 == "node_123_update"
        assert key3 == "node_456_"
        assert key1 != key3
    
    def test_cache_key_for_search(self):
        """Test generating cache keys for search."""
        key1 = cache_key_for_search("test query")
        key2 = cache_key_for_search("test query", {"filter": "value"})
        key3 = cache_key_for_search("different query")
        
        assert isinstance(key1, str)
        assert isinstance(key2, str)
        assert isinstance(key3, str)
        assert key1 != key2
        assert key1 != key3
    
    def test_invalidate_node_cache(self):
        """Test invalidating node-related caches."""
        manager = CacheManager()
        
        # Add some data to caches
        nodes_cache = manager.get_cache('nodes')
        render_cache = manager.get_cache('render')
        
        nodes_cache.put('test1', 'value1')
        render_cache.put('test2', 'value2')
        
        assert nodes_cache.get('test1') == 'value1'
        assert render_cache.get('test2') == 'value2'
        
        # Invalidate node cache
        with patch('src.infrastructure.cache.get_cache_manager', return_value=manager):
            invalidate_node_cache(123)
        
        # Caches should be cleared
        assert nodes_cache.get('test1') is None
        assert render_cache.get('test2') is None
    
    def test_invalidate_search_cache(self):
        """Test invalidating search cache."""
        manager = CacheManager()
        
        search_cache = manager.get_cache('search')
        search_cache.put('search_key', 'search_result')
        
        assert search_cache.get('search_key') == 'search_result'
        
        with patch('src.infrastructure.cache.get_cache_manager', return_value=manager):
            invalidate_search_cache()
        
        assert search_cache.get('search_key') is None


class TestGlobalCacheManager:
    """Test cases for global cache manager functions."""
    
    def test_get_cache_manager_singleton(self):
        """Test that get_cache_manager returns the same instance."""
        manager1 = get_cache_manager()
        manager2 = get_cache_manager()
        
        assert manager1 is manager2