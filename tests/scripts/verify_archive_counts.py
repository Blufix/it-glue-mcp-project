#!/usr/bin/env python3
"""
Verify counts after filtering by archived=true.
"""

import asyncio
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent))

from src.services.itglue import ITGlueClient
from src.config.settings import settings

async def verify_archive_filtering():
    """Check what remains after filtering archived items."""
    
    print("=" * 80)
    print("VERIFYING ARCHIVE FILTERING")
    print("=" * 80)
    
    client = ITGlueClient(
        api_key=settings.itglue_api_key,
        api_url=settings.itglue_api_url
    )
    
    try:
        # Find Faucets
        print("\nFetching Faucets Limited...")
        orgs = await client.get_organizations()
        faucets_org = None
        for org in orgs:
            if "faucets" in org.name.lower():
                faucets_org = org
                print(f"✓ Found: {org.name}")
                break
        
        if not faucets_org:
            return
        
        # Get configurations
        print(f"\nFetching all configurations...")
        configs = await client.get_configurations(org_id=faucets_org.id)
        total_count = len(configs)
        print(f"✓ Total configurations: {total_count}")
        
        # Filter out archived
        active_configs = []
        archived_configs = []
        
        for config in configs:
            attrs = config.attributes if hasattr(config, 'attributes') else {}
            is_archived = attrs.get('archived', False)
            
            if is_archived:
                archived_configs.append(config)
            else:
                active_configs.append(config)
        
        print(f"\n📊 After filtering archived=true:")
        print(f"   • Active (archived=false): {len(active_configs)} items")
        print(f"   • Archived (archived=true): {len(archived_configs)} items")
        
        # Show breakdown of active configs by type
        print("\n" + "=" * 80)
        print("ACTIVE CONFIGURATIONS BY TYPE")
        print("=" * 80)
        
        type_counter = Counter()
        for config in active_configs:
            config_type = config.configuration_type or "Unknown"
            type_counter[config_type] += 1
        
        for config_type, count in type_counter.most_common():
            print(f"• {config_type}: {count} items")
        
        # Show some examples of what will be shown
        print("\n" + "=" * 80)
        print("EXAMPLES OF CONFIGS THAT WILL BE SHOWN")
        print("=" * 80)
        
        for config in active_configs[:5]:
            attrs = config.attributes if hasattr(config, 'attributes') else {}
            status = attrs.get('configuration-status-name', 'Unknown')
            print(f"• {config.name} ({config.configuration_type})")
            print(f"  Status: {status}, Archived: False")
        
        # Show network devices that will be included
        print("\n" + "=" * 80)
        print("NETWORK DEVICES THAT WILL BE SHOWN")
        print("=" * 80)
        
        network_types = ["firewall", "switch", "ubiquiti access point", "printer", "server", "nas", "network device"]
        network_devices = []
        
        for config in active_configs:
            config_type_lower = (config.configuration_type or "").lower()
            if any(nt in config_type_lower for nt in network_types):
                network_devices.append(config)
        
        print(f"\nTotal network devices (not archived): {len(network_devices)}")
        for device in network_devices[:10]:
            print(f"• {device.name} ({device.configuration_type})")
        
        if len(network_devices) > 10:
            print(f"  ... and {len(network_devices) - 10} more")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await client.disconnect()
        print("\n✓ Verification complete")

if __name__ == "__main__":
    asyncio.run(verify_archive_filtering())