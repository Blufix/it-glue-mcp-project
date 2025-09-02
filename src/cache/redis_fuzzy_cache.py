"""Redis caching layer specifically optimized for fuzzy matching operations."""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import asdict, dataclass
from typing import Any, Optional

import redis.asyncio as redis
from redis.asyncio import ConnectionPool

logger = logging.getLogger(__name__)


@dataclass
class FuzzyCacheMetrics:
    """Metrics for fuzzy match caching performance."""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    avg_hit_latency_ms: float = 0.0
    avg_miss_latency_ms: float = 0.0
    total_bytes_cached: int = 0
    evictions: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests

    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate."""
        if self.total_requests == 0:
            return 0.0
        return self.cache_misses / self.total_requests


class RedisFuzzyCache:
    """
    Redis cache optimized for fuzzy matching operations.

    Features:
    - Automatic key generation for fuzzy match inputs
    - TTL-based expiration (default 3600 seconds)
    - Performance metrics tracking
    - Batch operations for multiple matches
    - Memory-efficient storage with compression
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        ttl: int = 3600,
        max_pool_size: int = 50,
        key_prefix: str = "fuzzy",
        enable_compression: bool = True
    ):
        """
        Initialize Redis fuzzy cache.

        Args:
            redis_url: Redis connection URL
            ttl: Default TTL in seconds (3600 = 1 hour)
            max_pool_size: Maximum connection pool size
            key_prefix: Prefix for all cache keys
            enable_compression: Enable value compression
        """
        self.redis_url = redis_url
        self.ttl = ttl
        self.key_prefix = key_prefix
        self.enable_compression = enable_compression

        # Connection pool for better performance
        self.pool = ConnectionPool.from_url(
            redis_url,
            max_connections=max_pool_size,
            decode_responses=False  # Handle bytes for compression
        )
        self.redis: Optional[redis.Redis] = None

        # Performance metrics
        self.metrics = FuzzyCacheMetrics()
        self._lock = asyncio.Lock()

        # Warm-up cache for common terms
        self.warm_cache_keys = set()

    async def connect(self):
        """Establish Redis connection."""
        if not self.redis:
            self.redis = redis.Redis(connection_pool=self.pool)
            await self.redis.ping()
            logger.info(f"Connected to Redis at {self.redis_url}")

    async def disconnect(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            await self.pool.disconnect()
            self.redis = None
            logger.info("Disconnected from Redis")

    def _generate_cache_key(
        self,
        input_text: str,
        candidates_hash: str,
        threshold: float = 0.7,
        match_type: str = "organization"
    ) -> str:
        """
        Generate cache key for fuzzy match operation.

        Format: fuzzy:{match_type}:{input_hash}:{candidates_hash}:{threshold}
        """
        # Normalize input for consistent hashing
        normalized_input = input_text.lower().strip()
        input_hash = hashlib.md5(normalized_input.encode()).hexdigest()[:8]

        # Candidates hash should be pre-computed
        candidates_short = candidates_hash[:8] if candidates_hash else "default"

        # Include threshold in key (rounded to 1 decimal)
        threshold_str = f"{threshold:.1f}"

        return f"{self.key_prefix}:{match_type}:{input_hash}:{candidates_short}:{threshold_str}"

    def _compress_value(self, value: Any) -> bytes:
        """Compress value for storage."""
        json_str = json.dumps(value)

        if self.enable_compression and len(json_str) > 100:
            import zlib
            compressed = zlib.compress(json_str.encode(), level=1)  # Fast compression
            # Add marker for compressed data
            return b"Z1:" + compressed
        else:
            return json_str.encode()

    def _decompress_value(self, data: bytes) -> Any:
        """Decompress value from storage."""
        if data.startswith(b"Z1:"):
            import zlib
            decompressed = zlib.decompress(data[3:])
            return json.loads(decompressed)
        else:
            return json.loads(data)

    async def get_fuzzy_match(
        self,
        input_text: str,
        candidates_hash: str,
        threshold: float = 0.7,
        match_type: str = "organization"
    ) -> Optional[list]:
        """
        Get cached fuzzy match results.

        Args:
            input_text: Input text to match
            candidates_hash: Hash of candidate list
            threshold: Match threshold
            match_type: Type of match (organization, configuration, etc.)

        Returns:
            Cached match results or None if not found
        """
        if not self.redis:
            await self.connect()

        key = self._generate_cache_key(input_text, candidates_hash, threshold, match_type)

        async with self._lock:
            self.metrics.total_requests += 1

        start_time = time.perf_counter()

        try:
            # Get from cache
            cached_data = await self.redis.get(key)

            if cached_data:
                # Cache hit
                results = self._decompress_value(cached_data)

                latency_ms = (time.perf_counter() - start_time) * 1000
                async with self._lock:
                    self.metrics.cache_hits += 1
                    # Update rolling average
                    if self.metrics.avg_hit_latency_ms == 0:
                        self.metrics.avg_hit_latency_ms = latency_ms
                    else:
                        self.metrics.avg_hit_latency_ms = (
                            self.metrics.avg_hit_latency_ms * 0.9 + latency_ms * 0.1
                        )

                logger.debug(f"Cache hit for key {key} ({latency_ms:.2f}ms)")
                return results
            else:
                # Cache miss
                latency_ms = (time.perf_counter() - start_time) * 1000
                async with self._lock:
                    self.metrics.cache_misses += 1
                    if self.metrics.avg_miss_latency_ms == 0:
                        self.metrics.avg_miss_latency_ms = latency_ms
                    else:
                        self.metrics.avg_miss_latency_ms = (
                            self.metrics.avg_miss_latency_ms * 0.9 + latency_ms * 0.1
                        )

                logger.debug(f"Cache miss for key {key}")
                return None

        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    async def set_fuzzy_match(
        self,
        input_text: str,
        candidates_hash: str,
        results: list,
        threshold: float = 0.7,
        match_type: str = "organization",
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache fuzzy match results.

        Args:
            input_text: Input text that was matched
            candidates_hash: Hash of candidate list
            results: Match results to cache
            threshold: Match threshold used
            match_type: Type of match
            ttl: Optional custom TTL (defaults to instance TTL)

        Returns:
            True if cached successfully
        """
        if not self.redis:
            await self.connect()

        key = self._generate_cache_key(input_text, candidates_hash, threshold, match_type)
        ttl = ttl or self.ttl

        try:
            # Compress and store
            compressed_data = self._compress_value(results)

            # Set with TTL
            await self.redis.setex(key, ttl, compressed_data)

            # Update metrics
            async with self._lock:
                self.metrics.total_bytes_cached += len(compressed_data)

            # Track warm cache keys
            if match_type == "organization" and len(results) > 0:
                self.warm_cache_keys.add(key)

            logger.debug(f"Cached results for key {key} (TTL: {ttl}s, Size: {len(compressed_data)} bytes)")
            return True

        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

    async def batch_get_fuzzy_matches(
        self,
        requests: list[dict[str, Any]]
    ) -> dict[str, Optional[list]]:
        """
        Batch get multiple fuzzy match results.

        Args:
            requests: List of request dicts with keys:
                - input_text: Text to match
                - candidates_hash: Hash of candidates
                - threshold: Match threshold
                - match_type: Type of match

        Returns:
            Dictionary mapping request keys to results
        """
        if not self.redis:
            await self.connect()

        # Build keys
        keys = []
        key_to_request = {}

        for req in requests:
            key = self._generate_cache_key(
                req['input_text'],
                req['candidates_hash'],
                req.get('threshold', 0.7),
                req.get('match_type', 'organization')
            )
            keys.append(key)
            key_to_request[key] = req

        # Batch get from Redis
        try:
            values = await self.redis.mget(keys)

            results = {}
            for key, value in zip(keys, values, strict=False):
                req = key_to_request[key]
                req_key = f"{req['input_text']}:{req['candidates_hash']}"

                if value:
                    results[req_key] = self._decompress_value(value)
                    async with self._lock:
                        self.metrics.cache_hits += 1
                else:
                    results[req_key] = None
                    async with self._lock:
                        self.metrics.cache_misses += 1

            async with self._lock:
                self.metrics.total_requests += len(requests)

            return results

        except Exception as e:
            logger.error(f"Redis batch get error: {e}")
            return {f"{req['input_text']}:{req['candidates_hash']}": None for req in requests}

    async def warm_up_cache(
        self,
        common_terms: list[str],
        organizations: list[dict[str, str]]
    ):
        """
        Pre-populate cache with common terms.

        Args:
            common_terms: List of commonly searched terms
            organizations: List of organization candidates
        """
        if not self.redis:
            await self.connect()

        logger.info(f"Warming up cache with {len(common_terms)} common terms")

        # Import fuzzy matcher to generate results
        from src.query.fuzzy_matcher import FuzzyMatcher
        matcher = FuzzyMatcher()

        # Generate candidates hash
        org_ids = sorted([org['id'] for org in organizations])
        candidates_hash = hashlib.md5(str(org_ids).encode()).hexdigest()

        # Warm up cache for common terms
        warmed = 0
        for term in common_terms:
            # Check if already cached
            key = self._generate_cache_key(term, candidates_hash, 0.7, "organization")

            if not await self.redis.exists(key):
                # Generate and cache results
                results = matcher.match_organization(term, organizations, 0.7)

                # Convert to cacheable format
                cache_results = [
                    {
                        'original': r.original,
                        'matched': r.matched,
                        'score': r.score,
                        'match_type': r.match_type,
                        'confidence': r.confidence,
                        'entity_id': r.entity_id
                    }
                    for r in results
                ]

                await self.set_fuzzy_match(
                    term,
                    candidates_hash,
                    cache_results,
                    ttl=7200  # 2 hours for warm cache
                )
                warmed += 1

        logger.info(f"Warmed up {warmed} cache entries")

    async def clear_cache(self, pattern: Optional[str] = None):
        """
        Clear cache entries.

        Args:
            pattern: Optional pattern to match keys (e.g., "fuzzy:organization:*")
        """
        if not self.redis:
            await self.connect()

        try:
            if pattern:
                # Clear specific pattern
                full_pattern = f"{self.key_prefix}:{pattern}" if pattern else f"{self.key_prefix}:*"

                # Use SCAN to find keys (safer than KEYS for production)
                cursor = 0
                deleted = 0

                while True:
                    cursor, keys = await self.redis.scan(
                        cursor,
                        match=full_pattern,
                        count=100
                    )

                    if keys:
                        deleted += await self.redis.delete(*keys)

                    if cursor == 0:
                        break

                logger.info(f"Cleared {deleted} cache entries matching {full_pattern}")
            else:
                # Clear all fuzzy cache
                await self.redis.flushdb()
                logger.info("Cleared entire cache")

            # Reset metrics
            self.metrics = FuzzyCacheMetrics()
            self.warm_cache_keys.clear()

        except Exception as e:
            logger.error(f"Cache clear error: {e}")

    async def get_metrics(self) -> dict[str, Any]:
        """
        Get cache performance metrics.

        Returns:
            Dictionary of metrics
        """
        metrics = asdict(self.metrics)
        metrics['hit_rate'] = self.metrics.hit_rate
        metrics['miss_rate'] = self.metrics.miss_rate
        metrics['warm_cache_size'] = len(self.warm_cache_keys)

        # Get Redis info
        if self.redis:
            try:
                info = await self.redis.info("memory")
                metrics['redis_memory_used'] = info.get('used_memory_human', 'N/A')
                metrics['redis_memory_peak'] = info.get('used_memory_peak_human', 'N/A')
            except:
                pass

        return metrics

    async def monitor_performance(self, interval: int = 60):
        """
        Monitor cache performance and log metrics.

        Args:
            interval: Logging interval in seconds
        """
        while True:
            await asyncio.sleep(interval)

            metrics = await self.get_metrics()

            logger.info(
                f"Fuzzy Cache Metrics - "
                f"Hit Rate: {metrics['hit_rate']:.2%}, "
                f"Hits: {metrics['cache_hits']}, "
                f"Misses: {metrics['cache_misses']}, "
                f"Avg Hit Latency: {metrics['avg_hit_latency_ms']:.2f}ms, "
                f"Avg Miss Latency: {metrics['avg_miss_latency_ms']:.2f}ms"
            )

            # Check if cache is performing poorly
            if metrics['hit_rate'] < 0.5 and metrics['total_requests'] > 100:
                logger.warning(
                    f"Low cache hit rate ({metrics['hit_rate']:.2%}). "
                    "Consider warming cache with more common terms."
                )


# Integration with existing FuzzyMatcher
def integrate_redis_cache(fuzzy_matcher, redis_url: str = "redis://localhost:6379"):
    """
    Integrate Redis cache with existing FuzzyMatcher.

    Args:
        fuzzy_matcher: Existing FuzzyMatcher instance
        redis_url: Redis connection URL

    Returns:
        RedisFuzzyCache instance
    """
    cache = RedisFuzzyCache(redis_url=redis_url)

    # Replace cache_manager in fuzzy_matcher
    fuzzy_matcher.cache_manager = cache

    logger.info("Redis cache integrated with FuzzyMatcher")
    return cache
