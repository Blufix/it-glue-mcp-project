#!/usr/bin/env python3
"""Test syncing IT Glue data to Neo4j."""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from neo4j import AsyncGraphDatabase
from src.config.settings import settings
import aiohttp
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def sync_it_glue_to_neo4j():
    """Sync IT Glue data to Neo4j database."""
    
    print("=" * 60)
    print("SYNCING IT GLUE DATA TO NEO4J")
    print("=" * 60)
    
    # IT Glue API configuration
    api_key = os.getenv('ITGLUE_API_KEY')
    api_url = os.getenv('ITGLUE_API_URL', 'https://api.eu.itglue.com')
    
    if not api_key:
        print("❌ IT Glue API key not found in environment")
        return
    
    headers = {
        'x-api-key': api_key,
        'Content-Type': 'application/vnd.api+json'
    }
    
    # Connect to Neo4j
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )
    
    async with aiohttp.ClientSession() as http_session:
        # 1. Fetch organizations
        print("\n1. Fetching Organizations from IT Glue...")
        async with http_session.get(
            f"{api_url}/organizations",
            headers=headers,
            params={'page[size]': 20}
        ) as response:
            if response.status == 200:
                data = await response.json()
                organizations = data.get('data', [])
                print(f"   • Found {len(organizations)} organizations")
                
                # Store Faucets Limited ID for later use
                faucets_org_id = None
                for org in organizations:
                    if 'Faucets' in org['attributes'].get('name', ''):
                        faucets_org_id = org['id']
                        print(f"   • Found Faucets Limited: ID {faucets_org_id}")
                        break
            else:
                print(f"   ❌ Failed to fetch organizations: {response.status}")
                return
        
        # 2. Sync organizations to Neo4j
        print("\n2. Syncing Organizations to Neo4j...")
        async with driver.session() as session:
            for org in organizations[:5]:  # Limit to first 5 for testing
                cypher = """
                    MERGE (o:Organization {itglue_id: $id})
                    SET o.name = $name,
                        o.created_at = $created_at,
                        o.updated_at = $updated_at,
                        o.description = $description,
                        o.synced_at = datetime()
                    RETURN o
                """
                await session.run(cypher,
                    id=org['id'],
                    name=org['attributes'].get('name'),
                    created_at=org['attributes'].get('created-at'),
                    updated_at=org['attributes'].get('updated-at'),
                    description=org['attributes'].get('description', '')
                )
            print(f"   ✅ Synced {min(5, len(organizations))} organizations")
        
        # 3. Fetch configurations for Faucets
        if faucets_org_id:
            print(f"\n3. Fetching Configurations for Faucets Limited...")
            async with http_session.get(
                f"{api_url}/organizations/{faucets_org_id}/relationships/configurations",
                headers=headers,
                params={'page[size]': 50}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    configurations = data.get('data', [])
                    print(f"   • Found {len(configurations)} configurations")
                    
                    # 4. Sync configurations to Neo4j
                    print("\n4. Syncing Configurations to Neo4j...")
                    async with driver.session() as session:
                        for config in configurations:
                            attrs = config['attributes']
                            cypher = """
                                MERGE (c:Configuration {itglue_id: $id})
                                SET c.name = $name,
                                    c.configuration_type = $config_type,
                                    c.hostname = $hostname,
                                    c.ip_address = $ip,
                                    c.serial_number = $serial,
                                    c.manufacturer = $manufacturer,
                                    c.model = $model,
                                    c.configuration_status = $status,
                                    c.operating_system = $os,
                                    c.created_at = $created_at,
                                    c.updated_at = $updated_at,
                                    c.synced_at = datetime()
                                WITH c
                                MATCH (o:Organization {itglue_id: $org_id})
                                MERGE (c)-[:BELONGS_TO]->(o)
                                RETURN c
                            """
                            await session.run(cypher,
                                id=config['id'],
                                name=attrs.get('name'),
                                config_type=attrs.get('configuration-type-name'),
                                hostname=attrs.get('hostname'),
                                ip=attrs.get('primary-ip'),
                                serial=attrs.get('serial-number'),
                                manufacturer=attrs.get('manufacturer-name'),
                                model=attrs.get('model-name'),
                                status=attrs.get('configuration-status-name'),
                                os=attrs.get('operating-system-name'),
                                created_at=attrs.get('created-at'),
                                updated_at=attrs.get('updated-at'),
                                org_id=faucets_org_id
                            )
                        print(f"   ✅ Synced {len(configurations)} configurations")
                        
                        # Create some relationships between configurations
                        print("\n5. Creating Configuration Relationships...")
                        
                        # Find firewall and servers
                        cypher = """
                            MATCH (fw:Configuration)-[:BELONGS_TO]->(o:Organization {itglue_id: $org_id})
                            WHERE fw.configuration_type = 'Firewall'
                            WITH fw, o
                            MATCH (srv:Configuration)-[:BELONGS_TO]->(o)
                            WHERE srv.configuration_type = 'Server'
                            MERGE (srv)-[:DEPENDS_ON]->(fw)
                            RETURN COUNT(*) as relationships
                        """
                        result = await session.run(cypher, org_id=faucets_org_id)
                        rel_count = await result.single()
                        if rel_count:
                            print(f"   ✅ Created {rel_count['relationships']} server->firewall dependencies")
                        
                        # Connect workstations to switches
                        cypher = """
                            MATCH (sw:Configuration)-[:BELONGS_TO]->(o:Organization {itglue_id: $org_id})
                            WHERE sw.configuration_type = 'Switch'
                            WITH sw, o
                            MATCH (ws:Configuration)-[:BELONGS_TO]->(o)
                            WHERE ws.configuration_type IN ['Workstation', 'Printer']
                            MERGE (ws)-[:CONNECTS_TO]->(sw)
                            RETURN COUNT(*) as relationships
                        """
                        result = await session.run(cypher, org_id=faucets_org_id)
                        rel_count = await result.single()
                        if rel_count:
                            print(f"   ✅ Created {rel_count['relationships']} device->switch connections")
            
            # 5. Fetch contacts for Faucets
            print(f"\n6. Fetching Contacts for Faucets Limited...")
            async with http_session.get(
                f"{api_url}/organizations/{faucets_org_id}/relationships/contacts",
                headers=headers,
                params={'page[size]': 50}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    contacts = data.get('data', [])
                    print(f"   • Found {len(contacts)} contacts")
                    
                    # Sync contacts to Neo4j
                    async with driver.session() as session:
                        for contact in contacts:
                            attrs = contact['attributes']
                            cypher = """
                                MERGE (ct:Contact {itglue_id: $id})
                                SET ct.first_name = $first_name,
                                    ct.last_name = $last_name,
                                    ct.title = $title,
                                    ct.email = $email,
                                    ct.phone = $phone,
                                    ct.synced_at = datetime()
                                WITH ct
                                MATCH (o:Organization {itglue_id: $org_id})
                                MERGE (ct)-[:BELONGS_TO]->(o)
                                RETURN ct
                            """
                            emails = attrs.get('contact-emails', [])
                            phones = attrs.get('contact-phones', [])
                            
                            await session.run(cypher,
                                id=contact['id'],
                                first_name=attrs.get('first-name'),
                                last_name=attrs.get('last-name'),
                                title=attrs.get('title'),
                                email=emails[0]['value'] if emails else None,
                                phone=phones[0]['value'] if phones else None,
                                org_id=faucets_org_id
                            )
                        print(f"   ✅ Synced {len(contacts)} contacts")
    
    # 7. Display Neo4j statistics
    print("\n7. Neo4j Database Statistics...")
    async with driver.session() as session:
        # Count nodes by type
        node_types = ["Organization", "Configuration", "Contact", "Password", "Document"]
        for node_type in node_types:
            result = await session.run(f"MATCH (n:{node_type}) RETURN COUNT(n) as count")
            record = await result.single()
            if record:
                print(f"   • {node_type}: {record['count']} nodes")
        
        # Count relationships
        result = await session.run("MATCH ()-[r]->() RETURN TYPE(r) as type, COUNT(r) as count")
        relationships = await result.data()
        print("\n   Relationships:")
        for rel in relationships:
            print(f"   • {rel['type']}: {rel['count']}")
    
    await driver.close()
    
    print("\n" + "=" * 60)
    print("IT GLUE TO NEO4J SYNC COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(sync_it_glue_to_neo4j())