"""Comprehensive logging infrastructure for TopoKit with structured logging and observability."""

import logging
import json
import sys
import traceback
from typing import Any, Dict, Optional, List, Union
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, asdict
import threading
from pathlib import Path

try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False

try:
    import opentelemetry
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False


class LogLevel(str, Enum):
    """Log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogComponent(str, Enum):
    """Logging components."""
    ORCHESTRATOR = "orchestrator"
    CONTEXT_STORE = "context_store"
    GUARDRAILS = "guardrails"
    PACK_PARSER = "pack_parser"
    SCHEMA_VALIDATOR = "schema_validator"
    API = "api"
    CLI = "cli"
    DASHBOARD = "dashboard"


@dataclass
class LogContext:
    """Structured log context."""
    trace_id: Optional[str] = None
    session_id: Optional[str] = None
    node_id: Optional[str] = None
    user_id: Optional[str] = None
    component: Optional[LogComponent] = None
    operation: Optional[str] = None
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ErrorDetails:
    """Structured error details."""
    error_type: str
    error_message: str
    stack_trace: Optional[str] = None
    context: Optional[LogContext] = None
    recovery_action: Optional[str] = None
    severity: str = "medium"
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class TopoKitFormatter(logging.Formatter):
    """Custom formatter for TopoKit logs."""
    
    def __init__(self, include_stack_trace: bool = True, include_metadata: bool = True):
        super().__init__()
        self.include_stack_trace = include_stack_trace
        self.include_metadata = include_metadata
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured data."""
        # Base log entry
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add trace context if available
        if hasattr(record, 'trace_id'):
            log_entry["trace_id"] = record.trace_id
        if hasattr(record, 'session_id'):
            log_entry["session_id"] = record.session_id
        if hasattr(record, 'node_id'):
            log_entry["node_id"] = record.node_id
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
        if hasattr(record, 'component'):
            log_entry["component"] = record.component
        if hasattr(record, 'operation'):
            log_entry["operation"] = record.operation
        if hasattr(record, 'duration_ms'):
            log_entry["duration_ms"] = record.duration_ms
        
        # Add exception info
        if record.exc_info and self.include_stack_trace:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "stack_trace": self.formatException(record.exc_info)
            }
        
        # Add extra metadata
        if self.include_metadata and hasattr(record, 'metadata'):
            log_entry["metadata"] = record.metadata
        
        return json.dumps(log_entry, default=str)


