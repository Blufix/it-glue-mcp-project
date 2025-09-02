#!/usr/bin/env python3
"""
Sync Faucets Limited data to local PostgreSQL database.
This populates the database so the search tool can work.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.mcp.server import ITGlueMCPServer
from datetime import datetime


async def sync_faucets_data():
    """Sync Faucets Limited data to local database."""
    
    print("=" * 80)
    print("SYNCING FAUCETS LIMITED DATA TO LOCAL DATABASE")
    print("=" * 80)
    print(f"Started: {datetime.now().isoformat()}\n")
    
    # Initialize server
    server = ITGlueMCPServer()
    
    print("Initializing components...")
    await server._initialize_components()
    
    # Find Faucets organization
    print("\nFinding Faucets Limited organization...")
    orgs = await server.itglue_client.get_organizations()
    
    faucets_org = None
    for org in orgs:
        if "faucets" in org.name.lower():
            faucets_org = org
            print(f"✅ Found: {org.name} (ID: {org.id})")
            break
    
    if not faucets_org:
        print("❌ Faucets Limited not found!")
        return
    
    # Sync the data
    print(f"\n🔄 Starting sync for Faucets Limited...")
    print("This may take a few minutes depending on data volume...\n")
    
    if server.sync_orchestrator:
        try:
            # Sync this specific organization
            stats = await server.sync_orchestrator.sync_organization(
                str(faucets_org.id)
            )
            
            print("\n✅ Sync completed!")
            print(f"Statistics: {stats}")
            
        except Exception as e:
            print(f"❌ Sync failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("❌ Sync orchestrator not initialized")
    
    # Check what was synced
    print("\n" + "=" * 80)
    print("CHECKING DATABASE CONTENTS")
    print("=" * 80)
    
    from src.data import db_manager
    from sqlalchemy import text
    
    async with db_manager.get_session() as session:
        # Count total entities
        result = await session.execute(
            text("SELECT COUNT(*) FROM itglue_entities WHERE organization_id = :org_id"),
            {"org_id": str(faucets_org.id)}
        )
        total = result.scalar()
        print(f"\nTotal Faucets entities synced: {total}")
        
        # Count by type
        result = await session.execute(
            text("""
                SELECT entity_type, COUNT(*) 
                FROM itglue_entities 
                WHERE organization_id = :org_id
                GROUP BY entity_type
                ORDER BY COUNT(*) DESC
            """),
            {"org_id": str(faucets_org.id)}
        )
        
        print("\nEntities by type:")
        for row in result:
            print(f"  • {row[0]}: {row[1]}")
    
    # Cleanup
    if server.itglue_client:
        await server.itglue_client.disconnect()
    
    print("\n" + "=" * 80)
    print("✅ Database is now populated! Search tool tests can be run.")
    print("=" * 80)


if __name__ == "__main__":
    print("Starting Faucets data sync...")
    asyncio.run(sync_faucets_data())