"""Comprehensive error handling system for the Enhanced Mind Map application."""

import logging
import traceback
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum


class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    VALIDATION = "validation"
    BUSINESS_LOGIC = "business_logic"
    DATA_ACCESS = "data_access"
    EXTERNAL_SERVICE = "external_service"
    SYSTEM = "system"
    SECURITY = "security"
    PERFORMANCE = "performance"
    UI = "ui"


class ErrorCode(Enum):
    VALIDATION_FAILED = "VALIDATION_FAILED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NODE_NOT_FOUND = "NODE_NOT_FOUND"
    NODE_UPDATE_FAILED = "NODE_UPDATE_FAILED"
    CIRCULAR_REFERENCE = "CIRCULAR_REFERENCE"
    DATA_LOAD_ERROR = "DATA_LOAD_ERROR"
    DATA_SAVE_ERROR = "DATA_SAVE_ERROR"
    CACHE_ERROR = "CACHE_ERROR"
    CACHE_INVALIDATION_FAILED = "CACHE_INVALIDATION_FAILED"
    PERFORMANCE_ERROR = "PERFORMANCE_ERROR"
    PERFORMANCE_DEGRADATION = "PERFORMANCE_DEGRADATION"
    UI_ERROR = "UI_ERROR"
    UI_RENDERING_ERROR = "UI_RENDERING_ERROR"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    EVENT_HANDLER_ERROR = "EVENT_HANDLER_ERROR"


class ErrorContext:
    def __init__(self, **kwargs):
        # Set default values for expected fields
        defaults = {
            'operation': None,
            'component': None,
            'user_id': None,
            'session_id': None,
            'request_id': None
        }
        defaults.update(kwargs)
        
        # Set attributes directly on the object
        for key, value in defaults.items():
            setattr(self, key, value)
        
        # Also store in data dict for compatibility
        self.data = defaults
    
    def get(self, key: str, default=None):
        return getattr(self, key, default)
    
    def set(self, key: str, value):
        setattr(self, key, value)
        self.data[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        return {key: getattr(self, key) for key in self.data.keys()}


class MindMapError(Exception):
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None,
        recovery_suggestions: Optional[List[str]] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.context = context or ErrorContext()
        self.cause = cause
        self.timestamp = datetime.now()
        self.error_id = str(uuid.uuid4())
        self.recovery_suggestions = recovery_suggestions or []
        self.stack_trace = traceback.format_exc() if cause else None
        
        # Set error code after category is set
        self.error_code = error_code or self._generate_error_code()
        
        # Set user message with default generation
        self.user_message = user_message or self._generate_user_message()
    
    def _generate_error_code(self) -> str:
        return f"MM_{self.category.value.upper()}_{uuid.uuid4().hex[:8].upper()}"
    
    def _generate_user_message(self) -> str:
        """Generate a user-friendly message based on error code."""
        if hasattr(self, 'error_code') and self.error_code:
            if 'NOT_FOUND' in str(self.error_code):
                return "The requested item could not be found."
            elif 'VALIDATION' in str(self.error_code):
                return "Please check your input and try again."
            elif 'PERMISSION' in str(self.error_code):
                return "You don't have permission to perform this action."
        return "An error occurred. Please try again."
    
    def to_dict(self) -> Dict[str, Any]:
        # Handle error_code - convert enum to value if needed
        error_code_value = self.error_code
        if hasattr(error_code_value, 'value'):
            error_code_value = error_code_value.value
        
        return {
            'error_id': self.error_id,
            'error_code': error_code_value,
            'message': self.message,
            'category': self.category.value,
            'severity': self.severity.value,
            'context': self.context.to_dict() if self.context else {},
            'timestamp': self.timestamp.isoformat(),
            'cause': str(self.cause) if self.cause else None,
            'traceback': traceback.format_exc() if self.cause else None,
            'user_message': self.user_message,
            'recovery_suggestions': self.recovery_suggestions
        }
    
    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message} (ID: {self.error_id})"


