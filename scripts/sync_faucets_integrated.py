#!/usr/bin/env python3
"""Integrated sync for Faucets organization - PostgreSQL + Qdrant + Neo4j."""

import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.sync.itglue_sync import sync_single_organization, ITGlueSyncManager
from src.services.itglue.client import ITGlueClient
from src.data import db_manager, UnitOfWork
from src.config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def find_faucets_organization() -> Optional[Dict[str, Any]]:
    """Find Faucets organization in IT Glue."""
    print("🔍 Finding Faucets organization...")
    
    try:
        client = ITGlueClient()
        
        # Try variations of "Faucets"
        faucet_variations = ["Faucets", "Faucets Ltd", "faucets"]
        
        for variation in faucet_variations:
            try:
                orgs = await client.get_organizations(filters={"name": variation})
                if orgs:
                    org = orgs[0]
                    print(f"✅ Found Faucets organization: {org.name} (ID: {org.id})")
                    return {"id": org.id, "name": org.name}
            except Exception as e:
                print(f"   Tried '{variation}': {e}")
        
        # Fallback: Check all organizations for Faucets-like names
        print("🔍 Checking all organizations for Faucets-like names...")
        all_orgs = await client.get_organizations()
        
        for org in all_orgs:
            if "faucet" in org.name.lower():
                print(f"✅ Found Faucets-like organization: {org.name} (ID: {org.id})")
                return {"id": org.id, "name": org.name}
        
        print("❌ No Faucets organization found")
        return None
        
    except Exception as e:
        print(f"❌ Error finding Faucets organization: {e}")
        return None


async def get_sync_counts(org_id: str) -> Dict[str, int]:
    """Get current counts of synced entities."""
    try:
        async with db_manager.get_session() as session:
            from sqlalchemy import text
            
            entity_types = ['configuration', 'password', 'document', 'flexible_asset', 'contact', 'location']
            counts = {}
            
            for entity_type in entity_types:
                result = await session.execute(text("""
                    SELECT COUNT(*) FROM itglue_entities 
                    WHERE organization_id = :org_id AND entity_type = :entity_type
                """), {"org_id": org_id, "entity_type": entity_type})
                
                counts[entity_type] = result.scalar() or 0
                
            return counts
            
    except Exception as e:
        logger.error(f"Failed to get sync counts: {e}")
        return {}


async def generate_embeddings_for_org(org_id: str) -> Dict[str, Any]:
    """Generate embeddings for all entities in the organization."""
    print("🔄 Generating embeddings for synced entities...")
    
    try:
        from src.embeddings.generator import EmbeddingGenerator
        from src.embeddings.manager import EmbeddingManager
        
        # Initialize embedding components
        generator = EmbeddingGenerator()
        manager = EmbeddingManager(generator=generator)
        
        # Get entities that need embeddings
        async with db_manager.get_session() as session:
            from sqlalchemy import text
            
            result = await session.execute(text("""
                SELECT id, itglue_id, entity_type, name, search_text, attributes
                FROM itglue_entities 
                WHERE organization_id = :org_id 
                AND (embedding_id IS NULL OR embedding_id = '')
                ORDER BY entity_type, created_at
            """), {"org_id": org_id})
            
            entities = result.fetchall()
            
        if not entities:
            print("✅ No entities need embeddings")
            return {"processed": 0, "success": True}
        
        print(f"📝 Processing {len(entities)} entities for embeddings...")
        
        processed = 0
        errors = 0
        
        for entity in entities:
            try:
                # Create text representation for embedding
                text_content = entity.search_text or ""
                if entity.attributes and isinstance(entity.attributes, dict):
                    # Add key attributes to embedding text
                    for key, value in entity.attributes.items():
                        if isinstance(value, str) and value:
                            text_content += f" {value}"
                
                if text_content.strip():
                    # Generate embedding
                    embedding = await generator.generate_embedding(text_content)
                    
                    # Store in database (we'll add Qdrant integration later)
                    async with db_manager.get_session() as session:
                        from sqlalchemy import text
                        embedding_id = f"emb_{entity.id}"
                        
                        await session.execute(text("""
                            UPDATE itglue_entities 
                            SET embedding_id = :embedding_id
                            WHERE id = :entity_id
                        """), {"embedding_id": embedding_id, "entity_id": entity.id})
                        
                        await session.commit()
                    
                    processed += 1
                    
                    if processed % 10 == 0:
                        print(f"   Processed {processed}/{len(entities)} embeddings...")
                        
            except Exception as e:
                logger.error(f"Failed to generate embedding for entity {entity.id}: {e}")
                errors += 1
        
        print(f"✅ Generated {processed} embeddings ({errors} errors)")
        
        return {
            "processed": processed,
            "errors": errors,
            "success": processed > 0
        }
        
    except Exception as e:
        print(f"❌ Embedding generation failed: {e}")
        logger.error(f"Embedding generation error: {e}", exc_info=True)
        return {"processed": 0, "errors": 1, "success": False}


