"""
Unit tests for centralized error handler.
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.infrastructure.errors import (
    MindMapError, ErrorCode, ErrorSeverity, ErrorContext,
    ValidationError, DataLoadError
)
from src.infrastructure.error_handler import (
    ErrorHandler, get_error_handler, handle_error,
    error_context, with_error_handling,
    setup_default_recovery_handlers, create_error_report
)


class TestErrorHandler:
    """Test cases for ErrorHandler class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.logger = Mock(spec=logging.Logger)
        self.error_handler = ErrorHandler(self.logger)
    
    def test_error_handler_initialization(self):
        """Test error handler initialization."""
        handler = ErrorHandler()
        
        assert handler.logger is not None
        assert handler.error_callbacks == []
        assert handler.recovery_handlers == {}
        assert handler.error_stats['total_errors'] == 0
    
    def test_register_error_callback(self):
        """Test registering error callbacks."""
        callback = Mock()
        
        self.error_handler.register_error_callback(callback)
        
        assert callback in self.error_handler.error_callbacks
        self.logger.info.assert_called_once()
    
    def test_register_recovery_handler(self):
        """Test registering recovery handlers."""
        handler = Mock()
        
        self.error_handler.register_recovery_handler(ErrorCode.CACHE_ERROR, handler)
        
        assert self.error_handler.recovery_handlers[ErrorCode.CACHE_ERROR] == handler
        self.logger.info.assert_called_once()
    
    def test_handle_mindmap_error(self):
        """Test handling MindMapError."""
        context = ErrorContext(operation="test", component="test")
        error = MindMapError(
            "Test error",
            error_code=ErrorCode.VALIDATION_ERROR,
            context=context
        )
        
        result = self.error_handler.handle_error(error)
        
        # Check error stats were updated
        assert self.error_handler.error_stats['total_errors'] == 1
        assert self.error_handler.error_stats['errors_by_code']['VALIDATION_ERROR'] == 1
        
        # Check logging was called
        self.logger.log.assert_called()
        
        assert result is None  # No recovery handler registered
    
    def test_handle_generic_exception(self):
        """Test handling generic exception."""
        context = ErrorContext(operation="test", component="test")
        generic_error = ValueError("Generic error")
        
        result = self.error_handler.handle_error(generic_error, context=context)
        
        # Check error was wrapped
        assert self.error_handler.error_stats['total_errors'] == 1
        assert 'INTERNAL_ERROR' in self.error_handler.error_stats['errors_by_code']
        
        # Check logging was called
        self.logger.log.assert_called()
        
        assert result is None
    
    def test_error_callback_execution(self):
        """Test that error callbacks are executed."""
        callback1 = Mock()
        callback2 = Mock()
        
        self.error_handler.register_error_callback(callback1)
        self.error_handler.register_error_callback(callback2)
        
        error = MindMapError("Test error")
        self.error_handler.handle_error(error)
        
        callback1.assert_called_once_with(error)
        callback2.assert_called_once_with(error)
    
    def test_error_callback_failure_handling(self):
        """Test handling of callback failures."""
        failing_callback = Mock(side_effect=Exception("Callback failed"))
        working_callback = Mock()
        
        self.error_handler.register_error_callback(failing_callback)
        self.error_handler.register_error_callback(working_callback)
        
        error = MindMapError("Test error")
        self.error_handler.handle_error(error)
        
        # Both callbacks should be called despite one failing
        failing_callback.assert_called_once()
        working_callback.assert_called_once()
        
        # Warning should be logged for failed callback
        self.logger.warning.assert_called()
    
    def test_recovery_handler_success(self):
        """Test successful recovery handler execution."""
        recovery_handler = Mock(return_value="recovery_result")
        self.error_handler.register_recovery_handler(ErrorCode.CACHE_ERROR, recovery_handler)
        
        error = MindMapError("Cache error", error_code=ErrorCode.CACHE_ERROR)
        result = self.error_handler.handle_error(error)
        
        recovery_handler.assert_called_once_with(error)
        assert result == "recovery_result"
        
        # Check success logging
        info_calls = [call for call in self.logger.info.call_args_list if "Recovery successful" in str(call)]
        assert len(info_calls) > 0
    
    def test_recovery_handler_failure(self):
        """Test recovery handler failure handling."""
        recovery_handler = Mock(side_effect=Exception("Recovery failed"))
        self.error_handler.register_recovery_handler(ErrorCode.CACHE_ERROR, recovery_handler)
        
        error = MindMapError("Cache error", error_code=ErrorCode.CACHE_ERROR)
        result = self.error_handler.handle_error(error)
        
        recovery_handler.assert_called_once_with(error)
        assert result is None
        
        # Check failure logging
        self.logger.error.assert_called()
    
    def test_error_stats_tracking(self):
        """Test error statistics tracking."""
        # Handle different types of errors
        error1 = MindMapError("Error 1", error_code=ErrorCode.VALIDATION_ERROR, severity=ErrorSeverity.LOW)
        error2 = MindMapError("Error 2", error_code=ErrorCode.VALIDATION_ERROR, severity=ErrorSeverity.HIGH)
        error3 = MindMapError("Error 3", error_code=ErrorCode.CACHE_ERROR, severity=ErrorSeverity.MEDIUM)
        
        self.error_handler.handle_error(error1)
        self.error_handler.handle_error(error2)
        self.error_handler.handle_error(error3)
        
        stats = self.error_handler.get_error_stats()
        
        assert stats['total_errors'] == 3
        assert stats['errors_by_code']['VALIDATION_ERROR'] == 2
        assert stats['errors_by_code']['CACHE_ERROR'] == 1
        assert stats['errors_by_severity']['low'] == 1
        assert stats['errors_by_severity']['high'] == 1
        assert stats['errors_by_severity']['medium'] == 1
        assert len(stats['recent_errors']) == 3
    
    def test_recent_errors_limit(self):
        """Test that recent errors are limited to 100."""
        # Create more than 100 errors
        for i in range(150):
            error = MindMapError(f"Error {i}")
            self.error_handler.handle_error(error, notify_user=False)
        
        stats = self.error_handler.get_error_stats()
        
        assert stats['total_errors'] == 150
        assert len(stats['recent_errors']) == 100
        
        # Check that the most recent errors are kept
        recent_messages = [err['message'] for err in stats['recent_errors']]
        assert "Error 149" in recent_messages
        assert "Error 50" in recent_messages
        assert "Error 49" not in recent_messages
    
    def test_get_recent_errors(self):
        """Test getting recent errors with limit."""
        for i in range(20):
            error = MindMapError(f"Error {i}")
            self.error_handler.handle_error(error, notify_user=False)
        
        recent_errors = self.error_handler.get_recent_errors(5)
        
        assert len(recent_errors) == 5
        # Should get the 5 most recent errors
        messages = [err['message'] for err in recent_errors]
        assert "Error 19" in messages
        assert "Error 15" in messages
        assert "Error 14" not in messages
    
    def test_clear_error_stats(self):
        """Test clearing error statistics."""
        error = MindMapError("Test error")
        self.error_handler.handle_error(error, notify_user=False)
        
        # Verify stats exist
        assert self.error_handler.error_stats['total_errors'] == 1
        
        self.error_handler.clear_error_stats()
        
        # Verify stats are cleared
        assert self.error_handler.error_stats['total_errors'] == 0
        assert self.error_handler.error_stats['errors_by_code'] == {}
        assert self.error_handler.error_stats['errors_by_severity'] == {}
        assert self.error_handler.error_stats['recent_errors'] == []
    
    def test_log_level_mapping(self):
        """Test that error severity maps to correct log levels."""
        errors = [
            (ErrorSeverity.LOW, logging.INFO),
            (ErrorSeverity.MEDIUM, logging.WARNING),
            (ErrorSeverity.HIGH, logging.ERROR),
            (ErrorSeverity.CRITICAL, logging.CRITICAL)
        ]
        
        for severity, expected_level in errors:
            error = MindMapError("Test error", severity=severity)
            self.error_handler.handle_error(error, notify_user=False)
            
            # Check that log was called with correct level
            log_calls = self.logger.log.call_args_list
            assert any(call[0][0] == expected_level for call in log_calls)
        
        # Reset mock for next iteration
        self.logger.reset_mock()
    
    @patch('src.infrastructure.error_handler.publish_event')
    def test_event_publishing(self, mock_publish_event):
        """Test that errors are published as events."""
        error = MindMapError(
            "Test error",
            error_code=ErrorCode.VALIDATION_ERROR,
            context=ErrorContext(operation="test", component="test")
        )
        
        self.error_handler.handle_error(error)
        
        mock_publish_event.assert_called_once()
        call_args = mock_publish_event.call_args
        
        # Check event type
        assert call_args[0][0].name == 'SYSTEM_ERROR'
        
        # Check event data
        event_data = call_args[1]['data']
        assert event_data['error_code'] == 'VALIDATION_ERROR'
        assert event_data['message'] == 'Test error'
    
    @patch('src.infrastructure.error_handler.publish_event')
    def test_event_publishing_failure_handling(self, mock_publish_event):
        """Test handling of event publishing failures."""
        mock_publish_event.side_effect = Exception("Event publishing failed")
        
        error = MindMapError("Test error")
        
        # Should not raise exception
        self.error_handler.handle_error(error)
        
        # Should log warning about event publishing failure
        self.logger.warning.assert_called()


