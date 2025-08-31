"""Metrics collector for query analytics dashboard."""

import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
from prometheus_client import (
    Counter, Histogram, Gauge, Summary,
    CollectorRegistry, generate_latest
)

logger = logging.getLogger(__name__)


@dataclass
class QueryMetrics:
    """Container for query metrics."""
    query_type: str
    success: bool
    duration_ms: float
    cache_hit: bool = False
    fuzzy_match_used: bool = False
    fuzzy_match_accurate: bool = None
    organization_id: str = None
    user_id: str = None
    error_type: str = None
    result_count: int = 0


class MetricsCollector:
    """Collect and expose metrics for Grafana dashboard."""
    
    def __init__(self, registry: CollectorRegistry = None):
        """Initialize metrics collector."""
        self.registry = registry or CollectorRegistry()
        
        # Query metrics
        self.query_total = Counter(
            'query_total',
            'Total number of queries',
            ['query_type', 'organization'],
            registry=self.registry
        )
        
        self.query_success = Counter(
            'query_success_total',
            'Total number of successful queries',
            ['query_type'],
            registry=self.registry
        )
        
        self.query_failures = Counter(
            'query_failures_total',
            'Total number of failed queries',
            ['query_type', 'error_type'],
            registry=self.registry
        )
        
        self.query_duration = Histogram(
            'query_duration_seconds',
            'Query duration in seconds',
            ['query_type', 'query_pattern'],
            buckets=(0.01, 0.025, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0),
            registry=self.registry
        )
        
        # Cache metrics
        self.cache_hits = Counter(
            'cache_hits_total',
            'Total cache hits',
            ['cache_type'],
            registry=self.registry
        )
        
        self.cache_misses = Counter(
            'cache_misses_total',
            'Total cache misses',
            ['cache_type'],
            registry=self.registry
        )
        
        # Fuzzy matching metrics
        self.fuzzy_match_total = Counter(
            'fuzzy_match_total',
            'Total fuzzy matches attempted',
            registry=self.registry
        )
        
        self.fuzzy_match_correct = Counter(
            'fuzzy_match_correct_total',
            'Total correct fuzzy matches',
            registry=self.registry
        )
        
        # User satisfaction metrics
        self.user_satisfaction = Gauge(
            'user_satisfaction_score',
            'User satisfaction score (0-5)',
            ['user_id'],
            registry=self.registry
        )
        
        # System metrics
        self.active_connections = Gauge(
            'active_connections',
            'Number of active database connections',
            ['database'],
            registry=self.registry
        )
        
        self.memory_usage = Gauge(
            'memory_usage_bytes',
            'Memory usage in bytes',
            ['component'],
            registry=self.registry
        )
        
        # Performance SLA metrics
        self.sla_violations = Counter(
            'sla_violations_total',
            'Total SLA violations (>200ms P95)',
            registry=self.registry
        )
        
        # Initialize tracking data
        self.query_patterns = {}
        self.user_scores = {}
        self.recent_queries = []
        self.p95_threshold_ms = 200
        
    def record_query(self, metrics: QueryMetrics) -> None:
        """Record query metrics."""
        org = metrics.organization_id or "unknown"
        
        # Increment counters
        self.query_total.labels(
            query_type=metrics.query_type,
            organization=org
        ).inc()
        
        if metrics.success:
            self.query_success.labels(query_type=metrics.query_type).inc()
        else:
            error_type = metrics.error_type or "unknown"
            self.query_failures.labels(
                query_type=metrics.query_type,
                error_type=error_type
            ).inc()
        
        # Record duration
        pattern = self._extract_query_pattern(metrics.query_type)
        self.query_duration.labels(
            query_type=metrics.query_type,
            query_pattern=pattern
        ).observe(metrics.duration_ms / 1000.0)
        
        # Cache metrics
        if metrics.cache_hit:
            self.cache_hits.labels(cache_type="query").inc()
        else:
            self.cache_misses.labels(cache_type="query").inc()
        
        # Fuzzy matching metrics
        if metrics.fuzzy_match_used:
            self.fuzzy_match_total.inc()
            if metrics.fuzzy_match_accurate:
                self.fuzzy_match_correct.inc()
        
        # Track for SLA violations
        self._check_sla_violation(metrics)
        
        # Store recent queries for analysis
        self.recent_queries.append({
            "timestamp": time.time(),
            "duration_ms": metrics.duration_ms,
            "query_type": metrics.query_type,
            "success": metrics.success
        })
        
        # Keep only last 1000 queries
        if len(self.recent_queries) > 1000:
            self.recent_queries = self.recent_queries[-1000:]
    
    def record_user_satisfaction(self, user_id: str, score: float) -> None:
        """Record user satisfaction score (0-5)."""
        score = max(0, min(5, score))  # Clamp to 0-5
        self.user_satisfaction.labels(user_id=user_id).set(score)
        self.user_scores[user_id] = {
            "score": score,
            "timestamp": time.time()
        }
    
    def update_connection_metrics(self, connections: Dict[str, int]) -> None:
        """Update database connection metrics."""
        for database, count in connections.items():
            self.active_connections.labels(database=database).set(count)
    
    def update_memory_metrics(self, memory_usage: Dict[str, int]) -> None:
        """Update memory usage metrics."""
        for component, bytes_used in memory_usage.items():
            self.memory_usage.labels(component=component).set(bytes_used)
    
    def _extract_query_pattern(self, query_type: str) -> str:
        """Extract query pattern for grouping similar queries."""
        # Track patterns for analysis
        if query_type not in self.query_patterns:
            self.query_patterns[query_type] = []
        
        # Simple pattern extraction (can be enhanced)
        patterns = {
            "search": "search_pattern",
            "exact": "exact_match",
            "fuzzy": "fuzzy_match",
            "graph": "graph_traversal",
            "batch": "batch_query"
        }
        
        return patterns.get(query_type, "other")
    
    def _check_sla_violation(self, metrics: QueryMetrics) -> None:
        """Check if query violates SLA."""
        if metrics.duration_ms > self.p95_threshold_ms:
            self.sla_violations.inc()
            logger.warning(
                f"SLA violation: {metrics.query_type} query took {metrics.duration_ms}ms"
            )
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of current metrics."""
        # Calculate P95 from recent queries
        if self.recent_queries:
            durations = sorted([q["duration_ms"] for q in self.recent_queries])
            p95_index = int(len(durations) * 0.95)
            p95_latency = durations[p95_index]
            
            success_count = sum(1 for q in self.recent_queries if q["success"])
            success_rate = success_count / len(self.recent_queries) * 100
        else:
            p95_latency = 0
            success_rate = 0
        
        # Calculate average user satisfaction
        if self.user_scores:
            avg_satisfaction = sum(
                s["score"] for s in self.user_scores.values()
            ) / len(self.user_scores)
        else:
            avg_satisfaction = 0
        
        return {
            "total_queries": len(self.recent_queries),
            "p95_latency_ms": p95_latency,
            "success_rate": success_rate,
            "avg_satisfaction": avg_satisfaction,
            "active_users": len(self.user_scores),
            "query_patterns": list(self.query_patterns.keys()),
            "meets_sla": p95_latency <= self.p95_threshold_ms
        }
    
    def export_prometheus_metrics(self) -> bytes:
        """Export metrics in Prometheus format."""
        return generate_latest(self.registry)
    
    def get_slow_queries(self, threshold_ms: float = 200) -> List[Dict[str, Any]]:
        """Get list of slow queries."""
        slow_queries = [
            q for q in self.recent_queries
            if q["duration_ms"] > threshold_ms
        ]
        
        # Sort by duration descending
        slow_queries.sort(key=lambda x: x["duration_ms"], reverse=True)
        
        return slow_queries[:20]  # Return top 20 slowest
    
    def get_failure_analysis(self) -> Dict[str, Any]:
        """Analyze query failures."""
        failures = [q for q in self.recent_queries if not q["success"]]
        
        if not failures:
            return {"failure_rate": 0, "patterns": []}
        
        # Group failures by type
        failure_types = {}
        for failure in failures:
            query_type = failure["query_type"]
            failure_types[query_type] = failure_types.get(query_type, 0) + 1
        
        # Calculate failure rate
        failure_rate = len(failures) / len(self.recent_queries) * 100
        
        return {
            "failure_rate": failure_rate,
            "total_failures": len(failures),
            "failure_types": failure_types,
            "recent_failures": failures[-10:]  # Last 10 failures
        }
    
    async def start_metrics_server(self, port: int = 9090) -> None:
        """Start Prometheus metrics server."""
        from aiohttp import web
        
        async def metrics_handler(request):
            """Handle metrics endpoint requests."""
            metrics = self.export_prometheus_metrics()
            return web.Response(text=metrics.decode('utf-8'))
        
        app = web.Application()
        app.router.add_get('/metrics', metrics_handler)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', port)
        await site.start()
        
        logger.info(f"Metrics server started on port {port}")


class QueryAnalytics:
    """Analytics engine for query patterns and optimization."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        """Initialize analytics engine."""
        self.metrics = metrics_collector
        self.pattern_cache = {}
        self.optimization_suggestions = []
    
    def analyze_query_patterns(self) -> Dict[str, Any]:
        """Analyze query patterns for optimization opportunities."""
        analysis = {
            "patterns": [],
            "optimizations": [],
            "trends": {}
        }
        
        # Analyze recent queries
        if not self.metrics.recent_queries:
            return analysis
        
        # Group by query type
        by_type = {}
        for query in self.metrics.recent_queries:
            query_type = query["query_type"]
            if query_type not in by_type:
                by_type[query_type] = []
            by_type[query_type].append(query)
        
        # Analyze each type
        for query_type, queries in by_type.items():
            durations = [q["duration_ms"] for q in queries]
            avg_duration = sum(durations) / len(durations)
            
            pattern = {
                "type": query_type,
                "count": len(queries),
                "avg_duration_ms": avg_duration,
                "min_duration_ms": min(durations),
                "max_duration_ms": max(durations)
            }
            
            analysis["patterns"].append(pattern)
            
            # Suggest optimizations
            if avg_duration > 150:
                analysis["optimizations"].append({
                    "query_type": query_type,
                    "issue": "High average latency",
                    "suggestion": "Consider adding caching or query optimization"
                })
        
        return analysis
    
    def calculate_user_engagement(self) -> Dict[str, Any]:
        """Calculate user engagement metrics."""
        # Group queries by time windows
        now = time.time()
        hour_ago = now - 3600
        day_ago = now - 86400
        
        recent_hour = [
            q for q in self.metrics.recent_queries
            if q["timestamp"] > hour_ago
        ]
        
        recent_day = [
            q for q in self.metrics.recent_queries
            if q["timestamp"] > day_ago
        ]
        
        return {
            "queries_last_hour": len(recent_hour),
            "queries_last_day": len(recent_day),
            "active_users": len(self.metrics.user_scores),
            "avg_queries_per_user": (
                len(recent_day) / len(self.metrics.user_scores)
                if self.metrics.user_scores else 0
            )
        }
    
    def generate_optimization_report(self) -> Dict[str, Any]:
        """Generate comprehensive optimization report."""
        return {
            "summary": self.metrics.get_metrics_summary(),
            "patterns": self.analyze_query_patterns(),
            "slow_queries": self.metrics.get_slow_queries(),
            "failures": self.metrics.get_failure_analysis(),
            "engagement": self.calculate_user_engagement(),
            "recommendations": self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate optimization recommendations."""
        recommendations = []
        summary = self.metrics.get_metrics_summary()
        
        # Check P95 latency
        if summary["p95_latency_ms"] > 200:
            recommendations.append(
                f"P95 latency ({summary['p95_latency_ms']}ms) exceeds 200ms target. "
                "Consider query optimization or caching."
            )
        
        # Check success rate
        if summary["success_rate"] < 95:
            recommendations.append(
                f"Success rate ({summary['success_rate']:.1f}%) is below 95%. "
                "Investigate failure patterns."
            )
        
        # Check user satisfaction
        if summary["avg_satisfaction"] < 4.0 and summary["avg_satisfaction"] > 0:
            recommendations.append(
                f"User satisfaction ({summary['avg_satisfaction']:.1f}) is below 4.0. "
                "Review user feedback and query relevance."
            )
        
        return recommendations


# Export main classes
__all__ = ["MetricsCollector", "QueryMetrics", "QueryAnalytics"]