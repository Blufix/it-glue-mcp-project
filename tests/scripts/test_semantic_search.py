#!/usr/bin/env python3
"""
Test semantic search functionality with Qdrant embeddings.
Compares keyword search vs semantic search results.
"""

import asyncio
import sys
from pathlib import Path
import aiohttp
import json
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from src.data import db_manager
from src.config.settings import settings
from sqlalchemy import text
from qdrant_client import QdrantClient
from src.search.hybrid import HybridSearch


async def generate_embedding_ollama(text: str) -> list[float]:
    """Generate embedding for a query using Ollama nomic model."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{settings.ollama_url}/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": text},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["embedding"]
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None


async def test_keyword_search(query: str):
    """Test traditional keyword search in PostgreSQL."""
    print(f"\n📝 KEYWORD SEARCH: '{query}'")
    print("-" * 50)
    
    await db_manager.initialize()
    
    async with db_manager.get_session() as session:
        result = await session.execute(text("""
            SELECT name, entity_type, search_text
            FROM itglue_entities
            WHERE search_text ILIKE :query
            LIMIT 5
        """), {"query": f"%{query}%"})
        
        results = result.fetchall()
        
        if results:
            for i, row in enumerate(results, 1):
                print(f"{i}. {row.name} ({row.entity_type})")
                print(f"   Match: ...{row.search_text[:100]}...")
        else:
            print("No results found")
    
    return len(results)


async def test_semantic_search(query: str):
    """Test semantic search using Qdrant embeddings."""
    print(f"\n🧠 SEMANTIC SEARCH: '{query}'")
    print("-" * 50)
    
    # Generate query embedding
    embedding = await generate_embedding_ollama(query)
    
    if not embedding:
        print("Failed to generate query embedding")
        return 0
    
    # Search in Qdrant
    client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
    
    results = client.search(
        collection_name="itglue_entities",
        query_vector=embedding,
        limit=5,
        score_threshold=0.3  # Lower threshold for nomic model
    )
    
    if results:
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.payload.get('name')} ({result.payload.get('entity_type')})")
            print(f"   Score: {result.score:.3f}")
            print(f"   Text: {result.payload.get('text', '')[:100]}...")
    else:
        print("No results found")
    
    return len(results)


async def test_hybrid_search(query: str):
    """Test hybrid search combining keyword and semantic."""
    print(f"\n🔄 HYBRID SEARCH: '{query}'")
    print("-" * 50)
    
    # Note: HybridSearch currently has initialization issues
    # It needs proper database setup in __init__
    # For now, we'll skip hybrid search or show the error
    
    try:
        search = HybridSearch()
        
        # Try to search
        results = await search.search(
            query=query,
            limit=5,
            company_id="3183713165639879"  # Faucets org ID
        )
        
        if results:
            for i, result in enumerate(results, 1):
                if hasattr(result, 'entity'):
                    print(f"{i}. {result.entity.name} ({result.entity.entity_type})")
                    print(f"   Combined Score: {result.combined_score:.3f}")
                    print(f"   Source: {result.source}")
                else:
                    print(f"{i}. {result}")
        else:
            print("No results found")
            
        return len(results)
    except Exception as e:
        print(f"Note: Hybrid search needs initialization fixes")
        print(f"Error: {e}")
        return 0


async def main():
    """Run comprehensive search tests."""
    print("=" * 80)
    print("SEMANTIC SEARCH TESTING WITH NOMIC EMBEDDINGS")
    print("=" * 80)
    
    # Check Qdrant status
    client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
    collection_info = client.get_collection("itglue_entities")
    print(f"\n📊 Qdrant Collection Status:")
    print(f"   Vectors: {collection_info.vectors_count}")
    print(f"   Points: {collection_info.points_count}")
    print(f"   Dimension: {collection_info.config.params.vectors.size}")
    
    # Check PostgreSQL status
    await db_manager.initialize()
    async with db_manager.get_session() as session:
        result = await session.execute(text("""
            SELECT COUNT(*) as total,
                   COUNT(embedding_id) as with_embeddings
            FROM itglue_entities
        """))
        row = result.fetchone()
        print(f"\n📊 PostgreSQL Status:")
        print(f"   Total entities: {row.total}")
        print(f"   With embeddings: {row.with_embeddings}")
    
    # Test queries
    test_queries = [
        "server configuration",
        "network infrastructure",
        "firewall security",
        "backup solution",
        "email system",
        "HP switch",
        "SQL database",
        "surface laptop",
        "printer setup",
        "sophos firewall"
    ]
    
    print("\n" + "=" * 80)
    print("RUNNING SEARCH COMPARISONS")
    print("=" * 80)
    
    results_summary = []
    
    for query in test_queries:
        print(f"\n{'=' * 80}")
        print(f"QUERY: '{query}'")
        print(f"{'=' * 80}")
        
        keyword_count = await test_keyword_search(query)
        semantic_count = await test_semantic_search(query)
        hybrid_count = await test_hybrid_search(query)
        
        results_summary.append({
            'query': query,
            'keyword': keyword_count,
            'semantic': semantic_count,
            'hybrid': hybrid_count
        })
        
        await asyncio.sleep(0.5)  # Small delay between queries
    
    # Print summary
    print("\n" + "=" * 80)
    print("SEARCH RESULTS SUMMARY")
    print("=" * 80)
    print(f"{'Query':<25} {'Keyword':<10} {'Semantic':<10} {'Hybrid':<10}")
    print("-" * 55)
    
    for result in results_summary:
        print(f"{result['query']:<25} {result['keyword']:<10} {result['semantic']:<10} {result['hybrid']:<10}")
    
    # Calculate totals
    total_keyword = sum(r['keyword'] for r in results_summary)
    total_semantic = sum(r['semantic'] for r in results_summary)
    total_hybrid = sum(r['hybrid'] for r in results_summary)
    
    print("-" * 55)
    print(f"{'TOTAL':<25} {total_keyword:<10} {total_semantic:<10} {total_hybrid:<10}")
    
    print("\n" + "=" * 80)
    print("✅ SEMANTIC SEARCH TESTING COMPLETE")
    print("=" * 80)
    
    await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())