class TopoKitLogger:
    """Enhanced logger for TopoKit with structured logging and observability."""
    
    def __init__(self, name: str, component: Optional[LogComponent] = None):
        """Initialize TopoKit logger.
        
        Args:
            name: Logger name
            component: Component this logger belongs to
        """
        self.name = name
        self.component = component
        self._logger = logging.getLogger(name)
        self._context = threading.local()
        
        # Configure structured logging if available
        if STRUCTLOG_AVAILABLE:
            self._struct_logger = structlog.get_logger(name)
        else:
            self._struct_logger = None
    
    def set_context(self, **kwargs):
        """Set logging context for current thread."""
        for key, value in kwargs.items():
            setattr(self._context, key, value)
    
    def clear_context(self):
        """Clear logging context for current thread."""
        for attr in dir(self._context):
            if not attr.startswith('_'):
                delattr(self._context, attr)
    
    def _get_context(self) -> LogContext:
        """Get current logging context."""
        return LogContext(
            trace_id=getattr(self._context, 'trace_id', None),
            session_id=getattr(self._context, 'session_id', None),
            node_id=getattr(self._context, 'node_id', None),
            user_id=getattr(self._context, 'user_id', None),
            component=self.component,
            operation=getattr(self._context, 'operation', None),
            duration_ms=getattr(self._context, 'duration_ms', None),
            metadata=getattr(self._context, 'metadata', {})
        )
    
    def _log_with_context(self, level: LogLevel, message: str, 
                         extra: Optional[Dict[str, Any]] = None,
                         exc_info: Optional[bool] = None):
        """Log with context information."""
        context = self._get_context()
        
        # Prepare extra data
        log_extra = {
            'trace_id': context.trace_id,
            'session_id': context.session_id,
            'node_id': context.node_id,
            'user_id': context.user_id,
            'component': context.component.value if context.component else None,
            'operation': context.operation,
            'duration_ms': context.duration_ms,
            'metadata': {**context.metadata, **(extra or {})}
        }
        
        # Log with standard logger
        self._logger.log(
            getattr(logging, level.value),
            message,
            extra=log_extra,
            exc_info=exc_info
        )
        
        # Log with structured logger if available
        if self._struct_logger:
            self._struct_logger.bind(**log_extra).log(level.value.lower(), message)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._log_with_context(LogLevel.DEBUG, message, kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log_with_context(LogLevel.INFO, message, kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log_with_context(LogLevel.WARNING, message, kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self._log_with_context(LogLevel.ERROR, message, kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self._log_with_context(LogLevel.CRITICAL, message, kwargs)
    
    def log_error(self, error: Exception, context: Optional[LogContext] = None, 
                  recovery_action: Optional[str] = None, severity: str = "medium"):
        """Log structured error details."""
        error_details = ErrorDetails(
            error_type=type(error).__name__,
            error_message=str(error),
            stack_trace=traceback.format_exc(),
            context=context or self._get_context(),
            recovery_action=recovery_action,
            severity=severity
        )
        
        self.error(
            f"Error in {error_details.context.operation or 'unknown operation'}: {error_details.error_message}",
            error_type=error_details.error_type,
            error_message=error_details.error_message,
            stack_trace=error_details.stack_trace,
            recovery_action=error_details.recovery_action,
            severity=error_details.severity,
            exc_info=True
        )
    
    def log_performance(self, operation: str, duration_ms: float, 
                       success: bool = True, **metadata):
        """Log performance metrics."""
        level = LogLevel.INFO if success else LogLevel.WARNING
        self._log_with_context(
            level,
            f"Performance: {operation} completed in {duration_ms:.2f}ms",
            {
                'operation': operation,
                'duration_ms': duration_ms,
                'success': success,
                **metadata
            }
        )
    
    def log_audit(self, action: str, resource: str, user_id: Optional[str] = None, 
                  success: bool = True, **metadata):
        """Log audit events."""
        self._log_with_context(
            LogLevel.INFO,
            f"Audit: {action} on {resource} by {user_id or 'system'}",
            {
                'audit_action': action,
                'audit_resource': resource,
                'audit_user_id': user_id,
                'audit_success': success,
                **metadata
            }
        )


class LoggingConfig:
    """Configuration for TopoKit logging system."""
    
    def __init__(self, 
                 log_level: LogLevel = LogLevel.INFO,
                 log_format: str = "json",
                 log_file: Optional[str] = None,
                 enable_console: bool = True,
                 enable_structured: bool = True,
                 enable_otel: bool = False,
                 otel_endpoint: Optional[str] = None):
        """Initialize logging configuration.
        
        Args:
            log_level: Minimum log level
            log_format: Log format (json, text)
            log_file: Log file path
            enable_console: Enable console logging
            enable_structured: Enable structured logging
            enable_otel: Enable OpenTelemetry integration
            otel_endpoint: OpenTelemetry endpoint
        """
        self.log_level = log_level
        self.log_format = log_format
        self.log_file = log_file
        self.enable_console = enable_console
        self.enable_structured = enable_structured
        self.enable_otel = enable_otel
        self.otel_endpoint = otel_endpoint
    
    def configure(self):
        """Configure logging system."""
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.log_level.value))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Console handler
        if self.enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, self.log_level.value))
            
            if self.log_format == "json":
                formatter = TopoKitFormatter()
            else:
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
        
        # File handler
        if self.log_file:
            file_handler = logging.FileHandler(self.log_file)
            file_handler.setLevel(getattr(logging, self.log_level.value))
            file_handler.setFormatter(TopoKitFormatter())
            root_logger.addHandler(file_handler)
        
        # Configure structured logging
        if self.enable_structured and STRUCTLOG_AVAILABLE:
            structlog.configure(
                processors=[
                    structlog.stdlib.filter_by_level,
                    structlog.stdlib.add_logger_name,
                    structlog.stdlib.add_log_level,
                    structlog.stdlib.PositionalArgumentsFormatter(),
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.StackInfoRenderer(),
                    structlog.processors.format_exc_info,
                    structlog.processors.UnicodeDecoder(),
                    structlog.processors.JSONRenderer()
                ],
                context_class=dict,
                logger_factory=structlog.stdlib.LoggerFactory(),
                wrapper_class=structlog.stdlib.BoundLogger,
                cache_logger_on_first_use=True,
            )
        
        # Configure OpenTelemetry
        if self.enable_otel and OPENTELEMETRY_AVAILABLE and self.otel_endpoint:
            self._configure_otel()
    
    def _configure_otel(self):
        """Configure OpenTelemetry tracing."""
        if not OPENTELEMETRY_AVAILABLE:
            return
        
        # Create resource
        resource = Resource.create({
            "service.name": "topokit",
            "service.version": "0.1.0"
        })
        
        # Create tracer provider
        tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(tracer_provider)
        
        # Create OTLP exporter
        otlp_exporter = OTLPSpanExporter(endpoint=self.otel_endpoint)
        
        # Create span processor
        span_processor = BatchSpanProcessor(otlp_exporter)
        tracer_provider.add_span_processor(span_processor)


def get_logger(name: str, component: Optional[LogComponent] = None) -> TopoKitLogger:
    """Get TopoKit logger instance.
    
    Args:
        name: Logger name
        component: Component this logger belongs to
        
    Returns:
        TopoKitLogger instance
    """
    return TopoKitLogger(name, component)


def configure_logging(config: LoggingConfig):
    """Configure TopoKit logging system.
    
    Args:
        config: Logging configuration
    """
    config.configure()


# Default configuration
DEFAULT_CONFIG = LoggingConfig(
    log_level=LogLevel.INFO,
    log_format="json",
    enable_console=True,
    enable_structured=True,
    enable_otel=False
)

# Configure default logging
configure_logging(DEFAULT_CONFIG)
