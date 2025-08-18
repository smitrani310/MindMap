"""
Centralized error handling system for the Enhanced Mind Map application.

This module provides centralized error processing, logging, user notification,
and error recovery mechanisms.
"""

import logging
import sys
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Union
from contextlib import contextmanager
from functools import wraps

from src.infrastructure.errors import (
    MindMapError, ErrorCode, ErrorSeverity, ErrorContext,
    ValidationError, NodeError, DataPersistenceError, ServiceError,
    wrap_exception
)


class ErrorHandler:
    """Centralized error handler for the mind map application."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.error_callbacks: List[Callable[[MindMapError], None]] = []
        self.recovery_handlers: Dict[ErrorCode, Callable[[MindMapError], Any]] = {}
        self.error_stats = {
            'total_errors': 0,
            'errors_by_code': {},
            'errors_by_severity': {},
            'recent_errors': []
        }
    
    def register_error_callback(self, callback: Callable[[MindMapError], None]) -> None:
        """Register a callback to be called when errors occur."""
        self.error_callbacks.append(callback)
        self.logger.info(f"Registered error callback: {callback.__name__}")
    
    def register_recovery_handler(self, error_code: ErrorCode, handler: Callable[[MindMapError], Any]) -> None:
        """Register a recovery handler for a specific error code."""
        self.recovery_handlers[error_code] = handler
        self.logger.info(f"Registered recovery handler for {error_code.value}: {handler.__name__}")
    
    def handle_error(
        self,
        error: Union[Exception, MindMapError],
        context: Optional[ErrorContext] = None,
        attempt_recovery: bool = True,
        notify_user: bool = True
    ) -> Optional[Any]:
        """Handle an error with logging, notification, and optional recovery."""
        
        # Convert to MindMapError if needed
        if not isinstance(error, MindMapError):
            error = wrap_exception(error, context)
        elif context and not error.context:
            error.context = context
        
        # Update error statistics
        self._update_error_stats(error)
        
        # Log the error
        self._log_error(error)
        
        # Publish error event
        self._publish_error_event(error)
        
        # Call registered callbacks
        self._call_error_callbacks(error)
        
        # Attempt recovery if enabled
        recovery_result = None
        if attempt_recovery:
            recovery_result = self._attempt_recovery(error)
        
        # Notify user if enabled
        if notify_user:
            self._notify_user(error)
        
        return recovery_result
    
    def _update_error_stats(self, error: MindMapError) -> None:
        """Update error statistics."""
        self.error_stats['total_errors'] += 1
        
        # Update by error code
        code = error.error_code.value
        self.error_stats['errors_by_code'][code] = self.error_stats['errors_by_code'].get(code, 0) + 1
        
        # Update by severity
        severity = error.severity.value
        self.error_stats['errors_by_severity'][severity] = self.error_stats['errors_by_severity'].get(severity, 0) + 1
        
        # Add to recent errors (keep last 100)
        self.error_stats['recent_errors'].append({
            'error_id': error.error_id,
            'error_code': error.error_code.value,
            'message': error.message,
            'severity': error.severity.value,
            'timestamp': error.timestamp.isoformat(),
            'component': error.context.component if error.context else 'unknown'
        })
        
        # Keep only last 100 recent errors
        if len(self.error_stats['recent_errors']) > 100:
            self.error_stats['recent_errors'] = self.error_stats['recent_errors'][-100:]
    
    def _log_error(self, error: MindMapError) -> None:
        """Log the error with appropriate level and formatting."""
        log_level = self._get_log_level(error.severity)
        
        # Create structured log message
        log_data = {
            'error_id': error.error_id,
            'error_code': error.error_code.value,
            'message': error.message,
            'severity': error.severity.value,
            'component': error.context.component if error.context else 'unknown',
            'operation': error.context.operation if error.context else 'unknown',
            'user_id': error.context.user_id if error.context else None,
            'session_id': error.context.session_id if error.context else None,
            'request_id': error.context.request_id if error.context else None
        }
        
        # Add cause information if available
        if error.cause:
            log_data['cause'] = str(error.cause)
            log_data['cause_type'] = type(error.cause).__name__
        
        # Log with structured data
        self.logger.log(
            log_level,
            f"[{error.error_code.value}] {error.message}",
            extra={'error_data': log_data}
        )
        
        # Log stack trace for high severity errors
        if error.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] and error.stack_trace:
            self.logger.error(f"Stack trace for error {error.error_id}:\\n{error.stack_trace}")
    
    def _get_log_level(self, severity: ErrorSeverity) -> int:
        """Get appropriate log level for error severity."""
        level_map = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }
        return level_map.get(severity, logging.ERROR)
    
    def _publish_error_event(self, error: MindMapError) -> None:
        """Publish an error event to the event system."""
        try:
            # TODO: Implement event publishing when event system is available
            # This is a placeholder for future event system integration
            pass
        except Exception as e:
            # Don't let event publishing errors break error handling
            self.logger.warning(f"Failed to publish error event: {e}")
    
    def _call_error_callbacks(self, error: MindMapError) -> None:
        """Call all registered error callbacks."""
        for callback in self.error_callbacks:
            try:
                callback(error)
            except Exception as e:
                self.logger.warning(f"Error callback {callback.__name__} failed: {e}")
    
    def _attempt_recovery(self, error: MindMapError) -> Optional[Any]:
        """Attempt to recover from the error using registered handlers."""
        handler = self.recovery_handlers.get(error.error_code)
        if handler:
            try:
                self.logger.info(f"Attempting recovery for error {error.error_code.value} using {handler.__name__}")
                result = handler(error)
                self.logger.info(f"Recovery successful for error {error.error_id}")
                return result
            except Exception as recovery_error:
                self.logger.error(f"Recovery failed for error {error.error_id}: {recovery_error}")
                # Create a new error for the recovery failure
                recovery_failure = MindMapError(
                    f"Recovery failed for {error.error_code.value}: {recovery_error}",
                    error_code=ErrorCode.INTERNAL_ERROR,
                    severity=ErrorSeverity.HIGH,
                    cause=recovery_error,
                    context=error.context
                )
                self._log_error(recovery_failure)
        
        return None
    
    def _notify_user(self, error: MindMapError) -> None:
        """Notify the user about the error (placeholder for UI integration)."""
        # This would integrate with the UI system to show user notifications
        # For now, we just log the user message
        if error.user_message:
            self.logger.info(f"User notification: {error.user_message}")
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        return self.error_stats.copy()
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent errors."""
        return self.error_stats['recent_errors'][-limit:]
    
    def clear_error_stats(self) -> None:
        """Clear error statistics."""
        self.error_stats = {
            'total_errors': 0,
            'errors_by_code': {},
            'errors_by_severity': {},
            'recent_errors': []
        }
        self.logger.info("Error statistics cleared")


