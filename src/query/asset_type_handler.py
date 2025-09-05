"""Handler for flexible asset type discovery queries."""

import logging
from typing import Any, Optional

from src.cache.manager import CacheManager
from src.services.itglue.client import ITGlueClient
from src.services.itglue.models import FlexibleAssetField

logger = logging.getLogger(__name__)


class AssetTypeHandler:
    """Handles queries related to flexible asset type discovery."""

    def __init__(
        self,
        itglue_client: ITGlueClient,
        cache_manager: Optional[CacheManager] = None
    ):
        """Initialize asset type handler.

        Args:
            itglue_client: IT Glue API client
            cache_manager: Optional cache manager
        """
        self.client = itglue_client
        self.cache = cache_manager

    async def list_asset_types(self) -> dict[str, Any]:
        """List all available flexible asset types.

        Returns:
            Dictionary with asset types information
        """
        # Check cache first
        cache_key = "asset_types:list"
        if self.cache and hasattr(self.cache, 'query_cache'):
            cached = await self.cache.query_cache.get(cache_key)
            if cached:
                logger.debug("Returning cached asset types")
                return cached

        try:
            # Get all asset types
            asset_types = await self.client.get_flexible_asset_types(include_fields=False)

            # Format response
            result = {
                "success": True,
                "count": len(asset_types),
                "asset_types": [
                    {
                        "id": asset_type.id,
                        "name": asset_type.name,
                        "description": asset_type.description,
                        "icon": asset_type.icon,
                        "enabled": asset_type.enabled,
                        "show_in_menu": asset_type.show_in_menu
                    }
                    for asset_type in asset_types
                    if asset_type.enabled  # Only show enabled types
                ]
            }

            # Cache for 1 hour (asset types don't change often)
            if self.cache and hasattr(self.cache, 'query_cache'):
                from ..cache.redis_cache import QueryType
                await self.cache.query_cache.set(cache_key, result, QueryType.OPERATIONAL)

            logger.info(f"Listed {len(result['asset_types'])} asset types")
            return result

        except Exception as e:
            logger.error(f"Failed to list asset types: {e}")
            return {
                "success": False,
                "error": str(e),
                "asset_types": []
            }

    async def describe_asset_type(self, asset_type_name: str) -> dict[str, Any]:
        """Describe a specific asset type including its fields.

        Args:
            asset_type_name: Name of the asset type to describe

        Returns:
            Dictionary with asset type details and field definitions
        """
        # Check cache first
        cache_key = f"asset_type:describe:{asset_type_name.lower()}"
        if self.cache and hasattr(self.cache, 'query_cache'):
            cached = await self.cache.query_cache.get(cache_key)
            if cached:
                logger.debug(f"Returning cached description for {asset_type_name}")
                return cached

        try:
            # Get the asset type by name
            asset_type = await self.client.get_flexible_asset_type_by_name(asset_type_name)

            if not asset_type:
                return {
                    "success": False,
                    "error": f"Asset type '{asset_type_name}' not found",
                    "suggestions": await self._suggest_similar_types(asset_type_name)
                }

            # Always fetch detailed field information via API
            # Relationship data only contains basic references without attributes
            fields = await self.client.get_flexible_asset_fields(asset_type.id)

            # Format response with detailed field information
            result = {
                "success": True,
                "asset_type": {
                    "id": asset_type.id,
                    "name": asset_type.name,
                    "description": asset_type.description,
                    "icon": asset_type.icon,
                    "enabled": asset_type.enabled,
                    "field_count": len(fields)
                },
                "fields": [
                    {
                        "name": field.name,
                        "key": field.name_key,
                        "type": field.kind,
                        "required": field.required,
                        "hint": field.hint,
                        "default_value": field.default_value,
                        "order": field.order,
                        "show_in_list": field.show_in_list,
                        "use_for_title": field.use_for_title
                    }
                    for field in sorted(fields, key=lambda f: f.order)
                ]
            }

            # Cache for 1 hour
            if self.cache and hasattr(self.cache, 'query_cache'):
                from ..cache.redis_cache import QueryType
                await self.cache.query_cache.set(cache_key, result, QueryType.OPERATIONAL)

            logger.info(f"Described asset type '{asset_type.name}' with {len(fields)} fields")
            return result

        except Exception as e:
            logger.error(f"Failed to describe asset type '{asset_type_name}': {e}")
            return {
                "success": False,
                "error": str(e),
                "asset_type": None,
                "fields": []
            }

    async def search_asset_types(self, query: str) -> dict[str, Any]:
        """Search for asset types matching a query.

        Args:
            query: Search query (partial name match)

        Returns:
            Dictionary with matching asset types
        """
        try:
            # Get all asset types
            all_types = await self.client.get_flexible_asset_types(include_fields=False)

            # Filter by query (case-insensitive)
            query_lower = query.lower()
            matching_types = [
                asset_type for asset_type in all_types
                if query_lower in asset_type.name.lower() or
                   (asset_type.description and query_lower in asset_type.description.lower())
            ]

            # Format response
            result = {
                "success": True,
                "query": query,
                "count": len(matching_types),
                "asset_types": [
                    {
                        "id": asset_type.id,
                        "name": asset_type.name,
                        "description": asset_type.description,
                        "icon": asset_type.icon,
                        "enabled": asset_type.enabled
                    }
                    for asset_type in matching_types
                ]
            }

            logger.info(f"Found {len(matching_types)} asset types matching '{query}'")
            return result

        except Exception as e:
            logger.error(f"Failed to search asset types for '{query}': {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "asset_types": []
            }

    async def get_common_asset_types(self) -> dict[str, Any]:
        """Get commonly used asset types with quick info.

        Returns:
            Dictionary with common asset types
        """
        # Common asset type names
        common_names = [
            "SSL Certificate",
            "Warranty",
            "Software License",
            "Domain",
            "Email",
            "Firewall",
            "Backup",
            "SLA",
            "Contract"
        ]

        try:
            all_types = await self.client.get_flexible_asset_types(include_fields=False)

            # Find common types
            common_types = []
            for name in common_names:
                for asset_type in all_types:
                    if name.lower() in asset_type.name.lower():
                        common_types.append({
                            "id": asset_type.id,
                            "name": asset_type.name,
                            "description": asset_type.description,
                            "icon": asset_type.icon
                        })
                        break

            return {
                "success": True,
                "common_asset_types": common_types,
                "count": len(common_types)
            }

        except Exception as e:
            logger.error(f"Failed to get common asset types: {e}")
            return {
                "success": False,
                "error": str(e),
                "common_asset_types": []
            }

    async def _suggest_similar_types(self, query: str) -> list[str]:
        """Suggest similar asset type names.

        Args:
            query: The query that didn't match

        Returns:
            List of suggestions
        """
        try:
            all_types = await self.client.get_flexible_asset_types(include_fields=False)

            # Simple similarity check
            query_lower = query.lower()
            suggestions = []

            for asset_type in all_types:
                name_lower = asset_type.name.lower()

                # Check for partial matches
                if any(word in name_lower for word in query_lower.split()):
                    suggestions.append(asset_type.name)

                # Check for common variations
                if "cert" in query_lower and "certificate" in name_lower:
                    suggestions.append(asset_type.name)
                elif "license" in query_lower and "licence" in name_lower:
                    suggestions.append(asset_type.name)
                elif "warranty" in query_lower and "warrant" in name_lower:
                    suggestions.append(asset_type.name)

            return suggestions[:5]  # Return top 5 suggestions

        except Exception as e:
            logger.error(f"Failed to generate suggestions: {e}")
            return []
