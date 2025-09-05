"""IT Glue API client with rate limiting and retry logic."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Optional, TypeVar

import aiohttp
import backoff
from aiohttp import ClientError, ClientTimeout

from src.config.settings import settings

from .models import (
    Configuration,
    Contact,
    Document,
    FlexibleAsset,
    ITGlueModel,
    Location,
    Organization,
    Password,
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
        self.api_key = api_key or settings.itglue_api_key
        self.api_url = (api_url or settings.itglue_api_url).rstrip('/')

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
        params: Optional[dict] = None,
        data: Optional[dict] = None
    ) -> dict[str, Any]:
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
        params: Optional[dict] = None
    ) -> dict[str, Any]:
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
        data: dict[str, Any]
    ) -> dict[str, Any]:
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
        data: dict[str, Any]
    ) -> dict[str, Any]:
        """PATCH request.

        Args:
            endpoint: API endpoint
            data: Request data

        Returns:
            Response data
        """
        return await self._request("PATCH", endpoint, data=data)

    async def delete(self, endpoint: str) -> dict[str, Any]:
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
        params: Optional[dict] = None,
        max_pages: Optional[int] = None
    ) -> list[dict[str, Any]]:
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
        filters: Optional[dict] = None
    ) -> list[Organization]:
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

    async def get_organization(self, org_id: str) -> Optional[dict]:
        """Get single organization.

        Args:
            org_id: Organization ID

        Returns:
            Organization data dictionary
        """
        try:
            response = await self.get(f"organizations/{org_id}")
            return response
        except Exception as e:
            logger.error(f"Failed to get organization {org_id}: {e}")
            return None

    async def get_configurations(
        self,
        org_id: Optional[str] = None,
        filters: Optional[dict] = None
    ) -> list[Configuration]:
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
        filters: Optional[dict] = None
    ) -> list[FlexibleAsset]:
        """Get flexible assets.

        NOTE: IT Glue API requires at least one filter parameter for flexible assets.
        If neither org_id nor asset_type_id is provided, this will return an empty list.

        Args:
            org_id: Organization ID (optional but recommended)
            asset_type_id: Asset type ID (optional but recommended)
            filters: Optional additional filters

        Returns:
            List of flexible assets
        """
        params = {}

        # Add organization filter if provided
        if org_id:
            params["filter[organization-id]"] = org_id

        # Add asset type filter if provided
        if asset_type_id:
            params["filter[flexible-asset-type-id]"] = asset_type_id

        # Add additional filters
        if filters:
            for key, value in filters.items():
                params[f"filter[{key}]"] = value

        # IT Glue flexible assets endpoint requires filters, so return empty if none provided
        if not params:
            logger.warning("No filters provided for flexible assets - returning empty list")
            return []

        # Always use the global flexible_assets endpoint with filters
        # Note: Must use underscore, not dash! flexible_assets not flexible-assets
        endpoint = "flexible_assets"

        try:
            data = await self.get_all_pages(endpoint, params)
            return [FlexibleAsset(**item) for item in data]
        except Exception as e:
            # IT Glue API returns 422 for flexible assets without proper filters
            if "422" in str(e):
                logger.warning(f"Flexible assets API returned 422 - likely missing required filters: {params}")
                return []
            raise

    async def get_all_flexible_assets_for_org(
        self,
        org_id: str,
        limit_per_type: int = 100
    ) -> list[FlexibleAsset]:
        """Get all flexible assets for an organization by iterating through asset types.

        This method works around IT Glue API limitations by:
        1. Getting all enabled asset types
        2. Querying each type specifically for the organization
        3. Combining results

        Args:
            org_id: Organization ID
            limit_per_type: Maximum assets per type to fetch

        Returns:
            List of all flexible assets for the organization
        """
        all_assets = []

        try:
            # Get all asset types
            asset_types = await self.get_flexible_asset_types(include_fields=False)
            enabled_types = [at for at in asset_types if at.enabled]

            logger.info(f"Checking {len(enabled_types)} enabled asset types for org {org_id}")

            # Check each asset type for assets in this organization
            for asset_type in enabled_types:
                try:
                    assets = await self.get_flexible_assets(
                        org_id=org_id,
                        asset_type_id=asset_type.id
                    )
                    
                    if assets:
                        all_assets.extend(assets[:limit_per_type])
                        logger.debug(f"Found {len(assets)} {asset_type.name} assets")

                except Exception as e:
                    logger.debug(f"No {asset_type.name} assets or error: {e}")
                    continue

            logger.info(f"Found {len(all_assets)} total flexible assets for org {org_id}")
            return all_assets

        except Exception as e:
            logger.error(f"Failed to get flexible assets for org {org_id}: {e}")
            return []

    async def get_passwords(
        self,
        org_id: Optional[str] = None,
        filters: Optional[dict] = None
    ) -> list[Password]:
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
        filters: Optional[dict] = None,
        include_folders: bool = False,
        folder_id: Optional[str] = None
    ) -> list[Document]:
        """Get API-created documents.

        NOTE: This only returns documents created via the IT Glue API.
        File uploads (Word docs, PDFs) made through the IT Glue UI are not
        accessible via the public API.

        Args:
            org_id: Organization ID (optional)
            filters: Optional filters
            include_folders: Whether to include documents in folders (default: False for root only)
            folder_id: Specific folder ID to filter by (optional)

        Returns:
            List of documents
        """
        # Global documents endpoint returns 404, must use organization-specific endpoint
        if org_id:
            endpoint = f"organizations/{org_id}/relationships/documents"
            params = {}
            
            # Add folder filtering based on parameters using exact syntax provided
            if folder_id:
                # Filter for documents in a specific folder: filter[document_folder_id]=<folder_id>
                params["filter[document_folder_id]"] = folder_id
            elif include_folders:
                # All documents including folders: filter[document_folder_id][ne]=null
                params["filter[document_folder_id][ne]"] = "null"
            else:
                # Root documents only: filter[document_folder_id]=null (without the null filter, might return all)
                # We'll test both approaches - with and without explicit null filter
                pass  # Default behavior - let's see what API returns without folder filter
            
            # Add other filters
            if filters:
                for key, value in filters.items():
                    params[f"filter[{key}]"] = value

            data = await self.get_all_pages(endpoint, params)
            return [Document(**item) for item in data]
        else:
            # Need to iterate through all organizations
            logger.warning("Global documents endpoint not available, fetching from all organizations")
            all_documents = []
            orgs = await self.get_organizations()

            for org in orgs:
                try:
                    org_docs = await self.get_documents(
                        org_id=org.id, 
                        filters=filters,
                        include_folders=include_folders,
                        folder_id=folder_id
                    )
                    all_documents.extend(org_docs)
                except Exception as e:
                    logger.error(f"Failed to get documents for org {org.id}: {e}")

            return all_documents

    async def get_contacts(
        self,
        org_id: Optional[str] = None,
        filters: Optional[dict] = None
    ) -> list[Contact]:
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
        filters: Optional[dict] = None
    ) -> list[Location]:
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

    async def get_flexible_asset_types(
        self,
        include_fields: bool = True
    ) -> list["FlexibleAssetType"]:
        """Get all flexible asset types with their field definitions.

        Args:
            include_fields: Whether to include field definitions

        Returns:
            List of FlexibleAssetType objects
        """
        from .models import FlexibleAssetType

        endpoint = "flexible_asset_types"
        params = {}

        if include_fields:
            params["include"] = "flexible_asset_fields"

        # Get all asset types
        response = await self.get(endpoint, params)
        data = response.get("data", [])

        # If fields are included, they'll be in the "included" section
        included_fields = {}
        if include_fields and "included" in response:
            for field_data in response.get("included", []):
                if field_data.get("type") == "flexible-asset-fields":
                    asset_type_id = field_data.get("attributes", {}).get("flexible-asset-type-id")
                    if asset_type_id:
                        if asset_type_id not in included_fields:
                            included_fields[asset_type_id] = []
                        included_fields[asset_type_id].append(field_data)

        # Build FlexibleAssetType objects with their fields
        asset_types = []
        for item in data:
            # Add fields to relationships if they exist
            type_id = item.get("id")
            if type_id and str(type_id) in included_fields:
                if "relationships" not in item:
                    item["relationships"] = {}
                item["relationships"]["flexible-asset-fields"] = {
                    "data": included_fields[str(type_id)]
                }

            asset_types.append(FlexibleAssetType(**item))

        logger.info(f"Retrieved {len(asset_types)} flexible asset types")
        return asset_types

    async def get_flexible_asset_type_by_name(
        self,
        name: str
    ) -> Optional["FlexibleAssetType"]:
        """Get a specific flexible asset type by name.

        Args:
            name: Name of the asset type (e.g., "SSL Certificate", "Warranty")

        Returns:
            FlexibleAssetType object or None if not found
        """
        asset_types = await self.get_flexible_asset_types(include_fields=True)

        # Case-insensitive search
        name_lower = name.lower()
        for asset_type in asset_types:
            if asset_type.name.lower() == name_lower:
                return asset_type

        # Try partial match if exact match not found
        for asset_type in asset_types:
            if name_lower in asset_type.name.lower():
                return asset_type

        return None

    async def get_flexible_asset_fields(
        self,
        asset_type_id: str
    ) -> list["FlexibleAssetField"]:
        """Get field definitions for a specific flexible asset type.

        Args:
            asset_type_id: ID of the flexible asset type

        Returns:
            List of FlexibleAssetField objects
        """
        from .models import FlexibleAssetField

        endpoint = f"flexible_asset_types/{asset_type_id}/relationships/flexible_asset_fields"

        data = await self.get_all_pages(endpoint)
        return [FlexibleAssetField(**item) for item in data]

    async def get_domains(
        self,
        organization_id: Optional[str] = None,
        **kwargs
    ) -> list[dict]:
        """Get domains from IT Glue.

        Args:
            organization_id: Filter by organization (optional)
            **kwargs: Additional filter parameters

        Returns:
            List of domain dictionaries
        """
        endpoint = "domains"
        params = {}

        if organization_id:
            params["filter[organization_id]"] = organization_id

        params.update(kwargs)

        data = await self.get_all_pages(endpoint, params)
        return data

    async def get_networks(
        self,
        organization_id: Optional[str] = None,
        **kwargs
    ) -> list[dict]:
        """Get networks from IT Glue.

        Args:
            organization_id: Filter by organization (optional)
            **kwargs: Additional filter parameters

        Returns:
            List of network dictionaries
        """
        endpoint = "networks"
        params = {}

        if organization_id:
            params["filter[organization_id]"] = organization_id

        params.update(kwargs)

        data = await self.get_all_pages(endpoint, params)
        return data

    async def create_document(
        self,
        document_data: dict
    ) -> Optional[dict]:
        """Create a new document in IT Glue.

        Args:
            document_data: Document data in IT Glue format

        Returns:
            Created document data or None if failed
        """
        endpoint = "documents"

        try:
            response = await self._request(
                "POST",
                endpoint,
                data=document_data
            )
            return response
        except Exception as e:
            logger.error(f"Failed to create document: {e}")
            return None