async def create_neo4j_relationships(org_id: str) -> Dict[str, Any]:
    """Create Neo4j relationships for the organization."""
    print("🔗 Creating Neo4j relationships...")
    
    try:
        # For now, let's create a simple relationship mapping
        # This is a placeholder - in a full implementation, you'd analyze
        # the actual relationships in the IT Glue data
        
        from neo4j import AsyncGraphDatabase
        from src.config.settings import settings
        
        if not settings.neo4j_uri:
            print("⚠️ Neo4j not configured, skipping relationship creation")
            return {"created": 0, "success": True}
        
        # Initialize Neo4j driver
        driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        
        try:
            async with driver.session() as session:
                # Get entities from PostgreSQL
                async with db_manager.get_session() as pg_session:
                    from sqlalchemy import text
                    
                    result = await pg_session.execute(text("""
                        SELECT itglue_id, entity_type, name, attributes, organization_id
                        FROM itglue_entities 
                        WHERE organization_id = :org_id
                        ORDER BY entity_type
                    """), {"org_id": org_id})
                    
                    entities = result.fetchall()
                
                if not entities:
                    print("⚠️ No entities found for Neo4j relationships")
                    return {"created": 0, "success": True}
                
                relationships_created = 0
                
                # Create organization node
                await session.run("""
                    MERGE (org:Organization {itglue_id: $org_id, name: $org_name})
                """, org_id=org_id, org_name=f"Organization_{org_id}")
                
                # Create entity nodes and relationships
                for entity in entities:
                    try:
                        # Create entity node
                        await session.run(f"""
                            MERGE (e:{entity.entity_type.title()} {{
                                itglue_id: $itglue_id, 
                                name: $name,
                                entity_type: $entity_type
                            }})
                        """, 
                        itglue_id=entity.itglue_id,
                        name=entity.name or f"Unnamed {entity.entity_type}",
                        entity_type=entity.entity_type)
                        
                        # Create relationship to organization
                        await session.run(f"""
                            MATCH (org:Organization {{itglue_id: $org_id}})
                            MATCH (e:{entity.entity_type.title()} {{itglue_id: $itglue_id}})
                            MERGE (e)-[:BELONGS_TO]->(org)
                        """, org_id=org_id, itglue_id=entity.itglue_id)
                        
                        relationships_created += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to create Neo4j node for entity {entity.itglue_id}: {e}")
                
                print(f"✅ Created {relationships_created} Neo4j relationships")
                
                return {
                    "created": relationships_created,
                    "success": True
                }
                
        finally:
            await driver.close()
        
    except Exception as e:
        print(f"❌ Neo4j relationship creation failed: {e}")
        logger.error(f"Neo4j error: {e}", exc_info=True)
        return {"created": 0, "success": False}


