"""
Unit tests for logging configuration system.
"""

import pytest
import logging
import json
import uuid
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from pathlib import Path

from src.infrastructure.logging_config import (
    CorrelationIdFilter, JSONFormatter, PerformanceFilter,
    MindMapLoggerAdapter, LoggingConfig,
    setup_logging, get_logger, correlation_context, performance_context,
    log_slow_operation, log_error_with_context, create_audit_log,
    setup_default_logging
)


class TestCorrelationIdFilter:
    """Test cases for CorrelationIdFilter."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.filter = CorrelationIdFilter()
    
    def test_filter_adds_correlation_id(self):
        """Test that filter adds correlation ID to log records."""
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=(), exc_info=None
        )
        
        result = self.filter.filter(record)
        
        assert result is True
        assert hasattr(record, 'correlation_id')
        assert len(record.correlation_id) == 8  # UUID first 8 chars
    
    def test_filter_uses_set_correlation_id(self):
        """Test that filter uses manually set correlation ID."""
        test_id = "test123"
        self.filter.set_correlation_id(test_id)
        
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=(), exc_info=None
        )
        
        self.filter.filter(record)
        
        assert record.correlation_id == test_id
    
    def test_clear_correlation_id(self):
        """Test clearing correlation ID."""
        self.filter.set_correlation_id("test123")
        self.filter.clear_correlation_id()
        
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=(), exc_info=None
        )
        
        self.filter.filter(record)
        
        # Should generate new ID, not use the cleared one
        assert record.correlation_id != "test123"
        assert len(record.correlation_id) == 8


class TestJSONFormatter:
    """Test cases for JSONFormatter."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = JSONFormatter()
    
    def test_format_basic_record(self):
        """Test formatting basic log record."""
        record = logging.LogRecord(
            name="test.module", level=logging.INFO, pathname="/path/test.py",
            lineno=42, msg="Test message", args=(), exc_info=None
        )
        record.correlation_id = "test123"
        
        result = self.formatter.format(record)
        
        # Should be valid JSON
        log_data = json.loads(result)
        
        assert log_data['level'] == 'INFO'
        assert log_data['logger'] == 'test.module'
        assert log_data['message'] == 'Test message'
        assert log_data['module'] == 'test'
        assert log_data['line'] == 42
        assert log_data['correlation_id'] == 'test123'
        assert 'timestamp' in log_data
    
    def test_format_record_with_exception(self):
        """Test formatting record with exception info."""
        try:
            raise ValueError("Test exception")
        except ValueError:
            exc_info = True
        
        record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="", lineno=0,
            msg="Error occurred", args=(), exc_info=exc_info
        )
        record.correlation_id = "test123"
        
        result = self.formatter.format(record)
        log_data = json.loads(result)
        
        assert 'exception' in log_data
        assert log_data['exception']['type'] == 'ValueError'
        assert log_data['exception']['message'] == 'Test exception'
        assert 'traceback' in log_data['exception']
    
    def test_format_record_with_extra_fields(self):
        """Test formatting record with extra fields."""
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Test message", args=(), exc_info=None
        )
        record.correlation_id = "test123"
        record.user_id = "user456"
        record.operation_name = "test_operation"
        record.custom_data = {"key": "value"}
        
        result = self.formatter.format(record)
        log_data = json.loads(result)
        
        assert 'extra' in log_data
        assert log_data['extra']['user_id'] == 'user456'
        assert log_data['extra']['operation_name'] == 'test_operation'
        assert log_data['extra']['custom_data'] == {"key": "value"}
    
    def test_format_record_exclude_extra(self):
        """Test formatting record with extra fields disabled."""
        formatter = JSONFormatter(include_extra=False)
        
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Test message", args=(), exc_info=None
        )
        record.correlation_id = "test123"
        record.user_id = "user456"
        
        result = formatter.format(record)
        log_data = json.loads(result)
        
        assert 'extra' not in log_data
    
    def test_format_record_non_serializable_extra(self):
        """Test formatting record with non-serializable extra fields."""
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Test message", args=(), exc_info=None
        )
        record.correlation_id = "test123"
        record.non_serializable = object()  # Can't be JSON serialized
        
        result = self.formatter.format(record)
        log_data = json.loads(result)
        
        # Should convert to string
        assert 'extra' in log_data
        assert isinstance(log_data['extra']['non_serializable'], str)


