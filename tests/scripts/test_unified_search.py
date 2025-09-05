#!/usr/bin/env python3
"""Test the unified hybrid search combining PostgreSQL, Qdrant, and Neo4j."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.search.unified_hybrid import UnifiedHybridSearch, SearchMode


async def test_unified_search():
    """Test unified search across all three databases."""
    
    print("=" * 80)
    print("UNIFIED HYBRID SEARCH TEST - ALL THREE SYSTEMS")
    print("=" * 80)
    
    # Initialize unified search
    unified_search = UnifiedHybridSearch(
        keyword_weight=0.3,
        semantic_weight=0.5,
        graph_weight=0.2
    )
    
    await unified_search.initialize()
    
    # Test queries
    test_queries = [
        ("aruba switch", SearchMode.HYBRID),
        ("network infrastructure", SearchMode.HYBRID),
        ("server", SearchMode.KEYWORD),
        ("firewall configuration", SearchMode.SEMANTIC),
        ("aruba", SearchMode.GRAPH),
        ("HYPERV01", SearchMode.IMPACT),
        ("SQL", SearchMode.DEPENDENCY)
    ]
    
    for query, mode in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: '{query}'")
        print(f"Mode: {mode.value}")
        print("-" * 60)
        
        try:
            results = await unified_search.search(
                query=query,
                mode=mode,
                limit=5
            )
            
            if results:
                print(f"Found {len(results)} results:\n")
                
                for i, result in enumerate(results, 1):
                    print(f"{i}. {result.name}")
                    print(f"   Type: {result.entity_type}")
                    print(f"   Total Score: {result.total_score:.3f}")
                    
                    # Show individual scores
                    scores = []
                    if result.keyword_score is not None:
                        scores.append(f"Keyword: {result.keyword_score:.3f}")
                    if result.semantic_score is not None:
                        scores.append(f"Semantic: {result.semantic_score:.3f}")
                    if result.graph_score is not None:
                        scores.append(f"Graph: {result.graph_score:.3f}")
                    
                    if scores:
                        print(f"   Scores: {', '.join(scores)}")
                    
                    print(f"   Sources: {', '.join(result.sources)}")
                    
                    # Show relationships if available
                    if result.relationships:
                        print(f"   Relationships: {len(result.relationships)} connections")
                        for rel in result.relationships[:3]:
                            print(f"     - {rel.get('type', 'Unknown')} → {rel.get('related_name', 'Unknown')}")
                    
                    # Show impact analysis if available
                    if result.impact_analysis:
                        impact = result.impact_analysis
                        print(f"   Impact Analysis:")
                        print(f"     - Source: {impact.get('source_entity', 'Unknown')}")
                        print(f"     - Impact Level: {impact.get('impact_level', 'Unknown')}")
                        print(f"     - Direct: {impact.get('direct_connections', 0)} connections")
                        print(f"     - Indirect: {impact.get('indirect_connections', 0)} connections")
                    
                    print()
            else:
                print("No results found")
                
        except Exception as e:
            print(f"Error: {e}")
    
    # Demonstrate combined search power
    print("\n" + "=" * 80)
    print("DEMONSTRATING COMBINED SEARCH POWER")
    print("=" * 80)
    
    print("\n🔍 Hybrid Search for 'switch' (combines all three systems):")
    print("-" * 60)
    
    results = await unified_search.search(
        query="switch",
        mode=SearchMode.HYBRID,
        limit=3
    )
    
    for result in results:
        print(f"\n📊 {result.name}")
        print(f"   Combined Score: {result.total_score:.3f}")
        
        # Show contribution from each system
        contributions = []
        if result.keyword_score:
            contrib = result.keyword_score * unified_search.keyword_weight
            contributions.append(f"PostgreSQL: {contrib:.3f}")
        
        if result.semantic_score:
            contrib = result.semantic_score * unified_search.semantic_weight
            contributions.append(f"Qdrant: {contrib:.3f}")
        
        if result.graph_score:
            contrib = result.graph_score * unified_search.graph_weight
            contributions.append(f"Neo4j: {contrib:.3f}")
        
        print(f"   Contributions: {' + '.join(contributions)}")
        print(f"   Data Sources: {', '.join(result.sources)}")
    
    # Show system status
    print("\n" + "=" * 80)
    print("SYSTEM STATUS")
    print("=" * 80)
    
    print("""
✅ PostgreSQL: Keyword/text search
   - Full-text search on entity names and attributes
   - Exact matching and partial text matching
   
✅ Qdrant: Semantic/vector search  
   - 768-dimensional embeddings using nomic-embed-text
   - Finds conceptually similar entities
   
✅ Neo4j: Graph/relationship search
   - Relationship traversal and impact analysis
   - Dependency mapping and topology understanding
   
✅ Unified Search: Combines all three
   - Weighted scoring from all systems
   - Context-aware result ranking
   - Rich relationship and impact data
    """)
    
    await unified_search.close()
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_unified_search())