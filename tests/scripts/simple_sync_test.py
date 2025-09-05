#!/usr/bin/env python3
"""
Simple test to populate the database with Faucets data for search testing.
This bypasses the sync orchestrator and directly inserts data.
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime
import uuid

sys.path.insert(0, str(Path(__file__).parent))

from src.services.itglue import ITGlueClient
from src.config.settings import settings
from src.data import db_manager
from src.data.models import ITGlueEntity
from sqlalchemy.orm import Session
from sqlalchemy import text


async def simple_sync():
    """Directly sync Faucets data to database."""
    
    print("=" * 80)
    print("SIMPLE SYNC - POPULATING DATABASE FOR SEARCH TESTING")
    print("=" * 80)
    
    # Connect to IT Glue
    client = ITGlueClient(
        api_key=settings.itglue_api_key,
        api_url=settings.itglue_api_url
    )
    
    # Find Faucets
    print("\n1. Finding Faucets Limited...")
    orgs = await client.get_organizations()
    
    faucets_org = None
    for org in orgs:
        if "faucets" in org.name.lower():
            faucets_org = org
            print(f"   ✅ Found: {org.name} (ID: {org.id})")
            break
    
    if not faucets_org:
        print("   ❌ Faucets not found")
        return
    
    # Get configurations for Faucets
    print("\n2. Fetching configurations...")
    configs = await client.get_configurations(org_id=faucets_org.id)
    print(f"   ✅ Found {len(configs)} configurations")
    
    # Initialize database
    await db_manager.initialize()
    
    # Insert data directly
    print("\n3. Inserting data into database...")
    
    async with db_manager.get_session() as session:
        inserted = 0
        
        # Insert organization
        try:
            org_entity = ITGlueEntity(
                id=uuid.uuid4(),
                itglue_id=str(faucets_org.id),
                entity_type="organization",
                organization_id=str(faucets_org.id),
                name=faucets_org.name,
                attributes={"name": faucets_org.name},
                relationships={},
                search_text=f"{faucets_org.name} organization",
                last_synced=datetime.utcnow()
            )
            session.add(org_entity)
            await session.commit()
            inserted += 1
            print(f"   ✅ Inserted organization: {faucets_org.name}")
        except Exception as e:
            print(f"   ⚠️ Organization insert failed: {e}")
            await session.rollback()
        
        # Insert configurations
        for config in configs:
            try:
                # Access attributes properly
                config_attrs = config.attributes if hasattr(config, 'attributes') else {}
                
                # Build search text
                search_parts = [
                    config.name,
                    config_attrs.get('configuration_type', ''),
                    config_attrs.get('hostname', ''),
                    config_attrs.get('primary_ip', '')
                ]
                search_text = " ".join(filter(None, search_parts))
                
                # Create entity
                config_entity = ITGlueEntity(
                    id=uuid.uuid4(),
                    itglue_id=str(config.id),
                    entity_type="configuration",
                    organization_id=str(faucets_org.id),
                    name=config.name,
                    attributes={
                        "name": config.name,
                        "configuration_type": config_attrs.get('configuration_type'),
                        "hostname": config_attrs.get('hostname'),
                        "primary_ip": config_attrs.get('primary_ip'),
                        "serial_number": config_attrs.get('serial_number'),
                        "archived": config_attrs.get('archived', False)
                    },
                    relationships={},
                    search_text=search_text.lower(),
                    last_synced=datetime.utcnow()
                )
                
                session.add(config_entity)
                inserted += 1
                
                # Commit every 10 records
                if inserted % 10 == 0:
                    await session.commit()
                    print(f"   ... inserted {inserted} records")
                    
            except Exception as e:
                print(f"   ⚠️ Failed to insert {config.name}: {e}")
                await session.rollback()
        
        # Final commit
        await session.commit()
        print(f"   ✅ Total inserted: {inserted} records")
    
    # Verify the data
    print("\n4. Verifying database contents...")
    
    async with db_manager.get_session() as session:
        # Total count
        result = await session.execute(
            text("SELECT COUNT(*) FROM itglue_entities")
        )
        total = result.scalar()
        print(f"   Total entities: {total}")
        
        # Count by type
        result = await session.execute(
            text("""
                SELECT entity_type, COUNT(*) 
                FROM itglue_entities 
                GROUP BY entity_type
            """)
        )
        print("   By type:")
        for row in result:
            print(f"      • {row[0]}: {row[1]}")
        
        # Faucets specific
        result = await session.execute(
            text("""
                SELECT COUNT(*) 
                FROM itglue_entities 
                WHERE organization_id = :org_id
            """),
            {"org_id": str(faucets_org.id)}
        )
        faucets_count = result.scalar()
        print(f"   Faucets entities: {faucets_count}")
        
        # Sample searches
        print("\n5. Testing search queries...")
        
        test_queries = ["server", "firewall", "switch", "network"]
        for query in test_queries:
            result = await session.execute(
                text("""
                    SELECT COUNT(*) 
                    FROM itglue_entities 
                    WHERE search_text ILIKE :query
                """),
                {"query": f"%{query}%"}
            )
            count = result.scalar()
            print(f"   '{query}': {count} matches")
    
    await client.disconnect()
    
    print("\n" + "=" * 80)
    print("✅ DATABASE POPULATED - Ready for search testing!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(simple_sync())