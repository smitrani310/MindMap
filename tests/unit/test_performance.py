"""
Unit tests for performance monitoring system.
"""

import pytest
import time
from unittest.mock import patch

from src.infrastructure.performance import (
    PerformanceMonitor, PerformanceMetric, get_performance_monitor,
    timed, performance_context, log_performance_summary
)


class TestPerformanceMonitor:
    """Test cases for PerformanceMonitor."""
    
    def test_monitor_initialization(self):
        """Test monitor initialization."""
        monitor = PerformanceMonitor(max_metrics=100)
        assert monitor.max_metrics == 100
        assert len(monitor._metrics) == 0
        assert len(monitor._operation_stats) == 0
    
    def test_record_metric(self):
        """Test recording a performance metric."""
        monitor = PerformanceMonitor()
        
        monitor.record_metric("test_operation", 150.5, success=True)
        
        assert len(monitor._metrics) == 1
        metric = monitor._metrics[0]
        assert metric.operation == "test_operation"
        assert metric.duration_ms == 150.5
        assert metric.success is True
        assert metric.error is None
    
    def test_record_failed_metric(self):
        """Test recording a failed operation metric."""
        monitor = PerformanceMonitor()
        
        monitor.record_metric("failed_operation", 75.0, success=False, error="Test error")
        
        assert len(monitor._metrics) == 1
        metric = monitor._metrics[0]
        assert metric.operation == "failed_operation"
        assert metric.success is False
        assert metric.error == "Test error"
    
    def test_operation_stats(self):
        """Test operation statistics calculation."""
        monitor = PerformanceMonitor()
        
        # Record multiple metrics for the same operation
        monitor.record_metric("test_op", 100.0, success=True)
        monitor.record_metric("test_op", 200.0, success=True)
        monitor.record_metric("test_op", 150.0, success=False, error="Test error")
        
        stats = monitor.get_operation_stats("test_op")
        
        assert stats is not None
        assert stats['count'] == 3
        assert stats['total_duration'] == 450.0
        assert stats['avg_duration'] == 150.0
        assert stats['min_duration'] == 100.0
        assert stats['max_duration'] == 200.0
        assert stats['success_count'] == 2
        assert stats['error_count'] == 1
        assert stats['success_rate'] == 2/3
        assert stats['error_rate'] == 1/3
    
    def test_nonexistent_operation_stats(self):
        """Test getting stats for non-existent operation."""
        monitor = PerformanceMonitor()
        stats = monitor.get_operation_stats("nonexistent")
        assert stats is None
    
    def test_get_all_stats(self):
        """Test getting all operation statistics."""
        monitor = PerformanceMonitor()
        
        monitor.record_metric("op1", 100.0)
        monitor.record_metric("op2", 200.0)
        
        all_stats = monitor.get_all_stats()
        
        assert len(all_stats) == 2
        assert "op1" in all_stats
        assert "op2" in all_stats
        assert all_stats["op1"]["count"] == 1
        assert all_stats["op2"]["count"] == 1
    
    def test_get_slow_operations(self):
        """Test getting slow operations."""
        monitor = PerformanceMonitor()
        
        monitor.record_metric("fast_op", 50.0)
        monitor.record_metric("slow_op1", 150.0)
        monitor.record_metric("slow_op2", 300.0)
        monitor.record_metric("medium_op", 75.0)
        
        slow_ops = monitor.get_slow_operations(threshold_ms=100, limit=10)
        
        assert len(slow_ops) == 2
        # Should be sorted by duration (descending)
        assert slow_ops[0].operation == "slow_op2"
        assert slow_ops[0].duration_ms == 300.0
        assert slow_ops[1].operation == "slow_op1"
        assert slow_ops[1].duration_ms == 150.0
    
    def test_get_recent_errors(self):
        """Test getting recent errors."""
        monitor = PerformanceMonitor()
        
        monitor.record_metric("success_op", 100.0, success=True)
        time.sleep(0.001)  # Small delay to ensure different timestamps
        monitor.record_metric("error_op1", 50.0, success=False, error="Error 1")
        time.sleep(0.001)  # Small delay to ensure different timestamps
        monitor.record_metric("error_op2", 75.0, success=False, error="Error 2")
        
        errors = monitor.get_recent_errors(limit=10)
        
        assert len(errors) == 2
        # Should be sorted by timestamp (most recent first)
        assert errors[0].operation == "error_op2"
        assert errors[1].operation == "error_op1"
    
    def test_clear_metrics(self):
        """Test clearing all metrics."""
        monitor = PerformanceMonitor()
        
        monitor.record_metric("test_op", 100.0)
        assert len(monitor._metrics) == 1
        assert len(monitor._operation_stats) == 1
        
        monitor.clear_metrics()
        
        assert len(monitor._metrics) == 0
        assert len(monitor._operation_stats) == 0
    
    def test_max_metrics_limit(self):
        """Test that metrics are limited to max_metrics."""
        monitor = PerformanceMonitor(max_metrics=3)
        
        # Add more metrics than the limit
        for i in range(5):
            monitor.record_metric(f"op_{i}", 100.0)
        
        # Should only keep the last 3 metrics
        assert len(monitor._metrics) == 3
        
        # Check that the oldest metrics were removed
        operations = [m.operation for m in monitor._metrics]
        assert "op_2" in operations
        assert "op_3" in operations
        assert "op_4" in operations
        assert "op_0" not in operations
        assert "op_1" not in operations


