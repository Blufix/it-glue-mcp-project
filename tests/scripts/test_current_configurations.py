#!/usr/bin/env python3
"""Test current configurations for Faucets Limited to find firewall."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.settings import settings
from src.services.itglue.client import ITGlueClient

async def test_faucets_configurations():
    """Get all current configurations for Faucets Limited."""
    
    print("=" * 60)
    print("FAUCETS LIMITED - CURRENT CONFIGURATIONS")
    print("=" * 60)
    
    # Faucets Limited org ID
    org_id = "3183713165639879"
    
    client = ITGlueClient(
        api_key=settings.itglue_api_key,
        api_url=settings.itglue_api_url
    )
    
    try:
        print(f"\n📋 Organization: Faucets Limited (ID: {org_id})")
        print("\n🔍 Fetching ALL configurations...")
        
        # Get all configurations for Faucets Limited
        configs = await client.get_configurations(org_id=org_id)
        
        print(f"\n✅ Found {len(configs)} total configurations")
        
        # Categorize configurations
        firewalls = []
        switches = []
        servers = []
        workstations = []
        nas_devices = []
        ups_devices = []
        printers = []
        other = []
        
        for config in configs:
            name_lower = config.name.lower()
            type_lower = (config.configuration_type or "").lower()
            
            # Debug info for each config
            # print(f"  Config: {config.name} | Type: {config.configuration_type}")
            
            # Categorize based on name or type
            if 'firewall' in name_lower or 'firewall' in type_lower or 'sophos' in name_lower or 'xg' in name_lower:
                firewalls.append(config)
            elif 'switch' in name_lower or 'switch' in type_lower:
                switches.append(config)
            elif 'server' in name_lower or 'server' in type_lower:
                servers.append(config)
            elif 'workstation' in name_lower or 'workstation' in type_lower or 'desktop' in type_lower:
                workstations.append(config)
            elif 'nas' in name_lower or 'nas' in type_lower or 'qnap' in name_lower:
                nas_devices.append(config)
            elif 'ups' in name_lower or 'ups' in type_lower:
                ups_devices.append(config)
            elif 'printer' in name_lower or 'printer' in type_lower:
                printers.append(config)
            else:
                other.append(config)
        
        # Display categorized results
        print("\n" + "=" * 60)
        print("CONFIGURATION BREAKDOWN:")
        print("=" * 60)
        
        print(f"\n🔥 FIREWALLS ({len(firewalls)}):")
        if firewalls:
            for fw in firewalls:
                print(f"  ✅ {fw.name}")
                print(f"     Type: {fw.configuration_type}")
                print(f"     ID: {fw.id}")
        else:
            print("  ❌ No firewall configurations found")
            print("  💡 Looking for anything with 'firewall', 'sophos', or 'xg' in name/type")
        
        print(f"\n🔌 SWITCHES ({len(switches)}):")
        for sw in switches[:5]:  # Show first 5
            print(f"  - {sw.name} ({sw.configuration_type})")
        
        print(f"\n🖥️ SERVERS ({len(servers)}):")
        for srv in servers[:5]:  # Show first 5
            print(f"  - {srv.name} ({srv.configuration_type})")
        
        print(f"\n💾 NAS DEVICES ({len(nas_devices)}):")
        for nas in nas_devices:
            print(f"  - {nas.name} ({nas.configuration_type})")
        
        print(f"\n🔋 UPS DEVICES ({len(ups_devices)}):")
        for ups in ups_devices:
            print(f"  - {ups.name} ({ups.configuration_type})")
        
        print(f"\n🖨️ PRINTERS ({len(printers)}):")
        for printer in printers[:3]:  # Show first 3
            print(f"  - {printer.name} ({printer.configuration_type})")
        
        print(f"\n💻 WORKSTATIONS ({len(workstations)}):")
        print(f"  Total: {len(workstations)} workstations")
        
        print(f"\n❓ OTHER ({len(other)}):")
        for item in other[:10]:  # Show first 10
            print(f"  - {item.name} ({item.configuration_type})")
        
        # Search specifically for Sophos or firewall-related items
        print("\n" + "=" * 60)
        print("DETAILED FIREWALL SEARCH:")
        print("=" * 60)
        
        print("\n🔍 Searching for Sophos/Firewall in ALL configurations...")
        potential_firewalls = []
        for config in configs:
            search_text = f"{config.name} {config.configuration_type or ''}".lower()
            if any(keyword in search_text for keyword in ['sophos', 'firewall', 'xg', 'utm', 'security appliance']):
                potential_firewalls.append(config)
                print(f"\n  📍 Potential match found:")
                print(f"     Name: {config.name}")
                print(f"     Type: {config.configuration_type}")
                print(f"     ID: {config.id}")
        
        if not potential_firewalls:
            print("\n  ❌ No Sophos firewall found in current configurations")
            print("  💡 The firewall may have been:")
            print("     - Deleted from IT Glue")
            print("     - Renamed to something else")
            print("     - Moved to a different organization")
            print("     - Changed to a different configuration type")
        
    finally:
        await client.disconnect()
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print("=" * 60)
    if firewalls or potential_firewalls:
        print("✅ Firewall configurations found - search should work")
    else:
        print("❌ No firewall found - search needs updating or data needs adding")

if __name__ == "__main__":
    asyncio.run(test_faucets_configurations())