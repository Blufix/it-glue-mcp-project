"""Handler for location-based queries."""

import logging
from difflib import SequenceMatcher
from typing import Any, Optional

from src.cache.manager import CacheManager
from src.services.itglue.client import ITGlueClient
from src.services.itglue.models import Location

logger = logging.getLogger(__name__)


class LocationsHandler:
    """Handles queries related to locations and sites."""

    def __init__(
        self,
        itglue_client: ITGlueClient,
        cache_manager: Optional[CacheManager] = None
    ):
        """Initialize locations handler.

        Args:
            itglue_client: IT Glue API client
            cache_manager: Optional cache manager
        """
        self.client = itglue_client
        self.cache = cache_manager

    async def list_all_locations(self) -> dict[str, Any]:
        """List all available locations across all organizations.

        Returns:
            Dictionary with location information
        """
        # Check cache first
        cache_key = "locations:all"
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                logger.debug("Returning cached all locations")
                return cached

        try:
            # Get all locations
            locations = await self.client.get_locations()

            # Format response
            result = {
                "success": True,
                "count": len(locations),
                "locations": [
                    {
                        "id": loc.id,
                        "name": loc.name,
                        "address": loc.address,
                        "city": loc.city,
                        "region": loc.region,
                        "country": loc.country,
                        "organization_id": loc.organization_id
                    }
                    for loc in locations[:100]  # Limit to 100 for response size
                ]
            }

            # Cache for 30 minutes
            if self.cache:
                await self.cache.set(cache_key, result, ttl=1800)

            logger.info(f"Listed {len(result['locations'])} locations")
            return result

        except Exception as e:
            logger.error(f"Failed to list all locations: {e}")
            return {
                "success": False,
                "error": str(e),
                "locations": []
            }

    async def find_locations_for_org(
        self,
        organization: str
    ) -> dict[str, Any]:
        """Find locations for a specific organization.

        Args:
            organization: Organization name or ID

        Returns:
            Dictionary with matching locations
        """
        # Check cache first
        cache_key = f"locations:org:{organization.lower()}"
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                logger.debug(f"Returning cached locations for {organization}")
                return cached

        try:
            # First, try to find the organization
            organizations = await self.client.get_organizations(
                filters={"name": organization}
            )

            if not organizations:
                # Try fuzzy match
                all_orgs = await self.client.get_organizations()
                org_match = self._find_best_match(
                    organization,
                    [(org.id, org.name) for org in all_orgs]
                )

                if not org_match:
                    return {
                        "success": False,
                        "error": f"Organization '{organization}' not found",
                        "locations": []
                    }

                org_id = org_match[0]
            else:
                org_id = organizations[0].id

            # Get locations for the organization
            locations = await self.client.get_locations(org_id=org_id)

            # Format response
            result = {
                "success": True,
                "organization_id": org_id,
                "count": len(locations),
                "locations": [
                    {
                        "id": loc.id,
                        "name": loc.name,
                        "address": loc.address,
                        "city": loc.city,
                        "region": loc.region,
                        "country": loc.country,
                        "full_address": self._format_full_address(loc)
                    }
                    for loc in locations
                ]
            }

            # Cache for 30 minutes
            if self.cache:
                await self.cache.set(cache_key, result, ttl=1800)

            logger.info(f"Found {len(result['locations'])} locations for organization {organization}")
            return result

        except Exception as e:
            logger.error(f"Failed to find locations for {organization}: {e}")
            return {
                "success": False,
                "error": str(e),
                "locations": []
            }

    async def find_location_by_city(
        self,
        city: str
    ) -> dict[str, Any]:
        """Find locations in a specific city.

        Args:
            city: City name

        Returns:
            Dictionary with matching locations
        """
        # Check cache first
        cache_key = f"locations:city:{city.lower()}"
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                logger.debug(f"Returning cached locations for city {city}")
                return cached

        try:
            # Get all locations and filter by city
            all_locations = await self.client.get_locations()

            # Case-insensitive city matching
            city_lower = city.lower()
            matching_locations = []

            for loc in all_locations:
                if loc.city and city_lower in loc.city.lower():
                    matching_locations.append(loc)
                elif loc.address and city_lower in loc.address.lower():
                    # Also check if city is mentioned in address
                    matching_locations.append(loc)

            # If no exact matches, try fuzzy matching
            if not matching_locations and len(all_locations) > 0:
                best_matches = []
                for loc in all_locations:
                    if loc.city:
                        similarity = SequenceMatcher(None, city_lower, loc.city.lower()).ratio()
                        if similarity > 0.7:
                            best_matches.append((loc, similarity))

                # Sort by similarity and take top matches
                best_matches.sort(key=lambda x: x[1], reverse=True)
                matching_locations = [loc for loc, _ in best_matches[:5]]

            # Format response
            result = {
                "success": True,
                "city": city,
                "count": len(matching_locations),
                "locations": [
                    {
                        "id": loc.id,
                        "name": loc.name,
                        "address": loc.address,
                        "city": loc.city,
                        "region": loc.region,
                        "country": loc.country,
                        "organization_id": loc.organization_id,
                        "full_address": self._format_full_address(loc)
                    }
                    for loc in matching_locations
                ]
            }

            # Cache for 30 minutes
            if self.cache:
                await self.cache.set(cache_key, result, ttl=1800)

            logger.info(f"Found {len(result['locations'])} locations in {city}")
            return result

        except Exception as e:
            logger.error(f"Failed to find locations in {city}: {e}")
            return {
                "success": False,
                "error": str(e),
                "city": city,
                "locations": []
            }

    async def find_location_by_name(
        self,
        name: str
    ) -> dict[str, Any]:
        """Find a specific location by name.

        Args:
            name: Location name

        Returns:
            Dictionary with matching location details
        """
        # Check cache first
        cache_key = f"locations:name:{name.lower()}"
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                logger.debug(f"Returning cached location {name}")
                return cached

        try:
            # Get all locations and find by name
            all_locations = await self.client.get_locations()

            # Exact match first
            name_lower = name.lower()
            exact_match = None
            partial_matches = []

            for loc in all_locations:
                loc_name_lower = loc.name.lower()
                if loc_name_lower == name_lower:
                    exact_match = loc
                    break
                elif name_lower in loc_name_lower or loc_name_lower in name_lower:
                    partial_matches.append(loc)

            # Use exact match if found, otherwise try fuzzy matching
            if exact_match:
                location = exact_match
            elif partial_matches:
                location = partial_matches[0]
            else:
                # Try fuzzy matching
                best_match = self._find_best_match(
                    name,
                    [(loc.id, loc.name) for loc in all_locations]
                )

                if not best_match:
                    return {
                        "success": False,
                        "error": f"Location '{name}' not found",
                        "suggestions": [loc.name for loc in all_locations[:5]]
                    }

                location = next(loc for loc in all_locations if loc.id == best_match[0])

            # Get organization details if available
            org_name = None
            if location.organization_id:
                try:
                    org = await self.client.get_organization(location.organization_id)
                    org_name = org.name
                except:
                    pass

            # Format response
            result = {
                "success": True,
                "location": {
                    "id": location.id,
                    "name": location.name,
                    "address": location.address,
                    "city": location.city,
                    "region": location.region,
                    "country": location.country,
                    "organization_id": location.organization_id,
                    "organization_name": org_name,
                    "full_address": self._format_full_address(location)
                }
            }

            # Cache for 30 minutes
            if self.cache:
                await self.cache.set(cache_key, result, ttl=1800)

            logger.info(f"Found location: {location.name}")
            return result

        except Exception as e:
            logger.error(f"Failed to find location {name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "location": None
            }

    async def search_locations(
        self,
        query: str
    ) -> dict[str, Any]:
        """Search locations by any field.

        Args:
            query: Search query

        Returns:
            Dictionary with matching locations
        """
        try:
            # Get all locations
            all_locations = await self.client.get_locations()

            # Search across all fields
            query_lower = query.lower()
            matching_locations = []

            for loc in all_locations:
                # Check all location fields
                if (
                    (loc.name and query_lower in loc.name.lower()) or
                    (loc.address and query_lower in loc.address.lower()) or
                    (loc.city and query_lower in loc.city.lower()) or
                    (loc.region and query_lower in loc.region.lower()) or
                    (loc.country and query_lower in loc.country.lower())
                ):
                    matching_locations.append(loc)

            # Format response
            result = {
                "success": True,
                "query": query,
                "count": len(matching_locations),
                "locations": [
                    {
                        "id": loc.id,
                        "name": loc.name,
                        "address": loc.address,
                        "city": loc.city,
                        "region": loc.region,
                        "country": loc.country,
                        "organization_id": loc.organization_id,
                        "full_address": self._format_full_address(loc)
                    }
                    for loc in matching_locations[:50]  # Limit to 50 results
                ]
            }

            logger.info(f"Found {len(result['locations'])} locations matching '{query}'")
            return result

        except Exception as e:
            logger.error(f"Failed to search locations for '{query}': {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "locations": []
            }

    def _format_full_address(self, location: Location) -> str:
        """Format a complete address string.

        Args:
            location: Location object

        Returns:
            Formatted address string
        """
        parts = []

        if location.address:
            parts.append(location.address)
        if location.city:
            parts.append(location.city)
        if location.region:
            parts.append(location.region)
        if location.country:
            parts.append(location.country)

        return ", ".join(parts)

    def _find_best_match(
        self,
        query: str,
        candidates: list[tuple]
    ) -> Optional[tuple]:
        """Find best matching candidate using fuzzy matching.

        Args:
            query: Search query
            candidates: List of (id, name) tuples

        Returns:
            Best matching tuple or None
        """
        if not candidates:
            return None

        query_lower = query.lower()
        best_match = None
        best_score = 0

        for candidate_id, candidate_name in candidates:
            score = SequenceMatcher(
                None,
                query_lower,
                candidate_name.lower()
            ).ratio()

            if score > best_score and score > 0.6:
                best_score = score
                best_match = (candidate_id, candidate_name)

        return best_match