class ValidationError(MindMapError):
    def __init__(self, message: str, field: Optional[str] = None, field_name: Optional[str] = None, 
                 field_value: Any = None, validation_rule: Optional[str] = None, **kwargs):
        # Handle both field and field_name parameters
        actual_field = field or field_name
        
        # Set default error code if not provided
        if 'error_code' not in kwargs:
            kwargs['error_code'] = ErrorCode.VALIDATION_ERROR
        
        super().__init__(
            message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            **kwargs
        )
        
        # Store validation-specific attributes
        self.field_name = actual_field
        self.field_value = str(field_value) if field_value is not None else None
        self.validation_rule = validation_rule
        
        # Also store in context for compatibility
        if actual_field:
            self.context.set('field', actual_field)
        if field_value is not None:
            self.context.set('field_value', str(field_value))
        if validation_rule:
            self.context.set('validation_rule', validation_rule)
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            'field_name': self.field_name,
            'field_value': self.field_value,
            'validation_rule': self.validation_rule
        })
        return result


class NodeError(MindMapError):
    def __init__(self, message: str, node_id: Optional[Union[int, str]] = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.BUSINESS_LOGIC,
            **kwargs
        )
        self.node_id = node_id
        if node_id is not None:
            self.context.set('node_id', node_id)


class NodeNotFoundError(NodeError):
    def __init__(self, node_id: Union[int, str], **kwargs):
        # Set default error code if not provided
        if 'error_code' not in kwargs:
            kwargs['error_code'] = ErrorCode.NODE_NOT_FOUND
        
        super().__init__(
            f"Node with ID {node_id} not found",
            node_id=node_id,
            **kwargs
        )
        self.recovery_suggestions = [
            "Check if the node ID is correct",
            "Refresh the data and try again",
            "Verify the node exists in the system"
        ]


class CircularReferenceError(NodeError):
    def __init__(self, node_id: Union[int, str], parent_id: Optional[Union[int, str]] = None, **kwargs):
        # Set default error code if not provided
        if 'error_code' not in kwargs:
            kwargs['error_code'] = ErrorCode.CIRCULAR_REFERENCE
        
        super().__init__(
            f"Circular reference detected for node {node_id}",
            node_id=node_id,
            **kwargs
        )
        self.parent_id = parent_id
        if parent_id is not None:
            self.context.set('parent_id', parent_id)
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result['parent_id'] = self.parent_id
        return result


class DataPersistenceError(MindMapError):
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.DATA_ACCESS,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class DataLoadError(DataPersistenceError):
    def __init__(self, message: Optional[str] = None, file_path: Optional[str] = None, **kwargs):
        # Set default error code if not provided
        if 'error_code' not in kwargs:
            kwargs['error_code'] = ErrorCode.DATA_LOAD_ERROR
        
        actual_message = message or f"Failed to load data from {file_path or 'unknown file'}"
        super().__init__(actual_message, **kwargs)
        self.file_path = file_path
        if file_path:
            self.context.set('file_path', file_path)
        
        # Add recovery suggestions
        self.recovery_suggestions = [
            "Check if the file exists and is accessible",
            "Verify file permissions",
            "Ensure the file format is correct",
            "Try reloading the data"
        ]


class DataSaveError(DataPersistenceError):
    def __init__(self, message: Optional[str] = None, file_path: Optional[str] = None, **kwargs):
        # Set default error code if not provided
        if 'error_code' not in kwargs:
            kwargs['error_code'] = ErrorCode.DATA_SAVE_ERROR
        
        actual_message = message or f"Failed to save data to {file_path or 'unknown file'}"
        super().__init__(actual_message, **kwargs)
        self.file_path = file_path
        if file_path:
            self.context.set('file_path', file_path)


