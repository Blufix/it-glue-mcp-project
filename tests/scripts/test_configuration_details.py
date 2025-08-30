#!/usr/bin/env python3
"""Test to see all available attributes for configurations."""

import asyncio
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.settings import settings
from src.services.itglue.client import ITGlueClient

async def test_configuration_details():
    """Get detailed attributes for firewall configurations."""
    
    print("=" * 60)
    print("CONFIGURATION DETAILED ATTRIBUTES")
    print("=" * 60)
    
    # Faucets Limited org ID
    org_id = "3183713165639879"
    
    client = ITGlueClient(
        api_key=settings.itglue_api_key,
        api_url=settings.itglue_api_url
    )
    
    try:
        # Get configurations for Faucets Limited
        configs = await client.get_configurations(org_id=org_id)
        
        # Find firewall configurations
        firewall_configs = []
        for config in configs:
            if "firewall" in (config.configuration_type or "").lower() or \
               any(fw in config.name.lower() for fw in ["sophos", "xgs", "xg"]):
                firewall_configs.append(config)
        
        print(f"\n📋 Found {len(firewall_configs)} firewall configuration(s)")
        
        for config in firewall_configs:
            print(f"\n{'=' * 60}")
            print(f"🔥 FIREWALL: {config.name}")
            print(f"{'=' * 60}")
            
            # Basic info
            print(f"\n📌 Basic Information:")
            print(f"  • ID: {config.id}")
            print(f"  • Name: {config.name}")
            print(f"  • Type: {config.configuration_type}")
            
            # All attributes
            print(f"\n📊 All Available Attributes:")
            
            # Access raw attributes
            if hasattr(config, 'attributes') and config.attributes:
                for key, value in sorted(config.attributes.items()):
                    if value is not None and value != "" and value != []:
                        # Format the key nicely
                        display_key = key.replace('-', ' ').replace('_', ' ').title()
                        
                        # Handle different value types
                        if isinstance(value, list):
                            if value:  # Only show non-empty lists
                                print(f"  • {display_key}: {', '.join(str(v) for v in value)}")
                        elif isinstance(value, dict):
                            if value:  # Only show non-empty dicts
                                print(f"  • {display_key}: {json.dumps(value, indent=4)}")
                        else:
                            print(f"  • {display_key}: {value}")
            
            # Check for relationships
            if hasattr(config, 'relationships') and config.relationships:
                print(f"\n🔗 Relationships:")
                for rel_key, rel_value in config.relationships.items():
                    if rel_value:
                        print(f"  • {rel_key}: {rel_value}")
        
        # Also check a regular workstation for comparison
        print(f"\n\n{'=' * 60}")
        print("📊 COMPARISON: Regular Device Attributes")
        print(f"{'=' * 60}")
        
        # Find a workstation
        for config in configs[:5]:
            if "desktop" in (config.configuration_type or "").lower():
                print(f"\n💻 WORKSTATION: {config.name}")
                if hasattr(config, 'attributes') and config.attributes:
                    for key, value in sorted(config.attributes.items())[:10]:
                        if value is not None and value != "" and value != []:
                            display_key = key.replace('-', ' ').replace('_', ' ').title()
                            print(f"  • {display_key}: {value}")
                break
        
    finally:
        await client.disconnect()
    
    print("\n" + "=" * 60)
    print("KEY ATTRIBUTES TO DISPLAY:")
    print("=" * 60)
    print("The search results should show:")
    print("  • Name & Type")
    print("  • IP Address (primary-ip)")
    print("  • Serial Number")
    print("  • Install Date (installed-at)")
    print("  • Operating System")
    print("  • Manufacturer & Model")
    print("  • Location")
    print("  • Notes")
    print("  • Related passwords")
    print("  • Related configurations")

if __name__ == "__main__":
    asyncio.run(test_configuration_details())