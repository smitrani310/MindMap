"""
Unit tests for error handling system.
"""

import pytest
import logging
from datetime import datetime
from unittest.mock import Mock, patch

from src.infrastructure.errors import (
    MindMapError, ErrorCode, ErrorSeverity, ErrorContext,
    ValidationError, NodeError, NodeNotFoundError, CircularReferenceError,
    DataPersistenceError, DataLoadError, DataSaveError,
    ServiceError, CacheError, PerformanceError, EventSystemError, UIError,
    create_validation_error, create_node_not_found_error,
    create_data_load_error, create_data_save_error, wrap_exception
)


class TestErrorContext:
    """Test cases for ErrorContext."""
    
    def test_error_context_creation(self):
        """Test creating error context."""
        context = ErrorContext(
            operation="test_operation",
            component="test_component",
            user_id="user123",
            session_id="session456",
            request_id="req789",
            additional_data={"key": "value"}
        )
        
        assert context.operation == "test_operation"
        assert context.component == "test_component"
        assert context.user_id == "user123"
        assert context.session_id == "session456"
        assert context.request_id == "req789"
        assert context.additional_data["key"] == "value"
    
    def test_error_context_to_dict(self):
        """Test converting error context to dictionary."""
        context = ErrorContext(
            operation="test_op",
            component="test_comp",
            additional_data={"test": "data"}
        )
        
        result = context.to_dict()
        
        assert result["operation"] == "test_op"
        assert result["component"] == "test_comp"
        assert result["additional_data"]["test"] == "data"
        assert "user_id" in result
        assert "session_id" in result
        assert "request_id" in result


class TestMindMapError:
    """Test cases for MindMapError base class."""
    
    def test_mindmap_error_creation(self):
        """Test creating a MindMapError."""
        context = ErrorContext(operation="test", component="test")
        error = MindMapError(
            message="Test error",
            error_code=ErrorCode.VALIDATION_ERROR,
            severity=ErrorSeverity.HIGH,
            context=context,
            user_message="User friendly message",
            recovery_suggestions=["Try again", "Check input"]
        )
        
        assert error.message == "Test error"
        assert error.error_code == ErrorCode.VALIDATION_ERROR
        assert error.severity == ErrorSeverity.HIGH
        assert error.context == context
        assert error.user_message == "User friendly message"
        assert "Try again" in error.recovery_suggestions
        assert error.error_id is not None
        assert isinstance(error.timestamp, datetime)
    
    def test_mindmap_error_default_user_message(self):
        """Test default user message generation."""
        error = MindMapError(
            "Test error",
            error_code=ErrorCode.NODE_NOT_FOUND
        )
        
        assert "could not be found" in error.user_message
    
    def test_mindmap_error_to_dict(self):
        """Test converting error to dictionary."""
        context = ErrorContext(operation="test", component="test")
        error = MindMapError(
            "Test error",
            error_code=ErrorCode.INTERNAL_ERROR,
            context=context
        )
        
        result = error.to_dict()
        
        assert result["error_code"] == ErrorCode.INTERNAL_ERROR.value
        assert result["message"] == "Test error"
        assert "error_id" in result
        assert "timestamp" in result
        assert "context" in result
        assert "user_message" in result
    
    def test_mindmap_error_str_representation(self):
        """Test string representation of error."""
        error = MindMapError(
            "Test error",
            error_code=ErrorCode.VALIDATION_ERROR
        )
        
        error_str = str(error)
        assert ErrorCode.VALIDATION_ERROR.value in error_str
        assert "Test error" in error_str
        assert error.error_id in error_str


class TestValidationError:
    """Test cases for ValidationError."""
    
    def test_validation_error_creation(self):
        """Test creating a validation error."""
        error = ValidationError(
            "Invalid field value",
            field_name="email",
            field_value="invalid-email",
            validation_rule="must be valid email"
        )
        
        assert error.message == "Invalid field value"
        assert error.error_code == ErrorCode.VALIDATION_ERROR
        assert error.field_name == "email"
        assert error.field_value == "invalid-email"
        assert error.validation_rule == "must be valid email"
    
    def test_validation_error_to_dict(self):
        """Test validation error dictionary representation."""
        error = ValidationError(
            "Test validation error",
            field_name="test_field",
            field_value=123,
            validation_rule="must be string"
        )
        
        result = error.to_dict()
        
        assert result["field_name"] == "test_field"
        assert result["field_value"] == "123"
        assert result["validation_rule"] == "must be string"


