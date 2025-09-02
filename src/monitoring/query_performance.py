"""Performance monitoring for query pipeline."""

import asyncio
import json
import time
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from prometheus_client import Counter, Gauge, Histogram, Summary

from src.monitoring.logging import StructuredLogger
from src.monitoring.tracing import SpanKind, TracingManager

# Configure logger
logger = StructuredLogger(__name__)


class QueryStage(Enum):
    """Query processing stages."""
    PARSING = "parsing"
    ENHANCEMENT = "enhancement"
    ENTITY_EXTRACTION = "entity_extraction"
    INTENT_CLASSIFICATION = "intent_classification"
    TEMPLATE_MATCHING = "template_matching"
    CACHE_LOOKUP = "cache_lookup"
    DATABASE_QUERY = "database_query"
    RESULT_RANKING = "result_ranking"
    RESPONSE_FORMATTING = "response_formatting"


@dataclass
class QueryMetrics:
    """Metrics for a query execution."""
    query_id: str
    query_text: str
    start_time: float
    end_time: Optional[float] = None
    stage_durations: dict[str, float] = field(default_factory=dict)
    fuzzy_corrections: int = 0
    cache_hit: bool = False
    result_count: int = 0
    error: Optional[str] = None
    slow_query: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_duration_ms(self) -> float:
        """Get total duration in milliseconds."""
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0

    @property
    def is_slow(self) -> bool:
        """Check if query is slow (>500ms)."""
        return self.total_duration_ms > 500


