#!/usr/bin/env python3
"""Direct test of IT Glue flexible assets API endpoints."""

import asyncio
import logging
from src.services.itglue.client import ITGlueClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_flexible_assets_endpoints():
    """Test flexible assets endpoints directly."""
    
    async with ITGlueClient() as client:
        print("🧪 Testing IT Glue Flexible Assets API Endpoints")
        print("=" * 60)
        
        # Test 1: Flexible Asset Types
        print("\n1️⃣ Testing /flexible_asset_types endpoint...")
        try:
            response = await client.get("flexible_asset_types")
            print(f"✅ flexible_asset_types: {len(response.get('data', []))} types found")
            
            # Show first few types
            for i, asset_type in enumerate(response.get('data', [])[:3]):
                name = asset_type.get('attributes', {}).get('name', 'Unknown')
                enabled = asset_type.get('attributes', {}).get('enabled', False)
                print(f"   • {name} (enabled: {enabled})")
                
        except Exception as e:
            print(f"❌ flexible_asset_types failed: {e}")
        
        # Test 2: Flexible Assets (all)
        print("\n2️⃣ Testing /flexible_assets endpoint...")
        try:
            response = await client.get("flexible_assets")
            print(f"✅ flexible_assets: {len(response.get('data', []))} assets found")
            
            # Show first few assets
            for i, asset in enumerate(response.get('data', [])[:3]):
                name = asset.get('attributes', {}).get('name', 'Unknown')
                org_id = asset.get('attributes', {}).get('organization-id')
                asset_type_id = asset.get('attributes', {}).get('flexible-asset-type-id')
                print(f"   • {name} (org: {org_id}, type: {asset_type_id})")
                
        except Exception as e:
            print(f"❌ flexible_assets failed: {e}")
        
        # Test 3: Faucets Organization ID
        print("\n3️⃣ Finding Faucets Limited organization...")
        try:
            orgs = await client.get_organizations(filters={"name": "Faucets Limited"})
            if orgs:
                faucets_id = orgs[0].id
                print(f"✅ Found Faucets Limited: ID = {faucets_id}")
                
                # Test 4: Flexible Assets for Faucets
                print(f"\n4️⃣ Testing flexible assets for Faucets (ID: {faucets_id})...")
                try:
                    # Try organization-specific endpoint
                    faucets_assets = await client.get_flexible_assets(org_id=faucets_id)
                    print(f"✅ Faucets flexible assets: {len(faucets_assets)} found")
                    
                    for asset in faucets_assets:
                        print(f"   • {asset.name} (type: {asset.flexible_asset_type_id})")
                        # Show some traits
                        for key, value in list(asset.traits.items())[:3]:
                            if value:
                                print(f"     - {key}: {value}")
                                
                except Exception as e:
                    print(f"❌ Faucets flexible assets failed: {e}")
                    
            else:
                print("❌ Faucets Limited not found")
                
        except Exception as e:
            print(f"❌ Organization lookup failed: {e}")
        
        print("\n" + "=" * 60)
        print("🏁 Test completed!")

if __name__ == "__main__":
    asyncio.run(test_flexible_assets_endpoints())