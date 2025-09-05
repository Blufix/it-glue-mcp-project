"""Cache service for MCP tools."""

import json
import logging
from typing import Any, Optional

from src.cache.manager import CacheManager

logger = logging.getLogger(__name__)


class CacheService:
    """Cache service interface for MCP tools.
    
    Provides a simple get/set interface that wraps the more complex CacheManager.
    """
    
    def __init__(self, cache_manager: Optional[CacheManager] = None):
        """Initialize cache service.
        
        Args:
            cache_manager: Optional cache manager instance
        """
        self.cache_manager = cache_manager or CacheManager()
        self._connected = False
    
    async def _ensure_connected(self):
        """Ensure cache connection is established."""
        if not self._connected:
            try:
                await self.cache_manager.connect()
                self._connected = True
            except Exception as e:
                logger.warning(f"Failed to connect to cache: {e}")
    
    async def get(self, cache_key: str) -> Optional[Any]:
        """Get value from cache by key.
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        await self._ensure_connected()
        
        if not self.cache_manager.redis:
            return None
            
        try:
            # Direct Redis get using the cache key
            cached_data = await self.cache_manager.redis.get(f"mcp:{cache_key}")
            
            if cached_data:
                logger.debug(f"Cache hit for key: {cache_key}")
                return json.loads(cached_data)
            
            logger.debug(f"Cache miss for key: {cache_key}")
            return None
            
        except Exception as e:
            logger.error(f"Cache get error for key {cache_key}: {e}")
            return None
    
    async def set(
        self, 
        cache_key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache with optional TTL.
        
        Args:
            cache_key: Cache key
            value: Value to cache  
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        await self._ensure_connected()
        
        if not self.cache_manager.redis:
            return False
            
        try:
            # Serialize value to JSON
            cached_data = json.dumps(value, default=str)
            
            # Store in Redis with TTL
            if ttl:
                await self.cache_manager.redis.setex(
                    f"mcp:{cache_key}", 
                    ttl, 
                    cached_data
                )
            else:
                await self.cache_manager.redis.set(
                    f"mcp:{cache_key}", 
                    cached_data
                )
            
            logger.debug(f"Cache set for key: {cache_key} (TTL: {ttl})")
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for key {cache_key}: {e}")
            return False
    
    async def delete(self, cache_key: str) -> bool:
        """Delete key from cache.
        
        Args:
            cache_key: Cache key to delete
            
        Returns:
            True if deleted, False otherwise
        """
        await self._ensure_connected()
        
        if not self.cache_manager.redis:
            return False
            
        try:
            result = await self.cache_manager.redis.delete(f"mcp:{cache_key}")
            logger.debug(f"Cache delete for key: {cache_key}")
            return bool(result)
            
        except Exception as e:
            logger.error(f"Cache delete error for key {cache_key}: {e}")
            return False
    
    async def clear(self) -> bool:
        """Clear all MCP cache entries.
        
        Returns:
            True if successful, False otherwise
        """
        await self._ensure_connected()
        
        if not self.cache_manager.redis:
            return False
            
        try:
            # Find all MCP cache keys
            mcp_keys = await self.cache_manager.redis.keys("mcp:*")
            
            if mcp_keys:
                await self.cache_manager.redis.delete(*mcp_keys)
                logger.info(f"Cleared {len(mcp_keys)} MCP cache entries")
            
            return True
            
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False
    
    async def close(self):
        """Close cache connections."""
        if self.cache_manager and self._connected:
            await self.cache_manager.disconnect()
            self._connected = False