class TestGlobalErrorHandler:
    """Test cases for global error handler functions."""
    
    def test_get_error_handler_singleton(self):
        """Test that get_error_handler returns singleton."""
        handler1 = get_error_handler()
        handler2 = get_error_handler()
        
        assert handler1 is handler2
    
    @patch('src.infrastructure.error_handler.get_error_handler')
    def test_handle_error_convenience_function(self, mock_get_handler):
        """Test handle_error convenience function."""
        mock_handler = Mock()
        mock_get_handler.return_value = mock_handler
        
        error = ValueError("Test error")
        context = ErrorContext(operation="test", component="test")
        
        handle_error(error, context=context, attempt_recovery=False, notify_user=False)
        
        mock_handler.handle_error.assert_called_once_with(
            error, context, False, False
        )


class TestErrorContext:
    """Test cases for error_context context manager."""
    
    @patch('src.infrastructure.error_handler.handle_error')
    def test_error_context_success(self, mock_handle_error):
        """Test error_context when no error occurs."""
        with error_context("test_op", "test_comp") as context:
            assert context.operation == "test_op"
            assert context.component == "test_comp"
        
        # handle_error should not be called
        mock_handle_error.assert_not_called()
    
    @patch('src.infrastructure.error_handler.handle_error')
    def test_error_context_with_exception(self, mock_handle_error):
        """Test error_context when exception occurs."""
        test_error = ValueError("Test error")
        
        with pytest.raises(ValueError):
            with error_context("test_op", "test_comp", user_id="user123") as context:
                assert context.user_id == "user123"
                raise test_error
        
        # handle_error should be called with the error and context
        mock_handle_error.assert_called_once()
        call_args = mock_handle_error.call_args
        assert call_args[0][0] == test_error
        assert call_args[1]['context'].operation == "test_op"
        assert call_args[1]['context'].component == "test_comp"
        assert call_args[1]['context'].user_id == "user123"


