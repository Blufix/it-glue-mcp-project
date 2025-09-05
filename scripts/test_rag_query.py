#!/usr/bin/env python3
"""Test RAG query against Faucets O365 conditional access policies."""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.query.engine import QueryEngine
from src.services.itglue.client import ITGlueClient
from src.data import db_manager
from src.embeddings.generator import EmbeddingGenerator


async def test_rag_query():
    """Test RAG query for Faucets O365 conditional access policies."""
    print("🔍 Testing RAG Query: Faucets O365 Conditional Access Policies")
    print("=" * 70)
    
    try:
        # Initialize database
        await db_manager.initialize()
        
        # First, let's check what's in the Security document
        print("📋 Step 1: Examining Security Policies document...")
        
        async with db_manager.get_session() as session:
            from sqlalchemy import text
            
            # Get the security document
            result = await session.execute(text("""
                SELECT name, attributes->>'content' as content
                FROM itglue_entities 
                WHERE organization_id = '3183713165639879' 
                AND entity_type = 'document' 
                AND name ILIKE '%security%'
                LIMIT 1
            """))
            
            doc = result.fetchone()
            
            if doc:
                print(f"✅ Found document: {doc.name}")
                content = doc.content or ""
                
                # Show first 500 chars as preview
                preview = content[:500] + "..." if len(content) > 500 else content
                print(f"\n📄 Content preview:\n{preview}\n")
                
                # Search for O365/conditional access related content
                o365_keywords = ['office 365', 'o365', 'conditional access', 'azure ad', 'multifactor', 'mfa']
                found_keywords = []
                
                content_lower = content.lower()
                for keyword in o365_keywords:
                    if keyword in content_lower:
                        found_keywords.append(keyword)
                
                if found_keywords:
                    print(f"🎯 Found O365/Security keywords: {', '.join(found_keywords)}")
                    
                    # Extract sections that mention these keywords
                    lines = content.split('\n')
                    relevant_sections = []
                    
                    for i, line in enumerate(lines):
                        if any(keyword in line.lower() for keyword in o365_keywords):
                            # Get context around this line (3 lines before and after)
                            start = max(0, i - 3)
                            end = min(len(lines), i + 4)
                            section = '\n'.join(lines[start:end])
                            relevant_sections.append(section)
                    
                    print(f"\n📑 Relevant sections about O365/Conditional Access:")
                    print("=" * 50)
                    
                    for i, section in enumerate(relevant_sections[:3], 1):  # Show first 3 sections
                        print(f"\nSection {i}:")
                        print(section)
                        print("-" * 30)
                
                else:
                    print("⚠️ No obvious O365/conditional access keywords found")
                    print("📝 Let's try semantic search with embeddings...")
                    
                    # Try semantic search using embeddings
                    await semantic_search_test(content)
                    
            else:
                print("❌ No security policy document found")
        
        print("\n" + "=" * 70)
        print("🚀 Now testing the actual RAG query engine...")
        
        # Test the actual query engine
        await test_query_engine()
        
    except Exception as e:
        print(f"❌ RAG query test failed: {e}")
        import traceback
        traceback.print_exc()


async def semantic_search_test(content: str):
    """Test semantic similarity search."""
    print("\n🔍 Testing semantic search...")
    
    try:
        generator = EmbeddingGenerator()
        
        # Generate embedding for our query
        query = "tell me what conditional access policies Faucets have in O365"
        query_embedding = await generator.generate_embedding(query)
        
        # Generate embedding for document content
        content_embedding = await generator.generate_embedding(content)
        
        # Calculate similarity (dot product for normalized embeddings)
        import numpy as np
        
        similarity = np.dot(query_embedding, content_embedding)
        print(f"📊 Semantic similarity score: {similarity:.3f}")
        
        if similarity > 0.3:  # Threshold for relevance
            print("✅ Document appears semantically relevant to the query")
        else:
            print("⚠️ Document may not contain specific O365 conditional access information")
            
    except Exception as e:
        print(f"❌ Semantic search test failed: {e}")


async def test_query_engine():
    """Test the actual QueryEngine with our question."""
    print("\n🤖 Testing QueryEngine...")
    
    try:
        # Initialize components
        client = ITGlueClient()
        query_engine = QueryEngine(itglue_client=client)
        
        # The specific query
        query = "tell me what conditional access policies Faucets have in O365"
        company = "Faucets Limited"
        
        print(f"🎯 Query: {query}")
        print(f"🏢 Company: {company}")
        
        # Execute the query
        result = await query_engine.process_query(
            query=query,
            company=company
        )
        
        print("\n📋 Query Result:")
        print("=" * 40)
        print(json.dumps(result, indent=2, default=str))
        
        # Extract and highlight the answer
        if result.get('success'):
            answer = result.get('answer', 'No answer provided')
            sources = result.get('sources', [])
            confidence = result.get('confidence', 0)
            
            print(f"\n🎯 Answer (Confidence: {confidence:.2f}):")
            print(answer)
            
            if sources:
                print(f"\n📚 Sources ({len(sources)}):")
                for i, source in enumerate(sources, 1):
                    print(f"  {i}. {source.get('name', 'Unknown')} ({source.get('type', 'Unknown type')})")
        else:
            error = result.get('error', 'Unknown error')
            print(f"❌ Query failed: {error}")
        
    except Exception as e:
        print(f"❌ QueryEngine test failed: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main function."""
    await test_rag_query()
    print("\n🎉 RAG Query Test Complete!")


if __name__ == "__main__":
    asyncio.run(main())