#!/usr/bin/env python3
"""Test RAG queries with the fixed confidence threshold."""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.query.engine import QueryEngine
from src.services.itglue.client import ITGlueClient


async def test_fixed_threshold():
    """Test RAG queries with lowered confidence threshold."""
    print("🎯 Testing RAG Queries with Fixed Confidence Threshold")
    print("=" * 70)
    
    try:
        # Initialize query engine
        client = ITGlueClient()
        query_engine = QueryEngine(itglue_client=client)
        
        # Test queries about compliance content
        test_queries = [
            "What compliance standards does Faucets follow?",
            "Tell me about Faucets' GDPR compliance",
            "What are Faucets' password policies?", 
            "What is Faucets' multi-factor authentication policy?",
            "What security audits does Faucets perform?"
        ]
        
        successful_queries = 0
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n🎯 Query {i}: {query}")
            print("-" * 50)
            
            try:
                result = await query_engine.process_query(
                    query=query,
                    company="Faucets Limited"
                )
                
                if result.get('success'):
                    answer = result.get('answer', 'No answer provided')
                    confidence = result.get('confidence', 0)
                    sources = result.get('sources', [])
                    
                    print(f"✅ SUCCESS (Confidence: {confidence:.2f})")
                    print(f"📝 Answer: {answer}")
                    if sources:
                        print(f"📚 Sources: {len(sources)} documents")
                        for source in sources:
                            print(f"   • {source.get('name', 'Unknown')}")
                    
                    successful_queries += 1
                else:
                    error = result.get('error', 'Unknown error')
                    confidence = result.get('confidence', 0)
                    print(f"❌ FAILED (Confidence: {confidence:.2f})")
                    print(f"   Error: {error}")
                    
            except Exception as e:
                print(f"❌ Query failed with exception: {e}")
        
        # Summary
        print(f"\n" + "=" * 70)
        print(f"📊 RESULTS SUMMARY")
        print(f"=" * 70)
        print(f"✅ Successful queries: {successful_queries}/{len(test_queries)}")
        print(f"📈 Success rate: {successful_queries/len(test_queries)*100:.1f}%")
        
        if successful_queries > 0:
            print(f"\n🎉 SUCCESS! The confidence threshold fix worked!")
            print(f"   RAG system can now query the Compliance document successfully.")
        else:
            print(f"\n❌ Issues persist - may need further investigation.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_fixed_threshold())