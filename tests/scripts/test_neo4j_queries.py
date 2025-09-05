#!/usr/bin/env python3
"""
Test Neo4j graph queries for IT infrastructure analysis.
Demonstrates impact analysis, dependency mapping, and topology queries.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from neo4j import AsyncGraphDatabase
from src.config.settings import settings


async def run_graph_queries():
    """Run various graph queries to demonstrate Neo4j capabilities."""
    
    print("=" * 80)
    print("NEO4J GRAPH QUERY DEMONSTRATIONS")
    print("=" * 80)
    
    # Connect to Neo4j
    driver = AsyncGraphDatabase.driver(
        "bolt://localhost:7688",
        auth=(settings.neo4j_user, settings.neo4j_password)
    )
    
    try:
        async with driver.session() as session:
            
            # Query 1: Impact Analysis - What breaks if a switch fails?
            print("\n🔴 IMPACT ANALYSIS: What would be affected if the main switch fails?")
            print("-" * 60)
            
            result = await session.run("""
                MATCH (sw:Switch) WHERE sw.name CONTAINS 'Aruba'
                OPTIONAL MATCH (affected)-[:CONNECTS_TO|ROUTES_THROUGH*1..3]->(sw)
                RETURN sw.name as switch_name,
                       COUNT(DISTINCT affected) as affected_count,
                       COLLECT(DISTINCT affected.name)[..10] as sample_affected
            """)
            
            async for record in result:
                print(f"Switch: {record['switch_name']}")
                print(f"Would affect {record['affected_count']} devices:")
                for device in record['sample_affected']:
                    print(f"  - {device}")
            
            # Query 2: Dependency Tree - What does a server depend on?
            print("\n🔗 DEPENDENCY ANALYSIS: What does the SQL server depend on?")
            print("-" * 60)
            
            result = await session.run("""
                MATCH path = (start:Server)-[:DEPENDS_ON|CONNECTS_TO|HOSTED_ON*1..3]->(dependency)
                WHERE start.name CONTAINS 'SQL'
                RETURN start.name as server,
                       [node in nodes(path) | node.name] as dependency_chain
                LIMIT 5
            """)
            
            record_found = False
            async for record in result:
                record_found = True
                print(f"Server: {record['server']}")
                print(f"Dependency chain: {' → '.join(record['dependency_chain'])}")
            
            if not record_found:
                print("No SQL server dependencies found (would need more data)")
            
            # Query 3: Network Topology - Show network hierarchy
            print("\n🌐 NETWORK TOPOLOGY: Infrastructure hierarchy")
            print("-" * 60)
            
            result = await session.run("""
                MATCH (fw:Firewall)
                OPTIONAL MATCH (sw:Switch)-[:ROUTES_THROUGH]->(fw)
                OPTIONAL MATCH (dev)-[:CONNECTS_TO]->(sw)
                RETURN fw.name as firewall,
                       COLLECT(DISTINCT sw.name) as switches,
                       COUNT(DISTINCT dev) as connected_devices
            """)
            
            async for record in result:
                print(f"Firewall: {record['firewall']}")
                print(f"Connected Switches: {', '.join(record['switches']) if record['switches'][0] else 'None'}")
                print(f"Total Connected Devices: {record['connected_devices']}")
            
            # Query 4: Find Single Points of Failure
            print("\n⚠️ SINGLE POINTS OF FAILURE: Critical infrastructure components")
            print("-" * 60)
            
            result = await session.run("""
                MATCH (critical)
                WHERE SIZE([(critical)<-[:CONNECTS_TO|DEPENDS_ON|ROUTES_THROUGH]-() | 1]) > 5
                RETURN LABELS(critical) as type,
                       critical.name as name,
                       SIZE([(critical)<-[:CONNECTS_TO|DEPENDS_ON|ROUTES_THROUGH]-() | 1]) as dependent_count
                ORDER BY dependent_count DESC
                LIMIT 5
            """)
            
            async for record in result:
                print(f"{record['type'][0]}: {record['name']}")
                print(f"  {record['dependent_count']} components depend on this")
            
            # Query 5: Path Finding - Network path between two devices
            print("\n🛤️ PATH FINDING: Network path from workstation to firewall")
            print("-" * 60)
            
            result = await session.run("""
                MATCH (w:Workstation), (f:Firewall)
                MATCH path = shortestPath((w)-[*..5]-(f))
                RETURN [node in nodes(path) | node.name] as path_nodes,
                       length(path) as hops
                LIMIT 1
            """)
            
            async for record in result:
                print(f"Path: {' → '.join(record['path_nodes'])}")
                print(f"Number of hops: {record['hops']}")
            
            # Query 6: Component Statistics
            print("\n📊 INFRASTRUCTURE STATISTICS")
            print("-" * 60)
            
            result = await session.run("""
                MATCH (n)
                WITH LABELS(n) as labels, n
                RETURN labels[0] as component_type,
                       COUNT(n) as count,
                       COLLECT(n.name)[..3] as examples
                ORDER BY count DESC
            """)
            
            print(f"{'Component Type':<20} {'Count':<10} {'Examples'}")
            print("-" * 60)
            
            async for record in result:
                examples = ', '.join(record['examples'][:3])
                print(f"{record['component_type']:<20} {record['count']:<10} {examples}")
            
            # Query 7: Archived/Active Analysis
            print("\n📦 ARCHIVED VS ACTIVE CONFIGURATIONS")
            print("-" * 60)
            
            result = await session.run("""
                MATCH (c:Configuration)
                RETURN c.archived as archived,
                       COUNT(c) as count
                ORDER BY archived
            """)
            
            async for record in result:
                status = "Archived" if record['archived'] else "Active"
                print(f"{status}: {record['count']} configurations")
            
            # Query 8: Virtual Infrastructure (if any)
            print("\n☁️ VIRTUALIZATION ANALYSIS")
            print("-" * 60)
            
            result = await session.run("""
                MATCH (host:Server)-[:HOSTS|HOSTED_ON]-(vm)
                RETURN host.name as hypervisor,
                       COLLECT(vm.name) as virtual_machines
            """)
            
            found_vms = False
            async for record in result:
                found_vms = True
                print(f"Hypervisor: {record['hypervisor']}")
                print(f"VMs: {', '.join(record['virtual_machines'])}")
            
            if not found_vms:
                # Check for potential hypervisors
                result = await session.run("""
                    MATCH (h:Server) WHERE h.name CONTAINS 'HYPERV'
                    RETURN h.name as hypervisor
                """)
                
                async for record in result:
                    print(f"Potential Hypervisor found: {record['hypervisor']}")
                    print("(No VM relationships defined yet)")
            
            print("\n" + "=" * 80)
            print("GRAPH QUERY CAPABILITIES DEMONSTRATED:")
            print("-" * 80)
            print("""
1. ✅ Impact Analysis - Trace what fails when component X fails
2. ✅ Dependency Mapping - Understand service dependencies  
3. ✅ Network Topology - Visualize infrastructure hierarchy
4. ✅ Single Points of Failure - Identify critical components
5. ✅ Path Finding - Trace network paths between components
6. ✅ Statistical Analysis - Infrastructure inventory
7. ✅ Status Tracking - Active vs archived components
8. ✅ Virtualization Mapping - Host/VM relationships

Neo4j enables complex relationship queries that would be difficult
or impossible with traditional SQL databases!
            """)
            print("=" * 80)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(run_graph_queries())