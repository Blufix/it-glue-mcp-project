#!/usr/bin/env python3
"""Test printer search functionality."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.itglue.client import ITGlueClient
from src.config.settings import settings


async def test_printer_search():
    """Test that printer search works correctly."""
    
    print("=" * 60)
    print("TESTING PRINTER SEARCH")
    print("=" * 60)
    
    client = ITGlueClient(
        api_key=settings.itglue_api_key,
        api_url=settings.itglue_api_url
    )
    
    try:
        # Find Faucets organization
        orgs = await client.get_organizations()
        faucets_id = None
        for org in orgs:
            if "Faucets" in org.name:
                faucets_id = org.id
                print(f"\n✅ Found organization: {org.name} (ID: {org.id})")
                break
        
        if not faucets_id:
            print("❌ Faucets Limited not found")
            return
        
        # Get all configurations for Faucets
        print(f"\n📋 Fetching all configurations for Faucets Limited...")
        configs = await client.get_configurations(org_id=faucets_id)
        
        # Find printers
        print(f"\n🖨️  Looking for printers...")
        printers = []
        
        for config in configs:
            config_type = (config.configuration_type or "").lower()
            config_name = config.name.lower()
            
            # Debug: Show all configuration types
            if "printer" in config_type or "printer" in config_name:
                printers.append(config)
                attrs = config.attributes if hasattr(config, 'attributes') else {}
                
                print(f"\n✅ Found printer: {config.name}")
                print(f"   Type: {config.configuration_type}")
                print(f"   IP: {attrs.get('primary-ip', 'N/A')}")
                print(f"   Serial: {attrs.get('serial-number', 'N/A')}")
                print(f"   Manufacturer: {attrs.get('manufacturer-name', 'N/A')}")
                print(f"   Model: {attrs.get('model-name', 'N/A')}")
        
        print(f"\n📊 Summary:")
        print(f"   Total configurations: {len(configs)}")
        print(f"   Printers found: {len(printers)}")
        
        # Show all configuration types to debug
        print(f"\n📋 All configuration types in Faucets:")
        type_counts = {}
        for config in configs:
            config_type = config.configuration_type or "Unknown"
            if config_type not in type_counts:
                type_counts[config_type] = []
            type_counts[config_type].append(config.name)
        
        for config_type, names in sorted(type_counts.items()):
            print(f"\n   {config_type} ({len(names)}):")
            for name in names[:3]:  # Show first 3 of each type
                print(f"      - {name}")
            if len(names) > 3:
                print(f"      ... and {len(names) - 3} more")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        await client.disconnect()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_printer_search())