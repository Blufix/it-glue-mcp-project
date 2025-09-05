#!/usr/bin/env python3
"""Test the Compliance document extraction and RAG query."""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data import db_manager
from src.query.engine import QueryEngine
from src.services.itglue.client import ITGlueClient
from sqlalchemy import text
import json


async def test_compliance_document():
    """Test Compliance document content and RAG query."""
    print("📋 Testing Compliance Document & RAG Query")
    print("=" * 60)
    
    try:
        await db_manager.initialize()
        
        # Step 1: Extract the Compliance document content
        print("📄 Step 1: Examining Security Policies and Compliance document...")
        
        async with db_manager.get_session() as session:
            result = await session.execute(text("""
                SELECT name, attributes->>'content' as content, 
                       search_text, embedding_id, last_synced
                FROM itglue_entities 
                WHERE organization_id = '3183713165639879' 
                AND entity_type = 'document'
                AND name ILIKE '%compliance%'
                LIMIT 1
            """))
            
            compliance_doc = result.fetchone()
            
            if compliance_doc:
                print(f"✅ Found document: {compliance_doc.name}")
                print(f"📏 Content length: {len(compliance_doc.content)} characters")
                print(f"🔍 Search text length: {len(compliance_doc.search_text)} characters")
                print(f"🔄 Embedding ID: {compliance_doc.embedding_id}")
                print(f"📅 Last synced: {compliance_doc.last_synced}")
                
                print(f"\n📄 FULL CONTENT:")
                print("=" * 50)
                print(compliance_doc.content)
                print("=" * 50)
                
                # Check for security-related terms
                security_terms = ['GDPR', 'ISO 27001', 'PCI DSS', 'multi-factor', 'authentication', 'compliance', 'audit']
                found_terms = []
                
                content_lower = compliance_doc.content.lower()
                for term in security_terms:
                    if term.lower() in content_lower:
                        found_terms.append(term)
                
                print(f"\n🔍 Found security terms: {', '.join(found_terms)}")
                
            else:
                print("❌ Compliance document not found")
                return
        
        # Step 2: Test RAG query on this specific content
        print(f"\n🤖 Step 2: Testing RAG query on Compliance document...")
        
        # Initialize query engine
        client = ITGlueClient()
        query_engine = QueryEngine(itglue_client=client)
        
        # Test queries about compliance content
        test_queries = [
            "What compliance standards does Faucets follow?",
            "Tell me about Faucets' GDPR compliance",
            "What are Faucets' password policies?", 
            "What security audits does Faucets perform?",
            "What is Faucets' multi-factor authentication policy?"
        ]
        
        for query in test_queries:
            print(f"\n🎯 Query: {query}")
            print("-" * 40)
            
            try:
                result = await query_engine.process_query(
                    query=query,
                    company="Faucets Limited"
                )
                
                if result.get('success'):
                    answer = result.get('answer', 'No answer provided')
                    confidence = result.get('confidence', 0)
                    sources = result.get('sources', [])
                    
                    print(f"✅ Success (Confidence: {confidence:.2f})")
                    print(f"📝 Answer: {answer}")
                    if sources:
                        print(f"📚 Sources: {len(sources)} documents")
                        for source in sources:
                            print(f"   • {source.get('name', 'Unknown')}")
                else:
                    error = result.get('error', 'Unknown error')
                    confidence = result.get('confidence', 0)
                    print(f"❌ Failed (Confidence: {confidence:.2f})")
                    print(f"   Error: {error}")
                    
            except Exception as e:
                print(f"❌ Query failed: {e}")
        
        # Step 3: Test a broader search to see what documents are being found
        print(f"\n🔍 Step 3: Testing document discovery...")
        
        async with db_manager.get_session() as session:
            # Search for any documents that mention security terms
            result = await session.execute(text("""
                SELECT name, 
                       CASE WHEN search_text ILIKE '%compliance%' THEN 'compliance'
                            WHEN search_text ILIKE '%security%' THEN 'security'
                            WHEN search_text ILIKE '%policy%' THEN 'policy'
                            WHEN search_text ILIKE '%GDPR%' THEN 'GDPR'
                            ELSE 'other' END as match_type,
                       length(search_text) as content_length
                FROM itglue_entities 
                WHERE organization_id = '3183713165639879' 
                AND entity_type = 'document'
                AND (
                    search_text ILIKE '%compliance%' OR
                    search_text ILIKE '%security%' OR 
                    search_text ILIKE '%policy%' OR
                    search_text ILIKE '%GDPR%'
                )
                ORDER BY match_type, name
            """))
            
            matching_docs = result.fetchall()
            print(f"📊 Found {len(matching_docs)} documents with compliance/security content:")
            
            for doc in matching_docs:
                print(f"   • {doc.name} ({doc.match_type}) - {doc.content_length} chars")
        
        print(f"\n🎉 Testing complete!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_compliance_document())