class TestPerformanceFilter:
    """Test cases for PerformanceFilter."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.filter = PerformanceFilter()
    
    def test_filter_without_operation(self):
        """Test filter when no operation is started."""
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=(), exc_info=None
        )
        
        result = self.filter.filter(record)
        
        assert result is True
        assert not hasattr(record, 'operation_duration_ms')
        assert not hasattr(record, 'operation_name')
    
    def test_filter_with_operation(self):
        """Test filter when operation is started."""
        self.filter.start_operation("test_operation")
        
        # Simulate some time passing
        import time
        time.sleep(0.01)
        
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=(), exc_info=None
        )
        
        result = self.filter.filter(record)
        
        assert result is True
        assert hasattr(record, 'operation_duration_ms')
        assert hasattr(record, 'operation_name')
        assert record.operation_name == "test_operation"
        assert record.operation_duration_ms > 0
    
    def test_end_operation(self):
        """Test ending operation timing."""
        self.filter.start_operation("test_operation")
        self.filter.end_operation()
        
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=(), exc_info=None
        )
        
        result = self.filter.filter(record)
        
        assert result is True
        assert not hasattr(record, 'operation_duration_ms')
        assert not hasattr(record, 'operation_name')


class TestMindMapLoggerAdapter:
    """Test cases for MindMapLoggerAdapter."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.logger = Mock(spec=logging.Logger)
        self.adapter = MindMapLoggerAdapter(self.logger, {'component': 'test'})
    
    def test_process_adds_extra_context(self):
        """Test that process method adds extra context."""
        msg, kwargs = self.adapter.process("test message", {})
        
        assert msg == "test message"
        assert 'extra' in kwargs
        assert kwargs['extra']['component'] == 'test'
    
    def test_process_merges_extra_context(self):
        """Test that process method merges extra context."""
        msg, kwargs = self.adapter.process(
            "test message", 
            {'extra': {'user_id': 'user123'}}
        )
        
        assert kwargs['extra']['component'] == 'test'
        assert kwargs['extra']['user_id'] == 'user123'
    
    def test_with_context(self):
        """Test creating adapter with additional context."""
        new_adapter = self.adapter.with_context(user_id='user456', operation='test_op')
        
        assert new_adapter.extra['component'] == 'test'
        assert new_adapter.extra['user_id'] == 'user456'
        assert new_adapter.extra['operation'] == 'test_op'
        
        # Original adapter should be unchanged
        assert 'user_id' not in self.adapter.extra


