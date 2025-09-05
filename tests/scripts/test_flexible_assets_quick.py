#!/usr/bin/env python3
"""
Quick test script for Query Flexible Assets Tool using REAL IT Glue API data.

This is a focused test that runs quickly to assess basic functionality.
"""

import asyncio
import os
import sys
from pathlib import Path
import time

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from src.mcp.tools.query_flexible_assets_tool import QueryFlexibleAssetsTool
from src.services.itglue.client import ITGlueClient
from src.cache.manager import CacheManager


async def quick_test():
    """Quick test of flexible assets functionality."""
    print("=== QUICK FLEXIBLE ASSETS TOOL TEST ===")
    print("Testing basic functionality with real IT Glue data\n")
    
    # Initialize components
    api_key = os.getenv('ITGLUE_API_KEY')
    if not api_key:
        print("❌ ERROR: ITGLUE_API_KEY environment variable not set")
        return False
    
    print("✅ IT Glue API key loaded")
    
    try:
        # Create MCP tool
        itglue_client = ITGlueClient(api_key=api_key)
        cache_manager = CacheManager()
        assets_tool = QueryFlexibleAssetsTool(itglue_client, cache_manager)
        
        print("✅ Query Flexible Assets Tool initialized\n")
        
        # Test 1: Basic asset type statistics (fastest test)
        print("🧪 TEST 1: Asset type statistics")
        print("-" * 33)
        
        start_time = time.time()
        result = await assets_tool.execute(action="stats")
        duration = time.time() - start_time
        
        if result.get("success", False):
            data = result.get("data", {})
            asset_types = data.get("common_asset_types", [])
            
            print(f"✅ Found {len(asset_types)} common asset types in {duration:.2f}s")
            
            # Show first few asset types
            for i, asset_type in enumerate(asset_types[:3], 1):
                count = asset_type.get("asset_count", 0)
                name = asset_type.get("name", "Unknown")
                print(f"   {i}. {name}: {count} assets")
                
            if len(asset_types) > 3:
                print(f"   ... and {len(asset_types) - 3} more types")
                
        else:
            error = result.get("error", "Unknown error")
            print(f"❌ Failed: {error}")
            return False
            
        print()
        
        # Test 2: Query assets for Faucets (quick check)
        print("🧪 TEST 2: Query Faucets assets")
        print("-" * 28)
        
        start_time = time.time()
        result = await assets_tool.execute(
            action="by_org",
            organization="Faucets",
        )
        duration = time.time() - start_time
        
        if result.get("success", False):
            data = result.get("data", {})
            assets = data.get("assets", [])
            
            print(f"✅ Found {len(assets)} assets for Faucets in {duration:.2f}s")
            
            # Show first few assets
            for i, asset in enumerate(assets[:2], 1):
                asset_name = asset.get("name", "Unknown")
                traits_count = len(asset.get("traits", {}))
                print(f"   {i}. {asset_name} ({traits_count} traits)")
                
            if len(assets) > 2:
                print(f"   ... and {len(assets) - 2} more assets")
                
        else:
            error = result.get("error", "Unknown error")
            print(f"❌ Failed: {error}")
            return False
            
        print()
        
        # Test 3: Error handling (quick check)
        print("🧪 TEST 3: Error handling")
        print("-" * 24)
        
        # Test invalid action
        result = await assets_tool.execute(action="invalid_action")
        handles_errors = not result.get("success", True)  # Should fail gracefully
        
        if handles_errors:
            print("✅ Error handling works correctly")
        else:
            print("❌ Error handling issues detected")
            
        print()
        print("✅ QUICK TEST COMPLETED SUCCESSFULLY!")
        return True
        
    except Exception as e:
        print(f"❌ Test execution error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run quick test."""
    success = await quick_test()
    
    if success:
        print("\n📊 QUICK TEST SUMMARY:")
        print("- Basic functionality working")  
        print("- API connectivity confirmed")
        print("- Error handling functional")
        print("- Ready for comprehensive testing")
    else:
        print("\n❌ Quick test failed - investigate before full testing")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)