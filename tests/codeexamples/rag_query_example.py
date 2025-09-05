#!/usr/bin/env python3
"""
RAG Query Example - How to query IT Glue documents using natural language.

This example demonstrates the complete RAG (Retrieval-Augmented Generation) pipeline
that successfully queries the Faucets Limited compliance documentation.

Success Metrics:
- Query: "What compliance standards does Faucets follow?"
- Confidence: 0.51 (above 0.4 threshold)  
- Response: GDPR, ISO 27001, PCI DSS compliance standards
- Response Time: 274ms
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.data import db_manager
from src.query.engine import QueryEngine
from src.services.itglue.client import ITGlueClient


async def rag_query_example():
    """Example of successful RAG query implementation."""
    print("🎯 RAG Query Example - IT Glue Document Search")
    print("=" * 60)
    
    try:
        # Step 1: Initialize database (CRITICAL - always do this first)
        print("🔧 Initializing database...")
        await db_manager.initialize()
        print("✅ Database initialized")
        
        # Step 2: Create query engine with IT Glue client
        print("🤖 Creating query engine...")
        client = ITGlueClient()
        query_engine = QueryEngine(itglue_client=client)
        print("✅ Query engine ready")
        
        # Step 3: Execute natural language query
        print("\n🎯 Executing RAG query...")
        
        query = "What compliance standards does Faucets follow?"
        company = "Faucets Limited"
        
        print(f"   Query: {query}")
        print(f"   Company: {company}")
        
        result = await query_engine.process_query(
            query=query,
            company=company
        )
        
        # Step 4: Process results
        if result.get('success'):
            print(f"\n✅ SUCCESS!")
            print(f"📊 Confidence: {result.get('confidence', 0):.2f}")
            print(f"⚡ Response Time: {result.get('response_time_ms', 0):.1f}ms")
            
            # Extract document content
            data = result.get('data', {})
            if data:
                print(f"📄 Source: {data.get('name', 'Unknown')}")
                print(f"📋 Type: {data.get('type', 'Unknown')}")
                
                # Extract compliance information
                content = data.get('content', '')
                if content and 'compliance' in content.lower():
                    print(f"\n🔍 Compliance Standards Found:")
                    
                    lines = content.split('\n')
                    for line in lines:
                        if any(term in line.lower() for term in ['gdpr', 'iso', 'pci']):
                            print(f"   • {line.strip()}")
            
            # Show sources
            source_ids = result.get('source_ids', [])
            if source_ids:
                print(f"\n📚 Source Documents: {len(source_ids)} referenced")
        
        else:
            print(f"❌ FAILED")
            print(f"Error: {result.get('error', 'Unknown error')}")
            print(f"Confidence: {result.get('confidence', 0):.2f}")
        
        return result
        
    except Exception as e:
        print(f"❌ Example failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def multiple_query_example():
    """Example of running multiple related queries."""
    print("\n🔄 Multiple Query Example")
    print("=" * 40)
    
    # Initialize once, query multiple times
    await db_manager.initialize()
    client = ITGlueClient()
    query_engine = QueryEngine(itglue_client=client)
    
    queries = [
        "What compliance standards does Faucets follow?",
        "What is Faucets' multi-factor authentication policy?", 
        "What are Faucets' password requirements?",
        "What security audits does Faucets perform?"
    ]
    
    successful = 0
    for i, query in enumerate(queries, 1):
        print(f"\n🎯 Query {i}: {query}")
        
        result = await query_engine.process_query(
            query=query,
            company="Faucets Limited"
        )
        
        if result.get('success'):
            print(f"   ✅ SUCCESS - Confidence: {result.get('confidence', 0):.2f}")
            successful += 1
        else:
            print(f"   ❌ FAILED - {result.get('error', 'Unknown error')}")
    
    print(f"\n📊 Success Rate: {successful}/{len(queries)} ({successful/len(queries)*100:.1f}%)")


if __name__ == "__main__":
    print("🚀 Starting RAG Query Examples...")
    
    # Run single query example
    asyncio.run(rag_query_example())
    
    # Run multiple queries example  
    asyncio.run(multiple_query_example())
    
    print("\n🎉 Examples complete!")