class QueryPerformanceMonitor:
    """Monitor query pipeline performance."""

    # Prometheus metrics
    query_counter = Counter(
        'itglue_query_total',
        'Total number of queries processed',
        ['status', 'cache_hit']
    )

    query_duration = Histogram(
        'itglue_query_duration_seconds',
        'Query processing duration in seconds',
        ['stage'],
        buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
    )

    fuzzy_corrections_counter = Counter(
        'itglue_fuzzy_corrections_total',
        'Total number of fuzzy corrections applied',
        ['correction_type']
    )

    cache_counter = Counter(
        'itglue_cache_requests_total',
        'Total cache requests',
        ['cache_type', 'hit']
    )

    slow_query_counter = Counter(
        'itglue_slow_queries_total',
        'Total number of slow queries (>500ms)'
    )

    active_queries = Gauge(
        'itglue_active_queries',
        'Number of currently active queries'
    )

    result_count_summary = Summary(
        'itglue_query_result_count',
        'Number of results returned per query'
    )

    fuzzy_success_rate = Gauge(
        'itglue_fuzzy_success_rate',
        'Success rate of fuzzy matching corrections'
    )

    p95_latency = Gauge(
        'itglue_query_p95_latency_ms',
        'P95 query latency in milliseconds'
    )

    def __init__(
        self,
        slow_query_threshold_ms: float = 500,
        enable_tracing: bool = True,
        log_slow_queries: bool = True
    ):
        """
        Initialize performance monitor.

        Args:
            slow_query_threshold_ms: Threshold for slow queries
            enable_tracing: Enable distributed tracing
            log_slow_queries: Log slow queries for analysis
        """
        self.slow_query_threshold = slow_query_threshold_ms
        self.enable_tracing = enable_tracing
        self.log_slow_queries = log_slow_queries

        # Initialize tracing
        if enable_tracing:
            self.tracer = TracingManager(
                service_name="itglue-query-pipeline",
                sample_rate=1.0
            )
        else:
            self.tracer = None

        # Track recent queries for P95 calculation
        self.recent_durations: list[float] = []
        self.max_recent = 1000  # Keep last 1000 queries

        # Track fuzzy correction success
        self.fuzzy_attempts = 0
        self.fuzzy_successes = 0

        # Active query tracking
        self.active_queries_map: dict[str, QueryMetrics] = {}

    @contextmanager
    def track_query(self, query_id: str, query_text: str):
        """
        Track a query execution.

        Args:
            query_id: Unique query ID
            query_text: Query text

        Usage:
            with monitor.track_query(query_id, "server status") as metrics:
                # Process query
                pass
        """
        # Start tracking
        metrics = QueryMetrics(
            query_id=query_id,
            query_text=query_text[:200],  # Truncate long queries
            start_time=time.time()
        )

        self.active_queries_map[query_id] = metrics
        self.active_queries.inc()

        # Start trace span if enabled
        span = None
        if self.tracer:
            span = self.tracer.create_span(
                name="query_processing",
                kind=SpanKind.SERVER,
                attributes={
                    "query.id": query_id,
                    "query.text": query_text[:200]
                }
            )

        try:
            yield metrics

            # Mark as successful
            metrics.end_time = time.time()
            self._record_metrics(metrics, success=True)

            if span:
                span.set_status(span.status.OK)

        except Exception as e:
            # Mark as failed
            metrics.end_time = time.time()
            metrics.error = str(e)
            self._record_metrics(metrics, success=False)

            if span:
                span.set_status(span.status.ERROR, str(e))

            raise

        finally:
            # Clean up
            self.active_queries_map.pop(query_id, None)
            self.active_queries.dec()

            if span:
                span.end()

    @contextmanager
    def track_stage(self, query_id: str, stage: QueryStage):
        """
        Track a specific stage within query processing.

        Args:
            query_id: Query ID
            stage: Processing stage

        Usage:
            with monitor.track_stage(query_id, QueryStage.ENHANCEMENT):
                # Perform enhancement
                pass
        """
        metrics = self.active_queries_map.get(query_id)
        if not metrics:
            yield None
            return

        start = time.time()

        # Start trace span if enabled
        span = None
        if self.tracer:
            span = self.tracer.create_span(
                name=f"query.{stage.value}",
                kind=SpanKind.INTERNAL,
                attributes={
                    "query.id": query_id,
                    "stage": stage.value
                }
            )

        try:
            yield metrics

            if span:
                span.set_status(span.status.OK)

        finally:
            # Record stage duration
            duration = time.time() - start
            metrics.stage_durations[stage.value] = duration
            self.query_duration.labels(stage=stage.value).observe(duration)

            if span:
                span.end()

    def record_fuzzy_correction(
        self,
        query_id: str,
        correction_type: str,
        original: str,
        corrected: str,
        confidence: float
    ):
        """
        Record a fuzzy correction.

        Args:
            query_id: Query ID
            correction_type: Type of correction (typo, phonetic, acronym)
            original: Original text
            corrected: Corrected text
            confidence: Correction confidence score
        """
        metrics = self.active_queries_map.get(query_id)
        if metrics:
            metrics.fuzzy_corrections += 1

            # Track correction details
            if "corrections" not in metrics.metadata:
                metrics.metadata["corrections"] = []

            metrics.metadata["corrections"].append({
                "type": correction_type,
                "original": original,
                "corrected": corrected,
                "confidence": confidence
            })

        # Update counters
        self.fuzzy_corrections_counter.labels(correction_type=correction_type).inc()

        # Track success rate
        self.fuzzy_attempts += 1
        if confidence > 0.8:  # Consider >80% confidence as success
            self.fuzzy_successes += 1

        # Update success rate gauge
        if self.fuzzy_attempts > 0:
            success_rate = self.fuzzy_successes / self.fuzzy_attempts
            self.fuzzy_success_rate.set(success_rate)

    def record_cache_hit(self, query_id: str, cache_type: str = "query"):
        """
        Record a cache hit.

        Args:
            query_id: Query ID
            cache_type: Type of cache (query, fuzzy, template)
        """
        metrics = self.active_queries_map.get(query_id)
        if metrics:
            metrics.cache_hit = True
            metrics.metadata["cache_type"] = cache_type

        self.cache_counter.labels(cache_type=cache_type, hit="true").inc()

    def record_cache_miss(self, query_id: str, cache_type: str = "query"):
        """
        Record a cache miss.

        Args:
            query_id: Query ID
            cache_type: Type of cache
        """
        self.cache_counter.labels(cache_type=cache_type, hit="false").inc()

    def record_result_count(self, query_id: str, count: int):
        """
        Record number of results returned.

        Args:
            query_id: Query ID
            count: Number of results
        """
        metrics = self.active_queries_map.get(query_id)
        if metrics:
            metrics.result_count = count

        self.result_count_summary.observe(count)

    def _record_metrics(self, metrics: QueryMetrics, success: bool):
        """
        Record metrics to Prometheus and logs.

        Args:
            metrics: Query metrics
            success: Whether query succeeded
        """
        # Update counters
        status = "success" if success else "failure"
        cache_hit = "true" if metrics.cache_hit else "false"
        self.query_counter.labels(status=status, cache_hit=cache_hit).inc()

        # Track duration
        duration_ms = metrics.total_duration_ms

        # Update recent durations for P95 calculation
        self.recent_durations.append(duration_ms)
        if len(self.recent_durations) > self.max_recent:
            self.recent_durations.pop(0)

        # Calculate and update P95
        if len(self.recent_durations) >= 20:  # Need minimum samples
            sorted_durations = sorted(self.recent_durations)
            p95_index = int(len(sorted_durations) * 0.95)
            p95_value = sorted_durations[p95_index]
            self.p95_latency.set(p95_value)

        # Check for slow query
        if duration_ms > self.slow_query_threshold:
            metrics.slow_query = True
            self.slow_query_counter.inc()

            if self.log_slow_queries:
                self._log_slow_query(metrics)

        # Log metrics
        logger.info(
            f"Query completed: {metrics.query_id}",
            query_id=metrics.query_id,
            duration_ms=duration_ms,
            stage_durations=metrics.stage_durations,
            fuzzy_corrections=metrics.fuzzy_corrections,
            cache_hit=metrics.cache_hit,
            result_count=metrics.result_count,
            slow_query=metrics.slow_query,
            success=success
        )

    def _log_slow_query(self, metrics: QueryMetrics):
        """
        Log details of a slow query for analysis.

        Args:
            metrics: Query metrics
        """
        # Find slowest stages
        slowest_stages = sorted(
            metrics.stage_durations.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]

        logger.warning(
            f"Slow query detected: {metrics.query_id}",
            query_id=metrics.query_id,
            query_text=metrics.query_text,
            total_duration_ms=metrics.total_duration_ms,
            slowest_stages=slowest_stages,
            fuzzy_corrections=metrics.fuzzy_corrections,
            cache_hit=metrics.cache_hit,
            result_count=metrics.result_count,
            metadata=metrics.metadata
        )

        # Also write to slow query log file
        slow_query_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "query_id": metrics.query_id,
            "query_text": metrics.query_text,
            "duration_ms": metrics.total_duration_ms,
            "stages": metrics.stage_durations,
            "corrections": metrics.metadata.get("corrections", []),
            "cache_hit": metrics.cache_hit,
            "result_count": metrics.result_count
        }

        # Append to slow query log
        with open("/tmp/slow_queries.jsonl", "a") as f:
            f.write(json.dumps(slow_query_data) + "\n")

    def get_active_queries(self) -> list[dict[str, Any]]:
        """
        Get currently active queries.

        Returns:
            List of active query details
        """
        active = []
        current_time = time.time()

        for query_id, metrics in self.active_queries_map.items():
            active.append({
                "query_id": query_id,
                "query_text": metrics.query_text,
                "duration_so_far_ms": (current_time - metrics.start_time) * 1000,
                "stages_completed": list(metrics.stage_durations.keys())
            })

        return active

    def get_performance_summary(self) -> dict[str, Any]:
        """
        Get performance summary.

        Returns:
            Performance metrics summary
        """
        # Calculate P95 if we have enough data
        p95 = None
        if len(self.recent_durations) >= 20:
            sorted_durations = sorted(self.recent_durations)
            p95_index = int(len(sorted_durations) * 0.95)
            p95 = sorted_durations[p95_index]

        # Calculate fuzzy success rate
        fuzzy_success_rate = 0
        if self.fuzzy_attempts > 0:
            fuzzy_success_rate = self.fuzzy_successes / self.fuzzy_attempts

        return {
            "active_queries": len(self.active_queries_map),
            "p95_latency_ms": p95,
            "fuzzy_success_rate": fuzzy_success_rate,
            "fuzzy_attempts": self.fuzzy_attempts,
            "recent_query_count": len(self.recent_durations),
            "slow_query_threshold_ms": self.slow_query_threshold
        }

    @asynccontextmanager
    async def track_async_query(self, query_id: str, query_text: str):
        """
        Async version of track_query for async pipelines.

        Args:
            query_id: Unique query ID
            query_text: Query text
        """
        metrics = QueryMetrics(
            query_id=query_id,
            query_text=query_text[:200],
            start_time=time.time()
        )

        self.active_queries_map[query_id] = metrics
        self.active_queries.inc()

        try:
            yield metrics

            metrics.end_time = time.time()
            self._record_metrics(metrics, success=True)

        except Exception as e:
            metrics.end_time = time.time()
            metrics.error = str(e)
            self._record_metrics(metrics, success=False)
            raise

        finally:
            self.active_queries_map.pop(query_id, None)
            self.active_queries.dec()

    @asynccontextmanager
    async def track_async_stage(self, query_id: str, stage: QueryStage):
        """
        Async version of track_stage.

        Args:
            query_id: Query ID
            stage: Processing stage
        """
        metrics = self.active_queries_map.get(query_id)
        if not metrics:
            yield None
            return

        start = time.time()

        try:
            yield metrics
        finally:
            duration = time.time() - start
            metrics.stage_durations[stage.value] = duration
            self.query_duration.labels(stage=stage.value).observe(duration)


# Global instance
_monitor = None


def get_monitor() -> QueryPerformanceMonitor:
    """Get global performance monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = QueryPerformanceMonitor()
    return _monitor


# Decorator for monitoring functions
def monitor_performance(stage: QueryStage):
    """
    Decorator to monitor function performance.

    Args:
        stage: Query processing stage

    Usage:
        @monitor_performance(QueryStage.ENHANCEMENT)
        def enhance_query(query_id, query):
            # Process query
            pass
    """
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                # Try to extract query_id from args/kwargs
                query_id = kwargs.get('query_id')
                if not query_id and args:
                    query_id = args[0] if isinstance(args[0], str) else None

                if query_id:
                    monitor = get_monitor()
                    async with monitor.track_async_stage(query_id, stage):
                        return await func(*args, **kwargs)
                else:
                    return await func(*args, **kwargs)

            return async_wrapper
        else:
            def wrapper(*args, **kwargs):
                # Try to extract query_id from args/kwargs
                query_id = kwargs.get('query_id')
                if not query_id and args:
                    query_id = args[0] if isinstance(args[0], str) else None

                if query_id:
                    monitor = get_monitor()
                    with monitor.track_stage(query_id, stage):
                        return func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)

            return wrapper

    return decorator
