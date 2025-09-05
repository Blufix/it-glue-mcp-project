"""Monitoring and observability module."""

from .health import ComponentHealth, HealthChecker, HealthStatus

# Import only what exists
try:
    from .logging import LogLevel, StructuredLogger
    _has_logging = True
except ImportError:
    _has_logging = False

try:
    from .tracing import SpanContext, TracingManager  
    _has_tracing = True
except ImportError:
    _has_tracing = False

__all__ = [
    'HealthChecker',
    'HealthStatus',
    'ComponentHealth',
]

if _has_logging:
    __all__.extend(['StructuredLogger', 'LogLevel'])
    
if _has_tracing:
    __all__.extend(['TracingManager', 'SpanContext'])