class TestNodeError:
    """Test cases for node-related errors."""
    
    def test_node_error_creation(self):
        """Test creating a node error."""
        error = NodeError(
            "Node operation failed",
            node_id=123,
            error_code=ErrorCode.NODE_UPDATE_FAILED
        )
        
        assert error.message == "Node operation failed"
        assert error.node_id == 123
        assert error.error_code == ErrorCode.NODE_UPDATE_FAILED
    
    def test_node_not_found_error(self):
        """Test NodeNotFoundError."""
        error = NodeNotFoundError(node_id=456)
        
        assert error.node_id == 456
        assert error.error_code == ErrorCode.NODE_NOT_FOUND
        assert "456" in error.message
        assert len(error.recovery_suggestions) > 0
    
    def test_circular_reference_error(self):
        """Test CircularReferenceError."""
        error = CircularReferenceError(node_id=1, parent_id=2)
        
        assert error.node_id == 1
        assert error.parent_id == 2
        assert error.error_code == ErrorCode.CIRCULAR_REFERENCE
        assert "circular reference" in error.message.lower()
        
        result = error.to_dict()
        assert result["parent_id"] == 2


class TestDataPersistenceError:
    """Test cases for data persistence errors."""
    
    def test_data_load_error(self):
        """Test DataLoadError."""
        cause = FileNotFoundError("File not found")
        error = DataLoadError(
            file_path="/path/to/file.json",
            cause=cause
        )
        
        assert error.file_path == "/path/to/file.json"
        assert error.error_code == ErrorCode.DATA_LOAD_ERROR
        assert error.cause == cause
        assert "file.json" in error.message
        assert len(error.recovery_suggestions) > 0
    
    def test_data_save_error(self):
        """Test DataSaveError."""
        cause = PermissionError("Permission denied")
        error = DataSaveError(
            file_path="/path/to/file.json",
            cause=cause
        )
        
        assert error.file_path == "/path/to/file.json"
        assert error.error_code == ErrorCode.DATA_SAVE_ERROR
        assert error.cause == cause
        assert "save" in error.message.lower()


class TestServiceError:
    """Test cases for service errors."""
    
    def test_service_error_creation(self):
        """Test creating a service error."""
        error = ServiceError(
            "Service operation failed",
            service_name="MindMapService"
        )
        
        assert error.message == "Service operation failed"
        assert error.service_name == "MindMapService"


class TestCacheError:
    """Test cases for cache errors."""
    
    def test_cache_error_creation(self):
        """Test creating a cache error."""
        error = CacheError(
            "Cache operation failed",
            cache_name="node_cache",
            cache_key="node_123",
            error_code=ErrorCode.CACHE_ERROR
        )
        
        assert error.message == "Cache operation failed"
        assert error.cache_name == "node_cache"
        assert error.cache_key == "node_123"
        assert error.error_code == ErrorCode.CACHE_ERROR
    
    def test_cache_error_to_dict(self):
        """Test cache error dictionary representation."""
        error = CacheError(
            "Cache miss",
            cache_name="render_cache",
            cache_key="render_key_456"
        )
        
        result = error.to_dict()
        
        assert result["cache_name"] == "render_cache"
        assert result["cache_key"] == "render_key_456"


class TestPerformanceError:
    """Test cases for performance errors."""
    
    def test_performance_error_creation(self):
        """Test creating a performance error."""
        error = PerformanceError(
            "Operation too slow",
            operation_duration=5000.0,
            threshold=1000.0
        )
        
        assert error.message == "Operation too slow"
        assert error.operation_duration == 5000.0
        assert error.threshold == 1000.0
        assert error.error_code == ErrorCode.PERFORMANCE_DEGRADATION
        assert error.severity == ErrorSeverity.MEDIUM
    
    def test_performance_error_to_dict(self):
        """Test performance error dictionary representation."""
        error = PerformanceError(
            "Slow query",
            operation_duration=2500.0,
            threshold=1000.0
        )
        
        result = error.to_dict()
        
        assert result["operation_duration"] == 2500.0
        assert result["threshold"] == 1000.0


