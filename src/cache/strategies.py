"""Cache strategies and policies for different query types."""

import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
from enum import Enum

from src.config.settings import settings


class CacheStrategy(Enum):
    """Cache strategy types."""
    AGGRESSIVE = "aggressive"  # Long TTL, cache everything
    MODERATE = "moderate"      # Medium TTL, selective caching
    CONSERVATIVE = "conservative"  # Short TTL, minimal caching
    BYPASS = "bypass"          # No caching


class QueryType(Enum):
    """Query types for cache strategy selection."""
    COMPANY_INFO = "company_info"
    CONFIGURATION = "configuration"
    PASSWORD = "password"
    ASSET = "asset"
    DOCUMENT = "document"
    SEARCH = "search"
    AGGREGATE = "aggregate"
    REAL_TIME = "real_time"


class CacheStrategyManager:
    """Manages cache strategies for different query types."""
    
    def __init__(self):
        """Initialize cache strategy manager."""
        self.strategies = self._initialize_strategies()
        self.ttl_map = self._initialize_ttl_map()
        
    def _initialize_strategies(self) -> Dict[QueryType, CacheStrategy]:
        """Initialize default strategies for query types."""
        return {
            QueryType.COMPANY_INFO: CacheStrategy.AGGRESSIVE,
            QueryType.CONFIGURATION: CacheStrategy.MODERATE,
            QueryType.PASSWORD: CacheStrategy.CONSERVATIVE,
            QueryType.ASSET: CacheStrategy.MODERATE,
            QueryType.DOCUMENT: CacheStrategy.AGGRESSIVE,
            QueryType.SEARCH: CacheStrategy.MODERATE,
            QueryType.AGGREGATE: CacheStrategy.AGGRESSIVE,
            QueryType.REAL_TIME: CacheStrategy.BYPASS,
        }
        
    def _initialize_ttl_map(self) -> Dict[CacheStrategy, int]:
        """Initialize TTL values for each strategy."""
        return {
            CacheStrategy.AGGRESSIVE: 3600,    # 1 hour
            CacheStrategy.MODERATE: 600,       # 10 minutes
            CacheStrategy.CONSERVATIVE: 60,    # 1 minute
            CacheStrategy.BYPASS: 0,           # No caching
        }
        
    def get_strategy(self, query_type: QueryType) -> CacheStrategy:
        """Get cache strategy for query type."""
        return self.strategies.get(query_type, CacheStrategy.MODERATE)
        
    def get_ttl(self, query_type: QueryType) -> int:
        """Get TTL for query type."""
        strategy = self.get_strategy(query_type)
        return self.ttl_map.get(strategy, 300)
        
    def should_cache(self, query_type: QueryType) -> bool:
        """Determine if query should be cached."""
        strategy = self.get_strategy(query_type)
        return strategy != CacheStrategy.BYPASS
        
    def detect_query_type(self, query: str) -> QueryType:
        """Detect query type from query string."""
        query_lower = query.lower()
        
        # Check for specific patterns
        if any(word in query_lower for word in ["password", "credential", "secret"]):
            return QueryType.PASSWORD
        elif any(word in query_lower for word in ["configuration", "config", "setting"]):
            return QueryType.CONFIGURATION
        elif any(word in query_lower for word in ["company", "organization", "client"]):
            return QueryType.COMPANY_INFO
        elif any(word in query_lower for word in ["asset", "device", "hardware"]):
            return QueryType.ASSET
        elif any(word in query_lower for word in ["document", "article", "kb"]):
            return QueryType.DOCUMENT
        elif any(word in query_lower for word in ["search", "find", "lookup"]):
            return QueryType.SEARCH
        elif any(word in query_lower for word in ["count", "total", "summary", "aggregate"]):
            return QueryType.AGGREGATE
        elif any(word in query_lower for word in ["current", "now", "real-time", "live"]):
            return QueryType.REAL_TIME
        else:
            return QueryType.SEARCH