class TestWithErrorHandling:
    """Test cases for with_error_handling decorator."""
    
    @patch('src.infrastructure.error_handler.handle_error')
    def test_decorator_success(self, mock_handle_error):
        """Test decorator when function succeeds."""
        @with_error_handling()
        def test_function():
            return "success"
        
        result = test_function()
        
        assert result == "success"
        mock_handle_error.assert_not_called()
    
    @patch('src.infrastructure.error_handler.handle_error')
    def test_decorator_with_exception_reraise(self, mock_handle_error):
        """Test decorator when function raises exception and reraise=True."""
        mock_handle_error.return_value = None
        
        @with_error_handling(reraise=True)
        def test_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            test_function()
        
        mock_handle_error.assert_called_once()
    
    @patch('src.infrastructure.error_handler.handle_error')
    def test_decorator_with_exception_no_reraise(self, mock_handle_error):
        """Test decorator when function raises exception and reraise=False."""
        mock_handle_error.return_value = None
        
        @with_error_handling(reraise=False)
        def test_function():
            raise ValueError("Test error")
        
        result = test_function()
        
        assert result is None
        mock_handle_error.assert_called_once()
    
    @patch('src.infrastructure.error_handler.handle_error')
    def test_decorator_with_recovery(self, mock_handle_error):
        """Test decorator when recovery handler returns result."""
        mock_handle_error.return_value = "recovered_result"
        
        @with_error_handling(reraise=False)
        def test_function():
            raise ValueError("Test error")
        
        result = test_function()
        
        assert result == "recovered_result"
        mock_handle_error.assert_called_once()
    
    @patch('src.infrastructure.error_handler.handle_error')
    def test_decorator_custom_operation_component(self, mock_handle_error):
        """Test decorator with custom operation and component names."""
        @with_error_handling(operation="custom_op", component="custom_comp", reraise=False)
        def test_function():
            raise ValueError("Test error")
        
        test_function()
        
        call_args = mock_handle_error.call_args
        context = call_args[1]['context']
        assert context.operation == "custom_op"
        assert context.component == "custom_comp"


