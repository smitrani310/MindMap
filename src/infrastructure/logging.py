"""
Enhanced logging system for the Enhanced Mind Map application.

This module provides structured logging with JSON format, correlation IDs,
log rotation, retention policies, and performance logging.
"""

import json
import logging
import logging.handlers
import os
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from contextvars import ContextVar
from contextlib import contextmanager
from functools import wraps

from src.infrastructure.config import AppConfig


# Context variable for correlation ID tracking
correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class CorrelationIdFilter(logging.Filter):
    """Filter to add correlation ID to log records."""
    
    def __init__(self):
        super().__init__()
        self._correlation_id = None
    
    def set_correlation_id(self, corr_id: str) -> None:
        """Set the correlation ID for this filter."""
        self._correlation_id = corr_id
    
    def clear_correlation_id(self) -> None:
        """Clear the correlation ID for this filter."""
        self._correlation_id = None
    
    def filter(self, record):
        """Add correlation ID to the log record."""
        if self._correlation_id:
            record.correlation_id = self._correlation_id
        else:
            # Generate a UUID and use first 8 characters
            import uuid
            record.correlation_id = str(uuid.uuid4())[:8]
        return True


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs.
    
    Provides consistent log formatting with correlation IDs, timestamps,
    and structured data fields.
    """
    
    def __init__(self, include_extra: bool = True):
        """
        Initialize the structured formatter.
        
        Args:
            include_extra: Whether to include extra fields from log records
        """
        super().__init__()
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as structured JSON."""
        
        # Base log structure
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'correlation_id': getattr(record, 'correlation_id', 'no-correlation-id'),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': record.thread,
            'thread_name': record.threadName,
            'process': record.process
        }
        
        # Add exception information if present
        if record.exc_info:
            if record.exc_info == True:
                # Handle case where exc_info is True but we need to get the actual exception info
                import sys
                exc_info = sys.exc_info()
                if exc_info[0]:
                    log_entry['exception'] = {
                        'type': exc_info[0].__name__,
                        'message': str(exc_info[1]) if exc_info[1] else None,
                        'traceback': self.formatException(exc_info)
                    }
                # If no current exception, don't add exception info
            else:
                # Handle case where exc_info is the actual exception tuple
                log_entry['exception'] = {
                    'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                    'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                    'traceback': self.formatException(record.exc_info) if record.exc_info else None
                }
        
        # Add extra fields if enabled
        if self.include_extra:
            # Get all extra attributes (those not in the standard LogRecord)
            standard_attrs = {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
                'module', 'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                'thread', 'threadName', 'processName', 'process', 'getMessage',
                'exc_info', 'exc_text', 'stack_info', 'correlation_id'
            }
            
            extra_fields = {}
            for key, value in record.__dict__.items():
                if key not in standard_attrs and not key.startswith('_'):
                    try:
                        # Ensure the value is JSON serializable
                        json.dumps(value)
                        extra_fields[key] = value
                    except (TypeError, ValueError):
                        extra_fields[key] = str(value)
            
            if extra_fields:
                log_entry['extra'] = extra_fields
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)


class PerformanceLogFilter(logging.Filter):
    """Filter for performance-related log entries."""
    
    def __init__(self, min_duration_ms: float = 100.0):
        """
        Initialize the performance log filter.
        
        Args:
            min_duration_ms: Minimum duration in milliseconds to log
        """
        super().__init__()
        self.min_duration_ms = min_duration_ms
        self._operation_name = None
        self._start_time = None
    
    def start_operation(self, operation_name: str) -> None:
        """Start timing an operation."""
        import time
        self._operation_name = operation_name
        self._start_time = time.time()
    
    def end_operation(self) -> None:
        """End timing the current operation."""
        self._operation_name = None
        self._start_time = None
    
    def filter(self, record):
        """Filter performance logs and add timing information."""
        # Add operation timing info if available
        if self._operation_name and self._start_time:
            import time
            duration_ms = (time.time() - self._start_time) * 1000
            record.operation_name = self._operation_name
            record.operation_duration_ms = duration_ms
        
        # Filter based on duration if present
        if hasattr(record, 'duration_ms'):
            return record.duration_ms >= self.min_duration_ms
        return True


