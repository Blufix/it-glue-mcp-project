#!/usr/bin/env python3
"""
Generate embeddings for Faucets data using Ollama's nomic-embed-text model.
This script populates Qdrant with 768-dimensional embeddings for semantic search.
"""

import asyncio
import sys
import uuid
from pathlib import Path
from datetime import datetime
import logging
import aiohttp
import json

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.data import db_manager
from src.config.settings import settings
from sqlalchemy import text
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
COLLECTION_NAME = "itglue_entities"
EMBEDDING_MODEL = "nomic-embed-text"
EMBEDDING_DIM = 768
BATCH_SIZE = 10  # Process in batches to avoid overload


async def generate_embedding_ollama(text: str, session: aiohttp.ClientSession) -> list[float]:
    """Generate embedding for a single text using Ollama nomic model."""
    try:
        async with session.post(
            f"{settings.ollama_url}/api/embeddings",
            json={"model": EMBEDDING_MODEL, "prompt": text},
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status == 200:
                data = await response.json()
                return data["embedding"]
            else:
                logger.error(f"Ollama API error: {response.status}")
                return None
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return None


async def recreate_qdrant_collection():
    """Recreate Qdrant collection with correct dimensions for nomic model."""
    logger.info("Recreating Qdrant collection for 768-dimensional nomic embeddings...")
    
    client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
    
    # Delete existing collection if it exists
    try:
        collections = client.get_collections().collections
        if any(c.name == COLLECTION_NAME for c in collections):
            logger.info(f"Deleting existing collection: {COLLECTION_NAME}")
            client.delete_collection(COLLECTION_NAME)
    except Exception as e:
        logger.warning(f"Error checking/deleting collection: {e}")
    
    # Create new collection with 768 dimensions
    logger.info(f"Creating collection with {EMBEDDING_DIM} dimensions...")
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=EMBEDDING_DIM,
            distance=Distance.COSINE
        )
    )
    
    logger.info("✅ Collection created successfully")
    return client


async def fetch_entities():
    """Fetch all entities from PostgreSQL."""
    logger.info("Fetching entities from database...")
    
    await db_manager.initialize()
    
    entities = []
    async with db_manager.get_session() as session:
        result = await session.execute(text("""
            SELECT 
                id,
                itglue_id,
                entity_type,
                organization_id,
                name,
                search_text,
                attributes
            FROM itglue_entities
            ORDER BY entity_type, name
        """))
        
        for row in result:
            entities.append({
                'id': str(row.id),
                'itglue_id': row.itglue_id,
                'entity_type': row.entity_type,
                'organization_id': row.organization_id,
                'name': row.name,
                'search_text': row.search_text or row.name,
                'attributes': row.attributes or {}
            })
    
    logger.info(f"✅ Fetched {len(entities)} entities")
    return entities


async def generate_and_store_embeddings(entities: list, qdrant_client: QdrantClient):
    """Generate embeddings and store in Qdrant."""
    logger.info(f"Generating embeddings for {len(entities)} entities...")
    
    points = []
    failed_count = 0
    
    async with aiohttp.ClientSession() as session:
        for i in range(0, len(entities), BATCH_SIZE):
            batch = entities[i:i + BATCH_SIZE]
            logger.info(f"Processing batch {i//BATCH_SIZE + 1}/{(len(entities) + BATCH_SIZE - 1)//BATCH_SIZE}")
            
            for entity in batch:
                # Generate embedding for search_text
                embedding = await generate_embedding_ollama(entity['search_text'], session)
                
                if embedding:
                    # Create Qdrant point
                    point_id = str(uuid.uuid4())
                    points.append(
                        PointStruct(
                            id=point_id,
                            vector=embedding,
                            payload={
                                'entity_id': entity['id'],
                                'itglue_id': entity['itglue_id'],
                                'entity_type': entity['entity_type'],
                                'organization_id': entity['organization_id'],
                                'name': entity['name'],
                                'text': entity['search_text'][:1000],  # First 1000 chars
                                'attributes': entity['attributes']
                            }
                        )
                    )
                    
                    # Store embedding_id back in PostgreSQL
                    await update_entity_embedding_id(entity['id'], point_id)
                    
                    logger.debug(f"✅ Generated embedding for: {entity['name']}")
                else:
                    failed_count += 1
                    logger.warning(f"❌ Failed to generate embedding for: {entity['name']}")
            
            # Upsert batch to Qdrant
            if points:
                qdrant_client.upsert(
                    collection_name=COLLECTION_NAME,
                    points=points[-len(batch):]  # Only upsert current batch
                )
                logger.info(f"   Stored {len(batch)} embeddings in Qdrant")
            
            # Small delay to avoid overloading Ollama
            await asyncio.sleep(0.5)
    
    logger.info(f"\n✅ Successfully generated {len(points)} embeddings")
    if failed_count > 0:
        logger.warning(f"⚠️ Failed to generate {failed_count} embeddings")
    
    return len(points), failed_count


