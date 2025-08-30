#!/usr/bin/env python3
"""Test firewall search logic to debug why it's not finding Sophos XGS138."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.settings import settings
from src.services.itglue.client import ITGlueClient

async def test_firewall_search():
    """Test different search queries for firewall."""
    
    print("=" * 60)
    print("TESTING FIREWALL SEARCH LOGIC")
    print("=" * 60)
    
    # Faucets Limited org ID
    org_id = "3183713165639879"
    
    client = ITGlueClient(
        api_key=settings.itglue_api_key,
        api_url=settings.itglue_api_url
    )
    
    try:
        # Test different query variations
        test_queries = [
            "@faucets what is the name of the firewall",
            "@faucets firewall details",
            "@faucets sophos",
            "@faucets xgs138",
            "firewall at faucets"
        ]
        
        print(f"\n📋 Testing queries for Faucets Limited (ID: {org_id})")
        
        # Get configurations
        configs = await client.get_configurations(org_id=org_id)
        print(f"Total configurations: {len(configs)}")
        
        for query in test_queries:
            print(f"\n🔍 Query: '{query}'")
            print("-" * 40)
            
            # Remove @faucets if present
            query_clean = query.replace("@faucets", "").strip()
            query_lower = query_clean.lower()
            
            # Search logic (mimicking the Streamlit app)
            found_items = []
            
            # Check if we should search configurations
            if any(word in query_lower for word in ["firewall", "sophos", "xgs", "configuration", "device", "network"]):
                print("  ✓ Triggers configuration search")
                
                # Search through configurations
                for config in configs[:10]:  # Limit to first 10 like in app
                    config_name_lower = config.name.lower()
                    
                    # Check if any word from query matches config name
                    query_words = query_lower.split()
                    matches = False
                    
                    for word in query_words:
                        if word in config_name_lower:
                            matches = True
                            break
                    
                    if matches:
                        found_items.append(f"    ✅ MATCH: {config.name} ({config.configuration_type})")
                    
                # Also check with broader matching
                print("\n  Broader search (any keyword in name):")
                for config in configs:
                    if any(kw in config.name.lower() for kw in ["firewall", "sophos", "xgs", "xg"]):
                        print(f"    🎯 {config.name} ({config.configuration_type})")
            else:
                print("  ✗ Does NOT trigger configuration search")
            
            if found_items:
                print("  Results found:")
                for item in found_items:
                    print(item)
            else:
                print("  ❌ No matches with current logic")
        
        # Show what SHOULD be found
        print("\n" + "=" * 60)
        print("EXPECTED RESULTS:")
        print("=" * 60)
        print("The search SHOULD find:")
        print("  1. Sophos XGS138 (Type: Firewall)")
        print("  2. XGS138 (Type: Network Device (Firewall))")
        
        # Debug the exact matching logic
        print("\n" + "=" * 60)
        print("DEBUG: Why matching might fail")
        print("=" * 60)
        
        query = "what is the name of the firewall at faucets"
        query_words = query.lower().split()
        print(f"Query words: {query_words}")
        
        firewall_configs = [c for c in configs if 'sophos' in c.name.lower() or 'xgs' in c.name.lower()]
        for config in firewall_configs:
            print(f"\nConfig: {config.name}")
            print(f"Config name words: {config.name.lower().split()}")
            
            # Check word-by-word matching
            matches = []
            for word in query_words:
                if word in config.name.lower():
                    matches.append(word)
            
            if matches:
                print(f"  ✅ Matching words: {matches}")
            else:
                print(f"  ❌ No word matches")
                print(f"  💡 Issue: Query words don't match config name")
                print(f"     Query has 'firewall' but config is named 'Sophos XGS138'")
        
    finally:
        await client.disconnect()
    
    print("\n" + "=" * 60)
    print("SOLUTION:")
    print("=" * 60)
    print("The search logic needs to be improved to:")
    print("  1. Match by configuration TYPE as well as name")
    print("  2. Use semantic matching (firewall → Sophos, XGS)")
    print("  3. Not rely on exact word matching from query")

if __name__ == "__main__":
    asyncio.run(test_firewall_search())