class LoggingManager:
    """
    Central logging manager for the application.
    
    Provides configuration, setup, and management of all logging concerns
    including structured logging, correlation IDs, and log rotation.
    """
    
    def __init__(self, config: AppConfig):
        """
        Initialize the logging manager.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.loggers: Dict[str, logging.Logger] = {}
        self.handlers: List[logging.Handler] = []
        self.is_configured = False
    
    def configure_logging(self) -> None:
        """Configure the logging system based on application configuration."""
        if self.is_configured:
            return
        
        # Create log directory if it doesn't exist
        log_dir = Path(self.config.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.config.log_level.value))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Add console handler
        self._add_console_handler(root_logger)
        
        # Add file handlers
        self._add_file_handlers(root_logger, log_dir)
        
        # Add performance logger
        self._configure_performance_logger(log_dir)
        
        # Add error logger
        self._configure_error_logger(log_dir)
        
        # Configure third-party loggers
        self._configure_third_party_loggers()
        
        self.is_configured = True
        
        # Log configuration completion
        logger = logging.getLogger(__name__)
        logger.info("Logging system configured successfully", extra={
            'log_level': self.config.log_level.value,
            'log_dir': str(log_dir),
            'handlers_count': len(self.handlers)
        })
    
    def _add_console_handler(self, logger: logging.Logger) -> None:
        """Add console handler with appropriate formatting."""
        console_handler = logging.StreamHandler(sys.stdout)
        
        if self.config.environment.value == 'development':
            # Use simple format for development
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        else:
            # Use structured format for production
            formatter = StructuredFormatter()
        
        console_handler.setFormatter(formatter)
        console_handler.addFilter(CorrelationIdFilter())
        
        logger.addHandler(console_handler)
        self.handlers.append(console_handler)
    
    def _add_file_handlers(self, logger: logging.Logger, log_dir: Path) -> None:
        """Add rotating file handlers."""
        
        # Main application log
        app_log_file = log_dir / 'mindmap.log'
        app_handler = logging.handlers.RotatingFileHandler(
            app_log_file,
            maxBytes=self._parse_size(self.config.log_rotation_size),
            backupCount=5,
            encoding='utf-8'
        )
        app_handler.setFormatter(StructuredFormatter())
        app_handler.addFilter(CorrelationIdFilter())
        
        logger.addHandler(app_handler)
        self.handlers.append(app_handler)
        
        # Debug log (only in development)
        if self.config.environment.value == 'development':
            debug_log_file = log_dir / 'debug.log'
            debug_handler = logging.handlers.RotatingFileHandler(
                debug_log_file,
                maxBytes=self._parse_size(self.config.log_rotation_size),
                backupCount=3,
                encoding='utf-8'
            )
            debug_handler.setLevel(logging.DEBUG)
            debug_handler.setFormatter(StructuredFormatter())
            debug_handler.addFilter(CorrelationIdFilter())
            
            logger.addHandler(debug_handler)
            self.handlers.append(debug_handler)
    
    def _configure_performance_logger(self, log_dir: Path) -> None:
        """Configure performance-specific logger."""
        perf_logger = logging.getLogger('performance')
        perf_logger.setLevel(logging.INFO)
        perf_logger.propagate = False  # Don't propagate to root logger
        
        # Performance log file
        perf_log_file = log_dir / 'performance.log'
        perf_handler = logging.handlers.RotatingFileHandler(
            perf_log_file,
            maxBytes=self._parse_size(self.config.log_rotation_size),
            backupCount=3,
            encoding='utf-8'
        )
        
        perf_handler.setFormatter(StructuredFormatter())
        perf_handler.addFilter(CorrelationIdFilter())
        perf_handler.addFilter(PerformanceLogFilter(min_duration_ms=50.0))
        
        perf_logger.addHandler(perf_handler)
        self.handlers.append(perf_handler)
        self.loggers['performance'] = perf_logger
    
    def _configure_error_logger(self, log_dir: Path) -> None:
        """Configure error-specific logger."""
        error_logger = logging.getLogger('errors')
        error_logger.setLevel(logging.ERROR)
        error_logger.propagate = False  # Don't propagate to root logger
        
        # Error log file
        error_log_file = log_dir / 'errors.log'
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=self._parse_size(self.config.log_rotation_size),
            backupCount=10,  # Keep more error logs
            encoding='utf-8'
        )
        
        error_handler.setFormatter(StructuredFormatter())
        error_handler.addFilter(CorrelationIdFilter())
        
        error_logger.addHandler(error_handler)
        self.handlers.append(error_handler)
        self.loggers['errors'] = error_logger
    
    def _configure_third_party_loggers(self) -> None:
        """Configure third-party library loggers."""
        
        # Reduce noise from third-party libraries
        third_party_loggers = [
            'urllib3',
            'requests',
            'streamlit',
            'matplotlib',
            'PIL'
        ]
        
        for logger_name in third_party_loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.WARNING)
    
    def _parse_size(self, size_str: str) -> int:
        """Parse size string (e.g., '10MB') to bytes."""
        size_str = size_str.upper().strip()
        
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            # Assume bytes
            return int(size_str)
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger with the specified name."""
        if name in self.loggers:
            return self.loggers[name]
        
        logger = logging.getLogger(name)
        self.loggers[name] = logger
        return logger
    
    def cleanup_old_logs(self) -> int:
        """Clean up old log files based on retention policy."""
        log_dir = Path(self.config.log_dir)
        if not log_dir.exists():
            return 0
        
        cutoff_date = datetime.now() - timedelta(days=self.config.log_retention_days)
        removed_count = 0
        
        for log_file in log_dir.glob('*.log*'):
            try:
                file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_mtime < cutoff_date:
                    log_file.unlink()
                    removed_count += 1
            except Exception as e:
                logging.getLogger(__name__).warning(f"Failed to remove old log file {log_file}: {e}")
        
        if removed_count > 0:
            logging.getLogger(__name__).info(f"Cleaned up {removed_count} old log files")
        
        return removed_count
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Get logging statistics."""
        log_dir = Path(self.config.log_dir)
        stats = {
            'configured': self.is_configured,
            'handlers_count': len(self.handlers),
            'loggers_count': len(self.loggers),
            'log_level': self.config.log_level.value,
            'log_dir': str(log_dir)
        }
        
        if log_dir.exists():
            log_files = list(log_dir.glob('*.log*'))
            total_size = sum(f.stat().st_size for f in log_files if f.is_file())
            
            stats.update({
                'log_files_count': len(log_files),
                'total_log_size_mb': round(total_size / (1024 * 1024), 2),
                'log_files': [f.name for f in log_files]
            })
        
        return stats


# Global logging manager instance
_logging_manager: Optional[LoggingManager] = None


def get_logging_manager() -> Optional[LoggingManager]:
    """Get the global logging manager instance."""
    return _logging_manager


def init_logging_manager(config: AppConfig) -> LoggingManager:
    """Initialize the global logging manager."""
    global _logging_manager
    _logging_manager = LoggingManager(config)
    _logging_manager.configure_logging()
    return _logging_manager


# Correlation ID utilities

def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())[:8]


def set_correlation_id(corr_id: str) -> None:
    """Set the correlation ID for the current context."""
    correlation_id.set(corr_id)


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID."""
    return correlation_id.get()