async def update_entity_embedding_id(entity_id: str, embedding_id: str):
    """Update entity with embedding_id reference."""
    async with db_manager.get_session() as session:
        await session.execute(text("""
            UPDATE itglue_entities 
            SET embedding_id = :embedding_id
            WHERE id = :entity_id
        """), {'entity_id': entity_id, 'embedding_id': embedding_id})
        await session.commit()


async def populate_embedding_queue():
    """Populate embedding queue for tracking."""
    logger.info("Populating embedding queue...")
    
    async with db_manager.get_session() as session:
        # Clear existing queue
        await session.execute(text("DELETE FROM embedding_queue"))
        
        # Add all entities to queue
        await session.execute(text("""
            INSERT INTO embedding_queue (id, entity_id, entity_type, status, created_at)
            SELECT 
                gen_random_uuid(),
                id::text,
                entity_type,
                'pending',
                NOW()
            FROM itglue_entities
        """))
        
        await session.commit()
        
        result = await session.execute(text("SELECT COUNT(*) FROM embedding_queue"))
        count = result.scalar()
        logger.info(f"✅ Added {count} items to embedding queue")


async def verify_embeddings(qdrant_client: QdrantClient):
    """Verify embeddings were created successfully."""
    logger.info("\nVerifying embeddings...")
    
    # Check Qdrant collection
    collection_info = qdrant_client.get_collection(COLLECTION_NAME)
    logger.info(f"Qdrant collection stats:")
    logger.info(f"  - Vectors: {collection_info.vectors_count}")
    logger.info(f"  - Points: {collection_info.points_count}")
    logger.info(f"  - Dimension: {collection_info.config.params.vectors.size}")
    
    # Check PostgreSQL
    async with db_manager.get_session() as session:
        result = await session.execute(text("""
            SELECT 
                COUNT(*) as total,
                COUNT(embedding_id) as with_embeddings
            FROM itglue_entities
        """))
        row = result.fetchone()
        logger.info(f"\nPostgreSQL stats:")
        logger.info(f"  - Total entities: {row.total}")
        logger.info(f"  - With embeddings: {row.with_embeddings}")
        
        # Test a sample search
        logger.info("\nTesting semantic search...")
        test_query = "server configuration"
        embedding = None
        
        async with aiohttp.ClientSession() as session_http:
            embedding = await generate_embedding_ollama(test_query, session_http)
        
        if embedding:
            results = qdrant_client.search(
                collection_name=COLLECTION_NAME,
                query_vector=embedding,
                limit=5
            )
            
            logger.info(f"Search for '{test_query}' returned {len(results)} results:")
            for i, result in enumerate(results, 1):
                logger.info(f"  {i}. {result.payload.get('name')} (score: {result.score:.3f})")


async def main():
    """Main execution function."""
    print("=" * 80)
    print("EMBEDDING GENERATION FOR FAUCETS DATA")
    print("=" * 80)
    print(f"Model: {EMBEDDING_MODEL} ({EMBEDDING_DIM} dimensions)")
    print(f"Ollama URL: {settings.ollama_url}")
    print(f"Qdrant URL: {settings.qdrant_url}")
    print("=" * 80)
    
    try:
        # Step 1: Recreate Qdrant collection
        qdrant_client = await recreate_qdrant_collection()
        
        # Step 2: Fetch entities
        entities = await fetch_entities()
        
        if not entities:
            logger.warning("No entities found in database!")
            return
        
        # Step 3: Populate embedding queue (for tracking)
        await populate_embedding_queue()
        
        # Step 4: Generate and store embeddings
        success_count, fail_count = await generate_and_store_embeddings(entities, qdrant_client)
        
        # Step 5: Verify embeddings
        await verify_embeddings(qdrant_client)
        
        # Update embedding queue status
        async with db_manager.get_session() as session:
            await session.execute(text("""
                UPDATE embedding_queue 
                SET status = 'processed', processed_at = NOW()
                WHERE entity_id IN (
                    SELECT id::text FROM itglue_entities WHERE embedding_id IS NOT NULL
                )
            """))
            await session.commit()
        
        print("\n" + "=" * 80)
        print("✅ EMBEDDING GENERATION COMPLETE")
        print(f"   Successfully processed: {success_count}")
        print(f"   Failed: {fail_count}")
        print("=" * 80)
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        raise
    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())