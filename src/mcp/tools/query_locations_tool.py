"""Query locations tool for MCP server."""

from typing import Any, Optional

from src.cache.manager import CacheManager
from src.query.locations_handler import LocationsHandler
from src.services.itglue.client import ITGlueClient

from .base import BaseTool


class QueryLocationsTool(BaseTool):
    """Tool for querying IT Glue locations."""

    def __init__(
        self, 
        itglue_client: ITGlueClient, 
        cache_manager: Optional[CacheManager] = None
    ):
        """Initialize query locations tool.

        Args:
            itglue_client: IT Glue API client
            cache_manager: Optional cache manager
        """
        super().__init__(
            name="query_locations",
            description="Query and search IT Glue locations by organization, city, or name"
        )
        self.locations_handler = LocationsHandler(itglue_client, cache_manager)

    async def execute(
        self,
        action: str = "list_all",
        organization: Optional[str] = None,
        city: Optional[str] = None,
        location_name: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 100,
        **kwargs
    ) -> dict[str, Any]:
        """Execute locations query.

        Args:
            action: Action to perform (list_all, by_org, by_city, by_name, search)
            organization: Organization name or ID to filter by
            city: City name to search by
            location_name: Specific location name to find
            query: General search query
            limit: Maximum number of results (not implemented in handler)
            **kwargs: Additional arguments

        Returns:
            Query results
        """
        try:
            self.logger.info(f"Executing locations query: action={action}")

            # Route to appropriate handler method based on action
            if action == "list_all":
                result = await self.locations_handler.list_all_locations()
                
            elif action == "by_org" or organization:
                if not organization:
                    return self.format_error("Organization parameter required for by_org action")
                result = await self.locations_handler.find_locations_for_org(organization)
                
            elif action == "by_city" or city:
                if not city:
                    return self.format_error("City parameter required for by_city action")
                result = await self.locations_handler.find_location_by_city(city)
                
            elif action == "by_name" or location_name:
                if not location_name:
                    return self.format_error("Location name parameter required for by_name action")
                result = await self.locations_handler.find_location_by_name(location_name)
                
            elif action == "search" or query:
                if not query:
                    return self.format_error("Query parameter required for search action")
                result = await self.locations_handler.search_locations(query)
                
            else:
                return self.format_error(
                    f"Unknown action '{action}'. Supported actions: "
                    "list_all, by_org, by_city, by_name, search"
                )

            # Add metadata to successful results
            if result.get("success", False):
                result["action"] = action
                result["parameters"] = {
                    "organization": organization,
                    "city": city,
                    "location_name": location_name,
                    "query": query,
                    "limit": limit
                }

            return self.format_success(result)

        except Exception as e:
            self.logger.error(f"Locations query failed: {e}", exc_info=True)
            return self.format_error(
                f"Failed to query locations: {str(e)}",
                action=action,
                organization=organization,
                city=city,
                location_name=location_name,
                query=query
            )

    def format_success(self, data: dict[str, Any]) -> dict[str, Any]:
        """Format successful response.

        Args:
            data: Response data

        Returns:
            Formatted success response
        """
        return {
            "success": True,
            "tool": self.name,
            "data": data
        }

    def format_error(self, message: str, **context) -> dict[str, Any]:
        """Format error response.

        Args:
            message: Error message
            **context: Additional context

        Returns:
            Formatted error response
        """
        return {
            "success": False,
            "tool": self.name,
            "error": message,
            "context": context
        }