class ServiceError(MindMapError):
    def __init__(self, message: str, service_name: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.BUSINESS_LOGIC,
            **kwargs
        )
        self.service_name = service_name
        if service_name:
            self.context.set('service_name', service_name)


class CacheError(MindMapError):
    def __init__(self, message: str, cache_name: Optional[str] = None, cache_key: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )
        self.cache_name = cache_name
        self.cache_key = cache_key
        if cache_name:
            self.context.set('cache_name', cache_name)
        if cache_key:
            self.context.set('cache_key', cache_key)
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            'cache_name': self.cache_name,
            'cache_key': self.cache_key
        })
        return result


class PerformanceError(MindMapError):
    def __init__(self, message: str, operation: Optional[str] = None, duration: Optional[float] = None, 
                 operation_duration: Optional[float] = None, threshold: Optional[float] = None, **kwargs):
        # Set default error code if not provided
        if 'error_code' not in kwargs:
            kwargs['error_code'] = ErrorCode.PERFORMANCE_DEGRADATION
        
        super().__init__(
            message,
            category=ErrorCategory.PERFORMANCE,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )
        
        # Handle both duration and operation_duration parameters
        actual_duration = duration or operation_duration
        
        self.operation_duration = actual_duration
        self.threshold = threshold
        
        if operation:
            self.context.set('operation', operation)
        if actual_duration:
            self.context.set('duration', actual_duration)
        if threshold:
            self.context.set('threshold', threshold)
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            'operation_duration': self.operation_duration,
            'threshold': self.threshold
        })
        return result


class EventSystemError(MindMapError):
    def __init__(self, message: str, event_type: Optional[str] = None, handler_name: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )
        self.event_type = event_type
        self.handler_name = handler_name
        if event_type:
            self.context.set('event_type', event_type)
        if handler_name:
            self.context.set('handler_name', handler_name)
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            'event_type': self.event_type,
            'handler_name': self.handler_name
        })
        return result


class UIError(MindMapError):
    def __init__(self, message: str, component: Optional[str] = None, component_name: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.UI,
            severity=ErrorSeverity.LOW,
            **kwargs
        )
        
        # Handle both component and component_name parameters
        actual_component = component or component_name
        self.component_name = actual_component
        
        if actual_component:
            self.context.set('component', actual_component)
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result['component_name'] = self.component_name
        return result


def create_validation_error(message: Optional[str] = None, field: Optional[str] = None, 
                          field_name: Optional[str] = None, field_value: Any = None, 
                          rule: Optional[str] = None, **kwargs) -> ValidationError:
    actual_message = message or f"Validation failed for field {field or field_name or 'unknown'}"
    return ValidationError(
        actual_message, 
        field=field, 
        field_name=field_name, 
        field_value=field_value, 
        validation_rule=rule, 
        **kwargs
    )


def create_node_not_found_error(node_id: Union[int, str], **kwargs) -> NodeNotFoundError:
    return NodeNotFoundError(node_id, **kwargs)


def create_data_load_error(message: Optional[str] = None, file_path: Optional[str] = None, **kwargs) -> DataLoadError:
    return DataLoadError(message=message, file_path=file_path, **kwargs)


def create_data_save_error(message: Optional[str] = None, file_path: Optional[str] = None, **kwargs) -> DataSaveError:
    return DataSaveError(message=message, file_path=file_path, **kwargs)


def wrap_exception(exception: Exception, message: Optional[str] = None, 
                  context: Optional[ErrorContext] = None, **kwargs) -> MindMapError:
    # If it's already a MindMapError, return it as-is
    if isinstance(exception, MindMapError):
        return exception
    
    error_message = message or str(exception)
    actual_context = context or ErrorContext(**kwargs)
    
    # Set default error code if not provided
    if 'error_code' not in kwargs:
        kwargs['error_code'] = ErrorCode.INTERNAL_ERROR
    
    return MindMapError(
        error_message,
        cause=exception,
        context=actual_context,
        **kwargs
    )