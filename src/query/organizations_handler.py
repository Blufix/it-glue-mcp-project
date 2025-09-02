"""Handler for organization queries with fuzzy matching."""

import hashlib
import logging
import time
from difflib import SequenceMatcher
from typing import Any, Optional

from src.cache.manager import CacheManager
from src.services.itglue.client import ITGlueClient
from src.services.itglue.models import Organization

logger = logging.getLogger(__name__)

# Performance requirement: <500ms response time
MAX_RESPONSE_TIME_MS = 500


class OrganizationsHandler:
    """Handles queries related to IT Glue organizations with performance optimization."""

    def __init__(
        self,
        itglue_client: ITGlueClient,
        cache_manager: Optional[CacheManager] = None
    ):
        """Initialize organizations handler.

        Args:
            itglue_client: IT Glue API client
            cache_manager: Optional cache manager
        """
        self.client = itglue_client
        self.cache = cache_manager
        self._org_cache = {}  # In-memory cache for performance
        self._cache_timestamp = 0
        self._cache_ttl = 300  # 5 minutes

    async def list_all_organizations(
        self,
        org_type: Optional[str] = None,
        limit: int = 100
    ) -> dict[str, Any]:
        """List all organizations with optional type filter.

        Args:
            org_type: Optional organization type filter (e.g., 'Customer', 'Vendor')
            limit: Maximum number of results

        Returns:
            Dictionary with organization information
        """
        start_time = time.time()

        # Check cache first
        cache_key = f"organizations:all:{org_type or 'all'}"
        if self.cache and hasattr(self.cache, 'query_cache'):
            cached = await self.cache.query_cache.get(cache_key)
            if cached:
                response_time_ms = (time.time() - start_time) * 1000
                logger.debug(f"Returning cached organizations in {response_time_ms:.2f}ms")
                cached["response_time_ms"] = response_time_ms
                return cached

        try:
            # Get organizations
            organizations = await self._get_organizations_cached()

            # Filter by type if specified
            if org_type:
                type_lower = org_type.lower()
                filtered_orgs = [
                    org for org in organizations
                    if type_lower in (org.organization_type or "").lower()
                ]
            else:
                filtered_orgs = organizations

            # Sort by name
            filtered_orgs.sort(key=lambda o: o.name)

            # Format response
            result = {
                "success": True,
                "organization_type": org_type,
                "count": len(filtered_orgs),
                "organizations": [
                    self._format_organization(org)
                    for org in filtered_orgs[:limit]
                ]
            }

            # Calculate response time
            response_time_ms = (time.time() - start_time) * 1000
            result["response_time_ms"] = response_time_ms

            # Ensure we meet performance requirement
            if response_time_ms > MAX_RESPONSE_TIME_MS:
                logger.warning(f"Response time {response_time_ms:.2f}ms exceeds {MAX_RESPONSE_TIME_MS}ms requirement")

            # Cache for 5 minutes
            if self.cache and hasattr(self.cache, 'query_cache'):
                from ..cache.redis_cache import QueryType
                await self.cache.query_cache.set(cache_key, result, QueryType.OPERATIONAL)

            logger.info(f"Listed {len(result['organizations'])} organizations in {response_time_ms:.2f}ms")
            return result

        except Exception as e:
            logger.error(f"Failed to list organizations: {e}")
            response_time_ms = (time.time() - start_time) * 1000
            return {
                "success": False,
                "error": str(e),
                "organizations": [],
                "response_time_ms": response_time_ms
            }

    async def find_organization(
        self,
        name: str,
        use_fuzzy: bool = True
    ) -> dict[str, Any]:
        """Find a specific organization by name with fuzzy matching.

        Args:
            name: Organization name to search for
            use_fuzzy: Whether to use fuzzy matching

        Returns:
            Dictionary with matching organization details
        """
        start_time = time.time()

        # Check cache first
        cache_key = f"organizations:find:{self._hash_query(name)}"
        if self.cache and hasattr(self.cache, 'query_cache'):
            cached = await self.cache.query_cache.get(cache_key)
            if cached:
                response_time_ms = (time.time() - start_time) * 1000
                logger.debug(f"Returning cached organization in {response_time_ms:.2f}ms")
                cached["response_time_ms"] = response_time_ms
                return cached

        try:
            # Get all organizations
            organizations = await self._get_organizations_cached()

            # Try exact match first
            name_lower = name.lower()
            exact_match = None

            for org in organizations:
                if org.name.lower() == name_lower:
                    exact_match = org
                    break

            if exact_match:
                result = {
                    "success": True,
                    "query": name,
                    "match_type": "exact",
                    "organization": self._format_organization_detailed(exact_match)
                }
            elif use_fuzzy:
                # Try fuzzy matching
                best_match = self._find_best_match(name, organizations)

                if best_match:
                    result = {
                        "success": True,
                        "query": name,
                        "match_type": "fuzzy",
                        "match_score": best_match[1],
                        "organization": self._format_organization_detailed(best_match[0])
                    }
                else:
                    # Provide suggestions
                    suggestions = self._get_suggestions(name, organizations)
                    result = {
                        "success": False,
                        "query": name,
                        "error": f"Organization '{name}' not found",
                        "suggestions": suggestions
                    }
            else:
                result = {
                    "success": False,
                    "query": name,
                    "error": f"Organization '{name}' not found (exact match required)"
                }

            # Calculate response time
            response_time_ms = (time.time() - start_time) * 1000
            result["response_time_ms"] = response_time_ms

            # Cache for 5 minutes
            if self.cache and result.get("success") and hasattr(self.cache, 'query_cache'):
                from ..cache.redis_cache import QueryType
                await self.cache.query_cache.set(cache_key, result, QueryType.OPERATIONAL)

            logger.info(f"Found organization '{name}' in {response_time_ms:.2f}ms")
            return result

        except Exception as e:
            logger.error(f"Failed to find organization '{name}': {e}")
            response_time_ms = (time.time() - start_time) * 1000
            return {
                "success": False,
                "error": str(e),
                "query": name,
                "response_time_ms": response_time_ms
            }

    async def list_customers(self, limit: int = 100) -> dict[str, Any]:
        """List all customer organizations.

        Args:
            limit: Maximum number of results

        Returns:
            Dictionary with customer organizations
        """
        return await self.list_all_organizations(org_type="Customer", limit=limit)

    async def list_vendors(self, limit: int = 100) -> dict[str, Any]:
        """List all vendor organizations.

        Args:
            limit: Maximum number of results

        Returns:
            Dictionary with vendor organizations
        """
        return await self.list_all_organizations(org_type="Vendor", limit=limit)

    async def search_organizations(
        self,
        query: str,
        limit: int = 50
    ) -> dict[str, Any]:
        """Search organizations by query.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            Dictionary with matching organizations
        """
        start_time = time.time()

        try:
            # Get all organizations
            organizations = await self._get_organizations_cached()

            # Search across name, type, and status
            query_lower = query.lower()
            query_words = query_lower.split()

            matches = []
            for org in organizations:
                score = 0

                # Check name
                name_lower = org.name.lower()
                for word in query_words:
                    if word in name_lower:
                        score += 2

                # Check type
                if org.organization_type:
                    type_lower = org.organization_type.lower()
                    for word in query_words:
                        if word in type_lower:
                            score += 1

                # Check status
                if org.organization_status:
                    status_lower = org.organization_status.lower()
                    for word in query_words:
                        if word in status_lower:
                            score += 0.5

                # Add fuzzy matching score
                name_similarity = SequenceMatcher(None, query_lower, name_lower).ratio()
                score += name_similarity * 3

                if score > 0:
                    matches.append((org, score))

            # Sort by relevance
            matches.sort(key=lambda x: x[1], reverse=True)

            # Format results
            result = {
                "success": True,
                "query": query,
                "count": len(matches),
                "organizations": [
                    {
                        **self._format_organization(org),
                        "relevance_score": score
                    }
                    for org, score in matches[:limit]
                ]
            }

            # Calculate response time
            response_time_ms = (time.time() - start_time) * 1000
            result["response_time_ms"] = response_time_ms

            logger.info(f"Found {len(matches)} organizations matching '{query}' in {response_time_ms:.2f}ms")
            return result

        except Exception as e:
            logger.error(f"Failed to search organizations for '{query}': {e}")
            response_time_ms = (time.time() - start_time) * 1000
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "organizations": [],
                "response_time_ms": response_time_ms
            }

    async def get_organization_stats(self) -> dict[str, Any]:
        """Get statistics about organizations.

        Returns:
            Dictionary with organization statistics
        """
        start_time = time.time()

        # Check cache first
        cache_key = "organizations:stats"
        if self.cache and hasattr(self.cache, 'query_cache'):
            cached = await self.cache.query_cache.get(cache_key)
            if cached:
                response_time_ms = (time.time() - start_time) * 1000
                cached["response_time_ms"] = response_time_ms
                return cached

        try:
            # Get all organizations
            organizations = await self._get_organizations_cached()

            # Calculate statistics
            type_counts = {}
            status_counts = {}

            for org in organizations:
                # Count by type
                org_type = org.organization_type or "Unknown"
                type_counts[org_type] = type_counts.get(org_type, 0) + 1

                # Count by status
                org_status = org.organization_status or "Unknown"
                status_counts[org_status] = status_counts.get(org_status, 0) + 1

            result = {
                "success": True,
                "total_organizations": len(organizations),
                "by_type": type_counts,
                "by_status": status_counts,
                "customers": type_counts.get("Customer", 0),
                "vendors": type_counts.get("Vendor", 0),
                "active": status_counts.get("Active", 0)
            }

            # Calculate response time
            response_time_ms = (time.time() - start_time) * 1000
            result["response_time_ms"] = response_time_ms

            # Cache for 10 minutes
            if self.cache and hasattr(self.cache, 'query_cache'):
                from ..cache.redis_cache import QueryType
                await self.cache.query_cache.set(cache_key, result, QueryType.OPERATIONAL)

            logger.info(f"Generated organization statistics in {response_time_ms:.2f}ms")
            return result

        except Exception as e:
            logger.error(f"Failed to get organization statistics: {e}")
            response_time_ms = (time.time() - start_time) * 1000
            return {
                "success": False,
                "error": str(e),
                "response_time_ms": response_time_ms
            }

    async def _get_organizations_cached(self) -> list[Organization]:
        """Get organizations with in-memory caching for performance.

        Returns:
            List of organizations
        """
        current_time = time.time()

        # Check in-memory cache
        if self._org_cache and (current_time - self._cache_timestamp) < self._cache_ttl:
            return self._org_cache

        # Fetch from API
        organizations = await self.client.get_organizations()

        # Update in-memory cache
        self._org_cache = organizations
        self._cache_timestamp = current_time

        return organizations

    def _format_organization(self, org: Organization) -> dict[str, Any]:
        """Format organization for response.

        Args:
            org: Organization object

        Returns:
            Formatted organization dictionary
        """
        return {
            "id": org.id,
            "name": org.name,
            "type": org.organization_type,
            "status": org.organization_status
        }

    def _format_organization_detailed(self, org: Organization) -> dict[str, Any]:
        """Format organization with detailed information.

        Args:
            org: Organization object

        Returns:
            Detailed organization dictionary
        """
        return {
            "id": org.id,
            "name": org.name,
            "type": org.organization_type,
            "status": org.organization_status,
            "created_at": org.created_at.isoformat() if org.created_at else None,
            "updated_at": org.updated_at.isoformat() if org.updated_at else None,
            "attributes": org.attributes  # Include all attributes
        }

    def _find_best_match(
        self,
        query: str,
        organizations: list[Organization]
    ) -> Optional[tuple]:
        """Find best matching organization using fuzzy matching.

        Args:
            query: Search query
            organizations: List of organizations

        Returns:
            Tuple of (organization, score) or None
        """
        if not organizations:
            return None

        query_lower = query.lower()
        best_match = None
        best_score = 0

        for org in organizations:
            # Calculate similarity score
            score = SequenceMatcher(
                None,
                query_lower,
                org.name.lower()
            ).ratio()

            # Boost score for partial exact matches
            if query_lower in org.name.lower():
                score += 0.2

            if score > best_score and score > 0.6:  # Minimum threshold
                best_score = score
                best_match = (org, score)

        return best_match

    def _get_suggestions(
        self,
        query: str,
        organizations: list[Organization],
        max_suggestions: int = 5
    ) -> list[str]:
        """Get organization name suggestions.

        Args:
            query: Search query
            organizations: List of organizations
            max_suggestions: Maximum number of suggestions

        Returns:
            List of suggested organization names
        """
        query_lower = query.lower()
        suggestions = []

        for org in organizations:
            name_lower = org.name.lower()

            # Check for partial matches
            if any(word in name_lower for word in query_lower.split()):
                suggestions.append(org.name)

            # Check for common variations
            elif query_lower[0] == name_lower[0]:  # Same first letter
                similarity = SequenceMatcher(None, query_lower, name_lower).ratio()
                if similarity > 0.4:
                    suggestions.append(org.name)

        # Remove duplicates and limit
        seen = set()
        unique_suggestions = []
        for s in suggestions:
            if s not in seen:
                seen.add(s)
                unique_suggestions.append(s)
                if len(unique_suggestions) >= max_suggestions:
                    break

        return unique_suggestions

    def _hash_query(self, query: str) -> str:
        """Create a hash of the query for caching.

        Args:
            query: Search query

        Returns:
            Hash string
        """
        return hashlib.md5(query.lower().encode()).hexdigest()[:8]