class TestLoggingConfig:
    """Test cases for LoggingConfig."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_log_dir = Path("test_logs")
    
    def teardown_method(self):
        """Clean up test fixtures."""
        # Clean up test log directory
        import shutil
        if self.temp_log_dir.exists():
            shutil.rmtree(self.temp_log_dir)
    
    def test_logging_config_initialization(self):
        """Test LoggingConfig initialization."""
        config = LoggingConfig(
            log_level="DEBUG",
            log_dir=str(self.temp_log_dir),
            max_file_size=1024,
            backup_count=3
        )
        
        assert config.log_level == "DEBUG"
        assert config.log_dir == self.temp_log_dir
        assert config.max_file_size == 1024
        assert config.backup_count == 3
        assert config.console_logging is True
        assert config.file_logging is True
    
    def test_logging_config_creates_log_directory(self):
        """Test that LoggingConfig creates log directory."""
        config = LoggingConfig(log_dir=str(self.temp_log_dir))
        
        assert self.temp_log_dir.exists()
    
    @patch('logging.getLogger')
    def test_setup_logging_basic(self, mock_get_logger):
        """Test basic logging setup."""
        mock_root_logger = Mock()
        mock_get_logger.return_value = mock_root_logger
        
        config = LoggingConfig(
            log_level="INFO",
            log_dir=str(self.temp_log_dir),
            file_logging=False  # Disable file logging for simpler test
        )
        
        config.setup_logging()
        
        # Check that root logger was configured
        mock_root_logger.setLevel.assert_called_with(logging.INFO)
        mock_root_logger.handlers.clear.assert_called_once()
        
        # Check that at least one handler was added (console)
        assert mock_root_logger.addHandler.called
    
    @patch('logging.getLogger')
    def test_setup_logging_with_file_handlers(self, mock_get_logger):
        """Test logging setup with file handlers."""
        mock_root_logger = Mock()
        mock_get_logger.return_value = mock_root_logger
        
        config = LoggingConfig(
            log_level="DEBUG",
            log_dir=str(self.temp_log_dir),
            console_logging=False,
            file_logging=True
        )
        
        config.setup_logging()
        
        # Should add multiple file handlers (app, error, performance)
        assert mock_root_logger.addHandler.call_count >= 2
    
    def test_get_correlation_filter(self):
        """Test getting correlation filter."""
        config = LoggingConfig(correlation_ids=True)
        config.setup_logging()
        
        correlation_filter = config.get_correlation_filter()
        
        assert correlation_filter is not None
        assert isinstance(correlation_filter, CorrelationIdFilter)
    
    def test_get_performance_filter(self):
        """Test getting performance filter."""
        config = LoggingConfig(performance_logging=True)
        config.setup_logging()
        
        performance_filter = config.get_performance_filter()
        
        assert performance_filter is not None
        assert isinstance(performance_filter, PerformanceFilter)


class TestLoggingUtilities:
    """Test cases for logging utility functions."""
    
    @patch('src.infrastructure.logging_config._logging_config')
    def test_setup_logging(self, mock_config):
        """Test setup_logging function."""
        result = setup_logging(
            log_level="DEBUG",
            log_dir="test_logs",
            json_format=False
        )
        
        assert isinstance(result, LoggingConfig)
        assert result.log_level == "DEBUG"
        assert result.json_format is False
    
    @patch('logging.getLogger')
    def test_get_logger(self, mock_get_logger):
        """Test get_logger function."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        result = get_logger("test.module", user_id="user123")
        
        assert isinstance(result, MindMapLoggerAdapter)
        assert result.extra['user_id'] == "user123"
        mock_get_logger.assert_called_with("test.module")
    
    @patch('src.infrastructure.logging_config._logging_config')
    def test_correlation_context_without_config(self, mock_config):
        """Test correlation_context when no config is set."""
        mock_config = None
        
        with correlation_context() as correlation_id:
            # Should still work, just not set correlation ID
            pass
    
    @patch('src.infrastructure.logging_config._logging_config')
    def test_correlation_context_with_config(self, mock_config):
        """Test correlation_context with logging config."""
        mock_filter = Mock()
        mock_logging_config = Mock()
        mock_logging_config.get_correlation_filter.return_value = mock_filter
        mock_config = mock_logging_config
        
        test_id = "test123"
        
        with correlation_context(test_id) as correlation_id:
            assert correlation_id == test_id
            mock_filter.set_correlation_id.assert_called_with(test_id)
        
        mock_filter.clear_correlation_id.assert_called_once()
    
    @patch('src.infrastructure.logging_config._logging_config')
    def test_correlation_context_generates_id(self, mock_config):
        """Test correlation_context generates ID when none provided."""
        mock_filter = Mock()
        mock_logging_config = Mock()
        mock_logging_config.get_correlation_filter.return_value = mock_filter
        mock_config = mock_logging_config
        
        with correlation_context() as correlation_id:
            assert correlation_id is not None
            assert len(correlation_id) == 8
            mock_filter.set_correlation_id.assert_called_with(correlation_id)
    
    @patch('src.infrastructure.logging_config._logging_config')
    def test_performance_context(self, mock_config):
        """Test performance_context context manager."""
        mock_filter = Mock()
        mock_logging_config = Mock()
        mock_logging_config.get_performance_filter.return_value = mock_filter
        mock_config = mock_logging_config
        
        with performance_context("test_operation"):
            mock_filter.start_operation.assert_called_with("test_operation")
        
        mock_filter.end_operation.assert_called_once()
    
    @patch('src.infrastructure.logging_config.get_logger')
    def test_log_slow_operation(self, mock_get_logger):
        """Test log_slow_operation function."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        log_slow_operation("slow_op", 2000.0, 1000.0)
        
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert "slow_op" in call_args[0][0]
        assert "2000.00ms" in call_args[0][0]
        
        # Check extra data
        extra = call_args[1]['extra']
        assert extra['operation_name'] == 'slow_op'
        assert extra['duration_ms'] == 2000.0
        assert extra['threshold_ms'] == 1000.0
        assert extra['performance_issue'] is True
    
    @patch('src.infrastructure.logging_config.get_logger')
    def test_log_slow_operation_not_slow(self, mock_get_logger):
        """Test log_slow_operation when operation is not slow."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        log_slow_operation("fast_op", 500.0, 1000.0)
        
        # Should not log anything
        mock_logger.warning.assert_not_called()
    
    @patch('src.infrastructure.logging_config.get_logger')
    def test_log_error_with_context(self, mock_get_logger):
        """Test log_error_with_context function."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        error = ValueError("Test error")
        context = {"user_id": "user123", "operation": "test_op"}
        
        log_error_with_context(error, context, "test.module")
        
        mock_get_logger.assert_called_with("test.module", user_id="user123", operation="test_op")
        mock_logger.error.assert_called_once()
        
        call_args = mock_logger.error.call_args
        assert "Test error" in call_args[0][0]
        assert call_args[1]['exc_info'] is True
        
        extra = call_args[1]['extra']
        assert extra['error_type'] == 'ValueError'
        assert extra['error_message'] == 'Test error'
    
    @patch('src.infrastructure.logging_config.get_logger')
    def test_create_audit_log(self, mock_get_logger):
        """Test create_audit_log function."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        create_audit_log(
            "CREATE",
            "node",
            user_id="user123",
            node_id=456,
            node_title="Test Node"
        )
        
        mock_get_logger.assert_called_with('audit')
        mock_logger.info.assert_called_once()
        
        call_args = mock_logger.info.call_args
        assert "CREATE on node" in call_args[0][0]
        
        extra = call_args[1]['extra']
        assert extra['audit_action'] == 'CREATE'
        assert extra['audit_resource'] == 'node'
        assert extra['audit_user_id'] == 'user123'
        assert 'audit_timestamp' in extra
        assert extra['audit_details']['node_id'] == 456
        assert extra['audit_details']['node_title'] == 'Test Node'
    
    @patch('src.infrastructure.logging_config.get_logger')
    def test_log_function_entry(self, mock_get_logger):
        """Test log_function_entry function."""
        from src.infrastructure.logging_config import log_function_entry
        
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        log_function_entry("test_function", (1, 2), {"key": "value"})
        
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        assert "Entering function: test_function" in call_args[0][0]
        
        extra = call_args[1]['extra']
        assert extra['function_name'] == 'test_function'
        assert extra['args_count'] == 2
        assert extra['kwargs_count'] == 1
    
    @patch('src.infrastructure.logging_config.get_logger')
    def test_log_function_exit(self, mock_get_logger):
        """Test log_function_exit function."""
        from src.infrastructure.logging_config import log_function_exit
        
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        log_function_exit("test_function", "result", 123.45)
        
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        assert "Exiting function: test_function" in call_args[0][0]
        
        extra = call_args[1]['extra']
        assert extra['function_name'] == 'test_function'
        assert extra['has_result'] is True
        assert extra['duration_ms'] == 123.45
    
    @patch.dict('os.environ', {'LOG_LEVEL': 'DEBUG', 'ENVIRONMENT': 'production'})
    @patch('src.infrastructure.logging_config.setup_logging')
    def test_setup_default_logging(self, mock_setup_logging):
        """Test setup_default_logging function."""
        setup_default_logging()
        
        mock_setup_logging.assert_called_once_with(
            log_level='DEBUG',
            log_dir='logs',
            json_format=True,  # Production environment
            console_logging=True,
            file_logging=True
        )
    
    @patch.dict('os.environ', {'ENVIRONMENT': 'development'})
    @patch('src.infrastructure.logging_config.setup_logging')
    def test_setup_default_logging_development(self, mock_setup_logging):
        """Test setup_default_logging in development mode."""
        setup_default_logging()
        
        mock_setup_logging.assert_called_once_with(
            log_level='INFO',  # Default when LOG_LEVEL not set
            log_dir='logs',
            json_format=False,  # Development environment
            console_logging=True,
            file_logging=True
        )