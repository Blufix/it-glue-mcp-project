"""Distributed tracing with OpenTelemetry."""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
import time
import uuid
from contextlib import contextmanager
import contextvars


class SpanKind(Enum):
    """Span kinds for tracing."""
    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


class SpanStatus(Enum):
    """Span status codes."""
    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


@dataclass
class SpanContext:
    """Context for a span."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    trace_flags: int = 0
    trace_state: Dict[str, str] = field(default_factory=dict)
    
    def is_valid(self) -> bool:
        """Check if context is valid."""
        return bool(self.trace_id and self.span_id)


@dataclass
class Span:
    """Represents a trace span."""
    name: str
    context: SpanContext
    kind: SpanKind = SpanKind.INTERNAL
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    status: SpanStatus = SpanStatus.UNSET
    status_message: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    links: List[SpanContext] = field(default_factory=list)
    
    @property
    def duration_ms(self) -> Optional[float]:
        """Get span duration in milliseconds."""
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return None
    
    def set_attribute(self, key: str, value: Any):
        """Set a span attribute."""
        self.attributes[key] = value
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Add an event to the span."""
        event = {
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {}
        }
        self.events.append(event)
    
    def set_status(self, status: SpanStatus, message: str = ""):
        """Set span status."""
        self.status = status
        self.status_message = message
    
    def end(self):
        """End the span."""
        if not self.end_time:
            self.end_time = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary."""
        return {
            "name": self.name,
            "trace_id": self.context.trace_id,
            "span_id": self.context.span_id,
            "parent_span_id": self.context.parent_span_id,
            "kind": self.kind.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "status_message": self.status_message,
            "attributes": self.attributes,
            "events": self.events
        }


# Context variable for current span
current_span_var = contextvars.ContextVar('current_span', default=None)


class TracingManager:
    """Manage distributed tracing."""
    
    def __init__(
        self,
        service_name: str,
        export_endpoint: Optional[str] = None,
        sample_rate: float = 1.0
    ):
        """
        Initialize tracing manager.
        
        Args:
            service_name: Service name for traces
            export_endpoint: Optional endpoint to export traces
            sample_rate: Sampling rate (0.0 to 1.0)
        """
        self.service_name = service_name
        self.export_endpoint = export_endpoint
        self.sample_rate = sample_rate
        self.spans: List[Span] = []
        self.exporters: List[Callable] = []
        
    def create_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent: Optional[Span] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Span:
        """
        Create a new span.
        
        Args:
            name: Span name
            kind: Span kind
            parent: Parent span
            attributes: Initial attributes
            
        Returns:
            New span
        """
        # Generate IDs
        trace_id = parent.context.trace_id if parent else self._generate_trace_id()
        span_id = self._generate_span_id()
        parent_span_id = parent.context.span_id if parent else None
        
        # Create context
        context = SpanContext(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id
        )
        
        # Create span
        span = Span(
            name=name,
            context=context,
            kind=kind,
            attributes=attributes or {}
        )
        
        # Add service name
        span.set_attribute("service.name", self.service_name)
        
        # Store span
        self.spans.append(span)
        
        return span
    
    @contextmanager
    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None
    ):
        """
        Context manager for creating and managing a span.
        
        Args:
            name: Span name
            kind: Span kind
            attributes: Initial attributes
            
        Usage:
            with tracer.start_span("operation") as span:
                span.set_attribute("key", "value")
                # operation code
        """
        # Get parent span from context
        parent = current_span_var.get()
        
        # Create new span
        span = self.create_span(name, kind, parent, attributes)
        
        # Set as current span
        token = current_span_var.set(span)
        
        try:
            yield span
            span.set_status(SpanStatus.OK)
        except Exception as e:
            span.set_status(SpanStatus.ERROR, str(e))
            span.set_attribute("error.type", type(e).__name__)
            span.set_attribute("error.message", str(e))
            raise
        finally:
            span.end()
            current_span_var.reset(token)
            self._export_span(span)
    
    def _generate_trace_id(self) -> str:
        """Generate a trace ID."""
        return uuid.uuid4().hex
    
    def _generate_span_id(self) -> str:
        """Generate a span ID."""
        return uuid.uuid4().hex[:16]
    
    def _export_span(self, span: Span):
        """Export a completed span."""
        # Call registered exporters
        for exporter in self.exporters:
            try:
                exporter(span)
            except Exception:
                # Ignore exporter errors
                pass
    
    def register_exporter(self, exporter: Callable[[Span], None]):
        """
        Register a span exporter.
        
        Args:
            exporter: Function that exports a span
        """
        self.exporters.append(exporter)
    
    def get_current_span(self) -> Optional[Span]:
        """Get the current active span."""
        return current_span_var.get()
    
    def get_current_trace_id(self) -> Optional[str]:
        """Get the current trace ID."""
        span = self.get_current_span()
        return span.context.trace_id if span else None
    
    def inject_context(self, carrier: Dict[str, str]):
        """
        Inject trace context into a carrier (e.g., HTTP headers).
        
        Args:
            carrier: Dictionary to inject context into
        """
        span = self.get_current_span()
        if span:
            carrier["traceparent"] = self._format_traceparent(span.context)
            if span.context.trace_state:
                carrier["tracestate"] = self._format_tracestate(span.context.trace_state)
    
    def extract_context(self, carrier: Dict[str, str]) -> Optional[SpanContext]:
        """
        Extract trace context from a carrier.
        
        Args:
            carrier: Dictionary containing trace context
            
        Returns:
            Extracted span context or None
        """
        traceparent = carrier.get("traceparent")
        if not traceparent:
            return None
        
        try:
            # Parse traceparent header
            parts = traceparent.split("-")
            if len(parts) != 4:
                return None
            
            version, trace_id, span_id, trace_flags = parts
            
            # Parse tracestate if present
            trace_state = {}
            if "tracestate" in carrier:
                trace_state = self._parse_tracestate(carrier["tracestate"])
            
            return SpanContext(
                trace_id=trace_id,
                span_id=span_id,
                trace_flags=int(trace_flags, 16),
                trace_state=trace_state
            )
        except Exception:
            return None
    
    def _format_traceparent(self, context: SpanContext) -> str:
        """Format traceparent header."""
        return f"00-{context.trace_id}-{context.span_id}-{context.trace_flags:02x}"
    
    def _format_tracestate(self, trace_state: Dict[str, str]) -> str:
        """Format tracestate header."""
        return ",".join(f"{k}={v}" for k, v in trace_state.items())
    
    def _parse_tracestate(self, tracestate: str) -> Dict[str, str]:
        """Parse tracestate header."""
        result = {}
        for item in tracestate.split(","):
            if "=" in item:
                key, value = item.split("=", 1)
                result[key.strip()] = value.strip()
        return result
    
    def trace_function(self, name: Optional[str] = None):
        """
        Decorator to trace function execution.
        
        Args:
            name: Optional span name (defaults to function name)
            
        Usage:
            @tracer.trace_function()
            def my_function():
                pass
        """
        def decorator(func):
            span_name = name or func.__name__
            
            def wrapper(*args, **kwargs):
                with self.start_span(span_name) as span:
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__)
                    return func(*args, **kwargs)
            
            async def async_wrapper(*args, **kwargs):
                with self.start_span(span_name) as span:
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__)
                    return await func(*args, **kwargs)
            
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return wrapper
        
        return decorator
    
    def get_traces_json(self) -> List[Dict[str, Any]]:
        """
        Get all traces as JSON.
        
        Returns:
            List of trace dictionaries
        """
        # Group spans by trace ID
        traces = {}
        for span in self.spans:
            trace_id = span.context.trace_id
            if trace_id not in traces:
                traces[trace_id] = []
            traces[trace_id].append(span.to_dict())
        
        # Format as list of traces
        result = []
        for trace_id, spans in traces.items():
            result.append({
                "trace_id": trace_id,
                "spans": spans,
                "span_count": len(spans),
                "duration_ms": self._calculate_trace_duration(spans)
            })
        
        return result
    
    def _calculate_trace_duration(self, spans: List[Dict[str, Any]]) -> Optional[float]:
        """Calculate total trace duration."""
        if not spans:
            return None
        
        start_times = [s["start_time"] for s in spans if s["start_time"]]
        end_times = [s["end_time"] for s in spans if s["end_time"]]
        
        if not start_times or not end_times:
            return None
        
        return (max(end_times) - min(start_times)) * 1000