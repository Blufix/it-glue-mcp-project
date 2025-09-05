#!/usr/bin/env python3
"""
Populate Neo4j graph database with Faucets data from PostgreSQL.
Creates nodes and relationships for graph-based queries and impact analysis.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import logging

sys.path.insert(0, str(Path(__file__).parent))

from neo4j import AsyncGraphDatabase
from src.config.settings import settings
from src.data import db_manager
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def clear_neo4j_data(session):
    """Clear existing data from Neo4j."""
    logger.info("Clearing existing Neo4j data...")
    
    # Delete all relationships first, then nodes
    await session.run("MATCH ()-[r]->() DELETE r")
    await session.run("MATCH (n) DELETE n")
    
    logger.info("✅ Neo4j data cleared")


async def create_constraints(session):
    """Create uniqueness constraints and indexes."""
    logger.info("Creating constraints and indexes...")
    
    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (o:Organization) REQUIRE o.itglue_id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Configuration) REQUIRE c.itglue_id IS UNIQUE",
        "CREATE INDEX IF NOT EXISTS FOR (o:Organization) ON (o.name)",
        "CREATE INDEX IF NOT EXISTS FOR (c:Configuration) ON (c.name)",
        "CREATE INDEX IF NOT EXISTS FOR (c:Configuration) ON (c.configuration_type)"
    ]
    
    for constraint in constraints:
        try:
            await session.run(constraint)
        except Exception as e:
            logger.warning(f"Constraint/index might already exist: {e}")
    
    logger.info("✅ Constraints and indexes created")


async def fetch_entities_from_postgres():
    """Fetch all entities from PostgreSQL."""
    logger.info("Fetching entities from PostgreSQL...")
    
    await db_manager.initialize()
    
    entities = {
        'organizations': [],
        'configurations': []
    }
    
    async with db_manager.get_session() as session:
        # Fetch organizations
        result = await session.execute(text("""
            SELECT id, itglue_id, name, attributes
            FROM itglue_entities
            WHERE entity_type = 'organization'
        """))
        
        for row in result:
            entities['organizations'].append({
                'id': str(row.id),
                'itglue_id': row.itglue_id,
                'name': row.name,
                'attributes': row.attributes or {}
            })
        
        # Fetch configurations
        result = await session.execute(text("""
            SELECT id, itglue_id, name, attributes, organization_id
            FROM itglue_entities
            WHERE entity_type = 'configuration'
            ORDER BY name
        """))
        
        for row in result:
            entities['configurations'].append({
                'id': str(row.id),
                'itglue_id': row.itglue_id,
                'name': row.name,
                'organization_id': row.organization_id,
                'attributes': row.attributes or {}
            })
    
    logger.info(f"✅ Fetched {len(entities['organizations'])} organizations, {len(entities['configurations'])} configurations")
    return entities


async def create_organization_nodes(session, organizations):
    """Create organization nodes in Neo4j."""
    logger.info(f"Creating {len(organizations)} organization nodes...")
    
    for org in organizations:
        query = """
            MERGE (o:Organization {itglue_id: $itglue_id})
            SET o.name = $name,
                o.postgres_id = $postgres_id,
                o.created_at = datetime(),
                o.updated_at = datetime()
            RETURN o
        """
        
        await session.run(
            query,
            itglue_id=org['itglue_id'],
            name=org['name'],
            postgres_id=org['id']
        )
    
    logger.info("✅ Organization nodes created")


async def create_configuration_nodes(session, configurations):
    """Create configuration nodes and relationships in Neo4j."""
    logger.info(f"Creating {len(configurations)} configuration nodes...")
    
    # Group configurations by type for better relationship inference
    servers = []
    switches = []
    firewalls = []
    workstations = []
    other = []
    
    for config in configurations:
        name_lower = config['name'].lower()
        attrs = config['attributes']
        
        # Categorize configurations
        if 'server' in name_lower or 'hyperv' in name_lower or 'sql' in name_lower:
            servers.append(config)
        elif 'switch' in name_lower or 'aruba' in name_lower:
            switches.append(config)
        elif 'firewall' in name_lower or 'sophos' in name_lower or 'xgs' in name_lower:
            firewalls.append(config)
        elif 'desktop' in name_lower or 'laptop' in name_lower or 'surface' in name_lower:
            workstations.append(config)
        else:
            other.append(config)
    
    # Create all configuration nodes
    for config in configurations:
        attrs = config['attributes']
        config_type = attrs.get('configuration_type', '')
        
        # Determine node type based on name and attributes
        if 'server' in config['name'].lower():
            node_type = 'Server'
        elif 'switch' in config['name'].lower():
            node_type = 'Switch'
        elif 'firewall' in config['name'].lower() or 'sophos' in config['name'].lower():
            node_type = 'Firewall'
        elif 'desktop' in config['name'].lower() or 'laptop' in config['name'].lower():
            node_type = 'Workstation'
        elif 'printer' in config['name'].lower():
            node_type = 'Printer'
        elif 'nas' in config['name'].lower() or 'qnap' in config['name'].lower():
            node_type = 'Storage'
        else:
            node_type = 'Device'
        
        query = f"""
            MERGE (c:Configuration:{node_type} {{itglue_id: $itglue_id}})
            SET c.name = $name,
                c.postgres_id = $postgres_id,
                c.hostname = $hostname,
                c.primary_ip = $primary_ip,
                c.configuration_type = $config_type,
                c.serial_number = $serial_number,
                c.archived = $archived,
                c.created_at = datetime(),
                c.updated_at = datetime()
            RETURN c
        """
        
        await session.run(
            query,
            itglue_id=config['itglue_id'],
            name=config['name'],
            postgres_id=config['id'],
            hostname=attrs.get('hostname'),
            primary_ip=attrs.get('primary_ip'),
            config_type=config_type,
            serial_number=attrs.get('serial_number'),
            archived=attrs.get('archived', False)
        )
    
    logger.info("✅ Configuration nodes created")
    
    # Create BELONGS_TO relationships with organizations
    logger.info("Creating BELONGS_TO relationships...")
    
    for config in configurations:
        if config['organization_id']:
            query = """
                MATCH (c:Configuration {itglue_id: $config_id})
                MATCH (o:Organization {itglue_id: $org_id})
                MERGE (c)-[:BELONGS_TO]->(o)
            """
            
            await session.run(
                query,
                config_id=config['itglue_id'],
                org_id=config['organization_id']
            )
    
    logger.info("✅ BELONGS_TO relationships created")
    
    # Infer and create infrastructure relationships
    logger.info("Inferring infrastructure relationships...")
    
    # Connect servers to switches
    for server in servers:
        # Find the most likely switch (simple heuristic)
        if switches:
            query = """
                MATCH (s:Server {itglue_id: $server_id})
                MATCH (sw:Switch {itglue_id: $switch_id})
                MERGE (s)-[:CONNECTS_TO]->(sw)
            """
            
            # Connect to first switch (in real scenario, would use more logic)
            await session.run(
                query,
                server_id=server['itglue_id'],
                switch_id=switches[0]['itglue_id']
            )
    
    # Connect switches to firewall
    for switch in switches:
        for firewall in firewalls:
            if 'sophos' in firewall['name'].lower():
                query = """
                    MATCH (sw:Switch {itglue_id: $switch_id})
                    MATCH (fw:Firewall {itglue_id: $firewall_id})
                    MERGE (sw)-[:ROUTES_THROUGH]->(fw)
                """
                
                await session.run(
                    query,
                    switch_id=switch['itglue_id'],
                    firewall_id=firewall['itglue_id']
                )
                break
    
    # Connect workstations to network
    for workstation in workstations[:10]:  # Limit for demo
        if switches:
            query = """
                MATCH (w:Workstation {itglue_id: $workstation_id})
                MATCH (sw:Switch {itglue_id: $switch_id})
                MERGE (w)-[:CONNECTS_TO]->(sw)
            """
            
            await session.run(
                query,
                workstation_id=workstation['itglue_id'],
                switch_id=switches[0]['itglue_id'] if switches else None
            )
    
    logger.info("✅ Infrastructure relationships created")
    
    return {
        'servers': len(servers),
        'switches': len(switches),
        'firewalls': len(firewalls),
        'workstations': len(workstations),
        'other': len(other)
    }


async def create_service_dependencies(session):
    """Create service dependency relationships."""
    logger.info("Creating service dependencies...")
    
    # Example: Create dependencies between specific servers
    dependencies = [
        # SQL server depends on domain controller
        """
        MATCH (sql:Server) WHERE sql.name CONTAINS 'SQL'
        MATCH (dc:Server) WHERE dc.name CONTAINS 'DCFP'
        MERGE (sql)-[:DEPENDS_ON {service: 'Authentication'}]->(dc)
        """,
        
        # Hypervisor hosts virtual machines
        """
        MATCH (hyperv:Server) WHERE hyperv.name CONTAINS 'HYPERV'
        MATCH (vm:Server) WHERE vm.name CONTAINS 'SQL' OR vm.name CONTAINS 'DCFP'
        MERGE (vm)-[:HOSTED_ON]->(hyperv)
        """
    ]
    
    for query in dependencies:
        try:
            await session.run(query)
        except Exception as e:
            logger.debug(f"Dependency might not apply: {e}")
    
    logger.info("✅ Service dependencies created")


async def verify_graph(session):
    """Verify the graph was created successfully."""
    logger.info("\nVerifying graph creation...")
    
    # Count nodes
    result = await session.run("MATCH (n) RETURN COUNT(n) as count")
    record = await result.single()
    total_nodes = record['count']
    
    # Count relationships
    result = await session.run("MATCH ()-[r]->() RETURN COUNT(r) as count")
    record = await result.single()
    total_rels = record['count']
    
    # Get node distribution
    result = await session.run("""
        MATCH (n)
        RETURN LABELS(n) as labels, COUNT(n) as count
        ORDER BY count DESC
    """)
    
    print("\n📊 Graph Statistics:")
    print(f"  Total nodes: {total_nodes}")
    print(f"  Total relationships: {total_rels}")
    print("\n  Node types:")
    
    async for record in result:
        labels = ':'.join(record['labels'])
        print(f"    {labels}: {record['count']}")
    
    # Get relationship distribution
    result = await session.run("""
        MATCH ()-[r]->()
        RETURN TYPE(r) as type, COUNT(r) as count
        ORDER BY count DESC
    """)
    
    print("\n  Relationship types:")
    async for record in result:
        print(f"    {record['type']}: {record['count']}")
    
    # Sample impact analysis query
    print("\n🔍 Sample Impact Analysis Query:")
    print("  'What would be affected if the main switch fails?'")
    
    result = await session.run("""
        MATCH (sw:Switch)
        MATCH (affected)-[:CONNECTS_TO|ROUTES_THROUGH*1..3]->(sw)
        RETURN sw.name as switch, 
               COLLECT(DISTINCT affected.name)[..5] as affected_devices
        LIMIT 1
    """)
    
    async for record in result:
        print(f"  Switch: {record['switch']}")
        print(f"  Would affect: {', '.join(record['affected_devices'])}")


async def main():
    """Main execution function."""
    print("=" * 80)
    print("NEO4J GRAPH POPULATION - FAUCETS DATA")
    print("=" * 80)
    
    # Connect to Neo4j
    neo4j_uri = "bolt://localhost:7688"
    driver = AsyncGraphDatabase.driver(
        neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )
    
    try:
        async with driver.session() as session:
            # Clear existing data
            await clear_neo4j_data(session)
            
            # Create constraints
            await create_constraints(session)
            
            # Fetch entities from PostgreSQL
            entities = await fetch_entities_from_postgres()
            
            # Create organization nodes
            await create_organization_nodes(session, entities['organizations'])
            
            # Create configuration nodes and relationships
            stats = await create_configuration_nodes(session, entities['configurations'])
            
            # Create service dependencies
            await create_service_dependencies(session)
            
            # Verify the graph
            await verify_graph(session)
            
            print("\n" + "=" * 80)
            print("✅ NEO4J GRAPH POPULATION COMPLETE")
            print("=" * 80)
            print(f"\nConfiguration breakdown:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
            print("\nYou can now:")
            print("  1. Browse the graph at http://localhost:7475")
            print("  2. Run impact analysis queries")
            print("  3. Trace dependencies")
            print("  4. Visualize infrastructure topology")
            print("=" * 80)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise
    finally:
        await driver.close()
        await db_manager.close()


async def update_neo4j_graph():
    """Update Neo4j graph with new entities."""
    logger.info("Updating Neo4j graph with new entities...")
    
    # Connect to Neo4j
    driver = AsyncGraphDatabase.driver(
        "bolt://localhost:7688",
        auth=(settings.neo4j_user, settings.neo4j_password)
    )
    
    try:
        # Fetch new entities from PostgreSQL
        entities = await fetch_entities_from_postgres()
        
        async with driver.session() as session:
            # Update organization nodes
            if entities['organizations']:
                await create_organization_nodes(session, entities['organizations'])
            
            # Update configuration nodes and relationships
            if entities['configurations']:
                await create_configuration_nodes(session, entities['configurations'])
            
            # Create service dependencies
            await create_service_dependencies(session)
        
        logger.info("✅ Neo4j graph updated successfully")
        
    finally:
        await driver.close()
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())