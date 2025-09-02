"""Redis cache layer with intelligent TTL and smart invalidation."""

import asyncio
import hashlib
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Query types with associated cache strategies."""
    CRITICAL = "critical"  # Passwords, emergency data
    INVESTIGATION = "investigation"  # Audit logs, recent changes
    OPERATIONAL = "operational"  # Configurations, current state
    DOCUMENTATION = "documentation"  # Static docs, procedures
    REPORT = "report"  # Analytics, summaries
    SEARCH = "search"  # General searches


@dataclass
class CacheStrategy:
    """Cache strategy for different query types."""
    ttl_seconds: int
    warm_on_startup: bool = False
    refresh_before_expiry: bool = False
    invalidate_on_update: bool = True
    max_entries: Optional[int] = None

    @classmethod
    def for_query_type(cls, query_type: QueryType) -> 'CacheStrategy':
        """Get cache strategy for a query type."""
        strategies = {
            QueryType.CRITICAL: cls(
                ttl_seconds=60,  # 1 minute for critical data
                warm_on_startup=True,
                refresh_before_expiry=True,
                invalidate_on_update=True,
                max_entries=100
            ),
            QueryType.INVESTIGATION: cls(
                ttl_seconds=300,  # 5 minutes for investigation
                warm_on_startup=False,
                refresh_before_expiry=True,
                invalidate_on_update=True,
                max_entries=500
            ),
            QueryType.OPERATIONAL: cls(
                ttl_seconds=900,  # 15 minutes for operational
                warm_on_startup=True,
                refresh_before_expiry=False,
                invalidate_on_update=True,
                max_entries=1000
            ),
            QueryType.DOCUMENTATION: cls(
                ttl_seconds=86400,  # 24 hours for documentation
                warm_on_startup=True,
                refresh_before_expiry=False,
                invalidate_on_update=False,
                max_entries=2000
            ),
            QueryType.REPORT: cls(
                ttl_seconds=3600,  # 1 hour for reports
                warm_on_startup=False,
                refresh_before_expiry=False,
                invalidate_on_update=True,
                max_entries=100
            ),
            QueryType.SEARCH: cls(
                ttl_seconds=600,  # 10 minutes for general search
                warm_on_startup=False,
                refresh_before_expiry=False,
                invalidate_on_update=False,
                max_entries=5000
            )
        }
        return strategies.get(query_type, cls(ttl_seconds=600))


@dataclass
class CacheEntry:
    """A cache entry with metadata."""
    key: str
    value: Any
    query_type: QueryType
    created_at: datetime
    expires_at: datetime
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    tags: list[str] = field(default_factory=list)
    checksum: Optional[str] = None


class RedisCache:
    """Redis-based cache with intelligent TTL and invalidation."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        db: int = 0,
        key_prefix: str = "itglue:",
        max_connections: int = 50
    ):
        """Initialize Redis cache.

        Args:
            redis_url: Redis connection URL
            db: Redis database number
            key_prefix: Prefix for all cache keys
            max_connections: Maximum connection pool size
        """
        self.redis_url = redis_url
        self.db = db
        self.key_prefix = key_prefix
        self.max_connections = max_connections

        self.client: Optional[redis.Redis] = None
        self.connected = False

        # Cache statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'errors': 0
        }

        # Invalidation subscriptions
        self.invalidation_patterns: dict[str, list[str]] = {}

        # Background tasks
        self.background_tasks = set()

    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            self.client = redis.Redis.from_url(
                self.redis_url,
                db=self.db,
                max_connections=self.max_connections,
                decode_responses=True
            )

            # Test connection
            await self.client.ping()
            self.connected = True
            logger.info(f"Connected to Redis at {self.redis_url}")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.client:
            # Cancel background tasks
            for task in self.background_tasks:
                task.cancel()

            await self.client.close()
            self.connected = False
            logger.info("Disconnected from Redis")

    def _make_key(self, key: str, namespace: Optional[str] = None) -> str:
        """Create a namespaced cache key."""
        if namespace:
            return f"{self.key_prefix}{namespace}:{key}"
        return f"{self.key_prefix}{key}"

    def _generate_cache_key(
        self,
        query: str,
        params: Optional[dict[str, Any]] = None,
        context: Optional[dict[str, Any]] = None
    ) -> str:
        """Generate a deterministic cache key for a query."""
        key_parts = [query]

        if params:
            # Sort params for consistent key generation
            sorted_params = sorted(params.items())
            key_parts.append(str(sorted_params))

        if context:
            # Include relevant context (e.g., organization, user)
            if 'organization_id' in context:
                key_parts.append(f"org:{context['organization_id']}")
            if 'user_id' in context:
                key_parts.append(f"user:{context['user_id']}")

        key_string = "|".join(key_parts)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()

        return f"query:{key_hash}"

    async def get(
        self,
        key: str,
        namespace: Optional[str] = None
    ) -> Optional[Any]:
        """Get a value from cache.

        Args:
            key: Cache key
            namespace: Optional namespace

        Returns:
            Cached value or None if not found
        """
        if not self.connected:
            logger.warning("Redis not connected, cache miss")
            return None

        full_key = self._make_key(key, namespace)

        try:
            # Get value
            value_str = await self.client.get(full_key)

            if value_str is None:
                self.stats['misses'] += 1
                return None

            # Update access count and timestamp
            await self._update_access_metadata(full_key)

            # Deserialize value
            value = json.loads(value_str)

            self.stats['hits'] += 1
            logger.debug(f"Cache hit: {full_key}")

            return value

        except Exception as e:
            logger.error(f"Cache get error for {full_key}: {e}")
            self.stats['errors'] += 1
            return None

    async def set(
        self,
        key: str,
        value: Any,
        query_type: QueryType = QueryType.SEARCH,
        namespace: Optional[str] = None,
        ttl_override: Optional[int] = None,
        tags: Optional[list[str]] = None
    ) -> bool:
        """Set a value in cache with intelligent TTL.

        Args:
            key: Cache key
            value: Value to cache
            query_type: Type of query for TTL strategy
            namespace: Optional namespace
            ttl_override: Override default TTL (seconds)
            tags: Tags for invalidation grouping

        Returns:
            True if successful
        """
        if not self.connected:
            logger.warning("Redis not connected, cache set skipped")
            return False

        full_key = self._make_key(key, namespace)
        strategy = CacheStrategy.for_query_type(query_type)

        # Determine TTL
        ttl = ttl_override if ttl_override is not None else strategy.ttl_seconds

        try:
            # Serialize value
            value_str = json.dumps(value)

            # Set with TTL
            await self.client.setex(full_key, ttl, value_str)

            # Store metadata
            metadata = {
                'query_type': query_type.value,
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(seconds=ttl)).isoformat(),
                'tags': tags or [],
                'checksum': hashlib.md5(value_str.encode()).hexdigest()
            }

            metadata_key = f"{full_key}:meta"
            await self.client.setex(metadata_key, ttl, json.dumps(metadata))

            # Register for invalidation if needed
            if tags and strategy.invalidate_on_update:
                await self._register_invalidation_tags(full_key, tags)

            # Schedule refresh if needed
            if strategy.refresh_before_expiry:
                await self._schedule_refresh(full_key, ttl)

            self.stats['sets'] += 1
            logger.debug(f"Cache set: {full_key} (TTL: {ttl}s)")

            return True

        except Exception as e:
            logger.error(f"Cache set error for {full_key}: {e}")
            self.stats['errors'] += 1
            return False

    async def delete(
        self,
        key: str,
        namespace: Optional[str] = None
    ) -> bool:
        """Delete a value from cache.

        Args:
            key: Cache key
            namespace: Optional namespace

        Returns:
            True if deleted
        """
        if not self.connected:
            return False

        full_key = self._make_key(key, namespace)

        try:
            # Delete value and metadata
            result = await self.client.delete(full_key, f"{full_key}:meta")

            if result > 0:
                self.stats['deletes'] += 1
                logger.debug(f"Cache delete: {full_key}")
                return True

            return False

        except Exception as e:
            logger.error(f"Cache delete error for {full_key}: {e}")
            self.stats['errors'] += 1
            return False

    async def invalidate_by_tags(self, tags: list[str]) -> int:
        """Invalidate all cache entries with specified tags.

        Args:
            tags: List of tags to match

        Returns:
            Number of entries invalidated
        """
        if not self.connected:
            return 0

        invalidated = 0

        try:
            for tag in tags:
                tag_key = f"{self.key_prefix}tag:{tag}"

                # Get all keys with this tag
                keys = await self.client.smembers(tag_key)

                if keys:
                    # Delete all matching keys
                    pipeline = self.client.pipeline()
                    for key in keys:
                        pipeline.delete(key, f"{key}:meta")

                    results = await pipeline.execute()
                    invalidated += sum(1 for r in results if r > 0)

                    # Clean up tag set
                    await self.client.delete(tag_key)

            if invalidated > 0:
                logger.info(f"Invalidated {invalidated} cache entries for tags: {tags}")

            return invalidated

        except Exception as e:
            logger.error(f"Error invalidating by tags {tags}: {e}")
            return 0

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching a pattern.

        Args:
            pattern: Redis pattern (e.g., "query:org:123:*")

        Returns:
            Number of entries invalidated
        """
        if not self.connected:
            return 0

        try:
            # Find matching keys
            full_pattern = f"{self.key_prefix}{pattern}"
            cursor = 0
            keys_to_delete = []

            while True:
                cursor, keys = await self.client.scan(
                    cursor,
                    match=full_pattern,
                    count=100
                )
                keys_to_delete.extend(keys)

                if cursor == 0:
                    break

            # Delete in batches
            invalidated = 0
            if keys_to_delete:
                pipeline = self.client.pipeline()
                for key in keys_to_delete:
                    pipeline.delete(key, f"{key}:meta")

                results = await pipeline.execute()
                invalidated = sum(1 for r in results if r > 0)

            if invalidated > 0:
                logger.info(f"Invalidated {invalidated} cache entries for pattern: {pattern}")

            return invalidated

        except Exception as e:
            logger.error(f"Error invalidating pattern {pattern}: {e}")
            return 0

    async def warm_cache(
        self,
        queries: list[dict[str, Any]],
        fetch_func: Callable
    ) -> int:
        """Warm cache with common queries.

        Args:
            queries: List of queries to warm with format:
                     [{'query': str, 'params': dict, 'query_type': QueryType}, ...]
            fetch_func: Async function to fetch data if not cached

        Returns:
            Number of entries warmed
        """
        warmed = 0

        for query_info in queries:
            query = query_info['query']
            params = query_info.get('params', {})
            query_type = query_info.get('query_type', QueryType.SEARCH)

            # Generate cache key
            cache_key = self._generate_cache_key(query, params)

            # Check if already cached
            existing = await self.get(cache_key)
            if existing is not None:
                continue

            try:
                # Fetch data
                data = await fetch_func(query, params)

                if data is not None:
                    # Cache the result
                    success = await self.set(
                        cache_key,
                        data,
                        query_type=query_type
                    )

                    if success:
                        warmed += 1

            except Exception as e:
                logger.error(f"Error warming cache for query '{query}': {e}")

        if warmed > 0:
            logger.info(f"Warmed {warmed} cache entries")

        return warmed

    async def get_or_fetch(
        self,
        query: str,
        fetch_func: Callable,
        params: Optional[dict[str, Any]] = None,
        context: Optional[dict[str, Any]] = None,
        query_type: QueryType = QueryType.SEARCH,
        force_refresh: bool = False
    ) -> Optional[Any]:
        """Get from cache or fetch if not found.

        Args:
            query: Query string
            fetch_func: Async function to fetch data if not cached
            params: Query parameters
            context: Query context (org, user, etc.)
            query_type: Type of query for caching strategy
            force_refresh: Force fetching new data

        Returns:
            Cached or fetched data
        """
        # Generate cache key
        cache_key = self._generate_cache_key(query, params, context)

        # Try cache first (unless forced refresh)
        if not force_refresh:
            cached = await self.get(cache_key)
            if cached is not None:
                return cached

        # Fetch data
        try:
            data = await fetch_func(query, params)

            if data is not None:
                # Cache the result
                await self.set(
                    cache_key,
                    data,
                    query_type=query_type,
                    tags=self._extract_tags(query, params, context)
                )

            return data

        except Exception as e:
            logger.error(f"Error fetching data for query '{query}': {e}")

            # Try stale cache on error
            if not force_refresh:
                stale = await self.get(cache_key)
                if stale is not None:
                    logger.warning("Returning stale cache due to fetch error")
                    return stale

            return None

    async def _update_access_metadata(self, key: str) -> None:
        """Update access count and timestamp for a cache entry."""
        try:
            # Increment access count
            access_key = f"{key}:access"
            await self.client.incr(access_key)

            # Update last accessed time
            await self.client.set(
                f"{key}:last_accessed",
                datetime.now().isoformat()
            )

        except Exception as e:
            logger.debug(f"Error updating access metadata: {e}")

    async def _register_invalidation_tags(
        self,
        key: str,
        tags: list[str]
    ) -> None:
        """Register cache key with invalidation tags."""
        try:
            pipeline = self.client.pipeline()

            for tag in tags:
                tag_key = f"{self.key_prefix}tag:{tag}"
                pipeline.sadd(tag_key, key)

            await pipeline.execute()

        except Exception as e:
            logger.error(f"Error registering invalidation tags: {e}")

    async def _schedule_refresh(self, key: str, ttl: int) -> None:
        """Schedule cache refresh before expiry."""
        # Refresh at 80% of TTL
        refresh_delay = int(ttl * 0.8)

        async def refresh_task():
            await asyncio.sleep(refresh_delay)

            # Check if key still exists
            if await self.client.exists(key):
                logger.debug(f"Triggering refresh for {key}")
                # Emit refresh event (to be handled by application)
                # This is a placeholder - actual implementation would
                # depend on the application's refresh mechanism

        task = asyncio.create_task(refresh_task())
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)

    def _extract_tags(
        self,
        query: str,
        params: Optional[dict[str, Any]],
        context: Optional[dict[str, Any]]
    ) -> list[str]:
        """Extract tags from query for invalidation grouping."""
        tags = []

        # Add organization tag
        if context and 'organization_id' in context:
            tags.append(f"org:{context['organization_id']}")

        # Add resource type tags from params
        if params:
            if 'resource_type' in params:
                tags.append(f"type:{params['resource_type']}")
            if 'resource_id' in params:
                tags.append(f"resource:{params['resource_id']}")

        # Extract entity types from query
        query_lower = query.lower()
        if 'password' in query_lower:
            tags.append('entity:password')
        if 'configuration' in query_lower:
            tags.append('entity:configuration')
        if 'organization' in query_lower:
            tags.append('entity:organization')

        return tags

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        stats = self.stats.copy()

        if self.connected:
            try:
                # Get Redis info
                info = await self.client.info('memory')
                stats['redis_memory_used'] = info.get('used_memory_human', 'N/A')
                stats['redis_memory_peak'] = info.get('used_memory_peak_human', 'N/A')

                # Get key count
                db_info = await self.client.info('keyspace')
                if f'db{self.db}' in db_info:
                    db_stats = db_info[f'db{self.db}']
                    stats['total_keys'] = db_stats.get('keys', 0)
                    stats['expires'] = db_stats.get('expires', 0)

            except Exception as e:
                logger.error(f"Error getting Redis stats: {e}")

        # Calculate hit rate
        total_requests = stats['hits'] + stats['misses']
        if total_requests > 0:
            stats['hit_rate'] = stats['hits'] / total_requests * 100
        else:
            stats['hit_rate'] = 0

        return stats

    async def clear_all(self) -> int:
        """Clear all cache entries (use with caution).

        Returns:
            Number of entries cleared
        """
        if not self.connected:
            return 0

        try:
            # Find all our keys
            pattern = f"{self.key_prefix}*"
            cursor = 0
            keys_to_delete = []

            while True:
                cursor, keys = await self.client.scan(
                    cursor,
                    match=pattern,
                    count=100
                )
                keys_to_delete.extend(keys)

                if cursor == 0:
                    break

            # Delete all keys
            if keys_to_delete:
                deleted = await self.client.delete(*keys_to_delete)
                logger.warning(f"Cleared {deleted} cache entries")
                return deleted

            return 0

        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return 0


class CacheManager:
    """High-level cache manager with multiple cache instances."""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """Initialize cache manager.

        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url

        # Create specialized cache instances
        self.query_cache = RedisCache(redis_url, db=0, key_prefix="query:")
        self.result_cache = RedisCache(redis_url, db=1, key_prefix="result:")
        self.session_cache = RedisCache(redis_url, db=2, key_prefix="session:")

        self.caches = [self.query_cache, self.result_cache, self.session_cache]

    async def connect(self) -> None:
        """Connect all cache instances."""
        for cache in self.caches:
            await cache.connect()

    async def disconnect(self) -> None:
        """Disconnect all cache instances."""
        for cache in self.caches:
            await cache.disconnect()

    async def invalidate_organization(self, org_id: str) -> int:
        """Invalidate all cache entries for an organization.

        Args:
            org_id: Organization ID

        Returns:
            Total number of entries invalidated
        """
        total = 0

        # Invalidate by tag
        tag = f"org:{org_id}"
        for cache in self.caches:
            total += await cache.invalidate_by_tags([tag])

        # Invalidate by pattern
        pattern = f"*org:{org_id}:*"
        for cache in self.caches:
            total += await cache.invalidate_pattern(pattern)

        logger.info(f"Invalidated {total} cache entries for organization {org_id}")
        return total

    async def invalidate_resource(
        self,
        resource_type: str,
        resource_id: str
    ) -> int:
        """Invalidate cache entries for a specific resource.

        Args:
            resource_type: Type of resource
            resource_id: Resource ID

        Returns:
            Number of entries invalidated
        """
        tags = [
            f"type:{resource_type}",
            f"resource:{resource_id}"
        ]

        total = 0
        for cache in self.caches:
            total += await cache.invalidate_by_tags(tags)

        logger.info(f"Invalidated {total} cache entries for {resource_type}:{resource_id}")
        return total

    async def get_combined_stats(self) -> dict[str, Any]:
        """Get combined statistics from all caches."""
        combined = {
            'query_cache': await self.query_cache.get_stats(),
            'result_cache': await self.result_cache.get_stats(),
            'session_cache': await self.session_cache.get_stats()
        }

        # Calculate totals
        totals = {
            'total_hits': sum(c['hits'] for c in combined.values()),
            'total_misses': sum(c['misses'] for c in combined.values()),
            'total_sets': sum(c['sets'] for c in combined.values()),
            'total_deletes': sum(c['deletes'] for c in combined.values()),
            'total_errors': sum(c['errors'] for c in combined.values())
        }

        total_requests = totals['total_hits'] + totals['total_misses']
        if total_requests > 0:
            totals['overall_hit_rate'] = totals['total_hits'] / total_requests * 100
        else:
            totals['overall_hit_rate'] = 0

        combined['totals'] = totals
        return combined


# Export main classes
__all__ = ['RedisCache', 'CacheManager', 'QueryType', 'CacheStrategy', 'CacheEntry']