class CacheKeyGenerator:
    """Advanced cache key generation with versioning and namespacing."""
    
    def __init__(self, version: str = "v1"):
        """Initialize cache key generator."""
        self.version = version
        
    def generate(
        self,
        query: str,
        company: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        user_context: Optional[str] = None
    ) -> str:
        """Generate cache key with multiple factors."""
        components = [
            f"version:{self.version}",
            f"query:{self._normalize_query(query)}",
            f"company:{company or 'all'}"
        ]
        
        if filters:
            filter_str = self._serialize_filters(filters)
            components.append(f"filters:{filter_str}")
            
        if user_context:
            components.append(f"context:{user_context}")
            
        key_string = ":".join(components)
        return f"cache:{hashlib.sha256(key_string.encode()).hexdigest()}"
        
    def _normalize_query(self, query: str) -> str:
        """Normalize query for consistent cache keys."""
        # Remove extra whitespace
        normalized = " ".join(query.split())
        # Convert to lowercase
        normalized = normalized.lower()
        # Remove punctuation at end
        normalized = normalized.rstrip(".,!?;")
        return normalized
        
    def _serialize_filters(self, filters: Dict[str, Any]) -> str:
        """Serialize filters for cache key."""
        # Sort keys for consistency
        sorted_filters = dict(sorted(filters.items()))
        return json.dumps(sorted_filters, sort_keys=True, separators=(",", ":"))


class CacheInvalidator:
    """Manages cache invalidation strategies."""
    
    def __init__(self, cache_manager):
        """Initialize cache invalidator."""
        self.cache = cache_manager
        
    async def invalidate_on_sync(self, sync_type: str, entity_ids: List[str]):
        """Invalidate cache after data sync."""
        # Invalidate specific entities
        for entity_id in entity_ids:
            await self.cache.invalidate(query=f"*{entity_id}*")
            
        # Invalidate aggregate queries
        if sync_type in ["full", "organization"]:
            await self.cache.invalidate(query="*count*")
            await self.cache.invalidate(query="*total*")
            await self.cache.invalidate(query="*summary*")
            
    async def invalidate_on_update(self, entity_type: str, entity_id: str):
        """Invalidate cache when entity is updated."""
        # Invalidate specific entity
        await self.cache.invalidate(query=f"*{entity_id}*")
        
        # Invalidate related queries
        if entity_type == "organization":
            await self.cache.invalidate(company=entity_id)
        elif entity_type == "configuration":
            await self.cache.invalidate(query="*configuration*")
        elif entity_type == "password":
            await self.cache.invalidate(query="*password*")
            
    async def invalidate_stale(self, max_age_hours: int = 24):
        """Invalidate cache entries older than max age."""
        cache_keys = await self.cache.redis.smembers("cache:keys")
        now = datetime.utcnow()
        invalidated = 0
        
        for key in cache_keys:
            meta = await self.cache.redis.hgetall(f"meta:{key}")
            if meta and "cached_at" in meta:
                cached_at = datetime.fromisoformat(meta["cached_at"])
                age = now - cached_at
                
                if age > timedelta(hours=max_age_hours):
                    await self.cache.redis.delete(
                        f"cache:{key}",
                        f"meta:{key}",
                        f"hits:{key}"
                    )
                    await self.cache.redis.srem("cache:keys", key)
                    invalidated += 1
                    
        return invalidated


class CacheWarmer:
    """Preloads cache with common queries."""
    
    def __init__(self, cache_manager, query_engine):
        """Initialize cache warmer."""
        self.cache = cache_manager
        self.query_engine = query_engine
        
    async def warmup_common_queries(self):
        """Warm up cache with common queries."""
        common_queries = [
            {"query": "list all companies", "company": None},
            {"query": "show recent configurations", "company": None},
            {"query": "get server assets", "company": None},
            {"query": "list active devices", "company": None},
            {"query": "show documentation", "company": None},
        ]
        
        for query_data in common_queries:
            try:
                # Execute query
                response = await self.query_engine.execute(
                    query=query_data["query"],
                    company=query_data.get("company")
                )
                
                # Cache response
                await self.cache.set(
                    query=query_data["query"],
                    response=response,
                    company=query_data.get("company"),
                    ttl=3600  # 1 hour for warmup queries
                )
            except Exception as e:
                logger.warning(f"Failed to warm up query '{query_data['query']}': {e}")
                
    async def warmup_organization_data(self, organization_id: str):
        """Warm up cache for specific organization."""
        queries = [
            f"get configurations for {organization_id}",
            f"list assets for {organization_id}",
            f"show contacts for {organization_id}",
            f"get locations for {organization_id}",
        ]
        
        for query in queries:
            try:
                response = await self.query_engine.execute(
                    query=query,
                    company=organization_id
                )
                
                await self.cache.set(
                    query=query,
                    response=response,
                    company=organization_id,
                    ttl=1800  # 30 minutes
                )
            except Exception as e:
                logger.warning(f"Failed to warm up org query: {e}")


import logging
logger = logging.getLogger(__name__)