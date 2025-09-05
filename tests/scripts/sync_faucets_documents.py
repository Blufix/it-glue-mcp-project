#!/usr/bin/env python3
"""Sync the 5 Faucets documents from IT Glue API."""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import logging

sys.path.insert(0, str(Path(__file__).parent))

from src.config.settings import settings
from src.data import db_manager, UnitOfWork
from src.data.models import ITGlueEntity
from sqlalchemy import text
import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fetch_document_details(session: aiohttp.ClientSession, doc_id: str) -> dict:
    """Fetch detailed information for a specific document."""
    url = f"{settings.itglue_api_url}/documents/{doc_id}"
    
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('data', {})
            else:
                logger.error(f"Failed to fetch document {doc_id}: {response.status}")
                return None
    except Exception as e:
        logger.error(f"Error fetching document {doc_id}: {e}")
        return None


async def sync_faucets_documents():
    """Sync the 5 Faucets documents into the database."""
    
    print("=" * 80)
    print("SYNCING FAUCETS DOCUMENTS")
    print("=" * 80)
    
    await db_manager.initialize()
    
    # Document IDs we found
    document_ids = [
        "4371391006916744",
        "4371399366541507", 
        "4371401968500956",
        "4371408978673864",
        "4371416047026426"
    ]
    
    org_id = "3183713165639879"  # Faucets organization ID
    
    headers = {
        "x-api-key": settings.itglue_api_key,
        "Content-Type": "application/vnd.api+json"
    }
    
    documents_synced = 0
    
    async with aiohttp.ClientSession(headers=headers) as session:
        print(f"\n📄 Fetching {len(document_ids)} documents...")
        print("-" * 40)
        
        for doc_id in document_ids:
            print(f"\nFetching document {doc_id}...")
            
            # Fetch document details
            doc_data = await fetch_document_details(session, doc_id)
            
            if doc_data:
                attributes = doc_data.get('attributes', {})
                
                # Extract document information
                name = attributes.get('name', f'Document {doc_id}')
                content = attributes.get('content', '')
                parsed_content = attributes.get('parsed-content', '')
                content_type = attributes.get('content-type', 'text/plain')
                created_at = attributes.get('created-at')
                updated_at = attributes.get('updated-at')
                
                print(f"  ✓ Name: {name}")
                print(f"  ✓ Content Type: {content_type}")
                print(f"  ✓ Content Length: {len(content)} chars")
                print(f"  ✓ Parsed Content Length: {len(parsed_content)} chars")
                
                # Build searchable text from all content
                search_text_parts = [name]
                if content:
                    search_text_parts.append(content)
                if parsed_content:
                    search_text_parts.append(parsed_content)
                
                # Also check for any description or notes
                if attributes.get('description'):
                    search_text_parts.append(attributes['description'])
                if attributes.get('notes'):
                    search_text_parts.append(attributes['notes'])
                
                search_text = ' '.join(search_text_parts).lower()
                
                # Store in database
                async with db_manager.get_session() as db_session:
                    uow = UnitOfWork(db_session)
                    
                    entity = ITGlueEntity(
                        itglue_id=doc_id,
                        entity_type='document',
                        organization_id=org_id,
                        name=name,
                        attributes=attributes,
                        relationships=doc_data.get('relationships', {}),
                        search_text=search_text,
                        last_synced=datetime.utcnow()
                    )
                    
                    await uow.itglue.create_or_update(entity)
                    await uow.commit()
                    
                    documents_synced += 1
                    print(f"  ✅ Saved to database")
            else:
                print(f"  ❌ Failed to fetch document")
            
            # Small delay to respect rate limits
            await asyncio.sleep(0.5)
    
    # Verify documents in database
    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)
    
    async with db_manager.get_session() as session:
        result = await session.execute(text("""
            SELECT itglue_id, name, 
                   LENGTH(search_text) as search_text_length,
                   attributes->>'content-type' as content_type
            FROM itglue_entities
            WHERE organization_id = :org_id
            AND entity_type = 'document'
            ORDER BY name
        """), {"org_id": org_id})
        
        docs = result.fetchall()
        print(f"\n📊 Documents in database: {len(docs)}")
        print("-" * 40)
        
        for doc in docs:
            print(f"\n📄 {doc.name}")
            print(f"   ID: {doc.itglue_id}")
            print(f"   Content Type: {doc.content_type}")
            print(f"   Search Text Length: {doc.search_text_length:,} chars")
        
        # Show sample content from one document
        if docs:
            result = await session.execute(text("""
                SELECT name, attributes
                FROM itglue_entities
                WHERE itglue_id = :doc_id
            """), {"doc_id": docs[0].itglue_id})
            
            sample = result.first()
            if sample and sample.attributes:
                content = sample.attributes.get('content', '')
                parsed = sample.attributes.get('parsed-content', '')
                
                print(f"\n📝 Sample from '{sample.name}':")
                print("-" * 40)
                
                if content:
                    preview = content[:500].replace('\n', ' ')
                    print(f"Content preview: {preview}...")
                elif parsed:
                    preview = parsed[:500].replace('\n', ' ')
                    print(f"Parsed content preview: {preview}...")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"""
✅ Documents synced: {documents_synced}/{len(document_ids)}

Next steps:
1. Generate embeddings for semantic search:
   python generate_embeddings_for_documents.py
   
2. Update Neo4j graph with document relationships:
   python update_document_graph.py
   
3. Test document search:
   python test_document_search.py

The documents are now in PostgreSQL and ready for:
- Keyword search (using search_text field)
- Semantic search (after embedding generation)
- Graph relationships (after Neo4j update)
""")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(sync_faucets_documents())