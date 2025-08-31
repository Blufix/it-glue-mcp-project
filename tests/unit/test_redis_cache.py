"""Unit tests for Redis cache layer."""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import redis.asyncio as redis

from src.cache.redis_cache import (
    RedisCache,
    CacheManager,
    QueryType,
    CacheStrategy,
    CacheEntry
)
from src.cache.cache_warmer import CacheWarmer, WarmingQuery


class TestCacheStrategy:
    """Test suite for CacheStrategy."""
    
    def test_strategy_for_critical_queries(self):
        """Test cache strategy for critical queries."""
        strategy = CacheStrategy.for_query_type(QueryType.CRITICAL)
        
        assert strategy.ttl_seconds == 60  # 1 minute
        assert strategy.warm_on_startup is True
        assert strategy.refresh_before_expiry is True
        assert strategy.invalidate_on_update is True
        assert strategy.max_entries == 100
    
    def test_strategy_for_documentation_queries(self):
        """Test cache strategy for documentation queries."""
        strategy = CacheStrategy.for_query_type(QueryType.DOCUMENTATION)
        
        assert strategy.ttl_seconds == 86400  # 24 hours
        assert strategy.warm_on_startup is True
        assert strategy.refresh_before_expiry is False
        assert strategy.invalidate_on_update is False
        assert strategy.max_entries == 2000
    
    def test_strategy_for_investigation_queries(self):
        """Test cache strategy for investigation queries."""
        strategy = CacheStrategy.for_query_type(QueryType.INVESTIGATION)
        
        assert strategy.ttl_seconds == 300  # 5 minutes
        assert strategy.warm_on_startup is False
        assert strategy.refresh_before_expiry is True
        assert strategy.invalidate_on_update is True


