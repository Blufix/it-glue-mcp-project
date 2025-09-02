"""Handler for flexible assets queries."""

import logging
from difflib import SequenceMatcher
from typing import Any, Optional

from src.cache.manager import CacheManager
from src.services.itglue.client import ITGlueClient
from src.services.itglue.models import FlexibleAsset, FlexibleAssetType

logger = logging.getLogger(__name__)


class FlexibleAssetsHandler:
    """Handles queries related to flexible assets."""

    def __init__(
        self,
        itglue_client: ITGlueClient,
        cache_manager: Optional[CacheManager] = None
    ):
        """Initialize flexible assets handler.

        Args:
            itglue_client: IT Glue API client
            cache_manager: Optional cache manager
        """
        self.client = itglue_client
        self.cache = cache_manager

    async def list_all_flexible_assets(
        self,
        asset_type: Optional[str] = None,
        limit: int = 100
    ) -> dict[str, Any]:
        """List all flexible assets, optionally filtered by type.

        Args:
            asset_type: Optional asset type name to filter by
            limit: Maximum number of results

        Returns:
            Dictionary with asset information
        """
        # Check cache first
        cache_key = f"flexible_assets:all:{asset_type or 'all'}"
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                logger.debug(f"Returning cached flexible assets for type {asset_type}")
                return cached

        try:
            # If asset type specified, find its ID
            asset_type_id = None
            asset_type_name = asset_type

            if asset_type:
                asset_type_obj = await self.client.get_flexible_asset_type_by_name(asset_type)
                if not asset_type_obj:
                    # Try to find similar asset types
                    all_types = await self.client.get_flexible_asset_types(include_fields=False)
                    suggestions = self._find_similar_types(asset_type, all_types)

                    return {
                        "success": False,
                        "error": f"Asset type '{asset_type}' not found",
                        "suggestions": suggestions,
                        "assets": []
                    }

                asset_type_id = asset_type_obj.id
                asset_type_name = asset_type_obj.name

            # Get flexible assets
            assets = await self.client.get_flexible_assets(
                asset_type_id=asset_type_id
            )

            # Format response
            result = {
                "success": True,
                "asset_type": asset_type_name,
                "count": len(assets),
                "assets": [
                    self._format_asset(asset)
                    for asset in assets[:limit]
                ]
            }

            # Cache for 15 minutes
            if self.cache:
                await self.cache.set(cache_key, result, ttl=900)

            logger.info(f"Listed {len(result['assets'])} flexible assets")
            return result

        except Exception as e:
            logger.error(f"Failed to list flexible assets: {e}")
            return {
                "success": False,
                "error": str(e),
                "assets": []
            }

    async def find_assets_for_org(
        self,
        organization: str,
        asset_type: Optional[str] = None
    ) -> dict[str, Any]:
        """Find flexible assets for a specific organization.

        Args:
            organization: Organization name or ID
            asset_type: Optional asset type to filter by

        Returns:
            Dictionary with matching assets
        """
        # Check cache first
        cache_key = f"flexible_assets:org:{organization.lower()}:{asset_type or 'all'}"
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                logger.debug(f"Returning cached assets for {organization}")
                return cached

        try:
            # Find the organization
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
                        "assets": []
                    }

                org_id = org_match[0]
                org_name = org_match[1]
            else:
                org_id = organizations[0].id
                org_name = organizations[0].name

            # Get asset type ID if specified
            asset_type_id = None
            asset_type_name = asset_type

            if asset_type:
                asset_type_obj = await self.client.get_flexible_asset_type_by_name(asset_type)
                if asset_type_obj:
                    asset_type_id = asset_type_obj.id
                    asset_type_name = asset_type_obj.name

            # Get assets for the organization
            assets = await self.client.get_flexible_assets(
                org_id=org_id,
                asset_type_id=asset_type_id
            )

            # Format response
            result = {
                "success": True,
                "organization_id": org_id,
                "organization_name": org_name,
                "asset_type": asset_type_name,
                "count": len(assets),
                "assets": [
                    self._format_asset(asset)
                    for asset in assets
                ]
            }

            # Cache for 15 minutes
            if self.cache:
                await self.cache.set(cache_key, result, ttl=900)

            logger.info(f"Found {len(result['assets'])} assets for {organization}")
            return result

        except Exception as e:
            logger.error(f"Failed to find assets for {organization}: {e}")
            return {
                "success": False,
                "error": str(e),
                "assets": []
            }

    async def search_flexible_assets(
        self,
        query: str,
        asset_type: Optional[str] = None
    ) -> dict[str, Any]:
        """Search flexible assets by query.

        Args:
            query: Search query
            asset_type: Optional asset type to filter by

        Returns:
            Dictionary with matching assets
        """
        try:
            # Get asset type ID if specified
            asset_type_id = None
            if asset_type:
                asset_type_obj = await self.client.get_flexible_asset_type_by_name(asset_type)
                if asset_type_obj:
                    asset_type_id = asset_type_obj.id

            # Get all assets (filtered by type if specified)
            all_assets = await self.client.get_flexible_assets(
                asset_type_id=asset_type_id
            )

            # Search across asset names and traits
            query_lower = query.lower()
            matching_assets = []

            for asset in all_assets:
                # Check asset name
                if query_lower in asset.name.lower():
                    matching_assets.append(asset)
                    continue

                # Check traits
                traits_match = False
                for key, value in asset.traits.items():
                    if value and isinstance(value, str) and query_lower in value.lower():
                        traits_match = True
                        break

                if traits_match:
                    matching_assets.append(asset)

            # Format response
            result = {
                "success": True,
                "query": query,
                "asset_type": asset_type,
                "count": len(matching_assets),
                "assets": [
                    self._format_asset(asset)
                    for asset in matching_assets[:50]  # Limit to 50 results
                ]
            }

            logger.info(f"Found {len(result['assets'])} assets matching '{query}'")
            return result

        except Exception as e:
            logger.error(f"Failed to search assets for '{query}': {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "assets": []
            }

    async def get_common_asset_types_with_counts(self) -> dict[str, Any]:
        """Get common asset types with their asset counts.

        Returns:
            Dictionary with asset type statistics
        """
        # Check cache first
        cache_key = "flexible_assets:stats"
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                logger.debug("Returning cached asset statistics")
                return cached

        try:
            # Get all asset types
            asset_types = await self.client.get_flexible_asset_types(include_fields=False)

            # Common asset type names to look for
            common_names = [
                "SSL Certificate",
                "Warranty",
                "Software License",
                "Domain",
                "Email",
                "Firewall",
                "Backup",
                "Contract",
                "SLA"
            ]

            # Get counts for each type
            type_stats = []

            for asset_type in asset_types:
                # Check if this is a common type
                is_common = any(
                    name.lower() in asset_type.name.lower()
                    for name in common_names
                )

                if is_common and asset_type.enabled:
                    # Get assets for this type
                    assets = await self.client.get_flexible_assets(
                        asset_type_id=asset_type.id
                    )

                    type_stats.append({
                        "id": asset_type.id,
                        "name": asset_type.name,
                        "description": asset_type.description,
                        "icon": asset_type.icon,
                        "asset_count": len(assets),
                        "example_assets": [
                            asset.name for asset in assets[:3]
                        ] if assets else []
                    })

            # Sort by asset count
            type_stats.sort(key=lambda x: x["asset_count"], reverse=True)

            result = {
                "success": True,
                "common_asset_types": type_stats,
                "total_types": len(asset_types),
                "types_with_assets": len([t for t in type_stats if t["asset_count"] > 0])
            }

            # Cache for 1 hour
            if self.cache:
                await self.cache.set(cache_key, result, ttl=3600)

            logger.info(f"Retrieved statistics for {len(type_stats)} common asset types")
            return result

        except Exception as e:
            logger.error(f"Failed to get asset type statistics: {e}")
            return {
                "success": False,
                "error": str(e),
                "common_asset_types": []
            }

    async def get_asset_details(
        self,
        asset_id: str
    ) -> dict[str, Any]:
        """Get detailed information about a specific asset.

        Args:
            asset_id: Asset ID

        Returns:
            Dictionary with asset details
        """
        # Check cache first
        cache_key = f"flexible_assets:detail:{asset_id}"
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                logger.debug(f"Returning cached asset details for {asset_id}")
                return cached

        try:
            # Get all assets and find the specific one
            # Note: IT Glue API might not have a direct get-by-id for flexible assets
            all_assets = await self.client.get_flexible_assets()

            asset = None
            for a in all_assets:
                if a.id == asset_id:
                    asset = a
                    break

            if not asset:
                return {
                    "success": False,
                    "error": f"Asset with ID '{asset_id}' not found",
                    "asset": None
                }

            # Get asset type details
            asset_type = await self.client.get_flexible_asset_type_by_name(
                asset.flexible_asset_type_id
            )

            # Get organization details if available
            org_name = None
            if asset.organization_id:
                try:
                    org = await self.client.get_organization(asset.organization_id)
                    org_name = org.name
                except:
                    pass

            # Format detailed response
            result = {
                "success": True,
                "asset": {
                    "id": asset.id,
                    "name": asset.name,
                    "type_id": asset.flexible_asset_type_id,
                    "type_name": asset_type.name if asset_type else None,
                    "organization_id": asset.organization_id,
                    "organization_name": org_name,
                    "traits": asset.traits,
                    "created_at": asset.created_at.isoformat() if asset.created_at else None,
                    "updated_at": asset.updated_at.isoformat() if asset.updated_at else None
                }
            }

            # Cache for 30 minutes
            if self.cache:
                await self.cache.set(cache_key, result, ttl=1800)

            logger.info(f"Retrieved details for asset {asset_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to get asset details for {asset_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "asset": None
            }

    def _format_asset(self, asset: FlexibleAsset) -> dict[str, Any]:
        """Format a flexible asset for response.

        Args:
            asset: FlexibleAsset object

        Returns:
            Formatted asset dictionary
        """
        # Extract key traits for display
        display_traits = {}
        for key, value in asset.traits.items():
            # Only include non-empty, meaningful traits
            if value and not key.startswith("_"):
                # Limit trait values to reasonable length
                if isinstance(value, str) and len(value) > 200:
                    display_traits[key] = value[:200] + "..."
                else:
                    display_traits[key] = value

        return {
            "id": asset.id,
            "name": asset.name,
            "type_id": asset.flexible_asset_type_id,
            "organization_id": asset.organization_id,
            "traits": display_traits,
            "created_at": asset.created_at.isoformat() if asset.created_at else None,
            "updated_at": asset.updated_at.isoformat() if asset.updated_at else None
        }

    def _find_similar_types(
        self,
        query: str,
        asset_types: list[FlexibleAssetType]
    ) -> list[str]:
        """Find similar asset type names.

        Args:
            query: The query that didn't match
            asset_types: List of available asset types

        Returns:
            List of similar type names
        """
        query_lower = query.lower()
        suggestions = []

        for asset_type in asset_types:
            if not asset_type.enabled:
                continue

            name_lower = asset_type.name.lower()

            # Check for partial matches
            if any(word in name_lower for word in query_lower.split()):
                suggestions.append(asset_type.name)

            # Check for common variations
            if "cert" in query_lower and "certificate" in name_lower:
                suggestions.append(asset_type.name)
            elif "license" in query_lower and ("licence" in name_lower or "license" in name_lower):
                suggestions.append(asset_type.name)
            elif "warranty" in query_lower and "warrant" in name_lower:
                suggestions.append(asset_type.name)

            # Use sequence matching for fuzzy match
            similarity = SequenceMatcher(None, query_lower, name_lower).ratio()
            if similarity > 0.6 and asset_type.name not in suggestions:
                suggestions.append(asset_type.name)

        return suggestions[:5]  # Return top 5 suggestions

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
