#!/usr/bin/env python3
"""
Check Neo4j database status and relationship with IT Glue data.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from neo4j import AsyncGraphDatabase
from src.config.settings import settings


async def check_neo4j():
    """Check Neo4j status and data."""
    
    print("=" * 80)
    print("NEO4J GRAPH DATABASE STATUS CHECK")
    print("=" * 80)
    
    # Connection details
    # Use the IT Glue Neo4j instance on port 7688 (bolt) / 7475 (http)
    neo4j_uri = "bolt://localhost:7688"  # This is correct for the itglue-neo4j container
    neo4j_user = settings.neo4j_user
    neo4j_password = settings.neo4j_password
    
    print(f"URI: {neo4j_uri}")
    print(f"User: {neo4j_user}")
    print(f"HTTP Browser: http://localhost:7475")
    print("-" * 80)
    
    try:
        # Connect to Neo4j
        driver = AsyncGraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )
        
        print("✅ Connected to Neo4j")
        
        async with driver.session() as session:
            # Check database info
            result = await session.run("CALL dbms.components() YIELD name, versions, edition")
            info = await result.single()
            print(f"\nDatabase Info:")
            print(f"  Edition: {info['edition']}")
            print(f"  Version: {info['versions'][0] if info['versions'] else 'Unknown'}")
            
            # Count nodes by label
            print("\n📊 Node Counts by Label:")
            
            labels = [
                "Organization",
                "Configuration", 
                "Password",
                "Document",
                "Contact",
                "Location",
                "FlexibleAsset",
                "User",
                "Service"
            ]
            
            total_nodes = 0
            for label in labels:
                result = await session.run(f"MATCH (n:{label}) RETURN COUNT(n) as count")
                record = await result.single()
                count = record["count"] if record else 0
                if count > 0:
                    print(f"  {label}: {count}")
                    total_nodes += count
            
            if total_nodes == 0:
                print("  ⚠️ No nodes found in database")
            else:
                print(f"  Total nodes: {total_nodes}")
            
            # Count relationships
            print("\n📊 Relationship Counts:")
            result = await session.run("MATCH ()-[r]->() RETURN TYPE(r) as type, COUNT(r) as count")
            
            total_rels = 0
            async for record in result:
                print(f"  {record['type']}: {record['count']}")
                total_rels += record['count']
            
            if total_rels == 0:
                print("  ⚠️ No relationships found in database")
            else:
                print(f"  Total relationships: {total_rels}")
            
            # Check for Faucets organization
            print("\n🔍 Checking for Faucets Organization:")
            result = await session.run(
                "MATCH (o:Organization) WHERE o.name CONTAINS 'Faucet' RETURN o.name as name, o.id as id"
            )
            
            faucets_found = False
            async for record in result:
                print(f"  Found: {record['name']} (ID: {record['id']})")
                faucets_found = True
            
            if not faucets_found:
                print("  ❌ Faucets organization not found in graph")
            
            # Sample query - find connected components
            if total_nodes > 0:
                print("\n🔗 Sample Graph Query - Find Most Connected Nodes:")
                result = await session.run("""
                    MATCH (n)
                    WITH n, SIZE([(n)-[]-() |1]) as degree
                    RETURN LABELS(n)[0] as label, n.name as name, degree
                    ORDER BY degree DESC
                    LIMIT 5
                """)
                
                async for record in result:
                    print(f"  {record['label']}: {record['name']} (connections: {record['degree']})")
        
        await driver.close()
        
        print("\n" + "=" * 80)
        print("NEO4J ARCHITECTURE ROLE:")
        print("-" * 80)
        print("""
Neo4j serves as the RELATIONSHIP GRAPH DATABASE in this architecture:

1. **Purpose**: Store and query complex IT infrastructure relationships
   - Organization → has → Configurations
   - Configuration → depends_on → Configuration
   - Service → runs_on → Server
   - User → manages → Asset
   
2. **Key Features**:
   - Graph traversal for impact analysis
   - Dependency mapping
   - Service topology visualization
   - Root cause analysis
   
3. **Integration Points**:
   - GraphTransformer: Converts IT Glue data to graph nodes/relationships
   - GraphTraversal: Complex queries (impact analysis, dependencies)
   - QueryEngine: Uses for relationship-based queries
   
4. **Current Status**:
   - Neo4j is running and accessible
   - Database appears to be EMPTY (no IT Glue data synced)
   - Need to run graph transformation to populate
        """)
        
        if total_nodes == 0:
            print("\n⚠️ ACTION NEEDED: Run graph transformation to populate Neo4j with IT Glue data")
            print("   This will enable relationship queries and impact analysis")
        
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error connecting to Neo4j: {e}")
        print("\nTroubleshooting:")
        print("1. Check if Neo4j container is running: docker ps | grep neo4j")
        print("2. Verify credentials in .env file")
        print("3. Check Neo4j logs: docker logs itglue-neo4j")
        return False
    
    return True


if __name__ == "__main__":
    asyncio.run(check_neo4j())