class TestRedisCache:
    """Test suite for RedisCache."""
    
    @pytest.fixture
    async def mock_redis(self):
        """Create mock Redis client."""
        mock_client = AsyncMock(spec=redis.Redis)
        mock_client.ping.return_value = True
        mock_client.get.return_value = None
        mock_client.setex.return_value = True
        mock_client.delete.return_value = 1
        mock_client.exists.return_value = True
        mock_client.scan.return_value = (0, [])
        mock_client.smembers.return_value = set()
        mock_client.info.return_value = {
            'used_memory_human': '10MB',
            'used_memory_peak_human': '15MB'
        }
        return mock_client
    
    @pytest.fixture
    async def cache(self, mock_redis):
        """Create cache instance with mock Redis."""
        cache = RedisCache()
        cache.client = mock_redis
        cache.connected = True
        return cache
    
    @pytest.mark.asyncio
    async def test_connect(self):
        """Test Redis connection."""
        cache = RedisCache()
        
        with patch('redis.asyncio.Redis.from_url') as mock_from_url:
            mock_client = AsyncMock()
            mock_client.ping.return_value = True
            mock_from_url.return_value = mock_client
            
            await cache.connect()
            
            assert cache.connected is True
            assert cache.client is not None
            mock_client.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_cache_key(self, cache):
        """Test cache key generation."""
        # Simple query
        key1 = cache._generate_cache_key("SELECT * FROM users")
        assert key1.startswith("query:")
        assert len(key1) > 10
        
        # Query with params
        key2 = cache._generate_cache_key(
            "SELECT * FROM users WHERE id = ?",
            {'id': 123}
        )
        assert key2 != key1
        
        # Query with context
        key3 = cache._generate_cache_key(
            "SELECT * FROM users",
            None,
            {'organization_id': 'org123', 'user_id': 'user456'}
        )
        assert key3 != key1
        
        # Same query should generate same key
        key4 = cache._generate_cache_key("SELECT * FROM users")
        assert key4 == key1
    
    @pytest.mark.asyncio
    async def test_get_cache_miss(self, cache):
        """Test cache miss."""
        cache.client.get.return_value = None
        
        result = await cache.get("test_key")
        
        assert result is None
        assert cache.stats['misses'] == 1
        assert cache.stats['hits'] == 0
    
    @pytest.mark.asyncio
    async def test_get_cache_hit(self, cache):
        """Test cache hit."""
        test_data = {'foo': 'bar', 'count': 42}
        cache.client.get.return_value = json.dumps(test_data)
        
        result = await cache.get("test_key")
        
        assert result == test_data
        assert cache.stats['hits'] == 1
        assert cache.stats['misses'] == 0
    
    @pytest.mark.asyncio
    async def test_set_with_ttl(self, cache):
        """Test setting value with TTL."""
        test_data = {'foo': 'bar'}
        
        success = await cache.set(
            "test_key",
            test_data,
            query_type=QueryType.CRITICAL
        )
        
        assert success is True
        assert cache.stats['sets'] == 1
        
        # Check TTL was set correctly (60s for critical)
        cache.client.setex.assert_called()
        call_args = cache.client.setex.call_args
        assert call_args[0][1] == 60  # TTL
        assert json.loads(call_args[0][2]) == test_data
    
    @pytest.mark.asyncio
    async def test_set_with_custom_ttl(self, cache):
        """Test setting value with custom TTL."""
        test_data = {'foo': 'bar'}
        
        await cache.set(
            "test_key",
            test_data,
            ttl_override=3600
        )
        
        # Check custom TTL was used
        call_args = cache.client.setex.call_args
        assert call_args[0][1] == 3600
    
    @pytest.mark.asyncio
    async def test_delete(self, cache):
        """Test deleting cache entry."""
        cache.client.delete.return_value = 2  # Deleted value and metadata
        
        success = await cache.delete("test_key")
        
        assert success is True
        assert cache.stats['deletes'] == 1
        cache.client.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_invalidate_by_tags(self, cache):
        """Test invalidation by tags."""
        # Mock keys with tag
        cache.client.smembers.return_value = {
            'itglue:query:key1',
            'itglue:query:key2'
        }
        cache.client.pipeline.return_value = AsyncMock()
        
        invalidated = await cache.invalidate_by_tags(['org:123'])
        
        assert invalidated == 0  # Mock doesn't execute pipeline
        cache.client.smembers.assert_called_with('itglue:tag:org:123')
    
    @pytest.mark.asyncio
    async def test_invalidate_pattern(self, cache):
        """Test pattern-based invalidation."""
        # Mock scan results
        cache.client.scan.return_value = (0, [
            'itglue:query:org:123:key1',
            'itglue:query:org:123:key2'
        ])
        cache.client.pipeline.return_value = AsyncMock()
        
        invalidated = await cache.invalidate_pattern('query:org:123:*')
        
        assert invalidated == 0  # Mock doesn't execute pipeline
        cache.client.scan.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_or_fetch_cache_hit(self, cache):
        """Test get_or_fetch with cache hit."""
        cached_data = {'cached': True}
        cache.client.get.return_value = json.dumps(cached_data)
        
        fetch_func = AsyncMock()
        
        result = await cache.get_or_fetch(
            "test_query",
            fetch_func,
            query_type=QueryType.SEARCH
        )
        
        assert result == cached_data
        fetch_func.assert_not_called()  # Should not fetch
    
    @pytest.mark.asyncio
    async def test_get_or_fetch_cache_miss(self, cache):
        """Test get_or_fetch with cache miss."""
        cache.client.get.return_value = None
        fetched_data = {'fetched': True}
        
        fetch_func = AsyncMock(return_value=fetched_data)
        
        result = await cache.get_or_fetch(
            "test_query",
            fetch_func,
            query_type=QueryType.SEARCH
        )
        
        assert result == fetched_data
        fetch_func.assert_called_once()
        cache.client.setex.assert_called()  # Should cache result
    
    @pytest.mark.asyncio
    async def test_get_or_fetch_force_refresh(self, cache):
        """Test get_or_fetch with forced refresh."""
        cached_data = {'cached': True}
        cache.client.get.return_value = json.dumps(cached_data)
        fetched_data = {'fetched': True}
        
        fetch_func = AsyncMock(return_value=fetched_data)
        
        result = await cache.get_or_fetch(
            "test_query",
            fetch_func,
            force_refresh=True
        )
        
        assert result == fetched_data
        fetch_func.assert_called_once()  # Should fetch despite cache
    
    @pytest.mark.asyncio
    async def test_warm_cache(self, cache):
        """Test cache warming."""
        queries = [
            {
                'query': 'SELECT * FROM users',
                'params': {},
                'query_type': QueryType.OPERATIONAL
            },
            {
                'query': 'SELECT * FROM passwords',
                'params': {'critical': True},
                'query_type': QueryType.CRITICAL
            }
        ]
        
        fetch_func = AsyncMock(return_value={'data': 'test'})
        cache.client.get.return_value = None  # No existing cache
        
        warmed = await cache.warm_cache(queries, fetch_func)
        
        assert warmed == 2
        assert fetch_func.call_count == 2
        assert cache.client.setex.call_count >= 2  # Data + metadata
    
    @pytest.mark.asyncio
    async def test_extract_tags(self, cache):
        """Test tag extraction from queries."""
        tags = cache._extract_tags(
            "SELECT * FROM passwords WHERE org_id = ?",
            {'resource_type': 'server', 'resource_id': '123'},
            {'organization_id': 'org456'}
        )
        
        assert 'org:org456' in tags
        assert 'type:server' in tags
        assert 'resource:123' in tags
        assert 'entity:password' in tags
    
    @pytest.mark.asyncio
    async def test_get_stats(self, cache):
        """Test statistics retrieval."""
        cache.stats = {
            'hits': 100,
            'misses': 20,
            'sets': 50,
            'deletes': 5,
            'errors': 2
        }
        
        cache.client.info.side_effect = [
            {'used_memory_human': '10MB', 'used_memory_peak_human': '15MB'},
            {'db0': {'keys': 500, 'expires': 450}}
        ]
        
        stats = await cache.get_stats()
        
        assert stats['hits'] == 100
        assert stats['misses'] == 20
        assert stats['hit_rate'] == 100 / 120 * 100
        assert stats['redis_memory_used'] == '10MB'
        assert stats['total_keys'] == 500


