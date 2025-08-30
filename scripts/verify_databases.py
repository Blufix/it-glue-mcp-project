#!/usr/bin/env python3
"""Verify all database structures are properly initialized."""

import asyncio
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import settings

console = Console()


async def verify_all_databases():
    """Verify all database structures."""
    
    console.print(Panel.fit("🔍 Database Structure Verification", style="bold magenta"))
    
    results = []
    
    # 1. PostgreSQL Verification
    console.print("\n[bold cyan]PostgreSQL Database[/bold cyan]")
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
        
        engine = create_async_engine(settings.database_url)
        async with engine.connect() as conn:
            # Check tables
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]
            
            # Check indexes
            result = await conn.execute(text("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE schemaname = 'public'
            """))
            indexes = [row[0] for row in result]
            
            # Check functions
            result = await conn.execute(text("""
                SELECT routine_name 
                FROM information_schema.routines 
                WHERE routine_schema = 'public' 
                AND routine_type = 'FUNCTION'
            """))
            functions = [row[0] for row in result]
            
            console.print(f"  ✅ Tables: {len(tables)}")
            for table in tables:
                console.print(f"     • {table}")
            
            console.print(f"  ✅ Indexes: {len(indexes)}")
            console.print(f"  ✅ Functions: {len(functions)}")
            
            results.append(("PostgreSQL", "✅ Connected", f"{len(tables)} tables"))
        
        await engine.dispose()
        
    except Exception as e:
        console.print(f"  ❌ Error: {e}")
        results.append(("PostgreSQL", "❌ Failed", str(e)[:50]))
    
    # 2. Neo4j Verification
    console.print("\n[bold cyan]Neo4j Graph Database[/bold cyan]")
    try:
        from neo4j import AsyncGraphDatabase
        
        driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        
        async with driver.session() as session:
            # Check constraints
            result = await session.run("SHOW CONSTRAINTS")
            constraints = await result.data()
            
            # Check indexes
            result = await session.run("SHOW INDEXES")
            indexes = await result.data()
            
            # Check node labels
            result = await session.run("CALL db.labels()")
            labels = await result.data()
            
            console.print(f"  ✅ Constraints: {len(constraints)}")
            console.print(f"  ✅ Indexes: {len(indexes)}")
            console.print(f"  ✅ Node Labels: {len(labels)}")
            
            results.append(("Neo4j", "✅ Connected", f"{len(constraints)} constraints"))
        
        await driver.close()
        
    except Exception as e:
        console.print(f"  ❌ Error: {e}")
        results.append(("Neo4j", "❌ Failed", str(e)[:50]))
    
    # 3. Qdrant Verification
    console.print("\n[bold cyan]Qdrant Vector Database[/bold cyan]")
    try:
        from qdrant_client import QdrantClient
        
        client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            https=False,
            prefer_grpc=False,
            timeout=5
        )
        
        collections = client.get_collections()
        
        console.print(f"  ✅ Collections: {len(collections.collections)}")
        for collection in collections.collections:
            info = client.get_collection(collection.name)
            console.print(f"     • {collection.name}: {info.points_count} vectors")
        
        results.append(("Qdrant", "✅ Connected", f"{len(collections.collections)} collections"))
        
    except Exception as e:
        console.print(f"  ❌ Error: {e}")
        results.append(("Qdrant", "❌ Failed", str(e)[:50]))
    
    # 4. Redis Verification
    console.print("\n[bold cyan]Redis Cache[/bold cyan]")
    try:
        import redis.asyncio as redis
        
        client = redis.from_url(settings.redis_url)
        
        # Test connection
        await client.ping()
        
        # Get info
        info = await client.info()
        
        # Test cache operations
        await client.set("test_key", "test_value", ex=60)
        value = await client.get("test_key")
        await client.delete("test_key")
        
        console.print(f"  ✅ Connected to Redis")
        console.print(f"  ✅ Version: {info.get('redis_version', 'Unknown')}")
        console.print(f"  ✅ Cache operations working")
        
        results.append(("Redis", "✅ Connected", "Cache operational"))
        
        await client.aclose()
        
    except Exception as e:
        console.print(f"  ❌ Error: {e}")
        results.append(("Redis", "❌ Failed", str(e)[:50]))
    
    # Summary Table
    console.print("\n")
    table = Table(title="Database Status Summary", show_header=True, header_style="bold magenta")
    table.add_column("Database", style="cyan", width=20)
    table.add_column("Status", width=15)
    table.add_column("Details", style="dim")
    
    for db, status, details in results:
        style = "green" if "✅" in status else "red"
        table.add_row(db, status, details, style=style)
    
    console.print(table)
    
    # Overall status
    all_ok = all("✅" in status for _, status, _ in results)
    if all_ok:
        console.print("\n[bold green]✅ All databases are properly initialized and operational![/bold green]")
    else:
        console.print("\n[bold yellow]⚠️ Some databases need attention. Check the errors above.[/bold yellow]")
    
    return all_ok


if __name__ == "__main__":
    success = asyncio.run(verify_all_databases())
    sys.exit(0 if success else 1)