class TestRecoveryHandlers:
    """Test cases for built-in recovery handlers."""
    
    @patch('src.infrastructure.error_handler.get_cache_manager')
    def test_cache_recovery(self, mock_get_cache_manager):
        """Test cache recovery handler."""
        from src.infrastructure.error_handler import cache_recovery
        
        mock_cache_manager = Mock()
        mock_get_cache_manager.return_value = mock_cache_manager
        
        error = MindMapError("Cache error", error_code=ErrorCode.CACHE_ERROR)
        result = cache_recovery(error)
        
        assert result is True
        
        # Check that all caches were invalidated
        expected_calls = [
            ('nodes',),
            ('render',),
            ('computation',),
            ('search',)
        ]
        
        actual_calls = [call[0] for call in mock_cache_manager.invalidate_cache.call_args_list]
        for expected_call in expected_calls:
            assert expected_call in actual_calls
    
    @patch('src.infrastructure.error_handler.get_cache_manager')
    def test_cache_recovery_failure(self, mock_get_cache_manager):
        """Test cache recovery handler when cache manager fails."""
        from src.infrastructure.error_handler import cache_recovery
        
        mock_get_cache_manager.side_effect = Exception("Cache manager failed")
        
        error = MindMapError("Cache error", error_code=ErrorCode.CACHE_ERROR)
        result = cache_recovery(error)
        
        assert result is None
    
    def test_fallback_data_recovery(self):
        """Test fallback data recovery handler."""
        from src.infrastructure.error_handler import fallback_data_recovery
        
        error = DataLoadError("/path/to/file.json", cause=FileNotFoundError())
        result = fallback_data_recovery(error)
        
        # This is a placeholder implementation, so it returns None
        assert result is None
    
    def test_fallback_data_recovery_non_persistence_error(self):
        """Test fallback data recovery with non-persistence error."""
        from src.infrastructure.error_handler import fallback_data_recovery
        
        error = MindMapError("Generic error")
        result = fallback_data_recovery(error)
        
        assert result is None


