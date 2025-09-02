"""Mock IT Glue client for testing."""

from typing import List, Dict, Any, Optional
from unittest.mock import AsyncMock, Mock
import asyncio

from .test_data import (
    get_sample_organizations,
    get_sample_configurations,
    get_sample_documents,
    get_sample_flexible_assets,
    get_sample_locations,
    get_sample_asset_types,
    get_sample_contacts,
    get_sample_passwords
)


class MockITGlueClient:
    """Mock IT Glue client with realistic test data."""
    
    def __init__(self):
        """Initialize mock client with test data."""
        self.organizations = get_sample_organizations()
        self.configurations = get_sample_configurations()
        self.documents = get_sample_documents()
        self.flexible_assets = get_sample_flexible_assets()
        self.locations = get_sample_locations()
        self.asset_types = get_sample_asset_types()
        self.contacts = get_sample_contacts()
        self.passwords = get_sample_passwords()
        
        # Track API calls for testing
        self.api_calls = []
    
    async def get_organizations(
        self, 
        page: int = 1, 
        per_page: int = 100,
        filter_organization_type: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Mock get organizations."""
        self.api_calls.append(('get_organizations', kwargs))
        
        orgs = self.organizations
        if filter_organization_type:
            orgs = [o for o in orgs if o.get('organization_type') == filter_organization_type]
        
        # Simulate pagination
        start = (page - 1) * per_page
        end = start + per_page
        page_orgs = orgs[start:end]
        
        return {
            "data": page_orgs,
            "meta": {
                "current_page": page,
                "total_pages": (len(orgs) + per_page - 1) // per_page,
                "total_count": len(orgs),
                "per_page": per_page
            }
        }
    
    async def get_organization(self, org_id: str) -> Dict[str, Any]:
        """Mock get single organization."""
        self.api_calls.append(('get_organization', {'org_id': org_id}))
        
        for org in self.organizations:
            if org['id'] == str(org_id):
                return {"data": org}
        
        raise ValueError(f"Organization {org_id} not found")
    
    async def get_configurations(
        self,
        organization_id: Optional[str] = None,
        page: int = 1,
        per_page: int = 100,
        **kwargs
    ) -> Dict[str, Any]:
        """Mock get configurations."""
        self.api_calls.append(('get_configurations', kwargs))
        
        configs = self.configurations
        if organization_id:
            configs = [c for c in configs if c.get('organization_id') == str(organization_id)]
        
        # Simulate pagination
        start = (page - 1) * per_page
        end = start + per_page
        page_configs = configs[start:end]
        
        return {
            "data": page_configs,
            "meta": {
                "current_page": page,
                "total_pages": (len(configs) + per_page - 1) // per_page,
                "total_count": len(configs),
                "per_page": per_page
            }
        }
    
    async def get_documents(
        self,
        organization_id: Optional[str] = None,
        page: int = 1,
        per_page: int = 100,
        **kwargs
    ) -> Dict[str, Any]:
        """Mock get documents."""
        self.api_calls.append(('get_documents', kwargs))
        
        docs = self.documents
        if organization_id:
            docs = [d for d in docs if d.get('organization_id') == str(organization_id)]
        
        # Simulate pagination
        start = (page - 1) * per_page
        end = start + per_page
        page_docs = docs[start:end]
        
        return {
            "data": page_docs,
            "meta": {
                "current_page": page,
                "total_pages": (len(docs) + per_page - 1) // per_page,
                "total_count": len(docs),
                "per_page": per_page
            }
        }
    
    async def get_document(self, doc_id: str) -> Dict[str, Any]:
        """Mock get single document."""
        self.api_calls.append(('get_document', {'doc_id': doc_id}))
        
        for doc in self.documents:
            if doc['id'] == str(doc_id):
                return {"data": doc}
        
        raise ValueError(f"Document {doc_id} not found")
    
    async def get_flexible_assets(
        self,
        flexible_asset_type_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        page: int = 1,
        per_page: int = 100,
        **kwargs
    ) -> Dict[str, Any]:
        """Mock get flexible assets."""
        self.api_calls.append(('get_flexible_assets', kwargs))
        
        assets = self.flexible_assets
        if organization_id:
            assets = [a for a in assets if a.get('organization_id') == str(organization_id)]
        if flexible_asset_type_id:
            assets = [a for a in assets if a.get('flexible_asset_type_id') == str(flexible_asset_type_id)]
        
        # Simulate pagination
        start = (page - 1) * per_page
        end = start + per_page
        page_assets = assets[start:end]
        
        return {
            "data": page_assets,
            "meta": {
                "current_page": page,
                "total_pages": (len(assets) + per_page - 1) // per_page,
                "total_count": len(assets),
                "per_page": per_page
            }
        }
    
    async def get_flexible_asset(self, asset_id: str) -> Dict[str, Any]:
        """Mock get single flexible asset."""
        self.api_calls.append(('get_flexible_asset', {'asset_id': asset_id}))
        
        for asset in self.flexible_assets:
            if asset['id'] == str(asset_id):
                return {"data": asset}
        
        raise ValueError(f"Flexible asset {asset_id} not found")
    
    async def get_flexible_asset_types(
        self,
        page: int = 1,
        per_page: int = 100,
        **kwargs
    ) -> Dict[str, Any]:
        """Mock get flexible asset types."""
        self.api_calls.append(('get_flexible_asset_types', kwargs))
        
        types = self.asset_types
        
        # Simulate pagination
        start = (page - 1) * per_page
        end = start + per_page
        page_types = types[start:end]
        
        return {
            "data": page_types,
            "meta": {
                "current_page": page,
                "total_pages": (len(types) + per_page - 1) // per_page,
                "total_count": len(types),
                "per_page": per_page
            }
        }
    
    async def get_flexible_asset_type(self, type_id: str) -> Dict[str, Any]:
        """Mock get single flexible asset type."""
        self.api_calls.append(('get_flexible_asset_type', {'type_id': type_id}))
        
        for asset_type in self.asset_types:
            if asset_type['id'] == str(type_id):
                return {"data": asset_type}
        
        raise ValueError(f"Asset type {type_id} not found")
    
    async def get_locations(
        self,
        organization_id: Optional[str] = None,
        page: int = 1,
        per_page: int = 100,
        **kwargs
    ) -> Dict[str, Any]:
        """Mock get locations."""
        self.api_calls.append(('get_locations', kwargs))
        
        locs = self.locations
        if organization_id:
            locs = [l for l in locs if l.get('organization_id') == str(organization_id)]
        
        # Simulate pagination
        start = (page - 1) * per_page
        end = start + per_page
        page_locs = locs[start:end]
        
        return {
            "data": page_locs,
            "meta": {
                "current_page": page,
                "total_pages": (len(locs) + per_page - 1) // per_page,
                "total_count": len(locs),
                "per_page": per_page
            }
        }
    
    async def get_location(self, location_id: str) -> Dict[str, Any]:
        """Mock get single location."""
        self.api_calls.append(('get_location', {'location_id': location_id}))
        
        for loc in self.locations:
            if loc['id'] == str(location_id):
                return {"data": loc}
        
        raise ValueError(f"Location {location_id} not found")
    
    async def get_contacts(
        self,
        organization_id: Optional[str] = None,
        location_id: Optional[str] = None,
        page: int = 1,
        per_page: int = 100,
        **kwargs
    ) -> Dict[str, Any]:
        """Mock get contacts."""
        self.api_calls.append(('get_contacts', kwargs))
        
        contacts = self.contacts
        if organization_id:
            contacts = [c for c in contacts if c.get('organization_id') == str(organization_id)]
        if location_id:
            contacts = [c for c in contacts if c.get('location_id') == str(location_id)]
        
        # Simulate pagination
        start = (page - 1) * per_page
        end = start + per_page
        page_contacts = contacts[start:end]
        
        return {
            "data": page_contacts,
            "meta": {
                "current_page": page,
                "total_pages": (len(contacts) + per_page - 1) // per_page,
                "total_count": len(contacts),
                "per_page": per_page
            }
        }
    
    async def get_passwords(
        self,
        organization_id: Optional[str] = None,
        page: int = 1,
        per_page: int = 100,
        **kwargs
    ) -> Dict[str, Any]:
        """Mock get passwords (metadata only)."""
        self.api_calls.append(('get_passwords', kwargs))
        
        pwds = self.passwords
        if organization_id:
            pwds = [p for p in pwds if p.get('organization_id') == str(organization_id)]
        
        # Simulate pagination
        start = (page - 1) * per_page
        end = start + per_page
        page_pwds = pwds[start:end]
        
        return {
            "data": page_pwds,
            "meta": {
                "current_page": page,
                "total_pages": (len(pwds) + per_page - 1) // per_page,
                "total_count": len(pwds),
                "per_page": per_page
            }
        }
    
    # Utility methods for testing
    def reset_calls(self):
        """Reset API call tracking."""
        self.api_calls = []
    
    def get_call_count(self, method_name: str) -> int:
        """Get count of calls to a specific method."""
        return sum(1 for call in self.api_calls if call[0] == method_name)


def create_mock_itglue_client() -> MockITGlueClient:
    """Create a mock IT Glue client for testing."""
    return MockITGlueClient()