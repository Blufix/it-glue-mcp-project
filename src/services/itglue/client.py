"""IT Glue API client with rate limiting and retry logic."""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Type, TypeVar
from datetime import datetime, timedelta
import aiohttp
from aiohttp import ClientError, ClientTimeout
import backoff

from src.config.settings import settings
from .models import (
    ITGlueModel,
    Organization,
    Configuration,
    FlexibleAsset,
    Password,
    Document,
    Contact,
    Location
)

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=ITGlueModel)


class RateLimiter:
    """Rate limiter for API requests."""
    
    def __init__(self, max_requests: int, time_window: int = 60):
        """Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        self._lock = asyncio.Lock()
        
    async def acquire(self):
        """Acquire permission to make a request."""
        async with self._lock:
            now = datetime.now()
            
            # Remove old requests outside the time window
            cutoff = now - timedelta(seconds=self.time_window)
            self.requests = [req for req in self.requests if req > cutoff]
            
            # Check if we can make a request
            if len(self.requests) >= self.max_requests:
                # Calculate wait time
                oldest = self.requests[0]
                wait_time = (oldest + timedelta(seconds=self.time_window) - now).total_seconds()
                
                if wait_time > 0:
                    logger.debug(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                    await asyncio.sleep(wait_time)
                    
                    # Clean up again after waiting
                    cutoff = datetime.now() - timedelta(seconds=self.time_window)
                    self.requests = [req for req in self.requests if req > cutoff]
            
            # Record this request
            self.requests.append(datetime.now())


class ITGlueClient:
    """IT Glue API client."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        rate_limit: Optional[int] = None
    ):
        """Initialize IT Glue client.
        
        Args:
            api_key: IT Glue API key
            api_url: IT Glue API URL
            rate_limit: Maximum requests per minute
        """
        self.api_key = api_key or settings.it_glue_api_key
        self.api_url = (api_url or settings.it_glue_api_url).rstrip('/')
        
        if not self.api_key:
            raise ValueError("IT Glue API key is required")
        
        self.rate_limiter = RateLimiter(
            max_requests=rate_limit or getattr(settings, 'itglue_rate_limit', None) or 100
        )
        
        self.session: Optional[aiohttp.ClientSession] = None
        self._timeout = ClientTimeout(total=30)
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
        
    async def connect(self):
        """Create HTTP session."""
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers={
                    "x-api-key": self.api_key,
                    "Content-Type": "application/vnd.api+json",
                    "Accept": "application/vnd.api+json"
                },
                timeout=self._timeout
            )
            logger.info("IT Glue client session created")
            
    async def disconnect(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("IT Glue client session closed")
            
    @backoff.on_exception(
        backoff.expo,
        (ClientError, asyncio.TimeoutError),
        max_tries=3,
        max_time=30
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make API request with retry logic.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            data: Request body data
            
        Returns:
            API response data
        """
        if not self.session:
            await self.connect()
            
        # Apply rate limiting
        await self.rate_limiter.acquire()
        
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        
        logger.debug(f"IT Glue API {method} {url}")
        
        try:
            async with self.session.request(
                method=method,
                url=url,
                params=params,
                json=data
            ) as response:
                response_data = await response.json()
                
                if response.status >= 400:
                    error_msg = response_data.get("errors", [{}])[0].get(
                        "detail",
                        f"API error: {response.status}"
                    )
                    logger.error(f"IT Glue API error: {error_msg}")
                    raise ClientError(error_msg)
                
                return response_data
                
        except asyncio.TimeoutError:
            logger.error(f"IT Glue API timeout: {url}")
            raise
            
        except Exception as e:
            logger.error(f"IT Glue API request failed: {e}")
            raise
            
    async def get(
        self,
        endpoint: str,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """GET request.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            Response data
        """
        return await self._request("GET", endpoint, params=params)
        
    async def post(
        self,
        endpoint: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """POST request.
        
        Args:
            endpoint: API endpoint
            data: Request data
            
        Returns:
            Response data
        """
        return await self._request("POST", endpoint, data=data)
        
    async def patch(
        self,
        endpoint: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """PATCH request.
        
        Args:
            endpoint: API endpoint
            data: Request data
            
        Returns:
            Response data
        """
        return await self._request("PATCH", endpoint, data=data)
        
    async def delete(self, endpoint: str) -> Dict[str, Any]:
        """DELETE request.
        
        Args:
            endpoint: API endpoint
            
        Returns:
            Response data
        """
        return await self._request("DELETE", endpoint)
        
    async def get_all_pages(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        max_pages: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get all pages of results.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            max_pages: Maximum number of pages to fetch
            
        Returns:
            All results from all pages
        """
        if params is None:
            params = {}
            
        # Set page size
        if "page[size]" not in params:
            params["page[size]"] = 1000
            
        all_data = []
        page = 1
        
        while True:
            params["page[number]"] = page
            
            response = await self.get(endpoint, params)
            
            data = response.get("data", [])
            all_data.extend(data)
            
            # Check if there are more pages
            links = response.get("links", {})
            if not links.get("next"):
                break
                
            page += 1
            
            if max_pages and page > max_pages:
                logger.warning(f"Reached max pages limit: {max_pages}")
                break
                
        logger.info(f"Fetched {len(all_data)} items from {endpoint}")
        return all_data
        
    # Entity-specific methods
    
    async def get_organizations(
        self,
        filters: Optional[Dict] = None
    ) -> List[Organization]:
        """Get organizations.
        
        Args:
            filters: Optional filters
            
        Returns:
            List of organizations
        """
        params = {}
        if filters:
            for key, value in filters.items():
                params[f"filter[{key}]"] = value
                
        data = await self.get_all_pages("organizations", params)
        return [Organization(**item) for item in data]
        
    async def get_organization(self, org_id: str) -> Organization:
        """Get single organization.
        
        Args:
            org_id: Organization ID
            
        Returns:
            Organization
        """
        response = await self.get(f"organizations/{org_id}")
        return Organization(**response["data"])
        
    async def get_configurations(
        self,
        org_id: Optional[str] = None,
        filters: Optional[Dict] = None
    ) -> List[Configuration]:
        """Get configurations.
        
        Args:
            org_id: Organization ID (optional)
            filters: Optional filters
            
        Returns:
            List of configurations
        """
        endpoint = f"organizations/{org_id}/relationships/configurations" if org_id else "configurations"
        
        params = {}
        if filters:
            for key, value in filters.items():
                params[f"filter[{key}]"] = value
                
        data = await self.get_all_pages(endpoint, params)
        return [Configuration(**item) for item in data]
        
    async def get_flexible_assets(
        self,
        org_id: Optional[str] = None,
        asset_type_id: Optional[str] = None,
        filters: Optional[Dict] = None
    ) -> List[FlexibleAsset]:
        """Get flexible assets.
        
        Args:
            org_id: Organization ID (optional)
            asset_type_id: Asset type ID (optional)
            filters: Optional filters
            
        Returns:
            List of flexible assets
        """
        params = {}
        
        if asset_type_id:
            params["filter[flexible-asset-type-id]"] = asset_type_id
            
        if filters:
            for key, value in filters.items():
                params[f"filter[{key}]"] = value
                
        endpoint = f"organizations/{org_id}/relationships/flexible-assets" if org_id else "flexible-assets"
        
        data = await self.get_all_pages(endpoint, params)
        return [FlexibleAsset(**item) for item in data]
        
    async def get_passwords(
        self,
        org_id: Optional[str] = None,
        filters: Optional[Dict] = None
    ) -> List[Password]:
        """Get passwords.
        
        Args:
            org_id: Organization ID (optional)
            filters: Optional filters
            
        Returns:
            List of passwords
        """
        endpoint = f"organizations/{org_id}/relationships/passwords" if org_id else "passwords"
        
        params = {}
        if filters:
            for key, value in filters.items():
                params[f"filter[{key}]"] = value
                
        data = await self.get_all_pages(endpoint, params)
        return [Password(**item) for item in data]
        
    async def get_documents(
        self,
        org_id: Optional[str] = None,
        filters: Optional[Dict] = None
    ) -> List[Document]:
        """Get documents.
        
        Args:
            org_id: Organization ID (optional)
            filters: Optional filters
            
        Returns:
            List of documents
        """
        endpoint = f"organizations/{org_id}/relationships/documents" if org_id else "documents"
        
        params = {}
        if filters:
            for key, value in filters.items():
                params[f"filter[{key}]"] = value
                
        data = await self.get_all_pages(endpoint, params)
        return [Document(**item) for item in data]
        
    async def get_contacts(
        self,
        org_id: Optional[str] = None,
        filters: Optional[Dict] = None
    ) -> List[Contact]:
        """Get contacts.
        
        Args:
            org_id: Organization ID (optional)
            filters: Optional filters
            
        Returns:
            List of contacts
        """
        endpoint = f"organizations/{org_id}/relationships/contacts" if org_id else "contacts"
        
        params = {}
        if filters:
            for key, value in filters.items():
                params[f"filter[{key}]"] = value
                
        data = await self.get_all_pages(endpoint, params)
        return [Contact(**item) for item in data]
        
    async def get_locations(
        self,
        org_id: Optional[str] = None,
        filters: Optional[Dict] = None
    ) -> List[Location]:
        """Get locations.
        
        Args:
            org_id: Organization ID (optional)
            filters: Optional filters
            
        Returns:
            List of locations
        """
        endpoint = f"organizations/{org_id}/relationships/locations" if org_id else "locations"
        
        params = {}
        if filters:
            for key, value in filters.items():
                params[f"filter[{key}]"] = value
                
        data = await self.get_all_pages(endpoint, params)
        return [Location(**item) for item in data]