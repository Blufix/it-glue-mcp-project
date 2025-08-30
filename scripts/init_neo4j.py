#!/usr/bin/env python3
"""Initialize Neo4j graph database schema and constraints."""

import asyncio
import sys
from pathlib import Path
from neo4j import AsyncGraphDatabase

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import settings


async def init_neo4j():
    """Initialize Neo4j schema with constraints and indexes."""
    
    print("Initializing Neo4j graph database...")
    print("-" * 50)
    
    # Connect to Neo4j
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )
    
    async with driver.session() as session:
        # Create constraints and indexes
        constraints_and_indexes = [
            # Node constraints
            ("CREATE CONSTRAINT IF NOT EXISTS FOR (o:Organization) REQUIRE o.itglue_id IS UNIQUE", "Organization uniqueness"),
            ("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Configuration) REQUIRE c.itglue_id IS UNIQUE", "Configuration uniqueness"),
            ("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Password) REQUIRE p.itglue_id IS UNIQUE", "Password uniqueness"),
            ("CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.itglue_id IS UNIQUE", "Document uniqueness"),
            ("CREATE CONSTRAINT IF NOT EXISTS FOR (ct:Contact) REQUIRE ct.itglue_id IS UNIQUE", "Contact uniqueness"),
            ("CREATE CONSTRAINT IF NOT EXISTS FOR (l:Location) REQUIRE l.itglue_id IS UNIQUE", "Location uniqueness"),
            ("CREATE CONSTRAINT IF NOT EXISTS FOR (dm:Domain) REQUIRE dm.itglue_id IS UNIQUE", "Domain uniqueness"),
            ("CREATE CONSTRAINT IF NOT EXISTS FOR (n:Network) REQUIRE n.itglue_id IS UNIQUE", "Network uniqueness"),
            ("CREATE CONSTRAINT IF NOT EXISTS FOR (s:SSLCertificate) REQUIRE s.itglue_id IS UNIQUE", "SSL Certificate uniqueness"),
            ("CREATE CONSTRAINT IF NOT EXISTS FOR (f:FlexibleAsset) REQUIRE f.itglue_id IS UNIQUE", "Flexible Asset uniqueness"),
            
            # Indexes for common queries
            ("CREATE INDEX IF NOT EXISTS FOR (o:Organization) ON (o.name)", "Organization name index"),
            ("CREATE INDEX IF NOT EXISTS FOR (c:Configuration) ON (c.name)", "Configuration name index"),
            ("CREATE INDEX IF NOT EXISTS FOR (c:Configuration) ON (c.configuration_type)", "Configuration type index"),
            ("CREATE INDEX IF NOT EXISTS FOR (d:Document) ON (d.name)", "Document name index"),
            ("CREATE INDEX IF NOT EXISTS FOR (ct:Contact) ON (ct.email)", "Contact email index"),
            ("CREATE INDEX IF NOT EXISTS FOR (l:Location) ON (l.name)", "Location name index"),
            ("CREATE INDEX IF NOT EXISTS FOR (p:Password) ON (p.name)", "Password name index"),
            
            # Full-text search indexes
            ("CREATE FULLTEXT INDEX organization_search IF NOT EXISTS FOR (o:Organization) ON EACH [o.name, o.description]", "Organization full-text"),
            ("CREATE FULLTEXT INDEX configuration_search IF NOT EXISTS FOR (c:Configuration) ON EACH [c.name, c.hostname, c.notes]", "Configuration full-text"),
            ("CREATE FULLTEXT INDEX document_search IF NOT EXISTS FOR (d:Document) ON EACH [d.name, d.content]", "Document full-text"),
        ]
        
        for query, description in constraints_and_indexes:
            try:
                await session.run(query)
                print(f"✅ Created: {description}")
            except Exception as e:
                if "already exists" in str(e).lower() or "equivalent" in str(e).lower():
                    print(f"✓ Exists: {description}")
                else:
                    print(f"❌ Failed: {description} - {e}")
        
        # Create relationship types with properties
        print("\nCreating relationship patterns...")
        relationship_patterns = [
            # Organization relationships
            ("MATCH (o:Organization) WHERE o.itglue_id IS NOT NULL RETURN COUNT(o) as count", "Organization nodes"),
            
            # Define common relationship types (these are created when data is added)
            ("RETURN 'BELONGS_TO' as rel", "Organization ownership"),
            ("RETURN 'LOCATED_AT' as rel", "Location relationships"),
            ("RETURN 'MANAGES' as rel", "Management relationships"),
            ("RETURN 'USES' as rel", "Usage relationships"),
            ("RETURN 'DOCUMENTS' as rel", "Documentation relationships"),
            ("RETURN 'RELATES_TO' as rel", "General relationships"),
            ("RETURN 'DEPENDS_ON' as rel", "Dependency relationships"),
            ("RETURN 'AUTHENTICATES' as rel", "Authentication relationships"),
            ("RETURN 'CONNECTS_TO' as rel", "Network connections"),
        ]
        
        for query, description in relationship_patterns:
            result = await session.run(query)
            data = await result.single()
            if data and 'count' in data:
                print(f"  • {description}: {data['count']} existing")
            else:
                print(f"  • {description}: Ready")
        
        # Create example data structure query templates
        print("\nCreating query templates...")
        
        # Store common Cypher query templates as node properties
        templates = [
            {
                "name": "find_related_configs",
                "description": "Find all configurations related to an organization",
                "query": "MATCH (o:Organization {itglue_id: $org_id})-[:BELONGS_TO]-(c:Configuration) RETURN c"
            },
            {
                "name": "find_dependencies",
                "description": "Find configuration dependencies",
                "query": "MATCH (c:Configuration {itglue_id: $config_id})-[:DEPENDS_ON]->(dep) RETURN dep"
            },
            {
                "name": "find_documentation",
                "description": "Find all documentation for an entity",
                "query": "MATCH (e {itglue_id: $entity_id})-[:DOCUMENTS]-(d:Document) RETURN d"
            },
            {
                "name": "find_passwords",
                "description": "Find passwords related to a configuration",
                "query": "MATCH (c:Configuration {itglue_id: $config_id})-[:AUTHENTICATES]-(p:Password) RETURN p.name, p.username, p.id"
            },
            {
                "name": "organization_overview",
                "description": "Get complete overview of an organization",
                "query": """
                    MATCH (o:Organization {itglue_id: $org_id})
                    OPTIONAL MATCH (o)-[:BELONGS_TO]-(c:Configuration)
                    OPTIONAL MATCH (o)-[:BELONGS_TO]-(d:Document)
                    OPTIONAL MATCH (o)-[:BELONGS_TO]-(ct:Contact)
                    RETURN o,
                           COUNT(DISTINCT c) as configs,
                           COUNT(DISTINCT d) as documents,
                           COUNT(DISTINCT ct) as contacts
                """
            }
        ]
        
        for template in templates:
            cypher = """
                MERGE (t:QueryTemplate {name: $name})
                SET t.description = $description,
                    t.query = $query_text,
                    t.updated_at = datetime()
            """
            await session.run(cypher, 
                             name=template['name'],
                             description=template['description'],
                             query_text=template['query'])
            print(f"✅ Template: {template['name']}")
        
        # Get database statistics
        print("\n" + "=" * 50)
        print("Neo4j Database Statistics:")
        
        stats_queries = [
            ("MATCH (n) RETURN COUNT(n) as count, LABELS(n)[0] as label", "Node counts by label"),
            ("MATCH ()-[r]->() RETURN COUNT(r) as count, TYPE(r) as type", "Relationship counts by type"),
            ("CALL db.indexes() YIELD name, state RETURN name, state", "Index status")
        ]
        
        for query, description in stats_queries:
            try:
                result = await session.run(query)
                records = await result.data()
                if records:
                    print(f"\n{description}:")
                    for record in records[:10]:  # Limit output
                        if 'label' in record:
                            print(f"  • {record.get('label', 'Unknown')}: {record.get('count', 0)}")
                        elif 'type' in record:
                            print(f"  • {record.get('type', 'Unknown')}: {record.get('count', 0)}")
                        elif 'name' in record:
                            print(f"  • {record.get('name', 'Unknown')}: {record.get('state', 'Unknown')}")
            except Exception as e:
                if "no variables" not in str(e).lower():
                    print(f"  {description}: No data yet")
    
    await driver.close()
    
    print("-" * 50)
    print("Neo4j initialization complete!")


if __name__ == "__main__":
    asyncio.run(init_neo4j())