#!/usr/bin/env python3
"""Test direct email flexible asset method comparison."""

import asyncio
import logging
from src.services.itglue.client import ITGlueClient

logging.basicConfig(level=logging.DEBUG)

async def test_email_flexible_assets():
    """Compare direct API vs client method for Email flexible assets."""
    
    async with ITGlueClient() as client:
        print("🧪 Testing Email Flexible Assets - Direct vs Method")
        print("=" * 60)
        
        # Get Faucets organization ID
        orgs = await client.get_organizations(filters={"name": "Faucets Limited"})
        faucets_id = orgs[0].id
        print(f"✅ Faucets Limited ID: {faucets_id}")
        
        # Get Email asset type ID
        asset_types = await client.get_flexible_asset_types(include_fields=False)
        email_type = None
        for at in asset_types:
            if "email" in at.name.lower():
                email_type = at
                break
        
        if not email_type:
            print("❌ Email asset type not found")
            return
            
        print(f"✅ Email asset type: {email_type.name} (ID: {email_type.id})")
        
        # Test 1: Direct API call (this worked before)
        print(f"\n1️⃣ Direct API call...")
        try:
            params = {
                "filter[flexible-asset-type-id]": email_type.id,
                "filter[organization-id]": faucets_id
            }
            response = await client.get("flexible_assets", params)
            email_assets_direct = response.get('data', [])
            print(f"✅ Direct API: Found {len(email_assets_direct)} Email assets")
            
            for asset in email_assets_direct:
                attrs = asset.get('attributes', {})
                name = attrs.get('name', 'Unknown')
                print(f"   • {name}")
                
        except Exception as e:
            print(f"❌ Direct API failed: {e}")
        
        # Test 2: Client method
        print(f"\n2️⃣ Client method...")
        try:
            email_assets_method = await client.get_flexible_assets(
                org_id=faucets_id,
                asset_type_id=email_type.id
            )
            print(f"✅ Client method: Found {len(email_assets_method)} Email assets")
            
            for asset in email_assets_method:
                print(f"   • {asset.name}")
                
        except Exception as e:
            print(f"❌ Client method failed: {e}")
        
        # Test 3: Client method without get_all_pages (direct single call)
        print(f"\n3️⃣ Testing single page call...")
        try:
            params = {
                "filter[flexible-asset-type-id]": email_type.id,
                "filter[organization-id]": faucets_id,
                "page[size]": "50",
                "page[number]": "1"
            }
            response = await client.get("flexible_assets", params)
            email_assets_single = response.get('data', [])
            print(f"✅ Single page: Found {len(email_assets_single)} Email assets")
            
        except Exception as e:
            print(f"❌ Single page failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_email_flexible_assets())