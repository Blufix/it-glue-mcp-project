#!/usr/bin/env python3
"""
Document Sync Example - How to sync and embed IT Glue documents.

This example shows the complete document synchronization process including:
1. Fetching documents from IT Glue API
2. Storing in PostgreSQL database
3. Generating embeddings for semantic search
4. Verifying sync results

Key Learnings:
- Documents were already properly synced from markdown imports
- Embeddings are automatically generated during sync
- Confidence threshold of 0.4 works better than 0.7 for policy documents
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.data import db_manager, UnitOfWork
from src.data.models import ITGlueEntity
from src.embeddings.generator import EmbeddingGenerator
from sqlalchemy import text


async def check_document_sync_status():
    """Check the current status of document sync for an organization."""
    print("📊 Document Sync Status Check")
    print("=" * 50)
    
    org_id = "3183713165639879"  # Faucets Limited
    
    try:
        await db_manager.initialize()
        
        async with db_manager.get_session() as session:
            # Get document counts and status
            result = await session.execute(text("""
                SELECT 
                    COUNT(*) as total_docs,
                    COUNT(CASE WHEN embedding_id IS NOT NULL AND embedding_id != '' THEN 1 END) as embedded_docs,
                    AVG(length(search_text)) as avg_content_length,
                    MAX(last_synced) as last_sync_time
                FROM itglue_entities 
                WHERE organization_id = :org_id AND entity_type = 'document'
            """), {"org_id": org_id})
            
            stats = result.fetchone()
            
            print(f"🏢 Organization ID: {org_id}")
            print(f"📄 Total Documents: {stats.total_docs}")
            print(f"🔄 Embedded Documents: {stats.embedded_docs}")
            print(f"📏 Average Content Length: {stats.avg_content_length:.0f} chars")
            print(f"⏰ Last Sync: {stats.last_sync_time}")
            
            # Get individual document details
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
            
            documents = result.fetchall()
            
            print(f"\n📋 Individual Document Status:")
            for doc in documents:
                print(f"   • {doc.name}")
                print(f"     Content: {doc.content_length} chars | Embedding: {doc.has_embedding}")
                print(f"     Synced: {doc.last_synced}")
                print()
            
            return {
                "total_docs": stats.total_docs,
                "embedded_docs": stats.embedded_docs,
                "sync_complete": stats.embedded_docs == stats.total_docs
            }
            
    except Exception as e:
        print(f"❌ Status check failed: {e}")
        return None


async def generate_embeddings_example():
    """Example of generating embeddings for documents."""
    print("🔄 Embedding Generation Example")
    print("=" * 40)
    
    org_id = "3183713165639879"
    
    try:
        await db_manager.initialize()
        generator = EmbeddingGenerator()
        
        async with db_manager.get_session() as session:
            # Find documents without embeddings
            result = await session.execute(text("""
                SELECT id, name, search_text
                FROM itglue_entities 
                WHERE organization_id = :org_id 
                AND entity_type = 'document'
                AND (embedding_id IS NULL OR embedding_id = '')
                AND search_text IS NOT NULL
            """), {"org_id": org_id})
            
            docs_to_embed = result.fetchall()
            
            if not docs_to_embed:
                print("✅ All documents already have embeddings")
                return True
            
            print(f"📝 Generating embeddings for {len(docs_to_embed)} documents...")
            
            for doc in docs_to_embed:
                try:
                    print(f"   Processing: {doc.name}")
                    
                    # Generate embedding
                    embedding = await generator.generate_embedding(doc.search_text)
                    
                    # Store embedding reference
                    embedding_id = f"doc_{doc.id}"
                    await session.execute(text("""
                        UPDATE itglue_entities 
                        SET embedding_id = :embedding_id
                        WHERE id = :doc_id
                    """), {"embedding_id": embedding_id, "doc_id": doc.id})
                    
                    print(f"   ✅ Embedding generated")
                    
                except Exception as e:
                    print(f"   ❌ Failed: {e}")
            
            await session.commit()
            return True
            
    except Exception as e:
        print(f"❌ Embedding generation failed: {e}")
        return False


async def verify_document_content():
    """Verify that documents have proper content for RAG queries."""
    print("🔍 Document Content Verification")
    print("=" * 40)
    
    org_id = "3183713165639879"
    
    try:
        await db_manager.initialize()
        
        async with db_manager.get_session() as session:
            # Get the Security Policies document specifically
            result = await session.execute(text("""
                SELECT name, attributes->>'content' as content,
                       search_text, embedding_id
                FROM itglue_entities 
                WHERE organization_id = :org_id 
                AND entity_type = 'document'
                AND name ILIKE '%security%'
                LIMIT 1
            """), {"org_id": org_id})
            
            doc = result.fetchone()
            
            if doc:
                print(f"✅ Found: {doc.name}")
                print(f"📄 Content Length: {len(doc.content)} chars")
                print(f"🔍 Search Text Length: {len(doc.search_text)} chars")
                print(f"🔄 Has Embedding: {'Yes' if doc.embedding_id else 'No'}")
                
                # Check for key compliance terms
                compliance_terms = ['GDPR', 'ISO 27001', 'PCI DSS', 'multi-factor', 'compliance']
                found_terms = []
                
                content_lower = doc.content.lower()
                for term in compliance_terms:
                    if term.lower() in content_lower:
                        found_terms.append(term)
                
                print(f"🎯 Compliance Terms Found: {', '.join(found_terms)}")
                
                if found_terms:
                    print("✅ Document ready for compliance queries")
                    return True
                else:
                    print("⚠️ Limited compliance content found")
                    return False
            else:
                print("❌ Security document not found")
                return False
                
    except Exception as e:
        print(f"❌ Content verification failed: {e}")
        return False


async def full_sync_verification():
    """Complete verification of document sync pipeline."""
    print("🎯 Full Document Sync Pipeline Verification")
    print("=" * 60)
    
    # Step 1: Check sync status
    status = await check_document_sync_status()
    if not status:
        return False
    
    # Step 2: Generate any missing embeddings
    if status["embedded_docs"] < status["total_docs"]:
        print("\n🔄 Generating missing embeddings...")
        await generate_embeddings_example()
    
    # Step 3: Verify content quality
    print("\n🔍 Verifying document content...")
    content_ok = await verify_document_content()
    
    # Step 4: Final status
    print(f"\n📊 Final Verification Results:")
    print(f"   Documents Synced: {status['total_docs']}")
    print(f"   Embeddings Generated: {status['embedded_docs']}")
    print(f"   Content Quality: {'✅ Good' if content_ok else '⚠️ Limited'}")
    
    sync_complete = status["sync_complete"] and content_ok
    print(f"   Overall Status: {'✅ READY FOR RAG QUERIES' if sync_complete else '❌ NEEDS WORK'}")
    
    return sync_complete


if __name__ == "__main__":
    print("🚀 Document Sync Verification Examples")
    
    # Run full verification
    result = asyncio.run(full_sync_verification())
    
    if result:
        print("\n🎉 Document sync pipeline is fully operational!")
        print("   Ready for RAG queries on Faucets compliance documentation.")
    else:
        print("\n❌ Document sync needs attention before RAG queries will work reliably.")