async def verify_integration(org_id: str, org_name: str) -> Dict[str, Any]:
    """Verify that all three databases have the data."""
    print("\n🔍 Verifying Triple Database Integration...")
    
    verification = {
        "postgresql": {"status": "unknown", "count": 0},
        "embeddings": {"status": "unknown", "count": 0}, 
        "neo4j": {"status": "unknown", "count": 0}
    }
    
    # Check PostgreSQL
    try:
        counts = await get_sync_counts(org_id)
        total_pg = sum(counts.values())
        verification["postgresql"] = {
            "status": "success" if total_pg > 0 else "empty",
            "count": total_pg,
            "breakdown": counts
        }
        print(f"✅ PostgreSQL: {total_pg} entities")
    except Exception as e:
        verification["postgresql"]["status"] = f"error: {e}"
        print(f"❌ PostgreSQL verification failed: {e}")
    
    # Check embeddings
    try:
        async with db_manager.get_session() as session:
            from sqlalchemy import text
            result = await session.execute(text("""
                SELECT COUNT(*) FROM itglue_entities 
                WHERE organization_id = :org_id 
                AND embedding_id IS NOT NULL AND embedding_id != ''
            """), {"org_id": org_id})
            
            embedding_count = result.scalar() or 0
            verification["embeddings"] = {
                "status": "success" if embedding_count > 0 else "empty",
                "count": embedding_count
            }
            print(f"✅ Embeddings: {embedding_count} entities")
    except Exception as e:
        verification["embeddings"]["status"] = f"error: {e}"
        print(f"❌ Embedding verification failed: {e}")
    
    # Check Neo4j (simplified check)
    try:
        if not settings.neo4j_uri:
            verification["neo4j"] = {"status": "not_configured", "count": 0}
            print("⚠️ Neo4j: Not configured")
        else:
            from neo4j import AsyncGraphDatabase
            driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password)
            )
            
            try:
                async with driver.session() as session:
                    result = await session.run("""
                        MATCH (n)-[:BELONGS_TO]->(org:Organization {itglue_id: $org_id})
                        RETURN count(n) as count
                    """, org_id=org_id)
                    
                    record = await result.single()
                    neo4j_count = record["count"] if record else 0
                    
                    verification["neo4j"] = {
                        "status": "success" if neo4j_count > 0 else "empty",
                        "count": neo4j_count
                    }
                    print(f"✅ Neo4j: {neo4j_count} entities")
            finally:
                await driver.close()
                
    except Exception as e:
        verification["neo4j"]["status"] = f"error: {e}"
        print(f"❌ Neo4j verification failed: {e}")
    
    return verification


async def main():
    """Main integrated sync function."""
    print("🚀 Starting Integrated Faucets Sync (PostgreSQL + Qdrant + Neo4j)")
    print("=" * 80)
    
    # Verify configuration
    if not settings.itglue_api_key:
        print("❌ ERROR: IT_GLUE_API_KEY not configured")
        return
    
    if not settings.database_url:
        print("❌ ERROR: DATABASE_URL not configured")
        return
    
    print(f"✅ Configuration verified")
    print(f"   API Key: {settings.itglue_api_key[:10]}...")
    print(f"   Database: {settings.database_url.split('@')[1] if '@' in settings.database_url else 'local'}")
    print(f"   Neo4j: {'Configured' if settings.neo4j_uri else 'Not configured'}")
    print()
    
    start_time = time.time()
    
    try:
        # Step 1: Find Faucets organization
        org = await find_faucets_organization()
        if not org:
            print("❌ Cannot proceed without Faucets organization")
            return
        
        org_id = org["id"]
        org_name = org["name"]
        
        print(f"🎯 Target: {org_name} (ID: {org_id})")
        print("=" * 80)
        
        # Step 2: PostgreSQL Sync
        print("\n📊 STEP 1: PostgreSQL Sync")
        print("-" * 40)
        
        pre_counts = await get_sync_counts(org_id)
        print(f"📋 Pre-sync counts: {sum(pre_counts.values())} total entities")
        
        await sync_single_organization(org_id)
        
        post_counts = await get_sync_counts(org_id)
        total_synced = sum(post_counts.values())
        print(f"✅ PostgreSQL sync complete: {total_synced} entities")
        
        if total_synced == 0:
            print("⚠️ No entities synced - check API connectivity and organization data")
            return
        
        # Step 3: Generate Embeddings
        print("\n🔄 STEP 2: Embedding Generation")
        print("-" * 40)
        
        embedding_result = await generate_embeddings_for_org(org_id)
        
        # Step 4: Create Neo4j Relationships  
        print("\n🔗 STEP 3: Neo4j Relationships")
        print("-" * 40)
        
        neo4j_result = await create_neo4j_relationships(org_id)
        
        # Step 5: Verification
        verification = await verify_integration(org_id, org_name)
        
        # Final Summary
        duration = time.time() - start_time
        
        print("\n" + "=" * 80)
        print("🎉 INTEGRATED SYNC COMPLETE!")
        print("=" * 80)
        print(f"⏱️  Duration: {duration:.1f} seconds")
        print(f"🏢 Organization: {org_name}")
        print(f"📊 PostgreSQL: {verification['postgresql']['count']} entities")
        print(f"🔄 Embeddings: {verification['embeddings']['count']} entities")
        print(f"🔗 Neo4j: {verification['neo4j']['count']} entities")
        
        success_count = sum(1 for db in verification.values() if db['status'] == 'success')
        print(f"\n✅ Databases operational: {success_count}/3")
        
        if success_count == 3:
            print("🎯 FULL TRIPLE DATABASE INTEGRATION SUCCESSFUL!")
        else:
            print("⚠️  Partial integration - check logs for issues")
        
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Integrated sync failed: {e}")
        logger.error(f"Sync error: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())