#!/usr/bin/env python3
"""
Discover all unique configuration types in IT Glue.
This will help us understand what types are available for matching.
"""

import asyncio
import sys
from pathlib import Path
from collections import Counter

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.services.itglue import ITGlueClient
from src.config.settings import settings

async def discover_configuration_types():
    """Fetch all configurations and list unique types."""
    
    print("=" * 80)
    print("IT GLUE CONFIGURATION TYPE DISCOVERY")
    print("=" * 80)
    
    client = ITGlueClient(
        api_key=settings.itglue_api_key,
        api_url=settings.itglue_api_url
    )
    
    try:
        # First, get organizations to show we can fetch specific org data
        print("\nFetching organizations...")
        orgs = await client.get_organizations()
        
        # Find Faucets Limited
        faucets_org = None
        for org in orgs:
            if "faucets" in org.name.lower():
                faucets_org = org
                print(f"✓ Found Faucets: {org.name} (ID: {org.id})")
                break
        
        if not faucets_org:
            print("⚠️ Faucets organization not found, will analyze all orgs")
        
        # Get configurations
        print("\nFetching configurations...")
        if faucets_org:
            print(f"Getting configurations for {faucets_org.name}...")
            configs = await client.get_configurations(org_id=faucets_org.id)
        else:
            print("Getting configurations from all organizations...")
            configs = await client.get_configurations()
        
        print(f"✓ Found {len(configs)} total configurations")
        
        # Collect all unique configuration types
        type_counter = Counter()
        types_with_examples = {}
        
        for config in configs:
            config_type = config.configuration_type or "Unknown/None"
            type_counter[config_type] += 1
            
            # Store first few examples of each type
            if config_type not in types_with_examples:
                types_with_examples[config_type] = []
            if len(types_with_examples[config_type]) < 3:
                types_with_examples[config_type].append(config.name)
        
        # Display results
        print("\n" + "=" * 80)
        print("CONFIGURATION TYPES FOUND")
        print("=" * 80)
        
        # Sort by count (most common first)
        for config_type, count in type_counter.most_common():
            print(f"\n📦 {config_type}: {count} items")
            print(f"   Examples:")
            for example in types_with_examples[config_type]:
                print(f"   • {example}")
        
        # Summary statistics
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total unique types: {len(type_counter)}")
        print(f"Total configurations: {sum(type_counter.values())}")
        
        # List all types as a Python list for easy copying
        print("\n" + "=" * 80)
        print("PYTHON LIST OF ALL TYPES (for code use):")
        print("=" * 80)
        all_types = sorted(type_counter.keys())
        print("configuration_types = [")
        for t in all_types:
            print(f'    "{t}",')
        print("]")
        
        # Also check what attributes are commonly available
        print("\n" + "=" * 80)
        print("COMMON ATTRIBUTES FOUND")
        print("=" * 80)
        
        # Sample first 10 configs to see what attributes they have
        attribute_counter = Counter()
        for config in configs[:20]:
            if hasattr(config, 'attributes') and config.attributes:
                for attr_key in config.attributes.keys():
                    attribute_counter[attr_key] += 1
        
        print("\nMost common attributes:")
        for attr, count in attribute_counter.most_common(20):
            print(f"  • {attr}: found in {count}/20 configs")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await client.disconnect()
        print("\n✓ Discovery complete")

if __name__ == "__main__":
    asyncio.run(discover_configuration_types())