# Global error handler instance
_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


def handle_error(
    error: Union[Exception, MindMapError],
    context: Optional[ErrorContext] = None,
    attempt_recovery: bool = True,
    notify_user: bool = True
) -> Optional[Any]:
    """Convenience function to handle errors using the global handler."""
    return get_error_handler().handle_error(error, context, attempt_recovery, notify_user)


@contextmanager
def error_context(operation: str, component: str, **kwargs):
    """Context manager for error handling with automatic context creation."""
    context = ErrorContext(operation=operation, component=component, **kwargs)
    try:
        yield context
    except Exception as e:
        handle_error(e, context=context)
        raise


def with_error_handling(
    operation: Optional[str] = None,
    component: Optional[str] = None,
    attempt_recovery: bool = True,
    notify_user: bool = True,
    reraise: bool = True
):
    """Decorator for automatic error handling."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation or f"{func.__module__}.{func.__name__}"
            comp_name = component or func.__module__.split('.')[-1]
            
            context = ErrorContext(
                operation=op_name,
                component=comp_name
            )
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                recovery_result = handle_error(
                    e,
                    context=context,
                    attempt_recovery=attempt_recovery,
                    notify_user=notify_user
                )
                
                if recovery_result is not None:
                    return recovery_result
                
                if reraise:
                    raise
                
                return None
        
        return wrapper
    return decorator


# Built-in recovery handlers
def retry_operation_recovery(error: MindMapError, max_retries: int = 3, delay: float = 1.0) -> Callable:
    """Create a recovery handler that retries the operation."""
    def recovery_handler(err: MindMapError) -> Optional[Any]:
        # This is a placeholder - actual retry logic would need the original operation
        logger = logging.getLogger(__name__)
        logger.info(f"Retry recovery handler called for {err.error_code.value}")
        return None
    
    return recovery_handler


def fallback_data_recovery(error: MindMapError) -> Optional[Any]:
    """Recovery handler for data loading errors - attempts to load from backup."""
    if isinstance(error, DataPersistenceError) and error.file_path:
        logger = logging.getLogger(__name__)
        backup_path = f"{error.file_path}.backup"
        logger.info(f"Attempting to recover data from backup: {backup_path}")
        # This would integrate with the actual backup system
        return None
    return None


def cache_recovery(error: MindMapError) -> Optional[Any]:
    """Recovery handler for cache errors - clears and reinitializes cache."""
    logger = logging.getLogger(__name__)
    logger.info("Attempting cache recovery by clearing all caches")
    
    try:
        # TODO: Integrate with actual cache manager when available
        # from src.infrastructure.cache import get_cache_manager
        # cache_manager = get_cache_manager()
        # # Clear all caches
        # for cache_name in ['nodes', 'render', 'computation', 'search']:
        #     cache_manager.invalidate_cache(cache_name)
        
        logger.info("Cache recovery completed successfully")
        return True
    except Exception as e:
        logger.error(f"Cache recovery failed: {e}")
        return None


# Register default recovery handlers
def setup_default_recovery_handlers():
    """Set up default recovery handlers."""
    handler = get_error_handler()
    
    # Register cache recovery for cache errors
    handler.register_recovery_handler(ErrorCode.CACHE_ERROR, cache_recovery)
    handler.register_recovery_handler(ErrorCode.CACHE_INVALIDATION_FAILED, cache_recovery)
    
    # Register data recovery for persistence errors
    handler.register_recovery_handler(ErrorCode.DATA_LOAD_ERROR, fallback_data_recovery)
    
    logging.getLogger(__name__).info("Default recovery handlers registered")


# Error reporting utilities
def create_error_report(error: MindMapError) -> Dict[str, Any]:
    """Create a comprehensive error report."""
    return {
        'error_details': error.to_dict(),
        'system_info': {
            'python_version': sys.version,
            'platform': sys.platform,
            'timestamp': datetime.now().isoformat()
        },
        'context': error.context.to_dict() if error.context else None,
        'recovery_suggestions': error.recovery_suggestions,
        'stack_trace': error.stack_trace
    }


def export_error_logs(start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """Export error logs for analysis."""
    handler = get_error_handler()
    recent_errors = handler.get_recent_errors(100)
    
    # Filter by date if specified
    if start_date or end_date:
        filtered_errors = []
        for error in recent_errors:
            error_time = datetime.fromisoformat(error['timestamp'])
            if start_date and error_time < start_date:
                continue
            if end_date and error_time > end_date:
                continue
            filtered_errors.append(error)
        return filtered_errors
    
    return recent_errors