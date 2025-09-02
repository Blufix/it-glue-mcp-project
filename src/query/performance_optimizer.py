"""Query performance optimization module for achieving <200ms P95 latency."""

import asyncio
import hashlib
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Optional

from src.cache.manager import CacheManager

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Track query performance metrics."""
    query_count: int = 0
    total_time_ms: float = 0
    p95_latency_ms: float = 0
    p99_latency_ms: float = 0
    cache_hit_rate: float = 0
    slow_queries: list[dict[str, Any]] = None

    def __post_init__(self):
        if self.slow_queries is None:
            self.slow_queries = []


class QueryPerformanceOptimizer:
    """Optimize query performance to achieve <200ms P95 latency."""

    def __init__(self, cache_manager: CacheManager):
        """Initialize performance optimizer."""
        self.cache_manager = cache_manager
        self.metrics = PerformanceMetrics()
        self.query_times = []
        self.slow_query_threshold_ms = 200
        self.executor = ThreadPoolExecutor(max_workers=10)

        # Connection pooling settings
        self.connection_pools = {
            "neo4j": {"min": 5, "max": 20},
            "postgresql": {"min": 10, "max": 50},
            "qdrant": {"min": 3, "max": 15},
            "redis": {"min": 5, "max": 25}
        }

        # Query optimization strategies
        self.optimization_strategies = {
            "cache_first": self._cache_first_strategy,
            "parallel_fetch": self._parallel_fetch_strategy,
            "batch_processing": self._batch_processing_strategy,
            "index_hints": self._index_hints_strategy
        }

    async def optimize_query(
        self,
        query: str,
        query_type: str,
        context: dict[str, Any]
    ) -> tuple[Any, float]:
        """
        Optimize and execute query with performance tracking.

        Args:
            query: The query to optimize
            query_type: Type of query (search, graph, exact, etc.)
            context: Query context including organization, filters, etc.

        Returns:
            Tuple of (results, execution_time_ms)
        """
        start_time = time.perf_counter()

        try:
            # Step 1: Check cache first
            cache_key = self._generate_cache_key(query, query_type, context)
            cached_result = await self._check_cache(cache_key)

            if cached_result:
                execution_time = (time.perf_counter() - start_time) * 1000
                self._record_metrics(execution_time, cache_hit=True)
                return cached_result, execution_time

            # Step 2: Apply optimization strategy based on query type
            strategy = self._select_optimization_strategy(query_type)
            optimized_query = await strategy(query, context)

            # Step 3: Execute optimized query with parallel processing
            results = await self._execute_optimized_query(
                optimized_query,
                query_type,
                context
            )

            # Step 4: Cache results with intelligent TTL
            ttl = self._calculate_ttl(query_type)
            await self._cache_results(cache_key, results, ttl)

            execution_time = (time.perf_counter() - start_time) * 1000
            self._record_metrics(execution_time, cache_hit=False)

            # Log slow queries for analysis
            if execution_time > self.slow_query_threshold_ms:
                self._log_slow_query(query, query_type, execution_time, context)

            return results, execution_time

        except Exception as e:
            logger.error(f"Query optimization failed: {e}")
            execution_time = (time.perf_counter() - start_time) * 1000
            self._record_metrics(execution_time, cache_hit=False, error=True)
            raise

    def _generate_cache_key(
        self,
        query: str,
        query_type: str,
        context: dict[str, Any]
    ) -> str:
        """Generate cache key for query."""
        key_data = {
            "query": query.lower().strip(),
            "type": query_type,
            "org": context.get("organization_id"),
            "filters": context.get("filters", {})
        }

        key_str = json.dumps(key_data, sort_keys=True)
        return f"query:{hashlib.md5(key_str.encode()).hexdigest()}"

    async def _check_cache(self, cache_key: str) -> Optional[Any]:
        """Check cache for query results."""
        try:
            cached = await self.cache_manager.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.debug(f"Cache check failed: {e}")
        return None

    async def _cache_results(
        self,
        cache_key: str,
        results: Any,
        ttl: int
    ) -> None:
        """Cache query results."""
        try:
            await self.cache_manager.set(
                cache_key,
                json.dumps(results),
                ttl=ttl
            )
        except Exception as e:
            logger.debug(f"Cache write failed: {e}")

    def _calculate_ttl(self, query_type: str) -> int:
        """Calculate cache TTL based on query type."""
        ttl_map = {
            "critical": 60,        # 1 minute for critical queries
            "investigation": 300,  # 5 minutes for investigation
            "documentation": 86400, # 24 hours for documentation
            "report": 3600,        # 1 hour for reports
            "search": 1800,        # 30 minutes for searches
            "graph": 600           # 10 minutes for graph queries
        }
        return ttl_map.get(query_type, 300)

    def _select_optimization_strategy(self, query_type: str):
        """Select optimization strategy based on query type."""
        strategy_map = {
            "search": "parallel_fetch",
            "graph": "index_hints",
            "batch": "batch_processing",
            "simple": "cache_first"
        }

        strategy_name = strategy_map.get(query_type, "cache_first")
        return self.optimization_strategies[strategy_name]

    async def _cache_first_strategy(
        self,
        query: str,
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """Cache-first optimization strategy."""
        return {
            "query": query,
            "strategy": "cache_first",
            "context": context,
            "optimizations": ["cache_check", "simple_query"]
        }

    async def _parallel_fetch_strategy(
        self,
        query: str,
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """Parallel fetch optimization strategy."""
        return {
            "query": query,
            "strategy": "parallel_fetch",
            "context": context,
            "optimizations": [
                "parallel_db_queries",
                "async_aggregation",
                "connection_pooling"
            ]
        }

    async def _batch_processing_strategy(
        self,
        query: str,
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """Batch processing optimization strategy."""
        return {
            "query": query,
            "strategy": "batch_processing",
            "context": context,
            "optimizations": [
                "batch_queries",
                "bulk_fetch",
                "result_streaming"
            ]
        }

    async def _index_hints_strategy(
        self,
        query: str,
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """Index hints optimization strategy for graph queries."""
        return {
            "query": query,
            "strategy": "index_hints",
            "context": context,
            "optimizations": [
                "use_indexes",
                "limit_traversal_depth",
                "early_termination"
            ]
        }

    async def _execute_optimized_query(
        self,
        optimized_query: dict[str, Any],
        query_type: str,
        context: dict[str, Any]
    ) -> Any:
        """Execute optimized query with parallel processing."""
        strategy = optimized_query.get("strategy", "cache_first")

        if strategy == "parallel_fetch":
            return await self._execute_parallel_queries(optimized_query, context)
        elif strategy == "batch_processing":
            return await self._execute_batch_queries(optimized_query, context)
        elif strategy == "index_hints":
            return await self._execute_indexed_query(optimized_query, context)
        else:
            return await self._execute_simple_query(optimized_query, context)

    async def _execute_parallel_queries(
        self,
        query: dict[str, Any],
        context: dict[str, Any]
    ) -> Any:
        """Execute multiple queries in parallel."""
        tasks = []

        # Example: Parallel fetch from multiple sources
        if context.get("sources"):
            for source in context["sources"]:
                task = asyncio.create_task(
                    self._fetch_from_source(query["query"], source)
                )
                tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and combine results
        valid_results = [r for r in results if not isinstance(r, Exception)]
        return self._merge_results(valid_results)

    async def _execute_batch_queries(
        self,
        query: dict[str, Any],
        context: dict[str, Any]
    ) -> Any:
        """Execute batch queries efficiently."""
        batch_size = context.get("batch_size", 100)
        results = []

        # Process in batches to avoid memory issues
        for i in range(0, len(context.get("items", [])), batch_size):
            batch = context["items"][i:i + batch_size]
            batch_result = await self._process_batch(query["query"], batch)
            results.extend(batch_result)

        return results

    async def _execute_indexed_query(
        self,
        query: dict[str, Any],
        context: dict[str, Any]
    ) -> Any:
        """Execute query with index hints."""
        # Add index hints to query
        indexed_query = self._add_index_hints(query["query"], context)

        # Limit traversal depth for graph queries
        if context.get("max_depth"):
            indexed_query = self._limit_traversal_depth(
                indexed_query,
                context["max_depth"]
            )

        return await self._execute_simple_query({"query": indexed_query}, context)

    async def _execute_simple_query(
        self,
        query: dict[str, Any],
        context: dict[str, Any]
    ) -> Any:
        """Execute simple query."""
        # Placeholder for actual query execution
        # This would interface with the actual database/search backends
        return {
            "query": query["query"],
            "results": [],
            "count": 0,
            "execution_time_ms": 0
        }

    async def _fetch_from_source(self, query: str, source: str) -> Any:
        """Fetch data from a specific source."""
        # Placeholder for source-specific fetching
        return {"source": source, "data": []}

    def _merge_results(self, results: list[Any]) -> Any:
        """Merge results from parallel queries."""
        merged = {
            "results": [],
            "sources": [],
            "total_count": 0
        }

        for result in results:
            if isinstance(result, dict):
                merged["results"].extend(result.get("data", []))
                merged["sources"].append(result.get("source"))
                merged["total_count"] += len(result.get("data", []))

        return merged

    async def _process_batch(self, query: str, batch: list[Any]) -> list[Any]:
        """Process a batch of items."""
        # Placeholder for batch processing
        return []

    def _add_index_hints(self, query: str, context: dict[str, Any]) -> str:
        """Add index hints to query."""
        # Add database-specific index hints
        if "neo4j" in context.get("backend", ""):
            query = f"USING INDEX {context.get('index_name', 'default')} {query}"
        elif "postgresql" in context.get("backend", ""):
            query = f"{query} /*+ INDEX({context.get('index_name', 'default')}) */"

        return query

    def _limit_traversal_depth(self, query: str, max_depth: int) -> str:
        """Limit graph traversal depth."""
        # Add depth limit to graph queries
        if "MATCH" in query:  # Neo4j
            query = query.replace("*", f"*1..{max_depth}")

        return query

    def _record_metrics(
        self,
        execution_time: float,
        cache_hit: bool = False,
        error: bool = False
    ) -> None:
        """Record performance metrics."""
        self.metrics.query_count += 1
        self.metrics.total_time_ms += execution_time

        # Track query times for percentile calculation
        self.query_times.append(execution_time)

        # Keep only last 1000 queries for percentile calculation
        if len(self.query_times) > 1000:
            self.query_times = self.query_times[-1000:]

        # Calculate percentiles
        if self.query_times:
            sorted_times = sorted(self.query_times)
            p95_index = int(len(sorted_times) * 0.95)
            p99_index = int(len(sorted_times) * 0.99)

            self.metrics.p95_latency_ms = sorted_times[p95_index]
            self.metrics.p99_latency_ms = sorted_times[p99_index]

        # Update cache hit rate
        if cache_hit:
            # Simple exponential moving average
            alpha = 0.1
            self.metrics.cache_hit_rate = (
                alpha * 1.0 + (1 - alpha) * self.metrics.cache_hit_rate
            )

    def _log_slow_query(
        self,
        query: str,
        query_type: str,
        execution_time: float,
        context: dict[str, Any]
    ) -> None:
        """Log slow queries for analysis."""
        slow_query = {
            "query": query[:200],  # Truncate long queries
            "type": query_type,
            "execution_time_ms": execution_time,
            "timestamp": time.time(),
            "context": {
                "organization": context.get("organization_id"),
                "filters": context.get("filters")
            }
        }

        self.metrics.slow_queries.append(slow_query)

        # Keep only last 100 slow queries
        if len(self.metrics.slow_queries) > 100:
            self.metrics.slow_queries = self.metrics.slow_queries[-100:]

        logger.warning(f"Slow query detected: {execution_time:.2f}ms - {query_type}")

    def get_performance_metrics(self) -> dict[str, Any]:
        """Get current performance metrics."""
        return {
            "query_count": self.metrics.query_count,
            "avg_latency_ms": (
                self.metrics.total_time_ms / self.metrics.query_count
                if self.metrics.query_count > 0 else 0
            ),
            "p95_latency_ms": self.metrics.p95_latency_ms,
            "p99_latency_ms": self.metrics.p99_latency_ms,
            "cache_hit_rate": self.metrics.cache_hit_rate,
            "slow_queries_count": len(self.metrics.slow_queries),
            "meets_sla": self.metrics.p95_latency_ms < 200
        }

    async def warm_cache(self, common_queries: list[dict[str, Any]]) -> None:
        """Warm cache with common queries."""
        logger.info(f"Warming cache with {len(common_queries)} common queries")

        tasks = []
        for query_data in common_queries:
            task = asyncio.create_task(
                self.optimize_query(
                    query_data["query"],
                    query_data.get("type", "search"),
                    query_data.get("context", {})
                )
            )
            tasks.append(task)

        # Execute cache warming in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(1 for r in results if not isinstance(r, Exception))
        logger.info(f"Cache warming complete: {success_count}/{len(common_queries)} successful")

    async def analyze_performance_bottlenecks(self) -> dict[str, Any]:
        """Analyze and identify performance bottlenecks."""
        analysis = {
            "bottlenecks": [],
            "recommendations": [],
            "metrics": self.get_performance_metrics()
        }

        # Check P95 latency
        if self.metrics.p95_latency_ms > 200:
            analysis["bottlenecks"].append({
                "issue": "P95 latency exceeds 200ms target",
                "current": f"{self.metrics.p95_latency_ms:.2f}ms",
                "target": "200ms"
            })
            analysis["recommendations"].append(
                "Increase cache TTL or add more aggressive caching"
            )

        # Check cache hit rate
        if self.metrics.cache_hit_rate < 0.7:
            analysis["bottlenecks"].append({
                "issue": "Low cache hit rate",
                "current": f"{self.metrics.cache_hit_rate:.2%}",
                "target": "70%"
            })
            analysis["recommendations"].append(
                "Implement cache warming for common queries"
            )

        # Analyze slow queries
        if self.metrics.slow_queries:
            query_types = {}
            for sq in self.metrics.slow_queries:
                query_type = sq["type"]
                query_types[query_type] = query_types.get(query_type, 0) + 1

            worst_type = max(query_types, key=query_types.get)
            analysis["bottlenecks"].append({
                "issue": f"Slow queries predominantly in {worst_type}",
                "count": query_types[worst_type],
                "recommendation": f"Optimize {worst_type} query processing"
            })

        return analysis

    def shutdown(self) -> None:
        """Shutdown performance optimizer."""
        self.executor.shutdown(wait=True)
        logger.info("Performance optimizer shutdown complete")


class ConnectionPoolManager:
    """Manage database connection pools for optimal performance."""

    def __init__(self):
        """Initialize connection pool manager."""
        self.pools = {}
        self.pool_stats = {}

    async def initialize_pools(self, config: dict[str, dict[str, int]]) -> None:
        """Initialize connection pools for all databases."""
        for db_name, pool_config in config.items():
            await self._create_pool(db_name, pool_config)

    async def _create_pool(self, db_name: str, config: dict[str, int]) -> None:
        """Create connection pool for specific database."""
        # Placeholder for actual pool creation
        # This would use database-specific pooling libraries
        self.pools[db_name] = {
            "min_size": config["min"],
            "max_size": config["max"],
            "active": 0,
            "idle": config["min"]
        }

        self.pool_stats[db_name] = {
            "requests": 0,
            "hits": 0,
            "misses": 0,
            "timeouts": 0
        }

        logger.info(f"Initialized connection pool for {db_name}: {config}")

    async def get_connection(self, db_name: str):
        """Get connection from pool."""
        if db_name not in self.pools:
            raise ValueError(f"No pool configured for {db_name}")

        pool = self.pools[db_name]
        stats = self.pool_stats[db_name]

        stats["requests"] += 1

        # Placeholder for actual connection retrieval
        # This would interact with the real connection pool
        if pool["idle"] > 0:
            pool["idle"] -= 1
            pool["active"] += 1
            stats["hits"] += 1
            return f"connection_{db_name}_{stats['requests']}"
        else:
            stats["misses"] += 1
            # Would wait or create new connection up to max_size
            return None

    async def release_connection(self, db_name: str, connection: Any) -> None:
        """Release connection back to pool."""
        if db_name in self.pools:
            pool = self.pools[db_name]
            pool["active"] -= 1
            pool["idle"] += 1

    def get_pool_statistics(self) -> dict[str, Any]:
        """Get connection pool statistics."""
        stats = {}

        for db_name, pool in self.pools.items():
            pool_stats = self.pool_stats[db_name]
            stats[db_name] = {
                "configuration": {
                    "min_size": pool["min_size"],
                    "max_size": pool["max_size"]
                },
                "current_state": {
                    "active": pool["active"],
                    "idle": pool["idle"],
                    "total": pool["active"] + pool["idle"]
                },
                "statistics": {
                    "total_requests": pool_stats["requests"],
                    "cache_hits": pool_stats["hits"],
                    "cache_misses": pool_stats["misses"],
                    "hit_rate": (
                        pool_stats["hits"] / pool_stats["requests"]
                        if pool_stats["requests"] > 0 else 0
                    )
                }
            }

        return stats


# Export main class
__all__ = ["QueryPerformanceOptimizer", "ConnectionPoolManager"]
