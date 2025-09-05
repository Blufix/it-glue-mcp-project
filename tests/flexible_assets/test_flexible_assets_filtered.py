#!/usr/bin/env python3
"""Test IT Glue flexible assets with proper organization filtering."""

import asyncio
import logging
from src.services.itglue.client import ITGlueClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_flexible_assets_with_filters():
    """Test flexible assets endpoints with proper organization filtering."""
    
    async with ITGlueClient() as client:
        print("🧪 Testing IT Glue Flexible Assets with Organization Filters")
        print("=" * 70)
        
        # First, get Faucets organization ID
        print("\n1️⃣ Getting Faucets Limited organization ID...")
        try:
            orgs = await client.get_organizations(filters={"name": "Faucets Limited"})
            if not orgs:
                print("❌ Faucets Limited not found")
                return
            
            faucets_id = orgs[0].id
            print(f"✅ Found Faucets Limited: ID = {faucets_id}")
        except Exception as e:
            print(f"❌ Failed to get organization: {e}")
            return
        
        # Test 2: Get flexible asset types (this works)
        print(f"\n2️⃣ Getting flexible asset types...")
        try:
            asset_types = await client.get_flexible_asset_types(include_fields=False)
            print(f"✅ Found {len(asset_types)} asset types")
            
            # Show first few enabled types
            enabled_types = [at for at in asset_types if at.enabled][:5]
            for at in enabled_types:
                print(f"   • {at.name} (ID: {at.id})")
                
        except Exception as e:
            print(f"❌ Failed to get asset types: {e}")
            return
        
        # Test 3: Try flexible assets with organization filter
        print(f"\n3️⃣ Testing flexible assets with organization filter...")
        try:
            params = {
                "filter[organization-id]": faucets_id
            }
            response = await client.get("flexible_assets", params)
            assets_data = response.get('data', [])
            print(f"✅ Found {len(assets_data)} flexible assets for Faucets")
            
            # Show details of assets found
            for asset in assets_data[:3]:
                attrs = asset.get('attributes', {})
                name = attrs.get('name', 'Unknown')
                asset_type_id = attrs.get('flexible-asset-type-id')
                org_id = attrs.get('organization-id')
                print(f"   • {name}")
                print(f"     - Type ID: {asset_type_id}")
                print(f"     - Org ID: {org_id}")
                
                # Show traits (the actual data)
                traits = attrs.get('traits', {})
                if traits:
                    print(f"     - Traits ({len(traits)} fields):")
                    for key, value in list(traits.items())[:5]:  # Show first 5 traits
                        if value and str(value).strip():
                            # Truncate long values
                            display_value = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
                            print(f"       * {key}: {display_value}")
                print()
                
        except Exception as e:
            print(f"❌ Flexible assets with org filter failed: {e}")
        
        # Test 4: Try without organization filter but with pagination
        print(f"\n4️⃣ Testing flexible assets without org filter (paginated)...")
        try:
            params = {
                "page[size]": "10",
                "page[number]": "1"
            }
            response = await client.get("flexible_assets", params)
            assets_data = response.get('data', [])
            print(f"✅ Found {len(assets_data)} flexible assets (first page)")
            
        except Exception as e:
            print(f"❌ Flexible assets without org filter failed: {e}")
        
        # Test 5: Try with specific asset type filter
        if enabled_types:
            email_type = None
            for at in asset_types:
                if "email" in at.name.lower():
                    email_type = at
                    break
            
            if email_type:
                print(f"\n5️⃣ Testing flexible assets for Email type (ID: {email_type.id})...")
                try:
                    params = {
                        "filter[flexible-asset-type-id]": email_type.id,
                        "filter[organization-id]": faucets_id
                    }
                    response = await client.get("flexible_assets", params)
                    email_assets = response.get('data', [])
                    print(f"✅ Found {len(email_assets)} Email assets for Faucets")
                    
                    for asset in email_assets:
                        attrs = asset.get('attributes', {})
                        name = attrs.get('name', 'Unknown')
                        traits = attrs.get('traits', {})
                        print(f"   • {name}")
                        
                        # Show email-specific traits
                        email_fields = ['domain', 'domains', 'spf', 'dkim', 'dmarc', 'mfa', 'service-location']
                        for field in email_fields:
                            for key, value in traits.items():
                                if field in key.lower() and value:
                                    print(f"     - {key}: {value}")
                        print()
                        
                except Exception as e:
                    print(f"❌ Email assets failed: {e}")
        
        print("\n" + "=" * 70)
        print("🏁 Flexible Assets API Test Complete!")

if __name__ == "__main__":
    asyncio.run(test_flexible_assets_with_filters())