class TestEventSystemError:
    """Test cases for event system errors."""
    
    def test_event_system_error_creation(self):
        """Test creating an event system error."""
        error = EventSystemError(
            "Event handler failed",
            event_type="NODE_CREATED",
            handler_name="NodeEventHandler",
            error_code=ErrorCode.EVENT_HANDLER_ERROR
        )
        
        assert error.message == "Event handler failed"
        assert error.event_type == "NODE_CREATED"
        assert error.handler_name == "NodeEventHandler"
        assert error.error_code == ErrorCode.EVENT_HANDLER_ERROR
    
    def test_event_system_error_to_dict(self):
        """Test event system error dictionary representation."""
        error = EventSystemError(
            "Event publication failed",
            event_type="NODE_UPDATED",
            handler_name="UIEventHandler"
        )
        
        result = error.to_dict()
        
        assert result["event_type"] == "NODE_UPDATED"
        assert result["handler_name"] == "UIEventHandler"


class TestUIError:
    """Test cases for UI errors."""
    
    def test_ui_error_creation(self):
        """Test creating a UI error."""
        error = UIError(
            "Component rendering failed",
            component_name="NodeVisualization",
            error_code=ErrorCode.UI_RENDERING_ERROR
        )
        
        assert error.message == "Component rendering failed"
        assert error.component_name == "NodeVisualization"
        assert error.error_code == ErrorCode.UI_RENDERING_ERROR
    
    def test_ui_error_to_dict(self):
        """Test UI error dictionary representation."""
        error = UIError(
            "User input validation failed",
            component_name="AddNodeForm"
        )
        
        result = error.to_dict()
        
        assert result["component_name"] == "AddNodeForm"


class TestConvenienceFunctions:
    """Test cases for convenience functions."""
    
    def test_create_validation_error(self):
        """Test creating validation error with convenience function."""
        context = ErrorContext(operation="test", component="test")
        error = create_validation_error(
            field_name="email",
            field_value="invalid-email",
            rule="must be valid email format",
            context=context
        )
        
        assert isinstance(error, ValidationError)
        assert error.field_name == "email"
        assert error.field_value == "invalid-email"
        assert error.validation_rule == "must be valid email format"
        assert error.context == context
    
    def test_create_node_not_found_error(self):
        """Test creating node not found error with convenience function."""
        context = ErrorContext(operation="get_node", component="repository")
        error = create_node_not_found_error(node_id=123, context=context)
        
        assert isinstance(error, NodeNotFoundError)
        assert error.node_id == 123
        assert error.context == context
    
    def test_create_data_load_error(self):
        """Test creating data load error with convenience function."""
        cause = FileNotFoundError("File not found")
        context = ErrorContext(operation="load_data", component="repository")
        error = create_data_load_error(
            file_path="/path/to/file.json",
            cause=cause,
            context=context
        )
        
        assert isinstance(error, DataLoadError)
        assert error.file_path == "/path/to/file.json"
        assert error.cause == cause
        assert error.context == context
    
    def test_create_data_save_error(self):
        """Test creating data save error with convenience function."""
        cause = PermissionError("Permission denied")
        context = ErrorContext(operation="save_data", component="repository")
        error = create_data_save_error(
            file_path="/path/to/file.json",
            cause=cause,
            context=context
        )
        
        assert isinstance(error, DataSaveError)
        assert error.file_path == "/path/to/file.json"
        assert error.cause == cause
        assert error.context == context
    
    def test_wrap_exception(self):
        """Test wrapping generic exception."""
        original_error = ValueError("Invalid value")
        context = ErrorContext(operation="validate", component="service")
        
        wrapped_error = wrap_exception(
            original_error,
            context=context,
            user_message="Please check your input"
        )
        
        assert isinstance(wrapped_error, MindMapError)
        assert wrapped_error.cause == original_error
        assert wrapped_error.context == context
        assert wrapped_error.user_message == "Please check your input"
        assert wrapped_error.error_code == ErrorCode.INTERNAL_ERROR
    
    def test_wrap_mindmap_error_returns_same(self):
        """Test wrapping MindMapError returns the same error."""
        original_error = ValidationError("Test validation error")
        
        wrapped_error = wrap_exception(original_error)
        
        assert wrapped_error is original_error


class TestErrorCodes:
    """Test cases for error codes."""
    
    def test_error_codes_are_strings(self):
        """Test that all error codes are strings."""
        for error_code in ErrorCode:
            assert isinstance(error_code.value, str)
            assert len(error_code.value) > 0
    
    def test_error_codes_are_unique(self):
        """Test that all error codes are unique."""
        error_code_values = [code.value for code in ErrorCode]
        assert len(error_code_values) == len(set(error_code_values))


class TestErrorSeverity:
    """Test cases for error severity."""
    
    def test_error_severity_values(self):
        """Test error severity enum values."""
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"