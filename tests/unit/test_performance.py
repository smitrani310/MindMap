"""
Unit tests for performance monitoring infrastructure.
"""

import pytest
import time
from datetime import datetime
from unittest.mock import Mock, patch

from src.infrastructure.performance import (
    PerformanceMetric, PerformanceMonitor, PerformanceContext,
    timed, performance_context, get_performance_monitor, log_performance_summary
)


class TestPerformanceMetric:
    """Test cases for PerformanceMetric."""
    
    def test_performance_metric_creation(self):
        """Test creating a performance metric."""
        metric = PerformanceMetric(
            operation="test_operation",
            duration_ms=123.45,
            timestamp=datetime.now(),
            success=True,
            metadata={"key": "value"}
        )
        
        assert metric.operation == "test_operation"
        assert metric.duration_ms == 123.45
        assert metric.success == True
        assert metric.error is None
        assert metric.metadata["key"] == "value"
    
    def test_performance_metric_with_error(self):
        """Test creating a performance metric with error."""
        metric = PerformanceMetric(
            operation="error_operation",
            duration_ms=50.0,
            timestamp=datetime.now(),
            success=False,
            error="Test error message"
        )
        
        assert metric.operation == "error_operation"
        assert metric.success == False
        assert metric.error == "Test error message"


class TestPerformanceMonitor:
    """Test cases for PerformanceMonitor."""
    
    @pytest.fixture
    def monitor(self):
        """Create performance monitor for testing."""
        return PerformanceMonitor(max_metrics=100)
    
    def test_monitor_initialization(self, monitor):
        """Test performance monitor initialization."""
        assert monitor.max_metrics == 100
        assert len(monitor._metrics) == 0
        assert len(monitor._operation_stats) == 0
    
    def test_record_metric_success(self, monitor):
        """Test recording successful metrics."""
        monitor.record_metric("test_op", 150.5, success=True, metadata={"test": "data"})
        
        assert len(monitor._metrics) == 1
        metric = monitor._metrics[0]
        assert metric.operation == "test_op"
        assert metric.duration_ms == 150.5
        assert metric.success == True
        assert metric.metadata["test"] == "data"
        
        # Check operation stats
        stats = monitor.get_operation_stats("test_op")
        assert stats is not None
        assert stats['count'] == 1
        assert stats['total_duration'] == 150.5
        assert stats['success_count'] == 1
        assert stats['error_count'] == 0
    
    def test_record_metric_error(self, monitor):
        """Test recording error metrics."""
        monitor.record_metric("error_op", 75.0, success=False, error="Test error")
        
        stats = monitor.get_operation_stats("error_op")
        assert stats is not None
        assert stats['count'] == 1
        assert stats['success_count'] == 0
        assert stats['error_count'] == 1
        assert stats['error_rate'] == 1.0
    
    def test_operation_stats_calculation(self, monitor):
        """Test operation statistics calculation."""
        # Record multiple metrics for the same operation
        monitor.record_metric("calc_op", 100.0, success=True)
        monitor.record_metric("calc_op", 200.0, success=True)
        monitor.record_metric("calc_op", 150.0, success=False, error="Error")
        
        stats = monitor.get_operation_stats("calc_op")
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
        
        # Check percentiles are calculated
        assert 'p50' in stats
        assert 'p95' in stats
        assert 'p99' in stats
    
    def test_get_operation_stats_nonexistent(self, monitor):
        """Test getting stats for non-existent operation."""
        stats = monitor.get_operation_stats("nonexistent")
        assert stats is None
    
    def test_get_all_stats(self, monitor):
        """Test getting all operation statistics."""
        monitor.record_metric("op1", 100.0)
        monitor.record_metric("op2", 200.0)
        
        all_stats = monitor.get_all_stats()
        assert len(all_stats) == 2
        assert "op1" in all_stats
        assert "op2" in all_stats
        assert all_stats["op1"]["count"] == 1
        assert all_stats["op2"]["count"] == 1
    
    def test_get_slow_operations(self, monitor):
        """Test getting slow operations."""
        monitor.record_metric("fast_op", 50.0)
        monitor.record_metric("slow_op1", 150.0)
        monitor.record_metric("slow_op2", 300.0)
        monitor.record_metric("very_slow_op", 500.0)
        
        slow_ops = monitor.get_slow_operations(threshold_ms=100, limit=2)
        assert len(slow_ops) == 2
        
        # Should be sorted by duration (descending)
        assert slow_ops[0].operation == "very_slow_op"
        assert slow_ops[0].duration_ms == 500.0
        assert slow_ops[1].operation == "slow_op2"
        assert slow_ops[1].duration_ms == 300.0
    
    def test_get_recent_errors(self, monitor):
        """Test getting recent errors."""
        monitor.record_metric("success_op", 100.0, success=True)
        monitor.record_metric("error_op1", 150.0, success=False, error="Error 1")
        time.sleep(0.01)  # Small delay to ensure different timestamps
        monitor.record_metric("error_op2", 200.0, success=False, error="Error 2")
        
        errors = monitor.get_recent_errors(limit=5)
        assert len(errors) == 2
        
        # Should be sorted by timestamp (most recent first)
        assert errors[0].operation == "error_op2"
        assert errors[1].operation == "error_op1"
    
    def test_clear_metrics(self, monitor):
        """Test clearing metrics."""
        monitor.record_metric("test_op", 100.0)
        assert len(monitor._metrics) == 1
        assert len(monitor._operation_stats) == 1
        
        monitor.clear_metrics()
        assert len(monitor._metrics) == 0
        assert len(monitor._operation_stats) == 0
    
    def test_percentile_calculation(self, monitor):
        """Test percentile calculation."""
        # Test with empty data
        assert monitor._percentile([], 50) == 0.0
        
        # Test with single value
        assert monitor._percentile([100.0], 50) == 100.0
        
        # Test with multiple values
        data = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        assert monitor._percentile(data, 50) == 55.0  # Median
        assert monitor._percentile(data, 90) == 91.0  # 90th percentile


