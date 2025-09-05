"""Query flexible assets tool for MCP server."""

from typing import Any, Optional

from src.cache.manager import CacheManager
from src.query.flexible_assets_handler import FlexibleAssetsHandler
from src.services.itglue.client import ITGlueClient

from .base import BaseTool


class QueryFlexibleAssetsTool(BaseTool):
    """Tool for querying IT Glue flexible assets."""

    def __init__(
        self, 
        itglue_client: ITGlueClient, 
        cache_manager: Optional[CacheManager] = None
    ):
        """Initialize query flexible assets tool.

        Args:
            itglue_client: IT Glue API client
            cache_manager: Optional cache manager
        """
        super().__init__(
            name="query_flexible_assets",
            description="Query and search IT Glue flexible assets by type, organization, or traits"
        )
        self.assets_handler = FlexibleAssetsHandler(itglue_client, cache_manager)

    async def execute(
        self,
        action: str = "list_all",
        organization: Optional[str] = None,
        asset_type: Optional[str] = None,
        query: Optional[str] = None,
        asset_id: Optional[str] = None,
        limit: int = 100,
        **kwargs
    ) -> dict[str, Any]:
        """Execute flexible assets query.

        Args:
            action: Action to perform (list_all, by_org, by_type, search, details, stats)
            organization: Organization name or ID to filter by
            asset_type: Asset type name to filter by (SSL Certificate, Warranty, etc.)
            query: Search query for assets
            asset_id: Specific asset ID to get details
            limit: Maximum number of results
            **kwargs: Additional arguments

        Returns:
            Query results
        """
        try:
            self.logger.info(f"Executing flexible assets query: action={action}")

            # Route to appropriate handler method based on action
            if action == "list_all":
                result = await self.assets_handler.list_all_flexible_assets(
                    asset_type=asset_type, 
                    limit=limit
                )
                
            elif action == "by_org" or organization:
                if not organization:
                    return self.format_error("Organization parameter required for by_org action")
                result = await self.assets_handler.find_assets_for_org(
                    organization=organization,
                    asset_type=asset_type
                )
                
            elif action == "by_type" or asset_type:
                if not asset_type:
                    return self.format_error("Asset type parameter required for by_type action")
                result = await self.assets_handler.list_all_flexible_assets(
                    asset_type=asset_type,
                    limit=limit
                )
                
            elif action == "search" or query:
                if not query:
                    return self.format_error("Query parameter required for search action")
                result = await self.assets_handler.search_flexible_assets(
                    query=query,
                    asset_type=asset_type
                )
                
            elif action == "details" or asset_id:
                if not asset_id:
                    return self.format_error("Asset ID parameter required for details action")
                result = await self.assets_handler.get_asset_details(asset_id)
                
            elif action == "stats" or action == "asset_types":
                result = await self.assets_handler.get_common_asset_types_with_counts()
                
            else:
                return self.format_error(
                    f"Unknown action '{action}'. Supported actions: "
                    "list_all, by_org, by_type, search, details, stats"
                )

            # Add metadata to successful results
            if result.get("success", False):
                result["action"] = action
                result["parameters"] = {
                    "organization": organization,
                    "asset_type": asset_type,
                    "query": query,
                    "asset_id": asset_id,
                    "limit": limit
                }

            return self.format_success(result)

        except Exception as e:
            self.logger.error(f"Flexible assets query failed: {e}", exc_info=True)
            return self.format_error(
                f"Failed to query flexible assets: {str(e)}",
                action=action,
                organization=organization,
                asset_type=asset_type,
                query=query,
                asset_id=asset_id
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