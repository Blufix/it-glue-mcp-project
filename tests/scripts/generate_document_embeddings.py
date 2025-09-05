#!/usr/bin/env python3
"""Generate embeddings for Faucets documents and store in Qdrant."""

import asyncio
import sys
from pathlib import Path
import aiohttp
import logging
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from src.config.settings import settings
from src.data import db_manager
from sqlalchemy import text
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "nomic-embed-text"


async def generate_embedding_ollama(text: str, session: aiohttp.ClientSession) -> list[float]:
    """Generate embedding for text using Ollama nomic model."""
    try:
        async with session.post(
            f"{settings.ollama_url}/api/embeddings",
            json={
                "model": EMBEDDING_MODEL,
                "prompt": text
            },
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status == 200:
                data = await response.json()
                return data["embedding"]
            else:
                logger.error(f"Ollama API error: {response.status}")
                return None
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        return None


async def generate_document_embeddings():
    """Generate embeddings for all Faucets documents."""
    
    print("=" * 80)
    print("GENERATING EMBEDDINGS FOR FAUCETS DOCUMENTS")
    print("=" * 80)
    
    await db_manager.initialize()
    
    org_id = "3183713165639879"  # Faucets organization ID
    
    # Fetch documents from database
    async with db_manager.get_session() as session:
        result = await session.execute(text("""
            SELECT 
                id,
                itglue_id,
                name,
                search_text,
                attributes
            FROM itglue_entities
            WHERE organization_id = :org_id
            AND entity_type = 'document'
            ORDER BY name
        """), {"org_id": org_id})
        
        documents = []
        for row in result:
            documents.append({
                'id': str(row.id),
                'itglue_id': row.itglue_id,
                'name': row.name,
                'search_text': row.search_text,
                'attributes': row.attributes
            })
    
    print(f"\n📄 Found {len(documents)} documents to process")
    print("-" * 40)
    
    # Initialize Qdrant client
    client = QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key if settings.qdrant_api_key else None
    )
    
    # Generate embeddings
    embeddings_generated = 0
    points = []
    
    async with aiohttp.ClientSession() as session:
        for doc in documents:
            print(f"\n📝 Processing: {doc['name']}")
            
            # Generate embedding for search text
            embedding = await generate_embedding_ollama(doc['search_text'], session)
            
            if embedding:
                # Create Qdrant point with numeric ID
                # Use hash of itglue_id to create numeric ID
                point_id = hash(doc['itglue_id']) % (10**8)  # Keep it positive and manageable
                
                point = PointStruct(
                    id=abs(point_id),
                    vector=embedding,
                    payload={
                        "entity_id": doc['id'],
                        "itglue_id": doc['itglue_id'],
                        "name": doc['name'],
                        "entity_type": "document",
                        "organization_id": org_id,
                        "tags": doc['attributes'].get('tags', []),
                        "word_count": doc['attributes'].get('word_count', 0),
                        "content_type": doc['attributes'].get('content-type', 'text/markdown')
                    }
                )
                points.append(point)
                embeddings_generated += 1
                print(f"  ✓ Embedding generated (768 dimensions)")
                print(f"  ✓ Tags: {', '.join(doc['attributes'].get('tags', []))}")
            else:
                print(f"  ❌ Failed to generate embedding")
    
    # Store in Qdrant
    if points:
        print(f"\n💾 Storing {len(points)} embeddings in Qdrant...")
        
        try:
            # Upsert points (update if exists, insert if not)
            client.upsert(
                collection_name="itglue_entities",
                points=points
            )
            print(f"✅ Successfully stored {len(points)} embeddings")
            
            # Update PostgreSQL with embedding IDs
            async with db_manager.get_session() as session:
                for point in points:
                    # Find the original doc by payload
                    itglue_id = point.payload['itglue_id']
                    await session.execute(text("""
                        UPDATE itglue_entities
                        SET embedding_id = :embedding_id,
                            updated_at = :updated_at
                        WHERE itglue_id = :itglue_id
                    """), {
                        'embedding_id': str(point.id),
                        'itglue_id': itglue_id,
                        'updated_at': datetime.utcnow()
                    })
                await session.commit()
                print("✅ Updated PostgreSQL with embedding IDs")
                
        except Exception as e:
            logger.error(f"Failed to store embeddings: {e}")
    
    print("\n" + "=" * 80)
    print("EMBEDDING SUMMARY")
    print("=" * 80)
    print(f"""
Documents processed: {len(documents)}
Embeddings generated: {embeddings_generated}
Model: {EMBEDDING_MODEL} (768 dimensions)

The documents are now ready for semantic search!
You can search for concepts and ideas, not just keywords.

Try searches like:
- "How to handle system failures"
- "Network security best practices"
- "Emergency procedures"
- "Data protection requirements"
- "Infrastructure monitoring"
""")


if __name__ == "__main__":
    asyncio.run(generate_document_embeddings())