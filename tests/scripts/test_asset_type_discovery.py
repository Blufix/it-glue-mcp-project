"""Test flexible asset type discovery functionality."""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from src.query.asset_type_handler import AssetTypeHandler
from src.services.itglue.models import FlexibleAssetType, FlexibleAssetField
from src.cache.manager import CacheManager


class TestAssetTypeHandler:
    """Test AssetTypeHandler functionality."""
    
    @pytest_asyncio.fixture
    async def mock_client(self):
        """Create mock IT Glue client."""
        client = Mock()
        client.get_flexible_asset_types = AsyncMock()
        client.get_flexible_asset_type_by_name = AsyncMock()
        client.get_flexible_asset_fields = AsyncMock()
        return client
    
    @pytest_asyncio.fixture
    async def mock_cache(self):
        """Create mock cache manager."""
        cache = Mock(spec=CacheManager)
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()
        return cache
    
    @pytest_asyncio.fixture
    async def handler(self, mock_client, mock_cache):
        """Create handler instance."""
        return AssetTypeHandler(
            itglue_client=mock_client,
            cache_manager=mock_cache
        )
    
    @pytest.mark.asyncio
    async def test_list_asset_types(self, handler, mock_client):
        """Test listing all asset types."""
        # Mock asset types
        mock_types = [
            FlexibleAssetType(
                id="1",
                type="flexible-asset-types",
                attributes={
                    "name": "SSL Certificate",
                    "description": "SSL/TLS certificates",
                    "icon": "certificate",
                    "enabled": True,
                    "show-in-menu": True
                }
            ),
            FlexibleAssetType(
                id="2",
                type="flexible-asset-types",
                attributes={
                    "name": "Warranty",
                    "description": "Hardware warranties",
                    "icon": "shield",
                    "enabled": True,
                    "show-in-menu": False
                }
            ),
            FlexibleAssetType(
                id="3",
                type="flexible-asset-types",
                attributes={
                    "name": "Old Type",
                    "description": "Disabled type",
                    "icon": "archive",
                    "enabled": False,
                    "show-in-menu": False
                }
            )
        ]
        
        mock_client.get_flexible_asset_types.return_value = mock_types
        
        # Test list action
        result = await handler.list_asset_types()
        
        assert result["success"] is True
        # The count is of all types returned from API (3), but only enabled ones (2) are in the list
        assert result["count"] == 3  # Count of all types from API
        assert len(result["asset_types"]) == 2  # Only enabled types in the list
        
        # Check first asset type
        first_type = result["asset_types"][0]
        assert first_type["name"] == "SSL Certificate"
        assert first_type["description"] == "SSL/TLS certificates"
        assert first_type["icon"] == "certificate"
        assert first_type["enabled"] is True
        assert first_type["show_in_menu"] is True
    
    @pytest.mark.asyncio
    async def test_describe_asset_type(self, handler, mock_client):
        """Test describing a specific asset type."""
        # Mock asset type
        mock_type = FlexibleAssetType(
            id="1",
            type="flexible-asset-types",
            attributes={
                "name": "SSL Certificate",
                "description": "SSL/TLS certificates",
                "icon": "certificate",
                "enabled": True,
                "show-in-menu": True
            }
        )
        
        # Mock fields
        mock_fields = [
            FlexibleAssetField(
                id="1",
                type="flexible-asset-fields",
                attributes={
                    "name": "Domain",
                    "name-key": "domain",
                    "kind": "Text",
                    "required": True,
                    "hint": "Domain name for the certificate",
                    "default-value": None,
                    "order": 1,
                    "show-in-list": True,
                    "use-for-title": True
                }
            ),
            FlexibleAssetField(
                id="2",
                type="flexible-asset-fields",
                attributes={
                    "name": "Expiry Date",
                    "name-key": "expiry_date",
                    "kind": "Date",
                    "required": True,
                    "hint": "Certificate expiration date",
                    "default-value": None,
                    "order": 2,
                    "show-in-list": True,
                    "use-for-title": False
                }
            )
        ]
        
        mock_client.get_flexible_asset_type_by_name.return_value = mock_type
        mock_client.get_flexible_asset_fields.return_value = mock_fields
        
        # Test describe action
        result = await handler.describe_asset_type("SSL Certificate")
        
        assert result["success"] is True
        assert result["asset_type"]["name"] == "SSL Certificate"
        assert result["asset_type"]["field_count"] == 2
        
        # Check fields
        assert len(result["fields"]) == 2
        
        domain_field = result["fields"][0]
        assert domain_field["name"] == "Domain"
        assert domain_field["key"] == "domain"
        assert domain_field["type"] == "Text"
        assert domain_field["required"] is True
        assert domain_field["use_for_title"] is True
    
    @pytest.mark.asyncio
    async def test_search_asset_types(self, handler, mock_client):
        """Test searching asset types."""
        # Mock asset types
        mock_types = [
            FlexibleAssetType(
                id="1",
                type="flexible-asset-types",
                attributes={
                    "name": "SSL Certificate",
                    "description": "SSL/TLS certificates",
                    "icon": "certificate",
                    "enabled": True,
                    "show-in-menu": True
                }
            ),
            FlexibleAssetType(
                id="2",
                type="flexible-asset-types",
                attributes={
                    "name": "Software License",
                    "description": "Software licensing",
                    "icon": "key",
                    "enabled": True,
                    "show-in-menu": True
                }
            ),
            FlexibleAssetType(
                id="3",
                type="flexible-asset-types",
                attributes={
                    "name": "Warranty",
                    "description": "Hardware warranties",
                    "icon": "shield",
                    "enabled": True,
                    "show-in-menu": False
                }
            )
        ]
        
        mock_client.get_flexible_asset_types.return_value = mock_types
        
        # Test search for "certificate"
        result = await handler.search_asset_types("certificate")
        
        assert result["success"] is True
        assert result["query"] == "certificate"
        assert result["count"] == 1
        assert len(result["asset_types"]) == 1
        assert result["asset_types"][0]["name"] == "SSL Certificate"
        
        # Test search for "license"
        result = await handler.search_asset_types("license")
        
        assert result["success"] is True
        assert result["count"] == 1
        assert result["asset_types"][0]["name"] == "Software License"
    
    @pytest.mark.asyncio
    async def test_get_common_asset_types(self, handler, mock_client):
        """Test getting common asset types."""
        # Mock asset types
        mock_types = [
            FlexibleAssetType(
                id="1",
                type="flexible-asset-types",
                attributes={
                    "name": "SSL Certificate",
                    "description": "SSL/TLS certificates",
                    "icon": "certificate",
                    "enabled": True,
                    "show-in-menu": True
                }
            ),
            FlexibleAssetType(
                id="2",
                type="flexible-asset-types",
                attributes={
                    "name": "Warranty",
                    "description": "Hardware warranties",
                    "icon": "shield",
                    "enabled": True,
                    "show-in-menu": True
                }
            ),
            FlexibleAssetType(
                id="3",
                type="flexible-asset-types",
                attributes={
                    "name": "Domain Registration",
                    "description": "Domain name registrations",
                    "icon": "globe",
                    "enabled": True,
                    "show-in-menu": True
                }
            ),
            FlexibleAssetType(
                id="4",
                type="flexible-asset-types",
                attributes={
                    "name": "Firewall Rules",
                    "description": "Firewall configurations",
                    "icon": "shield-alt",
                    "enabled": True,
                    "show-in-menu": False
                }
            )
        ]
        
        mock_client.get_flexible_asset_types.return_value = mock_types
        
        # Test common asset types
        result = await handler.get_common_asset_types()
        
        assert result["success"] is True
        assert result["count"] >= 2  # At least SSL Certificate and Warranty
        
        # Check that common types are found
        names = [t["name"] for t in result["common_asset_types"]]
        assert "SSL Certificate" in names
        assert "Warranty" in names
    
    @pytest.mark.asyncio
    async def test_caching(self, handler, mock_client, mock_cache):
        """Test that results are cached properly."""
        # Setup mock response
        mock_types = [
            FlexibleAssetType(
                id="1",
                type="flexible-asset-types",
                attributes={
                    "name": "SSL Certificate",
                    "description": "SSL/TLS certificates",
                    "icon": "certificate",
                    "enabled": True,
                    "show-in-menu": True
                }
            )
        ]
        
        mock_client.get_flexible_asset_types.return_value = mock_types
        
        # First call - should hit API and cache
        result1 = await handler.list_asset_types()
        
        assert result1["success"] is True
        mock_client.get_flexible_asset_types.assert_called_once()
        mock_cache.set.assert_called_once()
        
        # Reset mocks and set cache to return cached value
        mock_client.get_flexible_asset_types.reset_mock()
        mock_cache.get.return_value = result1
        
        # Second call - should use cache
        result2 = await handler.list_asset_types()
        
        assert result2 == result1
        mock_client.get_flexible_asset_types.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_error_handling(self, handler, mock_client):
        """Test error handling."""
        # Test API error
        mock_client.get_flexible_asset_types.side_effect = Exception("API Error")
        
        result = await handler.list_asset_types()
        
        assert result["success"] is False
        assert "API Error" in result["error"]
        assert result["asset_types"] == []
        
        # Test asset type not found
        mock_client.get_flexible_asset_type_by_name.return_value = None
        
        result = await handler.describe_asset_type("NonExistent")
        
        assert result["success"] is False
        assert "not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_suggestions_for_not_found(self, handler, mock_client):
        """Test suggestions when asset type is not found."""
        # Mock asset types for suggestions
        mock_types = [
            FlexibleAssetType(
                id="1",
                type="flexible-asset-types",
                attributes={
                    "name": "SSL Certificate",
                    "description": "SSL/TLS certificates",
                    "icon": "certificate",
                    "enabled": True,
                    "show-in-menu": True
                }
            ),
            FlexibleAssetType(
                id="2",
                type="flexible-asset-types",
                attributes={
                    "name": "Software License",
                    "description": "Software licensing",
                    "icon": "key",
                    "enabled": True,
                    "show-in-menu": True
                }
            )
        ]
        
        mock_client.get_flexible_asset_type_by_name.return_value = None
        mock_client.get_flexible_asset_types.return_value = mock_types
        
        # Test with partial match
        result = await handler.describe_asset_type("cert")
        
        assert result["success"] is False
        assert "suggestions" in result
        assert "SSL Certificate" in result["suggestions"]


class TestMCPServerIntegration:
    """Test MCP server integration with asset type discovery."""
    
    @pytest.mark.asyncio
    async def test_discover_asset_types_tool(self):
        """Test the discover_asset_types tool functionality directly."""
        # Test the handler directly without importing the server to avoid circular imports
        mock_client = Mock()
        mock_cache = Mock(spec=CacheManager)
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        
        handler = AssetTypeHandler(
            itglue_client=mock_client,
            cache_manager=mock_cache
        )
        
        # Mock asset types
        mock_types = [
            FlexibleAssetType(
                id="1",
                type="flexible-asset-types",
                attributes={
                    "name": "SSL Certificate",
                    "description": "SSL/TLS certificates",
                    "icon": "certificate",
                    "enabled": True,
                    "show-in-menu": True
                }
            )
        ]
        
        mock_client.get_flexible_asset_types = AsyncMock(return_value=mock_types)
        
        # Test that the handler can be used in the same way the MCP tool would use it
        result = await handler.list_asset_types()
        assert result["success"] is True
        assert "asset_types" in result
        assert len(result["asset_types"]) == 1
        assert result["asset_types"][0]["name"] == "SSL Certificate"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])