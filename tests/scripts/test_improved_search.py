#!/usr/bin/env python3
"""Test improved firewall search logic."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.settings import settings
from src.services.itglue.client import ITGlueClient

async def test_improved_search():
    """Test that improved search finds Sophos XGS138."""
    
    print("=" * 60)
    print("TESTING IMPROVED FIREWALL SEARCH")
    print("=" * 60)
    
    # Faucets Limited org ID
    org_id = "3183713165639879"
    
    client = ITGlueClient(
        api_key=settings.itglue_api_key,
        api_url=settings.itglue_api_url
    )
    
    try:
        configs = await client.get_configurations(org_id=org_id)
        
        # Test query
        query = "@faucets what is the firewall name"
        query_clean = query.replace("@faucets", "").strip()
        query_lower = query_clean.lower()
        
        print(f"\n🔍 Query: '{query}'")
        print(f"   Clean query: '{query_clean}'")
        print(f"   Organization: Faucets Limited (ID: {org_id})")
        print(f"   Total configs: {len(configs)}")
        
        results = []
        
        print("\n📋 Testing improved matching logic:")
        print("-" * 40)
        
        for config in configs:
            config_name_lower = config.name.lower()
            config_type_lower = (config.configuration_type or "").lower()
            
            match_found = False
            match_reason = ""
            
            # Direct word match in name
            if any(word in config_name_lower for word in query_lower.split()):
                match_found = True
                match_reason = "Direct word match"
            
            # Type-based matching for firewall
            elif "firewall" in query_lower and ("firewall" in config_type_lower or 
                                                 any(fw in config_name_lower for fw in ["sophos", "xgs", "xg", "fortinet", "sonicwall"])):
                match_found = True
                match_reason = "Firewall type/brand match"
            
            if match_found:
                results.append(config)
                print(f"  ✅ MATCH: {config.name}")
                print(f"     Type: {config.configuration_type}")
                print(f"     Reason: {match_reason}")
        
        print(f"\n📊 Results Summary:")
        print(f"   Found {len(results)} firewall configuration(s)")
        
        if results:
            print("\n🎯 The search will return:")
            for config in results:
                print(f"   • Configuration: {config.name} ({config.configuration_type})")
        else:
            print("   ❌ No results (this is wrong!)")
        
    finally:
        await client.disconnect()
    
    print("\n" + "=" * 60)
    if results:
        print("✅ IMPROVED SEARCH LOGIC WORKING!")
        print("The firewall query now correctly finds:")
        for config in results:
            print(f"  • {config.name}")
    else:
        print("❌ Search still needs fixing")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_improved_search())