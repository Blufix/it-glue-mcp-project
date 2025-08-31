"""Structured JSON logging for observability."""

import json
import logging
import sys
import traceback
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from enum import Enum
from datetime import datetime
import contextvars


class LogLevel(Enum):
    """Log levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# Context variables for request tracking
request_id_var = contextvars.ContextVar('request_id', default=None)
user_id_var = contextvars.ContextVar('user_id', default=None)
trace_id_var = contextvars.ContextVar('trace_id', default=None)


@dataclass
class LogEntry:
    """Structured log entry."""
    timestamp: str
    level: str
    message: str
    logger: str
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    trace_id: Optional[str] = None
    metadata: Dict[str, Any] = None
    error: Optional[Dict[str, Any]] = None
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        data = asdict(self)
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}
        return json.dumps(data)


class StructuredJSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Get context variables
        request_id = request_id_var.get()
        user_id = user_id_var.get()
        trace_id = trace_id_var.get()
        
        # Build metadata
        metadata = {}
        
        # Add record attributes
        if hasattr(record, 'metadata'):
            metadata.update(record.metadata)
        
        # Add standard fields
        metadata['pathname'] = record.pathname
        metadata['lineno'] = record.lineno
        metadata['funcName'] = record.funcName
        metadata['process'] = record.process
        metadata['thread'] = record.thread
        
        # Handle exception info
        error_info = None
        if record.exc_info:
            error_info = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Create log entry
        entry = LogEntry(
            timestamp=datetime.utcnow().isoformat() + 'Z',
            level=record.levelname.lower(),
            message=record.getMessage(),
            logger=record.name,
            request_id=request_id,
            user_id=user_id,
            trace_id=trace_id,
            metadata=metadata if metadata else None,
            error=error_info
        )
        
        return entry.to_json()


class StructuredLogger:
    """Structured logger with context support."""
    
    def __init__(
        self,
        name: str,
        level: LogLevel = LogLevel.INFO,
        output_format: str = "json"
    ):
        """
        Initialize structured logger.
        
        Args:
            name: Logger name
            level: Log level
            output_format: Output format (json or text)
        """
        self.logger = logging.getLogger(name)
        self._setup_logger(level, output_format)
        
    def _setup_logger(self, level: LogLevel, output_format: str):
        """Set up logger configuration."""
        # Set level
        level_map = {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.CRITICAL: logging.CRITICAL
        }
        self.logger.setLevel(level_map[level])
        
        # Remove existing handlers
        self.logger.handlers = []
        
        # Create handler
        handler = logging.StreamHandler(sys.stdout)
        
        # Set formatter
        if output_format == "json":
            formatter = StructuredJSONFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def debug(self, message: str, **metadata):
        """Log debug message."""
        self._log(LogLevel.DEBUG, message, metadata)
    
    def info(self, message: str, **metadata):
        """Log info message."""
        self._log(LogLevel.INFO, message, metadata)
    
    def warning(self, message: str, **metadata):
        """Log warning message."""
        self._log(LogLevel.WARNING, message, metadata)
    
    def error(self, message: str, error: Optional[Exception] = None, **metadata):
        """Log error message."""
        if error:
            metadata['error_type'] = type(error).__name__
            metadata['error_message'] = str(error)
            self.logger.error(message, exc_info=error, extra={'metadata': metadata})
        else:
            self._log(LogLevel.ERROR, message, metadata)
    
    def critical(self, message: str, error: Optional[Exception] = None, **metadata):
        """Log critical message."""
        if error:
            metadata['error_type'] = type(error).__name__
            metadata['error_message'] = str(error)
            self.logger.critical(message, exc_info=error, extra={'metadata': metadata})
        else:
            self._log(LogLevel.CRITICAL, message, metadata)
    
    def _log(self, level: LogLevel, message: str, metadata: Dict[str, Any]):
        """Internal log method."""
        level_map = {
            LogLevel.DEBUG: self.logger.debug,
            LogLevel.INFO: self.logger.info,
            LogLevel.WARNING: self.logger.warning,
            LogLevel.ERROR: self.logger.error,
            LogLevel.CRITICAL: self.logger.critical
        }
        
        log_func = level_map[level]
        log_func(message, extra={'metadata': metadata})
    
    def with_context(
        self,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ):
        """
        Context manager for setting log context.
        
        Args:
            request_id: Request ID
            user_id: User ID
            trace_id: Trace ID
            
        Usage:
            with logger.with_context(request_id="req-123"):
                logger.info("Processing request")
        """
        class LogContext:
            def __init__(self, req_id, usr_id, trc_id):
                self.request_id = req_id
                self.user_id = usr_id
                self.trace_id = trc_id
                self.tokens = []
            
            def __enter__(self):
                if self.request_id:
                    self.tokens.append(request_id_var.set(self.request_id))
                if self.user_id:
                    self.tokens.append(user_id_var.set(self.user_id))
                if self.trace_id:
                    self.tokens.append(trace_id_var.set(self.trace_id))
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                for token in self.tokens:
                    request_id_var.reset(token)
        
        return LogContext(request_id, user_id, trace_id)
    
    def log_request(
        self,
        method: str,
        path: str,
        status: int,
        duration_ms: float,
        **metadata
    ):
        """
        Log HTTP request.
        
        Args:
            method: HTTP method
            path: Request path
            status: Response status code
            duration_ms: Request duration in milliseconds
            **metadata: Additional metadata
        """
        self.info(
            f"{method} {path} {status}",
            method=method,
            path=path,
            status=status,
            duration_ms=duration_ms,
            **metadata
        )
    
    def log_query(
        self,
        query_type: str,
        query: str,
        duration_ms: float,
        result_count: int = 0,
        **metadata
    ):
        """
        Log database query.
        
        Args:
            query_type: Type of query
            query: Query string
            duration_ms: Query duration in milliseconds
            result_count: Number of results
            **metadata: Additional metadata
        """
        self.info(
            f"Query executed: {query_type}",
            query_type=query_type,
            query=query[:200],  # Truncate long queries
            duration_ms=duration_ms,
            result_count=result_count,
            **metadata
        )
    
    def log_cache_operation(
        self,
        operation: str,
        cache_key: str,
        hit: bool,
        **metadata
    ):
        """
        Log cache operation.
        
        Args:
            operation: Cache operation (get, set, delete)
            cache_key: Cache key
            hit: Whether it was a cache hit
            **metadata: Additional metadata
        """
        self.debug(
            f"Cache {operation}: {'hit' if hit else 'miss'}",
            operation=operation,
            cache_key=cache_key,
            cache_hit=hit,
            **metadata
        )
    
    def log_external_call(
        self,
        service: str,
        operation: str,
        duration_ms: float,
        success: bool,
        **metadata
    ):
        """
        Log external service call.
        
        Args:
            service: Service name
            operation: Operation performed
            duration_ms: Call duration in milliseconds
            success: Whether call succeeded
            **metadata: Additional metadata
        """
        level = LogLevel.INFO if success else LogLevel.WARNING
        self._log(
            level,
            f"External call to {service}: {operation}",
            {
                'service': service,
                'operation': operation,
                'duration_ms': duration_ms,
                'success': success,
                **metadata
            }
        )
    
    def log_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = "",
        **metadata
    ):
        """
        Log a metric value.
        
        Args:
            metric_name: Metric name
            value: Metric value
            unit: Unit of measurement
            **metadata: Additional metadata
        """
        self.info(
            f"Metric: {metric_name}={value}{unit}",
            metric_name=metric_name,
            metric_value=value,
            metric_unit=unit,
            **metadata
        )