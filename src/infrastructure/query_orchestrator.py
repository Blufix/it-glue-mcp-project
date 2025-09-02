"""Orchestrates parallel queries to IT Glue API for infrastructure documentation."""

import asyncio
import logging
import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Any, Optional

from src.cache import CacheManager
from src.data import db_manager
from src.services.itglue import ITGlueClient

logger = logging.getLogger(__name__)


class QueryOrchestrator:
    """Efficiently queries all IT Glue endpoints for an organization."""

    # IT Glue rate limit: 10 requests per second
    RATE_LIMIT = 10
    RATE_LIMIT_WINDOW = 1.0  # 1 second

    # Resource types to query
    RESOURCE_TYPES = [
        'configurations',
        'flexible_assets',
        'contacts',
        'locations',
        'documents',
        'passwords',
        'domains',
        'networks'
    ]

    def __init__(self, itglue_client: ITGlueClient, cache_manager: CacheManager):
        """Initialize the query orchestrator.

        Args:
            itglue_client: IT Glue API client
            cache_manager: Cache manager for performance
        """
        self.itglue_client = itglue_client
        self.cache_manager = cache_manager
        self.semaphore = asyncio.Semaphore(self.RATE_LIMIT)
        self.request_times: list[float] = []

    async def query_all_resources(
        self,
        organization_id: str,
        snapshot_id: str,
        progress_callback: Optional[Callable] = None
    ) -> dict[str, Any]:
        """Query all IT Glue resources for an organization.

        Args:
            organization_id: IT Glue organization ID
            snapshot_id: Snapshot ID for tracking
            progress_callback: Optional callback for progress updates

        Returns:
            Dictionary containing all resource data
        """
        # Check cache first
        cache_key = f"infrastructure:org:{organization_id}"
        if self.cache_manager and hasattr(self.cache_manager, 'query_cache'):
            cached_data = await self.cache_manager.query_cache.get(cache_key)
            if cached_data:
                logger.info(f"Using cached infrastructure data for org {organization_id}")
                return cached_data

        results = {
            'organization_id': organization_id,
            'snapshot_id': snapshot_id,
            'timestamp': datetime.utcnow().isoformat(),
            'resources': {}
        }

        # Create tasks for parallel execution
        tasks = []
        for resource_type in self.RESOURCE_TYPES:
            task = self._query_resource_type(
                organization_id=organization_id,
                resource_type=resource_type,
                snapshot_id=snapshot_id
            )
            tasks.append(task)

        # Execute tasks with rate limiting
        total_tasks = len(tasks)
        completed = 0

        for i in range(0, len(tasks), self.RATE_LIMIT):
            batch = tasks[i:i + self.RATE_LIMIT]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)

            for j, result in enumerate(batch_results):
                resource_type = self.RESOURCE_TYPES[i + j]

                if isinstance(result, Exception):
                    logger.error(f"Failed to query {resource_type}: {result}")
                    results['resources'][resource_type] = {
                        'error': str(result),
                        'data': []
                    }
                else:
                    results['resources'][resource_type] = result

                completed += 1
                if progress_callback:
                    progress_callback(
                        completed,
                        total_tasks,
                        f"Queried {resource_type}"
                    )

            # Rate limit between batches
            if i + self.RATE_LIMIT < len(tasks):
                await asyncio.sleep(self.RATE_LIMIT_WINDOW)

        # Cache results for 15 minutes
        if self.cache_manager and hasattr(self.cache_manager, 'query_cache'):
            from ..cache.redis_cache import QueryType
            await self.cache_manager.query_cache.set(cache_key, results, QueryType.OPERATIONAL)

        return results

    async def _query_resource_type(
        self,
        organization_id: str,
        resource_type: str,
        snapshot_id: str
    ) -> dict[str, Any]:
        """Query a specific resource type with pagination.

        Args:
            organization_id: Organization ID
            resource_type: Type of resource to query
            snapshot_id: Snapshot ID for tracking

        Returns:
            Resource data with metadata
        """
        async with self.semaphore:
            await self._enforce_rate_limit()

            start_time = datetime.utcnow()
            all_data = []
            page = 1
            total_pages = 1

            try:
                while page <= total_pages:
                    # Make API request based on resource type
                    response = await self._make_api_request(
                        organization_id=organization_id,
                        resource_type=resource_type,
                        page=page
                    )

                    if response and 'data' in response:
                        all_data.extend(response['data'])

                        # Get pagination info
                        meta = response.get('meta', {})
                        total_pages = meta.get('total-pages', 1)
                        page += 1

                        # Log API query to database
                        await self._log_api_query(
                            snapshot_id=snapshot_id,
                            endpoint=f"/organizations/{organization_id}/{resource_type}",
                            resource_type=resource_type,
                            response_status=200,
                            duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
                        )
                    else:
                        break

                return {
                    'type': resource_type,
                    'count': len(all_data),
                    'data': all_data,
                    'query_time': (datetime.utcnow() - start_time).total_seconds()
                }

            except Exception as e:
                logger.error(f"Error querying {resource_type}: {e}")

                # Log failed query
                await self._log_api_query(
                    snapshot_id=snapshot_id,
                    endpoint=f"/organizations/{organization_id}/{resource_type}",
                    resource_type=resource_type,
                    error_message=str(e),
                    duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
                )

                raise

    async def _make_api_request(
        self,
        organization_id: str,
        resource_type: str,
        page: int = 1
    ) -> Optional[dict]:
        """Make API request to IT Glue based on resource type.

        Args:
            organization_id: Organization ID
            resource_type: Type of resource
            page: Page number for pagination

        Returns:
            API response data
        """
        params = {
            'filter[organization_id]': organization_id,
            'page[number]': page,
            'page[size]': 100  # Max page size for IT Glue
        }

        # Map resource types to IT Glue client methods
        method_map = {
            'configurations': self.itglue_client.get_configurations,
            'flexible_assets': self.itglue_client.get_flexible_assets,
            'contacts': self.itglue_client.get_contacts,
            'locations': self.itglue_client.get_locations,
            'documents': self.itglue_client.get_documents,
            'passwords': self.itglue_client.get_passwords,
            'domains': self.itglue_client.get_domains,
            'networks': self.itglue_client.get_networks
        }

        method = method_map.get(resource_type)
        if not method:
            logger.warning(f"No method mapped for resource type: {resource_type}")
            return None

        try:
            return await method(**params)
        except Exception as e:
            logger.error(f"API request failed for {resource_type}: {e}")
            raise

    async def _enforce_rate_limit(self):
        """Enforce rate limiting to stay within IT Glue API limits."""
        current_time = asyncio.get_event_loop().time()

        # Remove old request times outside the window
        self.request_times = [
            t for t in self.request_times
            if current_time - t < self.RATE_LIMIT_WINDOW
        ]

        # If at rate limit, wait
        if len(self.request_times) >= self.RATE_LIMIT:
            sleep_time = self.RATE_LIMIT_WINDOW - (current_time - self.request_times[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

        # Record this request
        self.request_times.append(current_time)

    async def _log_api_query(
        self,
        snapshot_id: str,
        endpoint: str,
        resource_type: str,
        response_status: Optional[int] = None,
        error_message: Optional[str] = None,
        duration_ms: float = 0
    ):
        """Log API query to database for tracking.

        Args:
            snapshot_id: Snapshot ID
            endpoint: API endpoint called
            resource_type: Type of resource
            response_status: HTTP response status
            error_message: Error message if failed
            duration_ms: Query duration in milliseconds
        """
        query = """
            INSERT INTO api_queries
            (id, snapshot_id, endpoint, resource_type, response_status,
             error_message, duration_ms, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """

        try:
            async with db_manager.acquire() as conn:
                await conn.execute(
                    query,
                    uuid.uuid4(),
                    uuid.UUID(snapshot_id),
                    endpoint,
                    resource_type,
                    response_status,
                    error_message,
                    duration_ms,
                    datetime.utcnow()
                )
        except Exception as e:
            logger.error(f"Failed to log API query: {e}")

    async def query_with_retry(
        self,
        func: Callable,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        **kwargs
    ) -> Any:
        """Execute a query with exponential backoff retry.

        Args:
            func: Async function to call
            max_retries: Maximum number of retries
            backoff_factor: Exponential backoff factor
            **kwargs: Arguments to pass to func

        Returns:
            Query result
        """
        last_exception = None

        for attempt in range(max_retries):
            try:
                return await func(**kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    sleep_time = backoff_factor ** attempt
                    logger.warning(
                        f"Query failed (attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {sleep_time}s: {e}"
                    )
                    await asyncio.sleep(sleep_time)
                else:
                    logger.error(f"Query failed after {max_retries} attempts: {e}")

        raise last_exception