class TestErrorReporting:
    """Test cases for error reporting utilities."""
    
    def test_create_error_report(self):
        """Test creating comprehensive error report."""
        context = ErrorContext(
            operation="test_op",
            component="test_comp",
            user_id="user123"
        )
        error = MindMapError(
            "Test error",
            error_code=ErrorCode.VALIDATION_ERROR,
            context=context,
            recovery_suggestions=["Try again"]
        )
        
        report = create_error_report(error)
        
        assert 'error_details' in report
        assert 'system_info' in report
        assert 'context' in report
        assert 'recovery_suggestions' in report
        assert 'stack_trace' in report
        
        # Check error details
        assert report['error_details']['error_code'] == 'VALIDATION_ERROR'
        assert report['error_details']['message'] == 'Test error'
        
        # Check context
        assert report['context']['operation'] == 'test_op'
        assert report['context']['user_id'] == 'user123'
        
        # Check system info
        assert 'python_version' in report['system_info']
        assert 'platform' in report['system_info']
        assert 'timestamp' in report['system_info']
    
    @patch('src.infrastructure.error_handler.get_error_handler')
    def test_export_error_logs(self, mock_get_handler):
        """Test exporting error logs."""
        from src.infrastructure.error_handler import export_error_logs
        
        mock_handler = Mock()
        mock_recent_errors = [
            {
                'error_id': 'error1',
                'timestamp': '2023-01-01T10:00:00',
                'message': 'Error 1'
            },
            {
                'error_id': 'error2',
                'timestamp': '2023-01-02T10:00:00',
                'message': 'Error 2'
            }
        ]
        mock_handler.get_recent_errors.return_value = mock_recent_errors
        mock_get_handler.return_value = mock_handler
        
        result = export_error_logs()
        
        assert result == mock_recent_errors
        mock_handler.get_recent_errors.assert_called_once_with(100)
    
    @patch('src.infrastructure.error_handler.get_error_handler')
    def test_export_error_logs_with_date_filter(self, mock_get_handler):
        """Test exporting error logs with date filtering."""
        from src.infrastructure.error_handler import export_error_logs
        
        mock_handler = Mock()
        mock_recent_errors = [
            {
                'error_id': 'error1',
                'timestamp': '2023-01-01T10:00:00',
                'message': 'Error 1'
            },
            {
                'error_id': 'error2',
                'timestamp': '2023-01-02T10:00:00',
                'message': 'Error 2'
            },
            {
                'error_id': 'error3',
                'timestamp': '2023-01-03T10:00:00',
                'message': 'Error 3'
            }
        ]
        mock_handler.get_recent_errors.return_value = mock_recent_errors
        mock_get_handler.return_value = mock_handler
        
        start_date = datetime(2023, 1, 2)
        end_date = datetime(2023, 1, 2, 23, 59, 59)
        
        result = export_error_logs(start_date=start_date, end_date=end_date)
        
        # Should only include error2
        assert len(result) == 1
        assert result[0]['error_id'] == 'error2'


class TestSetupDefaultRecoveryHandlers:
    """Test cases for setting up default recovery handlers."""
    
    @patch('src.infrastructure.error_handler.get_error_handler')
    def test_setup_default_recovery_handlers(self, mock_get_handler):
        """Test setting up default recovery handlers."""
        mock_handler = Mock()
        mock_get_handler.return_value = mock_handler
        
        setup_default_recovery_handlers()
        
        # Check that recovery handlers were registered
        register_calls = mock_handler.register_recovery_handler.call_args_list
        
        # Should register handlers for cache errors and data load errors
        registered_codes = [call[0][0] for call in register_calls]
        assert ErrorCode.CACHE_ERROR in registered_codes
        assert ErrorCode.CACHE_INVALIDATION_FAILED in registered_codes
        assert ErrorCode.DATA_LOAD_ERROR in registered_codes