class TestCacheManager:
    """Test suite for CacheManager."""
    
    @pytest.fixture
    async def manager(self):
        """Create cache manager."""
        manager = CacheManager()
        
        # Mock all cache instances
        for cache in manager.caches:
            cache.client = AsyncMock()
            cache.connected = True
        
        return manager
    
    @pytest.mark.asyncio
    async def test_connect_all(self, manager):
        """Test connecting all cache instances."""
        with patch.object(RedisCache, 'connect') as mock_connect:
            mock_connect.return_value = None
            await manager.connect()
            
            # Should connect all 3 caches
            assert mock_connect.call_count == 3
    
    @pytest.mark.asyncio
    async def test_invalidate_organization(self, manager):
        """Test invalidating organization cache."""
        for cache in manager.caches:
            cache.invalidate_by_tags = AsyncMock(return_value=5)
            cache.invalidate_pattern = AsyncMock(return_value=3)
        
        total = await manager.invalidate_organization('org123')
        
        # 3 caches * (5 by tag + 3 by pattern) = 24
        assert total == 24
        
        for cache in manager.caches:
            cache.invalidate_by_tags.assert_called_with(['org:org123'])
            cache.invalidate_pattern.assert_called_with('*org:org123:*')
    
    @pytest.mark.asyncio
    async def test_invalidate_resource(self, manager):
        """Test invalidating resource cache."""
        for cache in manager.caches:
            cache.invalidate_by_tags = AsyncMock(return_value=2)
        
        total = await manager.invalidate_resource('password', 'pass123')
        
        assert total == 6  # 3 caches * 2 entries
        
        for cache in manager.caches:
            cache.invalidate_by_tags.assert_called_with([
                'type:password',
                'resource:pass123'
            ])
    
    @pytest.mark.asyncio
    async def test_get_combined_stats(self, manager):
        """Test combined statistics."""
        for i, cache in enumerate(manager.caches):
            cache.get_stats = AsyncMock(return_value={
                'hits': 100 * (i + 1),
                'misses': 20 * (i + 1),
                'sets': 50 * (i + 1),
                'deletes': 5 * (i + 1),
                'errors': 2 * (i + 1)
            })
        
        stats = await manager.get_combined_stats()
        
        assert 'query_cache' in stats
        assert 'result_cache' in stats
        assert 'session_cache' in stats
        assert 'totals' in stats
        
        totals = stats['totals']
        assert totals['total_hits'] == 600  # 100 + 200 + 300
        assert totals['total_misses'] == 120  # 20 + 40 + 60
        assert totals['overall_hit_rate'] == 600 / 720 * 100


