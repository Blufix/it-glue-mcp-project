"""Test flexible assets handler functionality."""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from src.query.flexible_assets_handler import FlexibleAssetsHandler
from src.services.itglue.models import FlexibleAsset, FlexibleAssetType, Organization
from src.cache.manager import CacheManager


class TestFlexibleAssetsHandler:
    """Test FlexibleAssetsHandler functionality."""
    
    @pytest_asyncio.fixture
    async def mock_client(self):
        """Create mock IT Glue client."""
        client = Mock()
        client.get_flexible_assets = AsyncMock()
        client.get_flexible_asset_types = AsyncMock()
        client.get_flexible_asset_type_by_name = AsyncMock()
        client.get_organizations = AsyncMock()
        client.get_organization = AsyncMock()
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
        return FlexibleAssetsHandler(
            itglue_client=mock_client,
            cache_manager=mock_cache
        )
    
    @pytest_asyncio.fixture
    async def sample_asset_types(self):
        """Create sample asset type data."""
        return [
            FlexibleAssetType(
                id="type-1",
                type="flexible-asset-types",
                attributes={
                    "name": "SSL Certificate",
                    "description": "SSL/TLS certificates",
                    "icon": "certificate",
                    "enabled": True
                }
            ),
            FlexibleAssetType(
                id="type-2",
                type="flexible-asset-types",
                attributes={
                    "name": "Warranty",
                    "description": "Hardware warranties",
                    "icon": "shield",
                    "enabled": True
                }
            )
        ]
    
    @pytest_asyncio.fixture
    async def sample_assets(self):
        """Create sample flexible asset data."""
        return [
            FlexibleAsset(
                id="asset-1",
                type="flexible-assets",
                attributes={
                    "name": "*.example.com SSL Certificate",
                    "flexible-asset-type-id": "type-1",
                    "organization-id": "org-1",
                    "traits": {
                        "domain": "*.example.com",
                        "expiry_date": "2024-12-31",
                        "issuer": "Let's Encrypt",
                        "key_size": "2048"
                    }
                },
                created_at=datetime(2023, 1, 1),
                updated_at=datetime(2023, 6, 1)
            ),
            FlexibleAsset(
                id="asset-2",
                type="flexible-assets",
                attributes={
                    "name": "Dell Server Warranty",
                    "flexible-asset-type-id": "type-2",
                    "organization-id": "org-1",
                    "traits": {
                        "device": "Dell PowerEdge R740",
                        "serial_number": "ABC123",
                        "expiry_date": "2025-06-30",
                        "support_level": "ProSupport Plus"
                    }
                },
                created_at=datetime(2023, 2, 1),
                updated_at=datetime(2023, 7, 1)
            ),
            FlexibleAsset(
                id="asset-3",
                type="flexible-assets",
                attributes={
                    "name": "api.example.com SSL Certificate",
                    "flexible-asset-type-id": "type-1",
                    "organization-id": "org-2",
                    "traits": {
                        "domain": "api.example.com",
                        "expiry_date": "2024-09-30",
                        "issuer": "DigiCert",
                        "key_size": "4096"
                    }
                }
            )
        ]
    
    @pytest.mark.asyncio
    async def test_list_all_flexible_assets(self, handler, mock_client, sample_assets):
        """Test listing all flexible assets."""
        mock_client.get_flexible_assets.return_value = sample_assets
        
        result = await handler.list_all_flexible_assets()
        
        assert result["success"] is True
        assert result["count"] == 3
        assert len(result["assets"]) == 3
        
        # Check first asset
        first_asset = result["assets"][0]
        assert first_asset["name"] == "*.example.com SSL Certificate"
        assert "domain" in first_asset["traits"]
        assert first_asset["traits"]["domain"] == "*.example.com"
    
    @pytest.mark.asyncio
    async def test_list_assets_by_type(self, handler, mock_client, sample_assets, sample_asset_types):
        """Test listing assets filtered by type."""
        mock_client.get_flexible_asset_type_by_name.return_value = sample_asset_types[0]
        
        # Filter to only SSL certificates
        ssl_assets = [a for a in sample_assets if a.flexible_asset_type_id == "type-1"]
        mock_client.get_flexible_assets.return_value = ssl_assets
        
        result = await handler.list_all_flexible_assets(asset_type="SSL Certificate")
        
        assert result["success"] is True
        assert result["asset_type"] == "SSL Certificate"
        assert result["count"] == 2
        assert all(
            "certificate" in asset["name"].lower()
            for asset in result["assets"]
        )
    
    @pytest.mark.asyncio
    async def test_find_assets_for_org(self, handler, mock_client, sample_assets):
        """Test finding assets for a specific organization."""
        # Mock organization lookup
        mock_org = Organization(
            id="org-1",
            type="organizations",
            attributes={"name": "TechCorp"}
        )
        mock_client.get_organizations.return_value = [mock_org]
        
        # Return only assets for org-1
        org_assets = [a for a in sample_assets if a.organization_id == "org-1"]
        mock_client.get_flexible_assets.return_value = org_assets
        
        result = await handler.find_assets_for_org("TechCorp")
        
        assert result["success"] is True
        assert result["organization_id"] == "org-1"
        assert result["organization_name"] == "TechCorp"
        assert result["count"] == 2
        assert len(result["assets"]) == 2
    
    @pytest.mark.asyncio
    async def test_search_flexible_assets(self, handler, mock_client, sample_assets):
        """Test searching flexible assets."""
        mock_client.get_flexible_assets.return_value = sample_assets
        
        # Search by domain
        result = await handler.search_flexible_assets("example.com")
        
        assert result["success"] is True
        assert result["query"] == "example.com"
        assert result["count"] == 2  # Both SSL certificates have example.com
        
        # Search by trait value
        result = await handler.search_flexible_assets("DigiCert")
        
        assert result["success"] is True
        assert result["count"] == 1
        assert result["assets"][0]["name"] == "api.example.com SSL Certificate"
    
    @pytest.mark.asyncio
    async def test_get_asset_details(self, handler, mock_client, sample_assets, sample_asset_types):
        """Test getting detailed asset information."""
        mock_client.get_flexible_assets.return_value = sample_assets
        mock_client.get_flexible_asset_type_by_name.return_value = sample_asset_types[0]
        
        mock_org = Organization(
            id="org-1",
            type="organizations",
            attributes={"name": "TechCorp"}
        )
        mock_client.get_organization.return_value = mock_org
        
        result = await handler.get_asset_details("asset-1")
        
        assert result["success"] is True
        assert result["asset"]["id"] == "asset-1"
        assert result["asset"]["name"] == "*.example.com SSL Certificate"
        assert result["asset"]["type_name"] == "SSL Certificate"
        assert result["asset"]["organization_name"] == "TechCorp"
        assert result["asset"]["traits"]["domain"] == "*.example.com"
    
    @pytest.mark.asyncio
    async def test_get_common_asset_types_with_counts(self, handler, mock_client, sample_asset_types, sample_assets):
        """Test getting asset type statistics."""
        mock_client.get_flexible_asset_types.return_value = sample_asset_types
        
        # Return different assets for each type
        async def mock_get_assets(asset_type_id=None, **kwargs):
            if asset_type_id == "type-1":
                return [a for a in sample_assets if a.flexible_asset_type_id == "type-1"]
            elif asset_type_id == "type-2":
                return [a for a in sample_assets if a.flexible_asset_type_id == "type-2"]
            return sample_assets
        
        mock_client.get_flexible_assets.side_effect = mock_get_assets
        
        result = await handler.get_common_asset_types_with_counts()
        
        assert result["success"] is True
        assert "common_asset_types" in result
        assert len(result["common_asset_types"]) > 0
        
        # Check SSL Certificate stats
        ssl_stats = next(
            (t for t in result["common_asset_types"] if t["name"] == "SSL Certificate"),
            None
        )
        assert ssl_stats is not None
        assert ssl_stats["asset_count"] == 2
        assert len(ssl_stats["example_assets"]) == 2
    
    @pytest.mark.asyncio
    async def test_asset_type_not_found(self, handler, mock_client, sample_asset_types):
        """Test handling of unknown asset type."""
        mock_client.get_flexible_asset_type_by_name.return_value = None
        mock_client.get_flexible_asset_types.return_value = sample_asset_types
        
        # Use "Certificate" which should suggest "SSL Certificate"
        result = await handler.list_all_flexible_assets(asset_type="Certificate")
        
        assert result["success"] is False
        assert "not found" in result["error"]
        assert "suggestions" in result
        # Should suggest SSL Certificate since it contains "Certificate"
        assert len(result["suggestions"]) > 0
        assert "SSL Certificate" in result["suggestions"]
    
    @pytest.mark.asyncio
    async def test_caching(self, handler, mock_client, mock_cache, sample_assets):
        """Test that results are cached properly."""
        mock_client.get_flexible_assets.return_value = sample_assets
        
        # First call - should hit API and cache
        result1 = await handler.list_all_flexible_assets()
        
        assert result1["success"] is True
        mock_client.get_flexible_assets.assert_called_once()
        mock_cache.set.assert_called_once()
        
        # Reset mocks and set cache to return cached value
        mock_client.get_flexible_assets.reset_mock()
        mock_cache.get.return_value = result1
        
        # Second call - should use cache
        result2 = await handler.list_all_flexible_assets()
        
        assert result2 == result1
        mock_client.get_flexible_assets.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_error_handling(self, handler, mock_client):
        """Test error handling."""
        # Test API error
        mock_client.get_flexible_assets.side_effect = Exception("API Error")
        
        result = await handler.list_all_flexible_assets()
        
        assert result["success"] is False
        assert "API Error" in result["error"]
        assert result["assets"] == []
        
        # Test organization not found
        mock_client.get_organizations.return_value = []
        mock_client.get_flexible_assets.side_effect = None
        mock_client.get_flexible_assets.return_value = []
        
        result = await handler.find_assets_for_org("NonExistent")
        
        assert result["success"] is False
        assert "not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_trait_truncation(self, handler, mock_client):
        """Test that long trait values are truncated."""
        long_description = "A" * 500  # Very long trait value
        
        asset_with_long_trait = FlexibleAsset(
            id="asset-long",
            type="flexible-assets",
            attributes={
                "name": "Asset with long trait",
                "flexible-asset-type-id": "type-1",
                "organization-id": "org-1",
                "traits": {
                    "description": long_description,
                    "short_field": "normal value"
                }
            }
        )
        
        mock_client.get_flexible_assets.return_value = [asset_with_long_trait]
        
        result = await handler.list_all_flexible_assets()
        
        assert result["success"] is True
        asset = result["assets"][0]
        
        # Long trait should be truncated
        assert len(asset["traits"]["description"]) == 203  # 200 + "..."
        assert asset["traits"]["description"].endswith("...")
        
        # Short trait should be unchanged
        assert asset["traits"]["short_field"] == "normal value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])