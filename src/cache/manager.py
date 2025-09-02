"""Redis cache management for query results."""

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Optional

import redis.asyncio as redis

from src.config.settings import settings

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages Redis cache for query results."""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        default_ttl: int = 300,
        max_cache_size: int = 10000
    ):
        """Initialize cache manager.

        Args:
            redis_url: Redis connection URL
            default_ttl: Default TTL in seconds
            max_cache_size: Maximum number of cache entries
        """
        self.redis_url = redis_url or settings.redis_url or "redis://localhost:6379"
        self.default_ttl = default_ttl
        self.max_cache_size = max_cache_size
        self.redis: Optional[redis.Redis] = None

    async def connect(self):
        """Connect to Redis."""
        if not self.redis:
            try:
                self.redis = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )

                # Test connection
                await self.redis.ping()
                logger.info("Connected to Redis cache")

            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self.redis = None
                raise

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.aclose()
            self.redis = None
            logger.info("Disconnected from Redis cache")

    def _generate_cache_key(
        self,
        query: str,
        company: Optional[str] = None
    ) -> str:
        """Generate cache key from query and company.

        Args:
            query: Query string
            company: Company filter

        Returns:
            Cache key
        """
        key_string = f"query:{query}:company:{company or ''}"
        return hashlib.md5(key_string.encode()).hexdigest()

    async def get(
        self,
        query: str,
        company: Optional[str] = None
    ) -> Optional[dict[str, Any]]:
        """Get cached query result.

        Args:
            query: Query string
            company: Company filter

        Returns:
            Cached response or None
        """
        if not self.redis:
            await self.connect()

        if not self.redis:
            return None

        try:
            cache_key = self._generate_cache_key(query, company)

            # Get from Redis
            cached_data = await self.redis.get(f"cache:{cache_key}")

            if cached_data:
                # Update hit counter
                await self.redis.incr(f"hits:{cache_key}")

                # Parse JSON
                response = json.loads(cached_data)

                # Add cache metadata
                response["from_cache"] = True
                response["cache_key"] = cache_key

                logger.debug(f"Cache hit for key: {cache_key}")
                return response

            logger.debug(f"Cache miss for key: {cache_key}")
            return None

        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(
        self,
        query: str,
        response: dict[str, Any],
        company: Optional[str] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """Cache query result.

        Args:
            query: Query string
            response: Response to cache
            company: Company filter
            ttl: TTL in seconds

        Returns:
            Success status
        """
        if not self.redis:
            await self.connect()

        if not self.redis:
            return False

        try:
            cache_key = self._generate_cache_key(query, company)
            ttl = ttl or self.default_ttl

            # Prepare cache data
            cache_data = {
                **response,
                "cached_at": datetime.utcnow().isoformat(),
                "query": query,
                "company": company
            }

            # Store in Redis
            await self.redis.setex(
                f"cache:{cache_key}",
                ttl,
                json.dumps(cache_data)
            )

            # Store metadata
            await self.redis.hset(
                f"meta:{cache_key}",
                mapping={
                    "query": query,
                    "company": company or "",
                    "cached_at": cache_data["cached_at"],
                    "ttl": str(ttl),
                    "hits": "0"
                }
            )

            # Set expiry on metadata
            await self.redis.expire(f"meta:{cache_key}", ttl)
            await self.redis.expire(f"hits:{cache_key}", ttl)

            # Add to cache index
            await self.redis.sadd("cache:keys", cache_key)

            # Enforce max cache size
            await self._enforce_cache_limit()

            logger.debug(f"Cached response with key: {cache_key}")
            return True

        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    async def invalidate(
        self,
        query: Optional[str] = None,
        company: Optional[str] = None
    ) -> int:
        """Invalidate cache entries.

        Args:
            query: Query to invalidate (None for all)
            company: Company to invalidate (None for all)

        Returns:
            Number of entries invalidated
        """
        if not self.redis:
            await self.connect()

        if not self.redis:
            return 0

        try:
            count = 0

            if query:
                # Invalidate specific query
                cache_key = self._generate_cache_key(query, company)

                if await self.redis.delete(
                    f"cache:{cache_key}",
                    f"meta:{cache_key}",
                    f"hits:{cache_key}"
                ):
                    await self.redis.srem("cache:keys", cache_key)
                    count = 1

            elif company:
                # Invalidate all queries for company
                cache_keys = await self.redis.smembers("cache:keys")

                for key in cache_keys:
                    meta = await self.redis.hgetall(f"meta:{key}")

                    if meta.get("company") == company:
                        await self.redis.delete(
                            f"cache:{key}",
                            f"meta:{key}",
                            f"hits:{key}"
                        )
                        await self.redis.srem("cache:keys", key)
                        count += 1

            else:
                # Invalidate all cache
                cache_keys = await self.redis.smembers("cache:keys")
                count = len(cache_keys)

                # Delete all cache entries
                for key in cache_keys:
                    await self.redis.delete(
                        f"cache:{key}",
                        f"meta:{key}",
                        f"hits:{key}"
                    )

                # Clear index
                await self.redis.delete("cache:keys")

            logger.info(f"Invalidated {count} cache entries")
            return count

        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
            return 0

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Cache statistics
        """
        if not self.redis:
            await self.connect()

        if not self.redis:
            return {"error": "Redis not connected"}

        try:
            # Get cache keys
            cache_keys = await self.redis.smembers("cache:keys")

            # Calculate statistics
            total_entries = len(cache_keys)
            total_hits = 0

            for key in cache_keys:
                hits = await self.redis.get(f"hits:{key}")
                if hits:
                    total_hits += int(hits)

            # Get memory usage
            info = await self.redis.info("memory")
            memory_used = info.get("used_memory_human", "Unknown")

            return {
                "total_entries": total_entries,
                "total_hits": total_hits,
                "memory_used": memory_used,
                "max_entries": self.max_cache_size,
                "default_ttl": self.default_ttl
            }

        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"error": str(e)}

    async def _enforce_cache_limit(self):
        """Enforce maximum cache size."""
        try:
            cache_keys = await self.redis.smembers("cache:keys")

            if len(cache_keys) > self.max_cache_size:
                # Get oldest entries
                entries_with_time = []

                for key in cache_keys:
                    meta = await self.redis.hgetall(f"meta:{key}")
                    if meta and "cached_at" in meta:
                        entries_with_time.append(
                            (key, meta["cached_at"])
                        )

                # Sort by cached time
                entries_with_time.sort(key=lambda x: x[1])

                # Remove oldest entries
                to_remove = len(cache_keys) - self.max_cache_size

                for key, _ in entries_with_time[:to_remove]:
                    await self.redis.delete(
                        f"cache:{key}",
                        f"meta:{key}",
                        f"hits:{key}"
                    )
                    await self.redis.srem("cache:keys", key)

                logger.debug(f"Removed {to_remove} old cache entries")

        except Exception as e:
            logger.error(f"Failed to enforce cache limit: {e}")

    async def warmup(self, queries: list[dict[str, Any]]):
        """Warm up cache with common queries.

        Args:
            queries: List of queries to cache
        """
        logger.info(f"Warming up cache with {len(queries)} queries")

        for query_data in queries:
            try:
                await self.set(
                    query=query_data["query"],
                    response=query_data["response"],
                    company=query_data.get("company"),
                    ttl=query_data.get("ttl", self.default_ttl)
                )
            except Exception as e:
                logger.warning(f"Failed to warm up query: {e}")

        logger.info("Cache warmup completed")
