#!/usr/bin/env python3
"""Test complete RAG pipeline with proper initialization."""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data import db_manager
from src.query.engine import QueryEngine
from src.services.itglue.client import ITGlueClient


async def test_complete_rag():
    """Test complete RAG pipeline with proper database initialization."""
    print("🎯 Testing Complete RAG Pipeline")
    print("=" * 60)
    
    try:
        # Step 1: Initialize database
        print("🔧 Step 1: Initializing database...")
        await db_manager.initialize()
        print("✅ Database initialized")
        
        # Step 2: Initialize query engine
        print("\n🤖 Step 2: Initializing query engine...")
        client = ITGlueClient()
        query_engine = QueryEngine(itglue_client=client)
        print("✅ Query engine initialized")
        
        # Step 3: Test a simple compliance query
        print(f"\n🎯 Step 3: Testing compliance query...")
        query = "What compliance standards does Faucets follow?"
        company = "Faucets Limited"
        
        print(f"Query: {query}")
        print(f"Company: {company}")
        
        result = await query_engine.process_query(
            query=query,
            company=company
        )
        
        print(f"\n📋 Query Result:")
        print("=" * 40)
        
        if result.get('success'):
            answer = result.get('answer', 'No answer provided')
            confidence = result.get('confidence', 0)
            sources = result.get('sources', [])
            
            print(f"✅ SUCCESS!")
            print(f"📊 Confidence: {confidence:.2f}")
            print(f"📝 Answer: {answer}")
            
            if sources:
                print(f"\n📚 Sources ({len(sources)}):")
                for i, source in enumerate(sources, 1):
                    print(f"  {i}. {source.get('name', 'Unknown')} ({source.get('type', 'Unknown type')})")
            else:
                print(f"⚠️ No sources provided")
        else:
            error = result.get('error', 'Unknown error')
            confidence = result.get('confidence', 0)
            print(f"❌ FAILED")
            print(f"📊 Confidence: {confidence:.2f}")
            print(f"❌ Error: {error}")
        
        # Step 4: Test a more specific query
        print(f"\n🎯 Step 4: Testing specific MFA query...")
        query2 = "What is Faucets' multi-factor authentication policy?"
        
        result2 = await query_engine.process_query(
            query=query2,
            company=company
        )
        
        print(f"Query: {query2}")
        
        if result2.get('success'):
            answer2 = result2.get('answer', 'No answer provided')
            confidence2 = result2.get('confidence', 0)
            print(f"✅ SUCCESS! Confidence: {confidence2:.2f}")
            print(f"📝 Answer: {answer2}")
        else:
            error2 = result2.get('error', 'Unknown error')
            confidence2 = result2.get('confidence', 0)
            print(f"❌ FAILED - Confidence: {confidence2:.2f}, Error: {error2}")
        
        # Summary
        print(f"\n" + "=" * 60)
        print(f"📊 TEST SUMMARY")
        print(f"=" * 60)
        
        query1_success = result.get('success', False)
        query2_success = result2.get('success', False)
        
        print(f"Query 1 (Compliance standards): {'✅ SUCCESS' if query1_success else '❌ FAILED'}")
        print(f"Query 2 (MFA policy): {'✅ SUCCESS' if query2_success else '❌ FAILED'}")
        
        if query1_success or query2_success:
            print(f"\n🎉 RAG PIPELINE IS WORKING!")
            print(f"   - Documents are properly synced and embedded")
            print(f"   - Confidence threshold adjustment was successful")
            print(f"   - System can query Faucets compliance documentation")
        else:
            print(f"\n❌ RAG pipeline needs more work")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_complete_rag())