class TestTimedDecorator:
    """Test cases for timed decorator."""
    
    def test_timed_decorator_success(self):
        """Test timed decorator with successful operation."""
        monitor = get_performance_monitor()
        monitor.clear_metrics()  # Start fresh
        
        @timed("test_function")
        def test_function(value):
            time.sleep(0.01)  # Small delay
            return value * 2
        
        result = test_function(5)
        assert result == 10
        
        stats = monitor.get_operation_stats("test_function")
        assert stats is not None
        assert stats['count'] == 1
        assert stats['success_count'] == 1
        assert stats['error_count'] == 0
        assert stats['avg_duration'] > 0
    
    def test_timed_decorator_error(self):
        """Test timed decorator with error."""
        monitor = get_performance_monitor()
        monitor.clear_metrics()
        
        @timed("error_function")
        def error_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            error_function()
        
        stats = monitor.get_operation_stats("error_function")
        assert stats is not None
        assert stats['count'] == 1
        assert stats['success_count'] == 0
        assert stats['error_count'] == 1
    
    def test_timed_decorator_default_name(self):
        """Test timed decorator with default operation name."""
        monitor = get_performance_monitor()
        monitor.clear_metrics()
        
        @timed()
        def another_function():
            return "test"
        
        result = another_function()
        assert result == "test"
        
        # Should use module.function_name as operation name
        expected_name = f"{another_function.__module__}.another_function"
        stats = monitor.get_operation_stats(expected_name)
        assert stats is not None
        assert stats['count'] == 1


class TestPerformanceContext:
    """Test cases for PerformanceContext."""
    
    def test_performance_context_success(self):
        """Test performance context with successful operation."""
        monitor = get_performance_monitor()
        monitor.clear_metrics()
        
        with PerformanceContext("context_test", {"key": "value"}):
            time.sleep(0.01)  # Small delay
        
        stats = monitor.get_operation_stats("context_test")
        assert stats is not None
        assert stats['count'] == 1
        assert stats['success_count'] == 1
        assert stats['error_count'] == 0
    
    def test_performance_context_error(self):
        """Test performance context with error."""
        monitor = get_performance_monitor()
        monitor.clear_metrics()
        
        with pytest.raises(RuntimeError):
            with PerformanceContext("context_error"):
                raise RuntimeError("Test error")
        
        stats = monitor.get_operation_stats("context_error")
        assert stats is not None
        assert stats['count'] == 1
        assert stats['success_count'] == 0
        assert stats['error_count'] == 1
    
    def test_performance_context_function(self):
        """Test performance_context function."""
        monitor = get_performance_monitor()
        monitor.clear_metrics()
        
        with performance_context("function_test", {"meta": "data"}):
            time.sleep(0.01)
        
        stats = monitor.get_operation_stats("function_test")
        assert stats is not None
        assert stats['count'] == 1


class TestGlobalPerformanceMonitor:
    """Test cases for global performance monitor functions."""
    
    def test_get_performance_monitor_singleton(self):
        """Test that get_performance_monitor returns singleton."""
        monitor1 = get_performance_monitor()
        monitor2 = get_performance_monitor()
        
        assert monitor1 is monitor2
        assert monitor1 is not None


class TestLogPerformanceSummary:
    """Test cases for log_performance_summary function."""
    
    @patch('src.infrastructure.performance.logger')
    def test_log_performance_summary_with_data(self, mock_logger):
        """Test logging performance summary with data."""
        monitor = get_performance_monitor()
        monitor.clear_metrics()
        
        # Add some test data
        monitor.record_metric("test_op", 150.0, success=True)
        monitor.record_metric("slow_op", 250.0, success=True)
        monitor.record_metric("error_op", 100.0, success=False, error="Test error")
        
        log_performance_summary()
        
        # Verify that logger.info was called
        assert mock_logger.info.called
        
        # Check that summary header was logged
        calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any("Performance Summary" in call for call in calls)
    
    @patch('src.infrastructure.performance.logger')
    def test_log_performance_summary_no_data(self, mock_logger):
        """Test logging performance summary with no data."""
        monitor = get_performance_monitor()
        monitor.clear_metrics()
        
        log_performance_summary()
        
        # Should log that no metrics are available
        mock_logger.info.assert_called_with("No performance metrics available")
    
    def test_log_performance_summary_custom_logger(self):
        """Test logging performance summary with custom logger."""
        custom_logger = Mock()
        monitor = get_performance_monitor()
        monitor.clear_metrics()
        
        monitor.record_metric("test_op", 100.0)
        
        log_performance_summary(custom_logger)
        
        # Verify custom logger was used
        assert custom_logger.info.called


if __name__ == "__main__":
    pytest.main([__file__])