"""
Performance monitoring and optimization utilities.

This module provides tools for monitoring application performance,
measuring execution times, and identifying bottlenecks.
"""

import time
import logging
import functools
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import RLock
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Represents a performance metric measurement."""
    operation: str
    duration_ms: float
    timestamp: datetime
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceMonitor:
    """
    Performance monitoring system for tracking operation performance.
    
    Tracks execution times, success rates, and provides performance analytics.
    """
    
    def __init__(self, max_metrics: int = 10000):
        """
        Initialize the performance monitor.
        
        Args:
            max_metrics: Maximum number of metrics to keep in memory
        """
        self.max_metrics = max_metrics
        self._metrics: deque = deque(maxlen=max_metrics)
        self._operation_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'count': 0,
            'total_duration': 0.0,
            'min_duration': float('inf'),
            'max_duration': 0.0,
            'success_count': 0,
            'error_count': 0,
            'recent_durations': deque(maxlen=100)  # Keep last 100 for percentiles
        })
        self._lock = RLock()
        
        logger.info(f"PerformanceMonitor initialized with max_metrics={max_metrics}")
    
    def record_metric(self, operation: str, duration_ms: float, success: bool = True, 
                     error: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record a performance metric."""
        with self._lock:
            metric = PerformanceMetric(
                operation=operation,
                duration_ms=duration_ms,
                timestamp=datetime.now(),
                success=success,
                error=error,
                metadata=metadata or {}
            )
            
            self._metrics.append(metric)
            
            # Update operation statistics
            stats = self._operation_stats[operation]
            stats['count'] += 1
            stats['total_duration'] += duration_ms
            stats['min_duration'] = min(stats['min_duration'], duration_ms)
            stats['max_duration'] = max(stats['max_duration'], duration_ms)
            stats['recent_durations'].append(duration_ms)
            
            if success:
                stats['success_count'] += 1
            else:
                stats['error_count'] += 1
            
            # Log slow operations
            if duration_ms > 1000:  # Log operations taking more than 1 second
                logger.warning(f"Slow operation detected: {operation} took {duration_ms:.2f}ms")
            elif duration_ms > 100:  # Log operations taking more than 100ms
                logger.info(f"Operation {operation} took {duration_ms:.2f}ms")
    
    def get_operation_stats(self, operation: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific operation."""
        with self._lock:
            if operation not in self._operation_stats:
                return None
            
            stats = self._operation_stats[operation].copy()
            
            # Calculate derived metrics
            if stats['count'] > 0:
                stats['avg_duration'] = stats['total_duration'] / stats['count']
                stats['success_rate'] = stats['success_count'] / stats['count']
                stats['error_rate'] = stats['error_count'] / stats['count']
                
                # Calculate percentiles from recent durations
                recent = sorted(stats['recent_durations'])
                if recent:
                    stats['p50'] = self._percentile(recent, 50)
                    stats['p95'] = self._percentile(recent, 95)
                    stats['p99'] = self._percentile(recent, 99)
            else:
                stats['avg_duration'] = 0
                stats['success_rate'] = 0
                stats['error_rate'] = 0
                stats['p50'] = 0
                stats['p95'] = 0
                stats['p99'] = 0
            
            # Remove internal data structures from the returned stats
            stats.pop('recent_durations', None)
            
            return stats
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all operations."""
        with self._lock:
            return {op: self.get_operation_stats(op) for op in self._operation_stats.keys()}
    
    def get_slow_operations(self, threshold_ms: float = 100, limit: int = 10) -> List[PerformanceMetric]:
        """Get the slowest operations above the threshold."""
        with self._lock:
            slow_ops = [m for m in self._metrics if m.duration_ms >= threshold_ms]
            return sorted(slow_ops, key=lambda x: x.duration_ms, reverse=True)[:limit]
    
    def get_recent_errors(self, limit: int = 10) -> List[PerformanceMetric]:
        """Get recent failed operations."""
        with self._lock:
            errors = [m for m in self._metrics if not m.success]
            return sorted(errors, key=lambda x: x.timestamp, reverse=True)[:limit]
    
    def clear_metrics(self) -> None:
        """Clear all stored metrics."""
        with self._lock:
            self._metrics.clear()
            self._operation_stats.clear()
            logger.info("Performance metrics cleared")
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile from sorted data."""
        if not data:
            return 0.0
        
        k = (len(data) - 1) * percentile / 100
        f = int(k)
        c = k - f
        
        if f == len(data) - 1:
            return data[f]
        else:
            return data[f] * (1 - c) + data[f + 1] * c


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def timed(operation_name: Optional[str] = None, log_slow: bool = True, threshold_ms: float = 100):
    """
    Decorator for timing function execution.
    
    Args:
        operation_name: Name for the operation (defaults to function name)
        log_slow: Whether to log slow operations
        threshold_ms: Threshold for considering an operation slow
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            monitor = get_performance_monitor()
            
            start_time = time.time()
            success = True
            error = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000
                
                # Record the metric
                monitor.record_metric(
                    operation=op_name,
                    duration_ms=duration_ms,
                    success=success,
                    error=error,
                    metadata={
                        'args_count': len(args),
                        'kwargs_count': len(kwargs)
                    }
                )
                
                # Log if slow and logging is enabled
                if log_slow and duration_ms >= threshold_ms:
                    logger.info(f"Operation {op_name} took {duration_ms:.2f}ms")
        
        return wrapper
    return decorator


class PerformanceContext:
    """Context manager for timing code blocks."""
    
    def __init__(self, operation_name: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize the performance context.
        
        Args:
            operation_name: Name of the operation being timed
            metadata: Additional metadata to record
        """
        self.operation_name = operation_name
        self.metadata = metadata or {}
        self.start_time: Optional[float] = None
        self.monitor = get_performance_monitor()
    
    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing and record metric."""
        if self.start_time is None:
            return
        
        end_time = time.time()
        duration_ms = (end_time - self.start_time) * 1000
        
        success = exc_type is None
        error = str(exc_val) if exc_val else None
        
        self.monitor.record_metric(
            operation=self.operation_name,
            duration_ms=duration_ms,
            success=success,
            error=error,
            metadata=self.metadata
        )


def performance_context(operation_name: str, metadata: Optional[Dict[str, Any]] = None) -> PerformanceContext:
    """Create a performance timing context manager."""
    return PerformanceContext(operation_name, metadata)


def log_performance_summary(logger_instance: Optional[logging.Logger] = None) -> None:
    """Log a summary of performance statistics."""
    if logger_instance is None:
        logger_instance = logger
    
    monitor = get_performance_monitor()
    all_stats = monitor.get_all_stats()
    
    if not all_stats:
        logger_instance.info("No performance metrics available")
        return
    
    logger_instance.info("=== Performance Summary ===")
    
    for operation, stats in all_stats.items():
        logger_instance.info(
            f"{operation}: "
            f"count={stats['count']}, "
            f"avg={stats['avg_duration']:.2f}ms, "
            f"p95={stats['p95']:.2f}ms, "
            f"success_rate={stats['success_rate']:.2%}"
        )
    
    # Log slow operations
    slow_ops = monitor.get_slow_operations(threshold_ms=100, limit=5)
    if slow_ops:
        logger_instance.info("=== Slowest Operations ===")
        for metric in slow_ops:
            logger_instance.info(
                f"{metric.operation}: {metric.duration_ms:.2f}ms at {metric.timestamp}"
            )
    
    # Log recent errors
    errors = monitor.get_recent_errors(limit=5)
    if errors:
        logger_instance.info("=== Recent Errors ===")
        for metric in errors:
            logger_instance.info(
                f"{metric.operation}: {metric.error} at {metric.timestamp}"
            )