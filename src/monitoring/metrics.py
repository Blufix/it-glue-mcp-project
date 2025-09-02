"""Prometheus metrics for IT Glue MCP Server."""

import time
from collections.abc import Callable
from functools import wraps

from prometheus_client import Counter, Gauge, Histogram, Info

# Request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# Query metrics
query_requests_total = Counter(
    'query_requests_total',
    'Total query requests',
    ['query_type', 'company']
)

query_duration_seconds = Histogram(
    'query_duration_seconds',
    'Query execution duration in seconds',
    ['query_type']
)

query_confidence_score = Histogram(
    'query_confidence_score',
    'Query confidence scores',
    ['query_type'],
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
)

# IT Glue sync metrics
itglue_sync_total = Counter(
    'itglue_sync_total',
    'Total IT Glue sync operations',
    ['sync_type', 'status']
)

itglue_sync_duration_seconds = Histogram(
    'itglue_sync_duration_seconds',
    'IT Glue sync duration in seconds',
    ['sync_type']
)

itglue_entities_total = Gauge(
    'itglue_entities_total',
    'Total number of IT Glue entities',
    ['entity_type']
)

itglue_last_sync_timestamp = Gauge(
    'itglue_last_sync_timestamp',
    'Timestamp of last successful sync',
    ['sync_type']
)

itglue_sync_failures_total = Counter(
    'itglue_sync_failures_total',
    'Total IT Glue sync failures',
    ['sync_type', 'error_type']
)

# Rate limiting metrics
itglue_rate_limit_remaining = Gauge(
    'itglue_rate_limit_remaining',
    'Remaining IT Glue API rate limit'
)

itglue_rate_limit_max = Gauge(
    'itglue_rate_limit_max',
    'Maximum IT Glue API rate limit'
)

# Cache metrics
cache_hits_total = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache_type']
)

cache_misses_total = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['cache_type']
)

cache_evictions_total = Counter(
    'cache_evictions_total',
    'Total cache evictions',
    ['cache_type']
)

cache_size_bytes = Gauge(
    'cache_size_bytes',
    'Current cache size in bytes',
    ['cache_type']
)

# Database metrics
db_connections_active = Gauge(
    'db_connections_active',
    'Active database connections',
    ['database']
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['database', 'operation']
)

# Vector search metrics
vector_search_duration_seconds = Histogram(
    'vector_search_duration_seconds',
    'Vector search duration in seconds',
    ['collection']
)

vector_search_results_count = Histogram(
    'vector_search_results_count',
    'Number of vector search results returned',
    ['collection'],
    buckets=(0, 1, 5, 10, 20, 50, 100)
)

# Graph database metrics
graph_query_duration_seconds = Histogram(
    'graph_query_duration_seconds',
    'Graph query duration in seconds',
    ['query_type']
)

graph_traversal_depth = Histogram(
    'graph_traversal_depth',
    'Graph traversal depth',
    ['query_type'],
    buckets=(1, 2, 3, 4, 5, 10)
)

# MCP Server metrics
mcp_connections_active = Gauge(
    'mcp_connections_active',
    'Active MCP connections'
)

mcp_tool_calls_total = Counter(
    'mcp_tool_calls_total',
    'Total MCP tool calls',
    ['tool_name', 'status']
)

mcp_tool_duration_seconds = Histogram(
    'mcp_tool_duration_seconds',
    'MCP tool execution duration in seconds',
    ['tool_name']
)

# System info
system_info = Info(
    'itglue_mcp_system',
    'IT Glue MCP Server system information'
)

# Initialize system info
system_info.info({
    'version': '1.0.0',
    'environment': 'production'
})


def track_request_metrics(method: str, endpoint: str, status: int, duration: float):
    """Track HTTP request metrics."""
    http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)


def track_query_metrics(query_type: str, company: str, duration: float, confidence: float):
    """Track query execution metrics."""
    query_requests_total.labels(query_type=query_type, company=company).inc()
    query_duration_seconds.labels(query_type=query_type).observe(duration)
    query_confidence_score.labels(query_type=query_type).observe(confidence)


def track_sync_metrics(sync_type: str, status: str, duration: float = None):
    """Track IT Glue sync metrics."""
    itglue_sync_total.labels(sync_type=sync_type, status=status).inc()
    if duration:
        itglue_sync_duration_seconds.labels(sync_type=sync_type).observe(duration)
    if status == 'success':
        itglue_last_sync_timestamp.labels(sync_type=sync_type).set(time.time())


def track_cache_metrics(cache_type: str, hit: bool):
    """Track cache metrics."""
    if hit:
        cache_hits_total.labels(cache_type=cache_type).inc()
    else:
        cache_misses_total.labels(cache_type=cache_type).inc()


def track_mcp_tool_call(tool_name: str, status: str, duration: float):
    """Track MCP tool call metrics."""
    mcp_tool_calls_total.labels(tool_name=tool_name, status=status).inc()
    mcp_tool_duration_seconds.labels(tool_name=tool_name).observe(duration)


def metrics_decorator(metric_type: str = "http"):
    """Decorator to automatically track metrics."""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                if metric_type == "http":
                    # Extract method and endpoint from args if available
                    track_request_metrics("GET", func.__name__, 200, duration)
                elif metric_type == "query":
                    track_query_metrics(func.__name__, "default", duration, 1.0)
                elif metric_type == "mcp":
                    track_mcp_tool_call(func.__name__, "success", duration)

                return result
            except Exception as e:
                duration = time.time() - start_time

                if metric_type == "http":
                    track_request_metrics("GET", func.__name__, 500, duration)
                elif metric_type == "mcp":
                    track_mcp_tool_call(func.__name__, "error", duration)

                raise e

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                if metric_type == "http":
                    track_request_metrics("GET", func.__name__, 200, duration)

                return result
            except Exception as e:
                duration = time.time() - start_time
                track_request_metrics("GET", func.__name__, 500, duration)
                raise e

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


import asyncio