@contextmanager
def correlation_context(corr_id: Optional[str] = None):
    """Context manager for correlation ID tracking."""
    if corr_id is None:
        corr_id = generate_correlation_id()
    
    token = correlation_id.set(corr_id)
    try:
        yield corr_id
    finally:
        correlation_id.reset(token)


def with_correlation_id(corr_id: Optional[str] = None):
    """Decorator to add correlation ID to function execution."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with correlation_context(corr_id):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Performance logging utilities

def log_performance(
    operation: str,
    duration_ms: float,
    success: bool = True,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """Log performance information."""
    perf_logger = logging.getLogger('performance')
    
    log_data = {
        'operation': operation,
        'duration_ms': duration_ms,
        'success': success,
        'metadata': metadata or {}
    }
    
    if success:
        perf_logger.info(f"Operation completed: {operation}", extra=log_data)
    else:
        perf_logger.warning(f"Operation failed: {operation}", extra=log_data)


@contextmanager
def performance_context(operation: str, metadata: Optional[Dict[str, Any]] = None):
    """Context manager for performance logging."""
    start_time = time.time()
    success = True
    
    try:
        yield
    except Exception:
        success = False
        raise
    finally:
        duration_ms = (time.time() - start_time) * 1000
        log_performance(operation, duration_ms, success, metadata)


def performance_logged(operation: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
    """Decorator for automatic performance logging."""
    def decorator(func):
        op_name = operation or f"{func.__module__}.{func.__name__}"
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            with performance_context(op_name, metadata):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Structured logging utilities

def log_structured(
    logger: logging.Logger,
    level: int,
    message: str,
    **kwargs
) -> None:
    """Log a structured message with additional fields."""
    logger.log(level, message, extra=kwargs)


def log_user_action(
    action: str,
    user_id: Optional[str] = None,
    resource: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """Log user actions for audit purposes."""
    audit_logger = logging.getLogger('audit')
    
    log_data = {
        'action': action,
        'user_id': user_id or 'anonymous',
        'resource': resource,
        'metadata': metadata or {}
    }
    
    audit_logger.info(f"User action: {action}", extra=log_data)


def log_system_event(
    event: str,
    component: str,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """Log system events."""
    system_logger = logging.getLogger('system')
    
    log_data = {
        'event': event,
        'component': component,
        'metadata': metadata or {}
    }
    
    system_logger.info(f"System event: {event}", extra=log_data)


# Error logging utilities

def log_error_with_context(
    logger: logging.Logger,
    error: Exception,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """Log an error with additional context."""
    error_data = {
        'error_type': type(error).__name__,
        'error_message': str(error),
        'context': context or {}
    }
    
    logger.error(f"Error occurred: {error}", extra=error_data, exc_info=True)


# Utility functions

def setup_logging(config: AppConfig) -> LoggingManager:
    """Set up logging for the application."""
    return init_logging_manager(config)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with proper configuration."""
    manager = get_logging_manager()
    if manager:
        return manager.get_logger(name)
    else:
        # Fallback to standard logger if manager not initialized
        return logging.getLogger(name)
