"""Cache warming and preloading for common queries."""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass

from .redis_cache import RedisCache, QueryType, CacheManager

logger = logging.getLogger(__name__)


@dataclass
class WarmingQuery:
    """A query to warm the cache with."""
    query: str
    params: Dict[str, Any]
    query_type: QueryType
    priority: int = 5  # 1-10, higher is more important
    organizations: Optional[List[str]] = None  # Specific orgs or None for all


class CacheWarmer:
    """Warms cache with common and predicted queries."""
    
    def __init__(
        self,
        cache_manager: CacheManager,
        data_fetcher: Callable,
        learning_engine=None
    ):
        """Initialize cache warmer.
        
        Args:
            cache_manager: Cache manager instance
            data_fetcher: Async function to fetch data
            learning_engine: Optional ML engine for predictive warming
        """
        self.cache_manager = cache_manager
        self.data_fetcher = data_fetcher
        self.learning_engine = learning_engine
        
        # Warming statistics
        self.stats = {
            'total_warmed': 0,
            'last_warm_time': None,
            'warm_duration_ms': 0,
            'queries_warmed': []
        }
        
        # Common queries to warm
        self.common_queries = self._define_common_queries()
        
        # Background warming task
        self.warming_task = None
        self.stop_warming = False
    
    def _define_common_queries(self) -> List[WarmingQuery]:
        """Define common queries that should be pre-cached."""
        return [
            # Critical queries - passwords and emergency access
            WarmingQuery(
                query="SELECT * FROM passwords WHERE organization_id = :org_id AND importance = 'critical'",
                params={'importance': 'critical'},
                query_type=QueryType.CRITICAL,
                priority=10
            ),
            WarmingQuery(
                query="SELECT * FROM configurations WHERE organization_id = :org_id AND status = 'production'",
                params={'status': 'production'},
                query_type=QueryType.OPERATIONAL,
                priority=9
            ),
            
            # Common organization queries
            WarmingQuery(
                query="SELECT * FROM organizations WHERE active = true ORDER BY name",
                params={},
                query_type=QueryType.OPERATIONAL,
                priority=8
            ),
            WarmingQuery(
                query="SELECT COUNT(*) as total, type FROM configurations WHERE organization_id = :org_id GROUP BY type",
                params={},
                query_type=QueryType.OPERATIONAL,
                priority=7
            ),
            
            # Documentation queries
            WarmingQuery(
                query="SELECT * FROM documents WHERE type = 'runbook' AND active = true",
                params={'type': 'runbook'},
                query_type=QueryType.DOCUMENTATION,
                priority=6
            ),
            WarmingQuery(
                query="SELECT * FROM documents WHERE type = 'disaster_recovery'",
                params={'type': 'disaster_recovery'},
                query_type=QueryType.DOCUMENTATION,
                priority=8
            ),
            
            # Recent changes for investigation
            WarmingQuery(
                query="SELECT * FROM audit_log WHERE organization_id = :org_id AND created_at > :since ORDER BY created_at DESC LIMIT 100",
                params={'since': (datetime.now() - timedelta(hours=24)).isoformat()},
                query_type=QueryType.INVESTIGATION,
                priority=7
            ),
            
            # Common search patterns
            WarmingQuery(
                query="SELECT * FROM configurations WHERE name ILIKE :pattern",
                params={'pattern': '%server%'},
                query_type=QueryType.SEARCH,
                priority=5
            ),
            WarmingQuery(
                query="SELECT * FROM passwords WHERE name ILIKE :pattern OR username ILIKE :pattern",
                params={'pattern': '%admin%'},
                query_type=QueryType.SEARCH,
                priority=6
            )
        ]
    
    async def warm_startup_cache(
        self,
        organizations: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Warm cache on application startup.
        
        Args:
            organizations: Specific organizations to warm, or None for all
            
        Returns:
            Warming statistics
        """
        start_time = datetime.now()
        warmed_count = 0
        errors = []
        
        logger.info("Starting cache warming...")
        
        # Sort queries by priority (highest first)
        queries = sorted(self.common_queries, key=lambda q: q.priority, reverse=True)
        
        # Filter queries by organization if specified
        if organizations:
            queries = [
                q for q in queries
                if q.organizations is None or 
                any(org in q.organizations for org in organizations)
            ]
        
        # Warm queries based on their type strategy
        for warming_query in queries:
            strategy = QueryType.CRITICAL if warming_query.priority >= 8 else warming_query.query_type
            
            # Skip if strategy doesn't require startup warming
            if strategy == QueryType.SEARCH:
                continue
            
            try:
                # For organization-specific queries
                if organizations and ':org_id' in warming_query.query:
                    for org_id in organizations:
                        params = warming_query.params.copy()
                        params['org_id'] = org_id
                        
                        result = await self._warm_single_query(
                            warming_query.query,
                            params,
                            warming_query.query_type,
                            {'organization_id': org_id}
                        )
                        
                        if result:
                            warmed_count += 1
                else:
                    # Global queries
                    result = await self._warm_single_query(
                        warming_query.query,
                        warming_query.params,
                        warming_query.query_type
                    )
                    
                    if result:
                        warmed_count += 1
                        
            except Exception as e:
                error_msg = f"Error warming query '{warming_query.query[:50]}...': {e}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Warm predicted queries if ML engine available
        if self.learning_engine:
            predicted_count = await self._warm_predicted_queries(organizations)
            warmed_count += predicted_count
        
        duration = (datetime.now() - start_time).total_seconds() * 1000
        
        self.stats.update({
            'total_warmed': warmed_count,
            'last_warm_time': start_time,
            'warm_duration_ms': duration,
            'queries_warmed': [q.query[:50] for q in queries[:10]]  # Top 10
        })
        
        logger.info(f"Cache warming completed: {warmed_count} queries in {duration:.0f}ms")
        
        return {
            'warmed': warmed_count,
            'duration_ms': duration,
            'errors': errors
        }
    
    async def _warm_single_query(
        self,
        query: str,
        params: Dict[str, Any],
        query_type: QueryType,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Warm a single query.
        
        Returns:
            True if successfully warmed
        """
        try:
            # Use the appropriate cache based on query type
            if query_type in [QueryType.CRITICAL, QueryType.INVESTIGATION]:
                cache = self.cache_manager.query_cache
            elif query_type == QueryType.DOCUMENTATION:
                cache = self.cache_manager.result_cache
            else:
                cache = self.cache_manager.query_cache
            
            # Get or fetch the data
            result = await cache.get_or_fetch(
                query,
                self.data_fetcher,
                params,
                context,
                query_type,
                force_refresh=True  # Force fresh data on warming
            )
            
            return result is not None
            
        except Exception as e:
            logger.debug(f"Failed to warm query: {e}")
            return False
    
    async def _warm_predicted_queries(
        self,
        organizations: Optional[List[str]] = None
    ) -> int:
        """Warm queries predicted by ML engine.
        
        Args:
            organizations: Organizations to warm for
            
        Returns:
            Number of queries warmed
        """
        if not self.learning_engine:
            return 0
        
        warmed = 0
        
        try:
            # Get predicted queries for each organization
            orgs_to_warm = organizations or ['global']
            
            for org_id in orgs_to_warm:
                # Get predictions from ML engine
                predictions = await self.learning_engine.get_predicted_queries(
                    organization_id=org_id,
                    time_window='next_hour',
                    max_queries=10
                )
                
                for prediction in predictions:
                    if prediction['confidence'] < 0.7:
                        continue  # Skip low confidence predictions
                    
                    success = await self._warm_single_query(
                        prediction['query'],
                        prediction.get('params', {}),
                        QueryType.SEARCH,  # Default type for predictions
                        {'organization_id': org_id}
                    )
                    
                    if success:
                        warmed += 1
                        
        except Exception as e:
            logger.error(f"Error warming predicted queries: {e}")
        
        return warmed
    
    async def start_background_warming(
        self,
        interval_minutes: int = 30,
        organizations: Optional[List[str]] = None
    ) -> None:
        """Start background cache warming task.
        
        Args:
            interval_minutes: Minutes between warming cycles
            organizations: Organizations to warm
        """
        if self.warming_task and not self.warming_task.done():
            logger.warning("Background warming already running")
            return
        
        self.stop_warming = False
        
        async def warming_loop():
            while not self.stop_warming:
                try:
                    # Warm cache
                    await self.warm_refresh_cache(organizations)
                    
                    # Wait for next cycle
                    await asyncio.sleep(interval_minutes * 60)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in warming loop: {e}")
                    await asyncio.sleep(60)  # Retry after 1 minute on error
        
        self.warming_task = asyncio.create_task(warming_loop())
        logger.info(f"Started background cache warming (interval: {interval_minutes}min)")
    
    async def stop_background_warming(self) -> None:
        """Stop background cache warming."""
        self.stop_warming = True
        
        if self.warming_task:
            self.warming_task.cancel()
            try:
                await self.warming_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped background cache warming")
    
    async def warm_refresh_cache(
        self,
        organizations: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Refresh cache with queries about to expire.
        
        Args:
            organizations: Organizations to refresh
            
        Returns:
            Refresh statistics
        """
        refreshed = 0
        
        # Focus on critical and operational queries that need refresh
        refresh_queries = [
            q for q in self.common_queries
            if q.query_type in [QueryType.CRITICAL, QueryType.OPERATIONAL]
            and q.priority >= 7
        ]
        
        for query in refresh_queries:
            try:
                if organizations and ':org_id' in query.query:
                    for org_id in organizations:
                        params = query.params.copy()
                        params['org_id'] = org_id
                        
                        success = await self._warm_single_query(
                            query.query,
                            params,
                            query.query_type,
                            {'organization_id': org_id}
                        )
                        
                        if success:
                            refreshed += 1
                else:
                    success = await self._warm_single_query(
                        query.query,
                        query.params,
                        query.query_type
                    )
                    
                    if success:
                        refreshed += 1
                        
            except Exception as e:
                logger.error(f"Error refreshing query: {e}")
        
        logger.debug(f"Refreshed {refreshed} cache entries")
        
        return {
            'refreshed': refreshed,
            'timestamp': datetime.now().isoformat()
        }
    
    async def warm_for_query_type(
        self,
        query_type: QueryType,
        organization_id: Optional[str] = None
    ) -> int:
        """Warm cache for a specific query type.
        
        Args:
            query_type: Type of queries to warm
            organization_id: Optional organization filter
            
        Returns:
            Number of queries warmed
        """
        warmed = 0
        
        # Filter queries by type
        type_queries = [
            q for q in self.common_queries
            if q.query_type == query_type
        ]
        
        for query in type_queries:
            try:
                params = query.params.copy()
                context = {}
                
                if organization_id and ':org_id' in query.query:
                    params['org_id'] = organization_id
                    context['organization_id'] = organization_id
                
                success = await self._warm_single_query(
                    query.query,
                    params,
                    query.query_type,
                    context if context else None
                )
                
                if success:
                    warmed += 1
                    
            except Exception as e:
                logger.error(f"Error warming {query_type} query: {e}")
        
        return warmed
    
    def get_warming_stats(self) -> Dict[str, Any]:
        """Get cache warming statistics."""
        stats = self.stats.copy()
        
        # Add current status
        stats['background_warming_active'] = (
            self.warming_task is not None and not self.warming_task.done()
        )
        
        # Calculate time since last warm
        if stats['last_warm_time']:
            elapsed = (datetime.now() - stats['last_warm_time']).total_seconds()
            stats['minutes_since_warm'] = elapsed / 60
        
        return stats


# Export main classes
__all__ = ['CacheWarmer', 'WarmingQuery']