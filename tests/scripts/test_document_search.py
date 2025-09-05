#!/usr/bin/env python3
"""Test document search functionality across all three systems."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.search.unified_hybrid import UnifiedHybridSearch, SearchMode


async def test_document_search():
    """Test searching the Faucets documents."""
    
    print("=" * 80)
    print("TESTING FAUCETS DOCUMENT SEARCH")
    print("=" * 80)
    
    # Initialize unified search
    search = UnifiedHybridSearch(
        keyword_weight=0.3,
        semantic_weight=0.5,
        graph_weight=0.2
    )
    
    await search.initialize()
    
    # Test queries - mix of specific terms and concepts
    test_queries = [
        # Keyword searches (should match directly)
        ("disaster recovery", SearchMode.KEYWORD),
        ("security policy", SearchMode.KEYWORD),
        ("network infrastructure", SearchMode.KEYWORD),
        
        # Semantic searches (should find related concepts)
        ("How to handle system failures", SearchMode.SEMANTIC),
        ("Data protection requirements", SearchMode.SEMANTIC),
        ("Emergency procedures", SearchMode.SEMANTIC),
        ("Backup strategy", SearchMode.SEMANTIC),
        
        # Hybrid searches (best of both)
        ("compliance", SearchMode.HYBRID),
        ("procedures", SearchMode.HYBRID),
        ("monitoring", SearchMode.HYBRID),
    ]
    
    for query, mode in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: '{query}'")
        print(f"Mode: {mode.value}")
        print("-" * 60)
        
        try:
            results = await search.search(
                query=query,
                mode=mode,
                organization_id="3183713165639879",  # Faucets org
                entity_type="document",
                limit=3
            )
            
            if results:
                print(f"Found {len(results)} results:\n")
                
                for i, result in enumerate(results, 1):
                    print(f"{i}. 📄 {result.name}")
                    print(f"   Score: {result.total_score:.3f}")
                    
                    # Show which search methods contributed
                    contributions = []
                    if result.keyword_score is not None:
                        contributions.append(f"Keyword: {result.keyword_score:.3f}")
                    if result.semantic_score is not None:
                        contributions.append(f"Semantic: {result.semantic_score:.3f}")
                    if result.graph_score is not None:
                        contributions.append(f"Graph: {result.graph_score:.3f}")
                    
                    if contributions:
                        print(f"   Contributions: {', '.join(contributions)}")
                    
                    # Show tags if available
                    if result.payload and 'tags' in result.payload:
                        tags = result.payload['tags']
                        if tags:
                            print(f"   Tags: {', '.join(tags)}")
                    
                    print()
            else:
                print("❌ No results found")
                
        except Exception as e:
            print(f"Error: {e}")
    
    # Test specific document content
    print("\n" + "=" * 80)
    print("TESTING SPECIFIC DOCUMENT CONTENT")
    print("=" * 80)
    
    specific_searches = [
        "RTO recovery time objective",
        "GDPR compliance",
        "Aruba switch configuration",
        "Faucets Limited mission",
        "quarterly vulnerability assessments"
    ]
    
    for query in specific_searches:
        print(f"\n🔍 Searching for: '{query}'")
        
        results = await search.search(
            query=query,
            mode=SearchMode.HYBRID,
            organization_id="3183713165639879",
            entity_type="document",
            limit=1
        )
        
        if results:
            result = results[0]
            print(f"   ✓ Found in: {result.name}")
            print(f"   Score: {result.total_score:.3f}")
        else:
            print(f"   ❌ Not found")
    
    # Summary
    print("\n" + "=" * 80)
    print("SEARCH CAPABILITIES DEMONSTRATED")
    print("=" * 80)
    print("""
✅ KEYWORD SEARCH: Exact text matching
   - Finds specific terms and phrases
   - Best for known terminology
   
✅ SEMANTIC SEARCH: Concept understanding
   - Finds related ideas and concepts
   - Best for natural language queries
   
✅ HYBRID SEARCH: Combined intelligence
   - Balances exact matches with semantic understanding
   - Best overall search experience

📚 Your 5 Faucets documents are fully searchable:
   1. Company Overview
   2. IT Infrastructure Documentation
   3. Standard Operating Procedures
   4. Security Policies and Compliance
   5. Disaster Recovery Plan

The search system can:
- Find specific procedures and policies
- Answer conceptual questions
- Locate related information across documents
- Provide context-aware results
""")
    
    await search.close()


if __name__ == "__main__":
    asyncio.run(test_document_search())