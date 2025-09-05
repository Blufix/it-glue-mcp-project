#!/usr/bin/env python3
"""Simple document sync for Faucets Limited - focusing on the Compliance document."""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.itglue.client import ITGlueClient
from src.data import db_manager, UnitOfWork
from src.data.models import ITGlueEntity
from src.embeddings.generator import EmbeddingGenerator
from sqlalchemy import text


async def sync_faucets_documents():
    """Sync documents for Faucets Limited organization."""
    print("📄 Syncing Faucets Limited Documents")
    print("=" * 60)
    
    org_id = "3183713165639879"  # Known Faucets Limited ID
    
    try:
        # Initialize services
        await db_manager.initialize()
        client = ITGlueClient()
        
        print(f"🎯 Target Organization ID: {org_id}")
        
        # Step 1: Get organization to verify
        print("\n📋 Step 1: Verifying organization...")
        try:
            org = await client.get_organization(org_id)
            print(f"✅ Organization: {org.name}")
        except Exception as e:
            print(f"❌ Failed to get organization: {e}")
            print("   Continuing with known org ID...")
        
        # Step 2: Get documents directly using individual API calls to avoid timeout
        print("\n📄 Step 2: Fetching documents (avoiding bulk API calls)...")
        
        # First, check what document IDs we already have in the database
        async with db_manager.get_session() as session:
            result = await session.execute(text("""
                SELECT itglue_id, name 
                FROM itglue_entities 
                WHERE organization_id = :org_id AND entity_type = 'document'
                ORDER BY name
            """), {"org_id": org_id})
            
            existing_docs = result.fetchall()
            print(f"📊 Found {len(existing_docs)} documents in database:")
            for doc in existing_docs:
                print(f"   • {doc.name} (ID: {doc.itglue_id})")
        
        # Step 3: Get fresh document data from API for each document
        print(f"\n🔄 Step 3: Refreshing document data from API...")
        
        synced_count = 0
        for doc_row in existing_docs:
            doc_id = doc_row.itglue_id
            doc_name = doc_row.name
            
            try:
                print(f"\n📋 Processing: {doc_name}")
                
                # Get full document from API
                full_doc = await client.get_document(doc_id)
                print(f"   ✅ Retrieved from API")
                
                # Check if it has content
                content = getattr(full_doc, 'content', None) or getattr(full_doc, 'body', None)
                if content:
                    print(f"   📄 Content: {len(content)} characters")
                    if 'compliance' in doc_name.lower():
                        print(f"   🎯 COMPLIANCE DOCUMENT FOUND!")
                        print(f"   Preview: {content[:200]}...")
                else:
                    print(f"   ⚠️ No content found")
                    print(f"   Available attributes: {list(full_doc.__dict__.keys())}")
                    # Try to extract content from attributes
                    if hasattr(full_doc, 'attributes') and full_doc.attributes:
                        content = full_doc.attributes.get('content') or full_doc.attributes.get('body')
                        if content:
                            print(f"   📄 Found content in attributes: {len(content)} characters")
                
                # Create search text
                search_text = ""
                if hasattr(full_doc, 'name'):
                    search_text += full_doc.name + " "
                if content:
                    search_text += content
                
                # Prepare attributes
                attributes = getattr(full_doc, 'attributes', {})
                if content and 'content' not in attributes:
                    attributes['content'] = content
                
                # Update database entry
                entity = ITGlueEntity(
                    itglue_id=doc_id,
                    entity_type='document',
                    organization_id=org_id,
                    name=getattr(full_doc, 'name', doc_name),
                    attributes=attributes,
                    relationships=getattr(full_doc, 'relationships', {}),
                    search_text=search_text,
                    last_synced=datetime.utcnow()
                )
                
                # Save to database
                async with db_manager.get_session() as session:
                    uow = UnitOfWork(session)
                    await uow.itglue.create_or_update(entity)
                    await uow.commit()
                
                print(f"   ✅ Updated in database")
                synced_count += 1
                
            except Exception as e:
                print(f"   ❌ Error processing {doc_name}: {e}")
        
        print(f"\n✅ Synced {synced_count} documents")
        
        # Step 4: Generate embeddings for documents with content
        print(f"\n🔄 Step 4: Generating embeddings...")
        
        try:
            generator = EmbeddingGenerator()
            embedded_count = 0
            
            async with db_manager.get_session() as session:
                # Get documents that need embeddings
                result = await session.execute(text("""
                    SELECT id, name, search_text, attributes
                    FROM itglue_entities 
                    WHERE organization_id = :org_id 
                    AND entity_type = 'document'
                    AND search_text IS NOT NULL 
                    AND search_text != ''
                    AND (embedding_id IS NULL OR embedding_id = '')
                """), {"org_id": org_id})
                
                docs_for_embedding = result.fetchall()
                
                for doc in docs_for_embedding:
                    try:
                        print(f"   🔄 Generating embedding for: {doc.name}")
                        
                        # Generate embedding from search text
                        embedding = await generator.generate_embedding(doc.search_text)
                        
                        # Store embedding reference
                        embedding_id = f"doc_{doc.id}"
                        await session.execute(text("""
                            UPDATE itglue_entities 
                            SET embedding_id = :embedding_id
                            WHERE id = :doc_id
                        """), {"embedding_id": embedding_id, "doc_id": doc.id})
                        
                        print(f"   ✅ Embedding generated")
                        embedded_count += 1
                        
                    except Exception as e:
                        print(f"   ❌ Embedding failed for {doc.name}: {e}")
                
                await session.commit()
            
            print(f"✅ Generated {embedded_count} embeddings")
            
        except Exception as e:
            print(f"❌ Embedding generation failed: {e}")
        
        # Step 5: Verify final state
        print(f"\n📊 Step 5: Final verification...")
        
        async with db_manager.get_session() as session:
            result = await session.execute(text("""
                SELECT name, 
                       length(search_text) as content_length,
                       CASE WHEN embedding_id IS NOT NULL AND embedding_id != '' 
                            THEN 'Yes' ELSE 'No' END as has_embedding,
                       last_synced
                FROM itglue_entities 
                WHERE organization_id = :org_id AND entity_type = 'document'
                ORDER BY name
            """), {"org_id": org_id})
            
            final_docs = result.fetchall()
            
            print(f"📋 Final document status:")
            for doc in final_docs:
                print(f"   • {doc.name}")
                print(f"     Content: {doc.content_length} chars")
                print(f"     Embedding: {doc.has_embedding}")
                print(f"     Last synced: {doc.last_synced}")
                print()
        
        print("🎉 Document sync complete!")
        
    except Exception as e:
        print(f"❌ Document sync failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(sync_faucets_documents())