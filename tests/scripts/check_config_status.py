#!/usr/bin/env python3
"""
Check configuration status values to understand how archived items are marked.
"""

import asyncio
import sys
from pathlib import Path
from collections import Counter

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.services.itglue import ITGlueClient
from src.config.settings import settings

async def check_configuration_statuses():
    """Check all unique status values for configurations."""
    
    print("=" * 80)
    print("IT GLUE CONFIGURATION STATUS CHECK")
    print("=" * 80)
    
    client = ITGlueClient(
        api_key=settings.itglue_api_key,
        api_url=settings.itglue_api_url
    )
    
    try:
        # Find Faucets
        print("\nFetching organizations...")
        orgs = await client.get_organizations()
        faucets_org = None
        for org in orgs:
            if "faucets" in org.name.lower():
                faucets_org = org
                print(f"✓ Found: {org.name} (ID: {org.id})")
                break
        
        if not faucets_org:
            print("⚠️ Faucets not found")
            return
        
        # Get configurations
        print(f"\nFetching configurations for {faucets_org.name}...")
        configs = await client.get_configurations(org_id=faucets_org.id)
        print(f"✓ Found {len(configs)} configurations")
        
        # Analyze status fields
        status_counter = Counter()
        archived_examples = []
        active_examples = []
        
        for config in configs:
            attrs = config.attributes if hasattr(config, 'attributes') else {}
            
            # Check various status fields
            status = attrs.get('configuration-status-name') or 'Unknown'
            status_counter[status] += 1
            
            # Collect examples of different statuses
            status_lower = status.lower() if status else ""
            if 'archive' in status_lower or 'inactive' in status_lower or 'retired' in status_lower:
                if len(archived_examples) < 3:
                    archived_examples.append({
                        'name': config.name,
                        'type': config.configuration_type,
                        'status': status
                    })
            elif 'active' in status_lower or status == 'Unknown':
                if len(active_examples) < 3:
                    active_examples.append({
                        'name': config.name,
                        'type': config.configuration_type,
                        'status': status
                    })
        
        # Display results
        print("\n" + "=" * 80)
        print("CONFIGURATION STATUSES FOUND")
        print("=" * 80)
        
        for status, count in status_counter.most_common():
            print(f"\n📊 Status: '{status}' - {count} items")
        
        print("\n" + "=" * 80)
        print("EXAMPLES OF ARCHIVED/INACTIVE")
        print("=" * 80)
        if archived_examples:
            for ex in archived_examples:
                print(f"• {ex['name']} ({ex['type']}) - Status: '{ex['status']}'")
        else:
            print("No archived/inactive items found")
        
        print("\n" + "=" * 80)
        print("EXAMPLES OF ACTIVE")
        print("=" * 80)
        if active_examples:
            for ex in active_examples:
                print(f"• {ex['name']} ({ex['type']}) - Status: '{ex['status']}'")
        
        # Check correlation between status and archived field
        print("\n" + "=" * 80)
        print("STATUS vs ARCHIVED FIELD ANALYSIS")
        print("=" * 80)
        
        # Analyze correlation
        status_archived_combo = Counter()
        
        for config in configs:
            attrs = config.attributes if hasattr(config, 'attributes') else {}
            status = attrs.get('configuration-status-name') or 'Unknown'
            archived = attrs.get('archived', False)
            
            combo = f"Status={status}, Archived={archived}"
            status_archived_combo[combo] += 1
        
        print("\nCombinations found:")
        for combo, count in status_archived_combo.most_common():
            print(f"• {combo}: {count} items")
        
        # Show specific examples of "Inactive" items
        print("\n" + "=" * 80)
        print("ALL INACTIVE ITEMS")
        print("=" * 80)
        
        inactive_items = []
        for config in configs:
            attrs = config.attributes if hasattr(config, 'attributes') else {}
            status = attrs.get('configuration-status-name') or 'Unknown'
            
            if status == 'Inactive':
                inactive_items.append({
                    'name': config.name,
                    'type': config.configuration_type,
                    'status': status,
                    'archived': attrs.get('archived', False)
                })
        
        if inactive_items:
            for item in inactive_items:
                print(f"• {item['name']} ({item['type']})")
                print(f"  Status: {item['status']}, Archived field: {item['archived']}")
        else:
            print("No inactive items found")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await client.disconnect()
        print("\n✓ Status check complete")

if __name__ == "__main__":
    asyncio.run(check_configuration_statuses())