class TestTimedDecorator:
    """Test cases for the @timed decorator."""
    
    def test_timed_decorator_success(self):
        """Test timed decorator with successful function."""
        monitor = PerformanceMonitor()
        
        with patch('src.infrastructure.performance.get_performance_monitor', return_value=monitor):
            @timed(operation_name="test_function")
            def test_func():
                time.sleep(0.01)  # Sleep for 10ms
                return "success"
            
            result = test_func()
            
            assert result == "success"
            assert len(monitor._metrics) == 1
            
            metric = monitor._metrics[0]
            assert metric.operation == "test_function"
            assert metric.success is True
            assert metric.duration_ms >= 10  # Should be at least 10ms
    
    def test_timed_decorator_error(self):
        """Test timed decorator with function that raises exception."""
        monitor = PerformanceMonitor()
        
        with patch('src.infrastructure.performance.get_performance_monitor', return_value=monitor):
            @timed(operation_name="failing_function")
            def failing_func():
                raise ValueError("Test error")
            
            with pytest.raises(ValueError, match="Test error"):
                failing_func()
            
            assert len(monitor._metrics) == 1
            
            metric = monitor._metrics[0]
            assert metric.operation == "failing_function"
            assert metric.success is False
            assert metric.error == "Test error"
    
    def test_timed_decorator_default_name(self):
        """Test timed decorator with default operation name."""
        monitor = PerformanceMonitor()
        
        with patch('src.infrastructure.performance.get_performance_monitor', return_value=monitor):
            @timed()
            def my_function():
                return "result"
            
            result = my_function()
            
            assert result == "result"
            assert len(monitor._metrics) == 1
            
            metric = monitor._metrics[0]
            # Should use module.function_name format
            assert "my_function" in metric.operation


class TestPerformanceContext:
    """Test cases for PerformanceContext."""
    
    def test_performance_context_success(self):
        """Test performance context with successful operation."""
        monitor = PerformanceMonitor()
        
        with patch('src.infrastructure.performance.get_performance_monitor', return_value=monitor):
            with performance_context("test_context"):
                time.sleep(0.01)  # Sleep for 10ms
            
            assert len(monitor._metrics) == 1
            
            metric = monitor._metrics[0]
            assert metric.operation == "test_context"
            assert metric.success is True
            assert metric.duration_ms >= 10
    
    def test_performance_context_error(self):
        """Test performance context with exception."""
        monitor = PerformanceMonitor()
        
        with patch('src.infrastructure.performance.get_performance_monitor', return_value=monitor):
            with pytest.raises(ValueError, match="Test error"):
                with performance_context("failing_context"):
                    raise ValueError("Test error")
            
            assert len(monitor._metrics) == 1
            
            metric = monitor._metrics[0]
            assert metric.operation == "failing_context"
            assert metric.success is False
            assert metric.error == "Test error"
    
    def test_performance_context_with_metadata(self):
        """Test performance context with metadata."""
        monitor = PerformanceMonitor()
        
        with patch('src.infrastructure.performance.get_performance_monitor', return_value=monitor):
            with performance_context("test_context", metadata={"key": "value"}):
                pass
            
            assert len(monitor._metrics) == 1
            
            metric = monitor._metrics[0]
            assert metric.metadata == {"key": "value"}


class TestGlobalPerformanceMonitor:
    """Test cases for global performance monitor functions."""
    
    def test_get_performance_monitor_singleton(self):
        """Test that get_performance_monitor returns the same instance."""
        monitor1 = get_performance_monitor()
        monitor2 = get_performance_monitor()
        
        assert monitor1 is monitor2
    
    def test_log_performance_summary_empty(self):
        """Test logging performance summary with no metrics."""
        monitor = PerformanceMonitor()
        
        with patch('src.infrastructure.performance.get_performance_monitor', return_value=monitor):
            with patch('src.infrastructure.performance.logger') as mock_logger:
                log_performance_summary()
                
                mock_logger.info.assert_called_with("No performance metrics available")
    
    def test_log_performance_summary_with_data(self):
        """Test logging performance summary with metrics."""
        monitor = PerformanceMonitor()
        monitor.record_metric("test_op", 150.0, success=True)
        monitor.record_metric("slow_op", 500.0, success=True)
        
        with patch('src.infrastructure.performance.get_performance_monitor', return_value=monitor):
            with patch('src.infrastructure.performance.logger') as mock_logger:
                log_performance_summary()
                
                # Should log performance summary
                assert mock_logger.info.call_count >= 3  # Header + operations + slow ops