#!/usr/bin/env python3
"""Debug actual flexible assets in Streamlit context."""

import asyncio
from src.services.itglue.client import ITGlueClient

async def debug_flexible_assets():
    """Debug what's actually happening with flexible assets."""
    
    print("🔍 Debugging Flexible Assets in Streamlit Context")
    print("=" * 60)
    
    faucets_id = "3183713165639879"
    
    async with ITGlueClient() as client:
        
        # Test 1: Direct flexible assets call for Faucets
        print(f"\n1️⃣ Testing get_all_flexible_assets_for_org({faucets_id})...")
        try:
            assets = await client.get_all_flexible_assets_for_org(faucets_id)
            print(f"✅ Found {len(assets)} flexible assets!")
            
            if assets:
                print("\n📋 First 5 assets:")
                for i, asset in enumerate(assets[:5]):
                    print(f"   {i+1}. {asset.name} (Type: {asset.flexible_asset_type_id})")
                    
                # Find the Office 365 asset specifically
                email_assets = [a for a in assets if "office 365" in a.name.lower() or "email" in a.name.lower()]
                if email_assets:
                    print(f"\n📧 Found {len(email_assets)} email-related assets:")
                    for asset in email_assets:
                        print(f"   • {asset.name}")
                        if hasattr(asset, 'traits') and asset.traits:
                            for key, value in list(asset.traits.items())[:3]:
                                if value:
                                    print(f"     - {key}: {str(value)[:50]}...")
            
        except Exception as e:
            print(f"❌ Failed: {e}")
        
        # Test 2: Test the query logic that Streamlit uses
        print(f"\n2️⃣ Testing Streamlit query logic...")
        try:
            # This mimics what the Streamlit search does
            query = "list flexible assets"
            query_lower = query.lower()
            
            if "list flexible" in query_lower:
                print("✅ Query matches flexible assets condition")
                
                # Get flexible assets like Streamlit does
                flexible_assets = await client.get_all_flexible_assets_for_org(faucets_id)
                print(f"✅ Retrieved {len(flexible_assets)} flexible assets")
                
                # Check if any match
                results = []
                sources = []
                
                for asset in flexible_assets:
                    asset_name_lower = asset.name.lower()
                    match_found = True  # For "list flexible" we show all
                    
                    if match_found:
                        sources.append({
                            "type": "Flexible Asset",
                            "name": asset.name,
                            "confidence": 0.9
                        })
                        
                        asset_details = [f"**{asset.name}** (Flexible Asset)"]
                        if hasattr(asset, 'traits') and asset.traits:
                            for key, value in list(asset.traits.items())[:2]:
                                if value and str(value).strip():
                                    display_value = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                                    asset_details.append(f"  • {key}: {display_value}")
                        
                        results.append("\n".join(asset_details))
                        
                        if len(results) >= 10:  # Limit for testing
                            break
                
                print(f"✅ Created {len(results)} result items")
                print(f"✅ Created {len(sources)} source items")
                
                if results:
                    print("\n📄 Sample result:")
                    print(results[0])
        
        except Exception as e:
            print(f"❌ Streamlit query logic failed: {e}")

if __name__ == "__main__":
    asyncio.run(debug_flexible_assets())