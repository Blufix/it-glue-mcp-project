#!/usr/bin/env python3
"""Debug script to test flexible assets for Faucets Limited."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from tests.scripts.test_query_flexible_assets_tool import main as test_flexible_assets


async def debug_flexible_assets():
    """Debug flexible assets for Faucets Limited."""
    print("🔍 Debugging Flexible Assets for Faucets Limited")
    print("=" * 60)
    
    # Use the existing test script that was created for flexible assets
    try:
        await test_flexible_assets()
    except Exception as e:
        print(f"Test script failed: {e}")
        print("Let's try a direct approach...")
        
        # Import what we need
        from src.mcp.server import ITGlueMCPServer
        
        try:
            # Create MCP server
            server = ITGlueMCPServer()
            
            # Get the query_flexible_assets tool
            query_tool = server.server.tools.get('query_flexible_assets')
            if not query_tool:
                print("❌ query_flexible_assets tool not found in MCP server")
                return
            
            # Test different queries
            print("\n🧪 Testing flexible assets queries...")
            
            # Test 1: List all flexible assets
            print("1. Testing list all flexible assets...")
            result1 = await query_tool(action="list_all", limit=50)
            print(f"   Result: {result1.get('success', False)}")
            if result1.get('success'):
                count = result1.get('data', {}).get('count', 0)
                print(f"   Total flexible assets found: {count}")
            else:
                print(f"   Error: {result1.get('error', 'Unknown error')}")
            
            # Test 2: Get assets for Faucets specifically
            print("\n2. Testing flexible assets for Faucets...")
            result2 = await query_tool(action="by_org", organization="Faucets")
            print(f"   Result: {result2.get('success', False)}")
            if result2.get('success'):
                count = result2.get('data', {}).get('count', 0)
                print(f"   Faucets flexible assets found: {count}")
                if count > 0:
                    assets = result2.get('data', {}).get('assets', [])
                    print(f"   Sample assets:")
                    for i, asset in enumerate(assets[:3]):
                        print(f"     {i+1}. {asset.get('name', 'Unnamed')}")
            else:
                print(f"   Error: {result2.get('error', 'Unknown error')}")
            
            # Test 3: Get asset type statistics
            print("\n3. Testing asset type statistics...")
            result3 = await query_tool(action="stats")
            print(f"   Result: {result3.get('success', False)}")
            if result3.get('success'):
                data = result3.get('data', {})
                types = data.get('common_asset_types', [])
                print(f"   Asset types available: {len(types)}")
                for asset_type in types[:5]:
                    name = asset_type.get('name', 'Unknown')
                    count = asset_type.get('asset_count', 0)
                    print(f"     • {name}: {count} assets")
            else:
                print(f"   Error: {result3.get('error', 'Unknown error')}")
            
            # Test 4: Direct IT Glue API call
            print("\n4. Testing direct IT Glue API...")
            from src.services.itglue.client import ITGlueClient
            
            client = ITGlueClient()
            
            # Test get all flexible assets
            try:
                all_assets = await client.get_flexible_assets()
                print(f"   Total flexible assets via direct API: {len(all_assets)}")
            except Exception as e:
                print(f"   Error getting all assets: {e}")
                
            # Test get Faucets flexible assets
            try:
                faucets_assets = await client.get_flexible_assets(org_id="3183713165639879")
                print(f"   Faucets flexible assets via direct API: {len(faucets_assets)}")
                
                if faucets_assets:
                    print("   Sample Faucets flexible assets:")
                    for i, asset in enumerate(faucets_assets[:5]):
                        asset_name = asset.name if hasattr(asset, 'name') else "Unnamed"
                        asset_type = getattr(asset, 'flexible_asset_type_name', 'Unknown Type')
                        print(f"     {i+1}. {asset_name} ({asset_type})")
                        
                        # Show traits if available
                        if hasattr(asset, 'traits') and asset.traits:
                            trait_names = list(asset.traits.keys())[:3]
                            print(f"        Traits: {trait_names}")
                            
            except Exception as e:
                print(f"   Error getting Faucets assets: {e}")
                
            # Test get flexible asset types
            try:
                asset_types = await client.get_flexible_asset_types()
                print(f"   Flexible asset types available: {len(asset_types)}")
                
                enabled_types = [t for t in asset_types if getattr(t, 'enabled', True)]
                print(f"   Enabled asset types: {len(enabled_types)}")
                
                if enabled_types:
                    print("   Available asset types:")
                    for i, asset_type in enumerate(enabled_types[:10]):
                        type_name = asset_type.name if hasattr(asset_type, 'name') else "Unknown"
                        print(f"     {i+1}. {type_name}")
                        
            except Exception as e:
                print(f"   Error getting asset types: {e}")
                
            await client.disconnect()
            
        except Exception as e:
            print(f"❌ Direct test failed: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_flexible_assets())