"""
Caching infrastructure for the Enhanced Mind Map application.

This module provides caching capabilities to improve performance by avoiding
redundant computations and data access operations.
"""

import time
import hashlib
import logging
from typing import Any, Optional, Dict, Callable, TypeVar, Generic
from functools import wraps
from threading import RLock
from dataclasses import dataclass
from datetime import datetime, timedelta

T = TypeVar('T')

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry(Generic[T]):
    """Represents a cached entry with metadata."""
    value: T
    created_at: datetime
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    ttl_seconds: Optional[int] = None
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        if self.ttl_seconds is None:
            return False
        
        age = datetime.now() - self.created_at
        return age.total_seconds() > self.ttl_seconds
    
    def access(self) -> T:
        """Access the cached value and update access metadata."""
        self.access_count += 1
        self.last_accessed = datetime.now()
        return self.value


class LRUCache(Generic[T]):
    """
    Least Recently Used (LRU) cache implementation.
    
    This cache automatically evicts the least recently used items when
    the maximum size is reached.
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: Optional[int] = None):
        """
        Initialize the LRU cache.
        
        Args:
            max_size: Maximum number of items to store
            default_ttl: Default time-to-live in seconds (None for no expiration)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry[T]] = {}
        self._access_order: Dict[str, int] = {}  # Use counter instead of datetime
        self._access_counter = 0
        self._lock = RLock()
        self._hits = 0
        self._misses = 0
        
        logger.debug(f"Initialized LRU cache with max_size={max_size}, default_ttl={default_ttl}")
    
    def get(self, key: str) -> Optional[T]:
        """Get a value from the cache."""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                logger.debug(f"Cache miss for key: {key}")
                return None
            
            entry = self._cache[key]
            
            # Check if expired
            if entry.is_expired():
                logger.debug(f"Cache entry expired for key: {key}")
                del self._cache[key]
                del self._access_order[key]
                self._misses += 1
                return None
            
            # Update access order
            self._access_counter += 1
            self._access_order[key] = self._access_counter
            self._hits += 1
            
            logger.debug(f"Cache hit for key: {key}")
            return entry.access()
    
    def put(self, key: str, value: T, ttl: Optional[int] = ...) -> None:
        """Put a value in the cache."""
        with self._lock:
            # Use default TTL if not specified, but allow explicit None to mean no expiration
            if ttl is ...:
                ttl = self.default_ttl
            
            # Create cache entry
            entry = CacheEntry(
                value=value,
                created_at=datetime.now(),
                ttl_seconds=ttl
            )
            
            # If cache is full, evict least recently used item
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_lru()
            
            # Store the entry
            self._cache[key] = entry
            self._access_counter += 1
            self._access_order[key] = self._access_counter
            
            logger.debug(f"Cached value for key: {key} (TTL: {ttl})")
    
    def invalidate(self, key: str) -> bool:
        """Remove a specific key from the cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                del self._access_order[key]
                logger.debug(f"Invalidated cache key: {key}")
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cached items."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self._hits = 0
            self._misses = 0
            logger.debug("Cache cleared")
    
    def _evict_lru(self) -> None:
        """Evict the least recently used item."""
        if not self._access_order:
            return
        
        # Find the least recently used key (smallest counter value)
        lru_key = min(self._access_order.keys(), key=lambda k: self._access_order[k])
        
        # Remove it
        del self._cache[lru_key]
        del self._access_order[lru_key]
        
        logger.debug(f"Evicted LRU cache entry: {lru_key}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests) if total_requests > 0 else 0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': hit_rate,
                'total_requests': total_requests
            }
    
    def cleanup_expired(self) -> int:
        """Remove expired entries and return the count of removed items."""
        with self._lock:
            expired_keys = []
            
            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
                del self._access_order[key]
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
            
            return len(expired_keys)


class CacheManager:
    """
    Central cache manager for the application.
    
    Manages multiple named caches with different configurations.
    """
    
    def __init__(self):
        """Initialize the cache manager."""
        self._caches: Dict[str, LRUCache] = {}
        self._lock = RLock()
        
        # Create default caches
        self.create_cache('nodes', max_size=1000, default_ttl=300)  # 5 minutes
        self.create_cache('render', max_size=100, default_ttl=60)   # 1 minute
        self.create_cache('computation', max_size=500, default_ttl=600)  # 10 minutes
        self.create_cache('search', max_size=200, default_ttl=120)  # 2 minutes
        
        logger.info("CacheManager initialized with default caches")
    
    def create_cache(self, name: str, max_size: int = 1000, default_ttl: Optional[int] = None) -> LRUCache:
        """Create a new named cache."""
        with self._lock:
            cache = LRUCache(max_size=max_size, default_ttl=default_ttl)
            self._caches[name] = cache
            logger.info(f"Created cache '{name}' with max_size={max_size}, default_ttl={default_ttl}")
            return cache
    
    def get_cache(self, name: str) -> Optional[LRUCache]:
        """Get a named cache."""
        return self._caches.get(name)
    
    def get_or_create_cache(self, name: str, max_size: int = 1000, default_ttl: Optional[int] = None) -> LRUCache:
        """Get an existing cache or create a new one."""
        cache = self.get_cache(name)
        if cache is None:
            cache = self.create_cache(name, max_size, default_ttl)
        return cache
    
    def invalidate_cache(self, name: str, key: Optional[str] = None) -> bool:
        """Invalidate a specific key or entire cache."""
        cache = self.get_cache(name)
        if cache is None:
            return False
        
        if key is None:
            cache.clear()
            logger.info(f"Cleared entire cache: {name}")
        else:
            result = cache.invalidate(key)
            if result:
                logger.info(f"Invalidated cache key '{key}' in cache '{name}'")
            return result
        
        return True
    
    def cleanup_all_expired(self) -> Dict[str, int]:
        """Clean up expired entries in all caches."""
        results = {}
        
        with self._lock:
            for name, cache in self._caches.items():
                expired_count = cache.cleanup_expired()
                if expired_count > 0:
                    results[name] = expired_count
        
        return results
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all caches."""
        stats = {}
        
        with self._lock:
            for name, cache in self._caches.items():
                stats[name] = cache.get_stats()
        
        return stats


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def cached(cache_name: str = 'default', ttl: Optional[int] = None, key_func: Optional[Callable] = None):
    """
    Decorator for caching function results.
    
    Args:
        cache_name: Name of the cache to use
        ttl: Time-to-live for cached results
        key_func: Function to generate cache key from arguments
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_manager = get_cache_manager()
            cache = cache_manager.get_or_create_cache(cache_name)
            
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = hashlib.md5('|'.join(key_parts).encode()).hexdigest()
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                logger.debug(f"Cache hit for {func.__name__} with key {cache_key}")
                return result
            
            # Execute function and cache result
            logger.debug(f"Cache miss for {func.__name__} with key {cache_key}, executing function")
            result = func(*args, **kwargs)
            cache.put(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


def cache_key_for_node(node_id: int, operation: str = '') -> str:
    """Generate a cache key for node-related operations."""
    return f"node_{node_id}_{operation}"


def cache_key_for_search(query: str, filters: Optional[Dict] = None) -> str:
    """Generate a cache key for search operations."""
    key_parts = [f"search_{query}"]
    if filters:
        key_parts.extend(f"{k}={v}" for k, v in sorted(filters.items()))
    return hashlib.md5('|'.join(key_parts).encode()).hexdigest()


def invalidate_node_cache(node_id: int) -> None:
    """Invalidate all cache entries related to a specific node."""
    cache_manager = get_cache_manager()
    
    # Invalidate node-specific caches
    for cache_name in ['nodes', 'render', 'computation']:
        cache = cache_manager.get_cache(cache_name)
        if cache:
            # We need to invalidate all keys that might be related to this node
            # For now, we'll clear the entire cache (could be optimized later)
            cache.clear()
    
    logger.debug(f"Invalidated caches for node {node_id}")


def invalidate_search_cache() -> None:
    """Invalidate search-related caches."""
    cache_manager = get_cache_manager()
    cache_manager.invalidate_cache('search')
    logger.debug("Invalidated search cache")


def invalidate_computation_cache() -> None:
    """Invalidate computation-related caches."""
    cache_manager = get_cache_manager()
    cache_manager.invalidate_cache('computation')
    logger.debug("Invalidated computation cache")