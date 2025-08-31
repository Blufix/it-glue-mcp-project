#!/usr/bin/env python3
"""Test Neo4j integration with IT Glue data."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from neo4j import AsyncGraphDatabase
from src.config.settings import settings
import json


async def test_neo4j_connection():
    """Test basic Neo4j connection and queries."""
    
    print("=" * 60)
    print("TESTING NEO4J INTEGRATION")
    print("=" * 60)
    
    # Connect to Neo4j
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )
    
    async with driver.session() as session:
        # Test 1: Check database connectivity
        print("\n1. Testing Database Connection...")
        try:
            result = await session.run("RETURN 'Connected!' as message")
            record = await result.single()
            print(f"   ✅ {record['message']}")
        except Exception as e:
            print(f"   ❌ Connection failed: {e}")
            return
        
        # Test 2: Check indexes and constraints
        print("\n2. Checking Indexes and Constraints...")
        result = await session.run("SHOW CONSTRAINTS")
        constraints = await result.data()
        print(f"   • Found {len(constraints)} constraints")
        
        result = await session.run("SHOW INDEXES")
        indexes = await result.data()
        print(f"   • Found {len(indexes)} indexes")
        
        # Test 3: Check node counts
        print("\n3. Checking Node Counts...")
        node_types = [
            "Organization", "Configuration", "Password", 
            "Document", "Contact", "Location", "QueryTemplate"
        ]
        
        for node_type in node_types:
            result = await session.run(f"MATCH (n:{node_type}) RETURN COUNT(n) as count")
            record = await result.single()
            count = record['count'] if record else 0
            print(f"   • {node_type}: {count} nodes")
        
        # Test 4: Test query templates
        print("\n4. Testing Query Templates...")
        result = await session.run("MATCH (t:QueryTemplate) RETURN t.name as name, t.description as description")
        templates = await result.data()
        for template in templates:
            print(f"   • {template['name']}: {template['description']}")
        
        # Test 5: Create sample data for testing
        print("\n5. Creating Sample Test Data...")
        
        # Create a test organization
        cypher = """
            MERGE (o:Organization {itglue_id: 'test-org-001', name: 'Test Organization'})
            SET o.created_at = datetime(),
                o.description = 'Test organization for Neo4j integration'
            RETURN o
        """
        result = await session.run(cypher)
        org = await result.single()
        if org:
            print("   ✅ Created test organization")
        
        # Create test configurations
        configs = [
            {"id": "test-fw-001", "name": "Test Firewall", "type": "Firewall", "ip": "192.168.1.1"},
            {"id": "test-srv-001", "name": "Test Server", "type": "Server", "ip": "192.168.1.10"},
            {"id": "test-sw-001", "name": "Test Switch", "type": "Switch", "ip": "192.168.1.254"}
        ]
        
        for config in configs:
            cypher = """
                MERGE (c:Configuration {
                    itglue_id: $id,
                    name: $name,
                    configuration_type: $type,
                    ip_address: $ip
                })
                WITH c
                MATCH (o:Organization {itglue_id: 'test-org-001'})
                MERGE (c)-[:BELONGS_TO]->(o)
                RETURN c
            """
            await session.run(cypher, **config)
        print("   ✅ Created test configurations")
        
        # Create relationships
        cypher = """
            MATCH (fw:Configuration {itglue_id: 'test-fw-001'})
            MATCH (srv:Configuration {itglue_id: 'test-srv-001'})
            MATCH (sw:Configuration {itglue_id: 'test-sw-001'})
            MERGE (srv)-[:DEPENDS_ON]->(fw)
            MERGE (srv)-[:CONNECTS_TO]->(sw)
            RETURN COUNT(*) as relationships
        """
        result = await session.run(cypher)
        rel = await result.single()
        print(f"   ✅ Created {rel['relationships'] if rel else 0} test relationships")
        
        # Test 6: Query relationships
        print("\n6. Testing Relationship Queries...")
        
        # Find dependencies
        cypher = """
            MATCH (c:Configuration {name: 'Test Server'})-[:DEPENDS_ON]->(dep)
            RETURN c.name as source, dep.name as dependency
        """
        result = await session.run(cypher)
        deps = await result.data()
        for dep in deps:
            print(f"   • {dep['source']} depends on {dep['dependency']}")
        
        # Find all connected systems
        cypher = """
            MATCH (c:Configuration {name: 'Test Server'})-[r]-(connected)
            RETURN c.name as source, TYPE(r) as relationship, connected.name as target
        """
        result = await session.run(cypher)
        connections = await result.data()
        for conn in connections:
            print(f"   • {conn['source']} {conn['relationship']} {conn['target']}")
        
        # Test 7: Impact analysis
        print("\n7. Testing Impact Analysis...")
        cypher = """
            MATCH path = (start:Configuration {name: 'Test Firewall'})<-[:DEPENDS_ON*1..3]-(affected)
            RETURN 
                start.name as critical_component,
                affected.name as affected_system,
                length(path) as impact_distance
            ORDER BY impact_distance
        """
        result = await session.run(cypher)
        impacts = await result.data()
        for impact in impacts:
            print(f"   • If {impact['critical_component']} fails → {impact['affected_system']} affected (distance: {impact['impact_distance']})")
        
        # Test 8: Full organization overview
        print("\n8. Testing Organization Overview...")
        cypher = """
            MATCH (o:Organization {itglue_id: 'test-org-001'})
            OPTIONAL MATCH (o)<-[:BELONGS_TO]-(c:Configuration)
            WITH o, COUNT(DISTINCT c) as config_count, COLLECT(DISTINCT c.configuration_type) as types
            RETURN 
                o.name as org_name,
                config_count,
                types
        """
        result = await session.run(cypher)
        overview = await result.single()
        if overview:
            print(f"   • Organization: {overview['org_name']}")
            print(f"   • Configurations: {overview['config_count']}")
            print(f"   • Types: {', '.join(overview['types'] if overview['types'] else [])}")
        
        print("\n" + "=" * 60)
        print("NEO4J INTEGRATION TEST COMPLETE")
        print("=" * 60)
        
    await driver.close()


async def cleanup_test_data():
    """Clean up test data from Neo4j."""
    print("\nCleaning up test data...")
    
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )
    
    async with driver.session() as session:
        # Delete test nodes and relationships
        cypher = """
            MATCH (n)
            WHERE n.itglue_id STARTS WITH 'test-'
            DETACH DELETE n
            RETURN COUNT(n) as deleted
        """
        result = await session.run(cypher)
        record = await result.single()
        if record:
            print(f"   • Deleted {record['deleted']} test nodes")
    
    await driver.close()


if __name__ == "__main__":
    asyncio.run(test_neo4j_connection())
    # Optionally cleanup
    # asyncio.run(cleanup_test_data())