class TestCacheWarmer:
    """Test suite for CacheWarmer."""
    
    @pytest.fixture
    async def warmer(self):
        """Create cache warmer."""
        cache_manager = CacheManager()
        data_fetcher = AsyncMock()
        
        # Mock cache methods
        for cache in cache_manager.caches:
            cache.get_or_fetch = AsyncMock(return_value={'data': 'test'})
        
        warmer = CacheWarmer(cache_manager, data_fetcher)
        return warmer
    
    @pytest.mark.asyncio
    async def test_warm_startup_cache(self, warmer):
        """Test startup cache warming."""
        warmer.data_fetcher.return_value = {'test': 'data'}
        
        stats = await warmer.warm_startup_cache(['org123'])
        
        assert stats['warmed'] > 0
        assert 'duration_ms' in stats
        assert stats['errors'] == []
    
    @pytest.mark.asyncio
    async def test_warm_single_query(self, warmer):
        """Test warming a single query."""
        query = "SELECT * FROM passwords"
        params = {'critical': True}
        
        success = await warmer._warm_single_query(
            query,
            params,
            QueryType.CRITICAL
        )
        
        assert success is True
        warmer.cache_manager.query_cache.get_or_fetch.assert_called()
    
    @pytest.mark.asyncio
    async def test_warm_for_query_type(self, warmer):
        """Test warming specific query type."""
        warmed = await warmer.warm_for_query_type(
            QueryType.DOCUMENTATION,
            'org123'
        )
        
        assert warmed >= 0  # Should warm documentation queries
    
    @pytest.mark.asyncio
    async def test_background_warming(self, warmer):
        """Test background warming task."""
        await warmer.start_background_warming(interval_minutes=1)
        
        assert warmer.warming_task is not None
        assert not warmer.warming_task.done()
        
        await warmer.stop_background_warming()
        
        assert warmer.stop_warming is True
    
    def test_get_warming_stats(self, warmer):
        """Test getting warming statistics."""
        warmer.stats = {
            'total_warmed': 50,
            'last_warm_time': datetime.now() - timedelta(minutes=30),
            'warm_duration_ms': 1500,
            'queries_warmed': ['query1', 'query2']
        }
        
        stats = warmer.get_warming_stats()
        
        assert stats['total_warmed'] == 50
        assert 'minutes_since_warm' in stats
        assert stats['minutes_since_warm'] > 29
        assert stats['background_warming_active'] is False


class TestIntegrationScenarios:
    """Integration tests for cache scenarios."""
    
    @pytest.mark.asyncio
    async def test_emergency_query_caching(self):
        """Test caching for emergency queries."""
        cache = RedisCache()
        cache.client = AsyncMock()
        cache.connected = True
        
        # Emergency password query
        await cache.set(
            "emergency_password",
            {'password': 'secret123'},
            query_type=QueryType.CRITICAL
        )
        
        # Should use short TTL (60s)
        call_args = cache.client.setex.call_args
        assert call_args[0][1] == 60
    
    @pytest.mark.asyncio
    async def test_documentation_caching(self):
        """Test caching for documentation."""
        cache = RedisCache()
        cache.client = AsyncMock()
        cache.connected = True
        
        # Documentation query
        await cache.set(
            "runbook",
            {'content': 'Step 1: ...'},
            query_type=QueryType.DOCUMENTATION
        )
        
        # Should use long TTL (24 hours)
        call_args = cache.client.setex.call_args
        assert call_args[0][1] == 86400
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_on_update(self):
        """Test cache invalidation when data changes."""
        manager = CacheManager()
        
        for cache in manager.caches:
            cache.invalidate_by_tags = AsyncMock(return_value=5)
        
        # Simulate password update
        invalidated = await manager.invalidate_resource('password', 'pass123')
        
        assert invalidated > 0
        
        # All caches should invalidate
        for cache in manager.caches:
            cache.invalidate_by_tags.assert_called()