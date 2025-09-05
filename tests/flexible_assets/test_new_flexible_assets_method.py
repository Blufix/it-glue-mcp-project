#!/usr/bin/env python3
"""Test the new flexible assets method."""

import asyncio
import logging
from src.services.itglue.client import ITGlueClient

logging.basicConfig(level=logging.INFO)

async def test_new_flexible_assets_method():
    """Test the new get_all_flexible_assets_for_org method."""
    
    async with ITGlueClient() as client:
        print("🧪 Testing New Flexible Assets Method")
        print("=" * 50)
        
        # Get Faucets organization ID
        orgs = await client.get_organizations(filters={"name": "Faucets Limited"})
        if not orgs:
            print("❌ Faucets Limited not found")
            return
        
        faucets_id = orgs[0].id
        print(f"✅ Testing with Faucets Limited (ID: {faucets_id})")
        
        # Test new method
        print(f"\n🔍 Getting all flexible assets for Faucets...")
        assets = await client.get_all_flexible_assets_for_org(faucets_id)
        
        print(f"✅ Found {len(assets)} total flexible assets!")
        print()
        
        # Display details
        for i, asset in enumerate(assets, 1):
            print(f"{i}. {asset.name}")
            print(f"   Type ID: {asset.flexible_asset_type_id}")
            print(f"   Organization: {asset.organization_id}")
            
            # Show key traits
            interesting_traits = {}
            for key, value in asset.traits.items():
                if value and str(value).strip():
                    # Look for common interesting fields
                    key_lower = key.lower()
                    if any(term in key_lower for term in ['domain', 'email', 'url', 'server', 'location', 'enabled', 'ip', 'address']):
                        interesting_traits[key] = value
            
            if interesting_traits:
                print("   Key traits:")
                for key, value in list(interesting_traits.items())[:5]:
                    display_value = str(value)[:80] + "..." if len(str(value)) > 80 else str(value)
                    print(f"   - {key}: {display_value}")
            print()

if __name__ == "__main__":
    asyncio.run(test_new_flexible_assets_method())