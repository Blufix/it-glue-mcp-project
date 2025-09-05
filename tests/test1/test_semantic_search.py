#!/usr/bin/env python3
"""Test semantic search functionality with newly generated embeddings."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.search.unified_hybrid import UnifiedHybridSearch
from src.data import db_manager
from src.config.settings import settings

async def test_semantic_search():
    """Test semantic search with Faucets data."""
    print("🔍 Testing Semantic Search with Qdrant Embeddings")
    print("=" * 60)
    
    # Initialize database and search
    await db_manager.initialize()
    
    try:
        search = UnifiedHybridSearch()
        await search.initialize()
        
        # Test queries
        test_queries = [
            "server configurations",
            "network equipment",
            "firewall settings", 
            "Windows systems",
            "backup solutions"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Query: '{query}'")
            print("-" * 30)
            
            results = await search.search(
                query=query,
                organization_id="12345",  # Faucets org ID
                limit=3
            )
            
            if results and results.get('success'):
                items = results.get('results', [])
                print(f"Found {len(items)} results:")
                
                for i, item in enumerate(items, 1):
                    print(f"  {i}. {item.get('name', 'N/A')} ({item.get('entity_type', 'N/A')})")
                    print(f"     Score: {item.get('score', 'N/A'):.3f}")
                    if 'snippet' in item:
                        print(f"     Snippet: {item['snippet'][:100]}...")
            else:
                print(f"❌ No results or error: {results}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(test_semantic_search())