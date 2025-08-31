"""Cache management for query results."""

from .manager import CacheManager as LegacyCacheManager
from .redis_cache import (
    RedisCache,
    CacheManager,
    QueryType,
    CacheStrategy,
    CacheEntry
)
from .cache_warmer import (
    CacheWarmer,
    WarmingQuery
)

__all__ = [
    'LegacyCacheManager',
    'RedisCache',
    'CacheManager',
    'QueryType',
    'CacheStrategy',
    'CacheEntry',
    'CacheWarmer',
    'WarmingQuery'
]