# Aliases for backward compatibility
JSONFormatter = StructuredFormatter
PerformanceFilter = PerformanceLogFilter
# Additional classes expected by tests
class LoggingConfig:
    """Configuration class for logging setup."""
    def __init__(self, 
                 log_level: str = "INFO", 
                 log_dir: str = None,
                 max_file_size: int = 10485760,  # 10MB
                 backup_count: int = 5,
                 console_logging: bool = True,
                 file_logging: bool = True,
                 correlation_ids: bool = True,
                 performance_logging: bool = True,
                 format_type: str = "json"):
        self.log_level = log_level
        self.log_dir = Path(log_dir) if log_dir else Path("logs")
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.console_logging = console_logging
        self.file_logging = file_logging
        self.correlation_ids = correlation_ids
        self.performance_logging = performance_logging
        self.format_type = format_type
        
        # Create log directory if it doesn't exist
        if self.file_logging:
            self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def get_correlation_filter(self):
        """Get correlation ID filter."""
        if self.correlation_ids:
            return CorrelationIdFilter()
        return None
    
    def get_performance_filter(self):
        """Get performance filter."""
        if self.performance_logging:
            return PerformanceLogFilter()
        return None
    
    def setup_logging(self):
        """Set up logging based on this configuration."""
        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.log_level.upper()))
        
        # Clear existing handlers and close them
        try:
            for handler in root_logger.handlers[:]:
                handler.close()
                root_logger.removeHandler(handler)
        except (TypeError, AttributeError):
            # Handle case where root_logger is a Mock object in tests
            if hasattr(root_logger, 'handlers'):
                try:
                    root_logger.handlers.clear()
                except:
                    pass
        
        # Create formatter
        formatter = StructuredFormatter()
        
        # Add console handler if enabled
        if self.console_logging:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            
            # Add filters
            if self.correlation_ids:
                console_handler.addFilter(CorrelationIdFilter())
            if self.performance_logging:
                console_handler.addFilter(PerformanceLogFilter())
            
            root_logger.addHandler(console_handler)
        
        # Add file handlers if enabled
        if self.file_logging:
            # Application log handler
            app_log_file = self.log_dir / "application.log"
            app_handler = logging.handlers.RotatingFileHandler(
                app_log_file,
                maxBytes=self.max_file_size,
                backupCount=self.backup_count
            )
            app_handler.setFormatter(formatter)
            
            # Add filters
            if self.correlation_ids:
                app_handler.addFilter(CorrelationIdFilter())
            if self.performance_logging:
                app_handler.addFilter(PerformanceLogFilter())
            
            root_logger.addHandler(app_handler)
            
            # Error log handler (only ERROR and CRITICAL)
            error_log_file = self.log_dir / "error.log"
            error_handler = logging.handlers.RotatingFileHandler(
                error_log_file,
                maxBytes=self.max_file_size,
                backupCount=self.backup_count
            )
            error_handler.setFormatter(formatter)
            error_handler.setLevel(logging.ERROR)
            
            # Add filters
            if self.correlation_ids:
                error_handler.addFilter(CorrelationIdFilter())
            
            root_logger.addHandler(error_handler)

class MindMapLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter for MindMap application."""
    def __init__(self, logger, extra=None):
        super().__init__(logger, extra or {})
    
    def process(self, msg, kwargs):
        """Process the logging call, adding extra context."""
        # Ensure 'extra' exists in kwargs
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        
        # Merge adapter's extra context with kwargs extra
        kwargs['extra'].update(self.extra)
        
        return msg, kwargs
    
    def with_context(self, **context):
        """Create a new adapter with additional context."""
        new_extra = self.extra.copy()
        new_extra.update(context)
        return MindMapLoggerAdapter(self.logger, new_extra)

# Additional utility functions expected by tests
def log_slow_operation(operation: str, duration: float, threshold: float = 1.0):
    """Log slow operations."""
    if duration > threshold:
        logger = logging.getLogger('performance')
        logger.warning(f"Slow operation: {operation} took {duration:.2f}s")

def create_audit_log(action: str, user: str, resource: str = None):
    """Create audit log entry."""
    audit_logger = logging.getLogger('audit')
    audit_logger.info(f"Audit: {user} performed {action} on {resource or 'system'}")

def setup_default_logging():
    """Setup default logging configuration."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')